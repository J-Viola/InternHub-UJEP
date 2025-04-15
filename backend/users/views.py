from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import json


@csrf_exempt
def login(request):
    if request.method == 'POST':
        try:
            # Parse credentials from request body
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return JsonResponse({
                    'success': False,
                    'message': 'Username and password are required'
                }, status=400)

            # Make request to stag.cz to get ws token
            # Note: URL and request format should be adjusted according to stag.cz API docs
            auth_response = requests.post(
                'https://ws.stag.cz/ws/login',  # Replace with actual endpoint
                data={
                    'username': username,
                    'password': password
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )

            if auth_response.status_code == 200:
                # Extract token from response (adjust field name as needed)
                auth_data = auth_response.json()
                ws_token = auth_data.get('token')

                return JsonResponse({
                    'success': True,
                    'ws_token': ws_token
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Authentication failed',
                    'status_code': auth_response.status_code,
                    'details': auth_response.text
                }, status=401)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    else:
        return JsonResponse({
            'success': False,
            'message': 'Only POST method is allowed'
        }, status=405)