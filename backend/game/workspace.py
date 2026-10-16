"""Workspace preferences never launch tools or grant software ownership."""
from django.core.exceptions import ValidationError
from .catalog import SOFTWARE, BUILTIN_APPS


def default_workspace():
    return [
        dict(id='terminal', product_id='terminal', x=0, y=0, w=6, h=5),
        dict(id='atlas', product_id='atlas', x=6, y=0, w=6, h=5),
        dict(id='mapper', product_id='mapper-1-standard', x=0, y=5, w=6, h=5),
        dict(id='cracker', product_id='cracker-1-standard', x=6, y=5, w=6, h=5),
    ]


def validate_workspace(layout):
    if not isinstance(layout, list) or len(layout) > 16:
        raise ValidationError('A workspace can contain at most 16 panels.')
    services = {'notes', 'history', 'blackmarket', 'backdoors'}
    seen = set()
    for panel in layout:
        if not isinstance(panel, dict) or set(panel) != {'id', 'product_id', 'x', 'y', 'w', 'h'}:
            raise ValidationError('Invalid workspace panel.')
        key, product = panel['id'], panel['product_id']
        if not isinstance(key, str) or not isinstance(product, str) or key in seen:
            raise ValidationError('Workspace panels must have unique application IDs.')
        seen.add(key)
        if key == 'cleaner':
            raise ValidationError('Logcleaner is a terminal extension, not a workspace panel.')
        if key in BUILTIN_APPS or key in services:
            valid = product == key
        else:
            valid = product in SOFTWARE and SOFTWARE[product]['kind'] == key
        if not valid:
            raise ValidationError('Unknown workspace application or software variant.')
        if any(type(panel[field]) is not int for field in ('x', 'y', 'w', 'h')):
            raise ValidationError('Panel coordinates must be whole numbers.')
        if not (3 <= panel['w'] <= 12 and 3 <= panel['h'] <= 18 and panel['x'] >= 0 and panel['y'] >= 0 and panel['x'] + panel['w'] <= 12 and panel['y'] + panel['h'] <= 512):
            raise ValidationError('Panel bounds exceed the workspace grid.')
    for index, panel in enumerate(layout):
        for other in layout[index + 1:]:
            if panel['x'] < other['x'] + other['w'] and other['x'] < panel['x'] + panel['w'] and panel['y'] < other['y'] + other['h'] and other['y'] < panel['y'] + panel['h']:
                raise ValidationError('Workspace panels cannot overlap.')
    return layout
