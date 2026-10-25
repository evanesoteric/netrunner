"""Persistent fictional addressing. No DNS, sockets or operating-system ping."""
from contextlib import contextmanager
from contextvars import ContextVar
from ipaddress import ip_address
from django.db import transaction, connection
from .models import NetworkAddress

_cache = ContextVar('network_addresses', default=None)


@contextmanager
def address_scope():
    token = _cache.set({})
    try:
        yield
    finally:
        _cache.reset(token)


def prime_addresses(hosts):
    cache = _cache.get()
    if cache is not None:
        missing = set(hosts) - cache.keys()
        if missing:
            cache.update(NetworkAddress.objects.filter(host__in=missing, ip__isnull=False).values_list('host', 'ip'))


def allocated_ip(index):
    # Three documentation ranges first; private 10/8 supports long-lived worlds.
    if index < 1:
        raise ValueError('Address indices start at one.')
    index -= 1
    if index < 762:
        return f'{["192.0.2", "198.51.100", "203.0.113"][index // 254]}.{index % 254 + 1}'
    index -= 762
    if index >= 254 * 256 * 256:
        raise ValueError('The fictional IPv4 address space is exhausted.')
    return f'10.{index // (254 * 256)}.{index // 254 % 256}.{index % 254 + 1}'


def ip_for(host):
    cache = _cache.get()
    if cache is not None and host in cache:
        return cache[host]
    value = _allocate_address(host)
    if cache is not None:
        cache[host] = value
    return value


@transaction.atomic
def _allocate_address(host):
    entry = NetworkAddress.objects.filter(host=host).first()
    if entry is None or entry.ip is None:
        # Serialize new allocations across the owning transaction. Requests may
        # encounter hosts in different orders; this avoids cross-host deadlocks.
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(78198422)')
        entry, _ = NetworkAddress.objects.get_or_create(host=host)
        if entry.ip is None:
            entry.ip = allocated_ip(entry.pk)
            entry.save(update_fields=['ip'])
    return entry.ip


def target_name(target):
    if not target.get('name') and not target.get('organization'):
        from .catalog import CONTRACT_BY_ID
        target = {**CONTRACT_BY_ID.get(target.get('id'), {}), **target}
    return target.get('name') or ': '.join(part for part in (target.get('organization'), target.get('server_name')) if part) or target.get('title', '').split(' // ')[0] or target.get('target', target.get('address', 'Unknown host'))


def known_targets(slot):
    from .world import all_servers, get_contract
    from .broker import offered_jobs
    job = get_contract(slot.active_contract, slot)
    return [*all_servers(slot), *[entry.descriptor for entry in slot.assignments.filter(status='accepted')], *offered_jobs(slot), *([job] if job else []), *[row.descriptor for row in slot.server_states.all()]]


def resolve_host(slot, identifier):
    try:
        value = str(ip_address(identifier))
    except ValueError:
        # Existing canonical hostnames remain valid aliases and are authorized by
        # the caller's normal directory, contract and rank checks.
        if '.' in identifier and ' ' not in identifier:
            return identifier.lower()
        matches = {entry.get('target', entry.get('address')) for entry in known_targets(slot)
                   if identifier.casefold() == target_name(entry).casefold()}
        matches.discard(None)
        if len(matches) == 1:
            return matches.pop()
        from .mechanics import GameError
        raise GameError('Name is unknown or ambiguous. Look up the organization and specific server in Atlas.')
    entry = NetworkAddress.objects.filter(ip=value).first()
    if entry:
        return entry.host
    from .mechanics import GameError
    raise GameError('Address not present in your fictional network directory.')


def ping_target(slot, identifier, resolve_only=False):
    from .mechanics import GameError
    host = resolve_host(slot, identifier)
    target = next((entry for entry in known_targets(slot) if entry.get('target', entry.get('address')) == host), None)
    if not target:
        raise GameError('Host not present in your network directory.')
    address = ip_for(host)
    name = target_name(target)
    if resolve_only:
        return f'{name}\nAddress: {address}'
    if not target.get('ping_response', True):
        return f'PING {name} [{address}]\nRequest timed out. ICMP may be filtered; scan and connect remain available.'
    return f'PING {name} [{address}]\nReply from {address}: bytes=32 time={max(1, target.get("latency", 4))}ms TTL=64\n1 sent, 1 received, 0% loss. No remote session opened.'
