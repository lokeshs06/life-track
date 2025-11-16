import os
import sys
proj_root = r'C:\lifetrack'
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lifetrack.settings')
import django
django.setup()
from django.contrib.sites.models import Site
print('All Site records:')
for s in Site.objects.all():
    print(f'id={s.id!s} domain={s.domain!s} name={s.name!s}')
