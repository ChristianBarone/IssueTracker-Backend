from django.db import migrations


def fill_fk_fields(apps, schema_editor):
    Issue = apps.get_model('issues', 'Issue')
    Status = apps.get_model('issues', 'Status')
    Priority = apps.get_model('issues', 'Priority')
    IssueType = apps.get_model('issues', 'IssueType')
    Severity = apps.get_model('issues', 'Severity')

    status_map   = {s.name: s for s in Status.objects.all()}
    priority_map = {p.name: p for p in Priority.objects.all()}
    type_map     = {t.name: t for t in IssueType.objects.all()}
    severity_map = {s.name: s for s in Severity.objects.all()}

    for issue in Issue.objects.all():
        issue.status        = status_map.get(issue.status_old)
        issue.priority      = priority_map.get(issue.priority_old)
        issue.issue_type    = type_map.get(issue.issue_type_old)
        issue.issue_severity = severity_map.get(issue.issue_severity_old)
        issue.save()


def unfill_fk_fields(apps, schema_editor):
    Issue = apps.get_model('issues', 'Issue')
    for issue in Issue.objects.all():
        issue.status_old        = issue.status.name        if issue.status        else ''
        issue.priority_old      = issue.priority.name      if issue.priority      else ''
        issue.issue_type_old    = issue.issue_type.name    if issue.issue_type    else ''
        issue.issue_severity_old = issue.issue_severity.name if issue.issue_severity else ''
        issue.save()


class Migration(migrations.Migration):

    dependencies = [
        ('issues', '0011_issue_fk_fields'),
    ]

    operations = [
        migrations.RunPython(fill_fk_fields, reverse_code=unfill_fk_fields),
    ]
