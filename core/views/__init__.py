# core/views/__init__.py

from .login_view import login_view
from .home_view import home_view, exports_view, tracking_view
from .logout_view import logout_view
from .generate_doc_view import generate_doc_view
from .invoice_view import invoice_view
from .pdf_views import (
    invoice_pdf_view,
    packing_list_pdf_view,
    invoice_pdf_per_pallet_view,       # ✅ NEW
    packing_list_pdf_per_pallet_view,  # ✅ NEW
)
