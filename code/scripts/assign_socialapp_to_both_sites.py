import os, sys
proj_root = r'C:\lifetrack'
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lifetrack.settings')
import django
django.setup()
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

# domains to ensure
domains = ['127.0.0.1:8000', 'localhost:8000']

apps = SocialApp.objects.filter(provider='google')
if not apps.exists():
    print('No SocialApp with provider=google found; please create one in admin with client id/secret.')
else:
    app = apps.first()
    print('Found SocialApp:', app.name, 'current sites:', [s.domain for s in app.sites.all()])
    for d in domains:
        try:
            site = Site.objects.get(domain=d)
        except Site.DoesNotExist:
            site = Site.objects.create(domain=d, name=d)
            print('Created site', d)
        if site not in app.sites.all():
            app.sites.add(site)
            print('Added site', d, 'to SocialApp')
        else:
            print('Site', d, 'already assigned')
    print('Final assigned sites:', [s.domain for s in app.sites.all()])
