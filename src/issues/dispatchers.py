from django.utils.crypto import get_random_string

from .controllers.controllers_web import *
from .controllers.controllers_api import *
from .helpers import validate_api_key
from .models import Profile


def _is_api_request(request):
    """Return True when the request should be treated as API.

    Heuristics:
    - If the client explicitly requests JSON in the Accept header
    - If an Authorization header is present (API key)
    - If the content type is JSON
    Otherwise treat as a web (HTML) request.
    """
    accept = request.META.get('HTTP_ACCEPT', '') or ''
    if 'application/json' in accept:
        return True
    if request.headers.get('Authorization'):
        return True
    if request.content_type == 'application/json':
        return True
    return False

# ISSUES
def issues_dispatcher(request):
    if not _is_api_request(request):
        if not request.user.is_authenticated:
            return redirect('/')

        #Lista filtro i new
        if request.method == 'GET':
            if 'new' in request.path:
                return render_issue_create(request)
            else:
                return issue_list_web(request)

        #Creacion
        if request.method == 'POST':
            return issue_create_web(request)
    else:
        user = validate_api_key(request.headers.get("Authorization"))
        if isinstance(user, JsonResponse):
            return user

        if request.method == 'GET':
            return issue_list_api(request)
        elif request.method == 'POST':
            data = {
                'subject': request.POST.get('subject'),
                'description': request.POST.get('description'),
                'assignee': request.POST.get('assignee'),
                'deadline': request.POST.get('deadline'),
                'issue_type': request.POST.get('issue_type'),
                'priority': request.POST.get('priority'),
                'issue_severity': request.POST.get('issue_severity'),
                'status': request.POST.get('status'),
                'attachment': request.FILES.get('files')
            }

            return issue_create_api(data, user)

    return JsonResponse({'message': 'Method not allowed'}, status=405)

def issue_detail_dispatcher(request, issue_id):
    try:
        issue = get_object_or_404(Issue, id=issue_id)
    except Http404:
        return JsonResponse({'message': f'There is no issue with \'id\'={issue_id}'}, status=404)

    # Web
    if not _is_api_request(request):
        if request.method == 'GET':
            return issue_detail_web(request, issue)

        if request.method == 'POST':
            # ERROR 403: No es el creador
            if request.POST.get('_method') == 'DELETE' or 'delete' in request.path:
                if issue.creator == request.user:
                    return issue_delete_web(request, issue_id)
                else:
                    return HttpResponseForbidden("You don't have permissions to delete")
        else:
            return issue_detail_web(request,issue)

    # API
    else:
        user = validate_api_key(request.headers.get("Authorization"))
        if isinstance(user, JsonResponse):
            return user

        if request.method == 'GET':
            return issue_detail_api(issue)
        else:
            auth_check = validate_api_user(request.headers.get("Authorization"), issue.creator.id)
            if isinstance(auth_check, JsonResponse):
                return auth_check

            if request.method == 'PUT':
                try:
                    data = json.loads(request.body)
                except (json.JSONDecodeError, ValueError):
                    return JsonResponse({'message': 'Invalid JSON body'}, status=400)

                return issue_edit_api(data, issue, user)
            elif request.method == 'DELETE':
                return issue_delete_api(issue_id)

    return JsonResponse({'message': 'Method not allowed'}, status=405)

def issues_bulk_dispatcher(request):
    if not _is_api_request(request):
        if not request.user.is_authenticated:
            return redirect('/')

        if request.method == 'GET':
            return render_issue_bulk_create(request)
        elif request.method == 'POST':
            return issue_bulk_web(request)
    else:
        if request.method == 'POST':
            user = validate_api_key(request.headers.get("Authorization"))
            if isinstance(user, JsonResponse):
                return user

            try:
                data = json.loads(request.body)
            except (json.JSONDecodeError, ValueError):
                return JsonResponse({'message': 'Invalid JSON body'}, status=400)

            if 'list' not in data:
                return JsonResponse({'message': "Subject list is required."}, status=400)

            return issue_bulk_api(data['list'], user)

    return JsonResponse({'message': 'Method not allowed'}, status=405)

def issue_update_assignee_dispatcher(request, issue_id):
    try:
        issue = get_object_or_404(Issue, id=issue_id)
    except Http404:
        return JsonResponse({'message': f'Issue {issue_id} not found'}, status=404)

    # Web
    if not _is_api_request(request):
        if not request.user.is_authenticated:
            return redirect('/')

        if request.method == 'POST':
            return issue_update_assignee_web(request, issue)

    # API
    else:
        user = validate_api_key(request.headers.get("Authorization"))
        if isinstance(user, JsonResponse):
            return user

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'message': 'Invalid JSON body'}, status=400)

        if request.method == 'PUT':
            return issue_update_assignee_api(data, issue, user)

    return JsonResponse({'message': 'Method not allowed'}, status=405)

def issue_watchers_dispatcher(request, issue_id, watcher_id=None):
    # only API
    try:
        issue = get_object_or_404(Issue, id=issue_id)
    except Http404:
        return JsonResponse({'message': 'There is no issue with \'id\'=' + str(issue_id)}, status=404)

    user = validate_api_key(request.headers.get("Authorization"))
    if isinstance(user, JsonResponse):
        return user

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'message': 'Invalid JSON body'}, status=400)

        return watcher_add_api(user, issue, data)
    elif request.method == 'DELETE':
        return watcher_remove_api(user, issue, watcher_id)

    return JsonResponse({'message': 'Method not allowed'}, status=405)

