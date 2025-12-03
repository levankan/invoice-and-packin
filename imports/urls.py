# imports/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.imports_dashboard, name="imports_home"),
    path("register/", views.register_import, name="imports_register"),
    path("export/", views.export_imports_excel, name="imports_export"),

    # Edit / Delete per row
    path("<int:pk>/edit/", views.edit_import, name="imports_edit"),
    path("<int:pk>/delete/", views.delete_import, name="imports_delete"),
    path("<int:pk>/upload-lines/", views.upload_import_lines, name="imports_upload_lines"),
    path(
        "exports/import-lines/",
        views.export_import_lines_excel,
        name="imports_export_lines_excel",
    ),

    path(
        "<int:import_id>/excel/",
        views.export_single_import_excel,
        name="import_single_excel",
    ),
]
