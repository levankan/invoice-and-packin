# core/views/__init__.py

# Authentication
from .login_view import login_view
from .logout_view import logout_view

# Home & Tracking
from .home_view import home_view, tracking_view

# Exports
from .export_views import exports_view, edit_export, delete_export

# Document generation
from .generate_doc_view import generate_doc_view
from .invoice_view import invoice_view

# PDF rendering
from .pdf_views import (
    invoice_pdf_view,
    packing_list_pdf_view,
    invoice_pdf_per_pallet_view,       # ✅ NEW
    packing_list_pdf_per_pallet_view,  # ✅ NEW
)
