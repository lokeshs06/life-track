from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(150)])
    height = models.FloatField(help_text="Height in cm", validators=[MinValueValidator(50)])
    weight = models.FloatField(help_text="Weight in kg", validators=[MinValueValidator(20)])
    target_weight = models.FloatField(help_text="Target weight in kg", validators=[MinValueValidator(20)], null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    activity_level = models.CharField(
        max_length=20,
        choices=[
            ('sedentary', 'Sedentary'),
            ('light', 'Lightly Active'),
            ('moderate', 'Moderately Active'),
            ('very', 'Very Active'),
            ('extra', 'Extra Active')
        ],
        default='moderate'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @property
    def bmi(self):
        height_m = self.height / 100
        return round(self.weight / (height_m ** 2), 2)
    
    @property
    def bmi_category(self):
        bmi = self.bmi
        if bmi < 18.5:
            return "Underweight"
        elif bmi < 25:
            return "Normal"
        elif bmi < 30:
            return "Overweight"
        else:
            return "Obese"

class HealthLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='health_logs')
    date = models.DateField(default=timezone.now)
    
    # Nutrition
    calories_intake = models.IntegerField(validators=[MinValueValidator(0)])
    protein = models.FloatField(validators=[MinValueValidator(0)], help_text="Grams")
    carbs = models.FloatField(validators=[MinValueValidator(0)], help_text="Grams")
    fats = models.FloatField(validators=[MinValueValidator(0)], help_text="Grams")
    water_intake = models.FloatField(validators=[MinValueValidator(0)], help_text="Liters")
    
    # Activity
    steps = models.IntegerField(validators=[MinValueValidator(0)])
    exercise_duration = models.IntegerField(validators=[MinValueValidator(0)], help_text="Minutes")
    exercise_type = models.CharField(max_length=100, blank=True)
    
    # Sleep & Vitals
    sleep_hours = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(24)])
    heart_rate = models.IntegerField(validators=[MinValueValidator(30), MaxValueValidator(220)], null=True, blank=True)
    blood_pressure_sys = models.IntegerField(null=True, blank=True, help_text="Systolic")
    blood_pressure_dia = models.IntegerField(null=True, blank=True, help_text="Diastolic")
    
    # Additional
    mood = models.CharField(
        max_length=20,
        choices=[
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('okay', 'Okay'),
            ('bad', 'Bad'),
            ('terrible', 'Terrible')
        ],
        default='okay'
    )
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"

class Recommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    category = models.CharField(
        max_length=20,
        choices=[
            ('nutrition', 'Nutrition'),
            ('exercise', 'Exercise'),
            ('sleep', 'Sleep'),
            ('lifestyle', 'Lifestyle')
        ]
    )
    priority = models.CharField(
        max_length=10,
        choices=[
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low')
        ]
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.category} - {self.title}"

class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    goal_type = models.CharField(
        max_length=20,
        choices=[
            ('weight', 'Weight Loss/Gain'),
            ('steps', 'Daily Steps'),
            ('exercise', 'Exercise Duration'),
            ('sleep', 'Sleep Hours'),
            ('water', 'Water Intake')
        ]
    )
    target_value = models.FloatField()
    current_value = models.FloatField(default=0)
    deadline = models.DateField()
    is_achieved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.goal_type} Goal"
    
    @property
    def progress_percentage(self):
        if self.target_value == 0:
            return 0
        return min(round((self.current_value / self.target_value) * 100, 1), 100)

class NutritionEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nutrition_entries')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Meal details
    meal_type = models.CharField(
        max_length=20,
        choices=[
            ('breakfast', 'Breakfast'),
            ('lunch', 'Lunch'),
            ('dinner', 'Dinner'),
            ('snack', 'Snack')
        ]
    )
    
    # Core metrics
    calories = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    water = models.PositiveIntegerField(help_text="Water intake in ml", validators=[MinValueValidator(0)])
    
    # Macronutrients (in grams)
    protein = models.FloatField(validators=[MinValueValidator(0)], default=0)
    carbs = models.FloatField(validators=[MinValueValidator(0)], default=0)
    fat = models.FloatField(validators=[MinValueValidator(0)], default=0)
    fiber = models.FloatField(validators=[MinValueValidator(0)], default=0)
    
    # Additional info
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.username}'s {self.meal_type} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"