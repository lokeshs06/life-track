from django.contrib import admin
from .models import UserProfile, HealthLog, Recommendation, Goal

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'age', 'bmi', 'bmi_category']
    search_fields = ['user__username']

@admin.register(HealthLog)
class HealthLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'calories_intake', 'steps', 'sleep_hours']
    list_filter = ['date']
    search_fields = ['user__username']

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'priority', 'title', 'is_read', 'created_at']
    list_filter = ['category', 'priority', 'is_read']

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ['user', 'goal_type', 'target_value', 'progress_percentage', 'is_achieved']
    list_filter = ['goal_type', 'is_achieved']