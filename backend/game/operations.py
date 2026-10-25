"""Simulated hidden-market operations; never execute code or contact hosts."""
from datetime import timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .world import all_servers, get_contract, session_target, target_for_server
from .world_seed import MARKET_ADDRESS
from .mechanics import GameError, transact, log, validate_route, route_stats, hardware
from .persistence import ensure_server, effective_target, event, record_visit, record_action, record_proxy_route, schedule

RANSOM_SECONDS = 120


def find_target(slot, address):
    job = get_contract(slot.active_contract, slot)
    if job:
        if address != job['target']:
            raise GameError('Finish or abort the reserved assignment before visiting another target.')
        return job
    server = next((server for server in all_servers(slot) if server['address'] == address and not server.get('market')), None)
    if not server:
        known = slot.server_states.filter(address=address).first()
        if known and known.descriptor.get('rank', 0) <= slot.rank + 1:
            return {**known.descriptor, 'objective':'explore'}
        raise GameError('Host not present in your network directory.')
    if server['rank'] > slot.rank:
        raise GameError('This server exceeds your rank clearance.')
    return target_for_server(server)


def connect_target(slot, address, backdoor=False):
    if slot.mission_started:
        raise GameError('Disconnect before opening another remote session.')
    if address == MARKET_ADDRESS and not backdoor:
        if slot.active_contract:
            raise GameError('Finish or abort your assignment before opening the hidden market.')
        slot.market_unlocked = True
        from .world import get_server
        market = target_for_server(get_server('world-4'))
        record_visit(slot, market, backdoor=False)
        return 'NULL EXCHANGE // invitation accepted. Hidden market unlocked in your sidebar.'
    if backdoor:
        if 'rootkit-epic' not in slot.installed_software:
            raise GameError('A Wraith Rootkit license is required.')
        target = next((entry for entry in slot.backdoors if entry['target'] == address), None)
        if not target:
            raise GameError('No installed backdoor on that server.')
        job = get_contract(slot.active_contract, slot)
        if job and job['target'] != address:
            raise GameError('Finish or abort the reserved assignment before jumping to another target.')
        target = dict(job or target)
        ensure_server(slot, target)
        target = effective_target(slot, target)
        record_visit(slot, target, backdoor=True)
        slot.remote_host = {**target, '_backdoor': True}
        slot.mission_state = {**(slot.mission_state if job else {}), 'access': True, 'scanned': True, 'dirty': False, 'work': 0}
        slot.mission_started = timezone.now()
        return f'Backdoor link established: {address}. Direct access / no proxy lease / remote logging suppressed.'
    target = find_target(slot, address)
    server = ensure_server(slot, target)
    target = effective_target(slot, target)
    validate_route(slot, slot.proxy_route)
    stats = route_stats(slot, target=target)
    transact(slot, -stats['fee'], f'Route lease // {address}')
    slot.remote_host = {} if slot.active_contract else target
    slot.mission_started = timezone.now()
    record_visit(slot, target)
    record_proxy_route(slot, target)
    state = slot.mission_state
    scanned = state.get('scanned') and (bool(slot.active_contract) or state.get('scanned_host') == address)
    scanned_revision = state.get('scanned_revision', 1)
    if not slot.active_contract:
        slot.mission_state = {'scanned_revision': scanned_revision}
        state = slot.mission_state
    state.update(trace_budget=100 - target['security'] * 10 + stats['delay'] + hardware(slot)['gateway']['stealth'] * 8,
                 work=0, trace_started=None, scanned_host=address, latency=stats['latency'], access=False, dirty=False, clean_exit=False, scanned=bool(scanned) and state.get('scanned_revision', 1) == server.revision, logs_recorded=False)
    state.pop('password_break', None)
    state.pop('password_result', None)
    state.pop('password_ready', None)
    return f'Dialing {address} via {stats["hops"]} proxies.\nLease paid: {stats["fee"]} CPH. Remote session established. Server login awaiting authentication.'


def install_rootkit(slot):
    target = effective_target(slot, session_target(slot))
    if not slot.mission_started or not slot.mission_state.get('access') or not target:
        raise GameError('Mount the current server filesystem before installing a rootkit.')
    if any(entry['target'] == target['target'] for entry in slot.backdoors):
        raise GameError('A backdoor is already installed on this server.')
    snapshot = {key: value for key, value in target.items() if not key.startswith('_')}
    slot.backdoors = slot.backdoors + [snapshot]
    server = ensure_server(slot, target)
    server.backdoor_installed = True
    event(server, 'backdoor_installed', 'Wraith persistent entry installed. Future direct connections suppress remote logging.')
    server.save()
    slot.mission_state['dirty'] = True
    return f'Wraith installed on {target["target"]}. Persistent entry added to Backdoored Servers. Clean your initial access logs before disconnecting.'


def deploy_ransomware(slot, address):
    target = effective_target(slot, session_target(slot))
    if not slot.mission_started or not target or target['target'] != address or not slot.mission_state.get('access'):
        raise GameError('Connect to the specified server and mount its filesystem first.')
    if slot.active_contract or not target.get('exploitable') or not target.get('server_id'):
        raise GameError('Ransomware requires an amber, non-contract opportunity server.')
    if len(slot.ransomware_ops) >= 3:
        raise GameError('Three ransomware instances are already active. Wait for a payout.')
    if any(entry['target'] == address for entry in slot.ransomware_ops):
        raise GameError('A ransomware instance is already active on this server.')
    due = timezone.now() + timedelta(seconds=RANSOM_SECONDS)
    slot.ransomware_ops = slot.ransomware_ops + [dict(target=address, due_at=due.isoformat(), reward=target['ransom_reward'])]
    record_action(slot, target, 'ransomware_deployed', 'Eclipse instance deployed; timed payout pending.')
    slot.mission_state['dirty'] = True
    return f'Eclipse deployed on {address}. Payout in {RANSOM_SECONDS}s. Active instances: {len(slot.ransomware_ops)}/3.'


def settle_ransomware(slot):
    pending = []
    changed = False
    for entry in slot.ransomware_ops:
        if parse_datetime(entry['due_at']) <= timezone.now():
            transact(slot, entry['reward'], f'Ransomware payout // {entry["target"]}')
            log(slot, 'terminal', f'Ransomware operation complete on {entry["target"]}, you earned {entry["reward"]} CPH. Instance removed.')
            server = slot.server_states.filter(address=entry['target']).first()
            if server:
                event(server, 'ransomware_completed', f'Eclipse operation paid {entry["reward"]} CPH; instance removed.')
                schedule(server)
                server.save()
            changed = True
        else:
            pending.append(entry)
    if changed:
        slot.ransomware_ops = pending
        slot.save()
