"""Server-authoritative game simulation. Commands never invoke a shell or network."""
import math
import shlex
from uuid import uuid4
from pathlib import PurePosixPath
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


def storage_used(slot):
    return sum(entry['size'] for entry in slot.local_files)


def local_filesystem(slot, verb, args):
    if verb == 'ls':
        listing = '\n'.join(f'{entry["name"]}  {entry["size"]} MB  {"encrypted" if entry.get("encrypted") else "readable"}  {entry["source"]}' for entry in slot.local_files) or 'Local directory empty.'
        return f'LOCAL FILESYSTEM\n{listing}\nStorage: {storage_used(slot)} / {hardware(slot)["storage"]["capacity"]} MB'
    entry = next((entry for entry in slot.local_files if entry['name'] == args[0]), None)
    if not entry:
        raise GameError('Local file not found.')
    slot.local_files = [item for item in slot.local_files if item['id'] != entry['id']]
    if slot.mission_state.get('local_file_id') == entry['id']:
        slot.mission_state.update(recovered=False)
        slot.mission_state.pop('local_file_id', None)
        slot.mission_state.pop('local_size', None)
    return f'{entry["name"]} removed from local storage. Reclaimed {entry["size"]} MB.'


def copy_to_local(slot, job):
    previous = next((entry for entry in slot.local_files if entry['source'] == job['target'] and entry['source_path'] == job['file'] and entry.get('revision', 1) == job.get('server_revision', 1)), None)
    occupied = storage_used(slot) - (previous['size'] if previous else 0)
    if occupied + job['size'] > hardware(slot)['storage']['capacity']:
        raise GameError('Local storage full. Remove local files while disconnected or fit a larger drive.')
    if previous:
        name, file_id = previous['name'], previous['id']
    else:
        original = PurePosixPath(job['file']).name
        name, index = original, 2
        names = {entry['name'] for entry in slot.local_files}
        while name in names:
            path = PurePosixPath(original)
            name = f'{path.stem}_{index}{path.suffix}'
            index += 1
        file_id = uuid4().hex
    entry = dict(id=file_id, name=name, size=job['size'], source=job['target'], source_path=job['file'], revision=job.get('server_revision', 1), encrypted=bool(job['encrypted'] and not slot.mission_state.get('decrypted')), security=job['security'], downloaded_at=timezone.now().isoformat())
    slot.local_files = [item for item in slot.local_files if item['id'] != file_id] + [entry]
    return entry


def hardware(slot):
    return {kind: HARDWARE[product_id] for kind, product_id in slot.equipment.items()}


def ram_used(slot):
    processes = sum(BUILTIN_APPS[key]['ram'] for key in slot.running_apps if key in BUILTIN_APPS)
    attempt = slot.mission_state.get('password_break')
    return processes + (SOFTWARE[attempt['product_id']]['ram'] if attempt else 0)


def choose_tool(slot, kind, product_id=None, require_ram=True):
    names = {'mapper':'Cartograph', 'cracker':'Lockpick', 'decryptor':'Rosetta', 'cleaner':'Logcleaner', 'monitor':'Tripwire', 'rootkit':'Wraith', 'ransomware':'Eclipse'}
    choices = [SOFTWARE[key] for key in slot.installed_software if key in SOFTWARE and SOFTWARE[key]['kind'] == kind]
    selected = product_id or slot.applet_preferences.get(kind)
    if selected:
        choices = [item for item in choices if item['id'] == selected]
    if not choices:
        raise GameError(f'An owned {names[kind]} license is required.')
    if require_ram:
        choices = [item for item in choices if item['ram'] <= hardware(slot)['memory']['ram'] - ram_used(slot)]
        if not choices:
            raise GameError(f'Not enough free RAM for {names[kind]}. Cancel an active decoder or select a Micro license.')
    return max(choices, key=lambda item: (item['power'], item['speed']))


