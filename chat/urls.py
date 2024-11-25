from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('message/', views.chat_view, name='message'),
    path('history/', views.conversation_history, name='history'),
]
