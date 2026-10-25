import json
from io import StringIO
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction, close_old_connections, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, Client, override_settings
from django.core.management import call_command, CommandError
from django.db.migrations.recorder import MigrationRecorder
from django.contrib.sessions.models import Session
from django.utils import timezone
from .contracts import public_code
from .models import SaveSlot, ContractIdentity
from .catalog import PRODUCTS, CONTRACT_BY_ID, RELAY_BY_ID, STARTER_EQUIPMENT


class APIHelpers:
    def post(self, route, data=None, status=200, client=None):
        response = (client or self.client).post(f'/api/{route}/', json.dumps({} if data is None else data), content_type='application/json')
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def endpoint(self, suffix):
        return f'slots/{self.slot.id}/{suffix}'

    def launch(self, product_id):
        if product_id in ['broker','bank','market']: return self.refresh()
        if product_id in PRODUCTS and PRODUCTS[product_id]['category'] == 'software':
            self.post(self.endpoint('applications'), {'action': 'launch', 'product_id': 'terminal'})
            return self.post(self.endpoint('applets'), {'product_id': product_id})
        return self.post(self.endpoint('applications'), {'action': 'launch', 'product_id': product_id})

    def cmd(self, command, app='terminal'):
        if app not in ['terminal', 'bank']: app = 'terminal'
        if command.startswith('accept ') and command[7:] in CONTRACT_BY_ID:
            command = 'accept ' + public_code(command[7:])
        response = self.post(self.endpoint('command'), {'application': app, 'command': command})
        # Existing gameplay scenarios wait for Lockpick; timing is exercised separately.
        if response.get('password_break') and command.startswith('crack '):
            slot = SaveSlot.objects.get(pk=self.slot.pk)
            slot.mission_state['password_break']['finishes_at'] = timezone.now().isoformat()
            slot.save()
            result = self.refresh()
            if result.get('password_result') == 'ready':
                return self.post(self.endpoint('password-breaker'), {'action': 'login'})
            return result
        return response

    def log_text(self, response):
        return '\n'.join(line['text'] for line in response['mission_log'])

    def refresh(self):
        return self.client.get(f'/api/slots/{self.slot.id}/').json()

    def reserve(self, job='0-0'):
        self.launch('terminal')
        return self.cmd(f'accept {job}')

    def scan_and_connect(self, job='0-0'):
        self.reserve(job)
        self.launch('mapper-1-standard')
        self.cmd(f'scan {CONTRACT_BY_ID[job]["target"]}', 'mapper')
        return self.cmd(f'connect {CONTRACT_BY_ID[job]["target"]}')

    def gain_access(self, job='0-0'):
        self.scan_and_connect(job)
        self.launch('cracker-1-standard')
        return self.cmd(f'crack {CONTRACT_BY_ID[job]["port"]}', 'cracker')

    def clean_exit(self):
        self.cmd('logcleaner')
        self.cmd('disconnect')


class AccountTests(APIHelpers, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('runner', password='test-passphrase-long')
        self.client.force_login(self.user)
        self.slot = SaveSlot.objects.create(user=self.user, position=1, alias='ghost')

    def test_registration_login_logout_and_password_validation(self):
        self.client.logout()
        self.post('register', {'username': 'new_runner', 'password': 'short'}, 400)
        self.post('register', {'username': 'new_runner', 'password': 'Nebula!72-private-key'}, 201)
        self.assertTrue(get_user_model().objects.get(username='new_runner').check_password('Nebula!72-private-key'))
        self.post('logout')
        self.post('login', {'username': 'new_runner', 'password': 'wrong'}, 401)
        self.post('login', {'username': 'new_runner', 'password': 'Nebula!72-private-key'})
        self.assertEqual(self.client.get('/api/session/').json()['user']['username'], 'new_runner')

    def test_csrf_and_development_origin(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get('/api/session/')
        self.assertIn('csrftoken', response.cookies)
        self.assertEqual(client.post('/api/login/', '{}', content_type='application/json').status_code, 403)
        response = client.post('/api/login/', json.dumps({'username': 'runner', 'password': 'test-passphrase-long'}), content_type='application/json', HTTP_ORIGIN='http://127.0.0.1:5173', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 200, response.content)

    def test_passphrase_whitespace_is_preserved(self):
        self.user.set_password(' a-special-passphrase-42 ')
        self.user.save()
        self.client.logout()
        self.post('login', {'username': 'runner', 'password': ' a-special-passphrase-42 '})

    def test_exactly_three_independent_slots(self):
        self.post('slots', {'position': 2, 'alias': 'echo'}, 201)
        self.post('slots', {'position': 3, 'alias': 'shade'}, 201)
        self.post('slots', {'position': 4, 'alias': 'overflow'}, 400)
        self.post('slots', {'position': 2, 'alias': 'duplicate'}, 400)
        self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': 'cpu-1-specialist'})
        self.assertEqual(SaveSlot.objects.get(user=self.user, position=2).balance, 1200)
        self.assertEqual(len(self.client.get('/api/slots/').json()['slots']), 3)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SaveSlot.objects.create(user=self.user, position=4, alias='invalid')

    def test_all_mutations_check_owner_and_authentication(self):
        other = get_user_model().objects.create_user('other')
        foreign = SaveSlot.objects.create(user=other, position=1, alias='private')
        self.assertEqual(self.client.get(f'/api/slots/{foreign.id}/').status_code, 404)
        for endpoint in ['applications', 'loadout', 'route', 'directory', 'command', 'restart', 'accept', 'upgrade']:
            self.post(f'slots/{foreign.id}/{endpoint}', {}, 404)
        self.client.logout()
        self.assertEqual(self.client.get('/api/slots/').status_code, 401)
        self.post(self.endpoint('restart'), {'confirmation': 'ghost'}, 401)

    def test_malformed_requests_do_not_change_state(self):
        for payload in [[], {'position': True, 'alias': 'bad'}, {'position': 2, 'alias': ['bad']}]:
            self.post('slots', payload, 400)
        self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': []}, 400)
        self.post(self.endpoint('applications'), {'action': 'launch', 'product_id': {}}, 400)
        self.post(self.endpoint('route'), {'nodes': ['london', {}]}, 400)
        self.assertEqual(self.refresh()['balance'], 1200)


class SimulationTests(APIHelpers, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('runner')
        self.client.force_login(self.user)
        self.slot = SaveSlot.objects.create(user=self.user, position=1, alias='ghost')

    def test_fresh_ghost_can_accept_every_contract_in_its_broker_listing(self):
        self.launch('terminal')
        listed = self.refresh()
        self.assertEqual(listed['rank_name'], 'Ghost')
        self.assertEqual({job['rank'] for job in listed['contracts']}, {0, 1})
        self.assertEqual(len(listed['contracts']), 27)
        for job in listed['contracts']:
            with self.subTest(contract_id=job['id']):
                SaveSlot.objects.filter(pk=self.slot.pk).update(active_contract='', mission_state={})
                result = self.cmd(f'accept {job["id"]}')
                self.assertIsNotNone(result['active_contract'], self.log_text(result))
                self.assertEqual(result['active_contract']['id'], job['id'])
                self.assertEqual(result['rank_name'], 'Ghost')

    def test_unknown_contract_id_is_not_reported_as_rank_denial(self):
        self.launch('terminal')
        result = self.cmd('accept 256')
        self.assertIsNone(result['active_contract'])
        self.assertIn('Unknown contract ID', self.log_text(result))
        self.assertNotIn('outside your rank', self.log_text(result))

    def test_target_address_and_security_class_are_not_rank_failures(self):
        self.launch('terminal')
        for value in ['helix-0.internal', '256', 'nonexistent']:
            with self.subTest(value=value):
                result = self.cmd(f'accept {value}')
                self.assertIsNone(result['active_contract'])
                self.assertIn('Unknown contract ID', result['mission_log'][-1]['text'])
                self.assertNotIn('rank clearance', result['mission_log'][-1]['text'])

    def test_codes_are_unique_eight_bit_and_persist_between_reads(self):
        first = self.refresh()['contracts']
        self.assertEqual(first, self.refresh()['contracts'])
        numbers = list(ContractIdentity.objects.values_list('code', flat=True))
        self.assertEqual(len(numbers), 63)
        self.assertEqual(len(set(numbers)), 63)
        self.assertTrue(all(0 <= number <= 255 for number in numbers))
        self.assertTrue(all(job['id'].isdigit() for job in first))

    def test_broker_actions_validate_current_assignment_and_cooldown(self):
        code = public_code('0-0')
        response = self.post(self.endpoint('contracts'), {'action': 'accept', 'contract_id': code})
        self.assertEqual(response['active_contract']['id'], code)
        self.assertFalse(response['connected'])
        self.post(self.endpoint('contracts'), {'action': 'accept', 'contract_id': code}, 400)
        self.post(self.endpoint('contracts'), {'action': 'abort', 'contract_id': public_code('0-1')}, 400)
        response = self.post(self.endpoint('contracts'), {'action': 'abort', 'contract_id': code})
        self.assertIsNone(response['active_contract'])
        self.assertEqual(response['balance'], 1110)
        self.post(self.endpoint('contracts'), {'action': 'abort', 'contract_id': code}, 400)
        self.post(self.endpoint('contracts'), {'action': 'accept', 'contract_id': code}, 400)
        self.post(self.endpoint('contracts'), {'action': 'accept', 'contract_id': public_code('2-0')}, 400)

    def test_genuinely_ineligible_job_reports_actual_rank_and_clearance(self):
        self.launch('terminal')
        result = self.cmd('accept 2-0')
        self.assertIsNone(result['active_contract'])
        self.assertIn('its rank is Operator', result['mission_log'][-1]['text'])
        self.assertIn('Ghost clearance covers Ghost through Signal', result['mission_log'][-1]['text'])

    def test_manual_reservation_does_not_connect_and_legacy_action_is_retired(self):
        self.post(self.endpoint('accept'), {'contract_id': '0-0'}, 410)
        response = self.reserve()
        self.assertEqual(response['active_contract']['id'], public_code('0-0'))
        self.assertFalse(response['connected'])
        self.assertEqual(response['balance'], 1200)
        self.assertNotIn('mission_step', response)
        self.assertNotIn('suggested', response)

    def test_command_requires_launch_and_correct_application_namespace(self):
        self.post(self.endpoint('command'), {'command': 'help', 'application': 'terminal'}, 400)
        self.reserve()
        response = self.cmd('scan helix-0.internal')
        self.assertIn('Scan complete', self.log_text(response))
        self.slot.refresh_from_db()
        self.assertTrue(self.slot.mission_state.get('scanned'))
        self.post(self.endpoint('applications'), {'action': 'launch', 'product_id': 'decryptor-5-standard'}, 400)

    def test_ram_limits_process_close_and_tool_variants(self):
        self.scan_and_connect()
        self.slot.refresh_from_db()
        self.slot.installed_software += ['cracker-5-standard', 'mapper-5-standard']
        self.slot.save()
        self.launch('cracker-5-standard')
        result = self.post(self.endpoint('password-breaker'), {'action':'start'})
        self.assertEqual(result['ram_used'], 9)
        self.launch('mapper-5-standard')
        self.assertIn('Not enough free RAM', self.cmd('scan helix-0.internal')['mission_log'][-1]['text'])
        result = self.post(self.endpoint('password-breaker'), {'action':'cancel'})
        self.assertEqual(result['ram_used'], 1)
        self.assertIn('Scan complete', self.cmd('scan helix-0.internal')['mission_log'][-1]['text'])

    def test_multiple_named_products_per_category_and_tier(self):
        self.assertEqual(len(PRODUCTS), 92)
        for category in ['cpu', 'gateway', 'memory', 'storage']:
            for tier in range(1, 6):
                self.assertEqual(len([p for p in PRODUCTS.values() if p['category'] == category and p['tier'] == tier]), 2)

    def test_rank_filter_and_terminal_reservation_enforcement(self):
        self.launch('terminal')
        for reputation, expected in [(0, {0, 1}), (100, {0, 1, 2}), (450, {2, 3, 4}), (700, {3, 4})]:
            SaveSlot.objects.filter(pk=self.slot.pk).update(reputation=reputation)
            self.assertEqual({c['rank'] for c in self.refresh()['contracts']}, expected)
        response = self.cmd('accept 0-0')
        self.assertIsNone(response['active_contract'])
        self.assertIn('outside your rank', self.log_text(response))

    def test_proxy_route_validation_order_latency_and_capacity(self):
        for nodes in [['london', 'london'], ['invented'], ['tokyo'], ['london', 'berlin', 'reykjavik', 'new-york']]:
            self.post(self.endpoint('route'), {'nodes': nodes}, 400)
        response = self.post(self.endpoint('route'), {'nodes': ['new-york', 'london', 'reykjavik']})
        first_latency = response['route_stats']['latency']
        response = self.post(self.endpoint('route'), {'nodes': ['london', 'new-york', 'reykjavik']})
        self.assertNotEqual(response['route_stats']['latency'], first_latency)
        self.assertEqual(response['proxy_route'], ['london', 'new-york', 'reykjavik'])

    def test_route_is_charged_on_connection_and_locked_while_connected(self):
        self.post(self.endpoint('route'), {'nodes': ['new-york', 'london']})
        response = self.scan_and_connect()
        self.assertEqual(response['balance'], 1200 - 2 - 8 - 5 - 6)
        self.assertTrue(response['connected'])
        self.post(self.endpoint('route'), {'nodes': []}, 400)
        self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': 'cpu-1-specialist'}, 400)

    def test_proxy_chain_increases_trace_budget(self):
        self.scan_and_connect()
        self.slot.refresh_from_db()
        direct = self.slot.mission_state['trace_budget']
        self.cmd('disconnect')
        self.post(self.endpoint('route'), {'nodes': ['reykjavik', 'london']})
        self.cmd('connect helix-0.internal')
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.mission_state['trace_budget'] - direct, RELAY_BY_ID['reykjavik']['delay'] + RELAY_BY_ID['london']['delay'])

    def test_plaintext_recovery_requires_manual_delivery_and_pays_once(self):
        self.slot.reputation = 90
        self.slot.save()
        self.gain_access()
        response = self.cmd('get research.dat')
        before_payment = response['balance']
        self.assertEqual(response['completed'], 0)
        self.assertIn('Copied research.dat', self.log_text(response))
        response = self.cmd('submit')
        self.assertEqual(response['completed'], 0)
        self.clean_exit()
        response = self.cmd('submit')
        self.assertEqual(response['balance'], before_payment - 2 + 220)
        self.assertEqual(response['rank'], 1)
        self.assertEqual(response['completed'], 1)
        self.cmd('submit')
        self.assertEqual(self.slot.ledger.filter(description=f'Contract payment // {public_code("0-0")}').count(), 1)

    def test_reading_after_cleaning_dirties_logs_and_fails_exit(self):
        self.gain_access()
        self.cmd('logcleaner')
        self.cmd('ls')
        response = self.cmd('disconnect')
        self.assertIsNone(response['active_contract'])
        self.assertIn('Forensics recovered', self.log_text(response))
        self.assertEqual(response['completed'], 0)

    def test_encrypted_archive_requires_separate_decryptor(self):
        self.gain_access('0-1')
        response = self.cmd('get ledger.enc')
        self.assertTrue(response['local_files'][0]['encrypted'])
        # End the session safely to buy a license; cracked files are preserved only in this game session.
        self.cmd('logcleaner')
        self.cmd('disconnect')
        self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': 'decryptor-1-standard'})
        self.launch('decryptor-1-standard')
        self.cmd('connect helix-1.internal')
        self.cmd('crack 443', 'cracker')
        response = self.cmd('decrypt ledger.enc', 'decryptor')
        self.assertIn('decrypted. Checksum intact', self.log_text(response))
        self.cmd('get ledger.enc')
        self.clean_exit()
        response = self.cmd('submit')
        self.assertEqual(response['completed'], 1)

    def test_deletion_contract_cannot_be_completed_by_copying_file(self):
        self.gain_access('0-2')
        self.cmd('get audit.log')
        self.clean_exit()
        response = self.cmd('submit')
        self.assertEqual(response['completed'], 0)
        self.cmd('connect helix-2.internal')
        self.cmd('crack 22', 'cracker')
        self.cmd('rm audit.log')
        self.clean_exit()
        self.assertEqual(self.cmd('submit')['completed'], 1)

    def test_underpowered_tool_fails_and_charges_compute_time(self):
        self.reserve('1-0')
        self.launch('mapper-1-standard')
        response = self.cmd('scan meridian-0.internal', 'mapper')
        self.assertEqual(response['balance'], 1198)
        self.assertIn('insufficient for security class 2', self.log_text(response))
        self.slot.refresh_from_db()
        self.assertFalse(self.slot.mission_state.get('scanned'))

    def test_bankruptcy_blocks_operations_without_negative_balance(self):
        self.reserve()
        SaveSlot.objects.filter(pk=self.slot.pk).update(balance=0)
        self.launch('mapper-1-standard')
        response = self.cmd('scan helix-0.internal', 'mapper')
        self.assertIn('Insufficient CPH', self.log_text(response))
        response = self.cmd('connect helix-0.internal')
        self.assertFalse(response['connected'])
        self.assertEqual(response['balance'], 0)

    def test_abort_lowers_rank_and_expired_jobs_settle_on_read_once(self):
        self.slot.reputation = 110
        self.slot.save()
        self.reserve()
        result = self.cmd('abort')
        self.assertEqual(result['rank'], 0)
        self.assertEqual(result['balance'], 1110)
        self.reserve('0-1')
        self.cmd('connect helix-1.internal')
        self.slot.refresh_from_db()
        self.slot.mission_state['trace_started'] = (timezone.now() - timedelta(seconds=500)).isoformat()
        self.slot.save()
        SaveSlot.objects.filter(pk=self.slot.pk).update(mission_started=timezone.now() - timedelta(seconds=500))
        first = self.refresh()
        self.assertIsNone(first['active_contract'])
        self.assertEqual(first['balance'], self.refresh()['balance'])
        self.assertEqual(self.slot.ledger.filter(description__startswith='Contract failure').count(), 2)

    def test_retired_job_never_returns_and_a_new_assignment_arrives(self):
        self.reserve()
        self.cmd('abort')
        result = self.cmd('accept 0-0')
        self.assertIsNone(result['active_contract'])
        self.assertIn('Unknown contract ID', result['mission_log'][-1]['text'])
        self.slot.refresh_from_db()
        self.slot.broker_pending[0]['due_at'] = (timezone.now()-timedelta(seconds=1)).isoformat()
        self.slot.save()
        offers = self.refresh()['contracts']
        self.assertNotIn('helix-0.internal', [job['target'] for job in offers])
        self.assertTrue(any(job['target'].startswith('broker-') for job in offers))

    def test_purchase_fit_sell_and_clearance(self):
        response = self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': 'gateway-1-specialist'})
        self.assertEqual(response['equipment']['gateway']['id'], 'gateway-1-standard')
        response = self.post(self.endpoint('loadout'), {'action': 'equip', 'product_id': 'gateway-1-specialist'})
        self.assertEqual(response['equipment']['gateway']['id'], 'gateway-1-specialist')
        self.post(self.endpoint('loadout'), {'action': 'sell', 'product_id': 'gateway-1-specialist'}, 400)
        response = self.post(self.endpoint('loadout'), {'action': 'sell', 'product_id': 'gateway-1-standard'})
        self.assertEqual(response['balance'], 1200 - PRODUCTS['gateway-1-specialist']['price'] + 140)
        self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': 'cpu-5-standard'}, 400)
        self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': 'gateway-1-specialist'}, 400)

    def test_owned_monitor_exposes_embedded_trace_without_a_process(self):
        self.gain_access()
        self.assertIsNone(self.refresh()['trace_remaining'])
        self.slot.refresh_from_db()
        self.slot.installed_software.append('monitor-1-standard')
        self.slot.save()
        result = self.launch('monitor-1-standard')
        self.assertGreater(result['trace_remaining'], 0)
        self.assertNotIn('monitor', [app['id'] for app in result['running_apps']])

    def test_monitor_must_decode_target_security(self):
        self.slot.installed_software.append('monitor-1-standard')
        self.slot.active_contract = '1-0'
        self.slot.mission_started = timezone.now()
        self.slot.mission_state = {'trace_budget': 130}
        self.slot.save()
        self.launch('monitor-1-standard')
        self.assertIsNone(self.refresh()['trace_remaining'])
        result = self.cmd('trace', 'monitor')
        self.assertIn('Trace encrypted', self.log_text(result))

    def test_running_processes_prevent_fitting_smaller_memory(self):
        self.slot.equipment['memory'] = 'memory-2-standard'
        self.slot.owned_hardware.append('memory-2-standard')
        self.slot.installed_software.append('decryptor-1-standard')
        self.slot.save()
        for product in ['terminal', 'atlas', 'mapper-1-standard', 'cracker-1-standard', 'decryptor-1-standard']:
            self.launch(product)
        self.post(self.endpoint('loadout'), {'action': 'equip', 'product_id': 'memory-1-standard'})
        result = self.post(self.endpoint('loadout'), {'action': 'equip', 'product_id': 'memory-1-standard'})
        self.assertEqual(result['equipment']['memory']['ram'], 12)

    def test_disk_capacity_can_block_recovery(self):
        self.slot.active_contract = '4-1'
        self.slot.mission_started = timezone.now()
        self.slot.mission_state = {'trace_budget': 300, 'access': True, 'decrypted': True}
        self.slot.running_apps = {'terminal': 'terminal'}
        self.slot.save()
        result = self.cmd('get ledger.enc')
        self.assertIn('Local storage full', self.log_text(result))
        self.slot.refresh_from_db()
        self.assertFalse(self.slot.mission_state.get('recovered'))

    def test_gateway_capacity_and_rank_loss_allow_route_repair(self):
        self.slot.reputation = 110
        self.slot.proxy_route = ['tokyo', 'new-york', 'london']
        self.slot.save()
        self.reserve()
        self.cmd('abort')
        result = self.post(self.endpoint('route'), {'nodes': ['new-york', 'london']})
        self.assertEqual(result['rank'], 0)
        self.assertNotIn('tokyo', result['proxy_route'])
        self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': 'gateway-1-specialist'})
        self.post(self.endpoint('route'), {'nodes': ['new-york', 'london', 'berlin']})
        self.post(self.endpoint('loadout'), {'action': 'equip', 'product_id': 'gateway-1-specialist'}, 400)
        self.post(self.endpoint('route'), {'nodes': []})
        self.post(self.endpoint('loadout'), {'action': 'equip', 'product_id': 'gateway-1-specialist'})

    def test_atlas_has_named_saved_servers_and_full_network_directory(self):
        result = self.refresh()
        self.assertEqual(len(result['relays']), 4)
        self.assertEqual(len(result['network_directory']), 56)
        names = {server['name'] for server in result['relays']}
        self.assertIn('Intel Corp: Public Access', names)
        self.assertIn('MilTech Research Center', names)
        self.assertIn('NY Public Library Terminal', names)
        self.assertTrue(all(server['address'].endswith('.internal') for server in result['network_directory']))

    def test_directory_add_is_idempotent_and_enables_routing(self):
        self.post(self.endpoint('route'), {'nodes': ['sao-paulo']}, 400)
        for _ in range(2):
            result = self.post(self.endpoint('directory'), {'action': 'add', 'server_id': 'sao-paulo'})
        self.assertEqual(result['atlas_nodes'].count('sao-paulo'), 1)
        self.assertEqual(result['balance'], 1200)
        self.post(self.endpoint('route'), {'nodes': ['sao-paulo']})

    def test_removing_server_prunes_only_this_slots_route_and_directory(self):
        other = SaveSlot.objects.create(user=self.user, position=2, alias='other', proxy_route=['london'])
        self.post(self.endpoint('route'), {'nodes': ['london', 'berlin', 'new-york']})
        result = self.post(self.endpoint('directory'), {'action': 'remove', 'server_id': 'berlin'})
        self.assertEqual(result['proxy_route'], ['london', 'new-york'])
        self.assertNotIn('berlin', result['atlas_nodes'])
        self.assertNotIn('berlin', {server['id'] for server in result['relays']})
        other.refresh_from_db()
        self.assertIn('berlin', other.atlas_nodes)
        self.assertEqual(other.proxy_route, ['london'])
        self.reserve()
        self.assertIn('Intel Corp: Public Access', self.log_text(self.cmd('route')))

    def test_directory_changes_are_locked_during_remote_session(self):
        self.post(self.endpoint('route'), {'nodes': ['london']})
        self.scan_and_connect()
        self.post(self.endpoint('directory'), {'action': 'remove', 'server_id': 'london'}, 400)
        self.post(self.endpoint('directory'), {'action': 'add', 'server_id': 'sao-paulo'}, 400)
        result = self.refresh()
        self.assertEqual(result['proxy_route'], ['london'])
        self.assertNotIn('sao-paulo', result['atlas_nodes'])

    def test_bookmark_does_not_bypass_server_clearance(self):
        self.post(self.endpoint('directory'), {'action': 'add', 'server_id': 'tokyo'})
        self.post(self.endpoint('route'), {'nodes': ['tokyo']}, 400)

    def test_invalid_directory_requests_do_not_change_atlas(self):
        for payload in [{'action': 'add', 'server_id': 'unknown.internal'}, {'action': 'remove', 'server_id': []}, {'action': 'invent', 'server_id': 'london'}]:
            self.post(self.endpoint('directory'), payload, 400)
        self.assertEqual(len(self.refresh()['atlas_nodes']), 4)

    def test_restart_requires_alias_and_only_resets_selected_slot(self):
        other = SaveSlot.objects.create(user=self.user, position=2, alias='other', balance=800)
        self.scan_and_connect()
        self.post(self.endpoint('restart'), {'confirmation': 'wrong'}, 400)
        result = self.post(self.endpoint('restart'), {'confirmation': 'ghost'})
        self.assertEqual(result['balance'], 1200)
        self.assertEqual(result['reputation'], 0)
        self.assertIsNone(result['active_contract'])
        self.assertEqual(result['running_apps'], [])
        self.assertEqual(result['equipment']['cpu']['id'], STARTER_EQUIPMENT['cpu'])
        self.assertEqual(len(result['ledger']), 1)
        other.refresh_from_db()
        self.assertEqual(other.balance, 800)

    def test_commands_are_simulation_data_and_cannot_run_host_commands(self):
        self.reserve()
        response = self.cmd('connect example.com; touch /tmp/should-not-exist')
        self.assertFalse(response['connected'])
        response = self.cmd('$(whoami)')
        self.assertIn('Unknown shell command', self.log_text(response))


class ConcurrentEconomyTests(APIHelpers, TransactionTestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('parallel')
        self.client.force_login(user)
        self.slot = SaveSlot.objects.create(user=user, position=1, alias='parallel', running_apps={'terminal': 'terminal'})

    def parallel_post(self, suffix, payload):
        def run(_):
            close_old_connections()
            try:
                client = Client()
                client.cookies = self.client.cookies.copy()
                return client.post(f'/api/slots/{self.slot.pk}/{suffix}/', json.dumps(payload), content_type='application/json').status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, range(2)))

    def test_concurrent_erase_all_submissions_only_pay_once(self):
        from .persistence import ensure_server
        job = CONTRACT_BY_ID['purge-0']
        server = ensure_server(self.slot, job)
        for entry in server.files:
            if entry['name'] in job['delete_paths']:
                entry['present'] = False
        server.save()
        self.slot.active_contract = job['id']
        self.slot.mission_state = dict(deleted=True, deletion_receipts=job['delete_paths'], clean_exit=True)
        self.slot.save()
        self.assertEqual(self.parallel_post('command', {'application': 'terminal', 'command': 'submit'}), [200, 200])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.balance, 1200 + job['reward'])
        self.assertEqual(self.slot.completed, 1)
        self.assertEqual(self.slot.ledger.count(), 1)

    def test_concurrent_submissions_only_pay_once(self):
        self.slot.active_contract = '0-0'
        self.slot.local_files = [dict(id='proof', name='research.dat', size=24, source='helix-0.internal', source_path='research.dat')]
        self.slot.mission_state = {'recovered': True, 'local_file_id': 'proof', 'clean_exit': True}
        self.slot.save()
        self.assertEqual(self.parallel_post('command', {'application': 'terminal', 'command': 'submit'}), [200, 200])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.balance, 1420)
        self.assertEqual(self.slot.completed, 1)
        self.assertEqual(self.slot.ledger.count(), 1)

    def test_concurrent_purchases_cannot_double_debit_or_overspend(self):
        self.slot.balance = 300
        self.slot.save()
        outcomes = self.parallel_post('loadout', {'action': 'buy', 'product_id': 'cpu-1-specialist'})
        self.assertCountEqual(outcomes, [200, 400])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.balance, 300 - PRODUCTS['cpu-1-specialist']['price'])
        self.assertEqual(self.slot.owned_hardware.count('cpu-1-specialist'), 1)

    def test_concurrent_irc_license_purchases_only_charge_once(self):
        outcomes = self.parallel_post('irc', {'command': '/buy ssh-v1-r1-license'})
        self.assertCountEqual(outcomes, [200, 400])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.balance, 840)
        self.assertEqual(self.slot.exploit_inventory['ssh-v1-r1-license']['quantity'], 1)
        self.assertEqual(self.slot.ledger.count(), 1)

    def test_concurrent_irc_single_use_purchases_cannot_overspend(self):
        self.slot.balance = 90
        self.slot.save()
        outcomes = self.parallel_post('irc', {'command': '/pay hexdealer 90 ssh-v1-r1-shot'})
        self.assertCountEqual(outcomes, [200, 400])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.balance, 0)
        self.assertEqual(self.slot.exploit_inventory['ssh-v1-r1-shot']['quantity'], 1)
        self.assertEqual(self.slot.ledger.count(), 1)

    def test_concurrent_requests_settle_ransomware_only_once(self):
        self.slot.ransomware_ops = [{'target': 'vesper-dispatch.internal', 'due_at': (timezone.now() - timedelta(seconds=1)).isoformat(), 'reward': 800}]
        self.slot.save()
        self.assertEqual(self.parallel_post('command', {'application': 'terminal', 'command': 'status'}), [200, 200])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.balance, 2000)
        self.assertEqual(self.slot.ransomware_ops, [])
        self.assertEqual(self.slot.ledger.filter(description__startswith='Ransomware payout').count(), 1)
        payout=next(entry for entry in self.slot.mission_log if 'you earned' in entry['text'])
        self.assertEqual(payout['app'],'terminal')

    def test_concurrent_password_starts_charge_once_and_completion_records_once(self):
        self.scan_and_connect()
        self.launch('cracker-1-standard')
        self.slot.refresh_from_db()
        balance = self.slot.balance
        self.assertCountEqual(self.parallel_post('password-breaker', {'action': 'start'}), [200, 400])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.balance, balance - 2)
        self.slot.mission_state['password_break']['finishes_at'] = timezone.now().isoformat()
        self.slot.save()
        self.assertEqual(self.parallel_post('command', {'application': 'terminal', 'command': 'status'}), [200, 200])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.mission_state['password_result'], 'ready')
        self.assertFalse(self.slot.mission_state['access'])
        self.assertCountEqual(self.parallel_post('password-breaker', {'action': 'login'}), [200, 400])
        self.assertEqual(self.slot.server_states.get(address='helix-0.internal').events.filter(kind='access_granted').count(), 1)

    def test_concurrent_broker_refresh_creates_one_replacement(self):
        self.reserve()
        self.cmd('abort')
        self.slot.refresh_from_db()
        self.slot.broker_pending[0]['due_at']=(timezone.now()-timedelta(seconds=1)).isoformat()
        self.slot.save()
        self.assertEqual(self.parallel_post('command',{'application':'terminal','command':'status'}),[200,200])
        self.slot.refresh_from_db()
        self.assertEqual(len(self.slot.broker_jobs),1)
        self.assertEqual(self.slot.broker_pending,[])

    def test_concurrent_note_edits_cannot_silently_overwrite_each_other(self):
        identity = self.slot.created_at.isoformat()
        def edit(text):
            close_old_connections()
            try:
                client = Client()
                client.cookies = self.client.cookies.copy()
                return client.post(f'/api/slots/{self.slot.pk}/notes/', json.dumps({'text': text, 'revision': 0, 'identity': identity}), content_type='application/json').status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(edit, ['first window', 'second window']))
        self.assertCountEqual(outcomes, [200, 409])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.notes_revision, 1)
        self.assertIn(self.slot.field_notes, ['first window', 'second window'])