def select_applet(slot, product_id):
    if product_id not in slot.installed_software or product_id not in SOFTWARE:
        raise GameError('Select an owned software license.')
    kind = SOFTWARE[product_id]['kind']
    if kind == 'cracker' and slot.mission_state.get('password_break') and slot.mission_state['password_break']['product_id'] != product_id:
        from .passwords import cancel_break
        cancel_break(slot)
    if kind == 'cracker':
        slot.mission_state['password_tool'] = product_id
    slot.applet_preferences = {**slot.applet_preferences, kind: product_id}


def monitor_tool(slot):
    try:
        return choose_tool(slot, 'monitor', require_ram=False)
    except GameError:
        return None


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
        transact(slot, -fine, f'Contract failure // {public_code(slot.active_contract, slot)}' if slot.active_contract else f'Intrusion failure // {job["target"]}')
    slot.reputation = max(0, slot.reputation - 60)
    if slot.active_contract:
        slot.contract_cooldowns = {**slot.contract_cooldowns, slot.active_contract: (timezone.now() + timedelta(seconds=FAILURE_COOLDOWN)).isoformat()}
    from .broker import delay_replacement
    delay_replacement(slot, slot.active_contract)
    slot.active_contract = ''
    slot.remote_host = {}
    slot.mission_started = None
    slot.mission_state = {}
    outcome = 'Contract lost.' if contract_failure else 'Remote link lost.'
    refresh = ' Broker sourcing updated; this assignment will not return.' if contract_failure else ''
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
    from .broker import settle_broker
    settle_broker(slot)


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
    if product_id in {'bank','broker','market'}:
        raise GameError('Open this online service from its sidebar page.')
    if product_id not in BUILTIN_APPS:
        raise GameError('Software is a terminal applet. Select its license and use the primary terminal.')
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
        if product_id in SOFTWARE:
            kind = item['kind']
            if slot.applet_preferences.get(kind) == product_id:
                slot.applet_preferences = {key:value for key,value in slot.applet_preferences.items() if key != kind}
            if slot.mission_state.get('password_tool') == product_id:
                slot.mission_state.pop('password_tool', None)
        transact(slot, item['price'] // 2, f'Resale // {item["name"]}')
    elif action == 'equip':
        if product_id not in HARDWARE or product_id not in owned:
            raise GameError('Only owned hardware can be fitted.')
        category = item['category']
        if category == 'memory' and ram_used(slot) > item['ram']:
            raise GameError('Close applications before fitting this smaller memory module.')
        if category == 'gateway' and len(slot.proxy_route) > item['hops']:
            raise GameError('Shorten your proxy route before fitting this gateway.')
        if category == 'storage' and storage_used(slot) > item['capacity']:
            raise GameError('This drive cannot hold your local files. Remove files or choose a larger drive.')
        slot.equipment = {**slot.equipment, category: product_id}
    else:
        raise GameError('Choose buy, sell, or equip.')


MANUALS = {
    'exploit': 'FINGERPRINT EXPLOITS\nBuy licenses or single-use copies in IRC Underground with CPH.\nexploits — list owned fingerprint tools\nexploit <id> — use on the connected, freshly scanned server\nMatch protocol, auth version and patch revision exactly. Uses 2 GB transient RAM.\nA lifetime license is reusable for that fingerprint; single-use copies burn on successful entry only.\nSuccess opens an admin shell immediately, starts a trace and leaves access logs. Clean logs before disconnecting.',
    'terminal': 'LOCAL SHELL\nexploits — list owned fingerprint exploits\nexploit <id> — instant shell using a matching exploit from IRC Underground\napplets — list owned terminal software\nuse <license-id> — select an applet version\ntrace — licensed Tripwire telemetry\ninstall — install owned Wraith rootkit\ndeploy <host> — deploy owned Eclipse ransomware\nhelp — application manual\nrumors — intercepted hidden-service invitation\njump <host> — use an installed Wraith backdoor\napps — running processes and RAM\ncontracts — broker listings\naccept <contract-id> — reserve by the numeric ID in contracts (0–255)\nbrief — read the accepted brief\nroute — inspect the committed proxy chain\nconnect <host> — dial a fictional target\nscan <host> — scan with owned Cartograph software\nlogcleaner [license-id] — erase remote logs with an owned Logcleaner license\nlockpick — open the server login dialog\nstatus — gateway status\nhistory — recent operator journal for this target\ndecrypt <local-file> — decrypt a local archive with owned Rosetta software while disconnected\nls — list local files when disconnected; remote files when logged in\nget <file> — copy a readable file to local storage\nrm <file> — remove a local file when disconnected; a remote file when logged in\ndisconnect — end the remote session\nsubmit — deliver evidence to the broker\nabort — abandon the contract (fine and reputation loss)\nclear — clear local console output',
    'mapper': 'CARTOGRAPH\nscan <host> — inspect a fictional host and its services\nCosts 1 + tool tier CPH. Scan quality depends on tool capability.',
    'cracker': 'LOCKPICK\nUse login in the primary terminal to open the password decoder. Connect to a server login and scan its authentication service first.',
    'decryptor': 'ROSETTA\ndecrypt <file> — decode an encrypted remote archive\nRequires file access and a sufficient decryption engine.',
    'cleaner': 'LOGCLEANER\nRun logcleaner from the local terminal with an owned license.',
    'monitor': 'TRIPWIRE\ntrace — inspect the active trace\nAn owned capable license decodes the embedded trace countdown; no separate process is needed.',
    'rootkit': 'WRAITH // EPIC\ninstall — persist a backdoor on the currently mounted server. Clean initial logs before leaving.\nFuture jump <host> connections bypass proxies and logs.',
    'ransomware': 'ECLIPSE // EPIC\ndeploy <host> — install on the currently mounted amber non-contract server. Maximum 3 instances; payout after 120 seconds; each instance then removes itself.',
    'bank': 'CIPHER BANK\nbalance — account balance\nhistory — latest 15 ledger entries',
}


def reserve(slot, contract_id):
    if slot.active_contract or slot.mission_started:
        raise GameError('An assignment or remote session is already open.')
    from .broker import offered_jobs
    mapping = codes(slot)
    eligible = offered_jobs(slot)
    key = next((job['id'] for job in eligible if str(mapping[job['id']]) == contract_id), None)
    if key is None:
        key = next((key for key, code in mapping.items() if str(code) == contract_id and key not in slot.broker_consumed), None)
    job = get_contract(key, slot)
    if not job:
        raise GameError(f'Unknown contract ID {contract_id!r}. Run contracts and use its numeric ID (0–255).')
    if abs(job['rank'] - slot.rank) > 1:
        lower, upper = max(0, slot.rank - 1), min(len(RANKS) - 1, slot.rank + 1)
        raise GameError(f'Contract {contract_id} is outside your rank clearance: its rank is {RANKS[job["rank"]]}; your {RANKS[slot.rank]} clearance covers {RANKS[lower]} through {RANKS[upper]}.')
    ready = available_at(slot, key)
    if ready and ready > timezone.now():
        raise GameError('The broker is still sourcing a replacement assignment. Check its availability time.')
    from .broker import consume
    consume(slot, job)
    slot.active_contract = key
    slot.remote_host = {}
    slot.mission_state = {}
    slot.mission_started = None
    return f'Reservation confirmed: {public_code(job["id"], slot)}.\n{job["description"]}\nTarget: {job["target"]}. Payment: {job["reward"]} CPH.'


def _tool_work(slot, app, base, tool=None):
    tool = tool or choose_tool(slot, app)
    cost = tool['tier'] + 1
    if slot.balance < cost:
        return False, 'Insufficient CPH for tool compute time. No operation was performed.'
    transact(slot, -cost, f'Compute // {tool["name"]}')
    if slot.mission_started and slot.mission_state.get('access'):
        slot.mission_state['work'] = slot.mission_state.get('work', 0) + math.ceil(base / (hardware(slot)['cpu']['speed'] * tool['speed']) * 2 + slot.mission_state.get('latency', 0) / 12)
    return True, tool


def execute(slot, app, raw):
    if (app not in slot.running_apps and app != 'bank') or app not in MANUALS:
        raise GameError('Launch this application before using its console.')
    try:
        parts = shlex.split(raw)
    except ValueError:
        log(slot, app, f'> {raw}\nUnclosed quote.')
        return
    if not parts:
        return
    verb, args = parts[0].lower(), parts[1:]
    remote = session_target(slot) if app == 'terminal' and slot.mission_started and slot.mission_state.get('access') else None
    prompt = f'admin@{remote["target"]}' if remote else f'{slot.alias}@{app}'
    log(slot, app, f'{prompt}:~$ {raw}')
    if verb == 'clear' and app == 'terminal':
        slot.mission_log = [entry for entry in slot.mission_log if entry.get('app') != app]
        return
    if verb == 'help' and not args:
        log(slot, app, MANUALS[app])
        return
    if verb == 'help' and len(args) == 1 and app == 'terminal':
        key = {'scan':'mapper','login':'cracker','decrypt':'decryptor','logcleaner':'cleaner','trace':'monitor','install':'rootkit','deploy':'ransomware'}.get(args[0], args[0])
        log(slot, app, MANUALS.get(key, 'Unknown applet. Use help for the command list.'))
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
        else:
            raise GameError('Use the primary terminal for software applets.')
    except GameError as exc:
        result = str(exc)
        if slot.mission_started:
            slot.mission_state['work'] = slot.mission_state.get('work', 0) + 6
    if slot.remote_host.get('_backdoor'):
        slot.mission_state['dirty'] = False
    sync_remote_logs(slot)
    log(slot, app, result)
    settle(slot)


def require_login(slot):
    if not slot.mission_started or not slot.mission_state.get('access'):
        raise GameError('You are not logged in. Connect to a server and log in first.')


def scan_target(slot, address):
    from .operations import find_target
    target = current_target(slot) if slot.mission_started else effective_target(slot, find_target(slot, address))
    if not target or address != target['target']:
        raise GameError('Host not present in your reserved network directory.')
    charged, tool = _tool_work(slot, 'mapper', 8)
    if not charged:
        raise GameError(tool)
    state = slot.mission_state
    if slot.mission_started and state.get('access'):
        state['dirty'] = True
    if tool['power'] < target['security']:
        raise GameError(f'Tool capability {tool["power"]} is insufficient for security class {target["security"]}. Operation failed.')
    server = ensure_server(slot, target)
    observe(server)
    from .exploits import fingerprint, fingerprint_text
    service = fingerprint_text(fingerprint(target))
    event(server, 'scanned', f'Service fingerprint observed: port {target["port"]}, revision {server.revision}.')
    server.save()
    state.update(scanned_revision=server.revision, scanned=True, scanned_host=target['target'])
    return f'Host: {target["target"]}\n{target["port"]}/tcp  OPEN  auth-v{target["security"]} / patch r{target.get("server_revision", 1)}\nArchive: {target["file"] if target.get("file_present", True) else "missing"} / {target["size"]} MB / {"encrypted" if target["encrypted"] else "plaintext"}\nFingerprint: {service}\nOther ports: filtered. Scan complete.'


def clean_logs(slot, license_id=None):
    require_login(slot)
    tool = choose_tool(slot, 'cleaner', license_id)
    charged, result = _tool_work(slot, 'cleaner', 14, tool)
    if not charged:
        raise GameError(result)
    job = current_target(slot)
    if tool['power'] < job['security']:
        raise GameError(f'Logcleaner capability {tool["power"]} is insufficient for security class {job["security"]}.')
    slot.mission_state['dirty'] = False
    clear_remote_logs(slot, job)
    return f'{tool["name"]}: Remote access logs erased.'


def decrypt_local(slot, name):
    if slot.mission_started:
        require_login(slot)
        target = current_target(slot)
        if name != target['file'] or not target.get('file_present', True):
            raise GameError('Archive unavailable or access denied.')
        if not target['encrypted']:
            raise GameError('This file is not encrypted.')
        charged, tool = _tool_work(slot, 'decryptor', 18)
        if not charged:
            raise GameError(tool)
        if tool['power'] < target['security']:
            raise GameError('Rosetta capability is insufficient for this archive.')
        slot.mission_state.update(decrypted=True, dirty=True)
        record_action(slot, target, 'file_decrypted', f'{name} decrypted on the remote filesystem.', decrypt=True)
        return f'{name}: decrypted. Checksum intact.'
    entry = next((entry for entry in slot.local_files if entry['name'] == name), None)
    if not entry:
        raise GameError('Local file not found.')
    if not entry.get('encrypted'):
        raise GameError('This local file is not encrypted.')
    charged, tool = _tool_work(slot, 'decryptor', 18)
    if not charged:
        raise GameError(tool)
    if tool['power'] < entry.get('security', 1):
        raise GameError('Rosetta capability is insufficient for this encrypted local file.')
    entry['encrypted'] = False
    entry['decrypted_at'] = timezone.now().isoformat()
    return f'{name}: decrypted locally. Checksum intact. Local copy is ready for delivery.'


def _shell(slot, verb, args, job):
    if verb == 'exploits' and not args:
        from .exploits import inventory
        return '\n'.join(f'{item["id"]}: {item["fingerprint"]} / {"lifetime" if item["mode"] == "license" else str(item["quantity"]) + " copies"}' for item in inventory(slot)) or 'No exploits owned. Visit IRC Underground.'
    if verb == 'exploit':
        if len(args) != 1:
            raise GameError('Use exploit <id>. List owned tools with exploits.')
        from .exploits import run_exploit
        return run_exploit(slot, args[0])
    arity = {'history': 0, 'jump': 1, 'rumors': 0, 'apps': 0, 'contracts': 0, 'accept': 1, 'route': 0, 'status': 0, 'brief': 0, 'abort': 0, 'connect': 1, 'submit': 0, 'disconnect': 0, 'ls': 0, 'get': 1, 'rm': 1}
    if verb == 'use':
        if len(args) != 1:
            raise GameError('Use use <license-id>.')
        select_applet(slot, args[0])
        return f'{SOFTWARE[args[0]]["name"]} selected for the primary terminal.'
    if verb == 'applets':
        return '\n'.join(f'{item["id"]}: {item["name"]}' for item in SOFTWARE.values() if item['id'] in slot.installed_software)
    if verb == 'crack':
        if len(args) != 1:
            raise GameError('Use login to open the password decoder.')
        from .passwords import start_break
        start_break(slot, args[0])
        return 'Password breaker started. Use login to view its progress.'
    if verb == 'trace':
        tool = choose_tool(slot, 'monitor', require_ram=False)
        target = current_target(slot)
        if slot.remote_host.get('_backdoor'):
            return 'Wraith link: remote logging suppressed. No active trace.'
        if trace_remaining(slot) is None:
            return 'No active remote trace.'
        if tool['power'] < target['security']:
            return 'Trace encrypted: this monitor cannot decode the target security class.'
        return f'Trace remaining: {trace_remaining(slot)} seconds.'
    if verb == 'install' and not args:
        choose_tool(slot, 'rootkit')
        from .operations import install_rootkit
        return install_rootkit(slot)
    if verb == 'deploy' and len(args) == 1:
        choose_tool(slot, 'ransomware')
        from .operations import deploy_ransomware
        return deploy_ransomware(slot, args[0])
    if verb == 'decrypt':
        if len(args) != 1:
            raise GameError('Use decrypt <local-file>.')
        return decrypt_local(slot, args[0])
    if verb == 'scan':
        if len(args) != 1:
            raise GameError('Use scan <host>.')
        return scan_target(slot, args[0])
    if verb == 'logcleaner':
        if len(args) > 1:
            raise GameError('Use logcleaner [license-id].')
        return clean_logs(slot, args[0] if args else None)
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
        from .broker import offered_jobs
        mapping = codes(slot)
        return '\n'.join(f'ID {mapping[c["id"]]}  [{RANKS[c["rank"]]}]  {c["title"]}  {c["reward"]} CPH' for c in offered_jobs(slot)) or 'No contracts available. The broker is sourcing new assignments.'
    if verb == 'accept' and len(args) == 1:
        return reserve(slot, args[0])
    if verb == 'route' and not args:
        return 'GATEWAY → ' + ' → '.join([get_server(key)['name'] + ' [' + get_server(key)['address'] + ']' for key in slot.proxy_route] + ['TARGET']) + f'\nConnection lease: {route_stats(slot)["fee"]} CPH'
    if verb == 'status' and not args:
        return f'Balance: {slot.balance} CPH\nRAM: {ram_used(slot)}/{hardware(slot)["memory"]["ram"]} GB\nRemote: {job["target"] if job and slot.mission_started else "disconnected"}\nLocal archive: {len(slot.local_files)} files / {storage_used(slot)} MB'
    if verb in ('ls', 'rm') and not slot.mission_started:
        return local_filesystem(slot, verb, args)
    if verb in ('ls', 'get', 'rm'):
        require_login(slot)
    if not job:
        raise GameError('No reserved contract.')
    if verb == 'brief' and not args:
        if not slot.active_contract:
            raise GameError('No reserved contract.')
        return f'{public_code(job["id"], slot)} // {job["description"]}\nTarget: {job["target"]}. Reward: {job["reward"]} CPH.'
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
        local_copy = next((entry for entry in slot.local_files if entry['id'] == state.get('local_file_id')), None)
        if job['objective'] == 'retrieve' and local_copy and local_copy.get('encrypted'):
            raise GameError('Broker rejected delivery: archive is encrypted. Decrypt the local copy with Rosetta first.')
        fulfilled = (state.get('recovered') and local_copy) if job['objective'] == 'retrieve' else state.get('deleted')
        if not fulfilled or not state.get('clean_exit'):
            raise GameError('Broker rejected delivery: objective or clean exit evidence missing.')
        transact(slot, job['reward'], f'Contract payment // {public_code(job["id"], slot)}')
        slot.reputation += job['reputation']
        slot.completed += 1
        record_contract(slot, job, timezone.now() + timedelta(seconds=SUCCESS_COOLDOWN))
        slot.contract_cooldowns = {**slot.contract_cooldowns, job['id']: (timezone.now() + timedelta(seconds=SUCCESS_COOLDOWN)).isoformat()}
        slot.active_contract = ''
        slot.mission_state = {}
        return f'Delivery verified. +{job["reward"]} CPH / +{job["reputation"]} reputation.\nThe broker will publish a new assignment after its sourcing delay.'
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
        state.pop('password_ready', None)
        state.pop('password_result', None)
        state.update(clean_exit=True, access=False, trace_started=None)
        slot.remote_host = {}
        return 'Remote link closed. No access signature found.'
    if verb in ('ls', 'get', 'rm'):
        if verb == 'ls' and not args:
            state['dirty'] = True
            record_action(slot, job, 'directory_listed', 'Remote directory inspected.', snapshot=True)
            return 'Directory empty.' if not job.get('file_present', True) else f'{job["file"]}  {job["size"]} MB  {"encrypted" if job["encrypted"] and not state.get("decrypted") else "readable"}'
        if len(args) != 1 or args[0] != job['file'] or not job.get('file_present', True):
            raise GameError('File not found.')
        if verb == 'get':
            local = copy_to_local(slot, job)
            record_action(slot, job, 'file_retrieved', f'{job["file"]} copied to local storage.')
            state.update(recovered=True, local_file_id=local['id'], dirty=True)
            state['work'] = state.get('work', 0) + math.ceil(job['size'] / hardware(slot)['gateway']['bandwidth'] + state.get('latency', 0) / 10)
            return f'Copied {job["file"]} to local storage. {job["size"]} MB verified.\nLocal file: {local["name"]} ({"encrypted" if local['encrypted'] else "readable"}) / drive usage {storage_used(slot)} MB.'
        if verb == 'rm':
            record_action(slot, job, 'file_deleted', f'{job["file"]} removed from the remote filesystem.', delete=True)
            state.update(deleted=True, dirty=True)
            return f'{job["file"]} removed. Deletion receipt stored locally.'
    raise GameError('Unknown shell command or arguments. Read help for the shell manual.')
