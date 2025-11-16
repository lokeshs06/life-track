# utils/evaluate_predictions.py
from datetime import timedelta
from django.utils import timezone
import numpy as np
import matplotlib.pyplot as plt

from .models import HealthLog, UserProfile, NutritionEntry
from .ml import predict_metric, predict_weight_bmi

from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import os


def evaluate_metric(user, metric_field, past_days=30, test_days=7, plot=False):
    """
    Evaluate linear regression prediction for a numeric metric.
    Returns a dict with R², MAE, RMSE, and optionally plot.
    """
    today = timezone.now().date()
    start = today - timedelta(days=past_days + test_days)
    logs = HealthLog.objects.filter(user=user, date__gte=start).order_by('date')

    xs, ys = [], []
    for i, log in enumerate(logs):
        val = getattr(log, metric_field, None)
        if val is None:
            continue
        try:
            v = float(val)
        except:
            continue
        xs.append([i])
        ys.append(v)

    if len(ys) < test_days + 3:
        return None

    X_train = np.array(xs[:-test_days])
    y_train = np.array(ys[:-test_days])
    X_test = np.array(xs[-test_days:])
    y_test = np.array(ys[-test_days:])

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = mse ** 0.5

    if plot:
        plt.figure(figsize=(8,4))
        plt.plot(range(len(y_train)), y_train, label='Train')
        plt.plot(range(len(y_train), len(y_train)+len(y_test)), y_test, label='Actual')
        plt.plot(range(len(y_train), len(y_train)+len(y_test)), y_pred, label='Predicted')
        plt.title(f'Metric Prediction: {metric_field}')
        plt.xlabel('Day Index')
        plt.ylabel(metric_field)
        plt.legend()
        # compute direction accuracy (up/down relative to last training value)
        try:
            last_train_value = float(y_train[-1])
            y_test_bin = [1 if v > last_train_value else 0 for v in y_test]
            y_pred_bin = [1 if p > last_train_value else 0 for p in y_pred]
            acc = accuracy_score(y_test_bin, y_pred_bin)
            # draw accuracy in upper-right corner of plot
            ax = plt.gca()
            ax.text(0.98, 0.95, f'Accuracy: {acc:.4f}', ha='right', va='top', transform=ax.transAxes,
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
        except Exception:
            # if any issue computing classification metrics, skip annotation
            pass
        plt.show()

    return {'r2': round(r2, 3), 'mae': round(mae, 3), 'rmse': round(rmse, 3)}


def evaluate_direction_metrics(user, metric_field, past_days=30, test_days=7):
    """Evaluate direction (up/down) classification derived from regression predictions.

    For the last `past_days + test_days` period, train on the first `past_days` and
    predict the next `test_days`. Convert predictions and ground truth to binary labels
    (1 = increase vs last training value, 0 = not increase). Compute accuracy, precision,
    recall and f1. Returns None if insufficient data.
    """
    today = timezone.now().date()
    start = today - timedelta(days=past_days + test_days)
    logs = HealthLog.objects.filter(user=user, date__gte=start).order_by('date')

    xs, ys = [], []
    for i, log in enumerate(logs):
        val = getattr(log, metric_field, None)
        if val is None:
            continue
        try:
            v = float(val)
        except:
            continue
        xs.append([i])
        ys.append(v)

    if len(ys) < test_days + 3:
        return None

    X_train = np.array(xs[:-test_days])
    y_train = np.array(ys[:-test_days])
    X_test = np.array(xs[-test_days:])
    y_test = np.array(ys[-test_days:])

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    # derive binary labels relative to last training value
    last_train_value = float(y_train[-1])
    y_test_bin = [1 if v > last_train_value else 0 for v in y_test]
    y_pred_bin = [1 if p > last_train_value else 0 for p in y_pred]

    # compute classification metrics
    acc = accuracy_score(y_test_bin, y_pred_bin)
    prec = precision_score(y_test_bin, y_pred_bin, zero_division=0)
    rec = recall_score(y_test_bin, y_pred_bin, zero_division=0)
    f1 = f1_score(y_test_bin, y_pred_bin, zero_division=0)

    return {
        'accuracy': round(float(acc), 4),
        'precision': round(float(prec), 4),
        'recall': round(float(rec), 4),
        'f1': round(float(f1), 4)
    }


def evaluate_weight_bmi(user, past_days=30, predict_days=14, plot=False):
    """
    Evaluate weight/BMI prediction against HealthLog ground truth.
    Returns MAE and RMSE.
    """
    preds = predict_weight_bmi(user, past_days=past_days, predict_days=predict_days)
    if not preds:
        return None

    today = timezone.now().date()
    logs = HealthLog.objects.filter(
        user=user,
        date__gte=today,
        date__lt=today + timedelta(days=predict_days)
    )

    actual_weights = {log.date.strftime('%m-%d'): float(log.weight) for log in logs if log.weight is not None}

    y_true, y_pred = [], []
    for date, w in zip(preds['dates'], preds['weight']):
        if date in actual_weights:
            y_true.append(actual_weights[date])
            y_pred.append(w)

    if not y_true:
        return None

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))

    if plot:
        plt.figure(figsize=(8,4))
        plt.plot(preds['dates'], y_pred, label='Predicted Weight')
        plt.plot(preds['dates'], [actual_weights.get(d, np.nan) for d in preds['dates']], label='Actual Weight')
        plt.title('Weight Prediction')
        plt.xlabel('Date')
        plt.ylabel('Weight (kg)')
        plt.legend()
        plt.show()

    return {'mae': round(mae,2), 'rmse': round(rmse,2)}


