"""Durable per-save server simulation. Call mutations while holding the SaveSlot lock."""
from datetime import timedelta
from django.utils import timezone
from .models import ServerState, ServerEvent
from .world import session_target
from .services import service_key, SERVICES, UNKNOWN_SERVICE

MAINTENANCE_SECONDS = 600


def initial_files(target):
    return [dict(name=target['file'], original=target['file'], size=target['size'],
                 encrypted=target['encrypted'], present=True)]


def event(server, kind, summary):
    ServerEvent.objects.create(server=server, kind=kind, summary=summary)


def ensure_server(slot, target):
    server, created = ServerState.objects.get_or_create(slot=slot, address=target['target'], defaults={
        'descriptor': {key: value for key, value in target.items() if not key.startswith('_')},
        'files': initial_files(target), 'security': target['security'], 'port': target['port'],
        'backdoor_installed': any(entry['target'] == target['target'] for entry in slot.backdoors),
    })
    if created:
        event(server, 'discovered', 'Server added to this runner’s persistent world.')
    return server


def effective_target(slot, target):
    if not target:
        return target
    server = ServerState.objects.filter(slot=slot, address=target['target']).first()
    if not server:
        return target
    artifact = server.files[0] if server.files else None
    key = service_key(server.descriptor)
    return {**target, 'service': key, 'service_version': server.descriptor.get('service_version', SERVICES.get(key, UNKNOWN_SERVICE)['release']),
            'security': server.security, 'port': server.port,
            'file': artifact['name'] if artifact else target['file'],
            'encrypted': artifact['encrypted'] if artifact else target['encrypted'],
            'file_present': bool(artifact and artifact['present']), 'server_revision': server.revision}


def current_target(slot):
    return effective_target(slot, session_target(slot))


def observe(server):
    key = service_key(server.descriptor)
    server.observed = dict(service=key, service_version=server.descriptor.get('service_version', SERVICES.get(key, UNKNOWN_SERVICE)['release']), revision=server.revision, port=server.port, security=server.security,
                           files=server.files, at=timezone.now().isoformat())


def schedule(server, due=None):
    due = due or timezone.now() + timedelta(seconds=MAINTENANCE_SECONDS)
    if not server.maintenance_due or due < server.maintenance_due:
        server.maintenance_due = due
        event(server, 'maintenance_scheduled', f'Administrator maintenance scheduled in about {max(1, round((due - timezone.now()).total_seconds() / 60))} minutes. Active sessions will be left undisturbed.')


def settle_world(slot):
    active = session_target(slot) if slot.mission_started else None
    due = slot.server_states.filter(maintenance_due__lte=timezone.now())
    if active:
        due = due.exclude(address=active['target'])
    for server in due:
        server.revision += 1
        server.files = initial_files(server.descriptor)
        for artifact in server.files:
            artifact['name'] = f'archive/r{server.revision}/{artifact["original"]}'
        original_port = server.descriptor['port']
        alternate_port = 2222 if original_port == 22 else 8443 if original_port in (80, 443) else original_port
        server.port = alternate_port if server.revision % 2 == 0 else original_port
        server.remote_logs = []
        server.maintenance_due = None
        # Keep the last observed snapshot until the player scans or lists again.
        event(server, 'administrator_patch', f'Administrator completed maintenance revision {server.revision}: archives restored and moved, authentication service rotated, remote logs archived. Scan again for the current fingerprint. Wraith links remain installed.')
        server.save()


def record_visit(slot, target, backdoor=False):
    server = ensure_server(slot, target)
    server.visits += 1
    server.last_visit = timezone.now()
    event(server, 'backdoor_visit' if backdoor else 'connected', 'Direct Wraith connection; remote logging suppressed.' if backdoor else 'Remote connection established through the committed route.')
    server.save()


def record_action(slot, target, kind, summary, *, delete=False, decrypt=False, snapshot=False):
    server = ensure_server(slot, target)
    if delete or decrypt:
        for artifact in server.files:
            if artifact['name'] == target['file']:
                if delete:
                    artifact['present'] = False
                    schedule(server)
                if decrypt:
                    artifact['encrypted'] = False
    if snapshot or delete or decrypt:
        observe(server)
    event(server, kind, summary)
    server.save()


def sync_remote_logs(slot):
    if not slot.mission_started or slot.remote_host.get('_backdoor') or not slot.mission_state.get('dirty'):
        return
    target = session_target(slot)
    if target:
        server = ensure_server(slot, target)
        if not slot.mission_state.get('logs_recorded'):
            server.remote_logs = (server.remote_logs + [dict(at=timezone.now().isoformat(), source='runner access')])[-100:]
            server.save()
            slot.mission_state['logs_recorded'] = True


def clear_remote_logs(slot, target):
    server = ensure_server(slot, target)
    server.remote_logs = []
    slot.mission_state['logs_recorded'] = False
    event(server, 'logs_erased', 'Remote access logs erased. The operator journal remains intact.')
    server.save()


def record_failure(slot, target, reason):
    server = ensure_server(slot, target)
    event(server, 'intrusion_detected', reason)
    schedule(server)
    server.save()


def record_contract(slot, target, due):
    server = ensure_server(slot, target)
    event(server, 'contract_completed', 'Broker verified objective evidence and clean exit.')
    schedule(server, due)
    server.save()


def record_proxy_route(slot, target):
    from .world import get_server, target_for_server
    for index, key in enumerate(slot.proxy_route, 1):
        proxy = ensure_server(slot, target_for_server(get_server(key)))
        proxy.visits += 1
        proxy.last_visit = timezone.now()
        event(proxy, 'proxy_transit', f'Relayed hop {index}/{len(slot.proxy_route)} toward {target["target"]}.')
        proxy.save()
