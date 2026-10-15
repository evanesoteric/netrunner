from django.conf import settings
from django.db import models
from django.db.models import Q
from .catalog import rank_for

class SaveSlot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()
    alias = models.CharField(max_length=24)
    balance = models.PositiveIntegerField(default=1200)
    reputation = models.PositiveIntegerField(default=0)
    hardware = models.PositiveSmallIntegerField(default=1)
    gateway = models.PositiveSmallIntegerField(default=1)
    software = models.PositiveSmallIntegerField(default=1)
    completed = models.PositiveIntegerField(default=0)
    active_contract = models.CharField(max_length=12, blank=True)
    mission_started = models.DateTimeField(null=True, blank=True)
    mission_step = models.PositiveSmallIntegerField(default=0)
    mission_log = models.JSONField(default=list)
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
