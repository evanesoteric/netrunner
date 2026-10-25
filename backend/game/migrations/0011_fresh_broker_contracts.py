from datetime import timedelta
from django.db import migrations, models
from django.utils import timezone
from game.catalog import CONTRACT_BY_ID


def retire_previous_assignments(apps, schema_editor):
    Slot = apps.get_model('game','SaveSlot')
    Mission = apps.get_model('game','GeneratedMission')
    for slot in Slot.objects.using(schema_editor.connection.alias).all().iterator():
        consumed = set(slot.contract_cooldowns)
        if slot.active_contract:
            consumed.add(slot.active_contract)
        pending = []
        for key in consumed:
            job = CONTRACT_BY_ID.get(key)
            if not job:
                row = Mission.objects.using(schema_editor.connection.alias).filter(key=key).first()
                job = row.data if row else None
            if job:
                pending.append(dict(template=job,due_at=slot.contract_cooldowns.get(key) or (timezone.now()+timedelta(minutes=5)).isoformat()))
        slot.broker_consumed = sorted(consumed)
        slot.broker_pending = pending
        slot.save(update_fields=['broker_consumed','broker_pending'])


class Migration(migrations.Migration):
    dependencies = [('game','0010_terminal_applets')]
    operations = [migrations.AlterField(model_name='saveslot',name='active_contract',field=models.CharField(max_length=64,blank=True))] + [migrations.AddField(model_name='saveslot',name=name,field=models.JSONField(default=kind)) for name,kind in [('broker_jobs',dict),('broker_consumed',list),('broker_pending',list),('broker_codes',dict)]] + [migrations.RunPython(retire_previous_assignments,migrations.RunPython.noop)]
