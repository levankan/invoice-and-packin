from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


@login_required
@require_POST
def logout_view(request):
    """
    Secure logout:
    - POST-only (prevents forced logouts)
    - CSRF-protected
    - Only for authenticated users
    """
    logout(request)
    return redirect("login")
