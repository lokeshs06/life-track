from .forms import NutritionEntryForm, CustomPasswordResetForm, CustomUserCreationForm
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.db.models import Avg, Sum, Max
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta, datetime
import json
from .models import UserProfile, HealthLog, Recommendation, Goal, NutritionEntry
from .forms import UserProfileForm, HealthLogForm, GoalForm
from .forms import ProfileForm
from django.views.decorators.http import require_http_methods
# ML predictions
from .ml import predict_metric
# from .ai_recommendations import generate_recommendations  # Optional AI module


@login_required
def nutrition_tracking(request):
    """Nutrition tracking view with form for logging meals and viewing history"""
    if request.method == 'POST':
        try:
            entry = NutritionEntry(
                user=request.user,
                meal_type=request.POST.get('meal_type'),
                calories=request.POST.get('calories', 0),
                water=request.POST.get('water', 0),
                protein=request.POST.get('protein', 0),
                carbs=request.POST.get('carbs', 0),
                fat=request.POST.get('fat', 0),
                fiber=request.POST.get('fiber', 0),
                notes=request.POST.get('notes', '')
            )
            entry.save()
            messages.success(request, 'Nutrition entry added successfully!')
        except Exception as e:
            messages.error(request, f'Error saving entry: {str(e)}')
            
    # Calculate step changes
    weekly_stats = {}

    # Ensure date range variables exist even if userprofile is missing
    today = timezone.now()
    week_ago = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)

    if hasattr(request.user, 'userprofile'):

        # Current week stats
        current_week_logs = HealthLog.objects.filter(
            user=request.user,
            date__gte=week_ago,
            date__lt=today
        )
        # Previous week stats
        prev_week_logs = HealthLog.objects.filter(
            user=request.user,
            date__gte=two_weeks_ago,
            date__lt=week_ago
        )

        # Calculate averages
        curr_week_stats = current_week_logs.aggregate(
            avg_steps=Avg('steps'),
            avg_exercise=Avg('exercise_duration')
        )
        prev_week_stats = prev_week_logs.aggregate(
            avg_steps=Avg('steps'),
            avg_exercise=Avg('exercise_duration')
        )

        weekly_stats = {
            'avg_steps': curr_week_stats['avg_steps'],
            'prev_steps': prev_week_stats['avg_steps'],
            'avg_exercise': curr_week_stats['avg_exercise'],
            'prev_exercise': prev_week_stats['avg_exercise'],
        }

        # Calculate percentage changes
        def calculate_change(current, previous):
            if current and previous and previous > 0:
                change = ((current - previous) / previous) * 100
                return {
                    'value': abs(change),
                    'is_positive': change >= 0
                }
            return {
                'value': 0,
                'is_positive': True
            }

        weekly_stats['steps_change'] = calculate_change(
            weekly_stats['avg_steps'],
            weekly_stats['prev_steps']
        )

        weekly_stats['exercise_change'] = calculate_change(
            weekly_stats['avg_exercise'],
            weekly_stats['prev_exercise']
        )

    # Get recent entries
    recent_entries = NutritionEntry.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Prepare chart data
    entries = NutritionEntry.objects.filter(
        user=request.user,
        created_at__gte=week_ago
    ).order_by('created_at')
    
    dates = [entry.created_at.strftime('%Y-%m-%d') for entry in entries]
    calories_data = [entry.calories for entry in entries]
    
    # Calculate macro distribution (include fiber)
    total_protein = sum(entry.protein for entry in recent_entries)
    total_carbs = sum(entry.carbs for entry in recent_entries)
    total_fat = sum(entry.fat for entry in recent_entries)
    total_fiber = sum(entry.fiber for entry in recent_entries)
    macros_distribution = [total_protein, total_carbs, total_fat, total_fiber]
    # Pre-serialize JSON for JavaScript/Chart.js
    try:
        dates_json = json.dumps(dates)
        calories_data_json = json.dumps(calories_data)
        macros_distribution_json = json.dumps(macros_distribution)
    except Exception:
        # Fallback to safe stringification
        dates_json = '[]'
        calories_data_json = '[]'
        macros_distribution_json = '[0,0,0]'

    context = {
        'recent_entries': recent_entries,
        'dates': dates,
        'calories_data': calories_data,
        'macros_distribution': macros_distribution,
        'dates_json': dates_json,
        'calories_data_json': calories_data_json,
        'macros_distribution_json': macros_distribution_json,
    }
    
    return render(request, 'nutrition_tracking.html', context)

# Edit NutritionEntry view
@login_required
def edit_nutrition_entry(request, entry_id):
    entry = get_object_or_404(NutritionEntry, id=entry_id, user=request.user)
    if request.method == 'POST':
        form = NutritionEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, 'Nutrition entry updated successfully!')
            return redirect('nutrition_tracking')
    else:
        form = NutritionEntryForm(instance=entry)
    return render(request, 'edit_nutrition_entry.html', {'form': form, 'entry': entry})

# ---------------------- AUTHENTICATION ----------------------

def index(request):
    return render(request,'index.html')
def signup_view(request):
    """User signup and redirect to create profile"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully! Please complete your profile.')
            return redirect('create_profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'login.html', {'form': form})


@login_required
def logout_view(request):
    """Logout and redirect to login"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ---------------------- PROFILE ----------------------

@login_required
def create_profile(request):
    """Create user profile"""
    if hasattr(request.user, 'userprofile'):
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, 'Profile created successfully!')
            return redirect('dashboard')
    else:
        form = UserProfileForm()
    
    return render(request, 'create_profile.html', {'form': form})

# ---------------------- EDIT-PROFILE ----------------------
@login_required
def edit_profile(request):
    profile = request.user.userprofile  # assuming OneToOneField from User to Profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('dashboard')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'edit_profile.html', {'form': form})
