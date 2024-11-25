import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Conversation, Message
from django.db import transaction
from django.db.models import Q

User = get_user_model()

def get_or_create_conversation(user: User) -> Conversation:
    """
    @atomic-function
    Get or create an active conversation for a user
    """
    # Try to get existing active conversation
    conversation = Conversation.objects.filter(
        user=user,
        is_active=True
    ).first()
    
    if not conversation:
        # Deactivate all existing conversations
        Conversation.objects.filter(
            user=user
        ).update(is_active=False)
        
        # Create new active conversation
        conversation = Conversation.objects.create(
            user=user,
            is_active=True
        )
    
    return conversation

def sanitize_message(content: str) -> str:
    """
    @atomic-function
    Sanitize message content to prevent XSS attacks
    """
    from django.utils.html import escape
    return escape(content)

def validate_message_size(content: str) -> None:
    """
    @atomic-function
    Validate message size to prevent large message attacks
    """
    MAX_MESSAGE_SIZE = 100000  # 100KB limit
    if len(content.encode('utf-8')) > MAX_MESSAGE_SIZE:
        raise ValidationError("Message too large. Maximum size is 100KB.")

def create_message(conversation: Conversation, content: str, sender: str) -> Message:
    """
    @atomic-function
    Create a new message in a conversation with validation
    """
    validate_message_size(content)
    content = sanitize_message(content)
    message = Message.objects.create(
        conversation=conversation,
        content=content,
        sender=sender
    )
    return message

def create_interview_message(
    conversation: Conversation,
    content: str,
    question_type: str,
    interview_data: Dict[str, Any]
) -> Message:
    """
    @atomic-function
    Create a message containing interview data
    """
    validate_message_size(content)
    sanitized_content = sanitize_message(content)
    
    message = Message.objects.create(
        conversation=conversation,
        content=sanitized_content,
        sender='user',
        is_interview_response=True,
        question_type=question_type,
        interview_data=interview_data
    )
    return message

def process_user_message(user: User, content: str) -> Dict[str, Any]:
    """
    @atomic-function
    Process a user message and return a response
    """
    # Validate and sanitize input
    try:
        validate_message_size(content)
    except ValidationError as e:
        return {
            'status': 'error',
            'error': str(e)
        }
    
    sanitized_content = sanitize_message(content)
    
    # Process message
    conversation = get_or_create_conversation(user)
    message = create_message(conversation, sanitized_content, "user")
    
    # Echo response for now
    response = f"You said: {sanitized_content}"
    create_message(conversation, response, "bot")
    
    return {
        'status': 'success',
        'response': response
    }

def get_conversation_history(user: User, limit: int = 50) -> list[Dict[str, Any]]:
    """
    @atomic-function
    Retrieves conversation history for a user
    
    Args:
        user (User): The user to get history for
        limit (int): Maximum number of messages to return
    
    Returns:
        list[Dict[str, Any]]: List of messages with sender and content
    """
    conversation = get_or_create_conversation(user)
    messages = conversation.messages.all()[:limit]
    
    return [
        {
            'sender': msg.sender,
            'content': msg.content,
            'timestamp': msg.timestamp
        }
        for msg in messages
    ]