class LegacySaveMigrationTests(TransactionTestCase):
    def test_legacy_equipment_balances_and_ledger_survive(self):
        executor = MigrationExecutor(connection)
        executor.migrate([('game', '0001_initial')])
        try:
            old = executor.loader.project_state([('game', '0001_initial')]).apps
            user = old.get_model('auth', 'User').objects.create(username='legacy')
            slot = old.get_model('game', 'SaveSlot').objects.create(user_id=user.pk, position=1, alias='veteran', balance=7321, reputation=270, hardware=3, gateway=2, software=3, active_contract='0-0', mission_log=['Legacy session'])
            old.get_model('game', 'LedgerEntry').objects.create(slot_id=slot.pk, amount=100, description='Preserved payment')
            executor = MigrationExecutor(connection)
            executor.migrate([('game', '0002_runner_desktop')])
            updated = executor.loader.project_state([('game', '0002_runner_desktop')]).apps.get_model('game', 'SaveSlot').objects.get(pk=slot.pk)
            self.assertEqual(updated.balance, 7321)
            self.assertEqual(updated.reputation, 270)
            self.assertEqual(updated.equipment['cpu'], 'cpu-3-standard')
            self.assertEqual(updated.equipment['gateway'], 'gateway-2-standard')
            self.assertIn('decryptor-3-standard', updated.installed_software)
            self.assertEqual(updated.active_contract, '')
            self.assertEqual(updated.ledger.get().description, 'Preserved payment')
            self.assertEqual(updated.mission_log[0]['text'], 'Legacy session')
        finally:
            restore = MigrationExecutor(connection)
            restore.migrate(restore.loader.graph.leaf_nodes())


class AtlasDirectoryMigrationTests(TransactionTestCase):
    def test_v02_routes_and_live_sessions_keep_their_servers(self):
        executor = MigrationExecutor(connection)
        executor.migrate([('game', '0002_runner_desktop')])
        try:
            old = executor.loader.project_state([('game', '0002_runner_desktop')]).apps
            user = old.get_model('auth', 'User').objects.create(username='atlas-veteran')
            started = timezone.now()
            slot = old.get_model('game', 'SaveSlot').objects.create(user_id=user.pk, position=1, alias='veteran', balance=900, proxy_route=['sao-paulo', 'london'], active_contract='0-0', mission_started=started, mission_state={'trace_budget': 160})
            executor = MigrationExecutor(connection)
            executor.migrate([('game', '0003_atlas_server_directory')])
            updated = executor.loader.project_state([('game', '0003_atlas_server_directory')]).apps.get_model('game', 'SaveSlot').objects.get(pk=slot.pk)
            self.assertEqual(len(updated.atlas_nodes), 12)
            self.assertEqual(updated.proxy_route, ['sao-paulo', 'london'])
            self.assertEqual(updated.balance, 900)
            self.assertEqual(updated.mission_started, started)
            self.assertEqual(updated.mission_state, {'trace_budget': 160})
        finally:
            restore = MigrationExecutor(connection)
            restore.migrate(restore.loader.graph.leaf_nodes())


class DevelopmentResetTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('reset-runner', password='A-test-passphrase-42')
        self.client.force_login(self.user)
        self.slot = SaveSlot.objects.create(user=self.user, position=1, alias='Reset')
        self.slot.ledger.create(amount=1200, description='Initial funding')

    @override_settings(DEBUG=True)
    def test_reset_requires_explicit_confirmation(self):
        for confirmation in [None, 'yes', '']:
            with self.subTest(confirmation=confirmation), self.assertRaises(CommandError):
                call_command('reset_dev', confirm=confirmation, stdout=StringIO())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())
        self.assertTrue(SaveSlot.objects.filter(pk=self.slot.pk).exists())

    @override_settings(DEBUG=False)
    def test_reset_is_refused_outside_development_mode(self):
        with self.assertRaises(CommandError):
            call_command('reset_dev', confirm='ERASE-ALL-DATA', stdout=StringIO())
        self.assertEqual(get_user_model().objects.count(), 1)

    @override_settings(DEBUG=True)
    def test_reset_recreates_and_migrates_instead_of_flushing(self):
        from unittest.mock import patch
        with patch('game.dev_database.recreate_database') as recreate, patch('game.dev_database.call_command') as migrate, patch('game.dev_database.remember_build'):
            call_command('reset_dev', confirm='ERASE-ALL-DATA', stdout=StringIO())
        recreate.assert_called_once()
        self.assertEqual(migrate.call_args.args, ('migrate',))


