from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('issues', '0012_issue_fk_data'),
    ]

    operations = [
        migrations.RemoveField(model_name='issue', name='status_old'),
        migrations.RemoveField(model_name='issue', name='priority_old'),
        migrations.RemoveField(model_name='issue', name='issue_type_old'),
        migrations.RemoveField(model_name='issue', name='issue_severity_old'),
    ]
