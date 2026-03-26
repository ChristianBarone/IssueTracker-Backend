from django.shortcuts import render, redirect, get_object_or_404
from .models import Issue, Comment
from django.contrib.auth.models import User
from django.db.models import Q

def issue_list(request):
    # Ordenades de més noves a més velles (Requisit)
    issues = Issue.objects.all().order_by('-created_at')

    search_query = request.GET.get('search')
    #Lògica de FILTRES
    f_type = request.GET.get('issue_type')
    f_status = request.GET.get('status')
    f_sev = request.GET.get('issue_severity')
    f_prio = request.GET.get('priority')
    show_filters = request.GET.get('show_filters') == '1'

    if search_query:
        issues = issues.filter(Q(subject__icontains=search_query) | Q(id__icontains=search_query))

    if f_status:
        issues = issues.filter(status=f_status)

    if f_type:
        issues = issues.filter(issue_type=f_type)
    if f_sev:
        issues = issues.filter(issue_severity=f_sev)
    if f_prio:
        issues = issues.filter(priority=f_prio)

    base_stats = Issue.objects.all()
    counts = {
        'bug': base_stats.filter(issue_type='Bug').count(),
        'question': base_stats.filter(issue_type='Question').count(),
        'enhancement': base_stats.filter(issue_type='Enhancement').count(),
        'wishlist': base_stats.filter(issue_type='Wishlist').count(),
        'minor': base_stats.filter(issue_type='Minor').count(),
        'normal': base_stats.filter(issue_type='Normal').count(),
        'important': base_stats.filter(issue_type='Important').count(),
        'critical': base_stats.filter(issue_type='Critical').count(),
        'new': base_stats.filter(status='New').count(),
        'done': base_stats.filter(status='Done').count(),
    }

    context = {
        'issues': issues,
        'counts': counts,
        'show_filters': show_filters,
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