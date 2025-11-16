from datetime import timedelta
from django.utils import timezone
from .models import HealthLog

def predict_metric(user, metric_field, past_days=30, predict_days=7):
    """Train a simple linear regression on the last `past_days` of `metric_field` and predict next `predict_days`.

    Returns None if not enough data or if sklearn not available. Otherwise returns a dict:
    { 'dates': [date1,...], 'values': [v1,...] }
    """
    try:
        from sklearn.linear_model import LinearRegression
        import numpy as np
    except Exception:
        # sklearn/numpy not available
        return None

    today = timezone.now().date()
    start = today - timedelta(days=past_days)
    logs = HealthLog.objects.filter(user=user, date__gte=start).order_by('date')
    # collect (day_index, value)
    xs = []
    ys = []
    for i, log in enumerate(logs):
        val = getattr(log, metric_field, None)
        if val is None:
            continue
        try:
            v = float(val)
        except Exception:
            continue
        xs.append([i])
        ys.append(v)

    if len(ys) < 3:
        # not enough data to train a model
        return None

    X = np.array(xs)
    y = np.array(ys)

    model = LinearRegression()
    model.fit(X, y)

    last_index = X[-1][0]
    pred_indices = np.array([[last_index + i + 1] for i in range(predict_days)])
    preds = model.predict(pred_indices)

    pred_dates = [ (today + timedelta(days=i + 1)).strftime('%m-%d') for i in range(predict_days) ]
    pred_values = [float(round(float(p), 2)) for p in preds]

    return {'dates': pred_dates, 'values': pred_values}


def predict_weight_bmi(user, past_days=30, predict_days=14):
    """Estimate future weight and BMI using calorie balance.

    Approach:
    - Estimate user's TDEE using Mifflin-St Jeor and activity multiplier from UserProfile.
    - Compute recent average daily calories from NutritionEntry (fall back to HealthLog calories_intake).
    - Daily weight change (kg) ~= (calories_in - TDEE) / 7700
    - Produce a simple linear projection for the next `predict_days` days.

    Returns: {'dates': [...], 'weight': [...], 'height': [...], 'bmi': [...]} or None on missing profile
    """
    try:
        from .models import NutritionEntry, UserProfile
    except Exception:
        return None

    today = timezone.now().date()
    # need a profile with demographic data
    profile = getattr(user, 'userprofile', None)
    if not profile:
        return None

    # estimate BMR (Mifflin-St Jeor)
    try:
        weight = float(profile.weight)
        height_cm = float(profile.height)
        age = int(profile.age) if profile.age else 30
    except Exception:
        return None

    gender = getattr(profile, 'gender', 'male')
    if gender == 'female':
        bmr = 10 * weight + 6.25 * height_cm - 5 * age - 161
    else:
        bmr = 10 * weight + 6.25 * height_cm - 5 * age + 5

    # activity multipliers
    mult_map = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'very': 1.725,
        'extra': 1.9
    }
    activity = getattr(profile, 'activity_level', 'moderate')
    tdee = bmr * mult_map.get(activity, 1.55)

    # compute average daily calories from NutritionEntry over past_days
    start = today - timedelta(days=past_days)
    entries = NutritionEntry.objects.filter(user=user, created_at__date__gte=start)
    # if we have per-meal entries, aggregate by date
    calories_by_date = {}
    for e in entries:
        d = e.created_at.date()
        calories_by_date[d] = calories_by_date.get(d, 0) + (float(e.calories or 0))

    if calories_by_date:
        avg_calories = sum(calories_by_date.values()) / max(1, len(calories_by_date))
    else:
        # fallback to HealthLog.daily calories_intake
        logs = HealthLog.objects.filter(user=user, date__gte=start)
        vals = [float(l.calories_intake or 0) for l in logs]
        if vals:
            avg_calories = sum(vals) / max(1, len(vals))
        else:
            # no data
            avg_calories = None

    if avg_calories is None:
        return None

    # daily weight change (kg/day)
    daily_surplus = avg_calories - tdee
    kg_per_day = daily_surplus / 7700.0

    # produce predictions for next predict_days
    dates = []
    weights = []
    heights = []
    bmis = []

    height_m = height_cm / 100.0 if height_cm else 1.0
    base_weight = float(weight)

    for i in range(1, predict_days + 1):
        d = today + timedelta(days=i)
        dates.append(d.strftime('%m-%d'))
        w = base_weight + kg_per_day * i
        weights.append(round(w, 2))
        heights.append(round(height_cm, 1))
        bmi = round(w / (height_m ** 2), 2) if height_m > 0 else None
        bmis.append(bmi)

    return {'dates': dates, 'weight': weights, 'height': heights, 'bmi': bmis}
