import os
import sys
import random
from datetime import timedelta

# prepare Django
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lifetrack.settings')
import django
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from lifeapp.models import HealthLog

User = get_user_model()

DAYS = 90  # change if you want more/less

u = User.objects.first()
if not u:
    print('No user found. Create a user first.')
    sys.exit(1)

today = timezone.now().date()
created = 0
skipped = 0
for i in range(1, DAYS + 1):
    d = today - timedelta(days=i)
    if HealthLog.objects.filter(user=u, date=d).exists():
        skipped += 1
        continue

    # produce reasonable synthetic values with some variability
    steps = int(max(0, random.gauss(7000, 2500)))
    calories = int(max(1200, random.gauss(2200, 300)))
    protein = round(random.uniform(50, 120), 1)
    carbs = round(random.uniform(150, 350), 1)
    fats = round(random.uniform(40, 100), 1)
    water = round(random.uniform(1.0, 3.0), 2)
    exercise = int(max(0, random.gauss(30, 20)))
    sleep = round(min(12.0, max(0.0, random.gauss(7.0, 1.2))), 2)
    hr = int(max(40, min(180, random.gauss(70, 8))))
    mood = random.choices(['excellent','good','okay','bad','terrible'], weights=[5,20,40,25,10])[0]

    vl = HealthLog(
        user=u,
        date=d,
        calories_intake=calories,
        protein=protein,
        carbs=carbs,
        fats=fats,
        water_intake=water,
        steps=steps,
        exercise_duration=exercise,
        exercise_type='walking' if exercise < 30 else 'running',
        sleep_hours=sleep,
        heart_rate=hr,
        blood_pressure_sys=None,
        blood_pressure_dia=None,
        mood=mood,
        notes='Synthetic generated log for evaluation'
    )
    try:
        vl.save()
        created += 1
    except Exception as e:
        print('Failed to save for date', d, 'error:', e)

print(f'Created {created} logs, skipped {skipped} existing logs for user {u}.')
