from django.test import TestCase
from django.contrib.auth import get_user_model
from chat.models import Conversation
from chat.services import (
    get_next_interview_question,
    process_interview_response,
    get_interview_responses
)

User = get_user_model()

class InterviewFlowTestCase(TestCase):
    """
    @atomic-test-suite
    Test suite for interview flow functionality
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.conversation = Conversation.objects.create(
            user=self.user,
            metadata={'current_question': 'introduction'}
        )

    def test_interview_flow(self):
        """
        @atomic-test
        Test complete interview flow from start to finish
        """
        # Start interview
        question = get_next_interview_question(self.conversation)
        self.assertEqual(question['current_stage'], 'introduction')
        
        # Test introduction response
        response = process_interview_response(
            self.conversation,
            "Hi, I'm John Doe, a software developer."
        )
        self.assertEqual(response['status'], 'continue')
        self.assertEqual(response['next_question']['current_stage'], 'experience')
        
        # Test experience response
        response = process_interview_response(
            self.conversation,
            "I have 5 years of experience"
        )
        self.assertEqual(response['status'], 'continue')
        responses = get_interview_responses(self.user, 'experience')
        self.assertEqual(responses[0]['interview_data']['years'], 5)
        
        # Test skills response
        response = process_interview_response(
            self.conversation,
            "Python, Django, React, JavaScript"
        )
        self.assertEqual(response['status'], 'continue')
        responses = get_interview_responses(self.user, 'skills')
        self.assertEqual(len(responses[0]['interview_data']['skills']), 4)
        
        # Complete remaining questions
        questions = ['role', 'project', 'problem_solving', 'team']
        for _ in questions:
            response = process_interview_response(
                self.conversation,
                "Test response for " + _
            )
            self.assertEqual(response['status'], 'continue')
        
        # Test conclusion
        response = process_interview_response(
            self.conversation,
            "No questions, thank you!"
        )
        self.assertEqual(response['status'], 'complete')
        
        # Verify interview is complete
        question = get_next_interview_question(self.conversation)
        self.assertIsNone(question)

    def test_question_sequence(self):
        """
        @atomic-test
        Test that questions follow the correct sequence
        """
        expected_sequence = [
            'introduction',
            'experience',
            'skills',
            'role',
            'project',
            'problem_solving',
            'team',
            'conclusion'
        ]
        
        current_question = get_next_interview_question(self.conversation)
        sequence = [current_question['current_stage']]
        
        while current_question and len(sequence) < len(expected_sequence):
            response = process_interview_response(
                self.conversation,
                f"Test response for {current_question['current_stage']}"
            )
            if response['status'] == 'continue':
                current_question = response['next_question']
                sequence.append(current_question['current_stage'])
            else:
                break
        
        self.assertEqual(sequence, expected_sequence)

    def test_invalid_responses(self):
        """
        @atomic-test
        Test handling of invalid responses
        """
        # Test non-numeric experience response
        self.conversation.metadata['current_question'] = 'experience'
        self.conversation.save()
        
        response = process_interview_response(
            self.conversation,
            "I have some experience"  # Non-numeric
        )
        responses = get_interview_responses(self.user, 'experience')
        self.assertIsNone(responses[0]['interview_data']['years'])
        
        # Test empty skills response
        self.conversation.metadata['current_question'] = 'skills'
        self.conversation.save()
        
        response = process_interview_response(
            self.conversation,
            ""  # Empty response
        )
        responses = get_interview_responses(self.user, 'skills')
        self.assertEqual(len(responses[0]['interview_data']['skills']), 0)
