from django.urls import path
from . import views
from stats.views.cost_export import export_cost_analysis_excel
from stats.views.fallback_cost_export import export_fallback_cost_analysis_excel

app_name = 'stats'

urlpatterns = [
    path('', views.main, name='main'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('cost/', views.cost_analysis, name='cost'),
    path("cost/export/", export_cost_analysis_excel, name="cost_export"),
    path("cost/fallback-export/", export_fallback_cost_analysis_excel, name="fallback_cost_export"),
]