"""Per-runner broker offers. Completed assignments are never reoffered."""
from datetime import timedelta
from pathlib import PurePosixPath
from uuid import uuid4
from secrets import choice
from .services import SERVICES, service_fields
from .filesystem import artifact_path
from .deletion import description as deletion_description
from django.utils import timezone
from django.utils.dateparse import parse_datetime


def offered_jobs(slot):
    from .world import all_contracts
    accepted = set(slot.assignments.values_list('key', flat=True))
    return [job for job in all_contracts(slot) if job['id'] not in accepted and job['id'] not in slot.broker_consumed and abs(job['rank'] - slot.rank) <= 1][:48]


def ensure_tickets(slot):
    from .contracts import codes
    base = codes()
    jobs = offered_jobs(slot)
    keys = list(slot.assignments.filter(status='accepted').values_list('key', flat=True)) + ([slot.active_contract] if slot.active_contract else []) + [job['id'] for job in jobs]
    # Retain active and already-visible tickets. Only live offers need distinct 8-bit codes.
    keys = sorted(set(keys), key=lambda key: (key != slot.active_contract, key not in slot.broker_codes))
    used, mapping = set(), dict(slot.broker_codes)
    for key in keys:
        preferred = mapping.get(key, base.get(key))
        if preferred is None or preferred in used:
            unused = [value for value in range(256) if value not in used and value not in mapping.values()]
            preferred = choice(unused) if unused else choice([value for value in range(256) if value not in used])
        mapping[key] = preferred
        used.add(preferred)
    changed = mapping != slot.broker_codes
    slot.broker_codes = mapping
    return changed


def consume(slot, job):
    if job['id'] not in slot.broker_consumed:
        slot.broker_consumed = slot.broker_consumed + [job['id']]
        slot.broker_pending = slot.broker_pending + [dict(template=job, due_at=(timezone.now() + timedelta(minutes=5)).isoformat())]


def delay_replacement(slot, key):
    slot.broker_pending = [{**entry, 'due_at': (timezone.now() + timedelta(minutes=10)).isoformat()} if entry['template']['id'] == key else entry for entry in slot.broker_pending]


def settle_broker(slot):
    pending, changed = [], False
    for entry in slot.broker_pending:
        if parse_datetime(entry['due_at']) > timezone.now():
            pending.append(entry)
            continue
        template = entry['template']
        nonce = uuid4().hex
        path = PurePosixPath(template['file'])
        job = {**template, 'id': f'offer-{nonce}', 'target': f'broker-{nonce[:16]}.internal',
               'file': f'{path.stem}_{nonce[:6]}{path.suffix}',
               'title': f'{["Lumen","Redwood","Silverline","Arcadia"][int(nonce[0],16)%4]} dossier {nonce[:6]} // {template["objective"]}',
               'x': 220 + int(nonce[1:4],16)%640, 'y': 120 + int(nonce[4:7],16)%230}
        job.update(service_fields(list(SERVICES)[int(nonce[7:9], 16) % len(SERVICES)]))
        job['artifact_path'] = artifact_path(job, nested=int(nonce[9], 16) < 5)
        if template.get('delete_paths'):
            job.update(service_fields(template['service']))
            job['delete_paths'] = [str(PurePosixPath(path).with_name(f'{PurePosixPath(path).stem}_{nonce[:6]}{PurePosixPath(path).suffix}')) for path in template['delete_paths']]
            job['artifact_path'] = job['delete_paths'][0]
            job['file'] = PurePosixPath(job['artifact_path']).name
            job['title'] = f'{job["title"].split(" // ")[0]} // erase all copies'
        job['organization'] = f'{["Lumen","Redwood","Silverline","Arcadia"][int(nonce[0],16)%4]} Research Group'
        job['server_name'] = f'Private Records Server {nonce[:8].upper()}'
        job['description'] = f'{"Recover" if job["objective"] == "retrieve" else "Delete"} {job["file"]} from {job["target"]}. Leave no remote access logs and deliver proof through the broker.' + (' The archive is encrypted.' if job['encrypted'] else '')
        if job.get('delete_paths'):
            job['description'] = deletion_description(job)
        slot.broker_jobs = {**slot.broker_jobs, job['id']: job}
        changed = True
    if changed:
        slot.broker_pending = pending
    changed = ensure_tickets(slot) or changed
    if changed:
        slot.save()
