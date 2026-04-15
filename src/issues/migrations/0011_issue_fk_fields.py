import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('issues', '0010_duedate_use_date_field'),
    ]

    operations = [
        # Rename old CharField columns so we can reuse the field names for the FKs
        migrations.RenameField(model_name='issue', old_name='status',         new_name='status_old'),
        migrations.RenameField(model_name='issue', old_name='priority',       new_name='priority_old'),
        migrations.RenameField(model_name='issue', old_name='issue_type',     new_name='issue_type_old'),
        migrations.RenameField(model_name='issue', old_name='issue_severity', new_name='issue_severity_old'),

        # Add new FK fields (nullable so the data migration can fill them)
        migrations.AddField(
            model_name='issue',
            name='status',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='issues.status',
            ),
        ),
        migrations.AddField(
            model_name='issue',
            name='priority',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='issues.priority',
            ),
        ),
        migrations.AddField(
            model_name='issue',
            name='issue_type',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='issues.issuetype',
            ),
        ),
        migrations.AddField(
            model_name='issue',
            name='issue_severity',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='issues.severity',
            ),
        ),

        # Add tags M2M
        migrations.AddField(
            model_name='issue',
            name='tags',
            field=models.ManyToManyField(blank=True, to='issues.tag'),
        ),
    ]
