from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, HttpResponseNotFound, Http404
from django.db.models import Q, Count

from .views import *
from .models import *
from .helpers import *
from .forms import *

import os
import json

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

"""""""""""""""""""""""""""""""""
            ENDPOINTS
"""""""""""""""""""""""""""""""""
# LOGIN 
def login_page(request):
    if request.user.is_authenticated:
        return redirect('issue_list')
    
    context = {
        'github_login_url': GITHUB_LOGIN_URL,
    }
    return render_login_page(request, context)

# ISSUES
@login_required(login_url='/')
def issue_list(request):
    # Ordenades de més noves a més velles (Requisit)
    order_param = request.GET.get('order_by', '-created_at')

    #Error 400
    if request.content_type == "application/json":
        valid_fields = ['issue_type', 'issue_severity', 'priority', 'subject', 'status', 'assignee', 'modified_at', 'deadline', 'created_at']
        clean_field = order_param.lstrip('-')
        if clean_field not in valid_fields:
            return JsonResponse({'error': f'Invalid order_by field: {order_param}'}, status=400)

    issues = Issue.objects.all().order_by(order_param)

    #Captura de parámetros
    selected_types = request.GET.getlist('issue_type')
    selected_statuses = request.GET.getlist('filter_status')
    selected_severities = request.GET.getlist('issue_severity')
    selected_priorities = request.GET.getlist('priority')
    f_assignee = request.GET.get('assigned_to')

    search_query = request.GET.get('search', '').strip()

    if search_query:
        # Cerca: Subject i ID (o Description si vols afegir-ho)
        issues = issues.filter(Q(subject__icontains=search_query) | Q(id__icontains=search_query) | Q(description__icontains=search_query))

    # Filtrado por TYPE (Acumulativo)
    if selected_types:
        issues = issues.filter(issue_type__name__in=selected_types)

    # Filtrado por SEVERITY (Acumulativo)
    if selected_severities:
        issues = issues.filter(issue_severity__name__in=selected_severities)

    # Filtrado por STATUS (Acumulativo)
    if selected_statuses:
        issues = issues.filter(status__name__in=selected_statuses)

    if selected_priorities:
        issues = issues.filter(priority__name__in=selected_priorities)

    # Filtrado por ASIGNADO (Uno solo)
    if f_assignee == 'unassigned':
        issues = issues.filter(assignee__isnull=True)
    elif f_assignee:
        issues = issues.filter(assignee_id=f_assignee)


    def toggle_order(field):
        if order_param == field:
            return f"-{field}" # Si ya es asc, pasamos a desc
        return field # Si es cualquier otra cosa, ponemos asc

    users = User.objects.annotate(num_issues=Count('assigned_issues'))
    unassigned_issues_count = Issue.objects.filter(assignee__isnull=True).count()

    # Listas desde BD (dinámicas) — queryset con color e issue_count por anotación
    all_types = IssueType.objects.annotate(issue_count=Count('issue')).order_by('order', 'name')
    all_severities = Severity.objects.annotate(issue_count=Count('issue')).order_by('order', 'name')
    all_statuses = Status.objects.annotate(issue_count=Count('issue')).order_by('order', 'name')

    context = {
        'issues': issues,
        'users': users,
        'show_filters': request.GET.get('show_filters') == '1',
        'all_types': all_types,
        'all_severities': all_severities,
        'all_statuses': all_statuses,
        'selected_types': selected_types,
        'selected_severities': selected_severities,
        'selected_statuses': selected_statuses,
        'search_query': search_query,
        'f_assignee': f_assignee,
        'unassigned_issues_count': unassigned_issues_count,
        'current_order':order_param,
        'order_links': {
            'type': toggle_order('issue_type'),
            'sev': toggle_order('issue_severity'),
            'prio': toggle_order('priority'),
            'subj': toggle_order('subject'),
            'stat': toggle_order('status'),
            'assign': toggle_order('assignee'),
            'mod': toggle_order('modified_at'),
            'deadline': toggle_order('deadline'),
        },
    }

    if request.content_type == "application/json":
        issues_data = []
        for issue in issues:
            issues_data.append({
                'id': issue.id,
                'subject': issue.subject,
                'description': issue.description,
                'priority': issue.priority.name if issue.priority else None,
                'status': issue.status.name if issue.status else None,
                'type': issue.issue_type.name if issue.issue_type else None,
                'assignee': issue.assignee.username if issue.assignee else "Unassigned",
                'created_at': issue.created_at.isoformat(),
            })
        response_data = {
            'issues': issues_data,
            'selectors': {
                'all_types': list(all_types.values('name', 'issue_count')),
                'all_severities': list(all_severities.values('name', 'issue_count')),
                'all_statuses': list(all_statuses.values('name', 'issue_count')),
                'users': list(users.values('id', 'username', 'num_issues')),
            },
            'filters_applied': {
                'selected_types': selected_types,
                'selected_severities': selected_severities,
                'selected_statuses': selected_statuses,
                'search_query': search_query,
                'f_assignee': f_assignee,
            },
            'unassigned_count': unassigned_issues_count,
            'current_order': order_param
        }
        return JsonResponse(response_data, safe=False, status=200)
    else:
        return render_issue_list(request, context)

