from django.shortcuts import render, redirect
from issues.models import Issue

def issue_list(request):
    # Agafem tots els issues de la base de dades
    issues = Issue.objects.all().order_by('-created_at')
    return render(request, 'issues/list.html', {'issues': issues})

def issue_create(request):
    if request.method == "POST":
        # Guardem el que l'usuari ha enviat pel formulari
        title = request.POST.get('title')
        description = request.POST.get('description')
        Issue.objects.create(title=title, description=description)
        return redirect('issue_list')
    return render(request, 'issues/create.html')