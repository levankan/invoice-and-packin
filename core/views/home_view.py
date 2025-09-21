#home_view.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def home_view(request):
    return render(request, 'core/home.html', {'user': request.user})



@login_required
def tracking_view(request):
    return render(request, 'core/tracking.html')
