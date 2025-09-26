from django.urls import path
from core.views.export_views import export_detail
from core.views.pdf_views import pallet_label_pdf_view

from core.views import (
    login_view,
    home_view,
    tracking_view,
    logout_view,
    generate_doc_view,
    invoice_view,
    invoice_pdf_view,
    packing_list_pdf_view,
    invoice_pdf_per_pallet_view,
    packing_list_pdf_per_pallet_view,
    download_export_template,

    # exports (from export_views.py)
    exports_view,
    edit_export,
    delete_export,
    export_database_excel,
)

urlpatterns = [
    path('', login_view, name='login'),
    path('home/', home_view, name='home'),
    path('logout/', logout_view, name='logout'),

    # Exports
    path('exports/', exports_view, name='exports_view'),
    path('exports/<int:export_id>/edit/', edit_export, name='edit_export'),
    path('exports/<int:export_id>/delete/', delete_export, name='delete_export'),
    path("exports/template/download/", download_export_template, name="download_export_template"),
    path("exports/database/download/", export_database_excel, name="export_database_excel"),
    path("exports/<int:export_id>/", export_detail, name="export_detail"),

    path('tracking/', tracking_view, name='tracking'),
    path('generate-doc/', generate_doc_view, name='generate_doc'),

    # Invoice & Packing List
    path('invoice/<int:export_id>/', invoice_view, name='invoice'),
    path("invoice/<int:export_id>/pdf/", invoice_pdf_view, name="invoice_pdf"),
    path("packing-list/<int:export_id>/pdf/", packing_list_pdf_view, name="packing_list_pdf"),
    path("invoice/<int:export_id>/pallet/<int:pallet_id>/pdf/", invoice_pdf_per_pallet_view, name="invoice_pdf_per_pallet"),
    path("packing-list/<int:export_id>/pallet/<int:pallet_id>/pdf/", packing_list_pdf_per_pallet_view, name="packing_list_pdf_per_pallet"),
    path("pallet-label/<int:export_id>/<int:pallet_id>/pdf/", pallet_label_pdf_view, name="pallet_label_pdf"),

]
