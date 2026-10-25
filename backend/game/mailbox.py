"""Fictional local mail only. No SMTP, network delivery or host-file uploads."""
from uuid import UUID, uuid4
from django.utils import timezone
from .models import MailMessage, EnforcementCase
from .mechanics import GameError

BROKER = 'dispatch@broker.internal'
AGENCY = 'enforcement@sib.internal'
LEGAL_ACCOUNT = 'MERIDIAN-LEGAL-001'


def address(slot):
    return f'runner-{slot.pk}@mail.internal'


def incoming(slot, sender, subject, body, **extra):
    return MailMessage.objects.create(slot=slot, sender=sender, recipient=address(slot), subject=subject[:180], body=body, **extra)


def briefing(slot, assignment):
    from .contracts import public_code
    from .addresses import target_name
    job = assignment.descriptor
    code = public_code(assignment.key, slot)
    body = (f'Assignment {code}: {job["title"]}\n\n{job["description"].replace(job["target"], target_name(job))}'
            f'\n\nTarget: {target_name(job)}\nFind its address in Atlas.\nObjective: {job["objective"]}\nArtifact: {job["file"]}'
            f'\nPayment: {job["reward"]} CPH\nReputation: +{job["reputation"]}')
    if job.get('delete_paths'):
        body += '\nRequired deletions:\n' + '\n'.join(job['delete_paths'])
    body += '\n\nDisconnect with clean logs, then reply with a contract delivery. Recovery jobs require the readable objective file attached from your local drive. Deletion receipts and clean-exit proof are verified automatically. Attachments do not remove your local copy.'
    return incoming(slot, BROKER, f'Briefing // {code} // {job["title"]}', body, kind='briefing', assignment=assignment)


def open_case(slot, target, amount, reason):
    case = EnforcementCase.objects.create(slot=slot, target=target, amount=amount)
    incoming(slot, AGENCY, f'Trace identified // case {case.reference}',
             f'SIGNAL INTELLIGENCE BUREAU\n\n{reason}\nYour gateway was identified at {target}. Your reputation has fallen by 60 (floor zero).'
             f'\n\nSettlement required: {amount} CPH\nBeneficiary: Meridian Legal Services\nAccount: {LEGAL_ACCOUNT}\nCase reference: {case.reference}'
             '\n\nMake the exact payment from your current account through Cipher Bank, quoting this case reference. Then reply to this notice with a settlement confirmation. We verify the bank receipt; a message alone is not payment.'
             '\n\nNew contract reservations are suspended until all cases are paid and confirmed. Existing accepted work remains available to earn funds. There is no deadline, compounding fee or offline escalation.', kind='enforcement', case=case)
    return case


def cases(slot):
    return [dict(id=row.pk, reference=str(row.reference), target=row.target, amount=row.amount, status=row.status,
                 payment_reference=str(row.payment_reference) if row.payment_reference else None,
                 account=LEGAL_ACCOUNT) for row in slot.enforcement_cases.exclude(status='closed').order_by('id')]


def pay_case(slot, reference, recipient, amount):
    from .mechanics import transact
    try:
        reference = UUID(str(reference))
    except (ValueError, TypeError, AttributeError):
        raise GameError('Enter the case reference from your agency email.')
    case = slot.enforcement_cases.filter(reference=reference).first()
    if not case:
        raise GameError('Case not found in this save.')
    if recipient != LEGAL_ACCOUNT or type(amount) is not int or amount != case.amount:
        raise GameError('The beneficiary account and exact amount must match the agency notice.')
    if case.status != 'unpaid':
        return 'Settlement already transferred. No additional funds moved. Confirm by replying to the agency email.'
    receipt = uuid4()
    transact(slot, -amount, f'Meridian Legal settlement // {case.reference}', reference=receipt)
    case.status, case.payment_reference, case.paid_at = 'paid', receipt, timezone.now()
    case.save()
    incoming(slot, 'receipts@cipher.internal', 'Settlement transfer receipt',
             f'{amount} CPH transferred to {LEGAL_ACCOUNT}.\nCase: {case.reference}\nBank reference: {receipt}\n\nReply to your Signal Intelligence Bureau notice to confirm settlement and close the case.', kind='bank_receipt', case=case)
    return f'{amount} CPH transferred. Reply to the agency notice in Email to close the case.'


def serialize(message):
    return dict(id=message.pk, folder=message.folder, sender=message.sender, recipient=message.recipient,
                subject=message.subject, body=message.body, kind=message.kind, read=message.read,
                assignment_id=message.assignment_id, case_id=message.case_id, reply_to=message.reply_to_id,
                attachments=message.attachments, created_at=message.created_at)


