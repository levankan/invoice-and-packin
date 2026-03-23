#stats/urls.py

from django.urls import path
from . import views

app_name = 'stats'

urlpatterns = [
    path('', views.main, name='main'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('cost/', views.cost_analysis, name='cost'),
]