def evaluate_user(user, metrics=None, past_days=30, test_days=7, predict_days=14, plot=False):
    """
    Evaluate all metrics and weight/BMI for a user.
    Returns a dict with metric evaluations and weight/BMI evaluation.
    """
    results = {}

    # evaluate numeric metrics
    if metrics:
        results['metrics'] = {}
        for metric in metrics:
            res = evaluate_metric(user, metric, past_days=past_days, test_days=test_days, plot=plot)
            dir_res = evaluate_direction_metrics(user, metric, past_days=past_days, test_days=test_days)
            # include direction (classification) metrics alongside regression metrics
            results['metrics'][metric] = {
                'regression': res,
                'direction_classification': dir_res
            }

    # evaluate weight/BMI
    results['weight_bmi'] = evaluate_weight_bmi(user, past_days=past_days, predict_days=predict_days, plot=plot)

    return results


def evaluate_overall(user, metrics=None, past_days=30, test_days=7, predict_days=14, plot=False):
    """Aggregate performance across multiple metrics.

    Returns a summary dict with averaged regression metrics (MAE, RMSE)
    and averaged classification metrics (accuracy, precision, recall, f1).
    Only metrics with available results are included in the averages.
    """
    if metrics is None:
        metrics = ['steps', 'calories_intake', 'sleep_hours']

    reg_maes = []
    reg_rmses = []
    cls_acc = []
    cls_prec = []
    cls_rec = []
    cls_f1 = []
    counted_metrics = 0

    for metric in metrics:
        reg = evaluate_metric(user, metric, past_days=past_days, test_days=test_days, plot=False)
        cls = evaluate_direction_metrics(user, metric, past_days=past_days, test_days=test_days)

        if reg is None and cls is None:
            continue

        counted_metrics += 1

        if reg is not None:
            # reg contains 'mae' and 'rmse'
            try:
                reg_maes.append(float(reg.get('mae')))
            except Exception:
                pass
            try:
                reg_rmses.append(float(reg.get('rmse')))
            except Exception:
                pass

        if cls is not None:
            try:
                cls_acc.append(float(cls.get('accuracy')))
            except Exception:
                pass
            try:
                cls_prec.append(float(cls.get('precision')))
            except Exception:
                pass
            try:
                cls_rec.append(float(cls.get('recall')))
            except Exception:
                pass
            try:
                cls_f1.append(float(cls.get('f1')))
            except Exception:
                pass

    summary = {
        'metrics_evaluated': counted_metrics,
        'regression': None,
        'classification': None
    }

    if reg_maes or reg_rmses:
        avg_mae = round(float(sum(reg_maes) / len(reg_maes)), 4) if reg_maes else None
        avg_rmse = round(float(sum(reg_rmses) / len(reg_rmses)), 4) if reg_rmses else None
        summary['regression'] = {'avg_mae': avg_mae, 'avg_rmse': avg_rmse}

    if cls_acc or cls_prec or cls_rec or cls_f1:
        avg_acc = round(float(sum(cls_acc) / len(cls_acc)), 4) if cls_acc else None
        avg_prec = round(float(sum(cls_prec) / len(cls_prec)), 4) if cls_prec else None
        avg_rec = round(float(sum(cls_rec) / len(cls_rec)), 4) if cls_rec else None
        avg_f1 = round(float(sum(cls_f1) / len(cls_f1)), 4) if cls_f1 else None
        summary['classification'] = {
            'avg_accuracy': avg_acc,
            'avg_precision': avg_prec,
            'avg_recall': avg_rec,
            'avg_f1': avg_f1
        }

    return summary


