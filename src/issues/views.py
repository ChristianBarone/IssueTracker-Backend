from django.shortcuts import render, redirect
from .models import Issue
from django.contrib.auth.models import User

def issue_list(request):
    # Ordenades de més noves a més velles (Requisit)
    issues = Issue.objects.all().order_by('-created_at')
    return render(request, 'issues/list.html', {'issues': issues})

def issue_create(request):
    # Simulem usuari loguejat (Hardcoded per a Sessió 2)
    default_user = User.objects.first() 

    if request.method == "POST":
        subject = request.POST.get('subject')
        description = request.POST.get('description')
        
        # Creem l'issue i l'assignem a nosaltres mateixos (Requisit)
        Issue.objects.create(
            subject=subject,
            description=description,
            creator=default_user,
            assignee=default_user
        )
        return redirect('issue_list')
    
    return render(request, 'issues/create.html')