@login_required
def issue_create(request):
    if request.method == "POST":
        subject = request.POST.get('subject')
        if not subject or subject.strip() == "":
            if request.content_type == "application/json":
                return JsonResponse({'error': 'Subject is required'}, status=400)

        description = request.POST.get('description')
        issue_type = request.POST.get('issue_type')
        issue_severity = request.POST.get('issue_severity')
        priority = request.POST.get('priority')
        status = request.POST.get('status') or 'New'
        d_line = request.POST.get('deadline')
        deadline_value = d_line if d_line and d_line.strip() != "" else None
        creator = request.user
        assignee_id = request.POST.get('assignee_id', '').strip()
        assignee = None

        if assignee_id:
            assignee = get_object_or_404(User, id=assignee_id)

        # Creem l'issue amb assignació per defecte: unassigned
        issue = issue_create_instance(subject, description, issue_type, issue_severity, priority, status,
                                      deadline_value, creator,
                                      assignee)

        if request.FILES.get('files') is not None:
            attachment_create_instance(issue.id, creator, request.FILES.get('files'))

        if request.content_type == "application/json":
            return JsonResponse({
                'id': issue.id,
                'subject': issue.subject,
                'description': issue.description,
                'type': issue.issue_type.name if issue.issue_type else None,
                'severity': issue.issue_severity.name if issue.issue_severity else None,
                'priority': issue.priority.name if issue.priority else None,
                'status': issue.status.name if issue.status else None,
                'deadline': issue.deadline.isoformat() if issue.deadline else None,
                'creator': issue.creator.username,
                'assignee': issue.assignee.username if issue.assignee else "Unassigned",
                'created_at': issue.created_at.isoformat()
            }, status=201)
        else:
            return redirect('issue_list')
    else:
        context = {
            'statuses': Status.objects.all(),
            'priorities': Priority.objects.all(),
            'issue_types': IssueType.objects.all(),
            'severities': Severity.objects.all(),
            'assignable_users': User.objects.all().order_by('username'),
        }
        
        if request.content_type == "application/json":
            return JsonResponse({
                'statuses': list(context['statuses'].values('id', 'name', 'is_closed')),
                'priorities': list(context['priorities'].values('id', 'name')),
                'issue_types': list(context['issue_types'].values('id', 'name')),
                'severities': list(context['severities'].values('id', 'name')),
                'assignable_users': list(context['assignable_users'].values('id', 'username'))
            }, status=200)
        else:
            return render_issue_create(request, context)

@login_required
def issue_bulk_create(request):
    if request.method == "POST":
        # Valors per defecte en fer bulk add
        subjects = request.POST.get('list').splitlines()
        description = ''
        issue_type = 'Bug'
        issue_severity = 'Normal'
        priority = 'Normal'
        status = 'New'
        d_line = None
        creator = request.user
        assignee = None

        for subject in subjects:
            issue_create_instance(subject, description, issue_type, issue_severity, priority, status, d_line, creator,
                              assignee)

        return redirect('issue_list')
    else:
        if request.content_type == "application/json":
            # implementar
            return None
        else:
            return render_issue_bulk_create(request)


