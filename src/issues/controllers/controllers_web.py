from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, HttpResponseNotFound, Http404
from django.db.models import Q, Count

from issues.views import *
from issues.models import *
from issues.helpers import *
from issues.forms import *
from issues.helpers import update_issue_assignee
from issues.helpers import log_watcher_activity
import os
import json

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
def issue_list_web(request):
    issues, order_param = apply_issue_queries(request)
    def toggle_order(field):
        if order_param == field:
            return f"-{field}"
        return field

    context = {
        'issues': issues,
        'users': User.objects.annotate(num_issues=Count('assigned_issues')),
        'show_filters': request.GET.get('show_filters') == '1',

        'all_types': IssueType.objects.annotate(issue_count=Count('issue')).order_by('order'),
        'all_severities': Severity.objects.annotate(issue_count=Count('issue')).order_by('order'),
        'all_statuses': Status.objects.annotate(issue_count=Count('issue')).order_by('order'),

        'search_query': request.GET.get('search', ''),
        'unassigned_issues_count': Issue.objects.filter(assignee__isnull=True).count(),
        'current_order': order_param,
        'f_assignee': request.GET.get('assigned_to'),
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

        'selected_types': request.GET.getlist('issue_type'),
        'selected_statuses': request.GET.getlist('status'),
        'selected_severities': request.GET.getlist('issue_severity'),
        'selected_priorities': request.GET.getlist('priority'),
    }
    return render_issue_list(request, context)

def issue_create_web(request):
    subject = request.POST.get('subject')
    if not subject or subject.strip() == "":
        return redirect('issue_list')

    assignee_id = request.POST.get('assignee_id', '').strip()
    assignee = get_object_or_404(User, id=assignee_id) if assignee_id else None

    d_line = request.POST.get('deadline')
    deadline_value = d_line if d_line and d_line.strip() != "" else None

    issue = issue_create_instance(
        subject=subject,
        description=request.POST.get('description'),
        issue_type=request.POST.get('issue_type'),
        issue_severity=request.POST.get('issue_severity'),
        priority=request.POST.get('priority'),
        status=request.POST.get('status') or 'New',
        d_line=deadline_value,
        creator=request.user,
        assignee=assignee
    )

    if request.FILES.get('files'):
        attachment_create_instance(issue, request.user, request.FILES.get('files'))

    return redirect('issue_list')

def issue_detail_web(request, issue):
    available_users = User.objects.exclude(id__in=issue.watchers.all())
    assignable_users = User.objects.all().order_by('username')

    edit_comment_id = request.GET.get('edit_comment')
    edit_comment_obj = None
    if edit_comment_id:
        edit_comment_obj = get_object_or_404(Comment, id=edit_comment_id, issue=issue)

    issue_tags = issue.tags.all()
    available_tags = Tag.objects.exclude(pk__in=issue_tags.values_list('pk', flat=True)).order_by('name')

    context = {
        'issue': issue,
        'attachments': issue.attachments.all(),
        'edit_comment_obj': edit_comment_obj,
        'active_tab': request.GET.get('tab', 'comments'),
        'activities': issue.activities.select_related('actor').all(),
        'available_users': available_users,
        'assignable_users': assignable_users,
        'editing': request.GET.get('editing', ''),
        'subject_error': request.GET.get('subject_error', ''),
        'is_creator': request.user.is_authenticated and request.user == issue.creator,
        'all_types': IssueType.objects.order_by('order', 'name'),
        'all_severities': Severity.objects.order_by('order', 'name'),
        'all_statuses': Status.objects.order_by('order', 'name'),
        'all_priorities': Priority.objects.order_by('order', 'name'),
        'issue_tags': issue_tags,
        'available_tags': available_tags,
    }
    return render_issue_detail(request, context)

