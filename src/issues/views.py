from django.shortcuts import render, redirect, get_object_or_404
from .models import Issue, Comment
from django.contrib.auth.models import User
from django.db.models import Q, Count

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
        },
    }
    return render(request, 'issues/list.html', context)

def issue_create(request):
    # Simulem usuari loguejat (Hardcoded per a Sessió 2)
    default_user = User.objects.first() 

    if request.method == "POST":
        subject = request.POST.get('subject')
        description = request.POST.get('description')
        d_line = request.POST.get('deadline')
        issue_type=request.POST.get('issue_type')
        issue_severity=request.POST.get('issue_severity')
        priority=request.POST.get('priority')
        status = request.POST.get('status') or 'New'
        d_line = request.POST.get('deadline')
        creator=default_user
        assignee=default_user
        
        # Creem l'issue i l'assignem a nosaltres mateixos (Requisit)
        Issue.objects.create(
            subject=subject,
            description=description,
            issue_type= issue_type,
            issue_severity=issue_severity,
            priority=priority,
            status=status,
            deadline=d_line if d_line else None,
            creator=default_user,
            assignee=default_user
        )
        return redirect('issue_list')
    
    return render(request, 'issues/create.html')


def issue_detail(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    edit_comment_id = request.GET.get('edit_comment')
    edit_comment_obj = None
    if edit_comment_id:
        edit_comment_obj = get_object_or_404(Comment, id=edit_comment_id, issue=issue)

    return render(request, 'issues/detail.html', {'issue': issue,'edit_comment_obj': edit_comment_obj})

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
        if nuevo_estado:
            issue.status = nuevo_estado
            issue.save()
    return redirect('issue_list')

def comment_add(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    if request.method == "POST":
        text = request.POST.get('body', '').strip()
        if text:
            # Si el usuario no está logueado, usamos el primero de la base de datos
            author = request.user
            if not author.is_authenticated:
                author = User.objects.first()

            Comment.objects.create(issue=issue, author=author, body=text)

    # Importante: Usa issue_id=issue_id para coincidir con tu nombre en urls.py
    return redirect('issue_detail', issue_id=issue_id)

def comment_edit(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    #Simulamos que el admin puede hacer todo
    current_user = User.objects.first()
    # Només el creador edita request.user
    if request.method == 'POST' and comment.author == current_user:
        text = request.POST.get('body', '').strip()
        if text:
            comment.body = text
            comment.save()

    return redirect('issue_detail', issue_id=comment.issue.id)

def comment_delete(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    issue_id = comment.issue.id

    # Simulamos el admin
    current_user = User.objects.first()

    # Només el creador esborra request.user
    if comment.author == current_user:
        comment.delete()
    return redirect('issue_detail', issue_id=issue_id)

def user_comments_view(request, username):
    # Obtenemos al usuario del perfil que estamos visitando
    profile_user = get_object_or_404(User, username=username)

    # Ordenados de más recientes a menos
    user_comments = Comment.objects.filter(author=profile_user).order_by('-created_at')

    return render(request, 'users/profile_comments_tab.html', {
        'profile_user': profile_user,
        'user_comments': user_comments,
    })