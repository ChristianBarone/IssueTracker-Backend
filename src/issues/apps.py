from django.apps import AppConfig
import importlib


class IssuesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'issues'

    def ready(self):
        importlib.import_module('issues.signals')