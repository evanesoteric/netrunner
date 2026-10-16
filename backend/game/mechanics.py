"""Server-authoritative game simulation. Commands never invoke a shell or network."""
import math
import shlex
from datetime import timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .catalog import (
    BUILTIN_APPS, CONTRACTS, CONTRACT_BY_ID, FAILURE_COOLDOWN, HARDWARE,
    PRODUCTS, RELAY_BY_ID, SOFTWARE, SUCCESS_COOLDOWN, HOME_NODE, RANKS,
)
from .models import LedgerEntry
from .contracts import codes, public_code


class GameError(Exception):
    pass


def hardware(slot):
    return {kind: HARDWARE[product_id] for kind, product_id in slot.equipment.items()}


def ram_used(slot):
    return sum(BUILTIN_APPS[key]['ram'] if key in BUILTIN_APPS else SOFTWARE[value]['ram'] for key, value in slot.running_apps.items())


def route_stats(slot, route=None):
    nodes = [RELAY_BY_ID[key] for key in (slot.proxy_route if route is None else route)]
    destination = CONTRACT_BY_ID.get(slot.active_contract)
    points = [HOME_NODE] + nodes + ([destination] if destination else [])
    transit = sum(math.hypot(a['x'] - b['x'], a['y'] - b['y']) for a, b in zip(points, points[1:]))
    return {'hops': len(nodes), 'fee': 8 + sum(n['fee'] for n in nodes), 'delay': sum(n['delay'] for n in nodes), 'latency': sum(n['latency'] for n in nodes) + math.ceil(transit / 30)}


def available_at(slot, contract_id):
    value = slot.contract_cooldowns.get(contract_id)
    return parse_datetime(value) if value else None


def trace_remaining(slot):
    if not slot.mission_started:
        return None
    elapsed = (timezone.now() - slot.mission_started).total_seconds()
    return max(0, math.ceil(slot.mission_state.get('trace_budget', 0) - slot.mission_state.get('work', 0) - elapsed))


def log(slot, app, message):
    slot.mission_log = (slot.mission_log + [{'app': app, 'text': message}])[-200:]


def transact(slot, amount, description):
    if slot.balance + amount < 0:
        raise GameError('Insufficient CPH.')
    slot.balance += amount
    LedgerEntry.objects.create(slot=slot, amount=amount, description=description)


def fail(slot, reason):
    job = CONTRACT_BY_ID.get(slot.active_contract)
    if not job:
        return
    fine = min(slot.balance, 90 + job['rank'] * 80)
    if fine:
        transact(slot, -fine, f'Contract failure // {public_code(job["id"])}')
    slot.reputation = max(0, slot.reputation - 60)
    slot.contract_cooldowns = {**slot.contract_cooldowns, job['id']: (timezone.now() + timedelta(seconds=FAILURE_COOLDOWN)).isoformat()}
    slot.active_contract = ''
    slot.mission_started = None
    slot.mission_state = {}
    log(slot, 'terminal', f'{reason}\nContract lost. Fine {fine} CPH. Reputation −60 (floor 0). Broker refresh: 10 minutes.')


def settle(slot):
    if slot.mission_started and trace_remaining(slot) == 0:
        fail(slot, 'TRACE COMPLETE. Your gateway was identified.')
        slot.save()


def validate_route(slot, route):
    if slot.mission_started:
        raise GameError('Disconnect before changing your route.')
    if not isinstance(route, list) or any(not isinstance(key, str) for key in route):
        raise GameError('Route must be a list of relay IDs.')
    if len(route) != len(set(route)) or any(key not in RELAY_BY_ID for key in route):
        raise GameError('Use distinct servers from Atlas.')
    if any(key not in slot.atlas_nodes for key in route):
        raise GameError('Add each server to your Atlas directory before routing through it.')
    if len(route) > hardware(slot)['gateway']['hops']:
        raise GameError('This gateway cannot support that many proxy hops.')
    if any(RELAY_BY_ID[key]['rank'] > slot.rank for key in route):
        raise GameError('A server on this route exceeds your clearance.')


