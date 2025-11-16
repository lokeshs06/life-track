import os, sys
proj_root = r'C:\lifetrack'
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lifetrack.settings')
import django
django.setup()
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

print('Before:')
for s in Site.objects.all():
    print('Site id=', s.id, 'domain=', repr(s.domain), 'name=', repr(s.name))

# Normalize site domains by stripping scheme and trailing slash
for s in Site.objects.all():
    domain = s.domain.strip()
    if domain.startswith('http://') or domain.startswith('https://'):
        # remove scheme
        domain = domain.split('://', 1)[1]
    # remove trailing slash
    domain = domain.rstrip('/')
    if domain != s.domain:
        print(f'Updating Site id={s.id} from {s.domain!r} to {domain!r}')
        s.domain = domain
        s.name = domain
        s.save()

# Ensure at least localhost:8000 and 127.0.0.1:8000 exist as site entries
required = ['localhost:8000','127.0.0.1:8000']
for d in required:
    if not Site.objects.filter(domain=d).exists():
        new = Site(domain=d, name=d)
        new.save()
        print('Created Site:', new.id, new.domain)

# Normalize SocialApp site assignments
apps = SocialApp.objects.filter(provider='google')
for a in apps:
    print('SocialApp:', a.name, 'client_id=', a.client_id)
    current_sites = list(a.sites.all())
    print('  current assigned sites:', [s.domain for s in current_sites])
    # Build desired site objects
    desired_sites = []
    for d in required:
        s_obj = Site.objects.get(domain=d)
        desired_sites.append(s_obj)
    # assign both sites
    a.sites.set(desired_sites)
    a.save()
    print('  new assigned sites:', [s.domain for s in a.sites.all()])

print('After:')
for s in Site.objects.all():
    print('Site id=', s.id, 'domain=', repr(s.domain), 'name=', repr(s.name))

print('Done')
