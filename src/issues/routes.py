from .controllers import *

# ATTACHMENTS
def attachments(request, issue_id):
    if request.content_type == "text/html":
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

    user = validate_api_key(request.headers.get("Authorization"))
    if type(user) is JsonResponse:
        return user

    if request.method == 'DELETE':
        user = validate_api_user(request.headers.get("Authorization"), attachment.creator.id)
        if type(user) is JsonResponse:
            return user

        return attachment_delete_api(attachment_id)
    elif request.method == 'GET':
        return attachment_get_api(attachment_id)
    else:
        response = JsonResponse({'message': 'The requested method for this resource is not allowed'}, status=205)
        response.headers["Allow"] = "GET, DELETE"
        return response