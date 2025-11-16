import os
import sys

# ensure project root is on PYTHONPATH so "import lifeapp" works when running this script
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
	sys.path.insert(0, ROOT)

# configure Django settings and initialize
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lifetrack.settings')
try:
	import django
	django.setup()
except Exception:
	# if django isn't available or setup fails, raise a clearer error
	raise

from django.contrib.auth import get_user_model
from lifeapp.evaluate_prediction import evaluate_user, evaluate_overall, plot_overall

User = get_user_model()
user = User.objects.first()  # pick the first user, or filter by username/email
metrics = ['steps', 'calories_intake', 'sleep_hours']

results = evaluate_user(user, metrics=metrics, plot=True)
print('Per-metric results:')
print(results)

overall = evaluate_overall(user, metrics=metrics, past_days=30, test_days=7, predict_days=14)
print('\nOverall aggregated performance:')
print(overall)
if overall:
	out = plot_overall(overall)
	if out:
		print(f'Overall performance plot saved to: {out}')
	else:
		print('Could not generate overall performance plot.')
