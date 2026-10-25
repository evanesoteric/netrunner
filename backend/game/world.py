"""Built-in content plus durable, locally generated world content."""
from .catalog import CONTRACTS, CONTRACT_BY_ID, RELAYS, RELAY_BY_ID
from .models import DirectoryServer, GeneratedMission
from .public_servers import PUBLIC_SERVERS, PUBLIC_BY_ID
from .services import service_name, service_key, service_fields, SERVICES


def all_contracts(slot=None):
    return CONTRACTS + [row.data for row in GeneratedMission.objects.order_by('key')] + (list(slot.broker_jobs.values()) if slot else [])


def get_contract(key, slot=None):
    if not key:
        return None
    if slot and key in slot.broker_jobs:
        return slot.broker_jobs[key]
    if key in CONTRACT_BY_ID:
        return CONTRACT_BY_ID[key]
    row = GeneratedMission.objects.filter(pk=key).first()
    return row.data if row else None


def all_servers(slot=None):
    entries = RELAYS + PUBLIC_SERVERS + [row.data for row in DirectoryServer.objects.order_by('key')]
    known = {address: {**descriptor, 'port': port} for address, descriptor, port in slot.server_states.values_list('address', 'descriptor', 'port')} if slot else {}
    result = []
    for entry in entries:
        if entry.get('hidden') and not (slot and slot.market_unlocked):
            continue
        profile = known.get(entry['address'], entry)
        key = service_key(profile)
        fields = service_fields(key) if key in SERVICES else {}
        result.append({**entry, **fields, 'port': profile.get('port', fields.get('port', 22)),
                       'service_version': profile.get('service_version', fields.get('service_version', '')),
                       'service_name': service_name(profile)})
    return result


def get_server(key):
    if key in RELAY_BY_ID:
        return RELAY_BY_ID[key]
    if key in PUBLIC_BY_ID:
        return PUBLIC_BY_ID[key]
    row = DirectoryServer.objects.filter(pk=key).first()
    return row.data if row else None


def target_for_server(server):
    return {**server, 'server_id': server['id'], 'target': server['address'],
            'file': 'public-index.dat', 'size': 12, 'encrypted': False,
            'security': server.get('security', server['rank'] + 1), 'port': server.get('port', 22),
            'objective': 'explore'}


def session_target(slot):
    return slot.remote_host or get_contract(slot.active_contract, slot)
