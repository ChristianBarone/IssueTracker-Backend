import json

from django.contrib.auth.models import User
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404

from issues.helpers import *
from issues.models import *

# ISSUES
def issue_list_api(request):
    issues, order_param = apply_issue_queries(request)

    valid_fields = ['issue_type', 'issue_severity', 'priority', 'subject', 'status', 'assignee', 'modified_at', 'deadline', 'created_at']
    if order_param.lstrip('-') not in valid_fields:
        return JsonResponse({'error': f'Invalid order_by field: {order_param}'}, status=400)

    issues_data = []
    for issue in issues:
        issues_data.append({
            'id': issue.id,
            'subject': issue.subject,
            'description': issue.description,
            'priority': issue.priority.name if issue.priority else None,
            'status': issue.status.name if issue.status else None,
            'issue_type': issue.issue_type.name if issue.issue_type else None,
            'severity': issue.issue_severity.name if issue.issue_severity else None,
            'assignee': issue.assignee.username if issue.assignee else "Unassigned",
            'creator': issue.creator.username,
            'created_at': issue.created_at.isoformat(),
            'modified_at': issue.modified_at.isoformat() if hasattr(issue, 'modified_at') else None,
            'deadline': issue.deadline.isoformat() if issue.deadline else None,
        })

    return JsonResponse({
        'issues': issues_data,
        'current_order': order_param,
        'total_count': issues.count(),
        'unassigned_count': Issue.objects.filter(assignee__isnull=True).count()
    }, status=200)

def issue_create_api(data, user):
    subject = data['subject']
    if not subject or subject.strip() == "":
        return JsonResponse({'error': 'Subject is required'}, status=400)

    assignee_id = data['assignee']
    assignee = resolve_user_reference(assignee_id)
    if assignee_id and not assignee:
        return JsonResponse({'error': 'Invalid assignee'}, status=400)

    d_line = data['deadline']
    deadline_value = d_line if d_line and d_line.strip() != "" else None

    issue = issue_create_instance(
        subject=subject,
        description=data['description'],
        issue_type=data['issue_type'],
        issue_severity=data['issue_severity'],
        priority=data['priority'],
        status=data['status'],
        d_line= deadline_value,
        creator=user,
        assignee=assignee
    )
    if data['attachment']:
        attachment_create_instance(issue, user, data['attachment'])

    return JsonResponse({
        'id': issue.id,
        'subject': issue.subject,
        'description': issue.description,
        'issue_type': issue.issue_type.name if issue.issue_type else None,
        'issue_severity': issue.issue_severity.name if issue.issue_severity else None,
        'priority': issue.priority.name if issue.priority else None,
        'status': issue.status.name if issue.status else None,
        'deadline': issue.deadline if issue.deadline else None,
        'creator': issue.creator.username if issue.creator else None,
        'assignee': issue.assignee.username if issue.assignee else None
    }, status=201)

def issue_detail_api(issue):
    return JsonResponse(issue_serializer(issue), status=200)