def edit_directory(slot, action, server_id):
    if slot.mission_started:
        raise GameError('Disconnect before editing your Atlas directory.')
    if not isinstance(server_id, str) or server_id not in RELAY_BY_ID:
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
    return app


def trade(slot, action, product_id):
    if slot.mission_started:
        raise GameError('Disconnect before changing your loadout.')
    if not isinstance(product_id, str) or product_id not in PRODUCTS:
        raise GameError('Unknown product.')
    item = PRODUCTS[product_id]
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
    'terminal': 'LOCAL SHELL\nhelp — application manual\napps — running processes and RAM\ncontracts — broker listings\naccept <contract-id> — reserve by the numeric ID in contracts (0–255)\nbrief — read the accepted brief\nroute — inspect the committed proxy chain\nconnect <host> — dial a fictional target\nstatus — gateway status\nls — remote file listing\nget <file> — copy a readable file to local storage\nrm <file> — remove a remote file\ndisconnect — end the remote session\nsubmit — deliver evidence to the broker\nabort — abandon the contract (fine and reputation loss)\nclear — clear local console output',
    'mapper': 'CARTOGRAPH\nscan <host> — inspect a fictional host and its services\nCosts 1 + tool tier CPH. Scan quality depends on tool capability.',
    'cracker': 'LOCKPICK\ncrack <port> — attack a discovered authentication service\nRequires an active remote connection. Underpowered tools can fail.',
    'decryptor': 'ROSETTA\ndecrypt <file> — decode an encrypted remote archive\nRequires file access and a sufficient decryption engine.',
    'cleaner': 'ASHFALL\nerase — remove remote access logs\nLater remote operations can leave new log entries.',
    'monitor': 'TRIPWIRE\ntrace — inspect the active trace\nThe monitor must remain running to show a live countdown.',
    'bank': 'CIPHER BANK\nbalance — account balance\nhistory — latest 15 ledger entries',
}


def reserve(slot, contract_id):
    if slot.active_contract:
        raise GameError('An assignment is already reserved.')
    mapping = codes()
    key = next((key for key, code in mapping.items() if str(code) == contract_id), None)
    job = CONTRACT_BY_ID.get(key)
    if not job:
        raise GameError(f'Unknown contract ID {contract_id!r}. Run contracts and use its numeric ID (0–255).')
    if abs(job['rank'] - slot.rank) > 1:
        lower, upper = max(0, slot.rank - 1), min(len(RANKS) - 1, slot.rank + 1)
        raise GameError(f'Contract {contract_id} is outside your rank clearance: its rank is {RANKS[job["rank"]]}; your {RANKS[slot.rank]} clearance covers {RANKS[lower]} through {RANKS[upper]}.')
    ready = available_at(slot, key)
    if ready and ready > timezone.now():
        raise GameError('The broker is still sourcing a replacement assignment. Check its availability time.')
    slot.active_contract = key
    slot.mission_state = {}
    slot.mission_started = None
    return f'Reservation confirmed: {public_code(job["id"])}.\n{job["description"]}\nTarget: {job["target"]}. Payment: {job["reward"]} CPH.'


