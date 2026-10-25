"""Bounded, entirely virtual server filesystems. Never read or write host paths."""
import hashlib
import posixpath
import random
from .services import service_key

LAYOUT_VERSION = 1
SERVICE_DIRS = {
    'ssh': 'home/admin', 'http': 'var/www', 'wordpress': 'var/www', 'php': 'var/www',
    'rdp': 'Users/admin/Documents', 'sip': 'var/spool/voip', 'telnet': 'home/operator',
    'ftp': 'srv/ftp', 'smtp': 'var/mail', 'mysql': 'var/lib/mysql', 'redis': 'var/lib/redis',
}
COMMON = {
    'NOTICE.txt': 'Internal operations files. Consult the service directory for application records.\n',
    'CHANGELOG.txt': 'Routine maintenance completed; previous deployments archived.\n',
    'disk-usage.csv': 'Volume,status\nsystem,healthy\ndata,healthy\n',
    'maintenance.log': 'Scheduled backup completed. Pending tasks are in the administrator notes.\n',
    'README.txt': 'Maintenance notes: service data is kept in the usual service directory. Backups are under /backup.\n',
    'etc/hostname': 'Managed internal host.\n', 'etc/motd': 'Authorized administrators only.\n',
    'etc/cron.d/maintenance': 'Nightly housekeeping and archive rotation enabled.\n',
    'var/log/system.log': 'Service startup complete. Scheduled health check passed.\n',
    'var/log/auth.log': 'Administrator credential service available.\n',
    'home/admin/notes.txt': 'Check the application directory before rotating the backups.\n',
    'home/admin/todo.txt': 'Review capacity report. Archive the previous deployment.\n',
    'backup/manifest.txt': 'Rotated snapshots are reference copies, not current production records.\n',
    'backup/previous.dat': 'Previous maintenance snapshot.\n',
    'tmp/session.tmp': 'Temporary session cache.\n', 'opt/tools/version.txt': 'Internal tools bundle, stable channel.\n',
}
SERVICE_FILES = {
    'ssh': {'home/admin/.profile': 'Terminal environment defaults.\n', 'home/admin/projects/roadmap.txt': 'Review next quarter milestones.\n', 'etc/ssh/sshd_config': 'Simulated SSH daemon configuration.\n'},
    'http': {'var/www/index.html': '<html>Internal portal</html>\n', 'var/www/assets/site.css': 'Internal portal stylesheet.\n', 'etc/http/server.conf': 'Document root: /var/www\n'},
    'wordpress': {'var/www/index.php': 'WordPress front controller.\n', 'var/www/wp-config.php': 'Database storage is managed locally. Review the site export before maintenance.\n', 'var/www/wp-content/uploads/media-index.txt': 'Media upload index.\n', 'var/www/wp-content/plugins/manifest.txt': 'Installed plugin inventory.\n', 'var/www/wp-content/themes/theme.css': 'Site theme stylesheet.\n', 'var/www/database-schema.sql': 'Site database schema; records are stored separately.\n'},
    'php': {'var/www/index.php': 'Legacy PHP application front controller.\n', 'var/www/config/app.ini': 'Legacy application configuration.\n', 'var/www/lib/bootstrap.php': 'Application bootstrap inventory.\n', 'var/www/cache/template.cache': 'Cached template output.\n'},
    'rdp': {'Users/admin/Desktop/README.txt': 'Office records are in /Users/admin/Documents.\n', 'Users/admin/Documents/meeting-notes.txt': 'Operations review, nothing urgent.\n', 'Users/admin/Documents/budget.csv': 'Department,allocation\nOperations,planned\n', 'Users/Public/welcome.txt': 'Shared workstation documents.\n', 'Windows/Logs/update.log': 'Last workstation update completed.\n'},
    'sip': {'etc/voip/sip.conf': 'Simulated SIP routing configuration.\n', 'var/spool/voip/extensions.csv': 'Extension,department\n100,Reception\n', 'var/spool/voip/recordings/index.txt': 'Recording archive index.\n'},
    'telnet': {'home/operator/.profile': 'Legacy terminal environment.\n', 'home/operator/inventory.txt': 'Terminal controller inventory.\n', 'etc/terminal.conf': 'Legacy controller configuration.\n'},
    'ftp': {'srv/ftp/welcome.txt': 'Transfer staging area.\n', 'srv/ftp/incoming/queue.txt': 'No pending inbound transfers.\n', 'srv/ftp/pub/catalog.txt': 'Public transfer catalog.\n'},
    'smtp': {'etc/mail/aliases': 'Administrator mailbox routing.\n', 'var/mail/postmaster/inbox.txt': 'Scheduled maintenance notice.\n', 'var/mail/queue/status.txt': 'Queue health normal.\n'},
    'mysql': {'etc/mysql/server.cnf': 'Data directory: /var/lib/mysql\n', 'var/lib/mysql/schema.sql': 'Schema migration index.\n', 'var/lib/mysql/maintenance.log': 'Latest consistency check passed.\n'},
    'redis': {'etc/redis/redis.conf': 'Snapshot directory: /var/lib/redis\n', 'var/lib/redis/appendonly.aof': 'Simulated cache journal.\n', 'var/lib/redis/metrics.csv': 'Metric,value\nhealth,normal\n'},
}


