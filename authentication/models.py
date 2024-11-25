from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

# Create your models here.

class UserProfile(AbstractUser):
    """
    @atomic-model
    Represents the user's profile data in the database.
    Following atomic function pattern with clear validation and error handling.
    """
    job_title = models.CharField(max_length=255, blank=True)
    experience = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'user_profile'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def clean(self):
        """
        @atomic-validation
        Validates the model's fields following atomic validation pattern
        """
        super().clean()
        if self.experience is not None and self.experience < 0:
            raise ValidationError({'experience': 'Experience cannot be negative.'})

    def save(self, *args, **kwargs):
        """
        @atomic-operation
        Ensures data validation before save
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
