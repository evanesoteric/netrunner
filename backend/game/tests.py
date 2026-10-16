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
        return self.post(self.endpoint('applications'), {'action': 'launch', 'product_id': product_id})

    def cmd(self, command, app='terminal'):
        if command.startswith('accept ') and command[7:] in CONTRACT_BY_ID:
            command = 'accept ' + public_code(command[7:])
        return self.post(self.endpoint('command'), {'application': app, 'command': command})

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
        self.launch('cleaner-1-standard')
        self.cmd('erase', 'cleaner')
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
        self.assertEqual(len(listed['contracts']), 6)
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
        self.assertEqual(len(numbers), 15)
        self.assertEqual(len(set(numbers)), 15)
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
        self.assertIn('Unknown shell command', self.log_text(response))
        self.assertFalse(self.slot.mission_state.get('scanned'))
        self.post(self.endpoint('applications'), {'action': 'launch', 'product_id': 'decryptor-5-standard'}, 400)

    def test_ram_limits_process_close_and_tool_variants(self):
        self.slot.installed_software += ['decryptor-1-standard', 'monitor-1-compact']
        self.slot.save()
        for product in ['terminal', 'mapper-1-standard', 'cracker-1-standard', 'cleaner-1-standard']:
            self.launch(product)
        self.post(self.endpoint('applications'), {'action': 'launch', 'product_id': 'decryptor-1-standard'}, 400)
        self.post(self.endpoint('applications'), {'action': 'close', 'application': 'mapper'})
        response = self.launch('monitor-1-compact')
        self.assertLessEqual(response['ram_used'], response['equipment']['memory']['ram'])

    def test_multiple_named_products_per_category_and_tier(self):
        self.assertEqual(len(PRODUCTS), 90)
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
        self.launch('cleaner-1-standard')
        self.cmd('erase', 'cleaner')
        self.cmd('ls')
        response = self.cmd('disconnect')
        self.assertIsNone(response['active_contract'])
        self.assertIn('Forensics recovered', self.log_text(response))
        self.assertEqual(response['completed'], 0)

    def test_encrypted_archive_requires_separate_decryptor(self):
        self.gain_access('0-1')
        response = self.cmd('get ledger.enc')
        self.assertIn('Archive encrypted', self.log_text(response))
        self.post(self.endpoint('applications'), {'action': 'close', 'application': 'mapper'})
        # End the session safely to buy a license; cracked files are preserved only in this game session.
        self.launch('cleaner-1-standard')
        self.cmd('erase', 'cleaner')
        self.cmd('disconnect')
        self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': 'decryptor-1-standard'})
        self.post(self.endpoint('applications'), {'action': 'close', 'application': 'cleaner'})
        self.launch('decryptor-1-standard')
        self.cmd('connect helix-1.internal')
        self.cmd('crack 443', 'cracker')
        response = self.cmd('decrypt ledger.enc', 'decryptor')
        self.assertIn('decrypted. Checksum intact', self.log_text(response))
        self.cmd('get ledger.enc')
        self.post(self.endpoint('applications'), {'action': 'close', 'application': 'decryptor'})
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
        SaveSlot.objects.filter(pk=self.slot.pk).update(mission_started=timezone.now() - timedelta(seconds=500))
        first = self.refresh()
        self.assertIsNone(first['active_contract'])
        self.assertEqual(first['balance'], self.refresh()['balance'])
        self.assertEqual(self.slot.ledger.filter(description__startswith='Contract failure').count(), 2)

    def test_cooldowns_use_server_time_and_jobs_return(self):
        self.reserve()
        self.cmd('abort')
        response = self.cmd('accept 0-0')
        self.assertIsNone(response['active_contract'])
        self.assertIn('still sourcing', self.log_text(response))
        SaveSlot.objects.filter(pk=self.slot.pk).update(contract_cooldowns={'0-0': (timezone.now() - timedelta(seconds=1)).isoformat()})
        self.assertEqual(self.cmd('accept 0-0')['active_contract']['id'], public_code('0-0'))

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

    def test_trace_monitor_exposes_time_only_while_running(self):
        self.post(self.endpoint('loadout'), {'action': 'buy', 'product_id': 'monitor-1-standard'})
        self.scan_and_connect()
        self.assertIsNone(self.refresh()['trace_remaining'])
        result = self.launch('monitor-1-standard')
        self.assertGreater(result['trace_remaining'], 0)
        self.post(self.endpoint('applications'), {'action': 'close', 'application': 'monitor'})
        self.assertIsNone(self.refresh()['trace_remaining'])

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
        for product in ['terminal', 'mapper-1-standard', 'cracker-1-standard', 'cleaner-1-standard', 'decryptor-1-standard']:
            self.launch(product)
        self.post(self.endpoint('loadout'), {'action': 'equip', 'product_id': 'memory-1-standard'}, 400)
        self.post(self.endpoint('applications'), {'action': 'close', 'application': 'decryptor'})
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
        self.assertEqual(len(result['network_directory']), 12)
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

    def test_concurrent_submissions_only_pay_once(self):
        self.slot.active_contract = '0-0'
        self.slot.mission_state = {'recovered': True, 'clean_exit': True}
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
                self.assertEqual(query('SELECT count(*) FROM game_contractidentity'), [(15,)])
                run(restore, '-d', name, '--clean', '--if-exists', '--no-owner', '--no-acl', '--exit-on-error', '--single-transaction', str(root / 'snapshot.dump'))
                build.write_text('build-three')
                run(sys.executable, str(manage), 'prepare_dev', '--preserve')
                run(sys.executable, str(manage), 'prepare_dev')
                self.assertEqual(query('SELECT * FROM lifecycle_probe'), [('backup survives',)])
                self.assertEqual(query('SELECT template_key, code FROM game_contractidentity ORDER BY template_key'), identities)
                self.assertEqual(query('SELECT alias, balance, reputation, active_contract FROM game_saveslot'), [('Archive', 842, 130, '0-1')])
                self.assertEqual(query('SELECT amount, description FROM game_ledgerentry'), [(-90, 'Archive test receipt')])
        finally:
            with psycopg.connect(dbname='postgres', autocommit=True, **params) as maintenance:
                maintenance.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
