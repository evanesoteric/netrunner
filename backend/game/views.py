import json
from functools import wraps
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import SaveSlot, LedgerEntry
from .catalog import CONTRACTS, CURRENCY, RANKS, THRESHOLDS, UPGRADES

class GameError(Exception):
    pass

def api(methods, authenticated=True):
    def decorate(fn):
        @wraps(fn)
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                return JsonResponse({'error': 'Method not allowed.'}, status=405)
            if authenticated and not request.user.is_authenticated:
                return JsonResponse({'error': 'Authenticate to access this terminal.'}, status=401)
            try:
                request.data = json.loads(request.body or b'{}') if request.method == 'POST' else {}
                if not isinstance(request.data, dict):
                    raise GameError('Expected a JSON object.')
                return fn(request, *args, **kwargs)
            except (GameError, ValidationError) as exc:
                return JsonResponse({'error': ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc)}, status=400)
            except (ValueError, TypeError, UnicodeDecodeError):
                return JsonResponse({'error': 'Invalid request data.'}, status=400)
            except SaveSlot.DoesNotExist:
                return JsonResponse({'error': 'Save slot not found.'}, status=404)
        return wrapped
    return decorate

def text_field(data, key, maximum):
    value = data.get(key, '')
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise GameError(f'{key.capitalize()} must contain 1–{maximum} characters.')
    return value.strip()

def catalog_contract(contract_id):
    return next((c for c in CONTRACTS if c['id'] == contract_id), None)

def serialize(slot, detailed=False):
    data = {'id': slot.id, 'position': slot.position, 'alias': slot.alias, 'balance': slot.balance, 'reputation': slot.reputation, 'rank': slot.rank, 'rank_name': RANKS[slot.rank], 'next_rank_at': THRESHOLDS[slot.rank+1] if slot.rank+1 < len(RANKS) else None, 'rank_floor': THRESHOLDS[slot.rank], 'hardware': slot.hardware, 'gateway': slot.gateway, 'software': slot.software, 'completed': slot.completed, 'active_contract': catalog_contract(slot.active_contract), 'mission_step': slot.mission_step, 'mission_log': slot.mission_log, 'mission_started': slot.mission_started.isoformat() if slot.mission_started else None}
    if detailed:
        data['contracts'] = [c for c in CONTRACTS if abs(c['rank'] - slot.rank) <= 1]
        data['ledger'] = list(slot.ledger.values('id', 'amount', 'description', 'created_at')[:30])
        data['upgrades'] = {key: {**value, 'level': getattr(slot, key), 'price': value['base_price'] * getattr(slot, key) ** 2, 'max_level': 5} for key, value in UPGRADES.items()}
    return data

@ensure_csrf_cookie
@api(['GET'], authenticated=False)
def session(request):
    return JsonResponse({'user': {'username': request.user.username} if request.user.is_authenticated else None, 'currency': CURRENCY, 'ranks': RANKS, 'server_time': timezone.now().isoformat()})

@api(['POST'], authenticated=False)
def register(request):
    username = text_field(request.data, 'username', 24)
    if not all(c.isalnum() or c in '_-' for c in username) or not username.isascii():
        raise GameError('Use letters, numbers, underscores, or hyphens for your handle.')
    password = request.data.get('password', '')
    if not isinstance(password, str) or len(password) > 128:
        raise GameError('Password must be at most 128 characters.')
    user = get_user_model()(username=username)
    validate_password(password, user)
    try:
        with transaction.atomic():
            user.set_password(password)
            user.save()
    except IntegrityError:
        raise GameError('This handle is already registered.')
    login(request, user)
    return JsonResponse({'username': username}, status=201)

@api(['POST'], authenticated=False)
def sign_in(request):
    username = text_field(request.data, 'username', 24)
    password = request.data.get('password', '')
    if not isinstance(password, str) or not password or len(password) > 128:
        raise GameError('Passphrase must contain 1–128 characters.')
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'error': 'Handle or passphrase not recognized.'}, status=401)
    login(request, user)
    return JsonResponse({'username': user.username})

@api(['POST'])
def sign_out(request):
    logout(request)
    return JsonResponse({'ok': True})