def _tool_work(slot, app, base):
    tool = SOFTWARE[slot.running_apps[app]]
    cost = tool['tier'] + 1
    if slot.balance < cost:
        return False, 'Insufficient CPH for tool compute time. No operation was performed.'
    transact(slot, -cost, f'Compute // {tool["name"]}')
    if slot.mission_started:
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
    job = CONTRACT_BY_ID.get(slot.active_contract)
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
        else:
            usages = {'mapper': ('scan', 1), 'cracker': ('crack', 1), 'decryptor': ('decrypt', 1), 'cleaner': ('erase', 0), 'monitor': ('trace', 0)}
            expected, count = usages[app]
            if verb != expected or len(args) != count:
                raise GameError('Unknown command or arguments for this application. Read help for its manual.')
            if app == 'monitor':
                if slot.mission_started and SOFTWARE[slot.running_apps[app]]['power'] < job['security']:
                    result = 'Trace encrypted: this monitor cannot decode the target security class.'
                else:
                    result = f'Trace remaining: {trace_remaining(slot)} seconds.' if slot.mission_started else 'No active remote trace.'
            else:
                if not job:
                    raise GameError('No reserved target.')
                if app != 'mapper' and not slot.mission_started:
                    raise GameError('No remote session.')
                if app == 'mapper' and args[0] != job['target']:
                    raise GameError('Host not present in your reserved network directory.')
                charged, tool = _tool_work(slot, app, {'mapper': 8, 'cracker': 22, 'decryptor': 18, 'cleaner': 14}[app])
                if not charged:
                    raise GameError(tool)
                if slot.mission_started:
                    state['dirty'] = True
                if tool['power'] < job['security']:
                    raise GameError(f'Tool capability {tool["power"]} is insufficient for security class {job["security"]}. Operation failed.')
                if app == 'mapper':
                    state['scanned'] = True
                    if slot.mission_started:
                        state['dirty'] = True
                    result = f'Host: {job["target"]}\n{job["port"]}/tcp  OPEN  auth-v{job["security"]}\nArchive: {job["file"]} / {job["size"]} MB / {"encrypted" if job["encrypted"] else "plaintext"}\nOther ports: filtered. Scan complete.'
                elif app == 'cracker':
                    if not state.get('scanned'):
                        raise GameError('No service fingerprint available.')
                    if args[0] != str(job['port']):
                        raise GameError('Connection refused on this port.')
                    state.update(access=True, dirty=True)
                    result = 'Authentication compromised. Remote filesystem mounted.'
                elif app == 'decryptor':
                    if not state.get('access') or args[0] != job['file'] or state.get('deleted'):
                        raise GameError('Archive unavailable or access denied.')
                    if not job['encrypted']:
                        raise GameError('This file is not encrypted.')
                    state.update(decrypted=True, dirty=True)
                    result = f'{job["file"]}: decrypted. Checksum intact.'
                elif app == 'cleaner':
                    if not state.get('access'):
                        raise GameError('Permission denied: remote log partition locked.')
                    state['dirty'] = False
                    result = 'Remote access logs erased.'
    except GameError as exc:
        result = str(exc)
        if slot.mission_started:
            slot.mission_state['work'] = slot.mission_state.get('work', 0) + 6
    log(slot, app, result)
    settle(slot)


