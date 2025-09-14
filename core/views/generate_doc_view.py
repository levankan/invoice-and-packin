import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from core.models import Export, LineItem

EXPECTED_HEADERS = [
    "Serial/Lot Number","Document Number","Item Number","Cross Reference #",
    "QTY","Unit of Measure","Box #","Commercial Invoice #","Posting Date",
    "Shipment #","Description","Carbon QTY","Carbon LOT","Customer PO",
    "PO Line","Sales Order","Sales Order Line","Pallet #","Price","LU"
]

@login_required
def generate_doc_view(request):
    seller_info = {
        "name": "Aero-Structure Technologies (Cyclone) JSC",
        "id": "404496121",
        "address": "Mikheil Grigorashvili 27, 0198, Samgori District, Tbilisi, Georgia",
        "origin": "Georgia",
    }

    sold_to_list = [
        {"name": "Spirit AeroSystems, Inc.", "country": "USA"},
        {"name": "Qarbon Aerospace", "country": "USA"},
        {"name": "Elbit Systems Cyclone", "country": "Israel"},
    ]

    shipped_to_list = [
        {"name": "Spirit AeroSystems Receiving Dock", "country": "USA"},
        {"name": "Qarbon Aerospace Facility", "country": "USA"},
        {"name": "Elbit Systems Warehouse", "country": "Israel"},
    ]

    project_list = ["D638", "D640", "D735", "D632", "D640-634", "OPF", "NWD"]

    if request.method == "POST":
        sold_to = request.POST.get("sold_to")
        shipped_to = request.POST.get("shipped_to")
        project = request.POST.get("project")
        file = request.FILES.get("excel_file")

        if not file:
            messages.error(request, "⚠ Please upload an Excel file.")
            return redirect("generate_doc")

        # Read Excel
        try:
            df = pd.read_excel(file)
        except Exception:
            messages.error(request, "⚠ Could not read Excel file. Make sure it's .xlsx or .xls")
            return redirect("generate_doc")

        # Validate headers
        if list(df.columns) != EXPECTED_HEADERS:
            messages.error(request, "⚠ Headers do not match expected format.")
            return redirect("generate_doc")

        # Check duplicates
        if df["Serial/Lot Number"].duplicated().any():
            messages.error(request, "⚠ Serial number is duplicated.")
            return redirect("generate_doc")

        # Create Export (auto generates EXP, Invoice, and Packing List numbers)
        export = Export.objects.create(
            seller=seller_info["name"],
            sold_to=sold_to,
            shipped_to=shipped_to,
            project_no=project,
        )

        # Save LineItems
        for _, row in df.iterrows():
            LineItem.objects.create(
                export=export,
                serial_lot_number=row["Serial/Lot Number"],
                document_number=row["Document Number"],
                item_number=row["Item Number"],
                cross_reference=row["Cross Reference #"],
                qty=row["QTY"],
                unit_of_measure=row["Unit of Measure"],
                box_number=row["Box #"],
                commercial_invoice_number=row["Commercial Invoice #"],
                posting_date=row["Posting Date"],
                shipment_number=row["Shipment #"],
                description=row["Description"],
                carbon_qty=row["Carbon QTY"],
                carbon_lot=row["Carbon LOT"],
                customer_po=row["Customer PO"],
                po_line=row["PO Line"],
                sales_order=row["Sales Order"],
                sales_order_line=row["Sales Order Line"],
                pallet_number=row["Pallet #"],
                price=row["Price"],
                lu=row["LU"],
            )

        return render(request, "core/export_success.html", {
            "export": export,
            "rows": len(df)
        })

    return render(request, "core/generate_doc.html", {
        "seller": seller_info,
        "sold_to_list": sold_to_list,
        "shipped_to_list": shipped_to_list,
        "project_list": project_list,
    })