@api(['GET', 'POST'])
def slots(request):
    if request.method == 'GET':
        return JsonResponse({'slots': [serialize(s) for s in SaveSlot.objects.filter(user=request.user)]})
    position = request.data.get('position')
    if type(position) is not int or position not in (1, 2, 3):
        raise GameError('Choose save slot 1, 2, or 3.')
    alias = text_field(request.data, 'alias', 24)
    try:
        with transaction.atomic():
            slot = SaveSlot.objects.create(user=request.user, position=position, alias=alias)
            LedgerEntry.objects.create(slot=slot, amount=1200, description='New runner // initial funding')
    except IntegrityError:
        raise GameError('This save slot is already occupied.')
    return JsonResponse(serialize(slot, True), status=201)

@api(['GET'])
def slot_detail(request, slot_id):
    return JsonResponse(serialize(SaveSlot.objects.get(pk=slot_id, user=request.user), True))

@api(['POST'])
@transaction.atomic
def accept(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    if slot.active_contract:
        raise GameError('Finish or abort your active contract first.')
    contract = catalog_contract(request.data.get('contract_id'))
    if not contract or abs(contract['rank'] - slot.rank) > 1:
        raise GameError('Contract outside your rank clearance.')
    slot.active_contract = contract['id']
    slot.mission_started = timezone.now()
    slot.mission_step = 0
    slot.mission_log = [f"Connected to {contract['target']}. Trace window: 180 seconds.", 'Run help to inspect available commands.']
    slot.save()
    return JsonResponse(serialize(slot, True))

@api(['POST'])
@transaction.atomic
def command(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    contract = catalog_contract(slot.active_contract)
    if not contract:
        raise GameError('No active contract. Connect through the broker.')
    cmd = text_field(request.data, 'command', 100).lower()
    if cmd == 'abort' or (timezone.now() - slot.mission_started).total_seconds() >= 180:
        slot.reputation = max(0, slot.reputation - 60)
        slot.mission_log.append('Connection terminated. Contract failed. Reputation -60 (minimum 0).')
        slot.active_contract = ''
        slot.mission_started = None
    elif cmd == 'help':
        slot.mission_log.append('Sequence: scan → breach → extract → wipe → disconnect. Use abort to abandon (-60 reputation).')
    else:
        sequence = ['scan', 'breach', 'extract', 'wipe', 'disconnect']
        expected = sequence[slot.mission_step]
        if cmd != expected:
            slot.mission_log.append(f'Command rejected. Expected: {expected}. Use help for instructions.')
        elif cmd == 'breach' and slot.hardware + slot.gateway + slot.software < 3 + contract['rank'] * 2:
            slot.mission_log.append('Insufficient system power. Upgrade before connecting, or abort this contract.')
        else:
            responses = ['Network mapped. Entry point isolated.', 'Firewall bypassed. Remote shell established.', 'Archive extracted. Checksum verified.', 'Access logs erased. Your signature is clean.', f"Contract complete. +{contract['reward']} CPH / +{contract['reputation']} reputation."]
            slot.mission_log.append(f'> {cmd}\n{responses[slot.mission_step]}')
            slot.mission_step += 1
            if cmd == 'disconnect':
                slot.balance += contract['reward']
                slot.reputation += contract['reputation']
                slot.completed += 1
                LedgerEntry.objects.create(slot=slot, amount=contract['reward'], description=contract['title'])
                slot.active_contract = ''
                slot.mission_started = None
    slot.mission_log = slot.mission_log[-50:]
    slot.save()
    return JsonResponse(serialize(slot, True))

@api(['POST'])
@transaction.atomic
def upgrade(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    if slot.active_contract:
        raise GameError('Disconnect from your contract before changing equipment.')
    kind = request.data.get('kind')
    if not isinstance(kind, str) or kind not in UPGRADES:
        raise GameError('Unknown upgrade category.')
    level = getattr(slot, kind)
    if level >= 5:
        raise GameError('Maximum upgrade level reached.')
    price = UPGRADES[kind]['base_price'] * level ** 2
    if slot.balance < price:
        raise GameError('Insufficient funds.')
    slot.balance -= price
    setattr(slot, kind, level + 1)
    slot.save()
    LedgerEntry.objects.create(slot=slot, amount=-price, description=f"{UPGRADES[kind]['name']} upgraded to level {level+1}")
    return JsonResponse(serialize(slot, True))
