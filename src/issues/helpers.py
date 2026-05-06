from django.shortcuts import get_object_or_404

from .controllers import *
from django.http import HttpResponse, JsonResponse


def issue_create_instance(subject, description, issue_type, issue_severity, priority, status, d_line, creator,
                          assignee):
    issue = Issue.objects.create(
        subject=subject,
        description=description,
        issue_type=IssueType.objects.filter(name=issue_type).first(),
        issue_severity=Severity.objects.filter(name=issue_severity).first(),
        priority=Priority.objects.filter(name=priority).first(),
        status=Status.objects.filter(name=status).first(),
        deadline=d_line,
        creator=creator,
        assignee=assignee
    )

    IssueActivity.objects.create(
        issue=issue,
        actor=creator,
        field_name='issue',
        old_value='',
        new_value='created'
    )

    return issue


def attachment_create_instance(issue_id, creator, file):
    issue = get_object_or_404(Issue, id=issue_id)

    attachment = Attachment(issue=issue, creator=creator, file=file, name=os.path.basename(file.name))
    attachment.save()

    return attachment

def log_watcher_activity(issue, actor, action, watcher_user):
    IssueActivity.objects.create(
        issue=issue,
        actor=actor,
        field_name='watchers',
        old_value='',
        new_value=f"{action} @{watcher_user.username}",
    )


def do_move(request, entity, pk, direction):
    from .controllers import ORDERABLE_ENTITIES, SETTINGS_MODELS
    if request.method != 'POST' or entity not in ORDERABLE_ENTITIES:
        return redirect(f'/settings/?tab={entity}')

    model = SETTINGS_MODELS[entity]
    obj = get_object_or_404(model, pk=pk)

    items = list(model.objects.order_by('order', 'name'))
    idx = next((i for i, item in enumerate(items) if item.pk == pk), None)
    if idx is None:
        return redirect(f'/settings/?tab={entity}')

    if direction == 'up' and idx > 0:
        swap_idx = idx - 1
    elif direction == 'down' and idx < len(items) - 1:
        swap_idx = idx + 1
    else:
        return redirect(f'/settings/?tab={entity}')

    items[idx], items[swap_idx] = items[swap_idx], items[idx]
    for i, item in enumerate(items):
        item.order = i + 1
        item.save(update_fields=['order'])


def update_fk_field(request, issue_id, field_name, model, activity_label):
    """Generic handler: update one FK field on an issue, log activity, redirect to detail."""
    issue = get_object_or_404(Issue, id=issue_id)
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
    if request.method == 'POST':
        pk = request.POST.get('value_pk')
        if pk:
            new_obj = get_object_or_404(model, pk=pk)
            old_obj = getattr(issue, field_name)
            if new_obj != old_obj:
                old_name = old_obj.name if old_obj else '—'
                setattr(issue, field_name, new_obj)
                issue.save()
                IssueActivity.objects.create(
                    issue=issue, actor=request.user,
                    field_name=activity_label,
                    old_value=old_name,
                    new_value=new_obj.name,
                )

    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return redirect('issue_detail', issue_id=issue_id)

def validate_api_user(api_key, user_id):
    user = Profile.objects.filter(api_key=api_key)

    if user.count() != 1:
        return JsonResponse({'message': "The API key you provided does not belong to any users"}, status=401)

    if user[0].user.id != user_id:
        return JsonResponse({'message': "The provided API key does not authorize this action"}, status= 403)

    return user[0].user

def validate_api_key(api_key):
    user = Profile.objects.filter(api_key=api_key)

    if user.count() != 1:
        return JsonResponse({'message': "The API key you provided does not belong to any users"}, status=401)
    else:
        return user[0].user

def issue_bulk_create(subjects, creator):
    # Valors per defecte en fer bulk add
    description = ''
    issue_type = 'Bug'
    issue_severity = 'Normal'
    priority = 'Normal'
    status = 'New'
    d_line = None
    assignee = None

    issues = []

    for subject in subjects:
        issues.append(issue_create_instance(subject, description, issue_type, issue_severity, priority, status, d_line, creator,
                          assignee))

    return issues