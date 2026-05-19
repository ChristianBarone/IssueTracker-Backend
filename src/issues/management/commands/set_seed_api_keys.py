from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string

from issues.models import Profile


DEFAULT_USERS = [
    ('Andreu-Caro', 'andreu-caro123'),
    ('Marti-Piris', 'marti-piris123'),
    ('Hala-Alkhatib', 'hala-alkhatib123'),
    ('Aleks-shahverdyan', 'aleks-shahverdyan123'),
    ('Christian-Alejandro-Barone', 'christian-alejandro-barone123'),
]

DEPRECATED_API_KEYS = {
    'a1c3e5f7a1c3e5f7a1c3e5f7a1c3e5f7',
    'b2d4f6a8b2d4f6a8b2d4f6a8b2d4f6a8',
    'c3e5a7c9c3e5a7c9c3e5a7c9c3e5a7c9',
    'd4f6b8d0d4f6b8d0d4f6b8d0d4f6b8d0',
    'e5a7c9e1e5a7c9e1e5a7c9e1e5a7c9e1',
}


class Command(BaseCommand):
    help = 'Set deterministic API keys and passwords for the default users (idempotent)'

    def handle(self, *args, **options):
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
            if not profile.api_key or profile.api_key in DEPRECATED_API_KEYS:
                profile.api_key = get_random_string(32)
                profile.save(update_fields=['api_key'])

        self.stdout.write('Default users seeded/updated with API keys.')