# ATTACHMENTS
def attachments_dispatcher(request, issue_id):
    try:
        issue = get_object_or_404(Issue, id=issue_id)
    except Http404:
        return JsonResponse({'message': 'There is no issue with \'id\'=' + str(issue_id)}, status=404)

    # Web
    if not _is_api_request(request):
        if request.method == 'POST':
            return attachment_add_web(request, issue)
    # API
    else:
        user = validate_api_key(request.headers.get("Authorization"))
        if isinstance(user, JsonResponse):
            return user

        if request.method == 'POST':
            uploaded_attachment = request.FILES.get('files')
            if not uploaded_attachment:
                return JsonResponse({'message': 'An attachment is mandatory'}, status=400)

            return attachment_add_api(uploaded_attachment, issue, user)
        elif request.method == 'GET':
            return attachment_list_api(issue_id)

    return JsonResponse({'message': 'Method not allowed'}, status=405)

def attachment_instance_dispatcher(request, attachment_id):
    # only used by API
    try:
        target_attachment = get_object_or_404(Attachment, id=attachment_id)
    except Http404:
        return JsonResponse({'message': f'There is no attachment with \'id\'={attachment_id}'}, status=404)

    user = validate_api_key(request.headers.get("Authorization"))
    if isinstance(user, JsonResponse):
        return user

    if request.method == 'DELETE':
        perm = validate_api_user(request.headers.get("Authorization"), target_attachment.creator.id)
        if isinstance(perm, JsonResponse):
            return perm

        return attachment_delete_api(target_attachment)
    elif request.method == 'GET':
        return attachment_get_api(target_attachment)

    return JsonResponse({'message': 'Method not allowed'}, status=405)

# COMMENTS
def comments_dispatcher(request, issue_id):
    try:
        get_object_or_404(Issue, id=issue_id)
    except Http404:
        return JsonResponse({'message': f"There is no issue with 'id'={issue_id}"}, status=404)

    if not _is_api_request(request):
        if request.method == 'POST':
            return comment_add_web(request, issue_id)
    else:
        user = validate_api_key(request.headers.get("Authorization"))
        if isinstance(user, JsonResponse):
            return user

        if request.method == 'POST':
            try:
                data = json.loads(request.body)
            except (json.JSONDecodeError, ValueError):
                return JsonResponse({'message': 'Invalid JSON body'}, status=400)

            if 'body' not in data or data['body'].strip() == '':
                return JsonResponse({'message': 'Body is required'}, status=400)

            return comment_add_api(data['body'], issue_id, user)
        elif request.method == 'GET':
            return comment_list_api(issue_id)

    return JsonResponse({'message': 'Method not allowed'}, status=405)


def comment_instance_dispatcher(request, comment_id):
    try:
        comment = get_object_or_404(Comment, id=comment_id)
    except Http404:
        return JsonResponse({'message': 'There is no comment with \'id\'=' + str(comment_id)}, status=404)

    if not _is_api_request(request):
        if comment.author != request.user:
            return JsonResponse({'message': "The provided API key does not authorize this action"}, status=403)

        if request.method == 'POST':
            if 'delete' in request.path or request.POST.get('_method') == 'DELETE':
                return comment_delete_web(request, comment_id)
            else:
                return comment_edit_web(request, comment)
        else:
            return comment_edit_web(request, comment)
    else:
        perm = validate_api_user(request.headers.get("Authorization"), comment.author.id)
        if isinstance(perm, JsonResponse):
            return perm

        if request.method == 'DELETE':
            return comment_delete_api(comment_id)
        elif request.method == 'PUT':
            try:
                data = json.loads(request.body)
            except (json.JSONDecodeError, ValueError):
                return JsonResponse({'message': 'Invalid JSON body'}, status=400)

            return comment_edit_api(data, comment)

    return JsonResponse({'message': 'Method not allowed'}, status=405)

# SETTINGS
def settings_dispatcher(request, entity, setting_id=None):
    user = validate_api_key(request.headers.get("Authorization"))
    if isinstance(user, JsonResponse):
        return user

    if entity not in SETTINGS_MODELS:
        return JsonResponse({'message': f"Unknown entity '{entity}'"}, status=404)

    if request.method == 'GET':
        return settings_list_api(entity)
    elif request.method == 'POST':
        return settings_create_api(request, entity)
    elif request.method == 'PUT':
        return settings_update_api(request, entity, setting_id)
    elif request.method == 'DELETE':
        return settings_delete_api(request, entity, setting_id)

    return JsonResponse({'message': 'Method not allowed'}, status=405)

def settings_move_dispatcher(request, entity, setting_id):
    if "text/html" in request.META.get("HTTP_ACCEPT", ""):
        return settings_move_up(request, entity, setting_id) if "up" in request.path else settings_move_down(request, entity, setting_id)

    user = validate_api_key(request.headers.get("Authorization"))
    if isinstance(user, JsonResponse):
        return user

    if entity not in SETTINGS_MODELS:
        return JsonResponse({'message': f"Unknown entity '{entity}'"}, status=404)

    if request.method == 'POST':
        if "up" in request.path:
            return settings_move_api(entity, setting_id, 'up')
        else:
            return settings_move_api(entity, setting_id, 'down')

    return JsonResponse({'message': 'Method not allowed'}, status=405)

# PROFILE
def profile_dispatcher(request, username=None):
    if not _is_api_request(request):
        return profile_view_web(request, username)

    user = validate_api_key(request.headers.get("Authorization"))
    if isinstance(user, JsonResponse):
        return user

    if request.method == 'GET':
        try:
            req_user = get_object_or_404(User, username=username)
        except Http404:
            return JsonResponse({'message': f'There is no user with \'username\'={username}'}, status=404)

        return profile_view_api(req_user, user == req_user)
    elif request.method == 'PUT':
        return profile_edit_api(request, user)

    return JsonResponse({'message': 'Method not allowed'}, status=405)
