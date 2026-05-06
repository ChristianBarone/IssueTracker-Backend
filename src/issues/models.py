import os

from django.db import models
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string

API_KEY_LENGTH=32

def generate_api_key():
    return get_random_string(length=API_KEY_LENGTH)

class Profile(models.Model):
    objects = models.Manager()
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    api_key = models.CharField(max_length=API_KEY_LENGTH, editable=False, default=generate_api_key)

    def __str__(self):
        return str(self.user)


class Issue(models.Model):
    objects = models.Manager()

    subject = models.CharField(max_length=200) # En Taiga és 'Subject', no 'Title'
    description = models.TextField(blank=True)

    # Relacions amb usuaris
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_issues')
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_issues')
    watchers = models.ManyToManyField(User, related_name='watched_issues', blank=True)
    tags = models.ManyToManyField('Tag', blank=True)

    # Atributs dinàmics (gestionats des de Settings)
    status = models.ForeignKey('Status', on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.ForeignKey('Priority', on_delete=models.SET_NULL, null=True, blank=True)
    issue_type = models.ForeignKey('IssueType', on_delete=models.SET_NULL, null=True, blank=True)
    issue_severity = models.ForeignKey('Severity', on_delete=models.SET_NULL, null=True, blank=True)

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
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    color = models.CharField(max_length=7, blank=True)  # hex, e.g. "#70728F"
    is_default = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'is_default' in update_fields:
            if self.is_default:
                Status.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
            elif self.pk and not Status.objects.filter(is_default=True).exclude(pk=self.pk).exists():
                self.is_default = True
        super().save(*args, **kwargs)


class Priority(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, blank=True)  # hex, e.g. "#E4CE40"
    is_default = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'is_default' in update_fields:
            if self.is_default:
                Priority.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
            elif self.pk and not Priority.objects.filter(is_default=True).exclude(pk=self.pk).exists():
                self.is_default = True
        super().save(*args, **kwargs)


class IssueType(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, blank=True)  # hex, e.g. "#E44057"
    is_default = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'is_default' in update_fields:
            if self.is_default:
                IssueType.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
            elif self.pk and not IssueType.objects.filter(is_default=True).exclude(pk=self.pk).exists():
                self.is_default = True
        super().save(*args, **kwargs)


class Severity(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, blank=True)  # hex, e.g. "#E44057"
    is_default = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'is_default' in update_fields:
            if self.is_default:
                Severity.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
            elif self.pk and not Severity.objects.filter(is_default=True).exclude(pk=self.pk).exists():
                self.is_default = True
        super().save(*args, **kwargs)


class Tag(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, blank=True)  # hex, e.g. "#5dc5b5"

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DueDate(models.Model):
    BEFORE = 'before'
    AFTER  = 'after'
    DIRECTION_CHOICES = [(BEFORE, 'Before'), (AFTER, 'After')]

    objects = models.Manager()
    name            = models.CharField(max_length=50, unique=True)
    color           = models.CharField(max_length=7, blank=True)
    days_offset     = models.IntegerField(null=True, blank=True)   # null = default/always
    before_or_after = models.CharField(max_length=6, choices=DIRECTION_CHOICES, null=True, blank=True)
    order           = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name
