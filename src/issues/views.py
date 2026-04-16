from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Issue, Comment, Profile, IssueActivity, Attachment, Status, Priority, IssueType, Severity, Tag, DueDate
from .forms import UploadFileForm, ProfileForm, StatusForm, PriorityForm, IssueTypeForm, SeverityForm, TagForm, DueDateForm
from django.contrib.auth.models import User
from django.db.models import Q, Count
import os


def login_page(request):
    if request.user.is_authenticated:
        return redirect('issue_list')

    github_login_url = '/accounts/github/login/?next=/issues/'
    return render(request, 'issues/login.html', {
        'github_login_url': github_login_url,
    })

@login_required(login_url='/')
def issue_list(request):
    # Ordenades de més noves a més velles (Requisit)
    order_param = request.GET.get('order_by', '-created_at')
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
        issues = issues.filter(Q(subject__icontains=search_query) | Q(id__icontains=search_query))

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
    return render(request, 'issues/list.html', context)

@login_required
def issue_create(request):
    if request.method == "POST":
        subject = request.POST.get('subject')
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
        issue = issue_create_instance(subject, description, issue_type, issue_severity, priority, status, deadline_value, creator,
                                      assignee)

        if request.FILES.get('files') is not None:
            attachment_create_instance(issue.id, creator, request.FILES.get('files'))

        return redirect('issue_list')

    return render(request, 'issues/create.html', {
        'statuses': Status.objects.all(),
        'priorities': Priority.objects.all(),
        'issue_types': IssueType.objects.all(),
        'severities': Severity.objects.all(),
        'assignable_users': User.objects.all().order_by('username'),
    })

# sobreescribir metodo save para notificar a watchers cada vez que se guardan cambios
def save(self, *args, **kwargs):
    is_update = self.pk is not None
    super().save(*args, **kwargs)
    if is_update:
        try:
            self.notify_watchers("ha sido actualizado")
        except Exception as e:
            print(f"Error al notificar: {e}")

@login_required
def issue_bulk_create(request):
    # S'ha de canviar en tenir la funcionalitat dels usuaris
    user = request.user

    if request.method == "POST":
        # Valors per defecte en fer bulk add
        subjects = request.POST.get('list').splitlines()
        description = ''
        issue_type = 'Bug'
        issue_severity = 'Normal'
        priority = 'Normal'
        status = 'New'
        d_line = None
        creator = user
        assignee = None

        for subject in subjects:
            issue_create_instance(subject, description, issue_type, issue_severity, priority, status, d_line, creator,
                              assignee)

        return redirect('issue_list')

    return render(request, 'issues/bulk_create.html')

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

def issue_detail(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)

    available_users = User.objects.exclude(id__in=issue.watchers.all())
    assignable_users = User.objects.all().order_by('username')

    edit_comment_id = request.GET.get('edit_comment')
    edit_comment_obj = None
    active_tab = request.GET.get('tab', 'comments')

    if edit_comment_id:
        edit_comment_obj = get_object_or_404(Comment, id=edit_comment_id, issue=issue)

    attachments = issue.attachments.all()

    context = {
        'issue': issue,
        'attachments': attachments,
        'edit_comment_obj': edit_comment_obj,
        'active_tab': active_tab,
        'activities': issue.activities.select_related('actor').all(),
        'available_users': available_users,
        'assignable_users': assignable_users,
    }
    return render(request, 'issues/detail.html', context)

def issue_delete(request, issue_id):
    if request.method == 'POST':
        issue = get_object_or_404(Issue, id=issue_id)
        # Només el creador pot esborrar
        #if issue.creator == request.user:
        issue.delete()
    return redirect('issue_list')


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

    return redirect('issue_detail', issue_id=issue_id)


def _log_watcher_activity(issue, actor, action, watcher_user):
    IssueActivity.objects.create(
        issue=issue,
        actor=actor,
        field_name='watchers',
        old_value='',
        new_value=f"{action} @{watcher_user.username}",
    )

def add_watcher(request, issue_id):
    if request.method == "POST":
        issue = get_object_or_404(Issue, id=issue_id)
        user_id = request.POST.get('user_id')
        if user_id:
            user_to_add = get_object_or_404(User, id=user_id)
            if not issue.watchers.filter(id=user_to_add.id).exists():
                issue.watchers.add(user_to_add)
                _log_watcher_activity(
                    issue,
                    request.user if request.user.is_authenticated else None,
                    'added',
                    user_to_add,
                )
    return redirect('issue_detail', issue_id=issue_id)


def toggle_watcher(request, issue_id):
    if request.method == "POST":
        issue = get_object_or_404(Issue, id=issue_id)
        target_user_id = request.POST.get('user_id')

        if target_user_id:
            user = get_object_or_404(User, id=target_user_id)
        else:
            user = request.user

        if user in issue.watchers.all():
            issue.watchers.remove(user)
            _log_watcher_activity(
                issue,
                request.user if request.user.is_authenticated else None,
                'removed',
                user,
            )
        else:
            issue.watchers.add(user)
            _log_watcher_activity(
                issue,
                request.user if request.user.is_authenticated else None,
                'added',
                user,
            )

    return redirect(request.META.get('HTTP_REFERER', 'issue_list'))

