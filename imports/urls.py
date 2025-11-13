from django.urls import path
from . import views

urlpatterns = [
    path("", views.imports_dashboard, name="imports_home"),
    path("register/", views.register_import, name="imports_register"),
    path("export/", views.export_imports_excel, name="imports_export"),  # <-- NEW
]