def issue_delete_web(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    if issue.creator == request.user:
        issue.delete()
        return redirect('issue_list')
    else:
        return HttpResponseForbidden()

def issue_bulk_web(request):
    issue_bulk_create(request.POST.get('list').splitlines(), request.user)
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
def issue_update_assignee_web(request, issue):
    assignee_id = request.POST.get('assignee_id', '').strip()

    new_assignee = None
    if assignee_id:
        new_assignee = get_object_or_404(User, id=assignee_id)

    update_issue_assignee(issue, new_assignee, request.user)

    return redirect('issue_detail', issue_id=issue.id)

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
        return JsonResponse({
            'new_deadline': issue.deadline.strftime('%Y-%m-%d') if issue.deadline else None,
        }, status=201)
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
def watcher_add_web(request, issue_id):
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

    return redirect('issue_detail', issue_id=issue_id)

@login_required
def watcher_remove_web(request, issue_id):
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


    return redirect('issue_detail', issue_id=issue_id)

# --- COMMENTS ---
def comment_add_web(request, issue_id):
    text = request.POST.get('body', '').strip()
    if text:
        Comment.objects.create(issue_id=issue_id, author=request.user, body=text)
    return redirect('issue_detail', issue_id=issue_id)

def comment_edit_web(request, comment):
    text = request.POST.get('body', '').strip()
    if text:
        comment.body = text
        comment.save()
    return redirect('issue_detail', issue_id=comment.issue_id)

def comment_delete_web(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    issue_id = comment.issue.id
    comment.delete()
    return redirect('issue_detail', issue_id=issue_id)

# ATTACHMENTS
def attachment_add_web(request, issue):
    form = UploadFileForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({'message': 'Invalid request format'}, status=400)

    attachment_create_instance(issue, request.user, request.FILES['files'])
    return redirect('issue_detail', issue_id=issue.id)

def attachment_delete_web(request, attachment_id):
    attachment = get_object_or_404(Attachment, id=attachment_id)
    issue_id = getattr(attachment, 'issue_id')

    attachment.delete()

    return redirect('issue_detail', issue_id=issue_id)

# PROFILES
def profile_view_web(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile_obj, _ = Profile.objects.get_or_create(user=profile_user)

    tab = request.GET.get('tab', 'assigned')

    created_issues = Issue.objects.filter(
        creator=profile_user
    ).count()

    open_assigned_issues = Issue.objects.filter(
        assignee=profile_user
    ).exclude(status__name='Closed').count()

    comments_count = Comment.objects.filter(
        author=profile_user
    ).count()

    watched_issues = Issue.objects.filter(
        watchers=profile_user
    ).count()

    if tab == 'assigned':
        items = Issue.objects.filter(
            assignee=profile_user
        ).exclude(status__name='Closed').order_by('-modified_at')

    elif tab == 'watched':
        items = Issue.objects.filter(
            watchers=profile_user
        ).order_by('-modified_at')

    else:
        items = Comment.objects.filter(
            author=profile_user
        ).order_by('-created_at')

    is_owner = (
        request.user.is_authenticated
        and request.user == profile_user
    )

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

    return render_profile_view(request, context)

def profile_view_api(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile_obj, _ = Profile.objects.get_or_create(user=profile_user)

    data = {
        'username': profile_user.username,

        'bio': profile_obj.bio,
        'created_issues': Issue.objects.filter(
            creator=profile_user
        ).count(),

        'open_assigned_issues': Issue.objects.filter(
            assignee=profile_user
        ).exclude(status__name='Closed').count(),

        'comments_count': Comment.objects.filter(
            author=profile_user
        ).count(),

        'watched_issues': Issue.objects.filter(
            watchers=profile_user
        ).count(),
    }

    return JsonResponse(data, status=200)

@login_required
def profile_edit_web(request, username):
    profile_user = get_object_or_404(User, username=username)

    if request.user != profile_user:
        return redirect('profile_view', username=username)

    profile_obj, _ = Profile.objects.get_or_create(user=profile_user)

    if request.method == 'POST':
        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=profile_obj
        )

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

    return render_profile_edit(request, context)

def profile_edit_api(request, username, user):
    profile_user = get_object_or_404(User, username=username)

    if user != profile_user:
        return JsonResponse({
            'message': 'Forbidden'
        }, status=403)

    profile_obj, _ = Profile.objects.get_or_create(
        user=profile_user
    )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({
            'message': 'Invalid JSON body'
        }, status=400)

    if 'bio' in data:
        profile_obj.bio = data['bio']

    if 'location' in data:
        profile_obj.location = data['location']

    profile_obj.save()

    return JsonResponse({
        'message': 'Profile updated',
        'bio': profile_obj.bio,
    }, status=200)



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
        if getattr(obj, 'is_default', False):
            next_obj = model.objects.exclude(pk=pk).order_by('order', 'name').first()
            if next_obj:
                next_obj.is_default = True
                next_obj.save(update_fields=['is_default'])
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


# ── SETTINGS API ──────────────────────────────────────────────────────────────

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
    obj = get_object_or_404(model, pk=pk)

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
    obj = get_object_or_404(model, pk=pk)

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
    return JsonResponse({'message': 'Deleted'}, status=200)


def settings_move_api(entity, pk, direction):
    if entity not in ORDERABLE_ENTITIES:
        return JsonResponse({'message': f"Entity '{entity}' is not orderable"}, status=400)

    model = SETTINGS_MODELS[entity]
    serializer = SETTINGS_SERIALIZERS[entity]
    obj = get_object_or_404(model, pk=pk)

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