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


class IssueActivity(models.Model):
    objects = models.Manager()

    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='activities')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    field_name = models.CharField(max_length=80)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.issue_id} {self.field_name}: {self.old_value} -> {self.new_value}"

class Attachment(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='attachments')
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='attachments')
    name = models.TextField()


#Models dels atributs

class Status(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, blank=True)  # hex, e.g. "#34495e"
    is_default = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Priority(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=50, unique=True)
    is_default = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class IssueType(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=50, unique=True)
    is_default = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Severity(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=50, unique=True)
    is_default = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Tag(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, blank=True)  # hex, e.g. "#5dc5b5"

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DueDate(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=50, unique=True)
    date = models.DateField()

    class Meta:
        ordering = ['date']

    def __str__(self):
        return self.name
