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
from issues.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_page, name='login_page'),
    path('issues/', issue_list, name='issue_list'),
    path('new/', issue_create, name='issue_create'),
    path('new_bulk/', issue_bulk_create, name='issue_bulk_create'),
    path('issue/<int:issue_id>/', issue_detail, name='issue_detail'),
    path('issue/<int:issue_id>/delete/', issue_delete, name='issue_delete'),
    path('issue/<int:issue_id>/update-status/', issue_update_status, name='issue_update_status'),
    path('issue/<int:issue_id>/update-assignee/', issue_update_assignee, name='issue_update_assignee'),

    path('issue/<int:issue_id>/add_watcher/', add_watcher, name='add_watcher'),
    path('issue/<int:issue_id>/toggle_watcher/', toggle_watcher, name='toggle_watcher'),

    path('issue/<int:issue_id>/comment/', comment_add, name='comment_add'),
    path('comment/<int:comment_id>/edit/', comment_edit, name='comment_edit'),
    path('comment/<int:comment_id>/delete/', comment_delete, name='comment_delete'),
    path('users/<str:username>/', user_comments_view, name='user_profile'),
    path('users/<str:username>/edit/', edit_profile, name='edit_profile'),
    path('accounts/', include('allauth.urls')),

    path('issue/<int:issue_id>/attachments', add_attachment, name='add_attachment'),
    path('attachments/<int:attachment_id>/delete', delete_attachment, name='delete_attachment'),

    path('settings/', settings_page, name='settings_page'),
    path('settings/<str:entity>/add/', settings_save, name='settings_add'),
    path('settings/<str:entity>/<int:pk>/edit/', settings_save, name='settings_edit'),
    path('settings/<str:entity>/<int:pk>/delete/', settings_delete, name='settings_delete'),
    path('settings/statuses/<int:pk>/toggle-closed/', settings_toggle_closed, name='settings_toggle_closed'),
    path('settings/<str:entity>/<int:pk>/move-up/', settings_move_up, name='settings_move_up'),
    path('settings/<str:entity>/<int:pk>/move-down/', settings_move_down, name='settings_move_down'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