def issue_edit_api(data, issue, user):
    update_fields = ['modified_at']

    if 'subject' in data:
        subject = str(data['subject']).strip() if data['subject'] else ''
        if not subject:
            return JsonResponse({'message': 'Subject cannot be empty'}, status=400)
        if subject != issue.subject:
            IssueActivity.objects.create(
                issue=issue, actor=user,
                field_name='subject',
                old_value=issue.subject,
                new_value=subject,
            )
            issue.subject = subject
            update_fields.append('subject')

    if 'description' in data:
        description = data['description'] or ''
        old = issue.description or ''
        if description != old:
            IssueActivity.objects.create(
                issue=issue, actor=user,
                field_name='description',
                old_value=old[:120],
                new_value=description[:120],
            )
            issue.description = description
            update_fields.append('description')

    if 'status' in data:
        status_id = data['status']
        if status_id is None:
            if issue.status is not None:
                IssueActivity.objects.create(
                    issue=issue, actor=user,
                    field_name='status',
                    old_value=issue.status.name,
                    new_value='—',
                )
                issue.status = None
                update_fields.append('status')
        else:
            new_status = Status.objects.filter(pk=status_id).first()
            if not new_status:
                return JsonResponse({'message': f"There is no status with 'id'={status_id}"}, status=400)
            if new_status != issue.status:
                IssueActivity.objects.create(
                    issue=issue, actor=user,
                    field_name='status',
                    old_value=issue.status.name if issue.status else '—',
                    new_value=new_status.name,
                )
                issue.status = new_status
                update_fields.append('status')

    if 'issue_type' in data:
        type_id = data['issue_type']
        if type_id is None:
            if issue.issue_type is not None:
                IssueActivity.objects.create(
                    issue=issue, actor=user,
                    field_name='type',
                    old_value=issue.issue_type.name,
                    new_value='—',
                )
                issue.issue_type = None
                update_fields.append('issue_type')
        else:
            new_type = IssueType.objects.filter(pk=type_id).first()
            if not new_type:
                return JsonResponse({'message': f"There is no type with 'id'={type_id}"}, status=400)
            if new_type != issue.issue_type:
                IssueActivity.objects.create(
                    issue=issue, actor=user,
                    field_name='type',
                    old_value=issue.issue_type.name if issue.issue_type else '—',
                    new_value=new_type.name,
                )
                issue.issue_type = new_type
                update_fields.append('issue_type')

    if 'issue_severity' in data:
        sev_id = data['issue_severity']
        if sev_id is None:
            if issue.issue_severity is not None:
                IssueActivity.objects.create(
                    issue=issue, actor=user,
                    field_name='severity',
                    old_value=issue.issue_severity.name,
                    new_value='—',
                )
                issue.issue_severity = None
                update_fields.append('issue_severity')
        else:
            new_sev = Severity.objects.filter(pk=sev_id).first()
            if not new_sev:
                return JsonResponse({'message': f"There is no severity with 'id'={sev_id}"}, status=400)
            if new_sev != issue.issue_severity:
                IssueActivity.objects.create(
                    issue=issue, actor=user,
                    field_name='severity',
                    old_value=issue.issue_severity.name if issue.issue_severity else '—',
                    new_value=new_sev.name,
                )
                issue.issue_severity = new_sev
                update_fields.append('issue_severity')

    if 'priority' in data:
        prio_id = data['priority']
        if prio_id is None:
            if issue.priority is not None:
                IssueActivity.objects.create(
                    issue=issue, actor=user,
                    field_name='priority',
                    old_value=issue.priority.name,
                    new_value='—',
                )
                issue.priority = None
                update_fields.append('priority')
        else:
            new_prio = Priority.objects.filter(pk=prio_id).first()
            if not new_prio:
                return JsonResponse({'message': f"There is no priority with 'id'={prio_id}"}, status=400)
            if new_prio != issue.priority:
                IssueActivity.objects.create(
                    issue=issue, actor=user,
                    field_name='priority',
                    old_value=issue.priority.name if issue.priority else '—',
                    new_value=new_prio.name,
                )
                issue.priority = new_prio
                update_fields.append('priority')

    if 'deadline' in data:
        deadline_val = data['deadline']
        old_deadline = str(issue.deadline) if issue.deadline else '—'
        new_deadline = deadline_val if deadline_val else None
        if new_deadline != issue.deadline:
            IssueActivity.objects.create(
                issue=issue, actor=user,
                field_name='deadline',
                old_value=old_deadline,
                new_value=str(new_deadline) if new_deadline else '—',
            )
            issue.deadline = new_deadline
            update_fields.append('deadline')

    if 'tags' in data:
        tag_ids = data['tags']
        if not isinstance(tag_ids, list):
            return JsonResponse({'message': "'tags' must be a list of IDs"}, status=400)
        new_tags = []
        for tid in tag_ids:
            tag = Tag.objects.filter(pk=tid).first()
            if not tag:
                return JsonResponse({'message': f"There is no tag with 'id'={tid}"}, status=400)
            new_tags.append(tag)
        old_tag_names = set(issue.tags.values_list('name', flat=True))
        new_tag_names = {t.name for t in new_tags}
        added = new_tag_names - old_tag_names
        removed = old_tag_names - new_tag_names
        if added:
            IssueActivity.objects.create(
                issue=issue, actor=user,
                field_name='tags',
                old_value='',
                new_value=f"added {', '.join(sorted(added))}",
            )
        if removed:
            IssueActivity.objects.create(
                issue=issue, actor=user,
                field_name='tags',
                old_value=f"removed {', '.join(sorted(removed))}",
                new_value='',
            )
        if added or removed:
            issue.tags.set(new_tags)

    issue.save(update_fields=update_fields)
    issue.refresh_from_db()
    return issue_detail_api(issue)