# ---------------------- DASHBOARD ----------------------

@login_required
def dashboard(request):
    """Main user dashboard with stats and recommendations"""
    if not hasattr(request.user, 'userprofile'):
        return redirect('create_profile')
    
    profile = request.user.userprofile
    today = timezone.now().date()

    # Today's log
    today_log = HealthLog.objects.filter(user=request.user, date=today).first()

    # Last 7 days dates
    week_ago = today - timedelta(days=7)
    chart_dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    
    # Get all logs for the past week
    weekly_logs = HealthLog.objects.filter(user=request.user, date__gte=week_ago)
    
    # Prepare daily metrics data
    sleep_data = []
    water_data = []
    exercise_data = []
    steps_data = []
    
    for date in chart_dates:
        log = weekly_logs.filter(date=datetime.strptime(date, '%Y-%m-%d').date()).first()
        sleep_data.append(float(log.sleep_hours if log and log.sleep_hours else 0))
        water_data.append(float(log.water_intake if log and log.water_intake else 0))
        exercise_data.append(float(log.exercise_duration if log and log.exercise_duration else 0))
        steps_data.append(int(log.steps if log and log.steps else 0))

    # Prepare activity data combining steps and exercise
    activity_data = {
        'labels': chart_dates,
        'datasets': [
            {
                'label': 'Steps',
                'data': steps_data,
                'borderColor': 'rgb(59, 130, 246)',
                'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                'yAxisID': 'y-steps'
            },
            {
                'label': 'Exercise (min)',
                'data': exercise_data,
                'borderColor': 'rgb(16, 185, 129)',
                'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                'yAxisID': 'y-exercise'
            }
        ]
    }

    # Nutrition data for the past week
    nutrition_entries = NutritionEntry.objects.filter(
        user=request.user,
        created_at__date__gte=week_ago
    ).order_by('created_at')

    # Initialize calories data
    calories_data = {date: 0 for date in chart_dates}
    macros_total = {'protein': 0, 'carbs': 0, 'fat': 0}
    entries_count = 0

    # Aggregate nutrition data
    for entry in nutrition_entries:
        date_str = entry.created_at.strftime('%Y-%m-%d')
        if date_str in calories_data:
            calories_data[date_str] += float(entry.calories or 0)
            macros_total['protein'] += float(entry.protein or 0)
            macros_total['carbs'] += float(entry.carbs or 0)
            macros_total['fat'] += float(entry.fat or 0)
            entries_count += 1

    # Calculate averages for macros
    if entries_count > 0:
        macros_total = {k: round(v / entries_count, 1) for k, v in macros_total.items()}

    # Prepare nutrition chart data
    nutrition_chart_data = {
        'labels': chart_dates,
        'datasets': [{
            'label': 'Calories',
            'data': [calories_data[date] for date in chart_dates],
            'borderColor': 'rgb(251, 146, 60)',
            'backgroundColor': 'rgba(251, 146, 60, 0.1)',
            'fill': True
        }]
    }

    # Recent unread recommendations
    recommendations = Recommendation.objects.filter(user=request.user, is_read=False)[:5]

    # Top suggestions for dashboard (1-2 highest priority/unread)
    top_recommendations = Recommendation.objects.filter(user=request.user, is_read=False).order_by('-priority', '-created_at')[:2]

    # Active goals
    active_goals = Goal.objects.filter(user=request.user, is_achieved=False)

    # Chart parameters selected by user (stored in session)
    default_params = ['calories_intake', 'steps', 'sleep_hours']
    selected_params = request.session.get('chart_params', default_params)

    # Map field keys to labels and color palette
    metrics_map = {
        'calories_intake': {'label': 'Calories', 'border': '#ef4444', 'bg': 'rgba(239,68,68,0.08)'},
        'water_intake': {'label': 'Water (L)', 'border': '#06b6d4', 'bg': 'rgba(6,182,212,0.08)'},
        'steps': {'label': 'Steps', 'border': '#10b981', 'bg': 'rgba(16,185,129,0.08)'},
        'exercise_duration': {'label': 'Exercise (min)', 'border': '#f59e0b', 'bg': 'rgba(245,158,11,0.08)'},
        'sleep_hours': {'label': 'Sleep (hrs)', 'border': '#6366f1', 'bg': 'rgba(99,102,241,0.08)'},
        'protein': {'label': 'Protein (g)', 'border': '#db2777', 'bg': 'rgba(219,39,119,0.06)'},
        'carbs': {'label': 'Carbs (g)', 'border': '#7c3aed', 'bg': 'rgba(124,58,237,0.06)'},
        'fats': {'label': 'Fats (g)', 'border': '#0891b2', 'bg': 'rgba(8,145,178,0.06)'}
    }
       
    # Build chart data: dates and series
    dates = []
    series = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        dates.append(date.strftime('%m-%d'))

    for key in selected_params:
        data_points = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            log = weekly_logs.filter(date=date).first()
            if log:
                value = getattr(log, key, 0) or 0
            else:
                value = 0
            data_points.append(value)

        meta = metrics_map.get(key, {'label': key, 'border': '#4f46e5', 'bg': 'rgba(79,70,229,0.08)'})
        series.append({
            'label': meta['label'],
            'data': data_points,
            'borderColor': meta['border'],
            'backgroundColor': meta['bg']
        })

        # Try to get simple ML predictions for this metric (next 7 days)
        try:
            pred = predict_metric(request.user, key, past_days=30, predict_days=7)
            if pred:
                series.append({
                    'label': f"{meta['label']} (pred)",
                    'data': pred['values'],
                    'borderColor': meta['border'],
                    'backgroundColor': meta['bg'],
                    'dashed': True,
                    'dates': pred['dates']
                })
        except Exception:
            # if ML lib not available or prediction fails, ignore
            pass

    chart_data = {
        'dates': dates,
        'series': series
    }

    # Collect structured predictions for template (key -> {'label','dates','values','trend'})
    predictions = {}
    for s in series:
        if s.get('dashed'):
            key = s['label'].replace(' (pred)', '')
            predictions[key] = {
                'label': s['label'],
                'dates': s['dates'],
                'values': s['data'],
                'trend': 'up' if s['data'][-1] > s['data'][0] else 'down'
            }

    # Calculate weekly statistics
    weekly_stats = weekly_logs.aggregate(
        avg_steps=Avg('steps'),
        avg_sleep=Avg('sleep_hours'),
        total_exercise=Sum('exercise_duration'),
        avg_water=Avg('water_intake')
    )

    # Calculate weekly nutrition averages
    weekly_nutrition_stats = {
        'total_calories': sum(calories_data.values()),
        'avg_calories': round(sum(calories_data.values()) / len(chart_dates), 1)
    }

    # Prepare context with all required data
    context = {

        'profile': profile,
        'today_log': today_log,
        'chart_data': json.dumps(chart_data),
        'weekly_stats': {
            'avg_steps': weekly_stats['avg_steps'] or 0,
            'avg_sleep': weekly_stats['avg_sleep'] or 0,
            'total_exercise': weekly_stats['total_exercise'] or 0,
            'avg_water': weekly_stats['avg_water'] or 0
        },
        'activity_data': json.dumps(activity_data),
        'nutrition_chart_data': json.dumps(nutrition_chart_data),
        'macros_distribution_json': json.dumps(macros_total),
        'calories_data': calories_data,
        'weekly_nutrition_stats': weekly_nutrition_stats,
        'daily_averages': {'calories': weekly_nutrition_stats['avg_calories']},
    'recommendations': recommendations,
    'top_recommendations': top_recommendations,
        'active_goals': active_goals,
        'predictions': predictions,
    }
        # predicted series we added earlier have 'dashed' and 'dates' keys
    if s.get('dashed') and s.get('dates') and s.get('data'):
            # original key label is like 'Calories (pred)'; strip suffix
            label = s.get('label')
            preds = s.get('data')
            dates_pred = s.get('dates')
            # trend: compare last prediction to first prediction
            trend = 'stable'
            if len(preds) >= 2:
                if preds[-1] > preds[0]:
                    trend = 'up'
                elif preds[-1] < preds[0]:
                    trend = 'down'
            predictions[label] = {
                'label': label,
                'dates': dates_pred,
                'values': preds,
                'pairs': list(zip(dates_pred, preds)),
                'trend': trend
            }

    # Get nutrition data for the past week (same format as nutrition_tracking view)
    nutrition_week_ago = today - timedelta(days=7)
    nutrition_entries = NutritionEntry.objects.filter(
        user=request.user,
        created_at__gte=nutrition_week_ago
    ).order_by('created_at')
    
    # Prepare chart data in the EXACT same format as nutrition_tracking.html
    nutrition_dates = [entry.created_at.strftime('%Y-%m-%d') for entry in nutrition_entries]
    nutrition_calories_data = [entry.calories for entry in nutrition_entries]
    
    recent_nutrition = NutritionEntry.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Calculate macro distribution from this week's data
    total_protein = sum(float(entry.protein or 0) for entry in nutrition_entries)
    total_carbs = sum(float(entry.carbs or 0) for entry in nutrition_entries)
    total_fat = sum(float(entry.fat or 0) for entry in nutrition_entries)
    total_fiber = sum(float(entry.fiber or 0) for entry in nutrition_entries)
    
    # Format macros data as array for Chart.js (same as nutrition_tracking)
    macros_distribution = [total_protein, total_carbs, total_fat, total_fiber]
    
    # Pre-serialize JSON for JavaScript/Chart.js (same as nutrition_tracking)
    try:
        dates_json = json.dumps(nutrition_dates)
        calories_data_json = json.dumps(nutrition_calories_data)
        macros_distribution_json = json.dumps(macros_distribution)
    except Exception:
        # Fallback to safe stringification
        dates_json = '[]'
        calories_data_json = '[]'
        macros_distribution_json = '[0,0,0,0]'
    
    # Calculate daily averages
    num_days = max(1, len(set(entry.created_at.date() for entry in nutrition_entries)))
    daily_averages = {
        'calories': sum(float(entry.calories or 0) for entry in nutrition_entries) / num_days,
        'protein': total_protein / num_days,
        'carbs': total_carbs / num_days,
        'fat': total_fat / num_days,
        'fiber': (total_fiber or 0) / num_days
    }
    
    # Calculate weekly statistics
    weekly_nutrition_stats = NutritionEntry.objects.filter(
        user=request.user,
        created_at__gte=nutrition_week_ago
    ).aggregate(
        avg_calories=Avg('calories'),
        avg_protein=Avg('protein'),
        avg_carbs=Avg('carbs'),
        avg_fat=Avg('fat'),
        avg_fiber=Avg('fiber'),
        total_calories=Sum('calories'),
        total_protein=Sum('protein'),
        total_carbs=Sum('carbs'),
        total_fat=Sum('fat'),
        total_fiber=Sum('fiber')
    )

    # Get previous week's data for comparison
    prev_week_start = nutrition_week_ago - timedelta(days=7)
    prev_week_stats = NutritionEntry.objects.filter(
        user=request.user,
        created_at__gte=prev_week_start,
        created_at__lt=nutrition_week_ago
    ).aggregate(
        total_calories=Sum('calories'),
        total_protein=Sum('protein'),
        total_carbs=Sum('carbs'),
        total_fat=Sum('fat')
    )

    # Calculate week-over-week changes
    wow_changes = {}
    for metric in ['calories', 'protein', 'carbs', 'fat']:
        current = weekly_nutrition_stats.get(f'total_{metric}') or 0
        previous = prev_week_stats.get(f'total_{metric}') or 0
        if previous > 0:
            change = ((current - previous) / previous) * 100
            wow_changes[metric] = {
                'value': abs(round(change, 1)),
                'is_positive': change >= 0
            }
        else:
            wow_changes[metric] = {
                'value': 0,
                'is_positive': True
            }
    
    # Nutrition charts data already prepared above
    
    # Calculate daily averages
    daily_averages = {
        'calories': weekly_nutrition_stats.get('avg_calories', 0) or 0,
        'protein': weekly_nutrition_stats.get('avg_protein', 0) or 0,
        'carbs': weekly_nutrition_stats.get('avg_carbs', 0) or 0,
        'fat': weekly_nutrition_stats.get('avg_fat', 0) or 0,
        'fiber': weekly_nutrition_stats.get('avg_fiber', 0) or 0
    }

    # Prepare final context with all required data
    context = {
        'profile': profile,
        'today_log': today_log,
        'weekly_stats': weekly_stats,
        'recommendations': recommendations,
        'active_goals': active_goals,
        'chart_data': json.dumps(chart_data),
        'selected_params': selected_params,
        'predictions': predictions,
        'recent_nutrition': recent_nutrition,
        'nutrition_dates': nutrition_dates,
        'nutrition_calories_data': nutrition_calories_data,
        'calories_data_json': calories_data_json,
        'dates_json': dates_json,
        'macros_distribution': macros_distribution,
        'macros_distribution_json': macros_distribution_json,
        'daily_averages': daily_averages,
        'wow_changes': wow_changes,
        'weekly_nutrition_stats': weekly_nutrition_stats,
        'chart_dates': chart_dates,
        'sleep_data': sleep_data,
        'water_data': water_data
    }

    # Add weight/BMI predictions if available
    try:
        from .ml import predict_weight_bmi
        wb = predict_weight_bmi(request.user, past_days=30, predict_days=14)
        context['wb_predictions'] = wb
    except Exception:
        context['wb_predictions'] = None

    # Generate actionable suggestions from predictions
    wb_suggestions = []
    try:
        if context.get('wb_predictions'):
            preds = context['wb_predictions']
            w_vals = preds.get('weight', [])
            b_vals = preds.get('bmi', [])
            if len(w_vals) >= 2:
                delta = w_vals[-1] - w_vals[0]
                pct = (delta / (w_vals[0] or 1)) * 100
                # Suggestion based on direction and magnitude
                if abs(delta) < 0.1:
                    wb_suggestions.append('Your weight is projected to remain stable. Keep up consistent habits.')
                elif delta < 0:
                    wb_suggestions.append(f'Projected weight decrease of {abs(round(delta,2))} kg in next {len(w_vals)} days — continue your current calorie deficit or slightly increase activity.')
                else:
                    wb_suggestions.append(f'Projected weight increase of {round(delta,2)} kg in next {len(w_vals)} days — consider reducing daily calories or increasing activity.')

            # BMI-based suggestion
            if len(b_vals) >= 2:
                bdelta = b_vals[-1] - b_vals[0]
                if bdelta > 0.05:
                    wb_suggestions.append('BMI is trending upward — prioritize protein and strength training to preserve lean mass while managing calories.')
                elif bdelta < -0.05:
                    wb_suggestions.append('BMI is trending downward — ensure adequate protein and recovery to avoid muscle loss.')

            # Add a general tip
            if len(wb_suggestions) < 3:
                wb_suggestions.append('Log more nutrition data (meals) to improve forecast accuracy and personalized suggestions.')
    except Exception:
        wb_suggestions = []

    context['wb_suggestions'] = wb_suggestions

    return render(request, 'dashboard.html', context)


