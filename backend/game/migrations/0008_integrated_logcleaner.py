from django.db import migrations


def integrate_cleaner(apps, schema_editor):
    Slot = apps.get_model('game', 'SaveSlot')
    for slot in Slot.objects.using(schema_editor.connection.alias).all().iterator():
        fields = []
        if 'cleaner' in slot.running_apps:
            slot.running_apps = {key: value for key, value in slot.running_apps.items() if key != 'cleaner'}
            fields.append('running_apps')
        layout = [panel for panel in slot.workspace_layout if panel.get('id') != 'cleaner']
        if layout != slot.workspace_layout:
            slot.workspace_layout = layout
            slot.workspace_revision += 1
            fields += ['workspace_layout', 'workspace_revision']
        if fields:
            slot.save(update_fields=fields)


class Migration(migrations.Migration):
    dependencies = [('game', '0007_saveslot_workspace_layout_and_more')]
    operations = [migrations.RunPython(integrate_cleaner, migrations.RunPython.noop)]
