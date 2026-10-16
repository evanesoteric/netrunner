from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command


class Command(BaseCommand):
    help = 'Erase all local development accounts, saves, sessions, and ledger entries; keep the database schema.'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', help='Must be ERASE-ALL-DATA to authorize this development reset.')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Development resets require DJANGO_DEBUG=1.')
        if options['confirm'] != 'ERASE-ALL-DATA':
            raise CommandError('This erases ALL accounts and saves. Pass --confirm ERASE-ALL-DATA to proceed.')
        call_command('migrate', interactive=False, stdout=self.stdout)
        call_command('flush', interactive=False, stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS('Development database cleared. Register a new account to begin.'))
