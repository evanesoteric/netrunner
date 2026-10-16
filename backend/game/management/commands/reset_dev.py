from django.conf import settings
from django.core.management import BaseCommand, CommandError
from game.dev_database import reset


class Command(BaseCommand):
    help = 'DROP and recreate the development PostgreSQL database, then migrate an empty schema.'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', help='Must be ERASE-ALL-DATA.')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Development resets require DJANGO_DEBUG=1.')
        if options['confirm'] != 'ERASE-ALL-DATA':
            raise CommandError('This drops ALL accounts and saves. Pass --confirm ERASE-ALL-DATA.')
        reset(self.stdout)
        self.stdout.write(self.style.SUCCESS('Development database dropped, recreated, and migrated.'))
