"""Offline world authoring. No API endpoint exposes this command."""
import random
import uuid
from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.db import transaction, connection
from game.filesystem import artifact_path, absolute, build_tree, FilesystemError
from game.deletion import description as deletion_description
from game.services import SERVICES, service_fields
from game.models import DirectoryServer, GeneratedMission, ContractIdentity


class Command(BaseCommand):
    help = 'Generate durable, unique development missions or directory proxy servers offline.'

    def add_arguments(self, parser):
        parser.add_argument('kind', choices=['missions', 'servers'])
        parser.add_argument('--count', type=int, default=1)
        parser.add_argument('--rank', type=int, choices=range(5), default=0)
        parser.add_argument('--placement', choices=['mixed', 'root', 'nested'], default='mixed', help='Mission artifact placement; mixed puts about 30 percent in service folders.')
        parser.add_argument('--artifact-dir', help='Explicit absolute virtual mission directory, e.g. /var/www.')
        parser.add_argument('--filename', help='Mission filename only, e.g. users.db.')
        parser.add_argument('--service', choices=list(SERVICES), help='Choose a service fingerprint family; otherwise vary services randomly.')
        parser.add_argument('--objective', choices=['retrieve', 'delete'], help='Choose a mission objective instead of random selection.')
        parser.add_argument('--delete-copy', action='append', default=[], metavar='/PATH', help='Require deletion of this backup too; repeat for up to four backup files.')
        parser.add_argument('--encrypted', action='store_true', help='Generate encrypted retrieval missions.')
        parser.add_argument('--exploitable', action='store_true', help='Mark generated servers as ransomware targets.')

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Content generation requires DJANGO_DEBUG=1.')
        count, rank = options['count'], options['rank']
        if not 1 <= count <= 100:
            raise CommandError('Choose a count from 1 to 100.')
        if options['exploitable'] and options['kind'] != 'servers':
            raise CommandError('--exploitable applies only to servers.')
        if options['kind'] == 'servers' and (options['objective'] or options['encrypted'] or options['delete_copy']):
            raise CommandError('--objective and --encrypted apply only to missions.')
        if options['kind'] == 'servers' and (options['filename'] or options['artifact_dir'] or options['placement'] != 'mixed'):
            raise CommandError('--filename, --artifact-dir and --placement apply only to missions.')
        if options['filename'] and (len(options['filename']) > 64 or '/' in options['filename'] or chr(92) in options['filename'] or options['filename'] in ('.', '..') or any(ord(char) < 32 for char in options['filename'])):
            raise CommandError('Use a filename of at most 64 characters without directories or control characters.')
        if options['artifact_dir'] and (not options['artifact_dir'].startswith('/') or len(options['artifact_dir']) > 70 or any(ord(char) < 32 for char in options['artifact_dir'])):
            raise CommandError('Use an absolute virtual artifact directory of at most 70 characters.')
        if options['delete_copy'] and (options['objective'] == 'retrieve' or options['encrypted']):
            raise CommandError('--delete-copy requires an unencrypted deletion mission.')
        if len(options['delete_copy']) > 4 or any(not path.startswith('/') or len(path) > 135 or any(ord(char) < 32 for char in path) or absolute(path) == '/' for path in options['delete_copy']):
            raise CommandError('Use up to four absolute backup file paths, each at most 135 characters.')
        if options['objective'] == 'delete' and options['encrypted']:
            raise CommandError('Encrypted missions must use the retrieve objective.')
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(78198421)')
        rng = random.SystemRandom()
        used = set(ContractIdentity.objects.values_list('code', flat=True))
        available = list(set(range(256)) - used)
        if options['kind'] == 'missions' and count > len(available):
            raise CommandError(f'Only {len(available)} of the 256 contract IDs remain available.')
        allocated = rng.sample(available, count) if options['kind'] == 'missions' else []
        created = []
        for index in range(count):
            token = uuid.uuid4().hex
            service = service_fields(options['service'] or rng.choice(list(SERVICES)))
            x, y = rng.randint(110, 900), rng.randint(90, 390)
            name = f'{rng.choice(["Vesper", "Halcyon", "Nimbus", "Aster", "Cobalt"])} {rng.choice(["Archive", "Logistics", "Research", "Systems"])}'
            if options['kind'] == 'servers':
                key, address = 'srv-' + token, 'node-' + token[:16] + '.internal'
                data = dict(id=key, name=f'{name}: {token[:6].upper()}', operator=name, address=address,
                            category='Opportunity' if options['exploitable'] else 'Infrastructure', location='Off-grid',
                            short_name=name.upper(), x=x, y=y, rank=rank, security=rank + 1, **service,
                            fee=rng.randint(3, 12), delay=rng.randint(14, 42), latency=rng.randint(4, 18),
                            exploitable=options['exploitable'], ransom_reward=800 + rank * 200)
                DirectoryServer.objects.create(key=key, address=address, data=data)
                created.append(f'{data["name"]} / {address}')
            else:
                key, address = token[:12], 'mission-' + token[:16] + '.internal'
                objective = options['objective'] or ('delete' if options['delete_copy'] else 'retrieve' if options['encrypted'] else rng.choice(['retrieve', 'delete']))
                encrypted = options['encrypted'] or (options['objective'] is None and objective == 'retrieve' and rng.choice([True, False]))
                filename = options['filename'] or (f'{token[:6]}.enc' if encrypted else 'users.db' if service['service'] == 'wordpress' else f'{token[:6]}.dat')
                description = f'{"Recover" if objective == "retrieve" else "Remove"} {filename} from {address}. Leave no access logs and submit proof through the broker.'
                data = dict(id=key, target=address, title=f'{name} // {token[:6].upper()}', client='Independent broker',
                            rank=rank, security=rank + 1, objective=objective, file=filename, encrypted=encrypted,
                            **service, size=24 + rank * 32, reward=220 + rank * 200 + rng.randrange(0, 100, 10),
                            reputation=35 + rank * 10, description=description, x=x, y=y)
                nested = options['placement'] == 'nested' or (options['placement'] == 'mixed' and rng.random() < .3)
                data['artifact_path'] = (absolute(options['artifact_dir'] + '/' + filename).lstrip('/') if options['artifact_dir'] else artifact_path(data, nested=nested))
                if options['delete_copy']:
                    paths = [data['artifact_path'], *[absolute(path).lstrip('/') for path in options['delete_copy']]]
                    if len(set(paths)) != len(paths):
                        raise CommandError('Each required deletion path must be distinct, including the primary file.')
                    data['delete_paths'] = paths
                    data['title'] += ' // erase all copies'
                    data['description'] = deletion_description(data)
                    data['reward'] += 100 * len(options['delete_copy'])
                try:
                    build_tree(data)
                except FilesystemError as error:
                    raise CommandError(str(error))
                GeneratedMission.objects.create(key=key, data=data)
                ContractIdentity.objects.create(template_key=key, code=allocated[index])
                created.append(f'Contract {allocated[index]} / {data["title"]} / {address} / artifact: /{data["artifact_path"]}')
        for line in created:
            self.stdout.write(line)
        self.stdout.write(self.style.SUCCESS(f'Created {count} {options["kind"]}. Content is stored in PostgreSQL and included in pg_dump.'))
