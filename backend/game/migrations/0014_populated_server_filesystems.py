from django.db import migrations


def populate(apps, schema_editor):
    from game.filesystem import build_tree, LAYOUT_VERSION
    ServerState = apps.get_model('game', 'ServerState')
    for server in ServerState.objects.using(schema_editor.connection.alias).iterator(chunk_size=100):
        if server.descriptor.get('filesystem_layout') == LAYOUT_VERSION:
            continue
        server.files = build_tree(server.descriptor, existing=server.files)
        server.descriptor = {**server.descriptor, 'filesystem_layout': LAYOUT_VERSION}
        server.save(using=schema_editor.connection.alias, update_fields=['files', 'descriptor'])


class Migration(migrations.Migration):
    dependencies = [('game', '0013_saveslot_irc_state')]
    operations = [migrations.RunPython(populate, migrations.RunPython.noop)]
