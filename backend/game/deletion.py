"""Exact-path requirements for fictional erase-all-copies contracts."""
from .filesystem import absolute


def required_paths(target, files=None):
    paths = []
    for source in target.get('delete_paths', []):
        source = absolute(source).lstrip('/')
        # Maintenance can relocate copies. Their original identity stays stable.
        entry = next((entry for entry in files or [] if entry.get('original') == source or entry['name'] == source), None)
        path = entry['name'] if entry else source
        if path not in paths:
            paths.append(path)
    return paths


def missing_deletions(target, files, receipts):
    return [path for path in required_paths(target, files)
            if path not in receipts or any(entry['name'] == path and entry['present'] for entry in files)]


def description(target):
    paths = ', '.join('/' + path for path in required_paths(target))
    return f'Erase all listed copies from {target["target"]}: {paths}. Delete every listed file, erase remote access logs, disconnect, and submit proof through the broker. Other files are not required.'
