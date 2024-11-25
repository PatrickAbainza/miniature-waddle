from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods
from .services import process_user_message, get_conversation_history, validate_message_size

# Create your views here.

@csrf_protect
@login_required
def chat_view(request):
    """
    @atomic-view
    Handles chat messages and returns bot responses
    """
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'error': 'Invalid request method'
        }, status=400)
    
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({
                'status': 'error',
                'error': 'Message cannot be empty'
            }, status=400)
        
        response = process_user_message(request.user, user_message)
        return JsonResponse(response)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)

@csrf_protect
@login_required
def message_view(request):
    """
    @atomic-view
    Handle incoming chat messages
    """
    try:
        data = json.loads(request.body)
        content = data.get('message', '')
        
        # Process message and handle validation errors
        result = process_user_message(request.user, content)
        
        if result.get('status') == 'error':
            return JsonResponse(
                {'error': result['error']},
                status=400
            )
            
        return JsonResponse(result)
            
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Invalid JSON'},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=500
        )

@login_required
def conversation_history(request):
    """
    @atomic-view
    Returns the conversation history for the current user
    """
    if request.method != 'GET':
        return JsonResponse({
            'status': 'error',
            'error': 'Invalid request method'
        }, status=400)
    
    try:
        limit = int(request.GET.get('limit', 50))
        history = get_conversation_history(request.user, limit)
        
        return JsonResponse({
            'status': 'success',
            'messages': history
        })
        
    except ValueError:
        return JsonResponse({
            'status': 'error',
            'error': 'Invalid limit parameter'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