def issue_delete_api(issue_id):
    Issue.objects.filter(id=issue_id).delete()
    return JsonResponse({'message': 'Issue deleted'}, status=204)

def issue_bulk_api(subjects, user):
    issues = issue_bulk_create(subjects, user)

    data = [{
            'id': issue.id,
            'subject': issue.subject,
        } for issue in issues]

    return JsonResponse(data, status=201, safe=False)

def issue_update_assignee_api(data, issue, user):
    assignee_id = data.get('user_id')

    new_assignee = None
    if assignee_id:
        new_assignee = resolve_user_reference(assignee_id)
        if not new_assignee:
            return JsonResponse({'message': 'Invalid user_id'}, status=400)

    if not update_issue_assignee(issue, new_assignee, user):
        return JsonResponse({'message': 'Provided user is already assigned to this issue'}, status=409)

    return issue_detail_api(issue)

# WATCHERS
def watcher_add_api(request_user, issue, data):
    try:
        user_to_add = get_object_or_404(User, id=data['user_id']) if 'user_id' in data else request_user
    except Http404:
        return JsonResponse({'message': f'There is no user with \'id\'={data['user_id']}'}, status=400)

    if issue.watchers.filter(id=user_to_add.id).exists():
        return JsonResponse({'message': f"User {user_to_add} is already watching this issue" }, status=409)

    issue.watchers.add(user_to_add.id)
    log_watcher_activity(
        issue,
        request_user if request_user.is_authenticated else None,
        'added',
        user_to_add,
    )

    return JsonResponse({
        'issue_id': issue.id,
        'current_watchers_count': issue.watchers.count(),
        'watchers_list': [w.username for w in issue.watchers.all()]
    }, status=201)

def watcher_remove_api(request_user, issue, watcher_id):
    try:
        watcher = get_object_or_404(User, id=watcher_id)

    except Http404:
        return JsonResponse({'message': f'There is no user with \'id\'={watcher_id}'}, status=404)

    if not issue.watchers.filter(id=watcher_id).exists():
        return JsonResponse({'message': 'The user you\'re trying to remove is not watching this issue'},
                            status=400)

    issue.watchers.remove(watcher)
    log_watcher_activity(
        issue,
        request_user if request_user.is_authenticated else None,
        'removed',
        watcher,
    )

    return JsonResponse({
        'issue_id': issue.id,
        'current_watchers_count': issue.watchers.count(),
        'watchers_list': [w.username for w in issue.watchers.all()]
    }, status=204)

# ATTACHMENTS
def attachment_list_api(issue_id):
    attachments = Attachment.objects.filter(issue_id=issue_id)
    data = [attachment_serializer(a) for a in attachments]

    return JsonResponse(data, status=200, safe=False)

def attachment_add_api(file, issue, user):
    attachment = attachment_create_instance(issue, user, file)

    return JsonResponse(attachment_serializer(attachment), status=201)

def attachment_get_api(attachment):
    return JsonResponse(attachment_serializer(attachment), status=200)

def attachment_delete_api(attachment):
    attachment.delete()
    return JsonResponse({'message': 'Attachment deleted'}, status=204)

# COMMENTS
def comment_list_api(issue_id):
    comments = Comment.objects.filter(issue_id=issue_id)
    data = []
    for c in comments:
        data.append({
            'id': c.id,
            'body': c.body,
            'author': c.author.username,
            'created_at': c.created_at.isoformat(),
            'issue_id': c.issue_id
        })
    return JsonResponse(data, status=200, safe=False)


def comment_add_api(text, issue_id, user):
    if Comment.objects.filter(issue_id=issue_id, author=user, body=text).exists():
        return JsonResponse({'error': 'Duplicate comment'}, status=409)

    comment = Comment.objects.create(issue_id=issue_id, author=user, body=text)

    return JsonResponse({
        'id': comment.id,
        'body': comment.body,
        'author': comment.author.username,
        'issue_id': issue_id
    }, status=201)

