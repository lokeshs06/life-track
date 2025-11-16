import os
import sys
# ensure project root is on sys.path
proj_root = r'C:\lifetrack'
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lifetrack.settings')
import django
try:
    django.setup()
    from django.conf import settings
    from django.contrib.sites.models import Site
    s = Site.objects.get(id=settings.SITE_ID)
    print('SITE_ID=', settings.SITE_ID)
    print('Site:', s.id, s.domain, s.name)
    from allauth.socialaccount.models import SocialApp
    apps = SocialApp.objects.filter(provider='google')
    print('Google SocialApp count:', apps.count())
    for a in apps:
        print('---')
        print('Name:', a.name)
        print('Client id:', a.client_id)
        print('Secret present:', bool(a.secret))
        print('Assigned sites:', [site.domain for site in a.sites.all()])
except Exception as e:
    print('ERROR:', repr(e))
