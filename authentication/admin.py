from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UserProfile

# Register your models here.

@admin.register(UserProfile)
class UserProfileAdmin(UserAdmin):
    """
    @atomic-admin
    Admin configuration for UserProfile model following atomic pattern
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'job_title', 'experience')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'job_title')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'job_title', 'experience')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