def comment_edit_api(data, comment):
    body = data["body"]
    if Comment.objects.filter(issue=comment.issue, author=comment.author, body=body).exclude(id=comment.id).exists():
        return JsonResponse({'error': 'Duplicate comment'}, status=409)

    comment.body = body
    comment.save()
    return JsonResponse({
        'id': comment.id,
        'body': comment.body,
        'author': comment.author.username,
        'created_at': comment.created_at.isoformat(),
        'issue_id': comment.issue.id
    }, status=200)

def comment_delete_api(comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    comment.delete()
    return JsonResponse({'message': 'Comment deleted'}, status=204)

# SETTINGS
def _serialize_status(o):
    return {'id': o.id, 'name': o.name, 'color': o.color, 'slug': o.slug,
            'is_closed': o.is_closed, 'is_default': o.is_default, 'order': o.order}

def _serialize_priority(o):
    return {'id': o.id, 'name': o.name, 'color': o.color, 'is_default': o.is_default, 'order': o.order}

def _serialize_type(o):
    return {'id': o.id, 'name': o.name, 'color': o.color, 'is_default': o.is_default, 'order': o.order}

def _serialize_severity(o):
    return {'id': o.id, 'name': o.name, 'color': o.color, 'is_default': o.is_default, 'order': o.order}

def _serialize_tag(o):
    return {'id': o.id, 'name': o.name, 'color': o.color}

def _serialize_duedate(o):
    return {'id': o.id, 'name': o.name, 'color': o.color,
            'days_offset': o.days_offset, 'before_or_after': o.before_or_after, 'order': o.order}

SETTINGS_SERIALIZERS = {
    'statuses':   _serialize_status,
    'priorities': _serialize_priority,
    'types':      _serialize_type,
    'severities': _serialize_severity,
    'tags':       _serialize_tag,
    'duedates':   _serialize_duedate,
}

def settings_list_api(entity):
    model = SETTINGS_MODELS[entity]
    serializer = SETTINGS_SERIALIZERS[entity]
    return JsonResponse([serializer(o) for o in model.objects.all()], safe=False, status=200)

def settings_create_api(request, entity):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'message': 'Invalid JSON body'}, status=400)

    name = str(data.get('name', '')).strip()
    if not name:
        return JsonResponse({'message': "'name' is required"}, status=400)

    model = SETTINGS_MODELS[entity]
    serializer = SETTINGS_SERIALIZERS[entity]

    kwargs = {'name': name, 'color': data.get('color', '') or ''}

    if entity in ('statuses', 'priorities', 'types', 'severities'):
        kwargs['is_default'] = bool(data.get('is_default', False))
    if entity == 'statuses':
        kwargs['is_closed'] = bool(data.get('is_closed', False))
        from django.utils.text import slugify
        base_slug = slugify(name)
        slug = base_slug
        if Status.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-new"
        kwargs['slug'] = slug
    if entity == 'duedates':
        kwargs['days_offset'] = data.get('days_offset')
        kwargs['before_or_after'] = data.get('before_or_after')

    if entity in ORDERABLE_ENTITIES:
        from django.db.models import Max
        kwargs['order'] = (model.objects.aggregate(m=Max('order'))['m'] or 0) + 1

    obj = model(**kwargs)
    obj.save()

    if entity == 'statuses':
        obj.refresh_from_db()

    return JsonResponse(serializer(obj), status=201)

def settings_update_api(request, entity, pk):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'message': 'Invalid JSON body'}, status=400)

    model = SETTINGS_MODELS[entity]
    serializer = SETTINGS_SERIALIZERS[entity]
    try:
        obj = get_object_or_404(model, pk=pk)
    except Http404:
        return JsonResponse({'message': f'There is no entity with \'id\'={pk}'}, status=404)

    if 'name' in data:
        name = str(data['name']).strip()
        if not name:
            return JsonResponse({'message': "'name' cannot be empty"}, status=400)
        obj.name = name
        if entity == 'statuses':
            from django.utils.text import slugify
            base_slug = slugify(name)
            slug = base_slug
            if Status.objects.filter(slug=slug).exclude(pk=pk).exists():
                slug = f"{base_slug}-{pk}"
            obj.slug = slug

    if 'color' in data:
        obj.color = data['color'] or ''

    if entity == 'statuses' and 'is_closed' in data:
        obj.is_closed = bool(data['is_closed'])

    if entity in ('statuses', 'priorities', 'types', 'severities') and 'is_default' in data:
        obj.is_default = bool(data['is_default'])

    if entity == 'duedates':
        if 'days_offset' in data:
            obj.days_offset = data['days_offset']
        if 'before_or_after' in data:
            obj.before_or_after = data['before_or_after']

    obj.save()
    obj.refresh_from_db()
    return JsonResponse(serializer(obj), status=200)

