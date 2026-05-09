from issues.helpers import *
from issues.models import *
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

# ISSUES
def issue_list_api(request):
    issues, order_param = apply_issue_queries(request)

    valid_fields = ['issue_type', 'issue_severity', 'priority', 'subject', 'status', 'assignee', 'modified_at', 'deadline', 'created_at']
    if order_param.lstrip('-') not in valid_fields:
        return JsonResponse({'error': f'Invalid order_by field: {order_param}'}, status=400)

    issues_data = []
    for issue in issues:
        issues_data.append({
            'id': issue.id,
            'subject': issue.subject,
            'description': issue.description,
            'priority': issue.priority.name if issue.priority else None,
            'status': issue.status.name if issue.status else None,
            'issue_type': issue.issue_type.name if issue.issue_type else None,
            'severity': issue.issue_severity.name if issue.issue_severity else None,
            'assignee': issue.assignee.username if issue.assignee else "Unassigned",
            'created_at': issue.created_at.isoformat(),
            'modified_at': issue.modified_at.isoformat() if hasattr(issue, 'modified_at') else None,
            'deadline': issue.deadline.isoformat() if issue.deadline else None,
        })

    return JsonResponse({
        'issues': issues_data,
        'current_order': order_param,
        'total_count': issues.count(),
        'unassigned_count': Issue.objects.filter(assignee__isnull=True).count()
    }, status=200)

def issue_create_api(data, user):
    subject = data['subject']
    if not subject or subject.strip() == "":
        return JsonResponse({'error': 'Subject is required'}, status=400)

    assignee_id = data['assignee']
    assignee = get_object_or_404(User, id=assignee_id) if assignee_id else None

    d_line = data['deadline']
    deadline_value = d_line if d_line and d_line.strip() != "" else None

    issue = issue_create_instance(
        subject=subject,
        description=data['description'],
        issue_type=data['issue_type'],
        issue_severity=data['issue_severity'],
        priority=data['priority'],
        status=data['status'] or 'New',
        d_line= deadline_value,
        creator=user,
        assignee=assignee
    )
    if data['attachment']:
        attachment_create_instance(issue.id, user, data['attachment'])

    return JsonResponse({
        'id': issue.id,
        'subject': issue.subject,
        'description': issue.description,
        'issue_type': issue.issue_type.name if issue.issue_type else None,
        'issue_severity': issue.issue_severity.name if issue.issue_severity else None,
        'priority': issue.priority.name if issue.priority else None,
        'status': issue.status.name if issue.status else None,
        'deadline': issue.deadline if issue.deadline else None,
        'creator': issue.creator.username if issue.creator else None,
        'assignee': issue.assignee.username if issue.assignee else None
    }, status=201)