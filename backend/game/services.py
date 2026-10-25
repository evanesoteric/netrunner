"""Fictional service banners and credential adapters; no real vulnerability data."""
SERVICES = {
    'ssh': dict(protocol='SSH', label='SSH', port=22, transport='tcp', release='', bot='hexdealer'),
    'http': dict(protocol='HTTP', label='HTTP', port=443, transport='tcp', release='', bot='packetwitch'),
    'rdp': dict(protocol='RDP', label='RDP remote desktop', port=3389, transport='tcp', release='', bot='zeroday'),
    'wordpress': dict(protocol='WORDPRESS', label='WordPress CMS', port=443, transport='tcp', release='6.4', bot='packetwitch'),
    'php': dict(protocol='PHP', label='PHP', port=443, transport='tcp', release='5.6', bot='packetwitch'),
    'sip': dict(protocol='SIP', label='VOIP / SIP', port=5060, transport='udp', release='2.0', bot='zeroday'),
    'telnet': dict(protocol='TELNET', label='Telnet', port=23, transport='tcp', release='', bot='hexdealer'),
    'ftp': dict(protocol='FTP', label='FTP', port=21, transport='tcp', release='', bot='hexdealer'),
    'smtp': dict(protocol='SMTP', label='SMTP mail', port=25, transport='tcp', release='', bot='zeroday'),
    'mysql': dict(protocol='MYSQL', label='MySQL', port=3306, transport='tcp', release='5.7', bot='packetwitch'),
    'redis': dict(protocol='REDIS', label='Redis', port=6379, transport='tcp', release='6.2', bot='hexdealer'),
}
UNKNOWN_SERVICE = dict(protocol='UNKNOWN', label='Unknown service', port=0, transport='tcp', release='')
PROTOCOLS = {entry['protocol']: key for key, entry in SERVICES.items()}


def service_key(target):
    if target.get('service') in SERVICES:
        return target['service']
    port = target.get('port', 22)
    if port == 2222:
        return 'ssh'
    if port in (80, 8080, 8443):
        return 'http'
    return next((key for key, entry in SERVICES.items() if entry['port'] == port), 'unknown')


def service_name(target):
    entry = SERVICES.get(service_key(target), UNKNOWN_SERVICE)
    release = target.get('service_version', entry['release'])
    return entry['label'] + (f' {release}' if release else '')


def service_fields(key):
    entry = SERVICES[key]
    return dict(service=key, service_version=entry['release'], port=entry['port'])


def fingerprint(target):
    entry = SERVICES.get(service_key(target), UNKNOWN_SERVICE)
    return dict(protocol=entry['protocol'], release=target.get('service_version', entry['release']),
                version=target['security'], revision=target.get('server_revision', 1))


def fingerprint_text(service):
    key = PROTOCOLS.get(service['protocol'])
    if key is None:
        return f'UNKNOWN / auth-v{service["version"]} / patch r{service["revision"]}'
    label = SERVICES[key]['label'] if key not in ('ssh', 'http', 'rdp') else service['protocol']
    release = service.get('release', SERVICES[key]['release'])
    return f'{label}{" " + release if release else ""} / auth-v{service["version"]} / patch r{service["revision"]}'
