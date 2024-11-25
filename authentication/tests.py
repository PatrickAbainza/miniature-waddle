from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import UserProfile
from .services import (
    validate_user_credentials,
    authenticate_user,
    create_user_profile,
    update_user_profile
)

class UserProfileTests(TestCase):
    """
    @atomic-test-suite
    Test suite for UserProfile atomic functions
    """
    def setUp(self):
        self.test_user = UserProfile.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

    def test_validate_user_credentials(self):
        """
        @atomic-test
        Test user credentials validation
        """
        # Test valid credentials
        result = validate_user_credentials('testuser', 'password')
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)

        # Test invalid credentials
        result = validate_user_credentials('', '')
        self.assertFalse(result['is_valid'])
        self.assertIn('username', result['errors'])
        self.assertIn('password', result['errors'])

    def test_authenticate_user(self):
        """
        @atomic-test
        Test user authentication
        """
        # Test valid authentication
        user = authenticate_user('testuser', 'testpass123')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testuser')

        # Test invalid authentication
        with self.assertRaises(ValidationError):
            authenticate_user('', '')

    def test_create_user_profile(self):
        """
        @atomic-test
        Test user profile creation
        """
        user = create_user_profile(
            username='newuser',
            password='newpass123',
            email='new@example.com',
            job_title='Developer',
            experience=5
        )
        
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(user.job_title, 'Developer')
        self.assertEqual(user.experience, 5)

    def test_update_user_profile(self):
        """
        @atomic-test
        Test user profile update
        """
        # Test valid update
        updated_user = update_user_profile(
            self.test_user,
            job_title='Senior Developer',
            experience=7
        )
        
        self.assertEqual(updated_user.job_title, 'Senior Developer')
        self.assertEqual(updated_user.experience, 7)

        # Test invalid field update
        with self.assertRaises(ValidationError):
            update_user_profile(
                self.test_user,
                invalid_field='value'
            )
