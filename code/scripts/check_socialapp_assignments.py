import os, sys
proj_root = r'C:\lifetrack'
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lifetrack.settings')
import django
django.setup()
from django.conf import settings
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
print('SITE_ID=', settings.SITE_ID)
print('Sites:', list(Site.objects.values_list('id','domain')))
apps=SocialApp.objects.filter(provider='google')
print('SocialApps count:', apps.count())
for a in apps:
    print('SocialApp', a.id, a.name, 'assigned_sites:', list(a.sites.values_list('id','domain')))
print('Exists for site domain 127.0.0.1:8000:', SocialApp.objects.filter(provider='google', sites__domain='127.0.0.1:8000').exists())
print('Exists for site domain localhost:8000:', SocialApp.objects.filter(provider='google', sites__domain='localhost:8000').exists())