def send(slot, data):
    from .assignments import focus, complete
    try:
        request_id = UUID(str(data.get('request_id')))
    except (ValueError, TypeError, AttributeError):
        raise GameError('A valid mail request reference is required.')
    old = slot.mail.filter(request_id=request_id).first()
    if old:
        old_ids = [item['id'] for item in old.attachments if 'id' in item]
        if (old.recipient, old.subject, old.body, old.reply_to_id, old.kind, old_ids) != (data.get('recipient'), data.get('subject').strip() if isinstance(data.get('subject'), str) else None, data.get('body').strip() if isinstance(data.get('body'), str) else None, data.get('reply_to'), data.get('intent', 'message'), data.get('attachments', [])):
            raise GameError('This mail request reference was already used for different instructions.')
        return 'Message already sent. No duplicate payment or delivery was made.'
    recipient, subject, body = data.get('recipient'), data.get('subject'), data.get('body')
    for label, value, limit in [('Recipient', recipient, 100), ('Subject', subject, 180), ('Message', body, 10000)]:
        if not isinstance(value, str) or not value.strip() or len(value) > limit or '\x00' in value:
            raise GameError(f'{label} must contain 1–{limit} characters.')
    if recipient not in (BROKER, AGENCY, address(slot)):
        raise GameError('Use an in-game contact: broker, agency or your own mailbox. No external email is sent.')
    reply = data.get('reply_to')
    if reply is not None and type(reply) is not int:
        raise GameError('Choose a valid message to reply to.')
    parent = slot.mail.filter(pk=reply, folder='inbox').first() if reply else None
    if reply and not parent:
        raise GameError('Reply message not found in this save.')
    ids = data.get('attachments', [])
    if not isinstance(ids, list) or len(ids) > 10 or any(not isinstance(item, str) for item in ids) or len(ids) != len(set(ids)):
        raise GameError('Choose up to ten distinct files from your local drive.')
    files = {entry['id']: entry for entry in slot.local_files}
    if any(item not in files for item in ids):
        raise GameError('An attached file is no longer present on your local drive.')
    action = data.get('intent', 'message')
    if action not in ('message', 'deliver', 'confirm'):
        raise GameError('Choose message, contract delivery or settlement confirmation.')
    if action == 'deliver' and (not parent or not parent.assignment_id or recipient != BROKER):
        raise GameError('Reply to the appropriate broker briefing to submit a contract.')
    if action == 'confirm' and (not parent or not parent.case_id or recipient != AGENCY or parent.sender != AGENCY):
        raise GameError('Reply to the agency notice to confirm settlement.')
    # Validate before changing focus or persisting a sent message.
    if action == 'deliver' and slot.mission_started:
        raise GameError('Cannot deliver evidence while connected to the target.')
    attachment_copies = [{key: entry.get(key) for key in ('id', 'name', 'size', 'source', 'source_path', 'revision', 'encrypted')} for entry in (files[item] for item in ids)]
    if action == 'deliver' and parent.assignment.descriptor.get('objective') == 'delete':
        state = slot.mission_state if slot.active_contract == parent.assignment.key else parent.assignment.state
        attachment_copies.append(dict(name='deletion-receipts.json', receipts=state.get('deletion_receipts', []), deleted=bool(state.get('deleted')), clean_exit=bool(state.get('clean_exit'))))
    sent = MailMessage.objects.create(slot=slot, folder='sent', sender=address(slot), recipient=recipient,
                                      subject=subject.strip(), body=body.strip(), attachments=attachment_copies,
                                      assignment=parent.assignment if parent else None, case=parent.case if parent else None,
                                      reply_to=parent, request_id=request_id, read=True, kind=action)
    result = 'Message sent.'
    if action == 'deliver':
        if parent.assignment.status != 'accepted':
            result = 'This assignment is already closed. No additional payment was made.'
        else:
            focus(slot, parent.assignment.key)
            try:
                result = complete(slot, ids)
            except GameError as failure:
                result = str(failure)
        incoming(slot, BROKER, 'Re: ' + parent.subject, result, kind='broker_reply', assignment=parent.assignment, reply_to=sent)
    elif action == 'confirm':
        case = parent.case
        if case.status == 'unpaid':
            result = 'Confirmation rejected: no matching Cipher Bank settlement transfer exists. Pay the exact amount first.'
        elif case.status == 'paid' and not slot.ledger.filter(reference=case.payment_reference, amount=-case.amount, account='current').exists():
            result = 'Confirmation rejected: bank receipt could not be verified.'
        elif case.status == 'closed':
            result = 'This case is already closed.'
        else:
            case.status, case.closed_at = 'closed', timezone.now(); case.save()
            result = f'Case {case.reference} closed. Your bank receipt was verified. Contract access resumes when no other cases remain open.'
        incoming(slot, AGENCY, 'Re: ' + parent.subject, result, kind='agency_reply', case=case, reply_to=sent)
    elif recipient == address(slot):
        incoming(slot, address(slot), subject.strip(), body.strip(), attachments=attachment_copies, reply_to=sent)
    return result


def terminal_submit(slot):
    from .assignments import ensure_legacy
    ensure_legacy(slot)
    assignment = slot.assignments.filter(key=slot.active_contract, status='accepted').first()
    if not assignment:
        raise GameError('No reserved contract to submit.')
    parent = assignment.mail.filter(kind='briefing').first()
    file_id = slot.mission_state.get('local_file_id')
    return send(slot, dict(request_id=str(uuid4()), recipient=BROKER, subject='Re: ' + parent.subject[:176],
                           body='Contract work complete. Please verify the attached evidence.', intent='deliver', reply_to=parent.pk,
                           attachments=[file_id] if any(entry['id'] == file_id for entry in slot.local_files) else []))