def get_interview_responses(user: User, question_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    @atomic-function
    Retrieve interview responses for a user, optionally filtered by question type
    
    Args:
        user (User): The user to get responses for
        question_type (Optional[str]): Filter responses by question type
        
    Returns:
        List[Dict[str, Any]]: List of interview responses with metadata
    """
    # Base query to get all interview responses for the user
    query = Message.objects.filter(
        conversation__user=user,
        is_interview_response=True
    ).select_related('conversation')
    
    # Add question type filter if specified
    if question_type:
        query = query.filter(question_type=question_type)
    
    # Order by timestamp to ensure consistent ordering
    query = query.order_by('timestamp')
    
    # Convert to list of dictionaries with all relevant data
    responses = []
    for message in query:
        response_data = {
            'id': message.id,
            'content': message.content,
            'question_type': message.question_type,
            'conversation_id': message.conversation.id,
            'interview_data': message.interview_data or {},
            'timestamp': message.timestamp.isoformat() if message.timestamp else None,
            'is_from_active_conversation': message.conversation.is_active
        }
        responses.append(response_data)
    
    return responses

def get_next_interview_question(conversation: Conversation) -> Dict[str, Any]:
    """
    @atomic-function
    Get the next interview question based on conversation state
    """
    # Define interview flow structure
    INTERVIEW_QUESTIONS = {
        'introduction': {
            'question': "Hello! I'll be conducting your interview today. Could you start by introducing yourself?",
            'type': 'open_ended',
            'next': 'experience'
        },
        'experience': {
            'question': "How many years of experience do you have in software development?",
            'type': 'numeric',
            'next': 'skills'
        },
        'skills': {
            'question': "What programming languages and technologies are you proficient in?",
            'type': 'multi_select',
            'next': 'role'
        },
        'role': {
            'question': "What was your most recent role and what were your key responsibilities?",
            'type': 'open_ended',
            'next': 'project'
        },
        'project': {
            'question': "Could you describe a challenging project you've worked on?",
            'type': 'open_ended',
            'next': 'problem_solving'
        },
        'problem_solving': {
            'question': "How do you approach complex technical problems?",
            'type': 'open_ended',
            'next': 'team'
        },
        'team': {
            'question': "How do you prefer to work within a team?",
            'type': 'open_ended',
            'next': 'conclusion'
        },
        'conclusion': {
            'question': "Do you have any questions for me?",
            'type': 'open_ended',
            'next': None
        }
    }

    # Get current question type from conversation state
    current_type = conversation.metadata.get('current_question', 'introduction')
    
    # If interview is complete, return None
    if current_type == 'conclusion' and conversation.metadata.get('asked_conclusion', False):
        return None
        
    question_data = INTERVIEW_QUESTIONS[current_type]
    
    return {
        'question': question_data['question'],
        'type': question_data['type'],
        'current_stage': current_type
    }

def process_interview_response(conversation: Conversation, content: str) -> Dict[str, Any]:
    """
    @atomic-function
    Process an interview response and return the next question
    """
    # Ensure metadata exists
    if not conversation.metadata:
        conversation.metadata = {}
    
    current_type = conversation.metadata.get('current_question', 'introduction')
    
    # Store the response
    interview_data = {
        'response_type': current_type,
        'timestamp': datetime.now().isoformat(),
        'original_response': content  # Always store original response
    }
    
    # Additional processing based on question type
    if current_type == 'experience':
        try:
            # Enhanced regex pattern to handle more formats including months
            years_pattern = r'(\d+)\s*(?:years?|yrs?|year|yr)'
            months_pattern = r'(\d+)\s*(?:months?|mos?)'
            
            years = 0
            months = 0
            
            years_match = re.search(years_pattern, content.lower())
            months_match = re.search(months_pattern, content.lower())
            
            if years_match:
                years = int(years_match.group(1))
            if months_match:
                months = int(months_match.group(1))
                years += months / 12
                
            if not years and not months:
                # Fallback to basic digit extraction with context validation
                numbers = [int(n) for n in re.findall(r'\d+', content)]
                years = next((n for n in numbers if 0 < n < 50), None)  # Reasonable range for years
            
            interview_data['years'] = round(years, 1) if years else None
            
            # Extract company names if mentioned
            company_pattern = r'(?:at|with|for)\s+([A-Z][A-Za-z0-9\s&]+(?:Inc\.?|LLC|Ltd\.?|Corporation|Corp\.?|Company|Co\.?)?)'
            companies = re.findall(company_pattern, content)
            if companies:
                interview_data['companies'] = [c.strip() for c in companies]
                
        except (ValueError, AttributeError):
            interview_data['years'] = None
            interview_data['error'] = 'Could not parse experience duration'
            
    elif current_type == 'skills':
        # Improved skill extraction with categorization
        skills_text = re.sub(r'[^\w\s,;]', '', content)  # Remove special chars except delimiters
        raw_skills = [
            s.strip() 
            for s in re.split(r'[,;\s]+', skills_text) 
            if s.strip() and len(s.strip()) > 1  # Filter out single chars
        ]
        
        # Categorize skills
        tech_keywords = {'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node', 'django', 'flask', 
                        'sql', 'mongodb', 'postgres', 'mysql', 'redis', 'aws', 'azure', 'gcp', 'docker', 'kubernetes'}
        soft_skills = {'leadership', 'communication', 'teamwork', 'problem solving', 'analytical', 'agile', 'scrum'}
        
        categorized_skills = {
            'technical': [s for s in raw_skills if s.lower() in tech_keywords],
            'soft_skills': [s for s in raw_skills if s.lower() in soft_skills],
            'other': [s for s in raw_skills if s.lower() not in tech_keywords and s.lower() not in soft_skills]
        }
        
        interview_data['skills'] = categorized_skills
        
    elif current_type == 'role':
        # Extract responsibilities and achievements
        sentences = [s.strip() for s in re.split(r'[.;]', content) if s.strip()]
        
        responsibilities = []
        achievements = []
        
        for sentence in sentences:
            # Look for achievement indicators
            if any(word in sentence.lower() for word in ['achieved', 'improved', 'increased', 'reduced', 'led', 'created', 'developed', 'implemented']):
                achievements.append(sentence.strip())
            # Look for responsibility indicators
            elif any(word in sentence.lower() for word in ['responsible', 'managed', 'handled', 'maintained', 'supported', 'coordinated']):
                responsibilities.append(sentence.strip())
            else:
                responsibilities.append(sentence.strip())  # Default to responsibility
                
        interview_data['responsibilities'] = responsibilities
        interview_data['achievements'] = achievements
        
        # Extract role titles
        role_pattern = r'\b(?:Senior|Lead|Principal|Junior|Software|Full[- ]Stack|Front[- ]End|Back[- ]End|DevOps|Cloud|Data|ML|AI)[\s-]*(?:Engineer|Developer|Architect|Consultant|Manager)\b'
        roles = re.findall(role_pattern, content, re.IGNORECASE)
        if roles:
            interview_data['roles'] = [r.strip() for r in roles]
            
    elif current_type == 'project':
        # Extract project details
        sentences = [s.strip() for s in re.split(r'[.;]', content) if s.strip()]
        
        project_data = {
            'challenges': [],
            'solutions': [],
            'technologies': [],
            'outcomes': []
        }
        
        for sentence in sentences:
            lower_sentence = sentence.lower()
            # Identify challenges
            if any(word in lower_sentence for word in ['challenge', 'problem', 'issue', 'difficult']):
                project_data['challenges'].append(sentence)
            # Identify solutions
            elif any(word in lower_sentence for word in ['solve', 'solution', 'implement', 'develop']):
                project_data['solutions'].append(sentence)
            # Identify outcomes
            elif any(word in lower_sentence for word in ['result', 'outcome', 'improve', 'increase', 'reduce']):
                project_data['outcomes'].append(sentence)
                
        # Extract technologies mentioned
        tech_pattern = r'\b(?:Python|Java|JavaScript|React|Angular|Vue|Node|Django|Flask|SQL|MongoDB|Postgres|MySQL|Redis|AWS|Azure|GCP|Docker|Kubernetes|API|REST|GraphQL)[.js]*\b'
        technologies = re.findall(tech_pattern, content, re.IGNORECASE)
        if technologies:
            project_data['technologies'] = [t.strip() for t in technologies]
            
        interview_data['project_details'] = project_data
        
    elif current_type == 'problem_solving':
        # Extract problem-solving approach
        sentences = [s.strip() for s in re.split(r'[.;]', content) if s.strip()]
        
        approach_data = {
            'analysis': [],
            'methodology': [],
            'tools': [],
            'collaboration': []
        }
        
        for sentence in sentences:
            lower_sentence = sentence.lower()
            # Identify analysis approach
            if any(word in lower_sentence for word in ['analyze', 'understand', 'research', 'investigate']):
                approach_data['analysis'].append(sentence)
            # Identify methodology
            elif any(word in lower_sentence for word in ['method', 'approach', 'process', 'step']):
                approach_data['methodology'].append(sentence)
            # Identify tools
            elif any(word in lower_sentence for word in ['tool', 'use', 'utilize', 'implement']):
                approach_data['tools'].append(sentence)
            # Identify collaboration
            elif any(word in lower_sentence for word in ['team', 'collaborate', 'communicate', 'work with']):
                approach_data['collaboration'].append(sentence)
                
        interview_data['problem_solving_approach'] = approach_data
    
    # Create the message with interview data
    with transaction.atomic():
        # Save the message
        message = create_interview_message(
            conversation=conversation,
            content=content,
            question_type=current_type,
            interview_data=interview_data
        )
        
        # Update conversation state
        if current_type == 'introduction':
            conversation.metadata['current_question'] = 'experience'
        elif current_type == 'experience':
            conversation.metadata['current_question'] = 'skills'
        elif current_type == 'skills':
            conversation.metadata['current_question'] = 'role'
        elif current_type == 'role':
            conversation.metadata['current_question'] = 'project'
        elif current_type == 'project':
            conversation.metadata['current_question'] = 'problem_solving'
        elif current_type == 'problem_solving':
            conversation.metadata['current_question'] = 'team'
        elif current_type == 'team':
            conversation.metadata['current_question'] = 'conclusion'
        elif current_type == 'conclusion':
            conversation.metadata['interview_complete'] = True
            conversation.metadata['asked_conclusion'] = True
            
        conversation.save()
        
        # Get next question after state update
        next_question = get_next_interview_question(conversation)
        conversation.refresh_from_db()  # Refresh to get latest state
    
    if next_question:
        return {
            'status': 'continue',
            'next_question': next_question,
            'message_id': message.id,
            'processed_data': interview_data
        }
    else:
        return {
            'status': 'complete',
            'message': "Thank you for completing the interview!",
            'message_id': message.id,
            'processed_data': interview_data
        }
