from django.shortcuts import render

# Create your views here.
# imports/views.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

ALLOWED_ROLES = {'logistics', 'procurement', 'Other Employee'}

def has_imports_access(user):
    # adapt if your user model stores role differently (e.g., user.role or user.profile.role)
    if getattr(user, 'is_superuser', False):
        return True
    role = getattr(user, 'role', None)
    return role in ALLOWED_ROLES

@login_required
@user_passes_test(has_imports_access)
def imports_dashboard(request):
    return render(request, 'imports/dashboard.html')
