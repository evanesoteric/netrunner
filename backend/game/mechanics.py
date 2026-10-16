"""Server-authoritative game simulation. Commands never invoke a shell or network."""
import math
import shlex
from datetime import timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .catalog import (
    BUILTIN_APPS, FAILURE_COOLDOWN, HARDWARE,
    PRODUCTS, SOFTWARE, SUCCESS_COOLDOWN, HOME_NODE, RANKS,
)
from .models import LedgerEntry
from .contracts import codes, public_code
from .world import all_contracts, get_contract, get_server, session_target
from .persistence import (current_target, effective_target, ensure_server, event, observe,
                          settle_world, record_action, record_failure, record_contract,
                          sync_remote_logs, clear_remote_logs)


class GameError(Exception):
    pass


def hardware(slot):
    return {kind: HARDWARE[product_id] for kind, product_id in slot.equipment.items()}


def ram_used(slot):
    return sum(BUILTIN_APPS[key]['ram'] if key in BUILTIN_APPS else SOFTWARE[value]['ram'] for key, value in slot.running_apps.items())


def route_stats(slot, route=None, target=None):
    nodes = [get_server(key) for key in (slot.proxy_route if route is None else route)]
    destination = target or session_target(slot)
    points = [HOME_NODE] + nodes + ([destination] if destination else [])
    transit = sum(math.hypot(a['x'] - b['x'], a['y'] - b['y']) for a, b in zip(points, points[1:]))
    return {'hops': len(nodes), 'fee': 8 + sum(n['fee'] for n in nodes), 'delay': sum(n['delay'] for n in nodes), 'latency': sum(n['latency'] for n in nodes) + math.ceil(transit / 30)}


def available_at(slot, contract_id):
    value = slot.contract_cooldowns.get(contract_id)
    return parse_datetime(value) if value else None


def trace_remaining(slot):
    if not slot.mission_started or slot.remote_host.get('_backdoor'):
        return None
    started = slot.mission_state.get('trace_started', slot.mission_started.isoformat())
    if not started:
        return None
    elapsed = (timezone.now() - parse_datetime(started)).total_seconds()
    return max(0, math.ceil(slot.mission_state.get('trace_budget', 0) - slot.mission_state.get('work', 0) - elapsed))


def log(slot, app, message):
    slot.mission_log = (slot.mission_log + [{'app': app, 'text': message}])[-200:]


def transact(slot, amount, description):
    if slot.balance + amount < 0:
        raise GameError('Insufficient CPH.')
    slot.balance += amount
    LedgerEntry.objects.create(slot=slot, amount=amount, description=description)


def fail(slot, reason):
    job = session_target(slot)
    if not job:
        return
    record_failure(slot, job, reason)
    contract_failure = bool(slot.active_contract)
    fine = min(slot.balance, 90 + job['rank'] * 80)
    if fine:
        transact(slot, -fine, f'Contract failure // {public_code(slot.active_contract)}' if slot.active_contract else f'Intrusion failure // {job["target"]}')
    slot.reputation = max(0, slot.reputation - 60)
    if slot.active_contract:
        slot.contract_cooldowns = {**slot.contract_cooldowns, slot.active_contract: (timezone.now() + timedelta(seconds=FAILURE_COOLDOWN)).isoformat()}
    slot.active_contract = ''
    slot.remote_host = {}
    slot.mission_started = None
    slot.mission_state = {}
    outcome = 'Contract lost.' if contract_failure else 'Remote link lost.'
    refresh = ' Broker refresh: 10 minutes.' if contract_failure else ''
    log(slot, 'terminal', f'{reason}\n{outcome} Fine {fine} CPH. Reputation −60 (floor 0).{refresh}')


def settle(slot):
    from .operations import settle_ransomware
    settle_ransomware(slot)
    from .passwords import settle_break
    settle_break(slot)
    if slot.mission_started and trace_remaining(slot) == 0:
        fail(slot, 'TRACE COMPLETE. Your gateway was identified.')
        slot.save()
    settle_world(slot)


