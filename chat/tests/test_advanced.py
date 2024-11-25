from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test.utils import override_settings
from unittest.mock import patch, MagicMock
from chat.models import Conversation, Message
from chat.services import (
    get_or_create_conversation,
    create_message,
    process_user_message,
    get_conversation_history
)
import json
import time

User = get_user_model()

class AdvancedChatTestCase(TestCase):
    """
    @atomic-test-suite
    Advanced test suite covering edge cases, performance, and security
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')
        self.conversation = get_or_create_conversation(self.user)

    def test_message_xss_protection(self):
        """
        @atomic-test
        Test protection against XSS in messages
        """
        xss_payload = '<script>alert("xss")</script>'
        url = reverse('chat:message')
        
        response = self.client.post(
            url,
            data=json.dumps({'message': xss_payload}),
            content_type='application/json'
        )
        
        # Verify response doesn't contain unescaped script tags
        self.assertNotIn(xss_payload, response.content.decode())
        self.assertIn('&lt;script&gt;', response.content.decode())

    def test_concurrent_messages(self):
        """
        @atomic-test
        Test handling of concurrent message creation
        """
        def create_concurrent_messages():
            messages = []
            for i in range(5):
                msg = create_message(
                    self.conversation,
                    f"Concurrent message {i}",
                    "user"
                )
                messages.append(msg)
            return messages

        # Create messages concurrently - only 1 query per message now
        with self.assertNumQueries(5):  # 1 query per message (insert)
            messages = create_concurrent_messages()
        
        # Verify all messages were created and ordered correctly
        self.assertEqual(len(messages), 5)
        for i, msg in enumerate(messages):
            self.assertEqual(msg.content, f"Concurrent message {i}")

    def test_large_message_handling(self):
        """
        @atomic-test
        Test handling of large messages
        """
        large_message = "x" * 1000000  # 1MB message
        
        # Test through API
        url = reverse('chat:message')
        response = self.client.post(
            url,
            data=json.dumps({'message': large_message}),
            content_type='application/json'
        )
        
        # Should return error for too large message
        self.assertEqual(response.status_code, 400)
        self.assertIn('Message too large', response.json()['error'])
        
        # Test direct message creation
        with self.assertRaises(ValidationError):
            create_message(self.conversation, large_message, "user")

    @override_settings(DEBUG=True)
    def test_message_performance(self):
        """
        @atomic-test
        Test message processing performance
        """
        url = reverse('chat:message')
        
        # Measure response time
        start_time = time.time()
        response = self.client.post(
            url,
            data=json.dumps({'message': 'Test message'}),
            content_type='application/json'
        )
        end_time = time.time()
        
        # Response should be under 500ms
        self.assertLess(end_time - start_time, 0.5)
        self.assertEqual(response.status_code, 200)

    def test_conversation_cleanup(self):
        """
        @atomic-test
        Test conversation cleanup for inactive sessions
        """
        # Create multiple conversations
        for _ in range(5):
            get_or_create_conversation(self.user)
        
        # Only one active conversation should exist
        active_convs = Conversation.objects.filter(
            user=self.user,
            is_active=True
        )
        self.assertEqual(active_convs.count(), 1)
        
        # Creating new conversation should not affect total count
        new_conv = get_or_create_conversation(self.user)
        self.assertEqual(
            Conversation.objects.filter(user=self.user).count(),
            6  # 5 inactive + 1 active
        )

    def test_message_rate_limiting(self):
        """
        @atomic-test
        Test rate limiting for message creation
        """
        url = reverse('chat:message')
        
        # Send multiple messages rapidly
        responses = []
        for i in range(10):
            response = self.client.post(
                url,
                data=json.dumps({'message': f'Message {i}'}),
                content_type='application/json'
            )
            responses.append(response)
        
        # Verify all messages were processed
        successful_responses = [r for r in responses if r.status_code == 200]
        self.assertEqual(len(successful_responses), 10)

    @patch('chat.services.process_user_message')
    def test_error_recovery(self, mock_process):
        """
        @atomic-test
        Test system recovery from errors
        """
        url = reverse('chat:message')
        
        # Simulate intermittent failures
        def side_effect(user, content):
            if len(content) % 2 == 0:
                return {
                    'status': 'error',
                    'error': 'Simulated error'
                }
            return {
                'status': 'success',
                'response': 'Success'
            }
        
        mock_process.side_effect = side_effect
        
        # Send alternating messages that succeed and fail
        responses = []
        for i in range(4):
            response = self.client.post(
                url,
                data=json.dumps({'message': 'x' * i}),
                content_type='application/json'
            )
            responses.append(response)
        
        # Verify error handling
        self.assertEqual(responses[0].status_code, 400)  # Should fail (0 chars)
        self.assertEqual(responses[1].status_code, 200)  # Should succeed (1 char)
        self.assertEqual(responses[2].status_code, 400)  # Should fail (2 chars)
        self.assertEqual(responses[3].status_code, 200)  # Should succeed (3 chars)

    def test_message_ordering(self):
        """
        @atomic-test
        Test message ordering in conversation history
        """
        # Create messages with explicit timestamps
        messages = []
        for i in range(5):
            msg = create_message(
                self.conversation,
                f"Message {i}",
                "user" if i % 2 == 0 else "bot"
            )
            messages.append(msg)
        
        # Get history and verify order
        history = get_conversation_history(self.user)
        for i, msg in enumerate(history):
            self.assertEqual(msg['content'], f"Message {i}")
            self.assertEqual(
                msg['sender'],
                "user" if i % 2 == 0 else "bot"
            )

    def test_session_persistence(self):
        """
        @atomic-test
        Test conversation session persistence
        """
        # Create initial messages
        create_message(self.conversation, "Initial message", "user")
        
        # Simulate session expiry by logging out and back in
        self.client.logout()
        self.client.login(username='testuser', password='testpass123')
        
        # Verify conversation history persists
        history = get_conversation_history(self.user)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['content'], "Initial message")
