# imports/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.imports_dashboard, name='imports_home'),
]
