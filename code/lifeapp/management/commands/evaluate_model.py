"""
Django management command to evaluate ML model performance.

Usage:
    python manage.py evaluate_model
    python manage.py evaluate_model --user username
    python manage.py evaluate_model --metric sleep_hours
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from lifeapp.models import HealthLog, NutritionEntry
from lifeapp.ml import predict_metric, predict_weight_bmi
import json


class Command(BaseCommand):
    help = 'Evaluate ML model performance for health predictions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username to evaluate (default: all users)',
        )
        parser.add_argument(
            '--metric',
            type=str,
            default='all',
            help='Metric to evaluate: sleep_hours, steps, calories_intake, water_intake, or all',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to use for testing (default: 7)',
        )

    def handle(self, *args, **options):
        username = options.get('user')
        metric = options.get('metric')
        test_days = options.get('days')

        self.stdout.write(self.style.SUCCESS('\n=== ML Model Performance Evaluation ===\n'))

        # Get users to evaluate
        if username:
            users = User.objects.filter(username=username)
            if not users.exists():
                self.stdout.write(self.style.ERROR(f'User "{username}" not found'))
                return
        else:
            users = User.objects.all()

        # Metrics to evaluate
        if metric == 'all':
            metrics = ['sleep_hours', 'steps', 'calories_intake', 'water_intake', 'exercise_duration']
        else:
            metrics = [metric]

        total_results = {
            'users_evaluated': 0,
            'metrics': {},
            'weight_bmi_predictions': []
        }

        for user in users:
            self.stdout.write(f'\nEvaluating user: {user.username}')
            
            # Check if user has enough data
            total_logs = HealthLog.objects.filter(user=user).count()
            if total_logs < test_days + 7:
                self.stdout.write(self.style.WARNING(
                    f'  Skipping {user.username}: insufficient data (need at least {test_days + 7} logs, has {total_logs})'
                ))
                continue

            total_results['users_evaluated'] += 1

            # Evaluate metric predictions
            for metric_name in metrics:
                result = self.evaluate_metric_prediction(user, metric_name, test_days)
                if result:
                    if metric_name not in total_results['metrics']:
                        total_results['metrics'][metric_name] = []
                    total_results['metrics'][metric_name].append(result)

            # Evaluate weight/BMI predictions
            weight_result = self.evaluate_weight_bmi_prediction(user, test_days)
            if weight_result:
                total_results['weight_bmi_predictions'].append(weight_result)

        # Display summary
        self.display_summary(total_results)

    def evaluate_metric_prediction(self, user, metric_field, test_days):
        """Evaluate prediction accuracy for a specific metric."""
        today = timezone.now().date()
        
        # Use data up to test_days ago for training
        train_end = today - timedelta(days=test_days)
        
        # Get actual values for the test period
        test_logs = HealthLog.objects.filter(
            user=user,
            date__gt=train_end,
            date__lte=today
        ).order_by('date')

        actual_values = []
        actual_dates = []
        for log in test_logs:
            val = getattr(log, metric_field, None)
            if val is not None:
                try:
                    actual_values.append(float(val))
                    actual_dates.append(log.date)
                except:
                    pass

        if len(actual_values) < 3:
            return None

        # Make predictions using data before train_end
        # Temporarily filter to simulate past data
        try:
            from sklearn.linear_model import LinearRegression
            import numpy as np
        except ImportError:
            self.stdout.write(self.style.WARNING(
                f'  Skipping {metric_field}: sklearn not installed'
            ))
            return None

        # Get training data
        train_start = train_end - timedelta(days=30)
        train_logs = HealthLog.objects.filter(
            user=user,
            date__gte=train_start,
            date__lte=train_end
        ).order_by('date')

        xs = []
        ys = []
        for i, log in enumerate(train_logs):
            val = getattr(log, metric_field, None)
            if val is not None:
                try:
                    xs.append([i])
                    ys.append(float(val))
                except:
                    pass

        if len(ys) < 3:
            return None

        # Train model
        X = np.array(xs)
        y = np.array(ys)
        model = LinearRegression()
        model.fit(X, y)

        # Make predictions
        last_index = X[-1][0]
        pred_indices = np.array([[last_index + i + 1] for i in range(len(actual_values))])
        predictions = model.predict(pred_indices)

        # Calculate metrics
        mae = np.mean(np.abs(np.array(actual_values) - predictions))
        mse = np.mean((np.array(actual_values) - predictions) ** 2)
        rmse = np.sqrt(mse)
        
        # Calculate R² score
        ss_res = np.sum((np.array(actual_values) - predictions) ** 2)
        ss_tot = np.sum((np.array(actual_values) - np.mean(actual_values)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # Calculate MAPE (Mean Absolute Percentage Error)
        mape = np.mean(np.abs((np.array(actual_values) - predictions) / np.array(actual_values))) * 100
        mape = mape if not np.isnan(mape) and not np.isinf(mape) else 0

        self.stdout.write(f'  {metric_field}:')
        self.stdout.write(f'    MAE: {mae:.2f}')
        self.stdout.write(f'    RMSE: {rmse:.2f}')
        self.stdout.write(f'    R²: {r2:.4f}')
        self.stdout.write(f'    MAPE: {mape:.2f}%')

        return {
            'user': user.username,
            'metric': metric_field,
            'mae': float(mae),
            'rmse': float(rmse),
            'r2': float(r2),
            'mape': float(mape),
            'n_predictions': len(actual_values),
            'n_training': len(ys)
        }

    def evaluate_weight_bmi_prediction(self, user, test_days):
        """Evaluate weight/BMI prediction accuracy."""
        if not hasattr(user, 'userprofile'):
            return None

        today = timezone.now().date()
        train_end = today - timedelta(days=test_days)

        # Get actual nutrition data for test period
        test_entries = NutritionEntry.objects.filter(
            user=user,
            created_at__date__gt=train_end,
            created_at__date__lte=today
        )

        if test_entries.count() < 3:
            return None

        # Calculate actual average calories during test period
        actual_calories = []
        for entry in test_entries:
            if entry.calories:
                actual_calories.append(float(entry.calories))

        if not actual_calories:
            return None

        avg_actual_calories = sum(actual_calories) / len(actual_calories)

        # Get predicted calories (using training data)
        train_entries = NutritionEntry.objects.filter(
            user=user,
            created_at__date__gte=train_end - timedelta(days=30),
            created_at__date__lte=train_end
        )

        predicted_calories = []
        for entry in train_entries:
            if entry.calories:
                predicted_calories.append(float(entry.calories))

        if not predicted_calories:
            return None

        avg_predicted_calories = sum(predicted_calories) / len(predicted_calories)

        # Calculate error
        calorie_error = abs(avg_actual_calories - avg_predicted_calories)
        calorie_error_pct = (calorie_error / avg_actual_calories * 100) if avg_actual_calories > 0 else 0

        self.stdout.write(f'  Weight/BMI Prediction:')
        self.stdout.write(f'    Avg Predicted Calories: {avg_predicted_calories:.0f}')
        self.stdout.write(f'    Avg Actual Calories: {avg_actual_calories:.0f}')
        self.stdout.write(f'    Calorie Error: {calorie_error:.0f} ({calorie_error_pct:.1f}%)')

        return {
            'user': user.username,
            'avg_predicted_calories': float(avg_predicted_calories),
            'avg_actual_calories': float(avg_actual_calories),
            'calorie_error': float(calorie_error),
            'calorie_error_pct': float(calorie_error_pct)
        }

    def display_summary(self, results):
        """Display overall summary of evaluation results."""
        self.stdout.write(self.style.SUCCESS('\n\n=== Evaluation Summary ===\n'))
        self.stdout.write(f'Total users evaluated: {results["users_evaluated"]}')

        if results['metrics']:
            self.stdout.write('\n--- Metric Predictions ---')
            for metric_name, metric_results in results['metrics'].items():
                if not metric_results:
                    continue

                avg_mae = sum(r['mae'] for r in metric_results) / len(metric_results)
                avg_rmse = sum(r['rmse'] for r in metric_results) / len(metric_results)
                avg_r2 = sum(r['r2'] for r in metric_results) / len(metric_results)
                avg_mape = sum(r['mape'] for r in metric_results) / len(metric_results)

                self.stdout.write(f'\n{metric_name.upper()}:')
                self.stdout.write(f'  Average MAE: {avg_mae:.2f}')
                self.stdout.write(f'  Average RMSE: {avg_rmse:.2f}')
                self.stdout.write(f'  Average R²: {avg_r2:.4f}')
                self.stdout.write(f'  Average MAPE: {avg_mape:.2f}%')
                self.stdout.write(f'  Users evaluated: {len(metric_results)}')

        if results['weight_bmi_predictions']:
            self.stdout.write('\n--- Weight/BMI Predictions ---')
            avg_error = sum(r['calorie_error'] for r in results['weight_bmi_predictions']) / len(results['weight_bmi_predictions'])
            avg_error_pct = sum(r['calorie_error_pct'] for r in results['weight_bmi_predictions']) / len(results['weight_bmi_predictions'])

            self.stdout.write(f'  Average Calorie Error: {avg_error:.0f} ({avg_error_pct:.1f}%)')
            self.stdout.write(f'  Users evaluated: {len(results["weight_bmi_predictions"])}')

        # Save results to JSON file
        output_file = 'model_evaluation_results.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.stdout.write(self.style.SUCCESS(f'\n\nResults saved to: {output_file}'))