@login_required
def comment_add(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    if request.method == "POST":
        text = request.POST.get('body', '').strip()
        if text:
            # Si el usuario no está logueado, usamos el primero de la base de datos
            if not request.user.is_authenticated:
                return redirect('account_login')  # allauth
            author = request.user
            Comment.objects.create(issue=issue, author=author, body=text)

    # Importante: Usa issue_id=issue_id para coincidir con tu nombre en urls.py
    return redirect('issue_detail', issue_id=issue_id)

@login_required
def comment_edit(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    issue_id = getattr(comment, 'issue_id')

    # Només el creador edita request.user
    if request.method == 'POST' and comment.author == request.user:
        text = request.POST.get('body', '').strip()
        if text:
            comment.body = text
            comment.save()

    return redirect('issue_detail', issue_id=issue_id)

@login_required
def comment_delete(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    issue_id = getattr(comment, 'issue_id')

    # Només el creador esborra request.user
    if comment.author == request.user:
        comment.delete()
    return redirect('issue_detail', issue_id=issue_id)

def user_comments_view(request, username):
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

    return render(request, 'users/profile.html', {
        'profile_user': profile_user,
        'profile_obj': profile_obj,
        'tab': tab,
        'items': items,
        'created_issues': created_issues,
        'open_assigned_issues': open_assigned_issues,
        'comments_count': comments_count,
        'watched_issues': watched_issues,
        'is_owner': is_owner,
    })


@login_required
def edit_profile(request, username):
    profile_user = get_object_or_404(User, username=username)

    if request.user != profile_user:
        return redirect('user_profile', username=username)

    profile_obj, _ = Profile.objects.get_or_create(user=profile_user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile_obj)
        if form.is_valid():
            form.save()
            return redirect('user_profile', username=username)
    else:
        form = ProfileForm(instance=profile_obj)

    return render(request, 'users/edit_profile.html', {
        'profile_user': profile_user,
        'profile_obj': profile_obj,
        'form': form,
    })

def add_attachment(request, issue_id):
    if request.method == 'POST':

        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            if not request.user.is_authenticated:
                return redirect('account_login')  # allauth

            attachment_create_instance(issue_id, request.user, request.FILES['files'])

    return redirect('issue_detail', issue_id=issue_id)

def attachment_create_instance(issue_id, creator, file):
    issue = get_object_or_404(Issue, id=issue_id)

    attachment = Attachment(issue=issue, creator=creator, file=file, name=os.path.basename(file.name))
    attachment.save()

def delete_attachment(request, attachment_id):
    attachment = get_object_or_404(Attachment, id=attachment_id)
    issue_id = getattr(attachment, 'issue_id')

    attachment.delete()

    return redirect('issue_detail', issue_id=issue_id)


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

@login_required
def settings_page(request):
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
    return render(request, 'issues/settings.html', context)


REASSIGNABLE_FIELD = {
    'statuses':   'status',
    'priorities': 'priority',
    'types':      'issue_type',
    'severities': 'issue_severity',
}

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

    return render(request, 'issues/settings_delete_confirm.html', {
        'obj': obj,
        'entity': entity,
        'entity_label': ENTITY_LABELS.get(entity, entity),
        'replacements': replacements,
    })


ORDERABLE_ENTITIES = {'statuses', 'priorities', 'types', 'severities', 'duedates'}

def _do_move(request, entity, pk, direction):
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

    return redirect(f'/settings/?tab={entity}')

@login_required
def settings_toggle_closed(request, pk):
    if request.method == 'POST':
        status = get_object_or_404(Status, pk=pk)
        status.is_closed = not status.is_closed
        status.save(update_fields=['is_closed'])
    return redirect('/settings/?tab=statuses')


@login_required
def settings_move_up(request, entity, pk):
    return _do_move(request, entity, pk, 'up')

@login_required
def settings_move_down(request, entity, pk):
    return _do_move(request, entity, pk, 'down')


@login_required
def settings_save(request, entity, pk=None):
    if entity not in SETTINGS_MODELS:
        return redirect(f'/settings/?tab={entity}')

    model = SETTINGS_MODELS[entity]
    FormClass = SETTINGS_FORMS[entity]
    instance = get_object_or_404(model, pk=pk) if pk else None

    if request.method == 'POST':
        form = FormClass(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            if not instance and entity in ORDERABLE_ENTITIES:
                from django.db.models import Max
                max_order = model.objects.aggregate(m=Max('order'))['m'] or 0
                obj.order = max_order + 1
            obj.save()
            return redirect(f'/settings/?tab={entity}')
    else:
        form = FormClass(instance=instance)

    action = 'Edit' if instance else 'Add'
    return render(request, 'issues/settings_form.html', {
        'form': form,
        'entity': entity,
        'instance': instance,
        'action': action,
        'entity_label': ENTITY_LABELS.get(entity, entity),
    })

