import os
import sys
# ensure project root is on PYTHONPATH
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE','lifetrack.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from lifeapp.evaluate_prediction import evaluate_overall, plot_overall

User = get_user_model()
u = User.objects.first()
if not u:
    print('No user found')
    raise SystemExit(1)

summary = evaluate_overall(u)
print('Summary:', summary)
out = plot_overall(summary, out_path=os.path.abspath('overall_performance.png'))
print('Saved:', out)
print('Exists:', os.path.exists(out) if out else False)
