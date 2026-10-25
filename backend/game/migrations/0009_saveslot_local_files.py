from uuid import uuid4
from django.db import migrations, models


def recover_current_download(apps, schema_editor):
    from game.catalog import CONTRACT_BY_ID
    Slot = apps.get_model('game', 'SaveSlot')
    Mission = apps.get_model('game', 'GeneratedMission')
    for slot in Slot.objects.using(schema_editor.connection.alias).all().iterator():
        state = slot.mission_state
        if not state.get('recovered') or not state.get('local_size'):
            continue
        target = CONTRACT_BY_ID.get(slot.active_contract) or slot.remote_host
        if not target and slot.active_contract:
            mission = Mission.objects.using(schema_editor.connection.alias).filter(key=slot.active_contract).first()
            target = mission.data if mission else None
        # Old builds discarded completed downloads; only the current known copy is recoverable.
        target = target or dict(target='legacy-download', file='recovered.dat')
        file_id = uuid4().hex
        slot.local_files = [dict(id=file_id, name=target['file'].rsplit('/', 1)[-1], size=state['local_size'], source=target['target'], source_path=target['file'], revision=1, encrypted=False, security=target.get('security', 1), downloaded_at=None)]
        state['local_file_id'] = file_id
        state.pop('local_size', None)
        slot.save(update_fields=['local_files', 'mission_state'])


class Migration(migrations.Migration):
    dependencies = [('game', '0008_integrated_logcleaner')]
    operations = [migrations.AddField(model_name='saveslot', name='local_files', field=models.JSONField(default=list)), migrations.RunPython(recover_current_download, migrations.RunPython.noop)]
