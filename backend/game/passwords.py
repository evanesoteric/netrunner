"""Timed password breaking inside the fictional game network."""
import math
from datetime import timedelta
from uuid import uuid4
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .catalog import SOFTWARE
from .mechanics import GameError, hardware, transact, log, choose_tool
from .persistence import current_target, record_action, sync_remote_logs


def cancel_break(slot):
    if slot.mission_state.pop('password_break', None):
        slot.mission_state['password_result'] = 'cancelled'
        log(slot, 'terminal', 'Password breaker cancelled. Compute charge is not refunded.')


def start_break(slot, port=None, product_id=None):
    if 'terminal' not in slot.running_apps:
        raise GameError('Launch the primary terminal first.')
    if not slot.mission_started:
        raise GameError('Connect to a server login first.')
    state = slot.mission_state
    if state.get('access'):
        raise GameError('Already logged in to this server.')
    if state.get('password_result') == 'ready':
        raise GameError('Password already decoded. Click Login to enter the system.')
    if state.get('password_break'):
        raise GameError('A password breaker is already running.')
    target = current_target(slot)
    if not state.get('scanned') or state.get('scanned_host') != target['target'] or state.get('scanned_revision', 1) != target.get('server_revision', 1):
        raise GameError('No service fingerprint available. Scan this server with Cartograph first.')
    if port is not None and str(port) != str(target['port']):
        raise GameError('Connection refused on this port.')
    tool = choose_tool(slot, 'cracker', product_id)
    product = tool['id']
    slot.mission_state['password_tool'] = product
    transact(slot, -(tool['tier'] + 1), f'Compute // {tool["name"]}')
    seconds = max(4, math.ceil(22 * target['security'] / (hardware(slot)['cpu']['speed'] * tool['speed']) + state.get('latency', 0) / 24))
    started = timezone.now()
    state['password_break'] = dict(id=uuid4().hex, target=target['target'], port=target['port'],
                                  revision=target.get('server_revision', 1), product_id=product,
                                  started_at=started.isoformat(), finishes_at=(started + timedelta(seconds=seconds)).isoformat(),
                                  duration=seconds)
    state.pop('password_result', None)
    log(slot, 'terminal', f'Password breaker started on {target["target"]}:{target["port"]}. Estimated duration: {seconds}s.')


def settle_break(slot):
    state = slot.mission_state
    attempt = state.get('password_break')
    if not attempt:
        return
    target = current_target(slot)
    if ('terminal' not in slot.running_apps or not slot.mission_started or not target or target['target'] != attempt['target'] or
            target.get('server_revision', 1) != attempt['revision'] or target['port'] != attempt['port'] or
            attempt['product_id'] not in slot.installed_software):
        cancel_break(slot)
        slot.save()
        return
    deadline = parse_datetime(attempt['finishes_at'])
    if timezone.now() < deadline:
        return
    tool = SOFTWARE[attempt['product_id']]
    del state['password_break']
    if tool['power'] < target['security']:
        state['password_result'] = 'failed'
        log(slot, 'terminal', f'Tool capability {tool["power"]} is insufficient for security class {target["security"]}. Operation failed.')
    else:
        state['password_result'] = 'ready'
        state['password_ready'] = dict(target=target['target'], port=target['port'], revision=target.get('server_revision', 1), connection=slot.mission_started.isoformat())
        log(slot, 'terminal', 'Password decoded. Click Login to enter the system.')
    slot.save()


def login_target(slot):
    state = slot.mission_state
    target = current_target(slot)
    ready = state.get('password_ready')
    if not slot.mission_started or not target or state.get('access'):
        raise GameError('Connect to a server login first.')
    expected = dict(target=target['target'], port=target['port'], revision=target.get('server_revision', 1), connection=slot.mission_started.isoformat())
    if state.get('password_result') != 'ready' or ready != expected:
        raise GameError('Decode this server password before logging in.')
    # Login is explicit; time spent decoding or reviewing the form consumes no trace.
    state.update(access=True, dirty=True, trace_started=timezone.now().isoformat(), work=0, password_result='granted')
    state.pop('password_ready', None)
    record_action(slot, target, 'access_granted', 'Administrator login accepted; filesystem mounted.')
    sync_remote_logs(slot)
    log(slot, 'terminal', f'Logged in as admin on {target["target"]}. Remote filesystem mounted. Trace started.')
