from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.models import User
from issues.forms import *
from .models import *
from django.http import JsonResponse

"""""""""""""""""""""""""""""""""
             GLOBALS
"""""""""""""""""""""""""""""""""
GITHUB_LOGIN_URL = '/accounts/github/login/'

SETTINGS_MODELS = {
    'statuses':   Status,
    'priorities': Priority,
    'types':      IssueType,
    'severities': Severity,
    'tags':       Tag,
    'duedates':   DueDate,
}

SETTINGS_FORMS = {
    'statuses':   StatusForm,
    'priorities': PriorityForm,
    'types':      IssueTypeForm,
    'severities': SeverityForm,
    'tags':       TagForm,
    'duedates':   DueDateForm,
}

ENTITY_LABELS = {
    'statuses':   'Status',
    'priorities': 'Priority',
    'types':      'Type',
    'severities': 'Severity',
    'tags':       'Tag',
    'duedates':   'Due Date Status',
}

REASSIGNABLE_FIELD = {
    'statuses':   'status',
    'priorities': 'priority',
    'types':      'issue_type',
    'severities': 'issue_severity',
}

ORDERABLE_ENTITIES = {'statuses', 'priorities', 'types', 'severities', 'duedates'}


def _get_default_or_first(model, name=None):
    if name:
        obj = model.objects.filter(name=name).first()
        if obj:
            return obj
    return model.objects.filter(is_default=True).first() or model.objects.order_by('order', 'name').first()


def issue_create_instance(subject, description, issue_type,
                           issue_severity, priority, status, d_line, creator,
                          assignee):
    issue = Issue.objects.create(
        subject=subject,
        description=description,
        issue_type=_get_default_or_first(IssueType, issue_type),
        issue_severity=_get_default_or_first(Severity, issue_severity),
        priority=_get_default_or_first(Priority, priority),
        status=_get_default_or_first(Status, status),
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

def update_issue_assignee(issue, new_assignee, actor):
    previous_assignee = issue.assignee

    if previous_assignee == new_assignee:
        return False  # no change

    issue.assignee = new_assignee
    issue.save(update_fields=['assignee', 'modified_at'])

    old_value = f"@{previous_assignee.username}" if previous_assignee else 'Unassigned'
    new_value = f"@{new_assignee.username}" if new_assignee else 'Unassigned'

    IssueActivity.objects.create(
        issue=issue,
        actor=actor,
        field_name='assignee',
        old_value=old_value,
        new_value=new_value,
    )

    return True


def attachment_create_instance(issue, creator, file):
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
        return JsonResponse({ 'message': "This action is not allowed." }, status=403)
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
    return user[0].user


def resolve_user_reference(user_reference):
    if user_reference in (None, ''):
        return None

    user = User.objects.filter(id=user_reference).first()
    if user:
        return user

    return User.objects.filter(username=user_reference).first()

def issue_bulk_create(subjects, creator):
    issues = []
    for subject in subjects:
        issues.append(issue_create_instance(subject, '', None, None, None, None, None, creator, None))
    return issues

def apply_issue_queries(request):
    #priority es asc pero -priority es desc
    order_param = request.GET.get('order_by', '-created_at')

    allowed_order_fields = [
        'issue_type', 'issue_severity', 'priority', 'subject',
        'status', 'assignee', 'modified_at', 'deadline', 'created_at'
    ]

    clean_order = order_param.lstrip('-')
    if clean_order not in allowed_order_fields:
        order_param = '-created_at'

    issues = Issue.objects.all().order_by(order_param)

    search_query = request.GET.get('search', '').strip()
    if search_query:
        from .models import Comment

        # 1. Buscamos de forma aislada los IDs de issues que tienen comentarios con esa palabra.
        # Al envolverlo en list(), forzamos a Django a sacar los datos en memoria limpiamente.
        issues_con_comentarios = list(
            Comment.objects.filter(body__icontains=search_query).values_list('issue_id', flat=True)
        )

        # 2. Aplicamos tu filtro original intacto + la lista de IDs de los comentarios
        issues = issues.filter(
            Q(subject__icontains=search_query) |
            Q(id__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(id__in=issues_con_comentarios) # <- El filtro extra para capturar los comentarios
        )

    if request.GET.getlist('issue_type'):
        issues = issues.filter(issue_type__name__in=request.GET.getlist('issue_type'))

    if request.GET.getlist('status'):
        issues = issues.filter(status__name__in=request.GET.getlist('status'))

    if request.GET.getlist('issue_severity'):
        issues = issues.filter(issue_severity__name__in=request.GET.getlist('issue_severity'))

    if request.GET.getlist('priority'):
        issues = issues.filter(priority__name__in=request.GET.getlist('priority'))

    f_assignee = request.GET.get('assigned_to')
    if f_assignee == 'unassigned':
        issues = issues.filter(assignee__isnull=True)
    elif f_assignee:
        issues = issues.filter(assignee_id=f_assignee)

    return issues, order_param

def issue_serializer(issue):
    attachments = issue.attachments.all()

    return {
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
            attachment_serializer(a) for a in attachments
        ],
        'tags': [t.name for t in issue.tags.all()],
        'watchers': [w.username for w in issue.watchers.all()],
        'activities': [
            {
                'id': a.id,
                'user': a.actor.username if a.actor else "System",
                'field': a.field_name,
                'old': a.old_value,
                'new': a.new_value,
                'date': a.created_at.isoformat()
            } for a in issue.activities.all()
        ]
    }

def attachment_serializer(attachment):
    return {
        'id': attachment.id,
        'issue_id': attachment.issue_id,
        'creator_id': attachment.creator_id,
        'url': attachment.file.url,
        'name': attachment.name
    }