from __future__ import annotations

import base64
from io import BytesIO

import pyotp
import qrcode

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated and request.session.get("is_2fa_verified", False):
        return redirect("home")

    next_url = request.POST.get("next") or request.GET.get("next")
    fallback_url = reverse("home")

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
            user = form.get_user()
            login(request, user)

            # reset every fresh login
            request.session["is_2fa_verified"] = False
            request.session["after_2fa_redirect"] = next_url

            if user.two_factor_enabled:
                return redirect("verify_2fa")

            request.session["is_2fa_verified"] = True
            return redirect(next_url)
    else:
        form = AuthenticationForm(request)

    return render(request, "core/login.html", {"form": form, "next": next_url})


@login_required
def setup_2fa(request):
    user = request.user

    if not user.two_factor_secret:
        user.two_factor_secret = pyotp.random_base32()
        user.save(update_fields=["two_factor_secret"])

    totp = pyotp.TOTP(user.two_factor_secret)
    otp_uri = totp.provisioning_uri(
        name=user.username,
        issuer_name="Shipment System"
    )

    qr = qrcode.make(otp_uri)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    if request.method == "POST":
        code = request.POST.get("code", "").strip()

        if totp.verify(code):
            user.two_factor_enabled = True
            user.save(update_fields=["two_factor_enabled"])
            request.session["is_2fa_verified"] = True
            messages.success(request, "Two-factor authentication enabled successfully.")
            return redirect("home")
        else:
            messages.error(request, "Invalid code. Please try again.")

    return render(request, "core/setup_2fa.html", {
        "qr_base64": qr_base64,
    })


@login_required
def verify_2fa(request):
    user = request.user

    if not user.two_factor_enabled or not user.two_factor_secret:
        request.session["is_2fa_verified"] = True
        return redirect("home")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        totp = pyotp.TOTP(user.two_factor_secret)

        if totp.verify(code):
            request.session["is_2fa_verified"] = True
            next_url = request.session.get("after_2fa_redirect") or reverse("home")
            return redirect(next_url)

        messages.error(request, "Invalid authentication code.")

    return render(request, "core/verify_2fa.html")