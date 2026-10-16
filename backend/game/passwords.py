"""Timed password breaking inside the fictional game network."""
import math
from datetime import timedelta
from uuid import uuid4
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .catalog import SOFTWARE
from .mechanics import GameError, hardware, transact, log
from .persistence import current_target, record_action, sync_remote_logs


def cancel_break(slot):
    if slot.mission_state.pop('password_break', None):
        slot.mission_state['password_result'] = 'cancelled'
        log(slot, 'cracker', 'Password breaker cancelled. Compute charge is not refunded.')


def start_break(slot, port=None):
    product = slot.running_apps.get('cracker')
    if not product:
        raise GameError('Launch Lockpick before starting the password breaker.')
    if not slot.mission_started:
        raise GameError('Connect to a server login first.')
    state = slot.mission_state
    if state.get('access'):
        raise GameError('Already logged in to this server.')
    if state.get('password_break'):
        raise GameError('A password breaker is already running.')
    target = current_target(slot)
    if not state.get('scanned') or state.get('scanned_host') != target['target'] or state.get('scanned_revision', 1) != target.get('server_revision', 1):
        raise GameError('No service fingerprint available. Scan this server with Cartograph first.')
    if port is not None and str(port) != str(target['port']):
        raise GameError('Connection refused on this port.')
    tool = SOFTWARE[product]
    transact(slot, -(tool['tier'] + 1), f'Compute // {tool["name"]}')
    seconds = max(4, math.ceil(22 * target['security'] / (hardware(slot)['cpu']['speed'] * tool['speed']) + state.get('latency', 0) / 24))
    started = timezone.now()
    state['password_break'] = dict(id=uuid4().hex, target=target['target'], port=target['port'],
                                  revision=target.get('server_revision', 1), product_id=product,
                                  started_at=started.isoformat(), finishes_at=(started + timedelta(seconds=seconds)).isoformat(),
                                  duration=seconds)
    state.pop('password_result', None)
    log(slot, 'cracker', f'Password breaker started on {target["target"]}:{target["port"]}. Estimated duration: {seconds}s.')


def settle_break(slot):
    state = slot.mission_state
    attempt = state.get('password_break')
    if not attempt:
        return
    target = current_target(slot)
    if (not slot.mission_started or not target or target['target'] != attempt['target'] or
            target.get('server_revision', 1) != attempt['revision'] or target['port'] != attempt['port'] or
            slot.running_apps.get('cracker') != attempt['product_id']):
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
        log(slot, 'cracker', f'Tool capability {tool["power"]} is insufficient for security class {target["security"]}. Operation failed.')
    else:
        # Completion time, rather than the next poll, starts the trace.
        state.update(access=True, dirty=True, trace_started=deadline.isoformat(), work=0, password_result='granted')
        record_action(slot, target, 'access_granted', 'Authentication compromised; filesystem mounted.')
        sync_remote_logs(slot)
        log(slot, 'cracker', 'Authentication compromised. Remote filesystem mounted. Trace started.')
    slot.save()
