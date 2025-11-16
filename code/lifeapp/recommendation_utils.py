from django.conf import settings as dj_settings
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Sum
from .models import NutritionEntry, HealthLog, Recommendation
import random


def generate_recommendations_for_user(user):
    """Generate lightweight, rule-based recommendations for a user based on the
    last 7 days of NutritionEntry and HealthLog data. This function is idempotent
    in the sense that callers may delete previous recommendations before calling it.
    """
    t = getattr(dj_settings, 'RECOMMENDATIONS_THRESHOLDS', {})

    def thr(k, default):
        return t.get(k, default)

    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    recent_nutrition = NutritionEntry.objects.filter(user=user, created_at__gte=seven_days_ago)
    recent_logs = HealthLog.objects.filter(user=user, date__gte=seven_days_ago)

    avg_calories = recent_nutrition.aggregate(avg=Avg('calories'))['avg'] or 0
    avg_protein = recent_nutrition.aggregate(avg=Avg('protein'))['avg'] or 0
    avg_fiber = recent_nutrition.aggregate(avg=Avg('fiber'))['avg'] or 0
    avg_steps = recent_logs.aggregate(avg=Avg('steps'))['avg'] or 0
    avg_sleep = recent_logs.aggregate(avg=Avg('sleep_hours'))['avg'] or 0
    avg_water = recent_nutrition.aggregate(avg=Avg('water'))['avg'] or 0
    avg_carbs = recent_nutrition.aggregate(avg=Avg('carbs'))['avg'] or 0
    avg_fat = recent_nutrition.aggregate(avg=Avg('fat'))['avg'] or 0
    # heart_rate and blood pressure are not used in recommendations for this project

    generated = []

    # Calories
    if avg_calories > thr('calories_high', 2500):
        generated.append(Recommendation(
            user=user,
            category='nutrition',
            priority='medium',
            title='High calorie pattern',
            message=f'Your average daily calories over the past week is {int(avg_calories)} kcal. Consider reducing portion sizes or choosing lower-calorie swaps.'
        ))
    elif avg_calories and avg_calories < thr('calories_low', 1400):
        generated.append(Recommendation(
            user=user,
            category='nutrition',
            priority='medium',
            title='Low calorie intake',
            message=(f'Your average intake ({int(avg_calories)} kcal) is low. Consider adding calorie-dense nutritious foods like nuts, avocado, whole-fat dairy, legumes, and healthy oils to meet your energy needs.')
        ))

    # Protein
    if avg_protein < thr('protein_low', 50):
        generated.append(Recommendation(
            user=user,
            category='nutrition',
            priority='low',
            title='Increase protein',
            message='Protein intake looks low. Add lean protein sources like chicken, fish, eggs, tofu, beans or Greek yogurt to support muscle and fullness.'
        ))
    elif avg_protein and avg_protein > thr('protein_high', 200):
        generated.append(Recommendation(
            user=user,
            category='nutrition',
            priority='low',
            title='Very high protein intake',
            message='Your protein intake appears very high. If you have kidney issues or other conditions, discuss very high-protein diets with your healthcare provider and ensure adequate hydration.'
        ))

    # Fiber
    generated = []

    # To provide varied output each time the user clicks "Regenerate Insights",
    # we use multiple message templates per parameter and pick randomly. We also
    # generate suggestions for all key parameters (calories, protein, carbs,
    # fat, fiber, water, steps, sleep, blood pressure, BMI) so each regenerate
    # produces a fresh set covering the project's parameters.

    # Message template pools per parameter
    templates = {
        'calories_high': [
            'Your average daily calories over the past week is {val} kcal — consider reducing portion sizes or swapping in lower-calorie options like vegetables and lean protein.',
            'You averaged {val} kcal/day recently. Small swaps (e.g., grilled vs fried, more veg) can trim calories without feeling deprived.',
            '{val} kcal/day is above your threshold. Try mindful portion control and higher-volume, lower-calorie foods.'
        ],
        'calories_low': [
            'Your average is {val} kcal/day — a bit low. Add nutrient-dense foods (nuts, avocado, full-fat dairy) to meet energy needs.',
            'At {val} kcal/day, you may benefit from including more calorie-dense healthy options like legumes and nut butters.',
            'Calories are low ({val} kcal/day). Consider adding balanced snacks between meals to keep energy up.'
        ],
        'protein_low': [
            'Protein seems low ({val} g/day). Add portions of eggs, Greek yogurt, legumes or lean meat to help satiety and recovery.',
            'At around {val} g/day protein, aim to include a protein source with each meal—chicken, tofu, fish, or beans work well.',
            'Consider adding 20–30 g of protein to one meal (e.g., a scoop of yogurt + nuts) to lift daily totals from {val} g.'
        ],
        'protein_high': [
            'Protein intake is high ({val} g/day). If you have kidney disease or other conditions, discuss very high-protein diets with your provider and stay hydrated.',
            'At {val} g/day protein, ensure balanced nutrition and adequate fluids — very high protein can stress some conditions.',
            'High protein ({val} g/day) detected; vary protein sources and keep an eye on overall calorie balance.'
        ],
        'fiber_low': [
            'Fiber looks low ({val} g/day). Add fruits, vegetables, legumes and whole grains to support digestion and fullness.',
            'Try adding a serving of fruit and a serving of whole grains to raise fiber from {val} g/day toward recommended levels.',
            'Increase fiber gradually from {val} g/day — beans, oats and veggies are easy wins.'
        ],
        'fiber_high': [
            'Fiber is high ({val} g/day). Spread intake across the day and ensure you drink enough water to reduce bloating.',
            'Very high fiber ({val} g/day) may cause gas — try spacing high-fiber foods and increase fluids.',
        ],
        'carbs_high': [
            'Carbohydrates are elevated ({val} g/day). Swap refined carbs for whole grains, legumes and extra vegetables.',
            'At {val} g/day carbs, choose fiber-rich carbs (brown rice, oats) and reduce sugary snacks to steady energy.'
        ],
        'carbs_low': [
            'Carbs are low ({val} g/day). Include whole grains, starchy vegetables or fruit around activity for fuel.',
            'Low carbs ({val} g/day) — add balanced carbs like potatoes, rice or beans to support workouts and recovery.'
        ],
        'fat_high': [
            'Fat intake is high ({val} g/day). Favor unsaturated fats (olive oil, avocado, nuts) and reduce fried/processed fats.',
            'At {val} g/day fat, choose healthier fats and reduce saturated fats from processed foods.'
        ],
        'fat_low': [
            'Fat is low ({val} g/day). Include sources like olive oil, fatty fish, nuts or avocado to support nutrient absorption.',
            'Having too little fat ({val} g/day) can affect satiety — try adding a small handful of nuts or a drizzle of olive oil.'
        ],
        'water_low': [
            'Average water intake is {val} ml/day. Aim for 1.5–3 L depending on activity — keep a bottle nearby and sip regularly.',
            'Hydration around {val} ml/day — try a glass of water before meals and carry a refillable bottle to increase intake.'
        ],
        'steps_low': [
            'Average daily steps are {val}. Add short walks after meals or a 10–15 minute walk break to increase movement.',
            'Steps around {val} — try breaking activity into small goals (e.g., a 10-minute walk three times daily).' 
        ],
        'sleep_low': [
            'Sleep averages {val} hours — aim for 7–8 hours. Try a consistent bedtime and screen-free wind-down routine.',
            'With {val} hours sleep, prioritize sleep hygiene: dark bedroom, regular schedule and limiting caffeine later in the day.'
        ],
        'bmi_high': [
            'Your BMI is {val}. A modest calorie deficit combined with regular activity can support a gradual weight reduction.',
            'BMI {val} suggests overweight — small, sustainable changes to diet and movement are more effective than drastic measures.'
        ],
        'bmi_low': [
            'BMI {val} is underweight — consider increasing nutrient-dense calories and consult a healthcare professional if concerned.',
        ]
    }

    def pick(tpl_key, **kw):
        pool = templates.get(tpl_key, [])
        if not pool:
            return ''
        return random.choice(pool).format(**kw)

    # Calories
    if avg_calories > thr('calories_high', 2500):
        generated.append(Recommendation(user=user, category='nutrition', priority='medium', title='High calorie pattern', message=pick('calories_high', val=int(avg_calories))))
    else:
        # also include a lower-calorie suggestion when below threshold
        if avg_calories and avg_calories < thr('calories_low', 1400):
            generated.append(Recommendation(user=user, category='nutrition', priority='medium', title='Low calorie intake', message=pick('calories_low', val=int(avg_calories))))
        else:
            # not out of range — still provide a general calorie tip (varying)
            generated.append(Recommendation(user=user, category='nutrition', priority='low', title='Calorie check', message=pick('calories_high', val=int(avg_calories))))

    # Protein
    if avg_protein < thr('protein_low', 50):
        generated.append(Recommendation(user=user, category='nutrition', priority='low', title='Increase protein', message=pick('protein_low', val=int(avg_protein))))
    elif avg_protein and avg_protein > thr('protein_high', 200):
        generated.append(Recommendation(user=user, category='nutrition', priority='low', title='Very high protein intake', message=pick('protein_high', val=int(avg_protein))))
    else:
        generated.append(Recommendation(user=user, category='nutrition', priority='low', title='Protein tip', message=pick('protein_low', val=int(avg_protein))))

    # Fiber
    if avg_fiber < thr('fiber_low', 20):
        generated.append(Recommendation(user=user, category='nutrition', priority='low', title='Add more fiber', message=pick('fiber_low', val=int(avg_fiber))))
    elif avg_fiber and avg_fiber > 70:
        generated.append(Recommendation(user=user, category='nutrition', priority='low', title='Very high fiber intake', message=pick('fiber_high', val=int(avg_fiber))))
    else:
        generated.append(Recommendation(user=user, category='nutrition', priority='low', title='Fiber tip', message=pick('fiber_low', val=int(avg_fiber))))

    # Carbs
    if avg_carbs and avg_carbs > thr('carbs_high', 350):
        generated.append(Recommendation(user=user, category='nutrition', priority='low', title='High carbohydrate intake', message=pick('carbs_high', val=int(avg_carbs))))
    elif avg_carbs and avg_carbs < thr('carbs_low', 130):
        generated.append(Recommendation(user=user, category='nutrition', priority='low', title='Low carbohydrate intake', message=pick('carbs_low', val=int(avg_carbs))))
    else:
        generated.append(Recommendation(user=user, category='nutrition', priority='low', title='Carb tip', message=pick('carbs_high', val=int(avg_carbs))))

    # Fat
    if avg_fat and avg_fat > thr('fat_high', 100):
        generated.append(Recommendation(user=user, category='nutrition', priority='low', title='High fat intake', message=pick('fat_high', val=int(avg_fat))))
    elif avg_fat and avg_fat < thr('fat_low', 20):
        generated.append(Recommendation(user=user, category='nutrition', priority='low', title='Low fat intake', message=pick('fat_low', val=int(avg_fat))))
    else:
        generated.append(Recommendation(user=user, category='nutrition', priority='low', title='Fat tip', message=pick('fat_high', val=int(avg_fat))))

    # Water
    generated.append(Recommendation(user=user, category='nutrition', priority='low', title='Hydration', message=pick('water_low', val=int(avg_water or 0))))

    # Steps
    generated.append(Recommendation(user=user, category='exercise', priority='low', title='Activity', message=pick('steps_low', val=int(avg_steps or 0))))

    # Sleep
    generated.append(Recommendation(user=user, category='sleep', priority='low', title='Sleep', message=pick('sleep_low', val=round(avg_sleep or 0, 1))))

    # Blood pressure removed from recommendations per project settings

    # BMI
    try:
        profile = user.userprofile
        bmi_val = profile.bmi
        if bmi_val is not None:
            if bmi_val >= 25:
                generated.append(Recommendation(user=user, category='nutrition', priority='medium', title='Consider weight management', message=pick('bmi_high', val=bmi_val)))
            elif bmi_val < 18.5:
                generated.append(Recommendation(user=user, category='nutrition', priority='medium', title='Underweight — ensure adequate intake', message=pick('bmi_low', val=bmi_val)))
            else:
                # add a neutral BMI tip to keep variety
                generated.append(Recommendation(user=user, category='lifestyle', priority='low', title='BMI note', message=f'Your BMI is {bmi_val}. Keep up balanced nutrition and activity.'))
    except Exception:
        pass

    # If nothing triggered (shouldn't happen because we always append), add a generic nudge
    if not generated:
        generated.append(Recommendation(
            user=user,
            category='lifestyle',
            priority='low',
            title='Keep it up!',
            message='No major patterns detected — keep logging daily and we will provide personalized suggestions.'
        ))

    # Shuffle to provide changed order each time and limit to a small set
    random.shuffle(generated)
    selected = generated[:3]

    # Bulk create only the selected recommendations (up to 4)
    Recommendation.objects.bulk_create(selected)

    return selected
