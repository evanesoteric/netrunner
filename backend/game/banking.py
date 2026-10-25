"""Server-authoritative fictional banking. Call changes under the SaveSlot lock."""
from uuid import UUID, uuid4
from django.utils import timezone
from .models import BankAction
from .mechanics import GameError, transact

PAGE_SIZE = 25
MAX_CPH = 2_000_000_000


def summary(slot):
    from .mailbox import cases
    notices = cases(slot)
    due = sum(row['amount'] for row in notices if row['status'] == 'unpaid')
    return dict(enforcement_cases=notices, enforcement_due=due, identity=slot.created_at.isoformat(), current_balance=slot.balance, reserve_balance=slot.reserve_balance,
                loan_balance=slot.loan_balance, loan_principal=slot.loan_principal, loan_fee=slot.loan_fee,
                loan_started_at=slot.loan_started_at, loan_limit=1000 + slot.rank * 750, minimum_loan=100,
                fee_percent=5, net_worth=slot.balance + slot.reserve_balance - slot.loan_balance - due)


def history(slot, page=1, snapshot=None, page_size=PAGE_SIZE):
    if type(page) is not int or page < 1:
        raise GameError('Choose a positive history page number.')
    latest = slot.ledger.values_list('id', flat=True).first() or 0
    if snapshot is None:
        snapshot = latest
    if type(snapshot) is not int or snapshot < 0 or snapshot > latest:
        raise GameError('Invalid ledger snapshot. Refresh the transaction history.')
    query = slot.ledger.filter(id__lte=snapshot)
    total = query.count()
    pages = max(1, (total + page_size - 1) // page_size)
    if page > pages:
        raise GameError(f'History has {pages} pages.')
    entries = list(query.values('id', 'amount', 'description', 'created_at', 'account', 'balance_after', 'reference')[(page-1)*page_size:page*page_size])
    return dict(entries=entries, page=page, pages=pages, total=total, page_size=page_size,
                snapshot=snapshot, latest_id=latest, has_newer=latest > snapshot)


def positive_amount(value):
    if type(value) is not int or not 1 <= value <= MAX_CPH:
        raise GameError('Enter a positive whole CPH amount up to 2,000,000,000.')
    return value


def perform(slot, action, amount, request_id=None, *, case_reference=None, recipient=None):
    amount = positive_amount(amount)
    if action not in ('loan', 'repay', 'deposit', 'withdraw', 'settle'):
        raise GameError('Choose loan, repay, deposit or withdraw.')
    try:
        reference = UUID(str(request_id)) if request_id is not None else uuid4()
    except (ValueError, TypeError, AttributeError):
        raise GameError('A valid transaction reference is required.')
    context = str(case_reference or '') if action == 'settle' else ''
    previous = slot.bank_actions.filter(request_id=reference).first()
    if previous:
        if previous.action != action or previous.amount != amount or previous.context != context:
            raise GameError('This transaction reference was already used for different instructions.')
        return 'Transaction already processed. No funds moved again.'
    if action == 'settle':
        from .mailbox import pay_case
        result = pay_case(slot, case_reference, recipient, amount)
    elif action == 'loan':
        if slot.loan_balance:
            raise GameError('Repay your existing loan before taking another.')
        if not 100 <= amount <= 1000 + slot.rank * 750:
            raise GameError(f'Loan principal must be 100–{1000 + slot.rank * 750} CPH at your current rank.')
        fee = (amount * 5 + 99) // 100
        transact(slot, amount, f'Bank loan // {amount} CPH principal', reference=reference)
        transact(slot, amount + fee, f'Loan opened // {amount} principal + {fee} fixed fee', account='loan', reference=reference)
        slot.loan_principal, slot.loan_fee, slot.loan_started_at = amount, fee, timezone.now()
        result = f'Loan funded: {amount:,} CPH. Fixed fee: {fee:,} CPH. Total to repay: {amount + fee:,} CPH. No compounding or automatic charges.'
    elif action == 'repay':
        if not slot.loan_balance:
            raise GameError('There is no outstanding loan.')
        if amount > slot.loan_balance:
            raise GameError(f'You owe {slot.loan_balance:,} CPH. Overpayments are not accepted.')
        transact(slot, -amount, 'Loan repayment // current account', reference=reference)
        transact(slot, -amount, 'Loan repayment // debt reduced', account='loan', reference=reference)
        if not slot.loan_balance:
            slot.loan_principal, slot.loan_fee, slot.loan_started_at = 0, 0, None
        result = f'Loan repayment received: {amount:,} CPH. Outstanding: {slot.loan_balance:,} CPH.'
    elif action == 'deposit':
        if slot.reserve_balance + amount > MAX_CPH:
            raise GameError('Reserve account balance limit exceeded.')
        transact(slot, -amount, 'Transfer to reserve // current account', reference=reference)
        transact(slot, amount, 'Transfer from current // reserve account', account='reserve', reference=reference)
        result = f'Transferred {amount:,} CPH to reserve.'
    else:
        if slot.balance + amount > MAX_CPH:
            raise GameError('Current account balance limit exceeded.')
        transact(slot, -amount, 'Transfer to current // reserve account', account='reserve', reference=reference)
        transact(slot, amount, 'Transfer from reserve // current account', reference=reference)
        result = f'Transferred {amount:,} CPH to current.'
    BankAction.objects.create(slot=slot, request_id=reference, action=action, amount=amount, context=context)
    return result


def bank_command(slot, verb, args):
    if verb in ('balance', 'accounts') and not args:
        return f'CIPHER CURRENT ACCOUNT // {slot.alias}\nAvailable: {slot.balance:,} CPH\nReserve: {slot.reserve_balance:,} CPH\nLoan outstanding: {slot.loan_balance:,} CPH'
    if verb == 'history' and len(args) <= 1:
        if args and (not args[0].isdecimal() or len(args[0]) > 9):
            raise GameError('Use history [positive-page-number].')
        data = history(slot, int(args[0]) if args else 1, page_size=15)
        lines = [f'{entry["created_at"]:%Y-%m-%d %H:%M} UTC  {entry["account"].upper()}  {entry["amount"]:+} CPH  {entry["description"]}' for entry in data['entries']]
        return f'Page {data["page"]}/{data["pages"]} · {data["total"]} transactions\n' + ('\n'.join(lines) or 'No transactions.')
    if verb == 'loan' and not args:
        offer = summary(slot)
        return f'Loan limit: {offer["loan_limit"]:,} CPH. Minimum: 100 CPH. One active loan. Fixed fee: 5% rounded up once; no compounding, due date or automatic repayment. Outstanding: {slot.loan_balance:,} CPH.'
    if verb in ('loan', 'repay', 'deposit', 'withdraw') and len(args) == 1:
        if not args[0].isdecimal() or len(args[0]) > 10:
            raise GameError('Enter a positive whole CPH amount.')
        return perform(slot, verb, int(args[0]))
    return 'Unknown bank command. Read help for the bank manual.'
