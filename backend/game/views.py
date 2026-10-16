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
from .catalog import CONTRACTS, CONTRACT_BY_ID, CURRENCY, RANKS, THRESHOLDS, PRODUCTS, BUILTIN_APPS, RELAYS, HOME_NODE
from .mechanics import GameError, hardware, ram_used, route_stats, available_at, trace_remaining, settle, launch, trade, validate_route, execute, edit_directory

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

def serialize(slot, detailed=False):
    monitor = PRODUCTS.get(slot.running_apps.get('monitor', ''))
    job = CONTRACT_BY_ID.get(slot.active_contract)
    remaining = trace_remaining(slot) if monitor and job and monitor['power'] >= job['security'] else None
    data = {
        'id': slot.id, 'position': slot.position, 'alias': slot.alias,
        'balance': slot.balance, 'reputation': slot.reputation, 'rank': slot.rank,
        'rank_name': RANKS[slot.rank],
        'next_rank_at': THRESHOLDS[slot.rank + 1] if slot.rank + 1 < len(RANKS) else None,
        'rank_floor': THRESHOLDS[slot.rank], 'completed': slot.completed,
        'active_contract': CONTRACT_BY_ID.get(slot.active_contract),
        'connected': bool(slot.mission_started),
        'mission_log': slot.mission_log,
        'trace_remaining': remaining if 'monitor' in slot.running_apps else None,
        'server_time': timezone.now().isoformat(),
    }
    if detailed:
        contracts = []
        for job in CONTRACTS:
            if abs(job['rank'] - slot.rank) <= 1:
                ready = available_at(slot, job['id'])
                contracts.append({**job, 'available_at': ready.isoformat() if ready else None})
        data.update({
            'contracts': contracts,
            'equipment': hardware(slot),
            'owned_hardware': slot.owned_hardware,
            'installed_software': slot.installed_software,
            'running_apps': [{
                'id': key, 'product_id': value,
                'name': BUILTIN_APPS[value]['name'] if value in BUILTIN_APPS else PRODUCTS[value]['name'],
                'ram': BUILTIN_APPS[value]['ram'] if value in BUILTIN_APPS else PRODUCTS[value]['ram'],
                'console': BUILTIN_APPS[value]['console'] if value in BUILTIN_APPS else True,
            } for key, value in slot.running_apps.items()],
            'ram_used': ram_used(slot), 'catalog': list(PRODUCTS.values()),
            'builtins': list(BUILTIN_APPS.values()), 'relays': [server for server in RELAYS if server['id'] in slot.atlas_nodes], 'network_directory': RELAYS, 'atlas_nodes': slot.atlas_nodes, 'home_node': HOME_NODE,
            'proxy_route': slot.proxy_route, 'route_stats': route_stats(slot),
            'ledger': list(slot.ledger.values('id', 'amount', 'description', 'created_at')[:30]),
        })
    return data

@ensure_csrf_cookie
@api(['GET'], authenticated=False)
def session(request):
    return JsonResponse({'user': {'username': request.user.username} if request.user.is_authenticated else None, 'currency': CURRENCY, 'ranks': RANKS, 'version': '0.3.1', 'server_time': timezone.now().isoformat()})

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
@transaction.atomic
def slots(request):
    if request.method == 'GET':
        saved = list(SaveSlot.objects.select_for_update().filter(user=request.user))
        for saved_slot in saved:
            settle(saved_slot)
        return JsonResponse({'slots': [serialize(saved_slot) for saved_slot in saved]})
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
@transaction.atomic
def slot_detail(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    settle(slot)
    return JsonResponse(serialize(slot, True))


@api(['POST'])
@transaction.atomic
def command(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    settle(slot)
    app = text_field(request.data, 'application', 24)
    raw = text_field(request.data, 'command', 160)
    execute(slot, app, raw)
    slot.save()
    return JsonResponse(serialize(slot, True))


@api(['POST'])
@transaction.atomic
def applications(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    settle(slot)
    action = request.data.get('action')
    if action == 'launch':
        launch(slot, request.data.get('product_id'))
    elif action == 'close':
        app = text_field(request.data, 'application', 24)
        if app not in slot.running_apps:
            raise GameError('Application is not running.')
        slot.running_apps = {key: value for key, value in slot.running_apps.items() if key != app}
    else:
        raise GameError('Choose launch or close.')
    slot.save()
    return JsonResponse(serialize(slot, True))


@api(['POST'])
@transaction.atomic
def loadout(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    settle(slot)
    trade(slot, request.data.get('action'), request.data.get('product_id'))
    slot.save()
    return JsonResponse(serialize(slot, True))


@api(['POST'])
@transaction.atomic
def route(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    settle(slot)
    nodes = request.data.get('nodes')
    validate_route(slot, nodes)
    slot.proxy_route = nodes
    slot.save()
    return JsonResponse(serialize(slot, True))


@api(['POST'])
@transaction.atomic
def directory(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    settle(slot)
    edit_directory(slot, request.data.get('action'), request.data.get('server_id'))
    slot.save()
    return JsonResponse(serialize(slot, True))


@api(['POST'])
@transaction.atomic
def restart(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    if request.data.get('confirmation') != slot.alias:
        raise GameError('Type the runner alias exactly to confirm restarting this slot.')
    fresh = SaveSlot(user=request.user, alias=slot.alias, position=slot.position)
    for field in ['balance', 'reputation', 'completed', 'equipment', 'owned_hardware', 'installed_software', 'running_apps', 'proxy_route', 'atlas_nodes', 'active_contract', 'mission_started', 'mission_state', 'mission_log', 'contract_cooldowns']:
        setattr(slot, field, getattr(fresh, field))
    slot.created_at = timezone.now()
    slot.save()
    slot.ledger.all().delete()
    LedgerEntry.objects.create(slot=slot, amount=1200, description='Restarted runner // initial funding')
    return JsonResponse(serialize(slot, True))


@api(['POST'])
def legacy_action(request, slot_id):
    SaveSlot.objects.get(pk=slot_id, user=request.user)
    return JsonResponse({'error': 'This v0.1 action has been retired. Reserve contracts in the local terminal; manage individual products in the exchange.'}, status=410)
