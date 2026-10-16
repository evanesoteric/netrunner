"""Persisted public contract numbers; catalog template keys are private."""
from .models import ContractIdentity


def codes():
    return dict(ContractIdentity.objects.values_list('template_key', 'code'))


def public_job(job, mapping=None):
    if job is None:
        return None
    mapping = codes() if mapping is None else mapping
    return {**job, 'id': str(mapping[job['id']])}


def public_code(key):
    return str(ContractIdentity.objects.get(template_key=key).code)


def ensure_codes(using='default'):
    import random
    from django.db import connections, transaction
    from .catalog import CONTRACTS
    with transaction.atomic(using=using):
        with connections[using].cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(78198421)')
        existing = dict(ContractIdentity.objects.using(using).values_list('template_key', 'code'))
        missing = [job['id'] for job in CONTRACTS if job['id'] not in existing]
        available = list(set(range(256)) - set(existing.values()))
        if len(missing) > len(available):
            raise RuntimeError('The 8-bit contract ID space is full.')
        allocated = random.SystemRandom().sample(available, len(missing))
        ContractIdentity.objects.using(using).bulk_create([
            ContractIdentity(template_key=key, code=code) for key, code in zip(missing, allocated)
        ])
