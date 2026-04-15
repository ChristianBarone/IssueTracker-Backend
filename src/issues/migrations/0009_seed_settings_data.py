from django.db import migrations


def seed_settings(apps, schema_editor):
    Status = apps.get_model('issues', 'Status')
    Priority = apps.get_model('issues', 'Priority')
    IssueType = apps.get_model('issues', 'IssueType')
    Severity = apps.get_model('issues', 'Severity')

    statuses = [
        ('New',            '#3498db', True,  1),
        ('In Progress',    '#e67e22', False, 2),
        ('Ready for test', '#9b59b6', False, 3),
        ('Needs Info',     '#f39c12', False, 4),
        ('Rejected',       '#e74c3c', False, 5),
        ('Postponed',      '#95a5a6', False, 6),
        ('Closed',         '#2ecc71', False, 7),
    ]
    for name, color, is_default, order in statuses:
        Status.objects.create(name=name, color=color, is_default=is_default, order=order)

    priorities = [
        ('Low',    False, 1),
        ('Normal', True,  2),
        ('High',   False, 3),
    ]
    for name, is_default, order in priorities:
        Priority.objects.create(name=name, is_default=is_default, order=order)

    types = [
        ('Bug',         True,  1),
        ('Question',    False, 2),
        ('Enhancement', False, 3),
    ]
    for name, is_default, order in types:
        IssueType.objects.create(name=name, is_default=is_default, order=order)

    severities = [
        ('Wishlist',  False, 1),
        ('Minor',     False, 2),
        ('Normal',    True,  3),
        ('Important', False, 4),
        ('Critical',  False, 5),
    ]
    for name, is_default, order in severities:
        Severity.objects.create(name=name, is_default=is_default, order=order)


def unseed_settings(apps, schema_editor):
    for model_name in ('Status', 'Priority', 'IssueType', 'Severity'):
        apps.get_model('issues', model_name).objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('issues', '0008_settings_models'),
    ]

    operations = [
        migrations.RunPython(seed_settings, reverse_code=unseed_settings),
    ]
