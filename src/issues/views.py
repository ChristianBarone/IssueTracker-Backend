from django.shortcuts import render, redirect, get_object_or_404
from .models import Issue, Comment
from django.contrib.auth.models import User
from django.db.models import Q, Count

def issue_list(request):
    # Ordenades de més noves a més velles (Requisit)
    issues = Issue.objects.all().order_by('-created_at')

    #Captura de parámetros
    selected_types = request.GET.getlist('issue_type')
    selected_statuses = request.GET.getlist('status')
    selected_severities = request.GET.getlist('issue_severity')
    selected_priorities = request.GET.getlist('priority')

    #Lògica de FILTRES
    f_assignee = request.GET.get('assigned_to')
    search_query = request.GET.get('search', '').strip()
    mode = request.GET.get('mode', 'include')

    show_filters = request.GET.get('show_filters') == '1'

    if search_query:
        issues = issues.filter(Q(subject__icontains=search_query) | Q(id__icontains=search_query))

    def apply_filter(qs, field, values):
        if not values: return qs
        if mode == 'exclude':
            return qs.exclude(**{f"{field}__in": values})
        return qs.filter(**{f"{field}__in": values})

    issues = apply_filter(issues, 'issue_type', selected_types)
    issues = apply_filter(issues, 'status', selected_statuses)
    issues = apply_filter(issues, 'issue_severity', selected_severities)
    issues = apply_filter(issues, 'priority', selected_priorities)

    if f_assignee:
        issues = issues.filter(assignee_id=f_assignee)

    base_stats = Issue.objects.all()

    users = User.objects.annotate(num_issues=Count('assigned_issues'))
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

        # Priorities
        'low': base_stats.filter(priority='Low').count(),
        'normal_prio': base_stats.filter(priority='Normal').count(),
        'high': base_stats.filter(priority='High').count(),

        # Status
        'new': base_stats.filter(status='New').count(),
        'in_progress': base_stats.filter(status='In Progress').count(),
        'ready_test': base_stats.filter(status='Ready for test').count(),
        'needs_info': base_stats.filter(status='Needs Info').count(),
        'rejected': base_stats.filter(status='Rejected').count(),
        'postponed': base_stats.filter(status='Postponed').count(),
        'closed': base_stats.filter(status='Closed').count(),
    }

    # Necesario para el conteo de usuarios
    #user_counts = {}
    #for u in users:
        #user_counts[u.id] = base_stats.filter(assignee=u).count()

    context = {
        'issues': issues,
        'counts': counts,
        'users': users,
        'show_filters': show_filters,
        # Opciones para el HTML
        'all_types': ['Bug', 'Question', 'Enhancement'],
        'all_severities': ['Wishlist', 'Minor', 'Normal', 'Important', 'Critical'],
        'all_priorities': ['Low', 'Normal', 'High'],
        'all_statuses': ['New', 'In Progress', 'Ready for test', 'Needs Info', 'Rejected', 'Postponed', 'Closed'],
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
    return render(request, 'issues/detail.html', {'issue': issue})

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
        if text: # No buit
            Comment.objects.create(issue=issue, author=request.user, body=text)
    return redirect('issue_detail', pk=issue_id)

def comment_edit(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    # Només el creador edita
    if comment.author != request.user:
        return redirect('issue_detail', pk=comment.issue.id)

    if request.method == "POST":
        comment.body = request.POST.get('body')
        comment.save()
        return redirect('issue_detail', pk=comment.issue.id)

    return render(request, 'issues/comment_edit.html', {'comment': comment})

def comment_delete(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    issue_id = comment.issue.id
    # Només el creador esborra
    if comment.author == request.user:
        comment.delete()
    return redirect('issue_detail', pk=issue_id)