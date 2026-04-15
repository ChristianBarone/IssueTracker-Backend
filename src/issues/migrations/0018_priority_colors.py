from django.db import migrations

PRIORITY_COLORS = {
    'Low':    '#A8E440',
    'Normal': '#E4CE40',
    'High':   '#E47340',
}

def set_priority_colors(apps, schema_editor):
    Priority = apps.get_model('issues', 'Priority')
    for name, color in PRIORITY_COLORS.items():
        Priority.objects.filter(name=name).update(color=color)

def unset_priority_colors(apps, schema_editor):
    apps.get_model('issues', 'Priority').objects.update(color='')

class Migration(migrations.Migration):
    dependencies = [
        ('issues', '0017_priority_add_color'),
    ]
    operations = [
        migrations.RunPython(set_priority_colors, reverse_code=unset_priority_colors),
    ]
