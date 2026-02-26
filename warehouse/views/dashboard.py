from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q
from imports.models import Import, ImportLine


@login_required
def dashboard(request):
    query = None
    results = None
    lines = None

    if request.method == "POST":
        query = request.POST.get("tracking_number", "").strip()

        if query:
            # 🔥 Remove spaces just in case
            query = query.replace(" ", "")

            # 🔥 If starts with 20010 and does NOT contain "/", add it
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

            if results.exists():
                lines = ImportLine.objects.filter(
                    import_header__in=results
                )

    return render(request, "warehouse/dashboard.html", {
        "query": query,
        "results": results,
        "lines": lines,
    })