@login_required
def issue_detail(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)

    available_users = User.objects.exclude(id__in=issue.watchers.all())
    assignable_users = User.objects.all().order_by('username')

    edit_comment_id = request.GET.get('edit_comment')
    edit_comment_obj = None
    active_tab = request.GET.get('tab', 'comments')
    editing = request.GET.get('editing', '')
    subject_error = request.GET.get('subject_error', '')
    is_creator = request.user.is_authenticated and request.user == issue.creator

    if edit_comment_id:
        edit_comment_obj = get_object_or_404(Comment, id=edit_comment_id, issue=issue)

    attachments = issue.attachments.all()
    issue_tags = issue.tags.all()
    available_tags = Tag.objects.exclude(pk__in=issue_tags.values_list('pk', flat=True)).order_by('name')

    context = {
        'issue': issue,
        'attachments': attachments,
        'edit_comment_obj': edit_comment_obj,
        'active_tab': active_tab,
        'activities': issue.activities.select_related('actor').all(),
        'available_users': available_users,
        'assignable_users': assignable_users,
        'editing': editing,
        'subject_error': subject_error,
        'is_creator': is_creator,
        'all_types': IssueType.objects.order_by('order', 'name'),
        'all_severities': Severity.objects.order_by('order', 'name'),
        'all_statuses': Status.objects.order_by('order', 'name'),
        'all_priorities': Priority.objects.order_by('order', 'name'),
        'issue_tags': issue_tags,
        'available_tags': available_tags,
    }

    if request.content_type == "application/json":
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
            'comments': [
                {
                    'id': c.id,
                    'author': c.author.username,
                    'body': c.body,
                    'created_at': c.created_at.isoformat()
                } for c in comments
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
    else:
        return render_issue_detail(request, context)

@login_required
def issue_delete(request, issue_id):
    #Error 404: Automatico
    issue = get_object_or_404(Issue, id=issue_id)
    #Logica profile 401

    succes = False
    if request.method == 'POST':
        if issue.creator == request.user:
            issue.delete()
            succes = True
        else:
            #Error 403: No es creador
            if request.content_type == "application/json":
                return JsonResponse({'message': 'Forbidden: Only creator can delete'}, status=403)
            else:
                return HttpResponseForbidden()

    if request.content_type == "application/json":
        if success:
            return JsonResponse({'id': issue_id, 'message': 'Deleted'}, status=200)
        else:
            return JsonResponse({'message': 'Bad Request'}, status=405) # 405 Bad request
    else:
        return redirect('issue_list')

@login_required
def issue_update_status(request, issue_id):
    if request.method == 'POST':
        issue = get_object_or_404(Issue, id=issue_id)

        nuevo_estado_str = request.POST.get('status')
        status_changed = False
        old_status_name = ''

        if nuevo_estado_str:
            new_status = Status.objects.filter(name=nuevo_estado_str).first()
            if new_status and new_status != issue.status:
                old_status_name = issue.status.name if issue.status else ''
                issue.status = new_status
                status_changed = True

        nueva_deadline = request.POST.get('deadline')
        if nueva_deadline == "":
            issue.deadline = None
        elif nueva_deadline:
            issue.deadline = nueva_deadline

        issue.save()

        if status_changed:
            IssueActivity.objects.create(
                issue=issue,
                actor=request.user if request.user.is_authenticated else None,
                field_name='status',
                old_value=old_status_name,
                new_value=nuevo_estado_str,
            )

    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return redirect('issue_list')

@login_required
def issue_update_assignee(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)

    if request.method == 'POST':
        assignee_id = request.POST.get('assignee_id', '').strip()
        previous_assignee = issue.assignee
        new_assignee = None

        if assignee_id:
            new_assignee = get_object_or_404(User, id=assignee_id)

        if previous_assignee != new_assignee:
            issue.assignee = new_assignee
            issue.save(update_fields=['assignee', 'modified_at'])

            old_value = f"@{previous_assignee.username}" if previous_assignee else 'Unassigned'
            new_value = f"@{new_assignee.username}" if new_assignee else 'Unassigned'

            IssueActivity.objects.create(
                issue=issue,
                actor=request.user if request.user.is_authenticated else None,
                field_name='assignee',
                old_value=old_value,
                new_value=new_value,
            )

    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return redirect('issue_detail', issue_id=issue_id)

@login_required
def issue_update_type(request, issue_id):
    return update_fk_field(request, issue_id, 'issue_type', IssueType, 'type')

@login_required
def issue_update_severity(request, issue_id):
    return update_fk_field(request, issue_id, 'issue_severity', Severity, 'severity')

@login_required
def issue_update_priority(request, issue_id):
    return update_fk_field(request, issue_id, 'priority', Priority, 'priority')

@login_required
def issue_update_status_detail(request, issue_id):
    return update_fk_field(request, issue_id, 'status', Status, 'status')

@login_required
def issue_update_subject(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    if issue.creator != request.user:
        return HttpResponseForbidden()
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        if not subject:
            if request.content_type == "application/json":
                # implementar
                return None
            else:
                return redirect(f'/issue/{issue_id}/?editing=subject&subject_error=1')
        old = issue.subject
        issue.subject = subject
        issue.save()
        IssueActivity.objects.create(
            issue=issue, actor=request.user,
            field_name='subject', old_value=old, new_value=subject,
        )

    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return redirect('issue_detail', issue_id=issue_id)

@login_required
def issue_update_description(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    if issue.creator != request.user:
        return HttpResponseForbidden()
    if request.method == 'POST':
        description = request.POST.get('description', '').strip()
        old = issue.description or ''
        issue.description = description
        issue.save()
        IssueActivity.objects.create(
            issue=issue, actor=request.user,
            field_name='description',
            old_value=old[:120],
            new_value=description[:120],
        )
    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return redirect('issue_detail', issue_id=issue_id)

@login_required
def issue_update_deadline_detail(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    if issue.creator != request.user:
        return HttpResponseForbidden()
    if request.method == 'POST':
        deadline_str = request.POST.get('deadline', '').strip()
        old = str(issue.deadline) if issue.deadline else '—'
        issue.deadline = deadline_str if deadline_str else None
        issue.save()
        IssueActivity.objects.create(
            issue=issue, actor=request.user,
            field_name='deadline',
            old_value=old,
            new_value=deadline_str or '—',
        )
    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return redirect('issue_detail', issue_id=issue_id)

@login_required
def issue_add_tag(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    if issue.creator != request.user:
        return HttpResponseForbidden()
    if request.method == 'POST':
        tag_pk = request.POST.get('tag_pk')
        if tag_pk:
            tag = get_object_or_404(Tag, pk=tag_pk)
            if not issue.tags.filter(pk=tag.pk).exists():
                issue.tags.add(tag)
                IssueActivity.objects.create(
                    issue=issue, actor=request.user,
                    field_name='tags', old_value='', new_value=f'added {tag.name}',
                )
    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return redirect('issue_detail', issue_id=issue_id)

@login_required
def issue_remove_tag(request, issue_id, tag_id):
    issue = get_object_or_404(Issue, id=issue_id)
    if issue.creator != request.user:
        return HttpResponseForbidden()
    if request.method == 'POST':
        tag = get_object_or_404(Tag, pk=tag_id)
        if issue.tags.filter(pk=tag.pk).exists():
            issue.tags.remove(tag)
            IssueActivity.objects.create(
                issue=issue, actor=request.user,
                field_name='tags', old_value=f'removed {tag.name}', new_value='',
            )
    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return redirect('issue_detail', issue_id=issue_id)

# WATCHERS
@login_required
def watcher_add(request, issue_id):
    if request.method == "POST":
        issue = get_object_or_404(Issue, id=issue_id)
        user_id = request.POST.get('user_id')

        if user_id:
            user_to_add = get_object_or_404(User, id=user_id)

            if not issue.watchers.filter(id=user_to_add.id).exists():
                issue.watchers.add(user_to_add)
                log_watcher_activity(
                    issue,
                    request.user if request.user.is_authenticated else None,
                    'added',
                    user_to_add,
                )

    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return redirect('issue_detail', issue_id=issue_id)

@login_required
def remove_watcher(request, issue_id):
    if request.method == "POST":
        issue = get_object_or_404(Issue, id=issue_id)
        target_user_id = request.POST.get('user_id')

        if target_user_id:
            user = get_object_or_404(User, id=target_user_id)
        else:
            user = request.user

        issue.watchers.remove(user)
        log_watcher_activity(
            issue,
            request.user if request.user.is_authenticated else None,
            'removed',
            user,
        )

    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return redirect('issue_detail', issue_id=issue_id)

# --- COMMENTS ---
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

def comment_add_api(request, issue_id, user):
    text = request.POST.get('body', '').strip()
    if not text:
        return JsonResponse({'message': 'Body is required'}, status=400)

    if Comment.objects.filter(issue_id=issue_id, author=user, body=text).exists():
        return JsonResponse({'error': 'Duplicate comment'}, status=409)

    comment = Comment.objects.create(issue_id=issue_id, author=user, body=text)
    return JsonResponse({
        'id': comment.id,
        'body': comment.body,
        'author': comment.author.username,
        'issue_id': issue_id
    }, status=201)

def comment_add_web(request, issue_id):
    text = request.POST.get('body', '').strip()
    if text:
        Comment.objects.create(issue_id=issue_id, author=request.user, body=text)
    return redirect('issue_detail', issue_id=issue_id)

def comment_edit_api(request, comment):
    text = request.POST.get('body', '').strip()
    if not text:
        return JsonResponse({'message': 'Body is required'}, status=400)

    if Comment.objects.filter(issue_id=issue_id, author=user, body=text).exists():
        return JsonResponse({'error': 'Duplicate comment'}, status=409)

    comment.body = text
    comment.save()
    return JsonResponse({'id': comment.id, 'body': comment.body, 'message': 'Comment updated'}, status=200)

def comment_edit_web(request, comment):
    text = request.POST.get('body', '').strip()
    if text:
        comment.body = text
        comment.save()
    return redirect('issue_detail', issue_id=comment.issue_id)

def comment_delete_api(comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    comment.delete()
    return JsonResponse({'id': comment_id, 'message': 'Comment deleted successfully'}, status=200)

def comment_delete_web(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    issue_id = comment.issue.id
    comment.delete()
    return redirect('issue_detail', issue_id=issue_id)

# ATTACHMENTS
def attachment_get_api(attachment_id):
    attachment = get_object_or_404(Attachment, id=attachment_id)
    data = {
        'attachment_id': attachment.id,
        'issue_id': attachment.issue_id,
        'creator_id': attachment.creator_id,
        'url': attachment.file.url,
        'name': attachment.name
    }

    return JsonResponse(data, status=200)

def attachment_list_api(issue_id):
    attachments = Attachment.objects.filter(issue_id=issue_id)
    data = []
    for attachment in attachments:
        data.append({
            'attachment_id': attachment.id,
            'issue_id': attachment.issue_id,
            'creator_id': attachment.creator_id,
            'url': attachment.file.url,
            'name': attachment.name
        })

    return JsonResponse(data, status=200, safe=False)

def attachment_add_api(request, issue_id, user):
    form = UploadFileForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({'message': 'Invalid request format'}, status=400)

    attachment = attachment_create_instance(issue_id, user, request.FILES['files'])

    data = {
        'attachment_id': attachment.id,
        'issue_id': attachment.issue_id,
        'creator_id': attachment.creator_id,
        'url': attachment.file.url,
        'name': attachment.name
    }

    return JsonResponse(data, status=201)

def attachment_add_web(request, issue_id):
    form = UploadFileForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({'message': 'Invalid request format'}, status=400)

    attachment_create_instance(issue_id, request.user, request.FILES['files'])
    return redirect('issue_detail', issue_id=issue_id)

def attachment_delete_api(attachment_id):
    attachment = get_object_or_404(Attachment, id=attachment_id)
    attachment.delete()

    return JsonResponse({'message': 'Attachment deleted'}, status=204)

def attachment_delete_web(request, attachment_id):
    attachment = get_object_or_404(Attachment, id=attachment_id)
    issue_id = getattr(attachment, 'issue_id')

    attachment.delete()

    return redirect('issue_detail', issue_id=issue_id)

# PROFILES
def profile_view(request, username):
    # Obtenemos al usuario del perfil que estamos visitando
    profile_user = get_object_or_404(User, username=username)
    profile_obj, _ = Profile.objects.get_or_create(user=profile_user)

    tab = request.GET.get('tab', 'assigned')

    created_issues = Issue.objects.filter(creator=profile_user).count()
    open_assigned_issues = Issue.objects.filter(assignee=profile_user).exclude(status__name='Closed').count()
    comments_count = Comment.objects.filter(author=profile_user).count()
    watched_issues = Issue.objects.filter(watchers=profile_user).count()

    if tab == 'assigned':
        items = Issue.objects.filter(assignee=profile_user).exclude(status__name='Closed').order_by('-modified_at')
    elif tab == 'watched':
        items = Issue.objects.filter(watchers=profile_user).order_by('-modified_at')
    else:
        items = Comment.objects.filter(author=profile_user).order_by('-created_at')

    is_owner = request.user.is_authenticated and request.user == profile_user

    context = {
        'profile_user': profile_user,
        'profile_obj': profile_obj,
        'tab': tab,
        'items': items,
        'created_issues': created_issues,
        'open_assigned_issues': open_assigned_issues,
        'comments_count': comments_count,
        'watched_issues': watched_issues,
        'is_owner': is_owner,
    }

    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return render_profile_view(request, context)

@login_required
def profile_edit(request, username):
    profile_user = get_object_or_404(User, username=username)

    if request.user != profile_user:
        return redirect('profile_view', username=username)

    profile_obj, _ = Profile.objects.get_or_create(user=profile_user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile_obj)
        if form.is_valid():
            form.save()
            return redirect('profile_view', username=username)
    else:
        form = ProfileForm(instance=profile_obj)


    context = {
        'profile_user': profile_user,
        'profile_obj': profile_obj,
        'form': form,
    }
    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return render_profile_edit(request, context)

# SETTINGS
@login_required
def settings_view(request):
    active_tab = request.GET.get('tab', 'statuses')
    context = {
        'statuses':   Status.objects.all(),
        'priorities': Priority.objects.all(),
        'types':      IssueType.objects.all(),
        'severities': Severity.objects.all(),
        'tags':       Tag.objects.all(),
        'duedates':   DueDate.objects.all(),
        'active_tab': active_tab,
    }

    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return render_settings_view(request, context)

@login_required
def settings_delete(request, entity, pk):
    if entity not in SETTINGS_MODELS:
        return redirect(f'/settings/?tab={entity}')

    model = SETTINGS_MODELS[entity]
    obj = get_object_or_404(model, pk=pk)

    if request.method == 'POST':
        if entity in REASSIGNABLE_FIELD:
            if model.objects.count() <= 1:
                return redirect(f'/settings/?tab={entity}')
            replacement_pk = request.POST.get('replacement_pk')
            if replacement_pk:
                replacement = get_object_or_404(model, pk=replacement_pk)
                field_name = REASSIGNABLE_FIELD[entity]
                Issue.objects.filter(**{field_name: obj}).update(**{field_name: replacement})
        obj.delete()
        return redirect(f'/settings/?tab={entity}')

    # GET — show confirmation page
    replacements = None
    if entity in REASSIGNABLE_FIELD:
        if model.objects.count() <= 1:
            return redirect(f'/settings/?tab={entity}')   # can't delete last
        replacements = model.objects.exclude(pk=pk).order_by('order', 'name')

    context = {
        'obj': obj,
        'entity': entity,
        'entity_label': ENTITY_LABELS.get(entity, entity),
        'replacements': replacements,
    }

    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return render_settings_delete(request, context)

@login_required
def settings_move_up(request, entity, pk):
    do_move(request, entity, pk, 'up')
    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return redirect(f'/settings/?tab={entity}')

@login_required
def settings_move_down(request, entity, pk):
    do_move(request, entity, pk, 'down')
    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return redirect(f'/settings/?tab={entity}')

@login_required
def settings_toggle_closed(request, pk):
    if request.method == 'POST':
        status = get_object_or_404(Status, pk=pk)
        status.is_closed = not status.is_closed
        status.save(update_fields=['is_closed'])
        
    if request.content_type == "application/json":
        # implementar
        return None
    else:
        return redirect(f'/settings/?tab=statuses')
    
@login_required
def settings_save(request, entity, pk=None):
    if entity not in SETTINGS_MODELS:
        return redirect(f'/settings/?tab={entity}')

    model = SETTINGS_MODELS[entity]
    form_class = SETTINGS_FORMS[entity]
    instance = get_object_or_404(model, pk=pk) if pk else None

    if request.method == 'POST':
        form = form_class(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            if not instance and entity in ORDERABLE_ENTITIES:
                from django.db.models import Max
                max_order = model.objects.aggregate(m=Max('order'))['m'] or 0
                obj.order = max_order + 1
            obj.save()

            if request.content_type == "application/json":
                # implementar
                return None
            else:
                return redirect(f'/settings/?tab={entity}')
    else:
        form = form_class(instance=instance)

    action = 'Edit' if instance else 'Add'

    context = {
        'form': form,
        'entity': entity,
        'instance': instance,
        'action': action,
        'entity_label': ENTITY_LABELS.get(entity, entity),
    }

    return render_settings_form(request, context)