from django.shortcuts import redirect
from django.urls import reverse


class TwoFactorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        if user.is_authenticated:
            allowed_paths = {
                reverse("login"),
                reverse("logout"),
                reverse("setup_2fa"),
                reverse("verify_2fa"),
            }

            # allow admin if needed, and static/media paths
            if (
                request.path not in allowed_paths
                #and not request.path.startswith("/admin/")
                and not request.path.startswith("/static/")
                and not request.path.startswith("/media/")
            ):
                if user.two_factor_enabled and not request.session.get("is_2fa_verified", False):
                    return redirect("verify_2fa")

        response = self.get_response(request)
        return response