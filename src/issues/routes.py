from .controllers import *
from .helpers import validate_api_key


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

# ATTACHMENTS
def attachments(request, issue_id):
    if not _is_api_request(request):
        if request.method == 'POST':
            return attachment_add_web(request, issue_id)
        else:
            response = JsonResponse({'message': 'The requested method for this resource is not allowed'}, status=205)
            response.headers["Allow"] = "GET, POST"
            return response

    else:
        try:
            get_object_or_404(Issue, id=issue_id)
        except Http404:
            return JsonResponse({'message': 'There is no issue with \'id\'=' + str(issue_id)}, status=404)

        if request.user.is_authenticated:
            user = request.user
        else:
            user = validate_api_key(request.headers.get("Authorization"))
            if type(user) is JsonResponse:
                return user

        if request.method == 'POST':
            return attachment_add_api(request, issue_id, user)
        elif request.method == 'GET':
            return attachment_list_api(issue_id)
        else:
            response = JsonResponse({'message': 'The requested method for this resource is not allowed'}, status=205)
            response.headers["Allow"] = "GET, POST"
            return response

def attachment(request, attachment_id):
    # only used by API
    try:
        attachment = get_object_or_404(Attachment, id=attachment_id)
    except Http404:
        return JsonResponse({'message': 'There is no attachment with \'id\'=' + str(attachment_id)}, status=404)

    if request.user.is_authenticated:
        user = request.user
    else:
        user = validate_api_key(request.headers.get("Authorization"))
        if type(user) is JsonResponse:
            return user

    if request.method == 'DELETE':
        if request.user.is_authenticated:
            perm = request.user
        else:
            perm = validate_api_user(request.headers.get("Authorization"), attachment.creator.id)
            if type(perm) is JsonResponse:
                return perm

        return attachment_delete_api(attachment_id)
    elif request.method == 'GET':
        return attachment_get_api(attachment_id)
    else:
        response = JsonResponse({'message': 'The requested method for this resource is not allowed'}, status=205)
        response.headers["Allow"] = "GET, DELETE"
        return response

# COMMENTS

def issue_comments(request, issue_id):
    if not _is_api_request(request):
        if request.method == 'POST':
            return comment_add_web(request, issue_id)
        else:
            response = JsonResponse({'message': 'Method not allowed'}, status=405)
            response.headers["Allow"] = "POST"
            return response

    else:
        try:
            get_object_or_404(Issue, id=issue_id)
        except:
            return JsonResponse({'message': f"There is no issue with 'id'={issue_id}"}, status=404)

        if request.user.is_authenticated:
            user = request.user
        else:
            user = validate_api_key(request.headers.get("Authorization"))
            if type(user) is JsonResponse: return user

        if request.method == 'POST':
            return comment_add_api(request, issue_id, user)
        elif request.method == 'GET':
            return comment_list_api(issue_id)
        else:
            response = JsonResponse({'message': 'The requested method for this resource is not allowed'}, status=405)
            response.headers["Allow"] = "GET, POST"
            return response


def comment_detail_route(request, comment_id):
    # Only api
    try:
        comment = get_object_or_404(Comment, id=comment_id)
    except Http404:
        return JsonResponse({'message': 'There is no comment with \'id\'=' + str(comment_id)}, status=404)

    if not _is_api_request(request):
        if comment.author != request.user:
            return JsonResponse({'message': 'Forbidden'}, status=403)

        if request.method == 'POST':
            if 'delete' in request.path or request.POST.get('_method') == 'DELETE':
                return comment_delete_web(request, comment_id)
            return comment_edit_web(request, comment)

    else:
        if request.user.is_authenticated:
            user = request.user
        else:
            user = validate_api_key(request.headers.get("Authorization"))
            if type(user) is JsonResponse: return user

        if request.user.is_authenticated:
            perm = request.user
        else:
            perm = validate_api_user(request.headers.get("Authorization"), comment.author.id)
            if type(perm) is JsonResponse: return perm

        if request.method == 'DELETE':
            return comment_delete_api(comment_id)
        elif request.method == 'PUT' or request.method == 'POST':
            return comment_edit_api(request, comment)

    response = JsonResponse({'message': 'Method not allowed'}, status=405)
    response.headers["Allow"] = "GET, POST, PUT, DELETE"
    return response

def issues_dispatcher(request):
    if not _is_api_request(request):
        if not request.user.is_authenticated:
            return redirect('/')
        #Lista filtron i new
        if request.method == 'GET':
            if 'new' in request.path:
                return issue_create_web(request)
            else:
                return issue_list_web(request)
        #Creacion
        if request.method == 'POST':
            return issue_create_web(request)
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    else:
        if request.user.is_authenticated:
            user = request.user
        else:
            user = validate_api_key(request.headers.get("Authorization"))
            if isinstance(user, JsonResponse):
                return user
        if request.method == 'GET':
            return issue_list_api(request)
        elif request.method == 'POST':
            return issue_create_api(request, user)
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
        if request.user.is_authenticated:
            user = request.user
        else:
            user = validate_api_key(request.headers.get("Authorization"))
            if isinstance(user, JsonResponse):
                return user

        if request.method == 'POST':
            if request.POST.get('list') is None:
                return JsonResponse({'message': "Subject list is required."}, status=400)

            return issue_bulk_api(request.POST.get('list').split(','), user)

    return JsonResponse({'message': 'Method not allowed'}, status=405)

def issue_detail_dispatcher(request, issue_id):
    try:
        issue = get_object_or_404(Issue, id=issue_id)
    except Exception:
        if "text/html" in request.META.get("HTTP_ACCEPT", ""):
            return render(request, '404.html', status=404)
        return JsonResponse({'error': f'Issue {issue_id} not found'}, status=404)

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
            return issue_detail_web(request,issue)

    # API
    else:
        if request.user.is_authenticated:
            user = request.user
        else:
            user = validate_api_key(request.headers.get("Authorization"))
            if isinstance(user, JsonResponse):
                return user

        if request.method == 'GET':
            return issue_detail_api(issue)

        elif request.method == 'PUT':
            if request.user.is_authenticated:
                auth_check = request.user
            else:
                auth_check = validate_api_user(request.headers.get("Authorization"), issue.creator.id)
                if isinstance(auth_check, JsonResponse):
                    return auth_check
            return issue_edit_api(request, issue, auth_check)

        elif request.method == 'DELETE':
            if request.user.is_authenticated:
                auth_check = request.user
            else:
                auth_check = validate_api_user(request.headers.get("Authorization"), issue.creator.id)
                if isinstance(auth_check, JsonResponse):
                    return auth_check
            return issue_delete_api(issue_id)

        else:
            response = JsonResponse({'message': 'Method not allowed'}, status=405)
            response.headers["Allow"] = "GET, PUT, DELETE"
            return response
        
def issue_update_assignee_dispatcher(request, issue_id):

    if not _is_api_request(request):
        return issue_update_assignee_web(request, issue_id)

    else:
        if request.user.is_authenticated:
            user = request.user
        else:
            user = validate_api_key(request.headers.get("Authorization"))
            if isinstance(user, JsonResponse):
                return user

        return issue_update_assignee_api(request, issue_id, user)