def validate_route(slot, route):
    if slot.mission_started:
        raise GameError('Disconnect before changing your route.')
    if not isinstance(route, list) or any(not isinstance(key, str) for key in route):
        raise GameError('Route must be a list of relay IDs.')
    if len(route) != len(set(route)) or any(not get_server(key) for key in route):
        raise GameError('Use distinct servers from Atlas.')
    if any(key not in slot.atlas_nodes for key in route):
        raise GameError('Add each server to your Atlas directory before routing through it.')
    if len(route) > hardware(slot)['gateway']['hops']:
        raise GameError('This gateway cannot support that many proxy hops.')
    if any(get_server(key)['rank'] > slot.rank for key in route):
        raise GameError('A server on this route exceeds your clearance.')


def edit_directory(slot, action, server_id):
    if slot.mission_started:
        raise GameError('Disconnect before editing your Atlas directory.')
    if not isinstance(server_id, str) or not get_server(server_id) or (get_server(server_id).get('hidden') and not slot.market_unlocked):
        raise GameError('Select a server from the network directory.')
    if action == 'add':
        if server_id not in slot.atlas_nodes:
            slot.atlas_nodes = slot.atlas_nodes + [server_id]
    elif action == 'remove':
        slot.atlas_nodes = [key for key in slot.atlas_nodes if key != server_id]
        slot.proxy_route = [key for key in slot.proxy_route if key != server_id]
    else:
        raise GameError('Choose add or remove.')


def launch(slot, product_id):
    if not isinstance(product_id, str):
        raise GameError('Select an application.')
    if product_id in BUILTIN_APPS:
        app = product_id
    elif product_id in slot.installed_software:
        app = SOFTWARE[product_id]['kind']
    else:
        raise GameError('This application is not installed.')
    previous = dict(slot.running_apps)
    slot.running_apps = {**previous, app: product_id}
    if ram_used(slot) > hardware(slot)['memory']['ram']:
        slot.running_apps = previous
        raise GameError('Not enough free RAM. Close an application or fit more memory.')
    if app == 'cracker' and previous.get(app) != product_id:
        from .passwords import cancel_break
        cancel_break(slot)
    return app


