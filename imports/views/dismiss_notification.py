# imports/views/dismiss_notification.py

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from ..models import GlobalNotification

@require_POST
@login_required
def dismiss_notification(request, pk):
    n = get_object_or_404(GlobalNotification, pk=pk)
    n.dismissed_by.add(request.user)
    return redirect(request.META.get("HTTP_REFERER", "/imports/"))