from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from chat.models import Conversation, Message
from chat.services import (
    get_or_create_conversation,
    create_message,
    process_user_message,
    get_conversation_history
)
from unittest.mock import patch

User = get_user_model()

class ChatServicesTestCase(TestCase):
    """
    @atomic-test-suite
    Test suite for chat atomic services
    """
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

    def test_get_or_create_conversation(self):
        """
        @atomic-test
        Test conversation creation and retrieval
        """
        # Test creation
        conversation = get_or_create_conversation(self.user)
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation.user, self.user)
        self.assertTrue(conversation.is_active)
        
        # Test retrieval of existing conversation
        same_conversation = get_or_create_conversation(self.user)
        self.assertEqual(conversation, same_conversation)
        
        # Test creation with inactive conversation
        conversation.is_active = False
        conversation.save()
        new_conversation = get_or_create_conversation(self.user)
        self.assertNotEqual(conversation, new_conversation)
        self.assertTrue(new_conversation.is_active)

    def test_create_message(self):
        """
        @atomic-test
        Test message creation with validation
        """
        conversation = get_or_create_conversation(self.user)
        
        # Test valid message creation
        message = create_message(conversation, "Hello", "user")
        self.assertEqual(message.conversation, conversation)
        self.assertEqual(message.content, "Hello")
        self.assertEqual(message.sender, "user")
        
        # Test empty message
        with self.assertRaises(ValidationError):
            create_message(conversation, "", "user")
        
        # Test whitespace-only message
        with self.assertRaises(ValidationError):
            create_message(conversation, "   ", "user")
        
        # Test invalid sender
        with self.assertRaises(ValidationError):
            create_message(conversation, "Hello", "invalid_sender")

    @patch('chat.services.create_message')
    def test_process_user_message(self, mock_create_message):
        """
        @atomic-test
        Test user message processing with mocks
        """
        # Mock create_message to return a message object
        mock_message = Message(content="Mocked response")
        mock_create_message.return_value = mock_message
        
        # Test successful processing
        result = process_user_message(self.user, "Hello")
        self.assertEqual(result['status'], 'success')
        self.assertTrue('response' in result)
        
        # Verify create_message was called twice (user message and bot response)
        self.assertEqual(mock_create_message.call_count, 2)
        
        # Test with validation error
        mock_create_message.side_effect = ValidationError("Test error")
        result = process_user_message(self.user, "")
        self.assertEqual(result['status'], 'error')
        self.assertTrue('error' in result)

    def test_get_conversation_history(self):
        """
        @atomic-test
        Test conversation history retrieval
        """
        conversation = get_or_create_conversation(self.user)
        
        # Create test messages
        messages = [
            create_message(conversation, f"Message {i}", "user" if i % 2 == 0 else "bot")
            for i in range(5)
        ]
        
        # Test default limit
        history = get_conversation_history(self.user)
        self.assertEqual(len(history), 5)
        
        # Test custom limit
        history = get_conversation_history(self.user, limit=3)
        self.assertEqual(len(history), 3)
        
        # Verify message order (should be chronological)
        self.assertEqual(history[0]['content'], "Message 0")
        self.assertEqual(history[1]['content'], "Message 1")
        self.assertEqual(history[2]['content'], "Message 2")
        
        # Verify message structure
        message = history[0]
        self.assertIn('sender', message)
        self.assertIn('content', message)
        self.assertIn('timestamp', message)

    def test_conversation_isolation(self):
        """
        @atomic-test
        Test that conversations are isolated between users
        """
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123',
            email='other@example.com'
        )
        
        # Create conversations and messages for both users
        conv1 = get_or_create_conversation(self.user)
        create_message(conv1, "User 1 message", "user")
        
        conv2 = get_or_create_conversation(other_user)
        create_message(conv2, "User 2 message", "user")
        
        # Verify each user only sees their own messages
        history1 = get_conversation_history(self.user)
        history2 = get_conversation_history(other_user)
        
        self.assertEqual(len(history1), 1)
        self.assertEqual(len(history2), 1)
        self.assertEqual(history1[0]['content'], "User 1 message")
        self.assertEqual(history2[0]['content'], "User 2 message")
