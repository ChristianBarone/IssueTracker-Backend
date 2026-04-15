from django.db import migrations

TYPE_COLORS = {
    'Bug':         '#E44057',
    'Question':    '#4070E4',
    'Enhancement': '#40E4CE',
}

def set_type_colors(apps, schema_editor):
    IssueType = apps.get_model('issues', 'IssueType')
    for name, color in TYPE_COLORS.items():
        IssueType.objects.filter(name=name).update(color=color)

def unset_type_colors(apps, schema_editor):
    apps.get_model('issues', 'IssueType').objects.update(color='')

class Migration(migrations.Migration):
    dependencies = [
        ('issues', '0019_issuetype_add_color'),
    ]
    operations = [
        migrations.RunPython(set_type_colors, reverse_code=unset_type_colors),
    ]
