from django.db import migrations

DUEDATE_DATA = [
    # (name,       color,     days_offset, before_or_after, order)
    ('Default',  '#A8E440', None,        None,             1),
    ('Due soon', '#E4A840', 14,          'before',         2),
    ('Past due', '#E44057', 0,           'after',          3),
]

def seed(apps, schema_editor):
    DueDate = apps.get_model('issues', 'DueDate')
    for name, color, days_offset, before_or_after, order in DUEDATE_DATA:
        DueDate.objects.get_or_create(
            name=name,
            defaults=dict(color=color, days_offset=days_offset,
                          before_or_after=before_or_after, order=order),
        )

def unseed(apps, schema_editor):
    apps.get_model('issues', 'DueDate').objects.filter(
        name__in=['Default', 'Due soon', 'Past due']
    ).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('issues', '0023_duedate_rework'),
    ]
    operations = [
        migrations.RunPython(seed, reverse_code=unseed),
    ]
