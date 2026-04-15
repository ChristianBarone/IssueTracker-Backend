from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('issues', '0015_status_colors_slug_isclosed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='status',
            name='slug',
            field=models.SlugField(unique=True),
        ),
    ]