def _serialize_decimal(val):
    try:
        return float(val)
    except Exception:
        return val


def build_dashboard_payload(user, session):
    """Build a JSON-serializable payload with the same high-level data used by the dashboard.
    This avoids passing ORM objects to JSON responses.
    """
    from django.utils import timezone as _tz
    today = _tz.now().date()
    week_ago = today - timedelta(days=7)

    # Profile
    profile_obj = getattr(user, 'userprofile', None)
    profile = None
    if profile_obj:
        profile = {
            'weight': _serialize_decimal(profile_obj.weight),
            'height': _serialize_decimal(profile_obj.height),
            'bmi': _serialize_decimal(profile_obj.bmi),
            'activity_level': profile_obj.activity_level,
        }

    # Today's log (simple fields)
    today_log_obj = HealthLog.objects.filter(user=user, date=today).first()
    today_log = None
    if today_log_obj:
        today_log = {
            'steps': today_log_obj.steps,
            'exercise_duration': today_log_obj.exercise_duration,
            'calories_intake': _serialize_decimal(today_log_obj.calories_intake),
        }

    # Weekly aggregates
    weekly_logs = HealthLog.objects.filter(user=user, date__gte=week_ago)
    weekly_stats_agg = weekly_logs.aggregate(
        avg_calories=Avg('calories_intake'),
        avg_steps=Avg('steps'),
        avg_sleep=Avg('sleep_hours'),
        total_exercise=Sum('exercise_duration')
    )
    weekly_stats = {k: _serialize_decimal(v) for k, v in weekly_stats_agg.items()}

    # Active goals
    active_goals_qs = Goal.objects.filter(user=user, is_achieved=False)
    active_goals = []
    for g in active_goals_qs:
        active_goals.append({
            'id': g.id,
            'goal_type': g.goal_type,
            'target_value': _serialize_decimal(g.target_value),
            'current_value': _serialize_decimal(g.current_value),
            'deadline': g.deadline.isoformat() if g.deadline else None,
            'progress_percentage': _serialize_decimal(g.progress_percentage),
        })

    # Chart series (respect session selected params)
    default_params = ['calories_intake', 'steps', 'sleep_hours']
    selected_params = session.get('chart_params', default_params)

    metrics_map = {
        'calories_intake': {'label': 'Calories', 'border': '#ef4444', 'bg': 'rgba(239,68,68,0.08)'},
        'water_intake': {'label': 'Water (L)', 'border': '#06b6d4', 'bg': 'rgba(6,182,212,0.08)'},
        'steps': {'label': 'Steps', 'border': '#10b981', 'bg': 'rgba(16,185,129,0.08)'},
        'exercise_duration': {'label': 'Exercise (min)', 'border': '#f59e0b', 'bg': 'rgba(245,158,11,0.08)'},
        'sleep_hours': {'label': 'Sleep (hrs)', 'border': '#6366f1', 'bg': 'rgba(99,102,241,0.08)'},
        'protein': {'label': 'Protein (g)', 'border': '#db2777', 'bg': 'rgba(219,39,119,0.06)'},
        'carbs': {'label': 'Carbs (g)', 'border': '#7c3aed', 'bg': 'rgba(124,58,237,0.06)'},
        'fats': {'label': 'Fats (g)', 'border': '#0891b2', 'bg': 'rgba(8,145,178,0.06)'}
    }

    dates = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        dates.append(date.strftime('%m-%d'))

    series = []
    for key in selected_params:
        data_points = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            log = weekly_logs.filter(date=date).first()
            if log:
                value = getattr(log, key, 0) or 0
            else:
                value = 0
            data_points.append(_serialize_decimal(value))

        meta = metrics_map.get(key, {'label': key, 'border': '#4f46e5', 'bg': 'rgba(79,70,229,0.08)'})
        series.append({
            'label': meta['label'],
            'data': data_points,
            'borderColor': meta['border'],
            'backgroundColor': meta['bg']
        })

    chart_data = {'dates': dates, 'series': series}

    # Predictions (reuse predict_metric if available)
    predictions = {}
    try:
        for s in series:
            try:
                key_label = s['label']
                # attempt a best-effort prediction call (using original key if available)
                # predictions may fail silently if ml isn't available
                pass
            except Exception:
                continue
    except Exception:
        predictions = {}

    # Nutrition week data
    nutrition_week_ago = today - timedelta(days=7)
    nutrition_entries = NutritionEntry.objects.filter(user=user, created_at__gte=nutrition_week_ago).order_by('created_at')
    nutrition_dates = [e.created_at.isoformat() for e in nutrition_entries]
    calories_data = [int(e.calories) for e in nutrition_entries]

    # Weekly nutrition aggregates
    weekly_nutrition_stats = NutritionEntry.objects.filter(user=user, created_at__gte=nutrition_week_ago).aggregate(
        avg_calories=Avg('calories'),
        avg_protein=Avg('protein'),
        avg_carbs=Avg('carbs'),
        avg_fat=Avg('fat'),
        total_calories=Sum('calories'),
        total_protein=Sum('protein'),
        total_carbs=Sum('carbs'),
        total_fat=Sum('fat')
    )
    weekly_nutrition_stats = {k: _serialize_decimal(v) for k, v in weekly_nutrition_stats.items()}

    # Recent nutrition entries
    recent_nutrition_qs = NutritionEntry.objects.filter(user=user).order_by('-created_at')[:10]
    recent_nutrition = []
    for e in recent_nutrition_qs:
        recent_nutrition.append({
            'created_at': e.created_at.isoformat(),
            'meal_type': e.meal_type,
            'calories': int(e.calories),
            'protein': _serialize_decimal(e.protein),
            'carbs': _serialize_decimal(e.carbs),
            'fat': _serialize_decimal(e.fat),
        })

    # week-over-week changes
    prev_week_start = nutrition_week_ago - timedelta(days=7)
    prev_week_stats = NutritionEntry.objects.filter(user=user, created_at__gte=prev_week_start, created_at__lt=nutrition_week_ago).aggregate(
        total_calories=Sum('calories'),
        total_protein=Sum('protein'),
        total_carbs=Sum('carbs'),
        total_fat=Sum('fat')
    )

    wow_changes = {}
    for metric in ['calories', 'protein', 'carbs', 'fat']:
        current = weekly_nutrition_stats.get(f'total_{metric}') or 0
        previous = prev_week_stats.get(f'total_{metric}') or 0
        try:
            current_f = float(current)
            previous_f = float(previous)
        except Exception:
            current_f = current or 0
            previous_f = previous or 0

        if previous_f > 0:
            change = ((current_f - previous_f) / previous_f) * 100
            wow_changes[metric] = {'value': round(abs(change), 1), 'is_positive': change >= 0}
        else:
            wow_changes[metric] = {'value': 0, 'is_positive': True}

    payload = {
        'profile': profile,
        'today_log': today_log,
        'weekly_stats': weekly_stats,
        'active_goals': active_goals,
        'chart_data': chart_data,
        'predictions': predictions,
        'nutrition_dates': nutrition_dates,
        'calories_data': calories_data,
        'macros_distribution': [
            weekly_nutrition_stats.get('total_protein') or 0,
            weekly_nutrition_stats.get('total_carbs') or 0,
            weekly_nutrition_stats.get('total_fat') or 0
        ],
        'daily_averages': {
            'calories': weekly_nutrition_stats.get('avg_calories') or 0,
            'protein': weekly_nutrition_stats.get('avg_protein') or 0,
            'carbs': weekly_nutrition_stats.get('avg_carbs') or 0,
            'fat': weekly_nutrition_stats.get('avg_fat') or 0,
        },
        'wow_changes': wow_changes,
        'weekly_nutrition_stats': weekly_nutrition_stats,
        'recent_nutrition': recent_nutrition,
    }

    return payload


