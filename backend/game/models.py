from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from .workspace import default_workspace
from .catalog import rank_for, STARTER_EQUIPMENT, STARTER_SOFTWARE, STARTER_ATLAS_NODES


def starter_equipment():
    return dict(STARTER_EQUIPMENT)


def starter_hardware():
    return list(STARTER_EQUIPMENT.values())


def starter_software():
    return list(STARTER_SOFTWARE)


def starter_atlas_nodes():
    return list(STARTER_ATLAS_NODES)


class SaveSlot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()
    alias = models.CharField(max_length=24)
    balance = models.PositiveIntegerField(default=1200)
    reputation = models.PositiveIntegerField(default=0)
    equipment = models.JSONField(default=starter_equipment)
    owned_hardware = models.JSONField(default=starter_hardware)
    installed_software = models.JSONField(default=starter_software)
    running_apps = models.JSONField(default=dict)
    proxy_route = models.JSONField(default=list)
    atlas_nodes = models.JSONField(default=starter_atlas_nodes)
    mission_state = models.JSONField(default=dict)
    contract_cooldowns = models.JSONField(default=dict)
    completed = models.PositiveIntegerField(default=0)
    active_contract = models.CharField(max_length=12, blank=True)
    mission_started = models.DateTimeField(null=True, blank=True)
    mission_log = models.JSONField(default=list)
    backdoors = models.JSONField(default=list)
    ransomware_ops = models.JSONField(default=list)
    remote_host = models.JSONField(default=dict)
    market_unlocked = models.BooleanField(default=False)
    workspace_layout = models.JSONField(default=default_workspace)
    workspace_revision = models.PositiveIntegerField(default=0)
    field_notes = models.TextField(blank=True, default='')
    notes_revision = models.PositiveIntegerField(default=0)
    notes_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'position'], name='unique_user_save_position'), models.CheckConstraint(condition=Q(position__gte=1, position__lte=3), name='three_save_slots')]
        ordering = ['position']
    @property
    def rank(self):
        return rank_for(self.reputation)

class LedgerEntry(models.Model):
    slot = models.ForeignKey(SaveSlot, on_delete=models.CASCADE, related_name='ledger')
    amount = models.IntegerField()
    description = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-id']


class ContractIdentity(models.Model):
    # Template keys remain private so existing saves and cooldowns survive migration.
    template_key = models.CharField(max_length=12, unique=True)
    code = models.PositiveSmallIntegerField(unique=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(code__gte=0, code__lte=255), name='eight_bit_contract_code')]


class DirectoryServer(models.Model):
    key = models.CharField(max_length=40, primary_key=True)
    address = models.CharField(max_length=100, unique=True)
    data = models.JSONField()


class GeneratedMission(models.Model):
    key = models.CharField(max_length=12, primary_key=True)
    data = models.JSONField()


class ServerState(models.Model):
    slot = models.ForeignKey(SaveSlot, on_delete=models.CASCADE, related_name='server_states')
    address = models.CharField(max_length=100)
    descriptor = models.JSONField(default=dict)
    files = models.JSONField(default=list)
    security = models.PositiveSmallIntegerField(default=1)
    port = models.PositiveIntegerField(default=22)
    revision = models.PositiveIntegerField(default=1)
    visits = models.PositiveIntegerField(default=0)
    remote_logs = models.JSONField(default=list)
    observed = models.JSONField(default=dict)
    backdoor_installed = models.BooleanField(default=False)
    maintenance_due = models.DateTimeField(null=True, blank=True)
    last_visit = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['slot', 'address'], name='unique_save_server_state')]
        ordering = ['address']


class ServerEvent(models.Model):
    server = models.ForeignKey(ServerState, on_delete=models.CASCADE, related_name='events')
    kind = models.CharField(max_length=32)
    summary = models.CharField(max_length=300)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-id']
