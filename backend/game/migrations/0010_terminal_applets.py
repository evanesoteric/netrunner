from django.db import migrations, models


def bundle_applets(apps, schema_editor):
    Slot = apps.get_model('game', 'SaveSlot')
    kinds = {'mapper','cracker','decryptor','cleaner','monitor','rootkit','ransomware'}
    for slot in Slot.objects.using(schema_editor.connection.alias).all().iterator():
        preferences = {kind: product for kind, product in slot.running_apps.items() if kind in kinds}
        slot.applet_preferences = preferences
        slot.running_apps = {kind: product for kind, product in slot.running_apps.items() if kind not in kinds and kind not in {'bank','broker','market'}}
        if slot.mission_state.get('password_break'):
            slot.running_apps['terminal'] = 'terminal'
        previous = slot.workspace_layout
        if previous == [dict(id='terminal',product_id='terminal',x=0,y=0,w=6,h=5),dict(id='atlas',product_id='atlas',x=6,y=0,w=6,h=5),dict(id='mapper',product_id='mapper-1-standard',x=0,y=5,w=6,h=5),dict(id='cracker',product_id='cracker-1-standard',x=6,y=5,w=6,h=5)]:
            slot.workspace_layout = [dict(id='terminal',product_id='terminal',x=0,y=0,w=7,h=8),dict(id='atlas',product_id='atlas',x=7,y=0,w=5,h=8)]
        else:
            slot.workspace_layout = [panel for panel in previous if panel['id'] not in kinds and panel['id'] not in {'bank','broker','market'}]
        if previous != slot.workspace_layout:
            slot.workspace_revision += 1
        slot.mission_log = [{**entry, 'app':'terminal'} if entry.get('app') in kinds else entry for entry in slot.mission_log]
        slot.save(update_fields=['applet_preferences','running_apps','workspace_layout','workspace_revision','mission_log'])


class Migration(migrations.Migration):
    dependencies = [('game','0009_saveslot_local_files')]
    operations = [migrations.AddField(model_name='saveslot',name='applet_preferences',field=models.JSONField(default=dict)), migrations.RunPython(bundle_applets,migrations.RunPython.noop)]
