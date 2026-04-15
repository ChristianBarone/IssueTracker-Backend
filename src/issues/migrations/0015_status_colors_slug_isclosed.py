from django.db import migrations
from django.utils.text import slugify


STATUS_DATA = [
    # (name,           color,     is_closed)
    ('New',            '#70728F', False),
    ('In Progress',    '#40A8E4', False),
    ('Ready for test', '#E4CE40', False),
    ('Closed',         '#A8E440', True),
    ('Needs Info',     '#E44057', False),
    ('Rejected',       '#A0A0B0', True),
    ('Postponed',      '#4070E4', False),
]


def update_status_data(apps, schema_editor):
    Status = apps.get_model('issues', 'Status')
    for name, color, is_closed in STATUS_DATA:
        Status.objects.filter(name=name).update(
            color=color,
            is_closed=is_closed,
            slug=slugify(name),
        )
    # Also generate slugs for any statuses not in the list above
    for s in Status.objects.filter(slug=''):
        s.slug = slugify(s.name)
        s.save()


def reverse_status_data(apps, schema_editor):
    Status = apps.get_model('issues', 'Status')
    Status.objects.update(slug='', is_closed=False)


class Migration(migrations.Migration):

    dependencies = [
        ('issues', '0014_status_slug_isclosed'),
    ]

    operations = [
        migrations.RunPython(update_status_data, reverse_code=reverse_status_data),
    ]
