"""Built-in content plus durable, locally generated world content."""
from .catalog import CONTRACTS, CONTRACT_BY_ID, RELAYS, RELAY_BY_ID
from .models import DirectoryServer, GeneratedMission
from .public_servers import PUBLIC_SERVERS, PUBLIC_BY_ID


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
    return [entry for entry in entries if not entry.get('hidden') or (slot and slot.market_unlocked)]


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
            'security': server.get('security', server['rank'] + 1), 'port': 22,
            'objective': 'explore'}


def session_target(slot):
    return slot.remote_host or get_contract(slot.active_contract, slot)
