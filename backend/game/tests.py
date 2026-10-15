import json
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, Client
from django.utils import timezone
from .models import SaveSlot

class GameTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('runner', password='test-passphrase-long')
        self.client.force_login(self.user)
        self.slot = SaveSlot.objects.create(user=self.user, position=1, alias='ghost')

    def post(self, route, data=None, status=200):
        response = self.client.post(f'/api/{route}/', json.dumps(data or {}), content_type='application/json')
        self.assertEqual(response.status_code, status, response.content)
        return response.json()

    def slot_route(self, suffix):
        return f'slots/{self.slot.id}/{suffix}'

    def test_registration_login_logout_and_password_validation(self):
        self.client.logout()
        self.post('register', {'username': 'new_runner', 'password': 'short'}, 400)
        self.post('register', {'username': 'new_runner', 'password': 'Nebula!72-private-key'}, 201)
        self.assertTrue(get_user_model().objects.get(username='new_runner').check_password('Nebula!72-private-key'))
        self.post('logout')
        self.post('login', {'username': 'new_runner', 'password': 'wrong'}, 401)
        self.post('login', {'username': 'new_runner', 'password': 'Nebula!72-private-key'})
        self.assertEqual(self.client.get('/api/session/').json()['user']['username'], 'new_runner')

    def test_csrf_required_and_session_cookie_initialized(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get('/api/session/')
        self.assertIn('csrftoken', response.cookies)
        self.assertEqual(client.post('/api/login/', '{}', content_type='application/json').status_code, 403)

    def test_exactly_three_slots_and_independent_balances(self):
        self.post('slots', {'position': 2, 'alias': 'echo'}, 201)
        self.post('slots', {'position': 3, 'alias': 'shade'}, 201)
        self.post('slots', {'position': 4, 'alias': 'overflow'}, 400)
        self.post('slots', {'position': 2, 'alias': 'duplicate'}, 400)
        self.post(self.slot_route('upgrade'), {'kind': 'hardware'})
        self.assertEqual(SaveSlot.objects.get(user=self.user, position=2).balance, 1200)
        self.assertEqual(len(self.client.get('/api/slots/').json()['slots']), 3)

    def test_database_rejects_fourth_slot(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SaveSlot.objects.create(user=self.user, position=4, alias='invalid')

    def test_ownership_and_anonymous_access(self):
        other = get_user_model().objects.create_user('other')
        foreign = SaveSlot.objects.create(user=other, position=1, alias='private')
        self.assertEqual(self.client.get(f'/api/slots/{foreign.id}/').status_code, 404)
        self.post(f'slots/{foreign.id}/upgrade', {'kind': 'hardware'}, 404)
        self.post(f'slots/{foreign.id}/accept', {'contract_id': '0-0'}, 404)
        self.post(f'slots/{foreign.id}/command', {'command': 'scan'}, 404)
        self.client.logout()
        self.assertEqual(self.client.get('/api/slots/').status_code, 401)

    def test_rank_filters_and_acceptance_enforced(self):
        for rep, expected in [(0, {0, 1}), (100, {0, 1, 2}), (450, {2, 3, 4}), (700, {3, 4})]:
            self.slot.reputation = rep
            self.slot.save()
            data = self.client.get(f'/api/slots/{self.slot.id}/').json()
            self.assertEqual({c['rank'] for c in data['contracts']}, expected)
        self.post(self.slot_route('accept'), {'contract_id': '0-0'}, 400)
        self.post(self.slot_route('accept'), {'contract_id': '4-0'})
        self.post(self.slot_route('accept'), {'contract_id': '4-1'}, 400)

    def test_success_paid_once_and_rank_rises(self):
        self.slot.reputation = 90
        self.slot.save()
        self.post(self.slot_route('accept'), {'contract_id': '0-0'})
        self.post(self.slot_route('command'), {'command': 'disconnect'})
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.balance, 1200)
        self.assertEqual(self.slot.mission_step, 0)
        for cmd in ['scan', 'breach', 'extract', 'wipe', 'disconnect']:
            result = self.post(self.slot_route('command'), {'command': cmd})
        self.assertEqual(result['balance'], 1420)
        self.assertEqual(result['rank'], 1)
        self.assertEqual(result['completed'], 1)
        self.assertEqual(self.slot.ledger.count(), 1)
        self.post(self.slot_route('command'), {'command': 'disconnect'}, 400)
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.balance, 1420)

    def test_failed_contract_lowers_rank_and_never_pays(self):
        self.slot.reputation = 110
        self.slot.save()
        self.post(self.slot_route('accept'), {'contract_id': '0-0'})
        result = self.post(self.slot_route('command'), {'command': 'abort'})
        self.assertEqual(result['rank'], 0)
        self.assertEqual(result['reputation'], 50)
        self.assertEqual(result['balance'], 1200)
        self.assertIsNone(result['active_contract'])

    def test_expired_contract_fails_on_server(self):
        self.post(self.slot_route('accept'), {'contract_id': '0-0'})
        SaveSlot.objects.filter(pk=self.slot.pk).update(mission_started=timezone.now() - timedelta(seconds=181))
        result = self.post(self.slot_route('command'), {'command': 'scan'})
        self.assertIsNone(result['active_contract'])
        self.assertEqual(result['balance'], 1200)
        self.assertEqual(result['reputation'], 0)

    def test_equipment_requirement_and_upgrade_locks(self):
        self.post(self.slot_route('accept'), {'contract_id': '1-0'})
        self.post(self.slot_route('command'), {'command': 'scan'})
        result = self.post(self.slot_route('command'), {'command': 'breach'})
        self.assertEqual(result['mission_step'], 1)
        self.post(self.slot_route('upgrade'), {'kind': 'software'}, 400)
        self.post(self.slot_route('command'), {'command': 'abort'})
        self.post(self.slot_route('upgrade'), {'kind': 'hardware'})
        result = self.post(self.slot_route('upgrade'), {'kind': 'software'})
        self.assertEqual(result['balance'], 550)
        self.assertEqual(result['software'], 2)
        self.post(self.slot_route('accept'), {'contract_id': '1-0'})
        for cmd in ['scan', 'breach', 'extract', 'wipe', 'disconnect']:
            result = self.post(self.slot_route('command'), {'command': cmd})
        self.assertEqual(result['completed'], 1)

    def test_insufficient_funds_and_max_level(self):
        self.slot.balance = 10
        self.slot.save()
        self.post(self.slot_route('upgrade'), {'kind': 'hardware'}, 400)
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.balance, 10)
        self.assertEqual(self.slot.hardware, 1)
        self.slot.balance = 50000
        self.slot.hardware = 5
        self.slot.save()
        self.post(self.slot_route('upgrade'), {'kind': 'hardware'}, 400)

    def test_malformed_input_has_no_side_effects(self):
        for payload in [[], {'position': True, 'alias': 'bad'}, {'position': 2, 'alias': ['bad']}]:
            self.post('slots', payload, 400)
        self.post(self.slot_route('upgrade'), {'kind': []}, 400)
        self.assertEqual(SaveSlot.objects.filter(user=self.user).count(), 1)

    def test_development_origin_with_valid_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/api/session/')
        response = client.post('/api/login/', json.dumps({'username': 'runner', 'password': 'test-passphrase-long'}), content_type='application/json', HTTP_ORIGIN='http://127.0.0.1:5173', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 200, response.content)

    def test_passphrase_whitespace_is_preserved(self):
        self.user.set_password(' a-special-passphrase-42 ')
        self.user.save()
        self.client.logout()
        self.post('login', {'username': 'runner', 'password': ' a-special-passphrase-42 '})
