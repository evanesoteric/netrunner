"""Ten independent contracts; only one remote session can be open at a time."""
from copy import deepcopy
from datetime import timedelta
from django.utils import timezone
from .models import Assignment
from .world import get_contract
from .mechanics import GameError

LIMIT = 10


def ensure_legacy(slot):
    if slot.active_contract and not slot.assignments.filter(key=slot.active_contract).exists():
        job = get_contract(slot.active_contract, slot)
        if job:
            Assignment.objects.create(slot=slot, key=slot.active_contract, descriptor=job, state=deepcopy(slot.mission_state))
    from .mailbox import briefing
    for assignment in slot.assignments.filter(status='accepted').exclude(mail__kind='briefing'):
        briefing(slot, assignment)


def stash(slot):
    if slot.active_contract:
        slot.assignments.filter(key=slot.active_contract, status='accepted').update(state=deepcopy(slot.mission_state))


def focus(slot, key):
    if slot.mission_started:
        if key == slot.active_contract:
            return
        raise GameError('Disconnect before switching assignments.')
    assignment = slot.assignments.filter(key=key, status='accepted').first() if key else None
    if key and not assignment:
        raise GameError('That assignment is no longer accepted.')
    if key == slot.active_contract:
        return
    stash(slot)
    slot.active_contract = key or ''
    slot.mission_state = deepcopy(assignment.state) if assignment else {}
    slot.remote_host = {}


def remove(slot, status):
    slot.assignments.filter(key=slot.active_contract, status='accepted').update(status=status, state=deepcopy(slot.mission_state))
    slot.active_contract = ''


def complete(slot, attachment_ids):
    from .mechanics import transact
    from .persistence import ensure_server, record_contract, effective_target
    from .catalog import SUCCESS_COOLDOWN
    from .contracts import public_code
    job = get_contract(slot.active_contract, slot)
    if not job:
        raise GameError('No reserved contract to submit.')
    if slot.mission_started:
        raise GameError('Cannot deliver evidence while connected to the target.')
    job = effective_target(slot, job)
    state = slot.mission_state
    local = next((entry for entry in slot.local_files if entry['id'] == state.get('local_file_id')), None)
    if job['objective'] == 'retrieve':
        if not local or local['id'] not in attachment_ids:
            raise GameError('Broker rejected delivery: attach the recovered objective file from your local drive.')
        if local.get('encrypted'):
            raise GameError('Broker rejected delivery: archive is encrypted. Decrypt the local copy with Rosetta first.')
        receipt = state.get('recovery_receipt')
        if receipt:
            matches = all(local.get(key) == receipt.get(key) for key in ('id', 'source', 'source_path', 'revision'))
        else:
            # Older saves have no explicit receipt. The persistent artifact keeps
            # its original identity when maintenance moves it into an archive.
            server = ensure_server(slot, job)
            artifact = server.files[0] if server.files else {}
            original = artifact.get('original')
            paths = [job['file'], original]
            revision = local.get('revision')
            if original and type(revision) is int and 1 < revision <= server.revision:
                paths.append(f'archive/r{revision}/{original.lstrip("/")}')
            matches = local.get('source_path') in paths
        if local['source'] != job['target'] or not matches:
            raise GameError('Broker rejected delivery: file provenance does not match this assignment.')
    if job.get('delete_paths'):
        from .deletion import missing_deletions
        server = ensure_server(slot, job)
        missing = missing_deletions(job, server.files, state.get('deletion_receipts', []))
        if missing:
            raise GameError('Broker rejected delivery: deletion proof missing for required copies:\n' + '\n'.join('/' + path for path in missing))
    elif job['objective'] == 'delete':
        server = ensure_server(slot, job)
        if any(entry['name'] == job['file'] and entry['present'] for entry in server.files):
            raise GameError('Broker rejected delivery: target file is present again. Revisit the server and delete the current copy.')
    fulfilled = (state.get('recovered') and local) if job['objective'] == 'retrieve' else state.get('deleted')
    if not fulfilled or not state.get('clean_exit'):
        raise GameError('Broker rejected delivery: objective or clean exit evidence missing.')
    transact(slot, job['reward'], f'Contract payment // {public_code(job["id"], slot)}')
    slot.reputation += job['reputation']; slot.completed += 1
    until = timezone.now() + timedelta(seconds=SUCCESS_COOLDOWN)
    record_contract(slot, job, until)
    slot.contract_cooldowns = {**slot.contract_cooldowns, job['id']: until.isoformat()}
    remove(slot, 'completed')
    slot.mission_state = {}
    return f'Delivery verified. +{job["reward"]} CPH / +{job["reputation"]} reputation.\nThe broker will publish a new assignment after its sourcing delay.'
