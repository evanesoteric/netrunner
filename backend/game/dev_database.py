"""Development-only PostgreSQL database lifecycle. Never delete cluster files."""
import os
from pathlib import Path
import psycopg
from psycopg import sql
from django.conf import settings
from django.core.management import CommandError, call_command
from django.db import connections


def recreate_database(config):
    name = config['NAME']
    if not settings.DEBUG:
        raise CommandError('Development resets require DJANGO_DEBUG=1.')
    if not name or name in {'postgres', 'template0', 'template1'}:
        raise CommandError('Refusing to recreate a PostgreSQL maintenance database.')
    params = {key: config.get(value) for key, value in {
        'host': 'HOST', 'port': 'PORT', 'user': 'USER', 'password': 'PASSWORD',
    }.items() if config.get(value)}
    with psycopg.connect(dbname='postgres', autocommit=True, **params) as conn:
        # Identifiers must be quoted, never interpolated into SQL text.
        conn.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
        conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))


def revision():
    path = os.environ.get('NETRUNNER_BUILD_ID_FILE', '/app/build-id')
    return Path(path).read_text().strip() if Path(path).exists() else None


def marker():
    return Path(os.environ.get('NETRUNNER_BUILD_STATE', '/state/build-id'))


def remember_build():
    build = revision()
    if build:
        path = marker()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(build + '\n')
        temporary.replace(path)


def reset(stdout):
    connections.close_all()
    recreate_database(settings.DATABASES['default'])
    call_command('migrate', interactive=False, stdout=stdout)
    remember_build()
