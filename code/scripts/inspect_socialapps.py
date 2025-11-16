import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lifetrack.settings')
import django
django.setup()
from django.conf import settings
from django.contrib.sites.models import Site
out = []
out.append('DJANGO SETTINGS MODULE: ' + str(os.environ.get('DJANGO_SETTINGS_MODULE')))
try:
    s = Site.objects.get(id=settings.SITE_ID)
    out.append('Site ID: ' + str(settings.SITE_ID))
    out.append('Site domain: ' + str(s.domain))
    out.append('Site name: ' + str(s.name))
except Exception as e:
    print('Could not get Site:', repr(e))

try:
    from allauth.socialaccount.models import SocialApp
    apps = list(SocialApp.objects.filter(provider='google'))
    out.append('Google SocialApp count: ' + str(len(apps)))
    for a in apps:
        out.append('---')
        out.append('Name: ' + str(a.name))
        out.append('Client id: ' + str(a.client_id))
        out.append('Secret present: ' + str(bool(a.secret)))
        out.append('Assigned sites: ' + str([site.domain for site in a.sites.all()]))
except Exception as e:
    out.append('Could not inspect SocialApp: ' + repr(e))

with open(r'c:\lifetrack\scripts\inspect_socialapps_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
