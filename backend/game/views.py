import json
from functools import wraps
from datetime import timedelta
from django.utils.dateparse import parse_datetime
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from .contracts import codes, public_job
from .world import all_contracts, get_contract, all_servers
from .models import SaveSlot, LedgerEntry
from .persistence import current_target
from .services import service_name
from .catalog import CURRENCY, RANKS, THRESHOLDS, PRODUCTS, BUILTIN_APPS, HOME_NODE
from .mechanics import GameError, hardware, ram_used, route_stats, available_at, trace_remaining, settle, launch, trade, validate_route, execute, edit_directory, reserve, fail, storage_used, monitor_tool, select_applet

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

def deletion_progress(slot, job):
    if not job or not job.get('delete_paths'):
        return []
    from .deletion import required_paths, missing_deletions
    server = slot.server_states.filter(address=job['target']).first()
    files = server.files if server else []
    missing = missing_deletions(job, files, slot.mission_state.get('deletion_receipts', []))
    return [dict(path='/' + path, deleted=path not in missing) for path in required_paths(job, files)]


def serialize(slot, detailed=False):
    from .exploits import inventory
    mapping = codes(slot)
    servers = all_servers(slot)
    monitor = monitor_tool(slot)
    job = get_contract(slot.active_contract, slot)
    target = current_target(slot)
    tracing = trace_remaining(slot)
    started = slot.mission_state.get('trace_started', slot.mission_started.isoformat() if slot.mission_started else None) if tracing is not None else None
    remaining = tracing if monitor and target and monitor['power'] >= target['security'] else None
    data = {
        'id': slot.id, 'position': slot.position, 'alias': slot.alias, 'created_at': slot.created_at,
        'balance': slot.balance, 'reputation': slot.reputation, 'rank': slot.rank,
        'rank_name': RANKS[slot.rank],
        'next_rank_at': THRESHOLDS[slot.rank + 1] if slot.rank + 1 < len(RANKS) else None,
        'rank_floor': THRESHOLDS[slot.rank], 'completed': slot.completed,
        'active_contract': public_job(job, mapping),
        'deletion_progress': deletion_progress(slot, job),
        'broker_next_at': min((entry['due_at'] for entry in slot.broker_pending), default=None),
        'connected': bool(slot.mission_started),
        'authenticated': bool(slot.mission_started and slot.mission_state.get('access')),
        'trace_active': tracing is not None,
        'trace_started_at': started,
        'trace_deadline': (parse_datetime(started) + timedelta(seconds=slot.mission_state.get('trace_budget', 0) - slot.mission_state.get('work', 0))).isoformat() if started and remaining is not None else None,
        'password_break': slot.mission_state.get('password_break') if slot.mission_started else None,
        'password_result': slot.mission_state.get('password_result') if slot.mission_started else None,
        'login_service': {'port': target['port'], 'security': target['security'], 'name': service_name(target)} if target and slot.mission_started and slot.mission_state.get('scanned') and slot.mission_state.get('scanned_host') == target['target'] and slot.mission_state.get('scanned_revision', 1) == target.get('server_revision', 1) else None,
        'remote_cwd': slot.mission_state.get('cwd', '/') if slot.mission_started and slot.mission_state.get('access') else None,
        'remote_entries': slot.mission_state.get('known_paths', []) if slot.mission_started and slot.mission_state.get('access') else [],
        'remote_target': target['target'] if target and slot.mission_started else None,
        'stealth_session': bool(slot.remote_host.get('_backdoor')),
        'remote_node': {key: target[key] for key in ('target', 'x', 'y')} if target and slot.mission_started else None,
        'market_unlocked': slot.market_unlocked,
        'mission_log': slot.mission_log,
        'trace_remaining': remaining,
        'trace_monitor_product': monitor['id'] if monitor else None,
        'cracker_product': slot.mission_state.get('password_tool') or slot.applet_preferences.get('cracker'),
        'trace_budget': slot.mission_state.get('trace_budget') if remaining is not None else None,
        'server_time': timezone.now().isoformat(),
    }
    if detailed:
        contracts = []
        from .broker import offered_jobs
        for job in offered_jobs(slot):
            if abs(job['rank'] - slot.rank) <= 1:
                ready = available_at(slot, job['id'])
                contracts.append({**public_job(job, mapping), 'available_at': ready.isoformat() if ready else None})
        data.update({
            'contracts': contracts,
            'workspace_layout': slot.workspace_layout,
            'workspace_revision': slot.workspace_revision,
            'equipment': hardware(slot),
            'local_files': slot.local_files,
            'exploits': inventory(slot),
            'applet_preferences': slot.applet_preferences,
            'storage_used': storage_used(slot),
            'owned_hardware': slot.owned_hardware,
            'installed_software': slot.installed_software,
            'running_apps': [{
                'id': key, 'product_id': value,
                'name': BUILTIN_APPS[value]['name'] if value in BUILTIN_APPS else PRODUCTS[value]['name'],
                'ram': BUILTIN_APPS[value]['ram'] if value in BUILTIN_APPS else PRODUCTS[value]['ram'],
                'console': BUILTIN_APPS[value]['console'] if value in BUILTIN_APPS else key != 'cracker',
            } for key, value in slot.running_apps.items()],
            'ram_used': ram_used(slot),
            'catalog': [item for item in PRODUCTS.values() if not item.get('black_market') or item['id'] in slot.installed_software],
            'black_market_catalog': [item for item in PRODUCTS.values() if item.get('black_market')] if slot.market_unlocked else [],
            'backdoors': [{key: value for key, value in entry.items() if key in {'target', 'name', 'title', 'rank', 'server_id', 'security', 'port'}} for entry in slot.backdoors] if 'rootkit-epic' in slot.installed_software else [],
            'ransomware_ops': slot.ransomware_ops,
            'builtins': list(BUILTIN_APPS.values()), 'relays': [server for server in servers if server['id'] in slot.atlas_nodes], 'network_directory': servers, 'atlas_nodes': slot.atlas_nodes, 'home_node': HOME_NODE,
            'proxy_route': slot.proxy_route, 'route_stats': route_stats(slot),
            'ledger': list(slot.ledger.values('id', 'amount', 'description', 'created_at')[:30]),
        })
    return data

