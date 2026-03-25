from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


@login_required
def logout_view(request):
    request.session.pop("is_2fa_verified", None)
    request.session.pop("after_2fa_redirect", None)
    logout(request)
    return redirect("login")