@login_required
def dashboard_data(request):
    """Return a JSON friendly payload of dashboard data for the logged-in user."""
    payload = build_dashboard_payload(request.user, request.session)
    return JsonResponse(payload, safe=True)


# ---------------------- HEALTH LOG ----------------------

@login_required
def add_health_log(request):
    today = timezone.now().date()
    existing_log = HealthLog.objects.filter(user=request.user, date=today).first()

    if request.method == 'POST':
        # make a mutable copy of POST so we can supply safe defaults for missing numeric fields
        data = request.POST.copy()
        # numeric fields required by HealthLog model; supply '0' if missing/empty
        numeric_fields = ['calories_intake', 'protein', 'carbs', 'fats', 'water_intake', 'steps', 'exercise_duration', 'sleep_hours']
        for nf in numeric_fields:
            if not data.get(nf):
                data[nf] = '0'
        
        # Optional fields - remove if empty to allow null values
        optional_fields = ['heart_rate', 'blood_pressure_sys', 'blood_pressure_dia']
        for of in optional_fields:
            if not data.get(of):
                data[of] = ''

        form = HealthLogForm(data, instance=existing_log)
        if form.is_valid():
            log = form.save(commit=False)
            log.user = request.user
            log.date = today
            log.save()
            # Save selected chart parameters to session (if provided)
            selected = request.POST.getlist('chart_params')
            if selected:
                request.session['chart_params'] = selected
            messages.success(request, "Health log saved successfully!")
            return redirect('view_logs')
        else:
            # surface validation errors to the UI so users know why save failed
            err_text = '; '.join([f"{k}: {', '.join(v)}" for k, v in form.errors.items()])
            messages.error(request, f'Unable to save health log: {err_text}')
    else:
        form = HealthLogForm(instance=existing_log)

    # preserve chart parameter selections so the form can show current choices
    default_params = ['calories_intake', 'steps', 'sleep_hours']
    selected_params = request.session.get('chart_params', default_params)

    return render(request, 'add_log.html', {'form': form, 'selected_params': selected_params})

