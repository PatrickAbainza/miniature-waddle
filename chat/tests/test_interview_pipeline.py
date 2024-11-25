from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from chat.models import Conversation, Message
from chat.services import (
    get_or_create_conversation,
    get_next_interview_question,
    process_interview_response,
    get_interview_responses,
    create_interview_message
)
from datetime import datetime
import json

User = get_user_model()

class InterviewPipelineTestCase(TransactionTestCase):
    """
    @atomic-test-suite
    End-to-end pipeline test for interview functionality
    Tests the complete interview flow with concurrent access and transaction handling
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.conversation = get_or_create_conversation(self.user)

    def test_interview_pipeline(self):
        """
        @atomic-test
        Test complete interview pipeline including data persistence and state transitions
        """
        # Stage 1: Interview Setup and Initial State
        self.assertEqual(
            self.conversation.metadata.get('current_question', 'introduction'),
            'introduction'
        )

        # Stage 2: Introduction Phase
        intro_question = get_next_interview_question(self.conversation)
        self.assertEqual(intro_question['type'], 'open_ended')
        
        intro_response = process_interview_response(
            self.conversation,
            "Hi, I'm Jane Doe, a senior software engineer with expertise in Django and React."
        )
        self.verify_response_persistence('introduction')

        # Stage 3: Experience Phase
        exp_response = process_interview_response(
            self.conversation,
            "I have 8 years of experience in software development"
        )
        self.verify_response_persistence('experience')
        responses = get_interview_responses(self.user, 'experience')
        self.assertEqual(responses[0]['interview_data']['years'], 8)

        # Stage 4: Skills Phase with Detailed Validation
        skills_response = process_interview_response(
            self.conversation,
            "Python, Django, React, JavaScript, AWS, Docker"
        )
        self.verify_response_persistence('skills')
        responses = get_interview_responses(self.user, 'skills')
        skills_data = responses[0]['interview_data']['skills']
        
        # Check if required skills are in any category
        all_skills = (
            skills_data.get('technical', []) + 
            skills_data.get('soft_skills', []) + 
            skills_data.get('other', [])
        )
        all_skills = [s.lower() for s in all_skills]
        required_skills = ['python', 'django', 'react']
        self.assertTrue(
            all(skill.lower() in all_skills for skill in required_skills),
            f"Not all required skills {required_skills} found in {all_skills}"
        )

        # Stage 5: Role Description with Transaction Test
        try:
            with transaction.atomic():
                role_response = process_interview_response(
                    self.conversation,
                    "Led a team of 5 developers, architected microservices"
                )
                # Simulate concurrent update
                other_conversation = Conversation.objects.get(id=self.conversation.id)
                other_conversation.metadata['current_question'] = 'different_stage'
                other_conversation.save()
        except Exception:
            self.fail("Transaction handling failed")
        
        self.verify_response_persistence('role')

        # Stage 6: Project Experience with Large Data
        project_desc = """
        Led the development of a high-scale e-commerce platform:
        - Implemented microservices architecture
        - Managed cloud infrastructure on AWS
        - Improved system performance by 40%
        - Integrated payment processing systems
        - Implemented CI/CD pipeline
        """
        project_response = process_interview_response(
            self.conversation,
            project_desc
        )
        self.verify_response_persistence('project')

        # Stage 7: Problem Solving Approach
        problem_response = process_interview_response(
            self.conversation,
            "I approach problems systematically: analyze, break down, plan, implement, test"
        )
        self.verify_response_persistence('problem_solving')

        # Stage 8: Team Collaboration
        team_response = process_interview_response(
            self.conversation,
            "I believe in open communication, knowledge sharing, and mentoring"
        )
        self.verify_response_persistence('team')

        # Stage 9: Conclusion and Final State
        conclusion_response = process_interview_response(
            self.conversation,
            "What are the next steps in the interview process?"
        )
        self.verify_response_persistence('conclusion')

        # Stage 10: Verify Complete Interview Data
        all_responses = get_interview_responses(self.user)
        self.assertEqual(len(all_responses), 8)  # All stages completed
        
        # Verify interview completion
        final_question = get_next_interview_question(self.conversation)
        self.assertIsNone(final_question)

    def verify_response_persistence(self, stage: str):
        """Helper method to verify response data persistence"""
        responses = get_interview_responses(self.user, stage)
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0]['question_type'], stage)
        self.assertIn('timestamp', responses[0]['interview_data'])

    def test_concurrent_interview_sessions(self):
        """
        @atomic-test
        Test handling of concurrent interview sessions
        """
        # Create two conversations for the same user
        conversation2 = Conversation.objects.create(
            user=self.user,
            metadata={'current_question': 'introduction'}
        )

        # Process responses in alternating order
        stages = ['introduction', 'experience']
        for stage in stages:
            # Process in first conversation
            response1 = process_interview_response(
                self.conversation,
                f"Response 1 for {stage}"
            )
            # Process in second conversation
            response2 = process_interview_response(
                conversation2,
                f"Response 2 for {stage}"
            )

        # Verify responses are correctly associated
        for stage in stages:
            responses = get_interview_responses(self.user, stage)
            self.assertEqual(len(responses), 2)
            contents = [r['content'] for r in responses]
            self.assertIn(f"Response 1 for {stage}", contents)
            self.assertIn(f"Response 2 for {stage}", contents)

    def test_interview_data_integrity(self):
        """
        @atomic-test
        Test data integrity throughout the interview process
        """
        test_data = {
            'experience': "10 years of experience",
            'skills': "Python, Django, React",
            'role': "Senior Developer",
        }

        for stage, content in test_data.items():
            # Set stage
            self.conversation.metadata['current_question'] = stage
            self.conversation.save()

            # Process response
            response = process_interview_response(
                self.conversation,
                content
            )

            # Verify immediate persistence
            messages = Message.objects.filter(
                conversation=self.conversation,
                question_type=stage
            )
            self.assertEqual(messages.count(), 1)
            
            # Verify data structure
            message = messages.first()
            self.assertTrue(isinstance(message.interview_data, dict))
            self.assertIn('timestamp', message.interview_data)
            self.assertIn('response_type', message.interview_data)

            # Verify special field handling
            if stage == 'experience':
                self.assertEqual(message.interview_data.get('years'), 10)
            elif stage == 'skills':
                self.assertEqual(len(message.interview_data.get('skills', [])), 3)
