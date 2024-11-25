from django.test import TestCase
from django.contrib.auth import get_user_model
from chat.models import Conversation, Message
from chat.services import (
    create_interview_message,
    get_interview_responses,
    get_or_create_conversation
)
from datetime import datetime

User = get_user_model()

class InterviewDataTestCase(TestCase):
    """
    @atomic-test-suite
    Test suite for interview data functionality
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.conversation = get_or_create_conversation(self.user)

    def test_create_interview_message(self):
        """
        @atomic-test
        Test creation of interview messages
        """
        # Test basic interview response
        interview_data = {
            'years_experience': 5,
            'skills': ['Python', 'Django', 'React'],
            'current_role': 'Senior Developer'
        }
        
        message = create_interview_message(
            self.conversation,
            "I have 5 years of experience",
            'experience',
            interview_data
        )
        
        # Verify message was created correctly
        self.assertTrue(message.is_interview_response)
        self.assertEqual(message.question_type, 'experience')
        self.assertEqual(message.interview_data['years_experience'], 5)
        self.assertEqual(len(message.interview_data['skills']), 3)

    def test_multiple_interview_responses(self):
        """
        @atomic-test
        Test handling multiple interview responses
        """
        # Create multiple responses
        responses = [
            {
                'content': "I'm a senior developer",
                'type': 'role',
                'data': {'role': 'senior', 'level': 'expert'}
            },
            {
                'content': "I know Python and Django",
                'type': 'skills',
                'data': {'languages': ['Python'], 'frameworks': ['Django']}
            },
            {
                'content': "5 years experience",
                'type': 'experience',
                'data': {'years': 5, 'domains': ['web', 'backend']}
            }
        ]
        
        for resp in responses:
            create_interview_message(
                self.conversation,
                resp['content'],
                resp['type'],
                resp['data']
            )
        
        # Test retrieving all responses
        all_responses = get_interview_responses(self.user)
        self.assertEqual(len(all_responses), 3)
        
        # Test filtering by type
        skill_responses = get_interview_responses(self.user, 'skills')
        self.assertEqual(len(skill_responses), 1)
        self.assertEqual(skill_responses[0]['question_type'], 'skills')

    def test_interview_data_validation(self):
        """
        @atomic-test
        Test validation of interview data
        """
        # Test with invalid JSON data
        with self.assertRaises(TypeError):
            create_interview_message(
                self.conversation,
                "Test message",
                'test',
                "invalid json"  # Should be a dict
            )
        
        # Test with empty data
        message = create_interview_message(
            self.conversation,
            "Test message",
            'test',
            {}
        )
        self.assertEqual(message.interview_data, {})

    def test_interview_response_ordering(self):
        """
        @atomic-test
        Test ordering of interview responses
        """
        # Create responses in specific order
        responses = ['first', 'second', 'third']
        for i, content in enumerate(responses):
            create_interview_message(
                self.conversation,
                content,
                f'type_{i}',
                {'order': i}
            )
        
        # Verify order is maintained
        saved_responses = get_interview_responses(self.user)
        for i, response in enumerate(saved_responses):
            self.assertEqual(response['content'], responses[i])
            self.assertEqual(response['interview_data']['order'], i)

    def test_interview_data_types(self):
        """
        @atomic-test
        Test handling of different data types in interview responses
        """
        complex_data = {
            'string': 'test',
            'integer': 42,
            'float': 3.14,
            'boolean': True,
            'list': [1, 2, 3],
            'nested': {
                'key': 'value',
                'array': ['a', 'b', 'c']
            }
        }
        
        message = create_interview_message(
            self.conversation,
            "Complex data test",
            'complex',
            complex_data
        )
        
        # Verify all data types are preserved
        saved_data = message.interview_data
        self.assertEqual(saved_data['string'], 'test')
        self.assertEqual(saved_data['integer'], 42)
        self.assertEqual(saved_data['float'], 3.14)
        self.assertTrue(saved_data['boolean'])
        self.assertEqual(len(saved_data['list']), 3)
        self.assertEqual(saved_data['nested']['key'], 'value')
        self.assertEqual(len(saved_data['nested']['array']), 3)