def plot_overall(summary, out_path=None):
    """Create and save a bar chart summarizing overall performance.

    - Left: regression averages (MAE, RMSE)
    - Right: classification averages (accuracy, precision, recall, f1)

    Returns the path to the saved PNG file or None if plotting failed or summary empty.
    """
    if not summary:
        return None

    metrics_evaluated = summary.get('metrics_evaluated', 0)
    reg = summary.get('regression') or {}
    cls = summary.get('classification') or {}

    # prepare values
    reg_names = []
    reg_vals = []
    if reg.get('avg_mae') is not None:
        reg_names.append('MAE')
        reg_vals.append(float(reg.get('avg_mae')))
    if reg.get('avg_rmse') is not None:
        reg_names.append('RMSE')
        reg_vals.append(float(reg.get('avg_rmse')))

    cls_names = []
    cls_vals = []
    if cls.get('avg_accuracy') is not None:
        cls_names.append('Accuracy')
        cls_vals.append(float(cls.get('avg_accuracy')))
    if cls.get('avg_precision') is not None:
        cls_names.append('Precision')
        cls_vals.append(float(cls.get('avg_precision')))
    if cls.get('avg_recall') is not None:
        cls_names.append('Recall')
        cls_vals.append(float(cls.get('avg_recall')))
    if cls.get('avg_f1') is not None:
        cls_names.append('F1')
        cls_vals.append(float(cls.get('avg_f1')))

    if not reg_names and not cls_names:
        return None

    try:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        # regression
        if reg_names:
            axes[0].bar(reg_names, reg_vals, color=['#4c72b0', '#55a868'][:len(reg_names)])
            axes[0].set_title('Average Regression Errors')
            axes[0].set_ylabel('Error')
        else:
            axes[0].text(0.5, 0.5, 'No regression data', ha='center', va='center')
            axes[0].axis('off')

        # classification
        if cls_names:
            # multiply classification decimals by 100 to show percentages
            axes[1].bar(cls_names, [v * 100.0 for v in cls_vals], color=['#c44e52', '#8172b2', '#ccb974', '#64b5cd'][:len(cls_names)])
            axes[1].set_title('Average Classification Metrics (%)')
            axes[1].set_ylabel('Percent')
        else:
            axes[1].text(0.5, 0.5, 'No classification data', ha='center', va='center')
            axes[1].axis('off')

        fig.suptitle(f'Overall Model Performance (metrics evaluated: {metrics_evaluated})')

        if out_path is None:
            out_path = os.path.join(os.getcwd(), 'overall_performance.png')

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        fig.savefig(out_path)
        plt.close(fig)
        return out_path
    except Exception:
        return None