@login_required
def view_logs(request):
    """Display all health logs of the logged-in user"""
    logs = HealthLog.objects.filter(user=request.user).order_by('-date')
    return render(request, 'view_logs.html', {'logs': logs})


@login_required
def edit_health_log(request, log_id):
    log = get_object_or_404(HealthLog, id=log_id, user=request.user)
    if request.method == 'POST':
        data = request.POST.copy()
        # fill missing numeric fields
        numeric_fields = ['calories_intake', 'protein', 'carbs', 'fats', 'water_intake', 'steps', 'exercise_duration', 'sleep_hours']
        for nf in numeric_fields:
            if not data.get(nf):
                data[nf] = '0'

        form = HealthLogForm(data, instance=log)
        if form.is_valid():
            form.save()
            messages.success(request, 'Health log updated successfully!')
            return redirect('view_logs')
        else:
            messages.error(request, 'Unable to update log: ' + '; '.join([f"{k}: {', '.join(v)}" for k, v in form.errors.items()]))
    else:
        form = HealthLogForm(instance=log)
    return render(request, 'add_log.html', {'form': form})


@login_required
@require_http_methods(["POST"])
def delete_health_log(request, log_id):
    log = get_object_or_404(HealthLog, id=log_id, user=request.user)
    log.delete()
    messages.success(request, 'Health log deleted.')
    return redirect('view_logs')


