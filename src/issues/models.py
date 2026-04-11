import os

from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    objects = models.Manager()
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)

    def __str__(self):
        return str(self.user)

class Issue(models.Model):
    objects = models.Manager()
    # Valors predefinits per a la Sessió 2 (Hardcoded com diuen les instruccions)
    STATUS_CHOICES = [('New', 'New'), ('In Progress', 'In Progress'), ('Ready for test', 'Ready for test'), ('Closed', 'Closed'), ('Needs Info', 'Needs Info'), ('Rejected', 'Rejected'), ('Postponed', 'Postponed')]
    PRIORITY_CHOICES = [('Low', 'Low'), ('Normal', 'Normal'), ('High', 'High')]
    TYPE_CHOICES = [('Bug', 'Bug'), ('Question', 'Question'), ('Enhancement', 'Enhancement')]
    SEVERITY_CHOICES = [('Minor', 'Minor'), ('Normal', 'Normal'), ('Important', 'Important'), ('Critical', 'Critical')]

    subject = models.CharField(max_length=200) # En Taiga és 'Subject', no 'Title'
    description = models.TextField(blank=True)
    
    # Relacions
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_issues')
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_issues')
    watchers = models.ManyToManyField(User, related_name='watched_issues', blank=True)

    # Atributs amb valors per defecte
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Normal')
    issue_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='Bug')
    issue_severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='Normal')

    deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"#{self.pk} {self.subject}"

class Comment(models.Model):
    objects = models.Manager()
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_edited(self):
         return self.updated_at > self.created_at

class Attachment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='attachments')
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='attachments')
    name = models.TextField()
