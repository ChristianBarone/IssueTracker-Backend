from issues.helpers import *
from issues.models import *
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404

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
    assignee = get_object_or_404(User, id=assignee_id) if assignee_id else None

    d_line = data['deadline']
    deadline_value = d_line if d_line and d_line.strip() != "" else None

    issue = issue_create_instance(
        subject=subject,
        description=data['description'],
        issue_type=data['issue_type'],
        issue_severity=data['issue_severity'],
        priority=data['priority'],
        status=data['status'] or 'New',
        d_line= deadline_value,
        creator=user,
        assignee=assignee
    )
    if data['attachment']:
        attachment_create_instance(issue.id, user, data['attachment'])

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
    attachments = issue.attachments.all()
    return JsonResponse({
        'id': issue.id,
        'subject': issue.subject,
        'description': issue.description,
        'status': issue.status.name if issue.status else None,
        'priority': issue.priority.name if issue.priority else None,
        'severity': issue.issue_severity.name if issue.issue_severity else None,
        'type': issue.issue_type.name if issue.issue_type else None,
        'creator': issue.creator.username,
        'assignee': issue.assignee.username if issue.assignee else "Unassigned",
        'created_at': issue.created_at.isoformat(),
        'modified_at': issue.modified_at.isoformat(),
        'deadline': issue.deadline.isoformat() if issue.deadline else None,
        'comments': [
            {
                'id': c.id,
                'author': c.author.username,
                'body': c.body,
                'created_at': c.created_at.isoformat()
            } for c in issue.comments.all()
        ],
        'attachments': [
            {
                'id': a.id,
                'name': a.file.name,
                'url': a.file.url
            } for a in attachments
        ],
        'tags': [t.name for t in issue.tags.all()],
        'watchers': [w.username for w in issue.watchers.all()],
        'activities': [
            {
                'user': a.actor.username if a.actor else "System",
                'field': a.field_name,
                'old': a.old_value,
                'new': a.new_value,
                'date': a.created_at.isoformat()
            } for a in issue.activities.all()
        ]
    }, status=200)

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