def settings_delete_api(request, entity, pk):
    model = SETTINGS_MODELS[entity]

    try:
        obj = get_object_or_404(model, pk=pk)
    except Http404:
        return JsonResponse({'message': f'There is no entity with \'id\'={pk}'}, status=404)

    if entity in REASSIGNABLE_FIELD:
        if model.objects.count() <= 1:
            return JsonResponse({'message': 'Cannot delete the last element'}, status=400)

        replacement_id = request.GET.get('replacement_id')
        if not replacement_id:
            return JsonResponse({'message': "'replacement_id' is required"}, status=400)

        replacement = model.objects.filter(pk=replacement_id).exclude(pk=pk).first()
        if not replacement:
            return JsonResponse({'message': f"There is no {entity.rstrip('s')} with 'id'={replacement_id}"}, status=400)

        field_name = REASSIGNABLE_FIELD[entity]
        Issue.objects.filter(**{field_name: obj}).update(**{field_name: replacement})

    if getattr(obj, 'is_default', False):
        next_obj = model.objects.exclude(pk=pk).order_by('order', 'name').first()
        if next_obj:
            next_obj.is_default = True
            next_obj.save(update_fields=['is_default'])

    obj.delete()
    return JsonResponse({'message': 'Deleted'}, status=204)

def settings_move_api(entity, pk, direction):
    if entity not in ORDERABLE_ENTITIES:
        return JsonResponse({'message': f"Entity '{entity}' is not orderable"}, status=400)

    model = SETTINGS_MODELS[entity]
    serializer = SETTINGS_SERIALIZERS[entity]
    try:
        obj = get_object_or_404(model, pk=pk)
    except Http404:
        return JsonResponse({'message': f'There is no entity with \'id\'={pk}'}, status=404)

    items = list(model.objects.order_by('order', 'name'))
    idx = next((i for i, item in enumerate(items) if item.pk == pk), None)

    if direction == 'up':
        if idx == 0:
            return JsonResponse({'message': 'Already at the top'}, status=400)
        swap_idx = idx - 1
    else:
        if idx == len(items) - 1:
            return JsonResponse({'message': 'Already at the bottom'}, status=400)
        swap_idx = idx + 1

    items[idx], items[swap_idx] = items[swap_idx], items[idx]
    for i, item in enumerate(items):
        item.order = i + 1
        item.save(update_fields=['order'])

    obj.refresh_from_db()
    return JsonResponse(serializer(obj), status=200)

# PROFILE
def profile_view_api(user, same_user):
    profile_obj, _ = Profile.objects.get_or_create(user=user)

    data = {
        'username': user.username,
        'bio': profile_obj.bio,
        'registered': user.date_joined.isoformat(),
        'avatar': profile_obj.avatar.url if profile_obj.avatar else None,
        'open_assigned_issues': [
            issue_serializer(i)
            for i in Issue.objects.all().filter(assignee=user).exclude(status__name='Closed')
        ],
        'comments': [
            {
                'id': c.id,
                'issue_id': c.issue_id,
                'author': c.author.username,
                'body': c.body,
                'created_at': c.created_at.isoformat()
            }
            for c in Comment.objects.all().filter(author=user)
        ],
    }

    if same_user:
        data['watched_issues'] = [
            issue_serializer(i)
            for i in user.watched_issues.all()
        ]
        data['auth_key'] = profile_obj.api_key

    return JsonResponse(data, status=200)

def profile_edit_api(request, user):
    profile_obj, _ = Profile.objects.get_or_create(user=user)
    request.method = 'POST'

    data = request.POST
    files = request.FILES

    if 'bio' in data and data['bio'].strip() != "":
        profile_obj.bio = data['bio']

    if 'avatar' in files:
        profile_obj.avatar = files['avatar']

    profile_obj.save()

    return profile_view_api(user, True)