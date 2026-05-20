"""issueTracker URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from issues.controllers.controllers_web import *
from issues.views import *
from issues.dispatchers import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_page, name='login_page'),
    
    path('issues/', issues_dispatcher, name='issue_list'),
    path('new/', issues_dispatcher, name='issue_create'),
    path('issues/bulk/', issues_bulk_dispatcher, name='issue_bulk_create'),
    path('issues/<int:issue_id>/', issue_detail_dispatcher, name='issue_detail'),
    path('issues/<int:issue_id>/delete/', issue_detail_dispatcher, name='issue_delete'),

    path('issues/<int:issue_id>/assignee/', issue_update_assignee_dispatcher, name='issue_update_assignee'),

    path('issues/<int:issue_id>/watchers/', issue_watchers_dispatcher, name='post_watcher'),
    path('issues/<int:issue_id>/watchers/<int:watcher_id>', issue_watchers_dispatcher, name='delete_watcher'),

    path('issues/<int:issue_id>/comments/', comments_dispatcher, name='comment_add'),
    path('comments/<int:comment_id>/', comment_instance_dispatcher, name='comment_api_detail'),
    path('comments/<int:comment_id>/edit/', comment_instance_dispatcher, name='comment_edit'),
    path('comments/<int:comment_id>/delete/', comment_delete_web, name='comment_delete'),

    path('profile/<str:username>/', profile_dispatcher, name='profile_view'),
    path('profile/', profile_dispatcher, name='profile_edit'),
    path('profile/<str:username>', profile_dispatcher, name='profile_edit'),
    path('accounts/', include('allauth.urls')),

    path('issues/<int:issue_id>/attachments', attachments_dispatcher, name='attachment_add'),
    path('attachments/<int:attachment_id>', attachment_instance_dispatcher, name='attachment'),

    path('settings/<str:entity>/<int:setting_id>/', settings_dispatcher, name='settings_api_detail'),
    path('settings/<str:entity>/', settings_dispatcher, name='settings_api_collection'),
    path('settings/', settings_view, name='settings_view'),
    path('settings/<str:entity>/add/', settings_save, name='settings_add'),
    path('settings/<str:entity>/<int:pk>/edit/', settings_save, name='settings_edit'),
    path('settings/<str:entity>/<int:pk>/delete/', settings_delete, name='settings_delete'),
    path('settings/statuses/<int:pk>/toggle-closed/', settings_toggle_closed, name='settings_toggle_closed'),
    path('settings/<str:entity>/<int:setting_id>/move-up/', settings_move_dispatcher, name='settings_move_up'),
    path('settings/<str:entity>/<int:setting_id>/move-down/', settings_move_dispatcher, name='settings_move_down'),

    path('attachments/<int:attachment_id>/delete', attachment_delete_web, name='attachment_delete'),

    path('issue/<int:issue_id>/watcher_add/', watcher_add_web, name='watcher_add'),
    path('issue/<int:issue_id>/remove_watcher/', watcher_remove_web, name='remove_watcher'),

    path('issue/<int:issue_id>/update-status/', issue_update_status, name='issue_update_status'),
    path('issue/<int:issue_id>/update-assignee/', issue_update_assignee_dispatcher, name='issue_update_assignee'),
    path('issue/<int:issue_id>/update-type/', issue_update_type, name='issue_update_type'),
    path('issue/<int:issue_id>/update-severity/', issue_update_severity, name='issue_update_severity'),
    path('issue/<int:issue_id>/update-priority/', issue_update_priority, name='issue_update_priority'),
    path('issue/<int:issue_id>/update-status-detail/', issue_update_status_detail, name='issue_update_status_detail'),
    path('issue/<int:issue_id>/update-subject/', issue_update_subject, name='issue_update_subject'),
    path('issue/<int:issue_id>/update-description/', issue_update_description, name='issue_update_description'),
    path('issue/<int:issue_id>/update-deadline/', issue_update_deadline_detail, name='issue_update_deadline_detail'),
    path('issue/<int:issue_id>/add-tag/', issue_add_tag, name='issue_add_tag'),
    path('issue/<int:issue_id>/remove-tag/<int:tag_id>/', issue_remove_tag, name='issue_remove_tag'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