def _shell(slot, verb, args, job):
    arity = {'apps': 0, 'contracts': 0, 'accept': 1, 'route': 0, 'status': 0, 'brief': 0, 'abort': 0, 'connect': 1, 'submit': 0, 'disconnect': 0, 'ls': 0, 'get': 1, 'rm': 1}
    if verb not in arity or len(args) != arity[verb]:
        raise GameError('Unknown shell command or arguments. Read help for the shell manual.')
    state = slot.mission_state
    if verb == 'apps' and not args:
        return '\n'.join(f'{key}: {BUILTIN_APPS[value]["name"] if value in BUILTIN_APPS else SOFTWARE[value]["name"]}' for key, value in slot.running_apps.items()) + f'\nRAM: {ram_used(slot)} / {hardware(slot)["memory"]["ram"]} GB'
    if verb == 'contracts' and not args:
        mapping = codes()
        return '\n'.join(f'ID {mapping[c["id"]]}  [{RANKS[c["rank"]]}]  {c["title"]}  {c["reward"]} CPH  {"cooling down" if available_at(slot, c["id"]) and available_at(slot, c["id"]) > timezone.now() else "available"}' for c in CONTRACTS if abs(c['rank'] - slot.rank) <= 1)
    if verb == 'accept' and len(args) == 1:
        return reserve(slot, args[0])
    if verb == 'route' and not args:
        return 'GATEWAY → ' + ' → '.join([RELAY_BY_ID[key]['name'] + ' [' + RELAY_BY_ID[key]['address'] + ']' for key in slot.proxy_route] + ['TARGET']) + f'\nConnection lease: {route_stats(slot)["fee"]} CPH'
    if verb == 'status' and not args:
        return f'Balance: {slot.balance} CPH\nRAM: {ram_used(slot)}/{hardware(slot)["memory"]["ram"]} GB\nRemote: {job["target"] if job and slot.mission_started else "disconnected"}\nLocal archive: {job["file"] if job and state.get("recovered") else "empty"}'
    if not job:
        raise GameError('No reserved contract.')
    if verb == 'brief' and not args:
        return f'{public_code(job["id"])} // {job["description"]}\nTarget: {job["target"]}. Reward: {job["reward"]} CPH.'
    if verb == 'abort' and not args:
        fail(slot, 'Assignment abandoned.')
        return 'Broker notified.'
    if verb == 'connect' and len(args) == 1:
        if slot.mission_started:
            raise GameError('A remote session is already open.')
        if args[0] != job['target']:
            raise GameError('Host not present in your reserved network directory.')
        # A rank loss can invalidate previously accessible relays.
        validate_route(slot, slot.proxy_route)
        stats = route_stats(slot)
        transact(slot, -stats['fee'], f'Route lease // {job["target"]}')
        slot.mission_started = timezone.now()
        state.update(trace_budget=100 - job['security'] * 10 + stats['delay'] + hardware(slot)['gateway']['stealth'] * 8, work=0, latency=stats['latency'], access=False, dirty=False, clean_exit=False)
        return f'Dialing {job["target"]} via {stats["hops"]} proxies.\nLease paid: {stats["fee"]} CPH. Remote session established.'
    if verb == 'submit' and not args:
        if slot.mission_started:
            raise GameError('Cannot deliver evidence while connected to the target.')
        fulfilled = state.get('recovered') if job['objective'] == 'retrieve' else state.get('deleted')
        if not fulfilled or not state.get('clean_exit'):
            raise GameError('Broker rejected delivery: objective or clean exit evidence missing.')
        transact(slot, job['reward'], f'Contract payment // {public_code(job["id"])}')
        slot.reputation += job['reputation']
        slot.completed += 1
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
        slot.mission_started = None
        state.update(clean_exit=True, access=False)
        return 'Remote link closed. No access signature found.'
    if verb in ('ls', 'get', 'rm'):
        if not state.get('access'):
            raise GameError('Permission denied.')
        if verb == 'ls' and not args:
            state['dirty'] = True
            return 'Directory empty.' if state.get('deleted') else f'{job["file"]}  {job["size"]} MB  {"encrypted" if job["encrypted"] and not state.get("decrypted") else "readable"}'
        if len(args) != 1 or args[0] != job['file'] or state.get('deleted'):
            raise GameError('File not found.')
        if verb == 'get':
            if job['encrypted'] and not state.get('decrypted'):
                raise GameError('Archive encrypted. Broker cannot accept ciphertext.')
            if job['size'] > hardware(slot)['storage']['capacity']:
                raise GameError('Local storage full. Transfer failed.')
            state.update(recovered=True, local_size=job['size'], dirty=True)
            state['work'] = state.get('work', 0) + math.ceil(job['size'] / hardware(slot)['gateway']['bandwidth'] + state.get('latency', 0) / 10)
            return f'Copied {job["file"]} to local storage. {job["size"]} MB verified.'
        if verb == 'rm':
            state.update(deleted=True, dirty=True)
            return f'{job["file"]} removed. Deletion receipt stored locally.'
    raise GameError('Unknown shell command or arguments. Read help for the shell manual.')
