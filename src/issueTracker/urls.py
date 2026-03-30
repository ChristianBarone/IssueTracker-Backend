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
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from issues.views import issue_list, issue_create, issue_bulk_create, issue_detail, issue_delete, issue_update_status, comment_add, comment_edit, comment_delete

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', issue_list, name='issue_list'),      # La página principal será la lista
    path('new/', issue_create, name='issue_create'),
    path('new_bulk/', issue_bulk_create, name='issue_bulk_create'),
    path('issue/<int:issue_id>/', issue_detail, name='issue_detail'),
    path('issue/<int:issue_id>/delete/', issue_delete, name='issue_delete'),
    path('issue/<int:issue_id>/update-status/', issue_update_status, name='issue_update_status'),

    path('issue/<int:issue_id>/comment/', comment_add, name='comment_add'),
    path('comment/<int:comment_id>/edit/', comment_edit, name='comment_edit'),
    path('comment/<int:comment_id>/delete/', comment_delete, name='comment_delete'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
