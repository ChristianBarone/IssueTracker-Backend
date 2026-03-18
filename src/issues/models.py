from django.db import models
from django.contrib.auth.models import User

class Issue(models.Model):
    # Valors predefinits per a la Sessió 2 (Hardcoded com diuen les instruccions)
    STATUS_CHOICES = [('New', 'New'), ('In Progress', 'In Progress'), ('Closed', 'Closed')]
    PRIORITY_CHOICES = [('Low', 'Low'), ('Normal', 'Normal'), ('High', 'High')]
    TYPE_CHOICES = [('Bug', 'Bug'), ('Question', 'Question'), ('Enhancement', 'Enhancement')]

    subject = models.CharField(max_length=200) # En Taiga és 'Subject', no 'Title'
    description = models.TextField(blank=True)
    
    # Relacions
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_issues')
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_issues')
    
    # Atributs amb valors per defecte
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Normal')
    issue_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='Bug')
    
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"#{self.id} {self.subject}"