from django.urls import path
from core.views import (
    login_view, home_view, logout_view, 
    exports_view, tracking_view, generate_doc_view,
    invoice_view   # ✅ make sure this is imported
)


urlpatterns = [
    path('', login_view, name='login'),
    path('home/', home_view, name='home'),
    path('logout/', logout_view, name='logout'),
    path('exports/', exports_view, name='exports'),
    path('tracking/', tracking_view, name='tracking'),
    path('generate-doc/', generate_doc_view, name='generate_doc'),
    path('invoice/<int:export_id>/', invoice_view, name='invoice'),   # ✅ new
]
