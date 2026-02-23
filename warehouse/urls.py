#warehouse/urls.py
from django.urls import path
from . import views

app_name = "warehouse"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("download-excel/", views.download_excel, name="download_excel"),
]