def trade(slot, action, product_id):
    if slot.mission_started:
        raise GameError('Disconnect before changing your loadout.')
    if not isinstance(product_id, str) or product_id not in PRODUCTS:
        raise GameError('Unknown product.')
    item = PRODUCTS[product_id]
    if item.get('black_market') and not slot.market_unlocked:
        raise GameError('Discover the hidden market before trading epic licenses.')
    owned = slot.installed_software if product_id in SOFTWARE else slot.owned_hardware
    if action == 'buy':
        if product_id in owned:
            raise GameError('You already own this product.')
        if item['tier'] > min(5, slot.rank + 2):
            raise GameError('This product exceeds your market clearance (rank + 2).')
        transact(slot, -item['price'], f'Purchase // {item["name"]}')
        owned.append(product_id)
    elif action == 'sell':
        if product_id not in owned:
            raise GameError('You do not own this product.')
        if product_id in slot.equipment.values() or product_id in slot.running_apps.values():
            raise GameError('Unequip or close this product before selling it.')
        owned.remove(product_id)
        transact(slot, item['price'] // 2, f'Resale // {item["name"]}')
    elif action == 'equip':
        if product_id not in HARDWARE or product_id not in owned:
            raise GameError('Only owned hardware can be fitted.')
        category = item['category']
        if category == 'memory' and ram_used(slot) > item['ram']:
            raise GameError('Close applications before fitting this smaller memory module.')
        if category == 'gateway' and len(slot.proxy_route) > item['hops']:
            raise GameError('Shorten your proxy route before fitting this gateway.')
        if category == 'storage' and slot.mission_state.get('local_size', 0) > item['capacity']:
            raise GameError('This drive cannot hold your current delivery.')
        slot.equipment = {**slot.equipment, category: product_id}
    else:
        raise GameError('Choose buy, sell, or equip.')


MANUALS = {
    'terminal': 'LOCAL SHELL\nhelp — application manual\nrumors — intercepted hidden-service invitation\njump <host> — use an installed Wraith backdoor\napps — running processes and RAM\ncontracts — broker listings\naccept <contract-id> — reserve by the numeric ID in contracts (0–255)\nbrief — read the accepted brief\nroute — inspect the committed proxy chain\nconnect <host> — dial a fictional target\nstatus — gateway status\nhistory — recent operator journal for this target\nls — remote file listing\nget <file> — copy a readable file to local storage\nrm <file> — remove a remote file\ndisconnect — end the remote session\nsubmit — deliver evidence to the broker\nabort — abandon the contract (fine and reputation loss)\nclear — clear local console output',
    'mapper': 'CARTOGRAPH\nscan <host> — inspect a fictional host and its services\nCosts 1 + tool tier CPH. Scan quality depends on tool capability.',
    'cracker': 'LOCKPICK\nOpen the graphical password breaker from Applications. Connect to a server login and scan its authentication service first.',
    'decryptor': 'ROSETTA\ndecrypt <file> — decode an encrypted remote archive\nRequires file access and a sufficient decryption engine.',
    'cleaner': 'ASHFALL\nerase — remove remote access logs\nLater remote operations can leave new log entries.',
    'monitor': 'TRIPWIRE\ntrace — inspect the active trace\nThe monitor must remain running to show a live countdown.',
    'rootkit': 'WRAITH // EPIC\ninstall — persist a backdoor on the currently mounted server. Clean initial logs before leaving.\nFuture jump <host> connections bypass proxies and logs.',
    'ransomware': 'ECLIPSE // EPIC\ndeploy <host> — install on the currently mounted amber non-contract server. Maximum 3 instances; payout after 120 seconds; each instance then removes itself.',
    'bank': 'CIPHER BANK\nbalance — account balance\nhistory — latest 15 ledger entries',
}


def reserve(slot, contract_id):
    if slot.active_contract or slot.mission_started:
        raise GameError('An assignment or remote session is already open.')
    mapping = codes()
    key = next((key for key, code in mapping.items() if str(code) == contract_id), None)
    job = get_contract(key)
    if not job:
        raise GameError(f'Unknown contract ID {contract_id!r}. Run contracts and use its numeric ID (0–255).')
    if abs(job['rank'] - slot.rank) > 1:
        lower, upper = max(0, slot.rank - 1), min(len(RANKS) - 1, slot.rank + 1)
        raise GameError(f'Contract {contract_id} is outside your rank clearance: its rank is {RANKS[job["rank"]]}; your {RANKS[slot.rank]} clearance covers {RANKS[lower]} through {RANKS[upper]}.')
    ready = available_at(slot, key)
    if ready and ready > timezone.now():
        raise GameError('The broker is still sourcing a replacement assignment. Check its availability time.')
    slot.active_contract = key
    slot.remote_host = {}
    slot.mission_state = {}
    slot.mission_started = None
    return f'Reservation confirmed: {public_code(job["id"])}.\n{job["description"]}\nTarget: {job["target"]}. Payment: {job["reward"]} CPH.'


def _tool_work(slot, app, base):
    tool = SOFTWARE[slot.running_apps[app]]
    cost = tool['tier'] + 1
    if slot.balance < cost:
        return False, 'Insufficient CPH for tool compute time. No operation was performed.'
    transact(slot, -cost, f'Compute // {tool["name"]}')
    if slot.mission_started and slot.mission_state.get('access'):
        slot.mission_state['work'] = slot.mission_state.get('work', 0) + math.ceil(base / (hardware(slot)['cpu']['speed'] * tool['speed']) * 2 + slot.mission_state.get('latency', 0) / 12)
    return True, tool


def execute(slot, app, raw):
    if app not in slot.running_apps or app not in MANUALS:
        raise GameError('Launch this application before using its console.')
    try:
        parts = shlex.split(raw)
    except ValueError:
        log(slot, app, f'> {raw}\nUnclosed quote.')
        return
    if not parts:
        return
    verb, args = parts[0].lower(), parts[1:]
    log(slot, app, f'{slot.alias}@{app}:~$ {raw}')
    if verb == 'clear' and app == 'terminal':
        slot.mission_log = [entry for entry in slot.mission_log if entry.get('app') != app]
        return
    if verb == 'help' and not args:
        log(slot, app, MANUALS[app])
        return
    job = current_target(slot)
    state = slot.mission_state
    result = ''
    try:
        if app == 'bank':
            if verb == 'balance' and not args:
                result = f'CIPHER CURRENT ACCOUNT // {slot.alias}\nAvailable: {slot.balance:,} CPH'
            elif verb == 'history' and not args:
                result = '\n'.join(f'{entry.created_at:%Y-%m-%d %H:%M} UTC  {entry.amount:+} CPH  {entry.description}' for entry in slot.ledger.all()[:15]) or 'No transactions.'
            else:
                result = 'Unknown bank command. Read help for the bank manual.'
        elif app == 'terminal':
            result = _shell(slot, verb, args, job)
        elif app == 'cracker':
            if verb != 'crack' or len(args) != 1:
                raise GameError('Open the graphical Lockpick password breaker.')
            from .passwords import start_break
            start_break(slot, args[0])
            return
        elif app == 'rootkit':
            from .operations import install_rootkit
            if verb != 'install' or args:
                raise GameError('Use install while connected to a mounted server.')
            result = install_rootkit(slot)
        elif app == 'ransomware':
            from .operations import deploy_ransomware
            if verb != 'deploy' or len(args) != 1:
                raise GameError('Use deploy <host> on an amber opportunity server.')
            result = deploy_ransomware(slot, args[0])
        else:
            usages = {'mapper': ('scan', 1), 'cracker': ('crack', 1), 'decryptor': ('decrypt', 1), 'cleaner': ('erase', 0), 'monitor': ('trace', 0)}
            expected, count = usages[app]
            if verb != expected or len(args) != count:
                raise GameError('Unknown command or arguments for this application. Read help for its manual.')
            if app == 'monitor':
                if trace_remaining(slot) is not None and SOFTWARE[slot.running_apps[app]]['power'] < job['security']:
                    result = 'Trace encrypted: this monitor cannot decode the target security class.'
                elif slot.remote_host.get('_backdoor'):
                    result = 'Wraith link: remote logging suppressed. No active trace.'
                else:
                    remaining = trace_remaining(slot)
                    result = f'Trace remaining: {remaining} seconds.' if remaining is not None else 'No active remote trace.'
            else:
                if app == 'mapper' and not slot.mission_started:
                    from .operations import find_target
                    job = effective_target(slot, find_target(slot, args[0]))
                if not job:
                    raise GameError('No target. Scan a directory server or reserve an assignment.')
                if app != 'mapper' and not slot.mission_started:
                    raise GameError('No remote session.')
                if app == 'mapper' and args[0] != job['target']:
                    raise GameError('Host not present in your reserved network directory.')
                charged, tool = _tool_work(slot, app, {'mapper': 8, 'cracker': 22, 'decryptor': 18, 'cleaner': 14}[app])
                if not charged:
                    raise GameError(tool)
                if slot.mission_started and state.get('access'):
                    state['dirty'] = True
                if tool['power'] < job['security']:
                    raise GameError(f'Tool capability {tool["power"]} is insufficient for security class {job["security"]}. Operation failed.')
                if app == 'mapper':
                    server = ensure_server(slot, job)
                    observe(server)
                    event(server, 'scanned', f'Service fingerprint observed: port {job["port"]}, revision {server.revision}.')
                    server.save()
                    state['scanned_revision'] = server.revision
                    state['scanned'] = True
                    state['scanned_host'] = job['target']
                    if slot.mission_started and state.get('access'):
                        state['dirty'] = True
                    result = f'Host: {job["target"]}\n{job["port"]}/tcp  OPEN  auth-v{job["security"]} / patch r{job.get("server_revision", 1)}\nArchive: {job["file"] if job.get("file_present", True) else "missing"} / {job["size"]} MB / {"encrypted" if job["encrypted"] else "plaintext"}\nOther ports: filtered. Scan complete.'
                elif app == 'decryptor':
                    if not state.get('access') or args[0] != job['file'] or not job.get('file_present', True):
                        raise GameError('Archive unavailable or access denied.')
                    if not job['encrypted']:
                        raise GameError('This file is not encrypted.')
                    state.update(decrypted=True, dirty=True)
                    record_action(slot, job, 'file_decrypted', f'{job["file"]} decrypted on the remote filesystem.', decrypt=True)
                    result = f'{job["file"]}: decrypted. Checksum intact.'
                elif app == 'cleaner':
                    if not state.get('access'):
                        raise GameError('Permission denied: remote log partition locked.')
                    state['dirty'] = False
                    clear_remote_logs(slot, job)
                    result = 'Remote access logs erased.'
    except GameError as exc:
        result = str(exc)
        if slot.mission_started:
            slot.mission_state['work'] = slot.mission_state.get('work', 0) + 6
    if slot.remote_host.get('_backdoor'):
        slot.mission_state['dirty'] = False
    sync_remote_logs(slot)
    log(slot, app, result)
    settle(slot)


def _shell(slot, verb, args, job):
    arity = {'history': 0, 'jump': 1, 'rumors': 0, 'apps': 0, 'contracts': 0, 'accept': 1, 'route': 0, 'status': 0, 'brief': 0, 'abort': 0, 'connect': 1, 'submit': 0, 'disconnect': 0, 'ls': 0, 'get': 1, 'rm': 1}
    if verb not in arity or len(args) != arity[verb]:
        raise GameError('Unknown shell command or arguments. Read help for the shell manual.')
    state = slot.mission_state
    if verb == 'history':
        if not job:
            raise GameError('Connect to a server or reserve its contract to read its journal.')
        server = ensure_server(slot, job)
        return '\n'.join(f'{entry.created_at.isoformat()}  {entry.summary}' for entry in reversed(list(server.events.all()[:20]))) or 'No recorded history.'
    if verb == 'rumors':
        return 'Intercepted invitation: null-exchange.internal. Dial it from a local terminal; the public directory has no listing.'
    if verb in ('connect', 'jump'):
        from .operations import connect_target
        return connect_target(slot, args[0], backdoor=verb == 'jump')
    if verb == 'apps' and not args:
        return '\n'.join(f'{key}: {BUILTIN_APPS[value]["name"] if value in BUILTIN_APPS else SOFTWARE[value]["name"]}' for key, value in slot.running_apps.items()) + f'\nRAM: {ram_used(slot)} / {hardware(slot)["memory"]["ram"]} GB'
    if verb == 'contracts' and not args:
        mapping = codes()
        return '\n'.join(f'ID {mapping[c["id"]]}  [{RANKS[c["rank"]]}]  {c["title"]}  {c["reward"]} CPH  {"cooling down" if available_at(slot, c["id"]) and available_at(slot, c["id"]) > timezone.now() else "available"}' for c in all_contracts() if abs(c['rank'] - slot.rank) <= 1)
    if verb == 'accept' and len(args) == 1:
        return reserve(slot, args[0])
    if verb == 'route' and not args:
        return 'GATEWAY → ' + ' → '.join([get_server(key)['name'] + ' [' + get_server(key)['address'] + ']' for key in slot.proxy_route] + ['TARGET']) + f'\nConnection lease: {route_stats(slot)["fee"]} CPH'
    if verb == 'status' and not args:
        return f'Balance: {slot.balance} CPH\nRAM: {ram_used(slot)}/{hardware(slot)["memory"]["ram"]} GB\nRemote: {job["target"] if job and slot.mission_started else "disconnected"}\nLocal archive: {job["file"] if job and state.get("recovered") else "empty"}'
    if not job:
        raise GameError('No reserved contract.')
    if verb == 'brief' and not args:
        if not slot.active_contract:
            raise GameError('No reserved contract.')
        return f'{public_code(job["id"])} // {job["description"]}\nTarget: {job["target"]}. Reward: {job["reward"]} CPH.'
    if verb == 'abort' and not args:
        if not slot.active_contract:
            raise GameError('No reserved contract. Use disconnect to leave this server.')
        fail(slot, 'Assignment abandoned.')
        return 'Broker notified.'
    if verb == 'submit' and not args:
        if not slot.active_contract:
            raise GameError('No reserved contract to submit.')
        if slot.mission_started:
            raise GameError('Cannot deliver evidence while connected to the target.')
        fulfilled = state.get('recovered') if job['objective'] == 'retrieve' else state.get('deleted')
        if not fulfilled or not state.get('clean_exit'):
            raise GameError('Broker rejected delivery: objective or clean exit evidence missing.')
        transact(slot, job['reward'], f'Contract payment // {public_code(job["id"])}')
        slot.reputation += job['reputation']
        slot.completed += 1
        record_contract(slot, job, timezone.now() + timedelta(seconds=SUCCESS_COOLDOWN))
        slot.contract_cooldowns = {**slot.contract_cooldowns, job['id']: (timezone.now() + timedelta(seconds=SUCCESS_COOLDOWN)).isoformat()}
        slot.active_contract = ''
        slot.mission_state = {}
        return f'Delivery verified. +{job["reward"]} CPH / +{job["reputation"]} reputation.\nReplacement assignment available in 5 minutes.'
    if not slot.mission_started:
        raise GameError('No remote connection.')
    if verb == 'disconnect' and not args:
        if state.get('dirty'):
            fail(slot, 'Forensics recovered your access logs after disconnect.')
            return 'Remote link closed.'
        record_action(slot, job, 'disconnected', 'Remote session closed with no new access signature.')
        slot.mission_started = None
        from .passwords import cancel_break
        cancel_break(slot)
        state.update(clean_exit=True, access=False, trace_started=None)
        slot.remote_host = {}
        return 'Remote link closed. No access signature found.'
    if verb in ('ls', 'get', 'rm'):
        if not state.get('access'):
            raise GameError('Permission denied.')
        if verb == 'ls' and not args:
            state['dirty'] = True
            record_action(slot, job, 'directory_listed', 'Remote directory inspected.', snapshot=True)
            return 'Directory empty.' if not job.get('file_present', True) else f'{job["file"]}  {job["size"]} MB  {"encrypted" if job["encrypted"] and not state.get("decrypted") else "readable"}'
        if len(args) != 1 or args[0] != job['file'] or not job.get('file_present', True):
            raise GameError('File not found.')
        if verb == 'get':
            if job['encrypted'] and not state.get('decrypted'):
                raise GameError('Archive encrypted. Broker cannot accept ciphertext.')
            if job['size'] > hardware(slot)['storage']['capacity']:
                raise GameError('Local storage full. Transfer failed.')
            record_action(slot, job, 'file_retrieved', f'{job["file"]} copied to local storage.')
            state.update(recovered=True, local_size=job['size'], dirty=True)
            state['work'] = state.get('work', 0) + math.ceil(job['size'] / hardware(slot)['gateway']['bandwidth'] + state.get('latency', 0) / 10)
            return f'Copied {job["file"]} to local storage. {job["size"]} MB verified.'
        if verb == 'rm':
            record_action(slot, job, 'file_deleted', f'{job["file"]} removed from the remote filesystem.', delete=True)
            state.update(deleted=True, dirty=True)
            return f'{job["file"]} removed. Deletion receipt stored locally.'
    raise GameError('Unknown shell command or arguments. Read help for the shell manual.')
