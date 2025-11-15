# admin_area/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_area'),
    path('users/', views.user_list, name='aa_user_list'),
    path('reports/', views.reports_overview, name='aa_reports'),

    path('vendors/', views.vendors_view, name='vendors_view'),
    path('vendors/upload/', views.vendors_upload, name='vendors_upload'),  # <-- must exist

    path('items/', views.items_view, name='items_view'),
    path('items/upload/', views.items_upload, name='items_upload'),

    path("forwarders/", views.forwarders_view, name="forwarders_view"),
    path("forwarders/export/", views.forwarders_export, name="forwarders_export"),
    path("forwarders/<int:pk>/edit/", views.forwarder_edit, name="forwarder_edit"),
    path("forwarders/upload/", views.forwarders_upload, name="forwarders_upload"),
    path("forwarders/<int:pk>/delete/", views.forwarder_delete, name="forwarder_delete"),

]