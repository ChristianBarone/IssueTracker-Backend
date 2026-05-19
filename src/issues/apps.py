from django.apps import AppConfig


class IssuesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'issues'

    def ready(self):
        """Idempotent seeding of default users and API keys on app startup.

        This runs on every Django process start but will silently skip if the
        database is not yet ready (migrations, missing DB, etc.). It's intended
        to make deployments platform-agnostic by ensuring the five default
        users exist and have generated API keys without requiring an external
        build step.
        """
        try:
            from django.contrib.auth import get_user_model
            from django.contrib.auth.hashers import make_password
            from django.utils.crypto import get_random_string
            from .models import Profile

            DEFAULT_USERS = [
                ('Andreu-Caro', 'andreu-caro123'),
                ('Marti-Piris', 'marti-piris123'),
                ('Hala-Alkhatib', 'hala-alkhatib123'),
                ('Aleks-shahverdyan', 'aleks-shahverdyan123'),
                ('Christian-Alejandro-Barone', 'christian-alejandro-barone123'),
            ]

            User = get_user_model()

            for username, password in DEFAULT_USERS:
                user, _ = User.objects.get_or_create(
                    username=username,
                    defaults={'email': f'{username.lower()}@example.com'},
                )

                if not user.password or user.has_usable_password() is False:
                    user.password = make_password(password)
                    user.save(update_fields=['password'])

                profile, _ = Profile.objects.get_or_create(user=user)
                if not profile.api_key:
                    profile.api_key = get_random_string(32)
                    profile.save(update_fields=['api_key'])

        except Exception:
            # Intentionally swallow exceptions to avoid crashing startup when
            # migrations haven't run yet, or the DB is unreachable.
            return
from django.apps import AppConfig
import importlib


class IssuesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'issues'

    def ready(self):
        importlib.import_module('issues.signals')
