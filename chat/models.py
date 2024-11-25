from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import JSONField

class Conversation(models.Model):
    """
    @atomic-model
    Represents a chat conversation
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    metadata = JSONField(default=dict)

    def save(self, *args, **kwargs):
        # Ensure only one active conversation per user
        if self.is_active:
            Conversation.objects.filter(
                user=self.user,
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Conversation with {self.user.username} ({self.created_at})"

class Message(models.Model):
    """
    @atomic-model
    Represents a message in a conversation
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    content = models.TextField()
    sender = models.CharField(max_length=50)  # 'user' or 'bot'
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Interview specific fields
    is_interview_response = models.BooleanField(default=False)
    question_type = models.CharField(max_length=50, null=True, blank=True)
    interview_data = JSONField(default=dict, null=True, blank=True)

    def clean(self):
        """
        @atomic-validation
        Validates message content
        """
        super().clean()
        if not self.content or not self.content.strip():
            raise ValidationError({'content': 'Message content cannot be empty.'})

    def save(self, *args, **kwargs):
        # Update conversation timestamp
        self.conversation.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sender}: {self.content[:50]}..."

    class Meta:
        ordering = ['timestamp']
