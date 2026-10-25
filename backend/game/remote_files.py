"""Primary-terminal commands over the saved virtual filesystem."""
import math
import fnmatch
import posixpath
from .filesystem import absolute, directory_exists, listing, resolve_file, FilesystemError
from .deletion import required_paths
from .persistence import ensure_server, observe, record_action


def command(slot, verb, args, target):
    from .mechanics import require_login, copy_to_local, hardware, storage_used
    require_login(slot)
    server = ensure_server(slot, target)
    state = slot.mission_state
    cwd = state.get('cwd', '/')
    if not directory_exists(server.files, cwd):
        cwd = state['cwd'] = '/'
    if verb == 'pwd':
        return cwd
    if verb == 'cd':
        destination = absolute(args[0] if args else '/', cwd)
        if not directory_exists(server.files, destination):
            raise FilesystemError('Directory not found.')
        state.update(cwd=destination, dirty=True, work=state.get('work', 0) + 1)
        record_action(slot, target, 'directory_changed', f'Working directory changed to {destination}.')
        return destination
    if verb == 'ls':
        directory = absolute(args[0], cwd) if args else cwd
        entries = listing(server.files, directory)
        remember(state, entries, directory=directory)
        state.update(dirty=True, work=state.get('work', 0) + 2)
        record_action(slot, target, 'directory_listed', f'Directory inspected: {directory}.', snapshot=True, directory=directory)
        rows = [f'{posixpath.basename(entry["name"])}{ "/" if entry.get("type") == "directory" else ""}  {"DIR" if entry.get("type") == "directory" else str(entry["size"]) + " MB  " + ("encrypted" if entry["encrypted"] else "readable")}' for entry in entries]
        return f'Directory: {directory}\n' + ('\n'.join(rows) if rows else 'Directory empty.')
    if verb == 'find':
        pattern = args[0]
        if '/' in pattern:
            raise FilesystemError('Use find <filename-or-pattern> in the directory you want to search.')
        entries = [entry for entry in server.files if entry['present'] and entry.get('type') != 'directory' and
                   (cwd == '/' or absolute(entry['name']).startswith(cwd.rstrip('/') + '/')) and
                   fnmatch.fnmatchcase(posixpath.basename(entry['name']), pattern)]
        entries.sort(key=lambda entry: entry['name'])
        remember(state, entries)
        state.update(dirty=True, work=state.get('work', 0) + 8)
        record_action(slot, target, 'files_searched', f'Searched {cwd} for {pattern}.')
        return '\n'.join(absolute(entry['name']) for entry in entries) or 'No matching files.'
    entry = resolve_file(server.files, args[0], cwd)
    remember(state, [entry])
    actual = {**target, 'file': entry['name'], 'size': entry['size'], 'encrypted': entry['encrypted']}
    primary = entry['name'] == target['file']
    if verb == 'cat':
        state.update(dirty=True, work=state.get('work', 0) + 1)
        observe(server, path=entry['name'])
        server.save()
        record_action(slot, actual, 'file_read', f'{entry["name"]} previewed.')
        return 'Encrypted archive. Use Rosetta before reading this file.' if entry['encrypted'] else entry.get('content', 'Binary archive. Use get to download a local copy.')
    if verb == 'get':
        local = copy_to_local(slot, actual)
        observe(server, path=entry['name'])
        server.save()
        record_action(slot, actual, 'file_retrieved', f'{entry["name"]} copied to local storage.')
        if primary:
            state.update(recovered=True, local_file_id=local['id'], recovery_receipt={
                key: local[key] for key in ('id', 'source', 'source_path', 'revision')
            })
        state.update(dirty=True, work=state.get('work', 0) + math.ceil(entry['size'] / hardware(slot)['gateway']['bandwidth'] + state.get('latency', 0) / 10))
        return f'Copied {entry["name"]} to local storage. {entry["size"]} MB verified.\nLocal file: {local["name"]} ({"encrypted" if local["encrypted"] else "readable"}) / drive usage {storage_used(slot)} MB.'
    if verb == 'rm':
        record_action(slot, actual, 'file_deleted', f'{entry["name"]} removed from the remote filesystem.', delete=True)
        state['dirty'] = True
        state['known_paths'] = [known for known in state.get('known_paths', []) if known['path'] != absolute(entry['name'])]
        required = required_paths(target, server.files)
        if entry['name'] in required:
            receipts = set(state.get('deletion_receipts', [])) | {entry['name']}
            state['deletion_receipts'] = sorted(receipts)
            state['deleted'] = set(required).issubset(receipts)
            return f'{entry["name"]} removed. Deletion receipt stored locally. Required copies: {len(set(required) & receipts)}/{len(required)}.'
        if primary and not required:
            state['deleted'] = True
        return f'{entry["name"]} removed. Deletion receipt stored locally.' if primary and not required else f'{entry["name"]} removed.'
    raise FilesystemError('Unknown filesystem command.')


def remember(state, entries, directory=None):
    known = {entry['path']: entry for entry in state.get('known_paths', [])}
    if directory is not None:
        known = {path: entry for path, entry in known.items() if posixpath.dirname(path) != directory}
    for entry in entries:
        known[absolute(entry['name'])] = dict(path=absolute(entry['name']), type=entry.get('type', 'file'))
    state['known_paths'] = list(known.values())[-100:]
