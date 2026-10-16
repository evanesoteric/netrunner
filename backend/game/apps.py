from django.apps import AppConfig
from django.db.models.signals import post_migrate


def seed_codes(sender, using, **kwargs):
    # Historical app state can omit this table after a deliberate rollback.
    try:
        kwargs['apps'].get_model('game', 'ContractIdentity')
    except LookupError:
        return
    # post_migrate also runs after Django's test database flush.
    from .contracts import ensure_codes
    ensure_codes(using)


class GameConfig(AppConfig):
    name = 'game'

    def ready(self):
        post_migrate.connect(seed_codes, sender=self, dispatch_uid='game.contract_codes')
