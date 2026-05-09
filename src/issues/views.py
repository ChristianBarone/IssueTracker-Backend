from django.shortcuts import render

from issues.models import *


def render_login_page(request, context):
    return render(request, 'issues/login.html', context)

def render_issue_list(request, context):
    return render(request, 'issues/list.html', context)

def render_issue_create(request):
    context = {
        'statuses': Status.objects.all(),
        'priorities': Priority.objects.all(),
        'issue_types': IssueType.objects.all(),
        'severities': Severity.objects.all(),
        'assignable_users': User.objects.all().order_by('username'),
    }

    return render(request, 'issues/create.html', context)

def render_issue_bulk_create(request):
    return render(request, 'issues/bulk_create.html')

def render_issue_detail(request, context):
    return render(request, 'issues/detail.html', context)

def render_profile_view(request, context):
    return render(request, 'users/profile.html', context)

def render_profile_edit(request, context):
    return render(request, 'users/edit_profile.html', context)

def render_settings_view(request, context):
    return render(request, 'settings/settings.html', context)

def render_settings_delete(request, context):
    return render(request, 'settings/settings_delete_confirm.html', context)

def render_settings_form(request, context):
    return render(request, 'settings/settings_form.html', context)