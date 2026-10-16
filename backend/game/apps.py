from django.apps import AppConfig
from django.db import connections
from django.db.models.signals import post_migrate


def seed_codes(sender, using, **kwargs):
    # Flush can supply an empty historical registry; inspect the actual schema.
    tables = connections[using].introspection.table_names()
    if 'game_contractidentity' in tables:
        from .contracts import ensure_codes
        ensure_codes(using)
    if 'game_directoryserver' in tables:
        from .models import DirectoryServer
        from .world_seed import initial_servers
        for data in initial_servers():
            DirectoryServer.objects.using(using).get_or_create(key=data['id'], defaults={'address': data['address'], 'data': data})


class GameConfig(AppConfig):
    name = 'game'

    def ready(self):
        post_migrate.connect(seed_codes, sender=self, dispatch_uid='game.contract_codes')
