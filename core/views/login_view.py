# views.py (core)
from __future__ import annotations

from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    """
    Secure, production-ready login view:
    - Uses Django's AuthenticationForm
    - Supports ?next=... (GET) and hidden next (POST)
    - Prevents open redirects (host validation)
    - Redirects already-authenticated users away from login page
    """

    # If user is already logged in, don't show login page again
    if request.user.is_authenticated:
        return redirect("home")

    # Grab next from GET or POST
    next_url = request.POST.get("next") or request.GET.get("next")

    # Build a safe fallback URL (named URL -> absolute path)
    fallback_url = reverse("home")

    # Validate next_url to prevent open redirect vulnerabilities
    if not (
        next_url
        and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
    ):
        next_url = fallback_url

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(next_url)  # safe by validation above
        # else: form carries errors to template
    else:
        form = AuthenticationForm(request)

    return render(request, "core/login.html", {"form": form, "next": next_url})
