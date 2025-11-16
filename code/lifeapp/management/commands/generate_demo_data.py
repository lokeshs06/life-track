from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random

from lifeapp.models import UserProfile, HealthLog

class Command(BaseCommand):
    help = 'Generate demo health logs for a user (username). Creates user/profile if missing.'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to create or use')
        parser.add_argument('--days', type=int, default=60, help='Number of days to generate')

    def handle(self, *args, **options):
        username = options['username']
        days = options['days']

        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password('password')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user {username} with password "password"'))

        # Ensure profile
        if not hasattr(user, 'userprofile'):
            profile = UserProfile.objects.create(
                user=user,
                age=random.randint(20,50),
                height=random.uniform(150,190),
                weight=random.uniform(60,90),
                gender=random.choice(['male','female','other']),
                activity_level=random.choice(['sedentary','light','moderate','very','extra'])
            )
            self.stdout.write(self.style.SUCCESS(f'Created profile for {username}'))

        today = timezone.now().date()
        for i in range(days):
            date = today - timedelta(days=i)
            # random but somewhat correlated time series
            calories = int(random.gauss(2200, 250) - (i * 0.5))
            steps = max(1000, int(random.gauss(7000, 2000)))
            sleep = round(max(3, random.gauss(7, 1)),1)
            water = round(random.uniform(1.5,3.0),2)
            protein = round(random.uniform(50,120),1)
            carbs = round(random.uniform(150,300),1)
            fats = round(random.uniform(40,100),1)
            exercise_dur = max(0,int(random.gauss(30,20)))
            exercise_type = random.choice(['Walking','Running','Yoga','Gym','Cycling',''])
            mood = random.choice(['excellent','good','okay','bad','terrible'])
            notes = ''

            # Avoid unique_together conflicts by updating if present
            log, created = HealthLog.objects.update_or_create(
                user=user, date=date,
                defaults={
                    'calories_intake': calories,
                    'protein': protein,
                    'carbs': carbs,
                    'fats': fats,
                    'water_intake': water,
                    'steps': steps,
                    'exercise_duration': exercise_dur,
                    'exercise_type': exercise_type,
                    'sleep_hours': sleep,
                    'heart_rate': None,
                    'blood_pressure_sys': None,
                    'blood_pressure_dia': None,
                    'mood': mood,
                    'notes': notes
                }
            )
        self.stdout.write(self.style.SUCCESS(f'Generated {days} days of logs for {username}'))