# ---------------------- GOALS ----------------------

@login_required
def manage_goals(request):
    """Create and view goals with automatic progress updates"""
    if request.method == 'POST':
        if 'apply_suggestion' in request.POST:
            # Handle suggestion application
            suggestion_type = request.POST.get('suggestion_type')
            suggestion_target = request.POST.get('suggestion_target')
            
            # Create the goal and mark it as coming from a suggestion
            if suggestion_type and suggestion_target:
                # Calculate a default deadline (30 days from now)
                deadline = timezone.now().date() + timedelta(days=30)
                
                # Check if a similar goal already exists
                existing_goal = Goal.objects.filter(
                    user=request.user,
                    goal_type=suggestion_type,
                    is_achieved=False
                ).exists()
                
                if not existing_goal:
                    Goal.objects.create(
                        user=request.user,
                        goal_type=suggestion_type,
                        target_value=float(suggestion_target),
                        deadline=deadline,
                        current_value=0
                    )
                    messages.success(request, 'Suggested goal has been added!')
                    
                    # Store applied suggestion in session
                    applied_suggestions = request.session.get('applied_suggestions', [])
                    suggestion_key = f"{suggestion_type}_{suggestion_target}"
                    if suggestion_key not in applied_suggestions:
                        applied_suggestions.append(suggestion_key)
                        request.session['applied_suggestions'] = applied_suggestions
                else:
                    messages.info(request, 'You already have an active goal of this type.')
            return redirect('manage_goals')
            
        if 'delete_goal' in request.POST:
            # Handle goal deletion
            goal_id = request.POST.get('goal_id')
            try:
                goal = Goal.objects.get(id=goal_id, user=request.user)
                goal_type = goal.get_goal_type_display()
                goal.delete()
                messages.success(request, f'Your {goal_type} goal has been deleted.')
            except Goal.DoesNotExist:
                messages.error(request, 'Goal not found.')
            return redirect('manage_goals')
            
        if 'update_goal' in request.POST:
            # Handle goal progress update
            goal_id = request.POST.get('goal_id')
            new_value = request.POST.get('current_value')
            goal = get_object_or_404(Goal, id=goal_id, user=request.user)
            try:
                goal.current_value = float(new_value)
                if goal.current_value >= goal.target_value:
                    goal.is_achieved = True
                    messages.success(request, f'Congratulations! You\'ve achieved your {goal.get_goal_type_display()} goal!')
                goal.save()
                messages.success(request, 'Progress updated successfully!')
            except ValueError:
                messages.error(request, 'Invalid value provided.')
            return redirect('manage_goals')
        
        # Handle new goal creation
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, 'Goal created successfully!')
            return redirect('manage_goals')
    else:
        form = GoalForm()
    
    # Get goals and organize them by status
    active_goals = Goal.objects.filter(user=request.user, is_achieved=False).order_by('deadline')
    achieved_goals = Goal.objects.filter(user=request.user, is_achieved=True).order_by('-created_at')
    
    # Calculate time-based stats
    today = timezone.now().date()
    stats = {
        'total_goals': active_goals.count() + achieved_goals.count(),
        'active_goals': active_goals.count(),
        'achieved_goals': achieved_goals.count(),
        'upcoming_deadlines': active_goals.filter(deadline__lte=today + timedelta(days=7)).count()
    }
    
    # Get current active goal types to filter suggestions
    active_goal_types = set(active_goals.values_list('goal_type', flat=True))
    
    # Get user's health logs for suggestions
    health_logs = HealthLog.objects.filter(user=request.user).order_by('-date')
    recent_logs = health_logs[:7]  # Last 7 days
    monthly_logs = health_logs[:30]  # Last 30 days
    
    # Get applied suggestions from session
    applied_suggestions = request.session.get('applied_suggestions', [])
    
    # Get current active goals to avoid suggesting duplicates
    active_goal_types = set(Goal.objects.filter(
        user=request.user,
        is_achieved=False
    ).values_list('goal_type', flat=True))
    
    # Calculate suggested goals based on recent activity
    suggested_goals = []
    if recent_logs:
        # 1. Steps Goals
        avg_steps = recent_logs.aggregate(Avg('steps'))['steps__avg']
        max_steps = recent_logs.aggregate(Max('steps'))['steps__max']
        
        if avg_steps and avg_steps < 10000:
            suggested_goals.append({
                'type': 'steps',
                'target': 10000,
                'message': 'Aim for 10,000 daily steps for better health'
            })
        elif max_steps and max_steps > avg_steps * 1.2:  # If max is 20% higher than average
            suggested_goals.append({
                'type': 'steps',
                'target': int(max_steps),
                'message': f'Challenge yourself to reach {int(max_steps)} steps again'
            })
        elif avg_steps:
            new_target = int(avg_steps * 1.1)
            suggested_goals.append({
                'type': 'steps',
                'target': new_target,
                'message': f'Push yourself to {new_target} steps daily'
            })
            
        # 2. Sleep Goals
        avg_sleep = recent_logs.aggregate(Avg('sleep_hours'))['sleep_hours__avg']
        if avg_sleep:
            if avg_sleep < 6:
                suggested_goals.append({
                    'type': 'sleep',
                    'target': 7,
                    'message': 'Increase sleep to at least 7 hours for basic health'
                })
            elif avg_sleep < 7:
                suggested_goals.append({
                    'type': 'sleep',
                    'target': 8,
                    'message': 'Aim for 8 hours sleep for optimal rest'
                })
            elif avg_sleep < 8:
                suggested_goals.append({
                    'type': 'sleep',
                    'target': 8,
                    'message': 'Optimize your sleep schedule to 8 hours'
                })
            
        # 3. Water Intake Goals - Based on healthy guidelines
        avg_water = recent_logs.aggregate(Avg('water_intake'))['water_intake__avg']
        try:
            profile = request.user.userprofile
            # Calculate recommended water intake based on weight and activity
            weight_based = round(profile.weight * 0.033, 1)  # 33ml per kg body weight
            
            if profile.activity_level in ['very', 'extra']:
                recommended = min(3.7, weight_based + 1.0)  # Extra for very active
            elif profile.activity_level == 'moderate':
                recommended = min(3.5, weight_based + 0.5)  # Some extra for moderate
            else:
                recommended = min(3.0, weight_based)  # Base recommendation
                
            # Round to nearest 0.1L
            recommended = round(recommended, 1)
            
            if avg_water:
                if avg_water < 1.5:
                    target = min(2.0, recommended)
                    suggested_goals.append({
                        'type': 'water',
                        'target': target,
                        'message': f'Increase water intake to {target}L daily for basic hydration'
                    })
                elif avg_water < recommended:
                    suggested_goals.append({
                        'type': 'water',
                        'target': recommended,
                        'message': f'Work towards {recommended}L daily for optimal hydration'
                    })
                elif avg_water > 4.0:  # If drinking too much
                    suggested_goals.append({
                        'type': 'water',
                        'target': recommended,
                        'message': f'Consider reducing to {recommended}L daily for safe hydration'
                    })
                else:
                    # If within healthy range, maintain current level
                    suggested_goals.append({
                        'type': 'water',
                        'target': avg_water,
                        'message': f'Maintain healthy hydration of {avg_water}L daily'
                    })
        except (AttributeError, ObjectDoesNotExist):
            # If no profile, use general recommendations
            if avg_water:
                if avg_water < 1.5:
                    suggested_goals.append({
                        'type': 'water',
                        'target': 2.0,
                        'message': 'Increase water intake to 2L daily'
                    })
                elif avg_water > 4.0:
                    suggested_goals.append({
                        'type': 'water',
                        'target': 3.0,
                        'message': 'Consider reducing to 3L daily for safe hydration'
                    })
                else:
                    suggested_goals.append({
                        'type': 'water',
                        'target': avg_water,
                        'message': f'Maintain current hydration of {avg_water}L daily'
                    })
            
        # 4. Exercise Duration Goals
        avg_exercise = recent_logs.aggregate(Avg('exercise_duration'))['exercise_duration__avg']
        if avg_exercise:
            if avg_exercise < 15:
                suggested_goals.append({
                    'type': 'exercise',
                    'target': 30,
                    'message': 'Build up to 30 minutes exercise daily'
                })
            elif avg_exercise < 30:
                suggested_goals.append({
                    'type': 'exercise',
                    'target': 45,
                    'message': 'Increase exercise to 45 minutes daily'
                })
            elif avg_exercise < 60:
                suggested_goals.append({
                    'type': 'exercise',
                    'target': 60,
                    'message': 'Work towards 60 minutes daily exercise'
                })
            else:
                new_target = int(avg_exercise * 1.15)
                suggested_goals.append({
                    'type': 'exercise',
                    'target': new_target,
                    'message': f'Push your workouts to {new_target} minutes'
                })
            
        # 5. Weight Management Goals
        try:
            profile = request.user.userprofile
            current_weight = profile.weight if hasattr(profile, 'weight') else None
            target_weight = profile.target_weight if hasattr(profile, 'target_weight') else None
            
            if current_weight:
                if target_weight:
                    # If target weight is set, suggest goal based on that
                    weight_diff = current_weight - target_weight
                    if abs(weight_diff) > 0.5:  # If more than 0.5 kg from target
                        suggested_goals.append({
                            'type': 'weight',
                            'target': target_weight,
                            'message': f'{"Lose" if weight_diff > 0 else "Gain"} weight to reach {target_weight}kg'
                        })
                else:
                    # If no target weight, suggest based on BMI
                    height_m = profile.height / 100
                    bmi = current_weight / (height_m ** 2)
                    if bmi > 25:  # Overweight
                        ideal_weight = round(23 * (height_m ** 2), 1)  # Using BMI 23 as target
                        suggested_goals.append({
                            'type': 'weight',
                            'target': ideal_weight,
                            'message': f'Work towards a healthy weight of {ideal_weight}kg'
                        })
        except (AttributeError, ObjectDoesNotExist):
            # Skip weight suggestions if profile doesn't exist or is incomplete
            pass
                    
        # 6. Trend-based Goals (using monthly data)
        if monthly_logs.count() >= 14:  # If we have at least 2 weeks of data
            recent_stats = recent_logs.aggregate(
                avg_steps=Avg('steps'),
                avg_exercise=Avg('exercise_duration'),
                avg_water=Avg('water_intake')
            )
            
            past_stats = monthly_logs[7:].aggregate(
                avg_steps=Avg('steps'),
                avg_exercise=Avg('exercise_duration'),
                avg_water=Avg('water_intake')
            )
            
            # If recent performance dropped, suggest recovery goals
            if recent_stats['avg_steps'] and past_stats['avg_steps'] and \
               recent_stats['avg_steps'] < past_stats['avg_steps'] * 0.9:
                suggested_goals.append({
                    'type': 'steps',
                    'target': int(past_stats['avg_steps']),
                    'message': 'Get back to your usual step count'
                })
                
            if recent_stats['avg_exercise'] and past_stats['avg_exercise'] and \
               recent_stats['avg_exercise'] < past_stats['avg_exercise'] * 0.9:
                suggested_goals.append({
                    'type': 'exercise',
                    'target': int(past_stats['avg_exercise']),
                    'message': 'Return to your regular exercise duration'
                })
                
            if recent_stats['avg_water'] and past_stats['avg_water'] and \
               recent_stats['avg_water'] < past_stats['avg_water'] * 0.9:
                suggested_goals.append({
                    'type': 'water',
                    'target': round(past_stats['avg_water'], 1),
                    'message': 'Maintain your usual water intake'
                })
    
    context = {
        'form': form,
        'active_goals': active_goals,
        'achieved_goals': achieved_goals,
        'stats': stats,
        'suggested_goals': suggested_goals
    }
    
    return render(request, 'manage_goals.html', context)