class DevelopmentDatabaseLifecycleTests(TestCase):
    """Real DROP/CREATE and dump/restore, always in a disposable database."""

    def test_build_reset_restart_and_dump_restore_round_trip(self):
        import os
        import shutil
        import subprocess
        import sys
        import tempfile
        import uuid
        from pathlib import Path
        import psycopg
        from psycopg import sql

        pg_bin = os.environ.get('NETRUNNER_PG_BIN', '')
        dump = shutil.which('pg_dump') or str(Path(pg_bin) / 'pg_dump')
        restore = shutil.which('pg_restore') or str(Path(pg_bin) / 'pg_restore')
        if not Path(dump).is_file() or not Path(restore).is_file():
            self.skipTest('pg_dump and pg_restore must be on PATH or in NETRUNNER_PG_BIN')
        config = connection.settings_dict
        params = {key: config[value] for key, value in {
            'host': 'HOST', 'port': 'PORT', 'user': 'USER', 'password': 'PASSWORD',
        }.items() if config.get(value)}
        name = 'netrunner_lifecycle_' + uuid.uuid4().hex
        env = {**os.environ, 'PGDATABASE': name, 'DJANGO_DEBUG': '1', 'NETRUNNER_RESET_ON_BUILD': '1'}
        for key, value in {'PGHOST': 'HOST', 'PGPORT': 'PORT', 'PGUSER': 'USER', 'PGPASSWORD': 'PASSWORD'}.items():
            env[key] = str(config.get(value, ''))
        manage = Path(__file__).resolve().parents[1] / 'manage.py'

        def run(*arguments):
            result = subprocess.run(arguments, env=env, text=True, capture_output=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout

        def query(statement):
            with psycopg.connect(dbname=name, autocommit=True, **params) as db:
                cursor = db.execute(statement)
                return cursor.fetchall() if cursor.description else None

        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                build = root / 'image-id'
                build.write_text('build-one')
                env.update(NETRUNNER_BUILD_ID_FILE=str(build), NETRUNNER_BUILD_STATE=str(root / 'state' / 'build-id'))
                self.assertIn('dropping and recreating', run(sys.executable, str(manage), 'prepare_dev'))
                run(sys.executable, str(manage), 'shell', '-c',
                    "from django.contrib.auth import get_user_model; from game.models import SaveSlot; "
                    "user = get_user_model().objects.create_user('lifecycle-runner'); "
                    "slot = SaveSlot.objects.create(user=user, position=1, alias='Archive', balance=842, reputation=130, active_contract='0-1'); "
                    "slot.ledger.create(amount=-90, description='Archive test receipt')")
                run(sys.executable, str(manage), 'generate_content', 'missions', '--count', '1')
                run(sys.executable, str(manage), 'generate_content', 'servers', '--count', '1', '--exploitable')
                run(sys.executable, str(manage), 'shell', '-c',
                    "from game.models import SaveSlot; from game.world import get_server, target_for_server; from django.utils import timezone; from datetime import timedelta; "
                    "slot = SaveSlot.objects.get(alias='Archive'); slot.backdoors = [target_for_server(get_server('world-0'))]; "
                    "slot.ransomware_ops = [dict(target='vesper-dispatch.internal', due_at=(timezone.now()+timedelta(seconds=120)).isoformat(), reward=800)]; "
                    "slot.market_unlocked=True; slot.installed_software += ['rootkit-epic', 'ransomware-epic']; slot.save()")
                run(sys.executable, str(manage), 'shell', '-c',
                    "from game.models import SaveSlot; from game.world import get_server, target_for_server; from game.persistence import ensure_server, event; "
                    "slot = SaveSlot.objects.get(alias='Archive'); slot.field_notes='Archive notebook: follow the old relay'; slot.notes_revision=2; slot.workspace_layout=[dict(id='terminal', product_id='terminal', x=1, y=2, w=9, h=6)]; slot.workspace_revision=4; slot.local_files=[dict(id='backup-file', name='archive.dat', size=12, source='backup.internal', source_path='archive.dat')]; slot.save(); "
                    "server = ensure_server(slot, target_for_server(get_server('world-0'))); server.files[0]['present']=False; server.visits=3; server.save(); event(server, 'file_deleted', 'Archive proof retained')")
                identities = query('SELECT template_key, code FROM game_contractidentity ORDER BY template_key')
                query('CREATE TABLE lifecycle_probe (value text)')
                query("INSERT INTO lifecycle_probe VALUES ('backup survives')")
                run(dump, '-d', name, '--format=custom', '--no-owner', '--no-acl', '--file=' + str(root / 'snapshot.dump'))
                self.assertNotIn('dropping and recreating', run(sys.executable, str(manage), 'prepare_dev'))
                self.assertEqual(query('SELECT * FROM lifecycle_probe'), [('backup survives',)])
                build.write_text('build-two')
                self.assertIn('dropping and recreating', run(sys.executable, str(manage), 'prepare_dev'))
                self.assertEqual(query("SELECT to_regclass('lifecycle_probe')"), [(None,)])
                # Prove the schema and migration history were recreated, not merely flushed.
                self.assertEqual(query('SELECT count(*) FROM auth_user'), [(0,)])
                self.assertEqual(query('SELECT count(*) FROM game_contractidentity'), [(len(CONTRACT_BY_ID),)])
                run(restore, '-d', name, '--clean', '--if-exists', '--no-owner', '--no-acl', '--exit-on-error', '--single-transaction', str(root / 'snapshot.dump'))
                build.write_text('build-three')
                run(sys.executable, str(manage), 'prepare_dev', '--preserve')
                run(sys.executable, str(manage), 'prepare_dev')
                self.assertEqual(query('SELECT * FROM lifecycle_probe'), [('backup survives',)])
                self.assertEqual(query('SELECT template_key, code FROM game_contractidentity ORDER BY template_key'), identities)
                self.assertEqual(query('SELECT alias, balance, reputation, active_contract FROM game_saveslot'), [('Archive', 842, 130, '0-1')])
                self.assertEqual(query('SELECT amount, description FROM game_ledgerentry'), [(-90, 'Archive test receipt')])
                self.assertEqual(query('SELECT count(*) FROM game_generatedmission'), [(1,)])
                self.assertEqual(query('SELECT count(*) FROM game_directoryserver'), [(6,)])
                self.assertEqual(query('SELECT field_notes, notes_revision FROM game_saveslot'), [('Archive notebook: follow the old relay', 2)])
                self.assertEqual(query("SELECT local_files->0->>'name', local_files->0->>'size' FROM game_saveslot"), [('archive.dat', '12')])
                self.assertEqual(query("SELECT workspace_revision, workspace_layout->0->>'x', workspace_layout->0->>'w' FROM game_saveslot"), [(4, '1', '9')])
                self.assertEqual(query("SELECT address, visits, files->0->>'present' FROM game_serverstate"), [('vesper-dispatch.internal', 3, 'false')])
                self.assertEqual(query("SELECT count(*) FROM game_serverevent WHERE kind='file_deleted'"), [(1,)])
                self.assertEqual(query("SELECT backdoors->0->>'target', ransomware_ops->0->>'reward', market_unlocked FROM game_saveslot"), [('vesper-dispatch.internal', '800', True)])
        finally:
            with psycopg.connect(dbname='postgres', autocommit=True, **params) as maintenance:
                maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))


