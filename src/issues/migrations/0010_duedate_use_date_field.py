from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('issues', '0009_seed_settings_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='duedate',
            name='days_offset',
        ),
        migrations.AddField(
            model_name='duedate',
            name='date',
            field=models.DateField(default='2026-01-01'),
            preserve_default=False,
        ),
    ]
