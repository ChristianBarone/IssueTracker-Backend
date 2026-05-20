"""
WSGI config for issueTracker project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from django.db import connections

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'issueTracker.settings')

try:
    from psycopg_pool import ConnectionPool
    from django.conf import settings

    db_config = settings.DATABASES['default']
    conninfo = f"postgresql://{db_config['USER']}:{db_config['PASSWORD']}@{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}"

    pool = ConnectionPool(conninfo, min_size=10, max_size=20)

    from psycopg import connect

    connections.databases['default']['CONNECTION'] = pool.connection()
except Exception as e:
    print(f"Error configurando pool: {e}")

application = get_wsgi_application()
