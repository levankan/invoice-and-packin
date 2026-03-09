from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.contrib import messages

from imports.models import Import, ImportLine, GlobalNotification

# 📧 Import email sender
from warehouse.services.email_service import send_delivery_email


@login_required
def dashboard(request):
    query = None
    results = None
    lines = None

    if request.method == "POST":
        query = request.POST.get("tracking_number", "").strip()

        if query:
            query = query.replace(" ", "")

            # normalize declaration C format: 20010/xxxx
            if query.startswith("20010") and "/" not in query:
                query = f"20010/{query[5:]}"

            results = Import.objects.filter(
                Q(import_code__icontains=query) |
                Q(tracking_no__icontains=query) |
                Q(vendor_reference__icontains=query) |
                Q(forwarder_reference__icontains=query) |
                Q(declaration_c_number__icontains=query) |
                Q(declaration_a_number__icontains=query)
            ).distinct()

            # Auto-mark Delivered if exactly one match
            if results.count() >= 1:
                imp = results.first()

                with transaction.atomic():
                    if getattr(imp, "shipment_status", None) != "DELIVERED":
                        imp.shipment_status = "DELIVERED"

                        if hasattr(imp, "received_at"):
                            imp.received_at = timezone.now()
                        if hasattr(imp, "received_by"):
                            imp.received_by = request.user

                        imp.save()

                        try:
                            send_delivery_email(imp)
                        except Exception as e:
                            print("Email sending failed:", e)

                        # Global notification
                        GlobalNotification.objects.create(
                            level="success",
                            message=f"✅ Status updated to Delivered (Import: {imp.import_code})",
                            created_by=request.user,
                            import_ref=imp,
                            is_active=True,
                        )

                        messages.success(
                            request,
                            f"Status updated to Delivered (Import: {imp.import_code})",
                            extra_tags="from_warehouse"
                        )

            if results.exists():
                lines = ImportLine.objects.filter(import_header__in=results)

    return render(request, "warehouse/dashboard.html", {
        "query": query,
        "results": results,
        "lines": lines,
    })