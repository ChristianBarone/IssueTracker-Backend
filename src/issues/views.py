from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Issue, Comment, Profile, IssueActivity, Attachment
from .forms import UploadFileForm, ProfileForm
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
        issues = issues.filter(issue_type__in=selected_types)

    # Filtrado por SEVERITY (Acumulativo)
    if selected_severities:
        issues = issues.filter(issue_severity__in=selected_severities)

    # Filtrado por STATUS (Acumulativo)
    if selected_statuses:
        issues = issues.filter(status__in=selected_statuses)

    if selected_priorities:
        issues = issues.filter(priority__in=selected_priorities)

    # Filtrado por ASIGNADO (Uno solo)
    if f_assignee:
        issues = issues.filter(assignee_id=f_assignee)


    def toggle_order(field):
        if order_param == field:
            return f"-{field}" # Si ya es asc, pasamos a desc
        return field # Si es cualquier otra cosa, ponemos asc

    base_stats = Issue.objects.all()

    users = User.objects.annotate(num_issues=Count('assigned_issues'))

    # Listas para iterar en el HTML
    all_types = ['Bug', 'Question', 'Enhancement']
    all_severities = ['Wishlist', 'Minor', 'Normal', 'Important', 'Critical']
    all_statuses = ['New', 'In Progress', 'Ready for test', 'Needs Info', 'Rejected', 'Postponed', 'Closed']

    counts = {
        # Types
        'bug': base_stats.filter(issue_type='Bug').count(),
        'question': base_stats.filter(issue_type='Question').count(),
        'enhancement': base_stats.filter(issue_type='Enhancement').count(),

        # Severities
        'wishlist': base_stats.filter(issue_severity='Wishlist').count(),
        'minor': base_stats.filter(issue_severity='Minor').count(),
        'normal_sev': base_stats.filter(issue_severity='Normal').count(),
        'important': base_stats.filter(issue_severity='Important').count(),
        'critical': base_stats.filter(issue_severity='Critical').count(),

        # Status
        'new': base_stats.filter(status='New').count(),
        'in_progress': base_stats.filter(status='In Progress').count(),
        'ready_test': base_stats.filter(status='Ready for test').count(),
        'needs_info': base_stats.filter(status='Needs Info').count(),
        'rejected': base_stats.filter(status='Rejected').count(),
        'postponed': base_stats.filter(status='Postponed').count(),
        'closed': base_stats.filter(status='Closed').count(),
    }

    context = {
        'issues': issues,
        'counts': counts,
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
        assignee= request.user
        
        # Creem l'issue i l'assignem a nosaltres mateixos (Requisit)
        issue = issue_create_instance(subject, description, issue_type, issue_severity, priority, status, deadline_value, creator,
                                      assignee)

        if request.FILES.get('files') is not None:
            attachment_create_instance(issue.id, creator, request.FILES.get('files'))

        return redirect('issue_list')

    return render(request, 'issues/create.html')

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
        assignee = user

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
        issue_type=issue_type,
        issue_severity=issue_severity,
        priority=priority,
        status=status,
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

        nuevo_estado = request.POST.get('status')
        status_changed = False
        old_status = ''

        if nuevo_estado and nuevo_estado != issue.status:
            old_status = issue.status
            issue.status = nuevo_estado
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
                old_value=old_status,
                new_value=nuevo_estado,
            )
    return redirect('issue_list')


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
    open_assigned_issues = Issue.objects.filter(assignee=profile_user).exclude(status='Closed').count()
    comments_count = Comment.objects.filter(author=profile_user).count()
    watched_issues = 0

    if tab == 'assigned':
        items = Issue.objects.filter(assignee=profile_user).exclude(status='Closed').order_by('-modified_at')
    elif tab == 'watched':
        items = Issue.objects.none()
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

