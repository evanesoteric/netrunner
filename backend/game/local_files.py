"""The runner's virtual drive: downloads at / and owned tools in /exploits."""
import posixpath
from .filesystem import absolute

EXPLOIT_KB = 64


def exploit_storage(slot):
    return sum(item['quantity'] for item in slot.exploit_inventory.values()) * EXPLOIT_KB / 1024


def entries(slot):
    return [dict(path='/' + item['name'], type='file') for item in slot.local_files] + [dict(path='/exploits', type='directory')] + [dict(path='/exploits/' + key, type='file') for key in sorted(slot.exploit_inventory)]


def exploit_key(slot, name):
    if '/' not in name:
        return name
    path = absolute(name, slot.local_cwd)
    return path.removeprefix('/exploits/') if posixpath.dirname(path) == '/exploits' else ''


def download_name(slot, name):
    path = absolute(name, slot.local_cwd)
    return path[1:] if posixpath.dirname(path) == '/' else ''


def command(slot, verb, args):
    from .mechanics import GameError, storage_used, hardware
    valid = (verb in ('ls', 'cd') and len(args) <= 1) or (verb == 'pwd' and not args) or (verb == 'rm' and len(args) == 1)
    if not valid:
        raise GameError(f'Use {verb}' + (' [path].' if verb in ('ls', 'cd') else ' <file>.' if verb == 'rm' else '.'))
    if verb == 'pwd':
        return slot.local_cwd
    path = absolute(args[0], slot.local_cwd) if args else '/' if verb == 'cd' else slot.local_cwd
    if verb == 'cd':
        if path not in ('/', '/exploits'):
            raise GameError('Local directory not found. Use / or /exploits.')
        slot.local_cwd = path
        return path
    if verb == 'ls':
        if path not in ('/', '/exploits'):
            raise GameError('Local directory not found.')
        if path == '/':
            listing = ['exploits/  DIR'] + [f'{item["name"]}  {item["size"]} MB  {"encrypted" if item.get("encrypted") else "readable"}  {item["source"]}' for item in slot.local_files]
        else:
            listing = [f'{key}  {EXPLOIT_KB * item["quantity"]} KB  {"lifetime license" if item["mode"] == "license" else str(item["quantity"]) + " single-use copies"}  {item["fingerprint"]}' for key, item in sorted(slot.exploit_inventory.items())]
        return f'LOCAL FILESYSTEM\nDirectory: {path}\n' + ('\n'.join(listing) or 'No exploits installed. Buy tools in IRC Underground.') + f'\nStorage: {storage_used(slot):g} / {hardware(slot)["storage"]["capacity"]} MB'
    if path in ('/', '/exploits'):
        raise GameError('Directory removal is not supported.')
    if posixpath.dirname(path) == '/exploits':
        key = posixpath.basename(path)
        item = slot.exploit_inventory.get(key)
        if not item:
            raise GameError('Local exploit not found.')
        slot.exploit_inventory = {name: tool for name, tool in slot.exploit_inventory.items() if name != key}
        return f'{key} removed from /exploits. Reclaimed {EXPLOIT_KB * item["quantity"]} KB. No resale payment.'
    name = download_name(slot, path)
    item = next((item for item in slot.local_files if item['name'] == name), None)
    if not item:
        raise GameError('Local file not found.')
    slot.local_files = [entry for entry in slot.local_files if entry['id'] != item['id']]
    if slot.mission_state.get('local_file_id') == item['id']:
        slot.mission_state.update(recovered=False)
        for key in ('local_file_id', 'local_size', 'recovery_receipt'):
            slot.mission_state.pop(key, None)
    return f'{item["name"]} removed from local storage. Reclaimed {item["size"]} MB.'