class FilesystemError(ValueError):
    pass


def absolute(path, cwd='/'):
    if not isinstance(path, str) or len(path) > 512 or any(ord(char) < 32 for char in path):
        raise FilesystemError('Invalid virtual path.')
    return '/' + posixpath.normpath('/' + posixpath.join(cwd, path).lstrip('/')).lstrip('/')


def artifact_path(target, nested=False):
    name = posixpath.basename(target['file'])
    return f'{SERVICE_DIRS.get(service_key(target), "home/admin")}/{name}' if nested else name


def build_tree(target, existing=None, revision=1):
    """Keep the contract artifact first for legacy saves, retaining every old record."""
    rng = random.Random(hashlib.sha256(target['target'].encode()).digest())
    old = existing or []
    primary = dict(old[0]) if old else dict(name=target.get('artifact_path', target['file']), original=target.get('artifact_path', target['file']), size=target['size'], encrypted=target['encrypted'], present=True)
    primary.update(type='file', artifact=True)
    primary['name'] = absolute(primary['name']).lstrip('/')
    if revision > 1 and not old:
        primary['name'] = f'archive/r{revision}/{primary["original"].lstrip("/")}'
    entries = {primary['name']: primary}
    for item in old[1:]:
        entries[absolute(item['name']).lstrip('/')] = dict(item)
    for source in target.get('delete_paths', []):
        original = absolute(source).lstrip('/')
        name = f'archive/r{revision}/{original}' if revision > 1 and not old else original
        if name not in entries:
            entries[name] = dict(name=name, original=original, type='file', size=target['size'], encrypted=False,
                                 present=True, contract_copy=True, content='Current retained copy. This exact file is included in the deletion brief.\n')
    files = {**COMMON, **SERVICE_FILES.get(service_key(target), {})}
    # A similarly named reference copy makes exact paths matter for evidence.
    if not target.get('delete_paths'):
        files[f'backup/reference/{posixpath.basename(target["file"])}'] = 'Reference copy from a prior export; not current production evidence.\n'
    for name, text in files.items():
        if name not in entries:
            entries[name] = dict(name=name, original=name, type='file', size=rng.randint(1, 4), encrypted=False, present=True, content=text)
    parents = {'tmp', 'backup', SERVICE_DIRS.get(service_key(target), 'home/admin')}
    for name in list(entries):
        parent = posixpath.dirname(name)
        while parent:
            parents.add(parent)
            parent = posixpath.dirname(parent)
    for name in sorted(parents):
        if name in entries and entries[name].get('type') != 'directory':
            raise FilesystemError(f'File path conflicts with a directory: /{name}')
        if name not in entries:
            entries[name] = dict(name=name, type='directory', size=0, encrypted=False, present=True)
    return list(entries.values())


def directory_exists(files, path):
    return path == '/' or any(item['present'] and item.get('type') == 'directory' and absolute(item['name']) == path for item in files)


def listing(files, directory):
    if not directory_exists(files, directory):
        raise FilesystemError('Directory not found.')
    return sorted([item for item in files if item['present'] and posixpath.dirname(absolute(item['name'])) == directory],
                  key=lambda item: (item.get('type') != 'directory', item['name']))


def resolve_file(files, path, cwd='/'):
    name = absolute(path, cwd).lstrip('/')
    entry = next((item for item in files if item['name'] == name and item['present']), None)
    if not entry:
        raise FilesystemError('File not found.')
    if entry.get('type') == 'directory':
        raise FilesystemError('This is a directory. Use cd or ls; directory removal is not supported.')
    return entry