@ensure_csrf_cookie
@api(['GET'], authenticated=False)
def session(request):
    return JsonResponse({'user': {'username': request.user.username} if request.user.is_authenticated else None, 'currency': CURRENCY, 'ranks': RANKS, 'version': '0.18.0', 'server_time': timezone.now().isoformat()})

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
def password_breaker(request, slot_id):
    from .passwords import start_break, cancel_break, login_target
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    settle(slot)
    action = request.data.get('action')
    if action == 'start':
        start_break(slot, product_id=request.data.get('product_id'))
    elif action == 'cancel':
        cancel_break(slot)
    elif action == 'login':
        launch(slot, 'terminal')
        login_target(slot)
    else:
        raise GameError('Choose start, cancel, or login.')
    slot.save()
    return JsonResponse(serialize(slot, True))


@api(['POST'])
@transaction.atomic
def applets(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    settle(slot)
    select_applet(slot, text_field(request.data, 'product_id', 80))
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
        if app == 'terminal':
            from .passwords import cancel_break
            cancel_break(slot)
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
    for field in ['balance', 'reputation', 'completed', 'equipment', 'owned_hardware', 'installed_software', 'running_apps', 'proxy_route', 'atlas_nodes', 'active_contract', 'mission_started', 'mission_state', 'local_files', 'exploit_inventory', 'irc_messages', 'irc_state', 'applet_preferences', 'broker_jobs', 'broker_consumed', 'broker_pending', 'broker_codes', 'mission_log', 'contract_cooldowns', 'backdoors', 'ransomware_ops', 'remote_host', 'market_unlocked', 'field_notes', 'notes_revision', 'notes_updated_at', 'workspace_layout', 'workspace_revision']:
        setattr(slot, field, getattr(fresh, field))
    slot.created_at = timezone.now()
    slot.save()
    slot.ledger.all().delete()
    slot.server_states.all().delete()
    LedgerEntry.objects.create(slot=slot, amount=1200, description='Restarted runner // initial funding')
    return JsonResponse(serialize(slot, True))


@api(['POST'])
def legacy_action(request, slot_id):
    SaveSlot.objects.get(pk=slot_id, user=request.user)
    return JsonResponse({'error': 'This v0.1 action has been retired. Reserve contracts in the local terminal; manage individual products in the exchange.'}, status=410)


@api(['POST'])
@transaction.atomic
def contract_action(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    settle(slot)
    code = text_field(request.data, 'contract_id', 3)
    action = request.data.get('action')
    if action == 'accept':
        reserve(slot, code)
    elif action == 'abort':
        current = get_contract(slot.active_contract, slot)
        if not current or public_job(current, codes(slot))['id'] != code:
            raise GameError('That assignment is no longer reserved. Refresh the broker.')
        fail(slot, 'Assignment abandoned.')
    else:
        raise GameError('Choose accept or abort.')
    slot.save()
    return JsonResponse(serialize(slot, True))


@api(['POST'])
@transaction.atomic
def backdoor_connect(request, slot_id):
    from .operations import connect_target
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    settle(slot)
    target = text_field(request.data, 'target', 100)
    launch(slot, 'terminal')
    message = connect_target(slot, target, backdoor=True)
    from .mechanics import log
    log(slot, 'terminal', message)
    slot.save()
    return JsonResponse(serialize(slot, True))


def note_data(slot):
    return {'text': slot.field_notes, 'revision': slot.notes_revision,
            'updated_at': slot.notes_updated_at, 'identity': slot.created_at.isoformat()}


@api(['GET', 'POST'])
@transaction.atomic
def field_notes(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    if request.method == 'GET':
        return JsonResponse(note_data(slot))
    if request.data.get('identity') != slot.created_at.isoformat():
        return JsonResponse({'error': 'This save was restarted or replaced. Its previous draft cannot overwrite the new notes.', 'note': note_data(slot)}, status=409)
    text = request.data.get('text')
    revision = request.data.get('revision')
    if not isinstance(text, str) or len(text) > 50000 or '\x00' in text:
        raise GameError('Notes must contain at most 50,000 characters and no null characters.')
    if type(revision) is not int or revision < 0:
        raise GameError('A valid notes revision is required.')
    if revision != slot.notes_revision and text != slot.field_notes:
        return JsonResponse({'error': 'Newer notes were saved in another window. Your draft has not overwritten them.', 'note': note_data(slot)}, status=409)
    if text != slot.field_notes:
        slot.field_notes = text
        slot.notes_revision += 1
        slot.notes_updated_at = timezone.now()
        slot.save(update_fields=['field_notes', 'notes_revision', 'notes_updated_at'])
    return JsonResponse(note_data(slot))


@api(['GET'])
@transaction.atomic
def server_history(request, slot_id):
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    settle(slot)
    servers = list(slot.server_states.all())
    summaries = [dict(address=server.address, name=server.descriptor.get('name') or server.descriptor.get('title') or server.address,
                      revision=server.revision, visits=server.visits, last_visit=server.last_visit,
                      observed=server.observed, remote_log_count=len(server.remote_logs),
                      backdoor_installed=server.backdoor_installed, maintenance_due=server.maintenance_due)
                 for server in servers]
    address = request.GET.get('server')
    events = []
    next_before = None
    if address:
        server = next((server for server in servers if server.address == address), None)
        if not server:
            return JsonResponse({'error': 'No history for this server in this save.'}, status=404)
        query = server.events.all()
        before = request.GET.get('before')
        if before:
            if not before.isdecimal() or len(before) > 18:
                raise GameError('Invalid history cursor.')
            query = query.filter(id__lt=int(before))
        rows = list(query[:51])
        events = [dict(id=row.id, kind=row.kind, summary=row.summary, created_at=row.created_at) for row in rows[:50]]
        if len(rows) > 50:
            next_before = rows[49].id
    return JsonResponse({'servers': summaries, 'events': events, 'next_before': next_before, 'server_time': timezone.now().isoformat()})



def workspace_data(slot):
    from .workspace import default_workspace
    return {'starter_layout': default_workspace(), 'layout': slot.workspace_layout, 'revision': slot.workspace_revision, 'identity': slot.created_at.isoformat()}


@api(['GET', 'POST'])
@transaction.atomic
def workspace(request, slot_id):
    from .workspace import validate_workspace
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    if request.method == 'GET':
        return JsonResponse(workspace_data(slot))
    if request.data.get('identity') != slot.created_at.isoformat():
        return JsonResponse({'error': 'This runner was restarted. Its old arrangement cannot overwrite the new workspace.', 'workspace': workspace_data(slot)}, status=409)
    layout = validate_workspace(request.data.get('layout'))
    revision = request.data.get('revision')
    if type(revision) is not int or revision < 0:
        raise GameError('A valid workspace revision is required.')
    if revision != slot.workspace_revision and layout != slot.workspace_layout:
        return JsonResponse({'error': 'Another window saved a newer arrangement. Your layout has been retained for review.', 'workspace': workspace_data(slot)}, status=409)
    if layout != slot.workspace_layout:
        slot.workspace_layout = layout
        slot.workspace_revision += 1
        slot.save(update_fields=['workspace_layout', 'workspace_revision'])
    return JsonResponse(workspace_data(slot))


@api(['GET', 'POST'])
@transaction.atomic
def irc(request, slot_id):
    from .exploits import channel_data, irc_command
    slot = SaveSlot.objects.select_for_update().get(pk=slot_id, user=request.user)
    settle(slot)
    if request.method == 'POST':
        irc_command(slot, text_field(request.data, 'command', 240))
        slot.save()
    return JsonResponse({'irc': channel_data(slot), 'slot': serialize(slot, True)})