class GeneratedWorldTests(APIHelpers, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('world-author')
        self.client.force_login(self.user)
        self.slot = SaveSlot.objects.create(user=self.user, position=1, alias='Author')

    @override_settings(DEBUG=True)
    def test_generated_mission_is_unique_rank_filtered_and_playable(self):
        from .models import GeneratedMission
        call_command('generate_content', 'missions', count=3, rank=0, objective='delete', stdout=StringIO())
        jobs = [row.data for row in GeneratedMission.objects.all()]
        self.assertEqual(len(set(job['target'] for job in jobs)), 3)
        self.assertEqual(len(set(public_code(job['id']) for job in jobs)), 3)
        listed = self.refresh()['contracts']
        self.assertEqual(len(listed), 30)
        for job in jobs:
            response = self.reserve(public_code(job['id']))
            self.assertEqual(response['active_contract']['target'], job['target'])
            self.launch('mapper-1-standard')
            self.cmd(f'scan {job["target"]}', 'mapper')
            self.cmd(f'connect {job["target"]}')
            self.launch('cracker-1-standard')
            self.cmd(f'crack {job["port"]}', 'cracker')
            if job['encrypted']:
                self.cmd('abort')
            else:
                self.cmd(f'{"get" if job["objective"] == "retrieve" else "rm"} /{job.get("artifact_path", job["file"])}')
                self.clean_exit()
                result = self.cmd('submit')
                self.assertIn('Delivery verified', self.log_text(result))
        call_command('generate_content', 'missions', count=1, rank=4, stdout=StringIO())
        result = self.refresh()
        self.assertTrue(all(abs(job['rank'] - result['rank']) <= 1 for job in result['contracts']))

    @override_settings(DEBUG=True)
    def test_generated_servers_can_be_bookmarked_and_used_as_proxies(self):
        from .models import DirectoryServer
        call_command('generate_content', 'servers', count=2, rank=0, exploitable=True, stdout=StringIO())
        servers = list(DirectoryServer.objects.filter(key__startswith='srv-'))
        self.assertEqual(len({server.address for server in servers}), 2)
        ids = [server.key for server in servers]
        for key in ids:
            self.post(self.endpoint('directory'), {'action': 'add', 'server_id': key})
        result = self.post(self.endpoint('route'), {'nodes': ids})
        self.assertEqual(result['proxy_route'], ids)
        self.assertTrue(all(server.data['exploitable'] for server in servers))

    @override_settings(DEBUG=False)
    def test_generation_is_development_only(self):
        with self.assertRaises(CommandError):
            call_command('generate_content', 'missions', count=1, rank=0, stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_generator_capacity_failure_is_atomic(self):
        from .models import GeneratedMission
        used = set(ContractIdentity.objects.values_list('code', flat=True))
        ContractIdentity.objects.bulk_create([ContractIdentity(template_key=f'fill{code}', code=code) for code in range(256) if code not in used])
        with self.assertRaises(CommandError):
            call_command('generate_content', 'missions', count=1, rank=0, stdout=StringIO())
        self.assertEqual(GeneratedMission.objects.count(), 0)
        with self.assertRaises(CommandError):
            call_command('generate_content', 'servers', count=0, rank=0, stdout=StringIO())


class HiddenOperationsTests(APIHelpers, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('hidden-runner')
        self.client.force_login(self.user)
        self.slot = SaveSlot.objects.create(user=self.user, position=1, alias='Hidden', balance=10000)
        self.slot.equipment['memory'] = 'memory-1-specialist'
        self.slot.owned_hardware.append('memory-1-specialist')
        self.slot.save()

    def purchase(self, product):
        self.launch('terminal')
        self.cmd('connect null-exchange.internal')
        return self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': product})

    def mount(self, address):
        self.launch('terminal')
        self.launch('mapper-1-standard')
        self.cmd(f'scan {address}', 'mapper')
        response = self.cmd(f'connect {address}')
        self.assertTrue(response['connected'], self.log_text(response))
        self.launch('cracker-1-standard')
        self.cmd('crack 22', 'cracker')

    def test_market_is_hidden_until_discovery_and_prices_are_enforced(self):
        before = self.refresh()
        self.assertFalse(before['market_unlocked'])
        self.assertEqual(before['black_market_catalog'], [])
        self.assertFalse(any(server.get('hidden') for server in before['network_directory']))
        self.post(self.endpoint('directory'), {'action': 'add', 'server_id': 'world-4'}, 400)
        self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': 'rootkit-epic'}, 400)
        after = self.purchase('rootkit-epic')
        self.assertTrue(after['market_unlocked'])
        self.assertEqual(after['balance'], 7600)
        self.assertIn('rootkit-epic', after['installed_software'])
        self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': 'rootkit-epic'}, 400)
        self.assertEqual(len(after['black_market_catalog']), 2)

    def test_rootkit_requires_access_and_persists_direct_log_free_connections(self):
        self.purchase('rootkit-epic')
        self.launch('rootkit-epic')
        rejected = self.cmd('install', 'rootkit')
        self.assertIn('Mount the current server', self.log_text(rejected))
        self.gain_access()
        installed = self.cmd('install', 'rootkit')
        self.assertEqual(installed['backdoors'][0]['target'], 'helix-0.internal')
        self.cmd('get research.dat')
        self.clean_exit()
        self.cmd('submit')
        self.slot.refresh_from_db()
        before = self.slot.balance
        # A saved route is retained, but bypassed even when current clearance disallows it.
        self.slot.proxy_route = ['tokyo']
        self.slot.save()
        connected = self.post(self.endpoint('backdoors'), {'target': 'helix-0.internal'})
        self.assertTrue(connected['stealth_session'])
        self.assertEqual(connected['balance'], before)
        self.assertEqual(connected['proxy_route'], ['tokyo'])
        self.cmd('ls')
        self.slot.refresh_from_db()
        self.assertFalse(self.slot.mission_state['dirty'])
        from unittest.mock import patch
        with patch('django.utils.timezone.now', return_value=timezone.now() + timedelta(hours=1)):
            self.assertTrue(self.refresh()['connected'])
        result = self.cmd('disconnect')
        self.assertEqual(result['balance'], before)
        self.assertEqual(len(result['backdoors']), 1)
        self.assertIn('No access signature', self.log_text(result))
        SaveSlot.objects.filter(pk=self.slot.pk).update(contract_cooldowns={})
        self.reserve()
        self.post(self.endpoint('backdoors'), {'target': 'helix-0.internal'})
        self.cmd('get research.dat')
        self.cmd('disconnect')
        result = self.cmd('submit')
        self.assertIn('Delivery verified', self.log_text(result))
        self.assertEqual(result['balance'], before)

    def test_backdoor_requests_require_ownership_known_target_and_slot_ownership(self):
        self.post(self.endpoint('backdoors'), {'target': 'helix-0.internal'}, 400)
        self.purchase('rootkit-epic')
        self.post(self.endpoint('backdoors'), {'target': 'nonexistent.internal'}, 400)
        other = get_user_model().objects.create_user('other-hidden')
        other_slot = SaveSlot.objects.create(user=other, position=1, alias='Other')
        self.post(f'slots/{other_slot.pk}/backdoors', {'target': 'helix-0.internal'}, 404)

    def test_ransomware_three_instance_limit_once_only_payout_and_redeployment(self):
        self.purchase('ransomware-epic')
        self.launch('ransomware-epic')
        addresses = ['vesper-dispatch.internal', 'cobalt-render.internal', 'nimbus-inventory.internal', 'aster-backup.internal']
        for index, address in enumerate(addresses):
            self.mount(address)
            result = self.cmd(f'deploy {address}', 'ransomware')
            if index < 3:
                self.assertEqual(len(result['ransomware_ops']), index + 1)
                repeated = self.cmd(f'deploy {address}', 'ransomware')
                self.assertEqual(len(repeated['ransomware_ops']), index + 1)
            else:
                self.assertIn('Three ransomware instances', self.log_text(result))
                self.assertEqual(len(result['ransomware_ops']), 3)
            self.clean_exit()
        before = self.refresh()['balance']
        from unittest.mock import patch
        with patch('django.utils.timezone.now', return_value=timezone.now() + timedelta(seconds=121)):
            result = self.refresh()
            self.assertEqual(result['balance'], before + 2400)
            self.assertEqual(result['ransomware_ops'], [])
            self.assertEqual(self.refresh()['balance'], before + 2400)
        self.assertEqual(self.slot.ledger.filter(description__startswith='Ransomware payout').count(), 3)
        self.mount(addresses[0])
        self.assertEqual(len(self.cmd(f'deploy {addresses[0]}', 'ransomware')['ransomware_ops']), 1)

    def test_ransomware_refuses_contract_and_proxy_only_servers(self):
        self.purchase('ransomware-epic')
        self.launch('ransomware-epic')
        self.gain_access()
        result = self.cmd('deploy helix-0.internal', 'ransomware')
        self.assertEqual(result['ransomware_ops'], [])
        self.assertIn('non-contract opportunity', self.log_text(result))
        self.cmd('abort')
        self.mount('intel-public.internal')
        result = self.cmd('deploy intel-public.internal', 'ransomware')
        self.assertEqual(result['ransomware_ops'], [])

    def test_restart_clears_hidden_progress_for_selected_save_only(self):
        self.purchase('rootkit-epic')
        other = SaveSlot.objects.create(user=self.user, position=2, alias='Untouched', market_unlocked=True)
        response = self.post(self.endpoint('restart'), {'confirmation': 'Hidden'})
        self.assertEqual(response['backdoors'], [])
        self.assertEqual(response['ransomware_ops'], [])
        self.assertFalse(response['market_unlocked'])
        other.refresh_from_db()
        self.assertTrue(other.market_unlocked)


class FieldNotesTests(APIHelpers, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('notebook')
        self.client.force_login(self.user)
        self.slot = SaveSlot.objects.create(user=self.user, position=1, alias='Notebook')

    def note(self):
        return self.client.get(f'/api/{self.endpoint("notes")}/').json()

    def write(self, text, revision=0, status=200, identity=None):
        return self.post(self.endpoint('notes'), {'text': text, 'revision': revision, 'identity': identity or self.note()['identity']}, status)

    def test_notes_preserve_unicode_whitespace_and_are_separate_per_save(self):
        text = '  Intel → library\n\nAlias: λ-runner 🛰️\n'
        result = self.write(text)
        self.assertEqual(result['text'], text)
        self.assertEqual(result['revision'], 1)
        other = SaveSlot.objects.create(user=self.user, position=2, alias='Other')
        self.assertEqual(self.client.get(f'/api/slots/{other.pk}/notes/').json()['text'], '')
        self.client.logout()
        self.client.force_login(self.user)
        self.assertEqual(self.note()['text'], text)
        self.assertEqual(self.write('', revision=1)['text'], '')
        self.assertEqual(self.note()['revision'], 2)

    def test_conflicts_retain_newer_notes_and_identical_retries_are_idempotent(self):
        first = self.write('first draft')
        self.assertEqual(self.write('first draft', revision=0)['revision'], 1)
        conflict = self.write('stale other draft', revision=0, status=409)
        self.assertEqual(conflict['note']['text'], 'first draft')
        self.assertEqual(self.note()['text'], 'first draft')
        self.assertEqual(self.write('reviewed merge', revision=first['revision'])['revision'], 2)

    def test_validation_authentication_and_ownership(self):
        for text, revision in [('x' * 50001, 0), (None, 0), ('null\x00byte', 0), ('text', True), ('text', -1)]:
            self.write(text, revision=revision, status=400)
        outsider = get_user_model().objects.create_user('notebook-outsider')
        other_slot = SaveSlot.objects.create(user=outsider, position=1, alias='Other')
        self.post(f'slots/{other_slot.pk}/notes', {'text': 'injected', 'revision': 0}, 404)
        self.assertEqual(self.client.get(f'/api/slots/{other_slot.pk}/notes/').status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(f'/api/{self.endpoint("notes")}/').status_code, 401)

    def test_notes_csrf_and_old_drafts_cannot_resurrect_a_restarted_save(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(f'/api/{self.endpoint("notes")}/', '{}', content_type='application/json').status_code, 403)
        identity = self.note()['identity']
        self.write('old life')
        self.post(self.endpoint('restart'), {'confirmation': 'Notebook'})
        self.write('delayed autosave', revision=0, identity=identity, status=409)
        self.assertEqual(self.note()['text'], '')
        self.assertNotEqual(self.note()['identity'], identity)


class PersistentWorldTests(APIHelpers, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('historian')
        self.client.force_login(self.user)
        self.slot = SaveSlot.objects.create(user=self.user, position=1, alias='Historian', balance=10000)
        self.slot.equipment['memory'] = 'memory-2-specialist'
        self.slot.owned_hardware.append('memory-2-specialist')
        self.slot.installed_software += ['rootkit-epic', 'ransomware-epic', 'decryptor-1-standard']
        self.slot.save()

    def mount(self, address='vesper-dispatch.internal', port=22):
        self.launch('terminal')
        self.launch('mapper-1-standard')
        self.cmd(f'scan {address}', 'mapper')
        self.cmd(f'connect {address}')
        self.launch('cracker-1-standard')
        result = self.cmd(f'crack {port}', 'cracker')
        self.assertIn('filesystem mounted', self.log_text(result))

    def history(self, address='vesper-dispatch.internal'):
        return self.client.get(f'/api/{self.endpoint("history")}/', {'server': address}).json()

    def test_deleted_files_remain_missing_and_journal_survives_log_erasure(self):
        self.mount()
        self.cmd('rm public-index.dat')
        self.clean_exit()
        self.client.logout()
        self.client.force_login(self.user)
        self.mount()
        result = self.cmd('ls')
        self.assertNotIn('public-index.dat', result['mission_log'][-1]['text'])
        self.assertIn('backup/', result['mission_log'][-1]['text'])
        self.assertIn('File not found', self.cmd('get public-index.dat')['mission_log'][-1]['text'])
        history = self.history()
        self.assertIn('file_deleted', {entry['kind'] for entry in history['events']})
        self.assertIn('logs_erased', {entry['kind'] for entry in history['events']})
        self.assertFalse(history['servers'][0]['observed']['files'][0]['present'])
        self.assertEqual(history['servers'][0]['visits'], 2)
        other = SaveSlot.objects.create(user=self.user, position=2, alias='Independent')
        self.assertFalse(other.server_states.exists())
        self.assertEqual(self.client.get(f'/api/slots/{other.pk}/history/', {'server': 'vesper-dispatch.internal'}).status_code, 404)

    def test_decryption_changes_the_remote_file_beyond_one_session(self):
        self.gain_access('0-1')
        self.launch('decryptor-1-standard')
        self.cmd('decrypt ledger.enc', 'decryptor')
        self.clean_exit()
        self.slot.refresh_from_db()
        self.slot.mission_state.pop('decrypted', None)
        self.slot.save()
        self.cmd('connect helix-1.internal')
        self.cmd('crack 443', 'cracker')
        result = self.cmd('get ledger.enc')
        self.assertIn('Copied ledger.enc', result['mission_log'][-1]['text'])
        self.assertFalse(self.slot.server_states.get(address='helix-1.internal').files[0]['encrypted'])

    def test_contract_replacement_restores_moves_files_and_rotates_service(self):
        from unittest.mock import patch
        self.gain_access('0-2')
        self.cmd('rm audit.log')
        self.clean_exit()
        self.cmd('submit')
        server = self.slot.server_states.get(address='helix-2.internal')
        self.assertFalse(server.files[0]['present'])
        with patch('django.utils.timezone.now', return_value=timezone.now() + timedelta(seconds=301)):
            self.refresh()
            server.refresh_from_db()
            self.assertEqual(server.port, 2222)
            self.assertEqual(server.files[0]['name'], 'archive/r2/audit.log')
            self.assertTrue(server.files[0]['present'])
            self.assertFalse(server.observed['files'][0]['present'])
            self.reserve('0-2')
            scan = self.cmd('scan helix-2.internal', 'mapper')
            self.assertIn('2222/tcp', scan['mission_log'][-1]['text'])
            self.cmd('connect helix-2.internal')
            self.assertIn('Connection refused', self.cmd('crack 22', 'cracker')['mission_log'][-1]['text'])
            self.cmd('crack 2222', 'cracker')
            self.cmd('rm archive/r2/audit.log')
            self.clean_exit()
            result = self.cmd('submit')
            self.assertEqual(result['completed'], 1)
            self.assertNotIn('helix-2.internal', [job['target'] for job in result['contracts']])
        self.assertEqual(server.events.filter(kind='administrator_patch').count(), 1)

    def test_live_wraith_session_delays_maintenance_without_losing_backdoor(self):
        from unittest.mock import patch
        self.mount()
        self.launch('rootkit-epic')
        self.cmd('install', 'rootkit')
        self.clean_exit()
        server = self.slot.server_states.get(address='vesper-dispatch.internal')
        server.maintenance_due = timezone.now() + timedelta(seconds=10)
        server.save()
        before = self.refresh()['balance']
        self.post(self.endpoint('backdoors'), {'target': server.address})
        with patch('django.utils.timezone.now', return_value=timezone.now() + timedelta(seconds=601)):
            self.refresh()
            server.refresh_from_db()
            self.assertEqual(server.revision, 1)
            self.cmd('disconnect')
            server.refresh_from_db()
            self.assertEqual(server.revision, 2)
            connected = self.post(self.endpoint('backdoors'), {'target': server.address})
            self.assertEqual(connected['balance'], before)
            self.assertTrue(connected['stealth_session'])
            self.assertIn('public-index.dat', self.cmd('ls /archive/r2')['mission_log'][-1]['text'])
            server.refresh_from_db()
            self.assertTrue(server.backdoor_installed)
            self.assertEqual(server.remote_logs, [])

    def test_proxy_transits_are_recorded_and_wraith_jumps_bypass_the_saved_chain(self):
        self.post(self.endpoint('route'), {'nodes': ['london', 'berlin']})
        self.mount()
        intel = self.slot.server_states.get(address='intel-public.internal')
        self.assertEqual(intel.visits, 1)
        self.assertEqual(intel.events.filter(kind='proxy_transit').count(), 1)
        self.launch('rootkit-epic')
        self.cmd('install', 'rootkit')
        self.clean_exit()
        self.post(self.endpoint('backdoors'), {'target': 'vesper-dispatch.internal'})
        intel.refresh_from_db()
        self.assertEqual(intel.visits, 1)

    def test_stale_fingerprint_requires_a_new_scan_after_maintenance(self):
        from unittest.mock import patch
        self.launch('terminal')
        self.launch('mapper-1-standard')
        self.cmd('scan vesper-dispatch.internal', 'mapper')
        server = self.slot.server_states.get(address='vesper-dispatch.internal')
        server.maintenance_due = timezone.now() + timedelta(seconds=10)
        server.save()
        with patch('django.utils.timezone.now', return_value=timezone.now() + timedelta(seconds=11)):
            self.cmd('connect vesper-dispatch.internal')
            self.launch('cracker-1-standard')
            self.assertIn('No service fingerprint', self.cmd('crack 2222', 'cracker')['mission_log'][-1]['text'])
            self.cmd('scan vesper-dispatch.internal', 'mapper')
            self.assertIn('filesystem mounted', self.cmd('crack 2222', 'cracker')['mission_log'][-1]['text'])

    def test_ransomware_events_and_payments_are_persistent_without_economy_changes(self):
        from unittest.mock import patch
        self.mount()
        self.launch('ransomware-epic')
        self.cmd('deploy vesper-dispatch.internal', 'ransomware')
        self.clean_exit()
        before = self.refresh()['balance']
        with patch('django.utils.timezone.now', return_value=timezone.now() + timedelta(seconds=121)):
            self.assertEqual(self.refresh()['balance'], before + 800)
            self.assertEqual(self.refresh()['balance'], before + 800)
        kinds = {entry['kind'] for entry in self.history()['events']}
        self.assertTrue({'ransomware_deployed', 'ransomware_completed'} <= kinds)

    def test_history_paginates_checks_ownership_and_restart_clears_only_one_world(self):
        from .models import ServerEvent
        self.mount()
        server = self.slot.server_states.get(address='vesper-dispatch.internal')
        ServerEvent.objects.bulk_create([ServerEvent(server=server, kind='test_entry', summary=f'Entry {index}') for index in range(55)])
        first = self.history()
        self.assertEqual(len(first['events']), 50)
        second = self.client.get(f'/api/{self.endpoint("history")}/', {'server': server.address, 'before': first['next_before']}).json()
        self.assertFalse({row['id'] for row in first['events']} & {row['id'] for row in second['events']})
        outsider = get_user_model().objects.create_user('world-outsider')
        other = SaveSlot.objects.create(user=outsider, position=1, alias='Other')
        self.assertEqual(self.client.get(f'/api/slots/{other.pk}/history/').status_code, 404)
        self.post(self.endpoint('restart'), {'confirmation': 'Historian'})
        self.assertFalse(self.slot.server_states.exists())


class PersistentWorldMigrationTests(TransactionTestCase):
    def test_live_mission_files_backdoors_and_pending_operations_are_preserved(self):
        from .catalog import CONTRACT_BY_ID
        executor = MigrationExecutor(connection)
        executor.migrate([('game', '0005_directoryserver_generatedmission_saveslot_backdoors_and_more')])
        try:
            old = executor.loader.project_state([('game', '0005_directoryserver_generatedmission_saveslot_backdoors_and_more')]).apps
            user = old.get_model('auth', 'User').objects.create(username='persistent-veteran')
            slot = old.get_model('game', 'SaveSlot').objects.create(user_id=user.pk, position=1, alias='Veteran', balance=4321, active_contract='0-2', mission_started=timezone.now(), mission_state={'deleted': True, 'scanned': True, 'dirty': True}, backdoors=[CONTRACT_BY_ID['0-2']], ransomware_ops=[{'target': 'vesper-dispatch.internal', 'due_at': (timezone.now() + timedelta(seconds=120)).isoformat(), 'reward': 800}])
            upgrade = MigrationExecutor(connection)
            upgrade.migrate(upgrade.loader.graph.leaf_nodes())
            from .models import SaveSlot
            saved = SaveSlot.objects.get(pk=slot.pk)
            state = saved.server_states.get(address='helix-2.internal')
            self.assertFalse(state.files[0]['present'])
            self.assertTrue(state.backdoor_installed)
            self.assertEqual(len(state.remote_logs), 1)
            self.assertTrue(saved.server_states.filter(address='vesper-dispatch.internal').exists())
            self.assertEqual(saved.balance, 4321)
            self.assertEqual(saved.field_notes, '')
            self.assertEqual(saved.active_contract, '0-2')
        finally:
            restore = MigrationExecutor(connection)
            restore.migrate(restore.loader.graph.leaf_nodes())


class WorkspaceTests(APIHelpers, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('workspace-runner')
        self.client.force_login(self.user)
        self.slot = SaveSlot.objects.create(user=self.user, position=1, alias='Workspace')

    def workspace(self):
        return self.client.get(f'/api/{self.endpoint("workspace")}/').json()

    def save_layout(self, layout, revision=0, identity=None, status=200):
        return self.post(self.endpoint('workspace'), {'layout': layout, 'revision': revision, 'identity': identity or self.workspace()['identity']}, status)

    def test_layout_persists_across_login_without_launching_or_charging_apps(self):
        from .workspace import validate_workspace
        initial = self.workspace()
        self.assertEqual(len(initial['layout']), 2)
        validate_workspace(initial['layout'])
        custom = [dict(id='terminal', product_id='terminal', x=2, y=1, w=8, h=6), dict(id='notes', product_id='notes', x=0, y=8, w=6, h=5)]
        self.assertEqual(self.save_layout(custom)['revision'], 1)
        self.client.logout()
        self.client.force_login(self.user)
        self.assertEqual(self.workspace()['layout'], custom)
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.running_apps, {})
        self.assertEqual(self.slot.balance, 1200)
        self.assertEqual(self.refresh()['workspace_layout'], custom)
        other = SaveSlot.objects.create(user=self.user, position=2, alias='Other')
        self.assertEqual(self.client.get(f'/api/slots/{other.pk}/workspace/').json()['layout'], initial['layout'])

    def test_layout_rejects_overlap_invalid_coordinates_and_duplicate_panels(self):
        import copy
        base = self.workspace()['layout']
        for field, value in [('x', -1), ('x', 12), ('w', 2), ('h', 19), ('y', 512), ('w', True), ('id', 'unknown'), ('product_id', 'rootkit-epic')]:
            invalid = copy.deepcopy(base)
            invalid[0][field] = value
            self.save_layout(invalid, status=400)
        self.save_layout([base[0], base[0]], status=400)
        overlap = copy.deepcopy(base)
        overlap[1]['x'] = 0
        self.save_layout(overlap, status=400)
        self.save_layout({}, status=400)
        self.assertEqual(self.workspace()['layout'], base)

    def test_layout_conflicts_and_identical_retries_cannot_overwrite_newer_arrangements(self):
        layout = self.workspace()['layout'][:1]
        self.save_layout(layout)
        self.assertEqual(self.save_layout(layout, revision=0)['revision'], 1)
        conflict = self.save_layout([], revision=0, status=409)
        self.assertEqual(conflict['workspace']['layout'], layout)
        self.assertEqual(self.workspace()['layout'], layout)
        self.assertEqual(self.save_layout([], revision=1)['layout'], [])

    def test_layout_preferences_do_not_bypass_license_or_ram_limits(self):
        self.save_layout([dict(id='rootkit', product_id='rootkit-epic', x=0, y=0, w=6, h=5)], status=400)
        self.post(self.endpoint('applications'), {'action': 'launch', 'product_id': 'rootkit-epic'}, 400)
        self.slot.refresh_from_db()
        self.assertNotIn('rootkit-epic', self.slot.installed_software)
        self.assertEqual(self.slot.running_apps, {})

    def test_workspace_auth_csrf_and_restart_identity(self):
        initial = self.workspace()
        self.save_layout([])
        outsider = get_user_model().objects.create_user('workspace-outsider')
        other = SaveSlot.objects.create(user=outsider, position=1, alias='Other')
        self.assertEqual(self.client.get(f'/api/slots/{other.pk}/workspace/').status_code, 404)
        self.post(f'slots/{other.pk}/workspace', {}, 404)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(f'/api/{self.endpoint("workspace")}/', '{}', content_type='application/json').status_code, 403)
        self.post(self.endpoint('restart'), {'confirmation': 'Workspace'})
        self.save_layout([], identity=initial['identity'], status=409)
        self.assertEqual(self.workspace()['layout'], initial['layout'])
        self.client.logout()
        self.assertEqual(self.client.get(f'/api/{self.endpoint("workspace")}/').status_code, 401)


class PasswordBreakerTests(APIHelpers, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('decoder', password='test-passphrase-long')
        self.client.force_login(self.user)
        self.slot = SaveSlot.objects.create(user=self.user, position=1, alias='decoder')
        self.scan_and_connect()
        self.launch('cracker-1-standard')

    def start(self, **extra):
        return self.post(self.endpoint('password-breaker'), {'action': 'start', **extra})

    def finish_at(self, delta=0):
        from unittest.mock import patch
        from django.utils.dateparse import parse_datetime
        attempt = self.refresh()['password_break']
        with patch('django.utils.timezone.now', return_value=parse_datetime(attempt['finishes_at']) + timedelta(seconds=delta)):
            return self.refresh()

    def test_login_has_no_trace_even_after_long_wait_or_scanning(self):
        self.slot.refresh_from_db()
        self.slot.mission_started = timezone.now() - timedelta(days=1)
        self.slot.save()
        self.cmd('scan helix-0.internal', 'mapper')
        result = self.refresh()
        self.assertTrue(result['connected'])
        self.assertFalse(result['authenticated'])
        self.assertFalse(result['trace_active'])
        self.assertFalse(self.slot.server_states.get(address='helix-0.internal').remote_logs)
        self.assertIn('not logged in', self.log_text(self.cmd('get research.dat')))

    def test_monitor_reports_no_active_trace_at_server_login(self):
        self.slot.refresh_from_db()
        self.slot.installed_software.append('monitor-1-standard')
        self.slot.save()
        self.launch('monitor-1-standard')
        result = self.cmd('trace', 'monitor')
        self.assertIsNone(result['trace_remaining'])
        self.assertIn('No active remote trace.', result['mission_log'][-1]['text'])

    def test_duration_is_authoritative_and_completion_starts_trace_once(self):
        result = self.start(finishes_at='2000-01-01T00:00:00Z', duration=0, access=True)
        self.assertFalse(result['authenticated'])
        self.assertFalse(result['trace_active'])
        self.assertGreaterEqual(result['password_break']['duration'], 4)
        self.assertFalse(self.refresh()['authenticated'])
        self.assertNotIn('cracker', [app['id'] for app in result['running_apps']])
        result = self.finish_at(7)
        self.assertFalse(result['authenticated'])
        self.assertFalse(result['trace_active'])
        self.assertEqual(result['password_result'], 'ready')
        self.assertIsNone(result['password_break'])
        result = self.post(self.endpoint('password-breaker'), {'action': 'login'})
        self.assertTrue(result['authenticated'])
        self.assertTrue(result['trace_active'])
        self.assertIsNone(result['password_break'])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.mission_state['work'], 0)
        from django.utils.dateparse import parse_datetime
        from game.mechanics import trace_remaining
        from unittest.mock import patch
        with patch('django.utils.timezone.now', return_value=parse_datetime(self.slot.mission_state['trace_started']) + timedelta(seconds=7)):
            self.assertEqual(trace_remaining(self.slot), self.slot.mission_state['trace_budget'] - 7)
        self.assertTrue(self.slot.server_states.get(address='helix-0.internal').remote_logs)
        self.assertEqual(self.slot.server_states.get(address='helix-0.internal').events.filter(kind='access_granted').count(), 1)
        self.refresh()
        self.assertEqual(self.slot.server_states.get(address='helix-0.internal').events.filter(kind='access_granted').count(), 1)

    def test_decoded_password_waits_for_explicit_login_without_trace(self):
        self.post(self.endpoint('password-breaker'), {'action': 'login'}, 400)
        self.start()
        result = self.finish_at(500)
        self.assertTrue(result['connected'])
        self.assertFalse(result['authenticated'])
        self.assertFalse(result['trace_active'])
        self.assertEqual(result['password_result'], 'ready')
        self.post(self.endpoint('password-breaker'), {'action': 'start'}, 400)
        result = self.post(self.endpoint('password-breaker'), {'action': 'login'})
        self.assertTrue(result['authenticated'])
        self.assertTrue(result['trace_active'])

    def test_duplicate_start_does_not_charge_twice_or_restart(self):
        first = self.start()
        self.post(self.endpoint('password-breaker'), {'action': 'start'}, 400)
        second = self.refresh()
        self.assertEqual(first['password_break'], second['password_break'])
        self.assertEqual(first['balance'], second['balance'])

    def test_cancellation_keeps_charge_and_prevents_access(self):
        start = self.start()
        result = self.post(self.endpoint('password-breaker'), {'action': 'cancel'})
        self.assertEqual(start['balance'], result['balance'])
        self.assertFalse(result['authenticated'])
        self.assertIsNone(result['password_break'])
        self.assertEqual(result['password_result'], 'cancelled')
        self.assertFalse(result['trace_active'])

    def test_stop_cancels_and_reopening_does_not_resume(self):
        self.start()
        result = self.post(self.endpoint('applications'), {'action': 'close', 'application': 'terminal'})
        self.assertIsNone(result['password_break'])
        result = self.launch('cracker-1-standard')
        self.assertFalse(result['authenticated'])
        self.assertIsNone(result['password_break'])

    def test_disconnecting_cancels_pending_attempt_without_contract_failure(self):
        self.start()
        result = self.cmd('disconnect')
        self.assertFalse(result['connected'])
        self.assertIsNotNone(result['active_contract'])
        self.assertIsNone(result['password_break'])
        self.assertFalse(self.cmd('connect helix-0.internal')['authenticated'])

    def test_insufficient_capability_fails_after_duration_without_trace(self):
        self.slot.server_states.filter(address='helix-0.internal').update(security=2)
        self.start()
        result = self.finish_at()
        self.assertEqual(result['password_result'], 'failed')
        self.assertFalse(result['authenticated'])
        self.assertFalse(result['trace_active'])
        self.assertIn('insufficient', self.log_text(result))

    def test_missing_scan_no_tool_or_insufficient_funds_reject_start(self):
        self.slot.refresh_from_db()
        self.slot.mission_state['scanned'] = False
        self.slot.save()
        self.post(self.endpoint('password-breaker'), {'action': 'start'}, 400)
        self.cmd('scan helix-0.internal', 'mapper')
        SaveSlot.objects.filter(pk=self.slot.pk).update(balance=0)
        self.post(self.endpoint('password-breaker'), {'action': 'start'}, 400)
        self.post(self.endpoint('applications'), {'action': 'close', 'application': 'terminal'})
        self.post(self.endpoint('password-breaker'), {'action': 'start'}, 400)
        self.assertIsNone(self.refresh()['password_break'])

    def test_reload_retains_same_attempt_and_slot_ownership_is_enforced(self):
        first = self.start()
        self.assertEqual(first['password_break'], self.refresh()['password_break'])
        stranger = get_user_model().objects.create_user('stranger', password='test-passphrase-long')
        client = Client()
        client.force_login(stranger)
        self.post(self.endpoint('password-breaker'), {'action': 'cancel'}, 404, client=client)
        self.assertEqual(first['password_break'], self.refresh()['password_break'])

    def test_faster_cpu_shortens_attempt_and_software_switch_cancels_it(self):
        slow = self.start()['password_break']['duration']
        self.post(self.endpoint('password-breaker'), {'action': 'cancel'})
        self.cmd('disconnect')
        self.slot.refresh_from_db()
        self.slot.equipment['cpu'] = 'cpu-2-standard'
        self.slot.installed_software.append('cracker-1-compact')
        self.slot.save()
        self.cmd('connect helix-0.internal')
        self.assertLess(self.start()['password_break']['duration'], slow)
        result = self.launch('cracker-1-compact')
        self.assertIsNone(result['password_break'])


class IntegratedLogcleanerTests(APIHelpers, TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('logcleaner')
        self.client.force_login(user)
        self.slot = SaveSlot.objects.create(user=user, position=1, alias='logcleaner')

    def test_logcleaner_is_owned_software_but_not_a_standalone_process(self):
        self.post(self.endpoint('applications'), {'action': 'launch', 'product_id': 'cleaner-1-standard'}, 400)
        self.assertIn('cleaner-1-standard', self.refresh()['installed_software'])
        self.assertTrue(PRODUCTS['cleaner-1-standard']['name'].startswith('Logcleaner'))

    def test_cleanup_runs_inside_primary_terminal_and_uses_license_compute(self):
        self.gain_access()
        self.slot.refresh_from_db()
        work = self.slot.mission_state['work']
        result = self.cmd('logcleaner cleaner-1-standard')
        self.assertIn('Remote access logs erased', result['mission_log'][-1]['text'])
        self.assertEqual(result['mission_log'][-1]['app'], 'terminal')
        self.assertNotIn('cleaner', [app['id'] for app in result['running_apps']])
        self.slot.refresh_from_db()
        self.assertFalse(self.slot.mission_state['dirty'])
        self.assertGreater(self.slot.mission_state['work'], work)
        self.assertFalse(self.slot.server_states.get(address='helix-0.internal').remote_logs)

    def test_cleanup_requires_login_owned_license_funds_and_free_memory(self):
        self.scan_and_connect()
        self.assertIn('log in', self.cmd('logcleaner')['mission_log'][-1]['text'])
        self.launch('cracker-1-standard')
        self.cmd('crack 22', 'cracker')
        self.assertIn('license is required', self.cmd('logcleaner cleaner-5-standard')['mission_log'][-1]['text'])
        SaveSlot.objects.filter(pk=self.slot.pk).update(balance=0)
        self.assertIn('Insufficient CPH', self.cmd('logcleaner')['mission_log'][-1]['text'])
        self.slot.refresh_from_db()
        self.slot.balance = 500
        self.slot.running_apps['monitor'] = 'monitor-1-standard'
        self.slot.running_apps['atlas'] = 'atlas'
        self.slot.installed_software.append('monitor-1-standard')
        self.slot.save()
        from unittest.mock import patch
        from .catalog import HARDWARE
        with patch.dict(HARDWARE[self.slot.equipment['memory']], {'ram':2}):
            self.assertIn('Not enough free RAM', self.cmd('logcleaner')['mission_log'][-1]['text'])
        self.slot.refresh_from_db()
        self.assertTrue(self.slot.mission_state['dirty'])
        self.assertNotIn('cleaner', self.slot.running_apps)

    def test_cleanup_capability_failure_retains_remote_logs(self):
        self.gain_access()
        self.slot.server_states.filter(address='helix-0.internal').update(security=2)
        result = self.cmd('logcleaner')
        self.assertIn('insufficient', result['mission_log'][-1]['text'])
        self.assertTrue(self.slot.server_states.get(address='helix-0.internal').remote_logs)

    def test_stale_decoded_password_cannot_login_to_a_changed_service(self):
        self.scan_and_connect()
        self.launch('cracker-1-standard')
        self.post(self.endpoint('password-breaker'), {'action': 'start'})
        self.slot.refresh_from_db()
        self.slot.mission_state['password_break']['finishes_at'] = timezone.now().isoformat()
        self.slot.save()
        self.assertEqual(self.refresh()['password_result'], 'ready')
        self.slot.server_states.filter(address='helix-0.internal').update(port=2222)
        self.post(self.endpoint('password-breaker'), {'action': 'login'}, 400)
        self.assertFalse(self.refresh()['authenticated'])


class IntegratedLogcleanerMigrationTests(TransactionTestCase):
    def test_migration_retires_process_and_panel_but_keeps_licenses_and_other_progress(self):
        executor = MigrationExecutor(connection)
        executor.migrate([('game', '0007_saveslot_workspace_layout_and_more')])
        try:
            old = executor.loader.project_state([('game', '0007_saveslot_workspace_layout_and_more')]).apps
            user = old.get_model('auth', 'User').objects.create(username='cleaner-veteran')
            terminal = dict(id='terminal', product_id='terminal', x=0, y=0, w=6, h=5)
            cleaner = dict(id='cleaner', product_id='cleaner-1-standard', x=6, y=0, w=6, h=5)
            slot = old.get_model('game', 'SaveSlot').objects.create(user_id=user.pk, position=1, alias='Veteran', balance=7654, field_notes='Keep this notebook', installed_software=['cleaner-1-standard', 'cleaner-2-compact'], running_apps={'terminal':'terminal', 'cleaner':'cleaner-1-standard'}, workspace_layout=[terminal, cleaner], workspace_revision=7)
            executor = MigrationExecutor(connection)
            executor.migrate([('game', '0008_integrated_logcleaner')])
            updated = executor.loader.project_state([('game', '0008_integrated_logcleaner')]).apps.get_model('game', 'SaveSlot').objects.get(pk=slot.pk)
            self.assertEqual(updated.balance, 7654)
            self.assertEqual(updated.field_notes, 'Keep this notebook')
            self.assertEqual(updated.installed_software, ['cleaner-1-standard', 'cleaner-2-compact'])
            self.assertEqual(updated.running_apps, {'terminal': 'terminal'})
            self.assertEqual(updated.workspace_layout, [terminal])
            self.assertEqual(updated.workspace_revision, 8)
        finally:
            restore = MigrationExecutor(connection)
            restore.migrate(restore.loader.graph.leaf_nodes())


class TerminalCartographTests(APIHelpers, TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('terminal-scanner')
        self.client.force_login(user)
        self.slot = SaveSlot.objects.create(user=user, position=1, alias='scanner')
        self.launch('terminal')

    def test_scan_uses_owned_software_without_leaving_a_process_running(self):
        self.reserve()
        before = self.refresh()
        result = self.cmd('scan helix-0.internal')
        self.assertIn('22/tcp  OPEN', result['mission_log'][-1]['text'])
        self.assertEqual(result['mission_log'][-1]['app'], 'terminal')
        self.assertEqual(result['balance'], before['balance'] - 2)
        self.assertNotIn('mapper', [app['id'] for app in result['running_apps']])
        self.assertEqual(result['ram_used'], before['ram_used'])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.mission_state['scanned_host'], 'helix-0.internal')
        self.cmd('connect helix-0.internal')
        self.launch('cracker-1-standard')
        self.assertTrue(self.cmd('crack 22', 'cracker')['authenticated'])

    def test_running_mapper_is_reused_and_standalone_output_is_unchanged(self):
        self.reserve()
        self.launch('mapper-1-standard')
        standalone = self.cmd('scan helix-0.internal', 'mapper')['mission_log'][-1]['text']
        result = self.cmd('scan helix-0.internal')
        self.assertEqual(result['mission_log'][-1]['text'], standalone)
        self.assertEqual(result['applet_preferences']['mapper'], 'mapper-1-standard')

    def test_scan_requires_license_funds_memory_and_capability(self):
        self.reserve()
        self.slot.refresh_from_db()
        self.slot.installed_software = []
        self.slot.save()
        self.assertIn('Cartograph license is required', self.cmd('scan helix-0.internal')['mission_log'][-1]['text'])
        self.slot.refresh_from_db()
        self.slot.installed_software = ['mapper-1-standard']
        self.slot.balance = 0
        self.slot.save()
        self.assertIn('Insufficient CPH', self.cmd('scan helix-0.internal')['mission_log'][-1]['text'])
        self.slot.refresh_from_db()
        self.slot.balance = 1000
        self.slot.equipment['memory'] = 'memory-1-specialist'
        self.slot.running_apps = {'terminal': 'terminal', 'cracker': 'cracker-5-standard', 'decryptor': 'decryptor-5-standard', 'atlas': 'atlas'}
        self.slot.save()
        from unittest.mock import patch
        from .catalog import HARDWARE
        with patch.dict(HARDWARE[self.slot.equipment['memory']], {'ram':2}):
            self.assertIn('Not enough free RAM', self.cmd('scan helix-0.internal')['mission_log'][-1]['text'])
        self.slot.refresh_from_db()
        self.slot.running_apps = {'terminal': 'terminal'}
        self.slot.save()
        self.cmd('scan helix-0.internal')
        self.slot.server_states.filter(address='helix-0.internal').update(security=2)
        self.assertIn('insufficient', self.cmd('scan helix-0.internal')['mission_log'][-1]['text'])

    def test_logged_out_file_commands_are_explicit_before_and_after_connect(self):
        self.assertIn('LOCAL FILESYSTEM', self.cmd('ls')['mission_log'][-1]['text'])
        self.assertIn('not logged in', self.cmd('get research.dat')['mission_log'][-1]['text'])
        self.assertIn('Local file not found', self.cmd('rm research.dat')['mission_log'][-1]['text'])
        self.reserve()
        self.cmd('connect helix-0.internal')
        for command in ('ls', 'get research.dat', 'rm research.dat'):
            self.assertIn('not logged in', self.cmd(command)['mission_log'][-1]['text'])


class LocalFilesystemTests(APIHelpers, TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('local-fs')
        self.client.force_login(user)
        self.slot = SaveSlot.objects.create(user=user, position=1, alias='Local')

    def download(self):
        self.gain_access()
        result = self.cmd('get research.dat')
        self.clean_exit()
        return result

    def test_download_survives_delivery_and_can_be_removed_to_reclaim_space(self):
        downloaded = self.download()
        self.assertEqual(downloaded['storage_used'], 24)
        self.assertEqual(len(downloaded['local_files']), 1)
        result = self.cmd('submit')
        self.assertIn('Delivery verified', result['mission_log'][-1]['text'])
        self.assertEqual(result['storage_used'], 24)
        self.assertIn('research.dat', self.cmd('ls')['mission_log'][-1]['text'])
        result = self.cmd('rm research.dat')
        self.assertIn('Reclaimed 24 MB', result['mission_log'][-1]['text'])
        self.assertEqual(result['storage_used'], 0)
        self.assertEqual(self.refresh()['local_files'], [])

    def test_removing_delivery_file_before_submit_invalidates_proof(self):
        self.download()
        self.cmd('rm research.dat')
        result = self.cmd('submit')
        self.assertIn('Broker rejected', result['mission_log'][-1]['text'])
        self.assertEqual(result['completed'], 0)

    def test_repeated_download_replaces_same_copy_and_remote_rm_keeps_local_copy(self):
        self.gain_access()
        first = self.cmd('get research.dat')
        second = self.cmd('get research.dat')
        self.assertEqual(first['local_files'][0]['id'], second['local_files'][0]['id'])
        self.assertEqual(second['storage_used'], 24)
        self.cmd('rm research.dat')
        self.assertEqual(self.refresh()['storage_used'], 24)
        self.clean_exit()
        self.assertIn('research.dat', self.cmd('ls')['mission_log'][-1]['text'])

    def test_storage_limit_accounts_for_all_local_files(self):
        self.gain_access()
        self.slot.refresh_from_db()
        self.slot.local_files = [dict(id='big', name='old.dat', size=150, source='old.internal', source_path='old.dat')]
        self.slot.save()
        result = self.cmd('get research.dat')
        self.assertIn('Local storage full', result['mission_log'][-1]['text'])
        self.assertEqual(result['storage_used'], 150)
        self.assertEqual(len(result['local_files']), 1)

    def test_filename_collisions_preserve_both_sources(self):
        from .mechanics import copy_to_local
        self.slot.local_files = [dict(id='old', name='research.dat', size=10, source='other.internal', source_path='research.dat')]
        entry = copy_to_local(self.slot, {**CONTRACT_BY_ID['0-0'], 'size': 24})
        self.assertEqual(entry['name'], 'research_2.dat')
        self.assertEqual({entry['name'] for entry in self.slot.local_files}, {'research.dat', 'research_2.dat'})

    def test_smaller_drive_cannot_be_fitted_if_files_do_not_fit(self):
        self.slot.equipment['storage'] = 'storage-2-standard'
        self.slot.local_files = [dict(id='large', name='large.dat', size=200, source='old.internal', source_path='large.dat')]
        self.slot.save()
        self.post(self.endpoint('loadout'), {'action': 'equip', 'product_id': 'storage-1-standard'}, 400)

    def test_other_slots_are_independent_and_restart_clears_files(self):
        self.download()
        other = SaveSlot.objects.create(user=self.slot.user, position=2, alias='Other')
        self.assertEqual(self.client.get(f'/api/slots/{other.pk}/').json()['local_files'], [])
        self.post(self.endpoint('restart'), {'confirmation': 'Local'})
        self.assertEqual(self.refresh()['local_files'], [])
        self.assertEqual(self.refresh()['storage_used'], 0)


class TraceClockTests(APIHelpers, TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('trace-clock')
        self.client.force_login(user)
        self.slot = SaveSlot.objects.create(user=user, position=1, alias='Clock')
        self.gain_access()

    def test_trace_clock_runs_without_monitor_but_deadline_requires_capable_monitor(self):
        from unittest.mock import patch
        self.slot.refresh_from_db()
        started = self.slot.mission_state['trace_started']
        result = self.refresh()
        self.assertEqual(result['trace_started_at'], started)
        self.assertIsNone(result['trace_deadline'])
        self.assertIsNone(result['trace_remaining'])
        self.slot.installed_software.append('monitor-1-standard')
        self.slot.save()
        result = self.launch('monitor-1-standard')
        deadline = result['trace_deadline']
        from django.utils.dateparse import parse_datetime
        self.assertIsNotNone(deadline)
        with patch('django.utils.timezone.now', return_value=timezone.now() + timedelta(seconds=5)):
            later = self.refresh()
        self.assertEqual(deadline, later['trace_deadline'])
        self.assertLessEqual(later['trace_remaining'], result['trace_remaining'] - 4)
        self.assertEqual(later['trace_started_at'], started)


class PublicProxyTests(APIHelpers, TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('public-proxies')
        self.client.force_login(user)
        self.slot = SaveSlot.objects.create(user=user, position=1, alias='Public')

    def test_new_public_proxies_can_be_bookmarked_routed_and_visited(self):
        data = self.refresh()
        nodes = [node for node in data['network_directory'] if node['id'].startswith('public-')]
        self.assertEqual(len(nodes), 40)
        self.assertEqual(len({node['address'] for node in nodes}), 40)
        self.assertTrue(all(node['rank'] == 0 and node['address'].endswith('.internal') and not node['exploitable'] for node in nodes))
        self.post(self.endpoint('directory'), {'action': 'add', 'server_id': 'public-01'})
        self.post(self.endpoint('route'), {'nodes': ['public-01']})
        self.reserve()
        self.cmd('connect helix-0.internal')
        self.assertEqual(self.slot.server_states.get(address=nodes[0]['address']).visits, 1)


class LocalFilesystemMigrationTests(TransactionTestCase):
    def test_current_legacy_download_is_preserved_with_its_delivery_proof(self):
        executor = MigrationExecutor(connection)
        executor.migrate([('game', '0008_integrated_logcleaner')])
        try:
            old = executor.loader.project_state([('game', '0008_integrated_logcleaner')]).apps
            user = old.get_model('auth', 'User').objects.create(username='download-veteran')
            slot = old.get_model('game', 'SaveSlot').objects.create(user_id=user.pk, position=1, alias='Archive', active_contract='0-0', mission_state={'recovered': True, 'local_size': 24, 'clean_exit': True})
            executor = MigrationExecutor(connection)
            executor.migrate([('game', '0009_saveslot_local_files')])
            updated = executor.loader.project_state([('game','0009_saveslot_local_files')]).apps.get_model('game','SaveSlot').objects.get(pk=slot.pk)
            self.assertEqual(updated.local_files[0]['name'], 'research.dat')
            self.assertEqual(updated.local_files[0]['size'], 24)
            self.assertEqual(updated.mission_state['local_file_id'], updated.local_files[0]['id'])
            self.assertNotIn('local_size', updated.mission_state)
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
            updated = SaveSlot.objects.get(pk=slot.pk)
            from .mechanics import execute
            updated.running_apps = {'terminal': 'terminal'}
            execute(updated, 'terminal', 'submit')
            self.assertEqual(updated.completed, 1)
            self.assertEqual(len(updated.local_files), 1)
        finally:
            restore = MigrationExecutor(connection)
            restore.migrate(restore.loader.graph.leaf_nodes())


class LocalDecryptionTests(APIHelpers, TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('local-decrypt')
        self.client.force_login(user)
        self.slot = SaveSlot.objects.create(user=user, position=1, alias='Rosetta')
        self.gain_access('0-1')
        self.cmd('get ledger.enc')
        self.clean_exit()

    def test_encrypted_copy_can_be_decrypted_locally_and_submitted_without_reconnecting(self):
        before = self.refresh()
        self.assertTrue(before['local_files'][0]['encrypted'])
        self.assertIn('archive is encrypted', self.cmd('submit')['mission_log'][-1]['text'])
        self.assertIn('Rosetta license is required', self.cmd('decrypt ledger.enc')['mission_log'][-1]['text'])
        self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': 'decryptor-1-standard'})
        result = self.cmd('decrypt ledger.enc')
        self.assertIn('decrypted locally', result['mission_log'][-1]['text'])
        self.assertFalse(result['connected'])
        self.assertFalse(result['local_files'][0]['encrypted'])
        self.assertNotIn('decryptor', [app['id'] for app in result['running_apps']])
        self.assertEqual(result['storage_used'], before['storage_used'])
        server = self.slot.server_states.get(address='helix-1.internal')
        self.assertTrue(server.files[0]['encrypted'])
        self.assertFalse(server.remote_logs)
        self.assertIn('Delivery verified', self.cmd('submit')['mission_log'][-1]['text'])
        self.assertEqual(len(self.refresh()['local_files']), 1)

    def test_rosetta_console_supports_local_decryption_and_enforces_funds_capability(self):
        self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': 'decryptor-1-standard'})
        self.launch('decryptor-1-standard')
        self.slot.refresh_from_db()
        self.slot.balance = 0
        self.slot.save()
        self.assertIn('Insufficient CPH', self.cmd('decrypt ledger.enc', 'decryptor')['mission_log'][-1]['text'])
        self.slot.refresh_from_db()
        self.slot.balance = 100
        self.slot.local_files[0]['security'] = 2
        self.slot.save()
        self.assertIn('insufficient', self.cmd('decrypt ledger.enc', 'decryptor')['mission_log'][-1]['text'])
        self.slot.refresh_from_db()
        self.slot.local_files[0]['security'] = 1
        self.slot.save()
        self.assertIn('decrypted locally', self.cmd('decrypt ledger.enc', 'decryptor')['mission_log'][-1]['text'])
        self.assertIn('not encrypted', self.cmd('decrypt ledger.enc', 'decryptor')['mission_log'][-1]['text'])


class FreshBrokerTests(APIHelpers, TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('fresh-broker')
        self.client.force_login(user)
        self.slot = SaveSlot.objects.create(user=user, position=1, alias='Fresh')

    def test_accept_removes_offer_and_due_replacement_has_new_identity_target_and_artifact(self):
        original = next(job for job in self.refresh()['contracts'] if job['target']=='helix-0.internal')
        accepted = self.reserve()
        self.assertEqual(len(accepted['contracts']),26)
        self.assertNotIn(original['target'],[job['target'] for job in accepted['contracts']])
        self.slot.refresh_from_db()
        self.slot.broker_pending[0]['due_at']=(timezone.now()-timedelta(seconds=1)).isoformat()
        self.slot.save()
        updated = self.refresh()
        new = next(job for job in updated['contracts'] if job['target'].startswith('broker-'))
        self.assertNotEqual(new['file'], original['file'])
        self.assertNotEqual(new['id'], original['id'])
        self.assertEqual(updated['active_contract']['target'], original['target'])
        self.assertEqual(len(self.refresh()['contracts']),27)
        self.slot.refresh_from_db()
        self.assertEqual(len(self.slot.broker_jobs),1)

    def test_replacement_is_playable_and_state_is_private_to_each_save(self):
        self.reserve(); self.cmd('abort')
        self.slot.refresh_from_db()
        self.slot.broker_pending[0]['due_at']=(timezone.now()-timedelta(seconds=1)).isoformat()
        self.slot.save()
        new=next(job for job in self.refresh()['contracts'] if job['target'].startswith('broker-'))
        self.cmd(f'accept {new["id"]}')
        self.cmd(f'scan {new["target"]}')
        self.cmd(f'connect {new["target"]}')
        self.cmd(f'crack {new["port"]}')
        matches = self.cmd(f'find {new["file"]}')['mission_log'][-1]['text'].splitlines()
        found = next(path for path in matches if not path.startswith('/backup/reference/'))
        self.cmd(f'get {found}')
        self.clean_exit()
        self.assertIn('Delivery verified',self.cmd('submit')['mission_log'][-1]['text'])
        other=SaveSlot.objects.create(user=self.slot.user,position=2,alias='Other')
        self.assertIn('helix-0.internal',[job['target'] for job in self.client.get(f'/api/slots/{other.pk}/').json()['contracts']])


class TerminalAppletTests(APIHelpers, TestCase):
    def setUp(self):
        user=get_user_model().objects.create_user('applet-runner')
        self.client.force_login(user)
        self.slot=SaveSlot.objects.create(user=user,position=1,alias='Applet')

    def test_commercial_services_do_not_run_as_processes_or_workspace_panels(self):
        for service in ['broker','bank','market']:
            self.post(self.endpoint('applications'),{'action':'launch','product_id':service},400)
            workspace=self.client.get(f'/api/slots/{self.slot.pk}/workspace/').json()
            self.post(self.endpoint('workspace'),{'layout':[dict(id=service,product_id=service,x=0,y=0,w=6,h=5)],'revision':workspace['revision'],'identity':workspace['identity']},400)
        self.assertEqual(self.refresh()['running_apps'],[])
        self.assertIn('Available:',self.cmd('balance','bank')['mission_log'][-1]['text'])
        self.assertEqual(self.refresh()['ram_used'],0)

    def test_selling_a_selected_license_clears_preferences_and_allows_an_owned_fallback(self):
        self.slot.installed_software += ['mapper-1-compact','cracker-1-compact']
        self.slot.save()
        for product in ['mapper-1-standard','cracker-1-standard']:
            self.launch(product)
            result=self.post(self.endpoint('loadout'),{'action':'sell','product_id':product})
            self.assertNotIn(PRODUCTS[product]['kind'],result['applet_preferences'])
        self.assertIsNone(self.refresh()['cracker_product'])
        self.reserve()
        self.assertIn('Scan complete',self.cmd('scan helix-0.internal')['mission_log'][-1]['text'])

    def test_all_software_is_rejected_as_process_and_preferences_persist_without_ram(self):
        for product in ['mapper-1-standard','cracker-1-standard','cleaner-1-standard']:
            self.post(self.endpoint('applications'),{'action':'launch','product_id':product},400)
        self.launch('mapper-1-standard')
        data=self.refresh()
        self.assertEqual(data['ram_used'],1)
        self.assertEqual(data['applet_preferences']['mapper'],'mapper-1-standard')
        self.assertEqual([app['id'] for app in data['running_apps']],['terminal'])
        self.post(self.endpoint('applets'),{'product_id':'rootkit-epic'},400)


class TerminalAppletMigrationTests(TransactionTestCase):
    def test_saved_tool_and_commercial_panels_become_terminal_preferences_and_page_services(self):
        executor=MigrationExecutor(connection)
        executor.migrate([('game','0009_saveslot_local_files')])
        try:
            old=executor.loader.project_state([('game','0009_saveslot_local_files')]).apps
            user=old.get_model('auth','User').objects.create(username='bundle-veteran')
            layout=[dict(id='terminal',product_id='terminal',x=0,y=0,w=6,h=5),dict(id='mapper',product_id='mapper-1-standard',x=6,y=0,w=6,h=5),dict(id='bank',product_id='bank',x=0,y=5,w=6,h=5)]
            slot=old.get_model('game','SaveSlot').objects.create(user_id=user.pk,position=1,alias='Bundled',running_apps={'terminal':'terminal','mapper':'mapper-1-standard','bank':'bank','market':'market'},workspace_layout=layout,field_notes='Preserve notebook',mission_log=[dict(app='mapper',text='Scan complete')])
            executor=MigrationExecutor(connection);executor.migrate(executor.loader.graph.leaf_nodes())
            saved=SaveSlot.objects.get(pk=slot.pk)
            self.assertEqual(saved.running_apps,{'terminal':'terminal'})
            self.assertEqual(saved.workspace_layout,[layout[0]])
            self.assertEqual(saved.applet_preferences['mapper'],'mapper-1-standard')
            self.assertEqual(saved.field_notes,'Preserve notebook')
            self.assertEqual(saved.mission_log[0]['app'],'terminal')
        finally:
            restore=MigrationExecutor(connection);restore.migrate(restore.loader.graph.leaf_nodes())


class IrcExploitTests(APIHelpers, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('irc-runner')
        self.client.force_login(self.user)
        self.slot = SaveSlot.objects.create(user=self.user, position=1, alias='Relay')
        self.launch('terminal')

    def irc(self, text, status=200):
        return self.post(self.endpoint('irc'), {'command': text}, status)

    def test_bot_broadcasts_follow_server_time_and_reads_do_not_charge(self):
        from unittest.mock import patch
        path = f'/api/{self.endpoint("irc")}/'
        first = self.client.get(path).json()
        self.assertTrue(any('EXPLOIT DROP | ssh-v1-r1-license' in row['text'] for row in first['irc']['messages']))
        with patch('django.utils.timezone.now', return_value=self.slot.created_at + timedelta(seconds=65)):
            later = self.client.get(path).json()
            self.slot.reputation = 700
            self.slot.save(update_fields=['reputation'])
            changed_offers = self.client.get(path).json()
            self.assertEqual(later['irc']['messages'], changed_offers['irc']['messages'])
        self.assertGreater(len(later['irc']['messages']), len(first['irc']['messages']))
        self.assertEqual(later['slot']['balance'], 1200)
        self.assertFalse(self.slot.ledger.exists())
        self.assertEqual([app['id'] for app in later['slot']['running_apps']], ['terminal'])

    def test_chat_help_purchases_inventory_and_bank_share_persistent_state(self):
        self.irc("I'm here, channel")
        self.irc('/help')
        self.irc('/msg hexdealer buy ssh-v1-r1-license')
        self.irc('/buy ssh-v1-r1-shot')
        data = self.irc('/pay hexdealer 90 ssh-v1-r1-shot')
        self.assertEqual(data['slot']['balance'], 660)
        self.assertEqual(next(item for item in data['irc']['inventory'] if item['id'] == 'ssh-v1-r1-shot')['quantity'], 2)
        self.assertEqual(self.slot.ledger.count(), 3)
        self.assertTrue(all(row.description.startswith('IRC trade') for row in self.slot.ledger.all()))
        restored = self.client.get(f'/api/{self.endpoint("irc")}/').json()
        self.assertEqual(data['irc']['inventory'], restored['irc']['inventory'])
        self.assertTrue(any(row['nick'] == 'Relay' and row['text'] == "I'm here, channel" for row in restored['irc']['messages']))
        self.irc('/inventory')
        self.assertIn('660 CPH', self.irc('/balance')['irc']['messages'][-1]['text'])
        self.assertTrue(any('ssh-v1-r1-license' in row['text'] for row in self.irc('/list')['irc']['messages']))

    def test_invalid_trades_are_atomic_and_do_not_move_funds(self):
        self.slot.refresh_from_db()
        original_messages = list(self.slot.irc_messages)
        for command in ['/buy missing', '/pay hexdealer 1 ssh-v1-r1-shot', '/msg packetwitch buy ssh-v1-r1-shot', '/buy ssh-v2-r1-license', '/pay hexdealer -90 ssh-v1-r1-shot', '/msg']:
            self.irc(command, 400)
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.balance, 1200)
        self.assertEqual(self.slot.exploit_inventory, {})
        self.assertEqual(self.slot.irc_messages, original_messages)
        self.assertFalse(self.slot.ledger.exists())
        self.irc('/buy ssh-v1-r1-license')
        self.irc('/buy ssh-v1-r1-license', 400)
        self.assertEqual(self.slot.ledger.count(), 1)

    def test_single_use_shell_requires_matching_scan_then_logs_and_traces(self):
        self.irc('/buy ssh-v1-r1-shot')
        self.cmd('exploit ssh-v1-r1-shot')
        self.scan_and_connect()
        self.slot.refresh_from_db()
        self.slot.mission_state['scanned'] = False
        self.slot.save()
        result = self.cmd('exploit ssh-v1-r1-shot')
        self.assertIn('Scan this server first', self.log_text(result))
        self.assertFalse(result['authenticated'])
        self.assertEqual(result['exploits'][0]['quantity'], 1)
        self.cmd('scan helix-0.internal')
        result = self.cmd('exploit ssh-v1-r1-shot')
        self.assertTrue(result['authenticated'])
        self.assertTrue(result['trace_active'])
        self.assertEqual(result['exploits'], [])
        self.assertTrue(self.slot.server_states.get(address='helix-0.internal').remote_logs)
        self.assertTrue(self.slot.server_states.get(address='helix-0.internal').events.filter(kind='exploit_shell').exists())
        self.assertIn('research.dat', self.log_text(self.cmd('ls')))
        self.clean_exit()
        self.assertIsNone(self.slot.server_states.get(address='helix-0.internal').maintenance_due)

    def test_lifetime_license_can_be_reused_without_another_purchase(self):
        self.irc('/buy ssh-v1-r1-license')
        for _ in range(2):
            self.cmd('connect harbor-library.internal')
            self.cmd('scan harbor-library.internal')
            data = self.cmd('exploit ssh-v1-r1-license')
            self.assertTrue(data['authenticated'])
            self.assertEqual(data['exploits'][0]['quantity'], 1)
            self.clean_exit()
        self.assertEqual(self.slot.ledger.filter(description__startswith='IRC trade').count(), 1)

    def test_protocol_and_patch_mismatch_and_low_ram_preserve_copies(self):
        self.irc('/buy ssh-v1-r1-shot')
        self.cmd('connect pacific-museum.internal')
        self.cmd('scan pacific-museum.internal')
        result = self.cmd('exploit ssh-v1-r1-shot')
        self.assertIn('Fingerprint mismatch: target is HTTP', self.log_text(result))
        self.assertEqual(result['exploits'][0]['quantity'], 1)
        self.cmd('disconnect')
        self.cmd('connect harbor-library.internal')
        self.cmd('scan harbor-library.internal')
        server = self.slot.server_states.get(address='harbor-library.internal')
        server.revision = 2
        server.port = 2222
        server.save()
        result = self.cmd('exploit ssh-v1-r1-shot')
        self.assertIn('current service fingerprint', result['mission_log'][-1]['text'])
        self.cmd('scan harbor-library.internal')
        result = self.cmd('exploit ssh-v1-r1-shot')
        self.assertIn('Fingerprint mismatch', result['mission_log'][-1]['text'])
        self.assertEqual(result['exploits'][0]['quantity'], 1)
        channel = self.client.get(f'/api/{self.endpoint("irc")}/').json()['irc']
        self.assertTrue(any(item['id'] == 'ssh-v1-r2-shot' for item in channel['offers']))
        self.irc('/buy ssh-v1-r2-shot')
        from unittest.mock import patch
        with patch('game.exploits.ram_used', return_value=12):
            result = self.cmd('exploit ssh-v1-r2-shot')
        self.assertIn('Insufficient free RAM', result['mission_log'][-1]['text'])
        self.assertFalse(result['authenticated'])
        result = self.cmd('exploit ssh-v1-r2-shot')
        self.assertTrue(result['authenticated'])
        self.assertEqual([item['id'] for item in result['exploits']], ['ssh-v1-r1-shot'])

    def test_http_and_rdp_fingerprints_work_on_their_own_services(self):
        for protocol, address in [('http', 'pacific-museum.internal'), ('rdp', 'summit-college.internal')]:
            key = f'{protocol}-v1-r1-shot'
            self.irc(f'/buy {key}')
            self.cmd(f'connect {address}')
            data = self.cmd(f'scan {address}')
            self.assertIn(f'{protocol.upper()} / auth-v1 / patch r1', data['mission_log'][-1]['text'])
            self.assertTrue(self.cmd(f'exploit {key}')['authenticated'])
            self.clean_exit()

    def test_channel_is_private_to_save_owner_and_restart_clears_stash(self):
        other = get_user_model().objects.create_user('other-irc-runner')
        other_slot = SaveSlot.objects.create(user=other, position=1, alias='Other')
        self.post(f'slots/{other_slot.id}/irc', {'command': '/buy ssh-v1-r1-license'}, 404)
        self.assertEqual(self.client.get(f'/api/slots/{other_slot.id}/irc/').status_code, 404)
        self.irc('/buy ssh-v1-r1-shot')
        second = SaveSlot.objects.create(user=self.user, position=2, alias='Second')
        self.assertEqual(self.client.get(f'/api/slots/{second.id}/irc/').json()['irc']['inventory'], [])
        data = self.post(self.endpoint('restart'), {'confirmation': 'Relay'})
        self.assertEqual(data['exploits'], [])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.irc_messages, [])
        self.assertEqual(self.slot.balance, 1200)

    def test_ambient_chatter_has_a_large_valid_local_library_and_coherent_threads(self):
        from .irc_chatter import content, ambient_message
        from string import Formatter
        data = content()
        self.assertGreaterEqual(len(set(data['members'])), 60)
        self.assertEqual(len(set(data['members'])), len(data['members']))
        self.assertGreaterEqual(len(data['threads']), 40)
        for thread in data['threads'] + data['templates']:
            self.assertEqual(len(thread), 3)
            self.assertTrue(all(isinstance(line, str) and line for line in thread))
        for thread in data['templates']:
            for line in thread:
                for _, field, _, _ in Formatter().parse(line):
                    if field:
                        self.assertIn(field, data['pools'])
        messages = [ambient_message(self.slot, index) for index in range(600)]
        self.assertGreater(len({message['text'] for message in messages}), 250)
        self.assertGreater(len({message['nick'] for message in messages}), 50)
        self.assertEqual(messages[13], ambient_message(self.slot, 13))
        for index in range(0, 600, 3):
            self.assertEqual(len({message['nick'] for message in messages[index:index+3]}), 3)

    def test_chat_arrives_every_ten_seconds_with_bounded_offline_catchup(self):
        from unittest.mock import patch
        path = f'/api/{self.endpoint("irc")}/'
        def read(seconds):
            with patch('django.utils.timezone.now', return_value=self.slot.created_at + timedelta(seconds=seconds)):
                return self.client.get(path).json()['irc']
        first = read(0)
        self.assertGreaterEqual(len(first['messages']), 24)
        self.assertGreaterEqual(len(first['members']), 65)
        self.assertEqual(first['messages'], read(9)['messages'])
        ten = read(10)
        self.assertEqual(len(ten['messages']), len(first['messages']) + 1)
        self.assertEqual(ten['messages'], read(19)['messages'])
        twenty = read(20)
        self.assertEqual(len(twenty['messages']), len(ten['messages']) + 1)
        thirty = read(30)
        self.assertEqual(len(thirty['messages']), len(twenty['messages']) + 2)
        drops = [row for row in thirty['messages'] if row.get('kind') == 'drop']
        self.assertEqual(len(drops), 2)
        days_later = read(5 * 24 * 60 * 60)
        self.assertEqual(len(days_later['messages']), 200)
        self.assertEqual(sum(row.get('kind') == 'chat' for row in days_later['messages']), 150)
        self.assertEqual(sum(row.get('kind') == 'drop' for row in days_later['messages']), 50)
        self.assertTrue(all(row['at'] > thirty['messages'][-1]['at'] for row in days_later['messages']))
        self.assertEqual(days_later['messages'], read(5 * 24 * 60 * 60)['messages'])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.balance, 1200)
        self.assertFalse(self.slot.ledger.exists())

    def test_scroll_cap_and_clear_preserve_stash_bank_and_delivery_cursor(self):
        from .exploits import add_message, SCROLLBACK_LIMIT
        from unittest.mock import patch
        self.irc('/buy ssh-v1-r1-license')
        self.slot.refresh_from_db()
        for index in range(800):
            add_message(self.slot, 'Relay', f'old chat {index}')
        self.slot.save()
        data = self.client.get(f'/api/{self.endpoint("irc")}/').json()['irc']
        self.assertLessEqual(len(data['messages']), SCROLLBACK_LIMIT)
        self.assertFalse(any('old chat 0' == message['text'] for message in data['messages']))
        self.slot.refresh_from_db()
        self.assertEqual(len(self.slot.irc_messages), SCROLLBACK_LIMIT)
        with patch('django.utils.timezone.now', return_value=self.slot.created_at + timedelta(seconds=300)):
            cleared = self.irc('/clear')
            reloaded = self.client.get(f'/api/{self.endpoint("irc")}/').json()
        self.assertEqual(cleared['irc']['messages'], reloaded['irc']['messages'])
        self.assertEqual(len(reloaded['irc']['messages']), 2)
        self.assertIn('Scrollback cleared', reloaded['irc']['messages'][-1]['text'])
        self.assertEqual(reloaded['slot']['balance'], 840)
        self.assertEqual(reloaded['irc']['inventory'][0]['id'], 'ssh-v1-r1-license')
        self.assertEqual(self.slot.ledger.count(), 1)
        with patch('django.utils.timezone.now', return_value=self.slot.created_at + timedelta(seconds=310)):
            next_tick = self.client.get(f'/api/{self.endpoint("irc")}/').json()['irc']
        self.assertEqual(len(next_tick['messages']), 3)
        self.assertEqual(next_tick['messages'][-1]['kind'], 'chat')

    def test_legacy_broadcast_cursor_is_preserved_when_chatter_is_added(self):
        from unittest.mock import patch
        self.slot.irc_messages = [dict(at=self.slot.created_at.isoformat(), nick='hexdealer', text='old exploit advert', tick=0)]
        self.slot.save()
        with patch('django.utils.timezone.now', return_value=self.slot.created_at + timedelta(seconds=20)):
            data = self.client.get(f'/api/{self.endpoint("irc")}/').json()['irc']
        self.assertEqual(sum(row['text'] == 'old exploit advert' for row in data['messages']), 1)
        self.assertFalse(any(row.get('kind') == 'drop' for row in data['messages']))
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.irc_state, dict(chat_tick=2, trade_tick=0))


    def test_regular_slot_refresh_advances_chat_without_opening_irc(self):
        from unittest.mock import patch
        self.slot.refresh_from_db()
        initial = list(self.slot.irc_messages)
        with patch('django.utils.timezone.now', return_value=self.slot.created_at + timedelta(seconds=35)):
            response = self.client.get(f'/api/slots/{self.slot.id}/')
        self.assertEqual(response.status_code, 200)
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.irc_state, dict(chat_tick=3, trade_tick=1))
        self.assertEqual(len(self.slot.irc_messages), len(initial) + 4)
        self.assertEqual(self.slot.running_apps, {'terminal': 'terminal'})
        self.assertEqual(self.slot.balance, 1200)

    def test_chat_continues_past_200_without_wiping_history_or_replaying_rows(self):
        from unittest.mock import patch
        path = f'/api/slots/{self.slot.id}/'
        with patch('django.utils.timezone.now', return_value=self.slot.created_at + timedelta(seconds=3000)):
            self.client.get(path)
        self.slot.refresh_from_db()
        old = list(self.slot.irc_messages)
        self.assertEqual(len(old), 200)
        with patch('django.utils.timezone.now', return_value=self.slot.created_at + timedelta(seconds=3010)):
            self.client.get(path)
            self.slot.refresh_from_db()
            new = list(self.slot.irc_messages)
            self.client.get(path)
        self.slot.refresh_from_db()
        self.assertEqual(len(new), 200)
        self.assertEqual(old[1:], new[:-1])
        self.assertEqual(self.slot.irc_messages, new)
        self.assertNotEqual(old[-1], new[-1])

    def test_existing_save_gets_current_history_even_if_irc_never_opened(self):
        old = SaveSlot.objects.create(user=self.user, position=2, alias='Old')
        SaveSlot.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=5))
        response = self.client.get(f'/api/slots/{old.pk}/')
        self.assertEqual(response.status_code, 200)
        old.refresh_from_db()
        self.assertEqual(len(old.irc_messages), 200)
        self.assertGreaterEqual(old.irc_state['chat_tick'], 5 * 24 * 60 * 6)
        self.assertEqual(old.balance, 1200)


class ExpandedServiceTests(APIHelpers, TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('service-runner')
        self.client.force_login(user)
        self.slot = SaveSlot.objects.create(user=user, position=1, alias='Services')

    def test_every_service_has_a_starter_affordable_contract_without_exploits(self):
        from .services import SERVICES
        seen = set()
        jobs = [job for job in CONTRACT_BY_ID.values() if job['rank'] == 0 and not job['encrypted'] and not job.get('delete_paths')]
        for job in jobs:
            with self.subTest(service=job['service'], contract=job['id']):
                # Each case starts with a normal runner's starter funding and tools.
                self.post(self.endpoint('restart'), {'confirmation': 'Services'})
                self.reserve(job['id'])
                data = self.cmd(f'scan {job["target"]}')
                self.assertIn('Lockpick admin login / matching exploit optional', data['mission_log'][-1]['text'])
                self.cmd(f'connect {job["target"]}')
                data = self.cmd(f'crack {job["port"]}')
                self.assertTrue(data['authenticated'])
                self.cmd(f'{"get" if job["objective"] == "retrieve" else "rm"} /{job.get("artifact_path", job["file"])}')
                self.clean_exit()
                data = self.cmd('submit')
                self.assertIn('Delivery verified', data['mission_log'][-1]['text'])
                self.assertGreater(data['balance'], 1200)
                self.assertEqual(data['exploits'], [])
                self.assertEqual(data['completed'], 1)
                seen.add(job['service'])
        # Plain HTTP is the existing encrypted archive contract; all new service
        # families have a complete starter-only path, including WordPress and PHP.
        self.assertEqual(seen, set(SERVICES) - {'http'})

    def test_all_services_have_matching_exploits_and_generic_http_cannot_match_apps(self):
        from .exploits import catalog, fingerprint
        from .services import SERVICES, service_fields
        self.slot.balance = 10000
        self.slot.running_apps = {'terminal': 'terminal'}
        self.slot.save()
        offers = catalog(self.slot)
        for key, entry in SERVICES.items():
            with self.subTest(service=key):
                if key == 'http':
                    # Existing encrypted target can be entered without buying Rosetta.
                    job = CONTRACT_BY_ID['0-1']
                else:
                    job = next(job for job in CONTRACT_BY_ID.values() if job['rank'] == 0 and job['service'] == key)
                offer = next(item for item in offers if item['protocol'] == entry['protocol'] and item['version'] == 1 and item['mode'] == 'shot')
                self.post(self.endpoint('irc'), {'command': f'/buy {offer["id"]}'})
                self.reserve(job['id'])
                self.cmd(f'connect {job["target"]}')
                self.cmd(f'scan {job["target"]}')
                data = self.cmd(f'exploit {offer["id"]}')
                self.assertTrue(data['authenticated'], data['mission_log'][-1]['text'])
                self.assertEqual(data['exploits'], [])
                self.clean_exit()
                self.cmd('abort')
        self.assertNotEqual(fingerprint(dict(port=443, security=1)), fingerprint(dict(security=1, **service_fields('wordpress'))))
        self.assertNotEqual(fingerprint(dict(security=1, **service_fields('wordpress'))), fingerprint(dict(security=1, **service_fields('php'))))

    def test_same_port_wrong_application_and_wrong_release_preserve_the_exploit(self):
        self.slot.balance = 10000
        self.slot.save()
        self.post(self.endpoint('irc'), {'command': '/buy http-v1-r1-shot'})
        self.post(self.endpoint('irc'), {'command': '/buy wordpress-6.4-v1-r1-shot'})
        self.reserve('0-3')
        self.cmd('connect helix-3.internal')
        self.cmd('scan helix-3.internal')
        data = self.cmd('exploit http-v1-r1-shot')
        self.assertFalse(data['authenticated'])
        self.assertIn('WordPress CMS 6.4', data['mission_log'][-1]['text'])
        self.assertEqual(len(data['exploits']), 2)
        server = self.slot.server_states.get(address='helix-3.internal')
        server.descriptor['service_version'] = '6.5'
        server.save()
        self.cmd('scan helix-3.internal')
        data = self.cmd('exploit wordpress-6.4-v1-r1-shot')
        self.assertFalse(data['authenticated'])
        self.assertEqual(len(data['exploits']), 2)
        self.assertIn('WordPress CMS 6.5', data['mission_log'][-1]['text'])
        offers = self.client.get(f'/api/{self.endpoint("irc")}/').json()['irc']['offers']
        self.assertTrue(any(item['id'] == 'wordpress-6.5-v1-r1-shot' for item in offers))
        self.post(self.endpoint('irc'), {'command': '/buy wordpress-6.5-v1-r1-shot'})
        self.assertTrue(self.cmd('exploit wordpress-6.5-v1-r1-shot')['authenticated'])

    def test_service_identity_and_release_survive_maintenance_and_new_scans(self):
        from .persistence import settle_world
        self.reserve('0-3')
        self.cmd('scan helix-3.internal')
        server = self.slot.server_states.get(address='helix-3.internal')
        server.maintenance_due = timezone.now() - timedelta(seconds=1)
        server.save()
        self.slot.refresh_from_db()
        settle_world(self.slot)
        self.cmd('connect helix-3.internal')
        data = self.cmd('scan helix-3.internal')
        self.assertIn('WordPress CMS 6.4 / auth-v1 / patch r2', data['mission_log'][-1]['text'])
        self.assertIn('8443/tcp', data['mission_log'][-1]['text'])
        offers = self.client.get(f'/api/{self.endpoint("irc")}/').json()['irc']['offers']
        self.assertTrue(any(item['id'] == 'wordpress-6.4-v1-r2-shot' for item in offers))

    def test_directory_and_contract_briefs_disclose_service_names(self):
        from .services import SERVICES
        data = self.refresh()
        self.assertEqual({job['service'] for job in data['contracts']}, set(SERVICES))
        self.assertTrue(all(job['service_name'] for job in data['contracts']))
        directory = data['network_directory']
        self.assertTrue(all(node['service_name'] for node in directory))
        self.assertTrue(set(SERVICES).issubset({node.get('service') for node in directory}))

    @override_settings(DEBUG=True)
    def test_offline_generator_can_choose_each_service_for_missions_and_servers(self):
        from .services import SERVICES
        from .models import GeneratedMission, DirectoryServer
        for key, entry in SERVICES.items():
            call_command('generate_content', 'missions', count=1, service=key, objective='retrieve', stdout=StringIO())
            call_command('generate_content', 'servers', count=1, service=key, stdout=StringIO())
        jobs = list(GeneratedMission.objects.values_list('data', flat=True))
        nodes = list(DirectoryServer.objects.filter(key__startswith='srv-').values_list('data', flat=True))
        self.assertEqual({job['service'] for job in jobs}, set(SERVICES))
        self.assertEqual({node['service'] for node in nodes}, set(SERVICES))
        self.assertTrue(all(job['port'] == SERVICES[job['service']]['port'] for job in jobs))

    def test_unknown_ports_do_not_silently_become_ssh_exploit_targets(self):
        from .services import fingerprint
        self.assertEqual(fingerprint(dict(port=9999, security=1))['protocol'], 'UNKNOWN')

    def test_existing_lifetime_ssh_licenses_without_release_field_still_work(self):
        self.post(self.endpoint('irc'), {'command': '/buy ssh-v1-r1-license'})
        self.slot.refresh_from_db()
        self.slot.exploit_inventory['ssh-v1-r1-license'].pop('release')
        self.slot.save()
        self.reserve('0-0')
        self.cmd('connect helix-0.internal')
        self.cmd('scan helix-0.internal')
        self.assertTrue(self.cmd('exploit ssh-v1-r1-license')['authenticated'])


    def test_directory_keeps_the_service_profile_of_an_existing_discovered_server(self):
        from .world import target_for_server, get_server
        from .persistence import ensure_server
        target = target_for_server(get_server('public-09'))
        target.pop('service')
        target.pop('service_version')
        target['port'] = 443  # An HTTP server discovered before profile expansion.
        ensure_server(self.slot, target)
        data = self.refresh()
        node = next(node for node in data['network_directory'] if node['id'] == 'public-09')
        self.assertEqual(node['service_name'], 'HTTP')
        self.assertEqual(node['service'], 'http')
        self.launch('terminal')
        self.cmd('connect atlantic-port.internal')
        data = self.cmd('scan atlantic-port.internal')
        self.assertIn('Fingerprint: HTTP / auth-v1 / patch r1', data['mission_log'][-1]['text'])


class RemoteFilesystemTests(APIHelpers, TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('file-runner')
        self.client.force_login(user)
        self.slot = SaveSlot.objects.create(user=user, position=1, alias='Files')

    def test_every_service_gets_a_deterministic_bounded_background_tree(self):
        from .filesystem import build_tree
        from .services import SERVICES, service_fields
        for key in SERVICES:
            target = dict(target=f'{key}.internal', file='payload.dat', size=24, encrypted=False, security=1, **service_fields(key))
            files = build_tree(target)
            self.assertEqual(files, build_tree(target))
            self.assertTrue(files[0]['artifact'])
            self.assertGreaterEqual(sum(item.get('type') == 'file' for item in files), 16)
            self.assertGreaterEqual(sum(item.get('type') == 'directory' for item in files), 7)
            self.assertLess(len(files), 80)
            self.assertEqual(len({item['name'] for item in files}), len(files))

    def test_navigation_scopes_listings_and_does_not_disclose_hidden_paths_before_login(self):
        self.reserve('0-3')
        data = self.cmd('scan helix-3.internal')
        self.assertNotIn('var/www/cms-backup.dat', data['mission_log'][-1]['text'])
        self.assertNotIn('artifact_path', data['active_contract'])
        server = self.slot.server_states.get(address='helix-3.internal')
        self.assertEqual(server.observed['files'], [])
        self.cmd('connect helix-3.internal')
        self.cmd('crack 443')
        root = self.cmd('ls')
        self.assertIn('var/', root['mission_log'][-1]['text'])
        self.assertNotIn('cms-backup.dat', root['mission_log'][-1]['text'])
        self.assertNotIn('/var/www/cms-backup.dat', [item['path'] for item in root['remote_entries']])
        self.cmd('cd /var/www')
        self.assertEqual(self.cmd('pwd')['mission_log'][-1]['text'], '/var/www')
        data = self.cmd('ls')
        self.assertIn('cms-backup.dat', data['mission_log'][-1]['text'])
        self.assertIn('wp-content/', data['mission_log'][-1]['text'])
        self.assertIn('/var/www/cms-backup.dat', [item['path'] for item in data['remote_entries']])
        self.assertIn('WordPress front controller', self.cmd('cat ./index.php')['mission_log'][-1]['text'])
        self.assertEqual(self.cmd('cd ..')['remote_cwd'], '/var')
        self.assertEqual(self.cmd('cd ../../../../../')['remote_cwd'], '/')
        self.assertIn('Directory not found', self.cmd('cd /missing')['mission_log'][-1]['text'])
        self.assertEqual(self.refresh()['remote_cwd'], '/')

    def test_same_named_reference_copy_never_fulfils_retrieval_and_real_evidence_is_retained(self):
        self.gain_access('0-0')
        data = self.cmd('get /backup/reference/research.dat')
        self.assertEqual(data['local_files'][0]['name'], 'research.dat')
        self.assertNotIn('local_file_id', SaveSlot.objects.get(pk=self.slot.pk).mission_state)
        self.clean_exit()
        self.assertIn('Broker rejected', self.cmd('submit')['mission_log'][-1]['text'])
        self.cmd('connect helix-0.internal')
        self.cmd('crack 22')
        data = self.cmd('get /research.dat')
        real = next(entry for entry in data['local_files'] if entry['source_path'] == 'research.dat')
        self.assertEqual(real['name'], 'research_2.dat')
        self.cmd('get /backup/reference/research.dat')
        self.assertEqual(SaveSlot.objects.get(pk=self.slot.pk).mission_state['local_file_id'], real['id'])
        self.clean_exit()
        self.assertIn('Delivery verified', self.cmd('submit')['mission_log'][-1]['text'])

    def test_deleting_decoy_does_not_complete_contract_and_background_changes_persist(self):
        self.gain_access('0-2')
        self.cmd('rm /backup/reference/audit.log')
        self.cmd('rm /home/admin/todo.txt')
        self.clean_exit()
        self.assertIn('Broker rejected', self.cmd('submit')['mission_log'][-1]['text'])
        self.cmd('connect helix-2.internal')
        self.cmd('crack 22')
        self.assertIn('File not found', self.cmd('cat /home/admin/todo.txt')['mission_log'][-1]['text'])
        self.cmd('rm /audit.log')
        self.assertIn('README.txt', self.cmd('ls')['mission_log'][-1]['text'])
        self.clean_exit()
        self.assertIn('Delivery verified', self.cmd('submit')['mission_log'][-1]['text'])

    def test_browse_and_search_cost_trace_work_without_adding_cash_charges(self):
        self.gain_access('0-0')
        self.slot.refresh_from_db()
        balance = self.slot.balance
        before = self.slot.mission_state['work']
        self.cmd('ls')
        self.cmd('cd /backup')
        self.cmd('cat manifest.txt')
        data = self.cmd('find *.dat')
        self.assertIn('/backup/reference/research.dat', data['mission_log'][-1]['text'])
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.mission_state['work'] - before, 12)
        self.assertEqual(self.slot.balance, balance)
        self.assertTrue(self.slot.mission_state['dirty'])
        self.cmd('cd /')
        self.assertIn('directory removal', self.cmd('rm /backup')['mission_log'][-1]['text'].lower())
        self.assertEqual(self.cmd('pwd')['mission_log'][-1]['text'], '/')

    @override_settings(DEBUG=True)
    def test_generator_places_wordpress_database_at_explicit_path_and_validates_options(self):
        from .models import GeneratedMission
        call_command('generate_content', 'missions', count=1, service='wordpress', objective='retrieve', artifact_dir='/var/www', filename='users.db', stdout=StringIO())
        job = GeneratedMission.objects.get().data
        self.assertEqual(job['file'], 'users.db')
        self.assertEqual(job['artifact_path'], 'var/www/users.db')
        self.reserve(public_code(job['id']))
        self.cmd(f'connect {job["target"]}')
        self.cmd(f'scan {job["target"]}')
        self.cmd('crack 443')
        self.cmd('cd /var/www')
        self.assertIn('users.db', self.cmd('ls')['mission_log'][-1]['text'])
        self.cmd('get users.db')
        self.clean_exit()
        self.assertIn('Delivery verified', self.cmd('submit')['mission_log'][-1]['text'])
        for options in [dict(filename='../bad.db'), dict(filename='bad\\name'), dict(artifact_dir='relative'), dict(filename='bad\nname')]:
            with self.assertRaises(CommandError):
                call_command('generate_content', 'missions', count=1, stdout=StringIO(), **options)
        with self.assertRaises(CommandError):
            call_command('generate_content', 'servers', count=1, placement='nested', stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_generator_root_and_nested_placements_are_service_aware(self):
        from .models import GeneratedMission
        call_command('generate_content', 'missions', count=1, service='rdp', placement='nested', objective='retrieve', stdout=StringIO())
        nested = GeneratedMission.objects.get().data
        self.assertTrue(nested['artifact_path'].startswith('Users/admin/Documents/'))
        call_command('generate_content', 'missions', count=1, service='wordpress', placement='root', objective='retrieve', stdout=StringIO())
        root = GeneratedMission.objects.exclude(pk=nested['id']).get().data
        self.assertEqual(root['artifact_path'], root['file'])

    def test_rdp_paths_and_encrypted_nested_archives_work_with_local_decryption(self):
        from .persistence import ensure_server
        self.launch('terminal')
        self.slot.refresh_from_db()
        self.slot.installed_software.append('decryptor-1-standard')
        self.slot.save()
        self.reserve('0-5')
        target = dict(CONTRACT_BY_ID['0-5'])
        server = ensure_server(self.slot, target)
        server.files[0]['encrypted'] = True
        server.save()
        self.cmd('connect helix-5.internal')
        self.cmd('scan helix-5.internal')
        self.cmd('crack 3389')
        self.cmd('cd /Users/admin/Documents')
        self.cmd('get desktop-archive.dat')
        self.clean_exit()
        self.assertIn('archive is encrypted', self.cmd('submit')['mission_log'][-1]['text'])
        self.cmd('decrypt desktop-archive.dat')
        self.assertIn('Delivery verified', self.cmd('submit')['mission_log'][-1]['text'])

    def test_decrypting_one_file_does_not_decrypt_other_downloads(self):
        self.gain_access('0-1')
        self.slot.refresh_from_db()
        self.slot.installed_software.append('decryptor-1-standard')
        self.slot.save()
        self.cmd('decrypt /ledger.enc')
        server = self.slot.server_states.get(address='helix-1.internal')
        server.files.append(dict(name='var/www/decoy.enc', original='var/www/decoy.enc', type='file', size=2, encrypted=True, present=True))
        server.save()
        data = self.cmd('get /var/www/decoy.enc')
        self.assertTrue(data['local_files'][0]['encrypted'])
        self.cmd('decrypt /var/www/decoy.enc')
        data = self.cmd('get /var/www/decoy.enc')
        self.assertFalse(data['local_files'][0]['encrypted'])

    def test_backdoor_summaries_do_not_disclose_unexplored_artifact_paths(self):
        self.gain_access('0-3')
        self.slot.refresh_from_db()
        self.slot.installed_software.append('rootkit-epic')
        self.slot.save()
        data = self.cmd('install')
        self.assertEqual(data['backdoors'][0]['target'], 'helix-3.internal')
        self.assertNotIn('file', data['backdoors'][0])
        self.assertNotIn('artifact_path', data['backdoors'][0])


class PopulatedFilesystemMigrationTests(TransactionTestCase):
    def test_old_primary_paths_and_deletions_survive_population(self):
        executor = MigrationExecutor(connection)
        executor.migrate([('game', '0013_saveslot_irc_state')])
        try:
            old = executor.loader.project_state([('game', '0013_saveslot_irc_state')]).apps
            user = old.get_model('auth', 'User').objects.create(username='fs-migration')
            slot = old.get_model('game', 'SaveSlot').objects.create(user_id=user.pk, position=1, alias='Legacy')
            artifact = dict(name='archive/r3/var/www/users.db', original='var/www/users.db', present=False, encrypted=True, size=24)
            old.get_model('game', 'ServerState').objects.create(slot_id=slot.pk, address='legacy.internal', descriptor=dict(target='legacy.internal', file='users.db', size=24, encrypted=True, security=1, port=443, service='wordpress'), files=[artifact], visits=4)
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
            from .models import ServerState
            server = ServerState.objects.get(address='legacy.internal')
            for key, value in artifact.items():
                self.assertEqual(server.files[0][key], value)
            self.assertGreater(len(server.files), 20)
            self.assertEqual(server.visits, 4)
            self.assertTrue(any(item['name'] == 'var/www/index.php' for item in server.files))
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())


class EraseAllCopiesTests(APIHelpers, TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('copy-cleaner')
        self.client.force_login(user)
        self.slot = SaveSlot.objects.create(user=user, position=1, alias='Cleaner')

    def mount(self, key='purge-0'):
        self.reserve(key)
        job = CONTRACT_BY_ID.get(key)
        if not job:
            self.slot.refresh_from_db()
            job = self.slot.broker_jobs[self.slot.active_contract]
        self.cmd(f'scan {job["target"]}')
        self.cmd(f'connect {job["target"]}')
        return self.cmd(f'crack {job["port"]}')

    def test_three_authored_jobs_have_real_named_primary_and_backup_copies(self):
        from .filesystem import build_tree
        jobs = [job for job in CONTRACT_BY_ID.values() if job.get('delete_paths')]
        self.assertEqual(len(jobs), 3)
        self.assertEqual({job['service'] for job in jobs}, {'ssh', 'wordpress', 'rdp'})
        for job in jobs:
            files = build_tree(job)
            self.assertIn(len(job['delete_paths']), (2, 3))
            for path in job['delete_paths']:
                self.assertTrue(next(entry for entry in files if entry['name'] == path)['present'])
                self.assertIn('/' + path, job['description'])
            self.assertFalse(any(entry['name'].startswith('backup/reference/') for entry in files))

    def test_primary_only_is_rejected_then_remaining_backup_receipt_completes_job(self):
        self.mount()
        data = self.cmd('rm /root/audit.txt')
        self.assertIn('Required copies: 1/2', data['mission_log'][-1]['text'])
        self.assertEqual([copy['deleted'] for copy in data['deletion_progress']], [True, False])
        self.clean_exit()
        rejected = self.cmd('submit')
        self.assertIn('/bak/audit.log', rejected['mission_log'][-1]['text'])
        self.assertEqual(rejected['completed'], 0)
        self.assertFalse(self.slot.ledger.filter(description__startswith='Contract payment').exists())
        self.cmd('connect ashfall-audit.internal')
        self.cmd('crack 22')
        self.cmd('cd /bak')
        data = self.cmd('rm ./audit.log')
        self.assertIn('Required copies: 2/2', data['mission_log'][-1]['text'])
        self.assertTrue(all(copy['deleted'] for copy in data['deletion_progress']))
        self.clean_exit()
        paid = self.cmd('submit')
        self.assertEqual(paid['completed'], 1)
        self.assertIn('Delivery verified', paid['mission_log'][-1]['text'])
        self.cmd('submit')
        self.assertEqual(self.slot.ledger.filter(description__startswith='Contract payment').count(), 1)

    def test_backup_first_and_unrelated_deletion_do_not_replace_primary_requirement(self):
        self.mount('purge-1')
        data = self.cmd('rm /backup/previous.dat')
        self.assertFalse(any(copy['deleted'] for copy in data['deletion_progress']))
        data = self.cmd('rm /backup/nightly/users.db')
        self.assertEqual([copy['deleted'] for copy in data['deletion_progress']], [False, True])
        self.clean_exit()
        self.assertIn('/var/www/users.db', self.cmd('submit')['mission_log'][-1]['text'])
        self.cmd('connect juniper-cms.internal')
        self.cmd('crack 443')
        self.cmd('rm /var/www/users.db')
        self.assertIn('Cannot deliver evidence while connected', self.cmd('submit')['mission_log'][-1]['text'])
        self.clean_exit()
        self.assertIn('Delivery verified', self.cmd('submit')['mission_log'][-1]['text'])

    def test_three_copy_rdp_job_requires_every_path(self):
        self.slot.installed_software += ['mapper-2-standard', 'cracker-2-standard', 'cleaner-2-standard']
        self.slot.save()
        self.mount('purge-2')
        paths = CONTRACT_BY_ID['purge-2']['delete_paths']
        for index, path in enumerate(reversed(paths), 1):
            data = self.cmd(f'rm /{path}')
            self.assertEqual(sum(copy['deleted'] for copy in data['deletion_progress']), index)
        self.clean_exit()
        self.assertIn('Delivery verified', self.cmd('submit')['mission_log'][-1]['text'])

    def test_restored_copies_invalidate_old_receipts_after_maintenance(self):
        self.mount()
        for path in CONTRACT_BY_ID['purge-0']['delete_paths']:
            self.cmd(f'rm /{path}')
        self.clean_exit()
        server = self.slot.server_states.get(address='ashfall-audit.internal')
        server.maintenance_due = timezone.now() - timedelta(seconds=1)
        server.save()
        data = self.refresh()
        self.assertTrue(all(not copy['deleted'] for copy in data['deletion_progress']))
        self.assertIn('/archive/r2/bak/audit.log', self.cmd('submit')['mission_log'][-1]['text'])
        self.cmd('connect ashfall-audit.internal')
        self.cmd('scan ashfall-audit.internal')
        self.cmd('crack 2222')
        for path in CONTRACT_BY_ID['purge-0']['delete_paths']:
            self.cmd(f'rm /archive/r2/{path}')
        self.clean_exit()
        self.assertIn('Delivery verified', self.cmd('submit')['mission_log'][-1]['text'])

    def test_receipt_flags_cannot_pay_for_copies_that_still_exist(self):
        self.mount()
        self.clean_exit()
        self.slot.refresh_from_db()
        self.slot.mission_state.update(deleted=True, deletion_receipts=CONTRACT_BY_ID['purge-0']['delete_paths'])
        self.slot.save()
        self.assertIn('deletion proof missing', self.cmd('submit')['mission_log'][-1]['text'])
        self.assertFalse(self.slot.ledger.filter(description__startswith='Contract payment').exists())

    @override_settings(DEBUG=True)
    def test_offline_generator_authors_multiple_backup_paths_and_rejects_invalid_jobs(self):
        from .models import GeneratedMission
        call_command('generate_content', 'missions', count=1, service='ssh', filename='audit.txt', artifact_dir='/root', delete_copy=['/bak/audit.log', '/backup/audit.txt'], stdout=StringIO())
        job = GeneratedMission.objects.get().data
        self.assertEqual(job['objective'], 'delete')
        self.assertEqual(job['delete_paths'], ['root/audit.txt', 'bak/audit.log', 'backup/audit.txt'])
        self.assertIn('/bak/audit.log', job['description'])
        for options in [dict(objective='retrieve'), dict(encrypted=True), dict(delete_copy=['relative']), dict(delete_copy=['/']),
                        dict(delete_copy=['/root/audit.txt']), dict(delete_copy=['/bak/audit.log', '/bak/./audit.log']), dict(delete_copy=['/backup']),
                        dict(delete_copy=[f'/bak/{n}.log' for n in range(5)])]:
            settings = dict(count=1, filename='audit.txt', artifact_dir='/root', delete_copy=['/bak/audit.log'], stdout=StringIO())
            settings.update(options)
            with self.assertRaises(CommandError):
                call_command('generate_content', 'missions', **settings)
        self.assertEqual(GeneratedMission.objects.count(), 1)

    def test_broker_replacement_retains_copy_requirements_with_fresh_paths(self):
        self.reserve('purge-0')
        self.cmd('abort')
        self.slot.refresh_from_db()
        self.slot.broker_pending[0]['due_at'] = (timezone.now() - timedelta(seconds=1)).isoformat()
        self.slot.save()
        new = next(job for job in self.refresh()['contracts'] if job['target'].startswith('broker-'))
        self.assertEqual(len(new['delete_paths']), 2)
        self.assertEqual(new['service'], 'ssh')
        self.assertTrue(set(new['delete_paths']).isdisjoint(CONTRACT_BY_ID['purge-0']['delete_paths']))
        self.assertIn('erase all copies', new['title'])
        self.mount(new['id'])
        for path in new['delete_paths']:
            self.cmd(f'rm /{path}')
        self.clean_exit()
        self.assertIn('Delivery verified', self.cmd('submit')['mission_log'][-1]['text'])
