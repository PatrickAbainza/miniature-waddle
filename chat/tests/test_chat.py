from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch
from chat.models import Conversation, Message
from chat.services import process_user_message, get_conversation_history
import json

User = get_user_model()

class ChatTestCase(TestCase):
    """
    @atomic-test-suite
    Test suite for chat functionality using mock APIs
    """
    def setUp(self):
        """Set up test data and client"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create a test conversation
        self.conversation = Conversation.objects.create(user=self.user)
        
        # Create some test messages
        Message.objects.create(
            conversation=self.conversation,
            sender='user',
            content='Hello'
        )
        Message.objects.create(
            conversation=self.conversation,
            sender='bot',
            content='Hi there!'
        )

    @patch('chat.services.process_user_message')
    def test_chat_view_with_mock_processing(self, mock_process):
        """
        @atomic-test
        Test chat view with mocked message processing
        """
        # Mock the response from process_user_message
        mock_process.return_value = {
            'status': 'success',
            'response': 'Mocked bot response'
        }
        
        # Make a POST request to the chat endpoint
        url = reverse('chat:message')
        data = {'message': 'Test message'}
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['response'], 'Mocked bot response')
        
        # Verify mock was called correctly
        mock_process.assert_called_once_with(self.user, 'Test message')

    def test_chat_view_invalid_request(self):
        """
        @atomic-test
        Test chat view with invalid requests
        """
        url = reverse('chat:message')
        
        # Test empty message
        data = {'message': ''}
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        # Test invalid JSON
        response = self.client.post(
            url,
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        # Test GET request (should be POST only)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_conversation_history(self):
        """
        @atomic-test
        Test conversation history retrieval
        """
        url = reverse('chat:history')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertEqual(response_data['status'], 'success')
        messages = response_data['messages']
        self.assertEqual(len(messages), 2)
        
        # Verify message contents
        self.assertEqual(messages[0]['sender'], 'user')
        self.assertEqual(messages[0]['content'], 'Hello')
        self.assertEqual(messages[1]['sender'], 'bot')
        self.assertEqual(messages[1]['content'], 'Hi there!')

    @patch('chat.services.process_user_message')
    def test_error_handling(self, mock_process):
        """
        @atomic-test
        Test error handling in chat view
        """
        # Mock an error response
        mock_process.return_value = {
            'status': 'error',
            'error': 'Something went wrong'
        }
        
        url = reverse('chat:message')
        data = {'message': 'Test message'}
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'error')
        self.assertEqual(response_data['error'], 'Something went wrong')

    def test_authentication_required(self):
        """
        @atomic-test
        Test that views require authentication
        """
        # Logout the user
        self.client.logout()
        
        # Try to access chat endpoint
        url = reverse('chat:message')
        data = {'message': 'Test message'}
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        
        # Try to access history endpoint
        url = reverse('chat:history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
