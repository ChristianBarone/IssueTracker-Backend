from django.db import migrations

SEVERITY_DATA = [
    # (name,       color,     is_default, order)
    ('Wishlist',  '#70728F', False,      1),
    ('Minor',     '#40A8E4', False,      2),
    ('Normal',    '#40E4A8', True,       3),
    ('Important', '#E4A840', False,      4),
    ('Critical',  '#E44057', False,      5),
]

def apply(apps, schema_editor):
    Severity = apps.get_model('issues', 'Severity')
    for name, color, is_default, order in SEVERITY_DATA:
        # update if exists, create if missing (Wishlist may already exist from seed)
        obj, created = Severity.objects.get_or_create(name=name)
        obj.color      = color
        obj.is_default = is_default
        obj.order      = order
        obj.save()

def revert(apps, schema_editor):
    apps.get_model('issues', 'Severity').objects.update(color='')
    apps.get_model('issues', 'Severity').objects.filter(name='Wishlist').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('issues', '0021_severity_add_color'),
    ]
    operations = [
        migrations.RunPython(apply, reverse_code=revert),
    ]
