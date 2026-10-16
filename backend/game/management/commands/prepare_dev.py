import os
import fcntl
from django.core.management import BaseCommand, call_command
from game.dev_database import revision, marker, remember_build, reset


class Command(BaseCommand):
    help = 'Recreate the local database once per changed image; preserve it on restarts.'

    def add_arguments(self, parser):
        parser.add_argument('--preserve', action='store_true', help='Keep data and acknowledge this build (used after restore).')

    def handle(self, *args, **options):
        path = marker()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.with_suffix('.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            previous = path.read_text().strip() if path.exists() else None
            changed = revision() is not None and previous != revision()
            if changed and not options['preserve'] and os.environ.get('NETRUNNER_RESET_ON_BUILD', '1') == '1':
                self.stdout.write('New development build: dropping and recreating the game database.')
                reset(self.stdout)
            else:
                call_command('migrate', interactive=False, stdout=self.stdout)
                remember_build()
