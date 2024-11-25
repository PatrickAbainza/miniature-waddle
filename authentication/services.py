from typing import Optional, Dict, Any
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from .models import UserProfile

def validate_user_credentials(username: str, password: str) -> Dict[str, Any]:
    """
    @atomic-function
    Validates user credentials and returns validation result
    
    Args:
        username (str): The username to validate
        password (str): The password to validate
    
    Returns:
        Dict[str, Any]: Dictionary containing validation status and errors if any
    """
    errors = {}
    
    if not username:
        errors['username'] = 'Username is required'
    if not password:
        errors['password'] = 'Password is required'
        
    return {
        'is_valid': len(errors) == 0,
        'errors': errors
    }

def authenticate_user(username: str, password: str) -> Optional[UserProfile]:
    """
    @atomic-function
    Authenticates a user with provided credentials
    
    Args:
        username (str): The username to authenticate
        password (str): The password to authenticate
    
    Returns:
        Optional[UserProfile]: Authenticated user if successful, None otherwise
    """
    validation = validate_user_credentials(username, password)
    if not validation['is_valid']:
        raise ValidationError(validation['errors'])
        
    return authenticate(username=username, password=password)

def create_user_profile(
    username: str,
    password: str,
    email: str,
    first_name: str = '',
    last_name: str = '',
    job_title: str = '',
    experience: Optional[int] = None
) -> UserProfile:
    """
    @atomic-function
    Creates a new user profile with provided information
    
    Args:
        username (str): Username for the new user
        password (str): Password for the new user
        email (str): Email address for the new user
        first_name (str, optional): User's first name
        last_name (str, optional): User's last name
        job_title (str, optional): User's job title
        experience (Optional[int], optional): User's years of experience
    
    Returns:
        UserProfile: Created user profile instance
    """
    user = UserProfile(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        job_title=job_title,
        experience=experience
    )
    user.set_password(password)
    user.full_clean()
    user.save()
    
    return user

def update_user_profile(
    user: UserProfile,
    **fields_to_update: Dict[str, Any]
) -> UserProfile:
    """
    @atomic-function
    Updates specified fields of a user profile
    
    Args:
        user (UserProfile): User profile to update
        **fields_to_update: Dictionary of fields to update with their new values
    
    Returns:
        UserProfile: Updated user profile instance
    """
    allowed_fields = {
        'first_name', 'last_name', 'email',
        'job_title', 'experience'
    }
    
    invalid_fields = set(fields_to_update.keys()) - allowed_fields
    if invalid_fields:
        raise ValidationError(f'Invalid fields for update: {invalid_fields}')
        
    for field, value in fields_to_update.items():
        setattr(user, field, value)
        
    user.full_clean()
    user.save()
    
    return user