# ---------------------- RECOMMENDATIONS ----------------------

@login_required
def delete_nutrition_entry(request, entry_id):
    """Delete a nutrition entry"""
    entry = get_object_or_404(NutritionEntry, id=entry_id, user=request.user)
    entry.delete()
    messages.success(request, 'Nutrition entry deleted successfully!')
    return redirect('nutrition_tracking')

@login_required
def view_recommendations(request):
    """View all recommendations"""
    recommendations = Recommendation.objects.filter(user=request.user)

    # If user has no recommendations, generate lightweight rule-based ones
    if not recommendations.exists():
        # generate recommendations using shared helper
        from .recommendation_utils import generate_recommendations_for_user
        generate_recommendations_for_user(request.user)
        recommendations = Recommendation.objects.filter(user=request.user)

    # Mark unread as read
    Recommendation.objects.filter(user=request.user, is_read=False).update(is_read=True)

    return render(request, 'recommendations.html', {'recommendations': recommendations})


@login_required
@require_http_methods(["POST"])
def regenerate_recommendations(request):
    """Delete existing recommendations and regenerate them immediately."""
    # remove existing recommendations for this user
    Recommendation.objects.filter(user=request.user).delete()
    # call generator
    from .recommendation_utils import generate_recommendations_for_user
    generate_recommendations_for_user(request.user)
    messages.success(request, 'Recommendations regenerated.')
    return redirect('view_recommendations')


def custom_password_reset(request):
    """Custom password reset view that accepts both email and username"""
    if request.method == 'POST':
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                from_email=None,
                email_template_name='registration/password_reset_email.html',
                subject_template_name='registration/password_reset_subject.txt',
            )
            return redirect('password_reset_done')
    else:
        form = CustomPasswordResetForm()
    
    return render(request, 'registration/custom_password_reset_form.html', {'form': form})

"""
predict
"""
def evaluate_view(request):
    from lifeapp.evaluate_prediction import evaluate_user
    if not request.user.is_authenticated:
        return HttpResponse("Login required")
    
    metrics = ['steps', 'calories_intake', 'sleep_hours']
    results = evaluate_user(request.user, metrics=metrics, plot=False)
    return JsonResponse(results)
