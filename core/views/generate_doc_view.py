import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from core.models import Export, LineItem, Pallet
from decimal import Decimal
from django.db.models import Q  # keep unused as you requested


EXPECTED_HEADERS = [
    "Serial/Lot Number", "Document Number", "Item Number", "Cross Reference #",
    "QTY", "Unit of Measure", "Box #", "Commercial Invoice #", "Posting Date",
    "Shipment #", "Description", "Carbon QTY", "Carbon LOT", "Customer PO",
    "PO Line", "Sales Order", "Sales Order Line", "Pallet #", "Price", "LU"
]

EXPECTED_PALLET_HEADERS = [
    "Pallet #", "Lenght (Cm)", "Width (Cm)", "Height (Cm)", "Gross Weight (Kg)"
]


def _is_blank(val) -> bool:
    """Treat NaN / None / '' / 'nan' as blank."""
    if val is None:
        return True
    if pd.isna(val):
        return True
    if isinstance(val, str) and val.strip().lower() in ("", "nan", "none"):
        return True
    return False


@login_required
def generate_doc_view(request):
    seller_info = {
        "name": "Aero-Structure Technologies (Cyclone) JSC",
        "id": "404496121",
        "address": "Mikheil Grigorashvili 27, 0198, Samgori District, Tbilisi, Georgia",
        "origin": "Georgia",
    }

    sold_to_options = {
        "elbit": {
            "name": "Elbit Systems Cyclone",
            "id": "520033374",
            "address_lines": [
                "Industrial Park Bar-Lev, P.O.B 114,",
                "Karmiel, Israel",
            ],
            "terms": "Terms of Payment: 30D",
        },
        "elmec": {
            "name": "Elmec INC.",
            "id": "043548482",
            "address_lines": [
                "9004 Sightline Drive, Ladson ,SC,",
                "29456 USA SUITE N",
            ],
            "terms": "Terms of Payment: 30D",
        },
    }

    shipped_to_list = [
        {
            "name": "SPIRIT AEROSYSTEMS, INC.",
            "address": "4555 E MacArthur Rd BLDG 3-213H, Wichita, KS 67210, United States",
            "incoterms": "Incoterms 2010: EXW Tbilisi",
        },
        {
            "name": "Qarbon Aerospace (Lafayette), LLC",
            "address": "90 Hwy 22 West, Milledgeville, GA 31061-9600, United States",
            "incoterms": "Incoterms 2010: EXW Tbilisi",
        },
        {
            "name": "Boeing 787 / GXO Logistics",
            "address": "7405 Magi Rd, Hanahan, SC 29410, United States",
            "incoterms": "Incoterms 2010: EXW Tbilisi",
        },
        {
            "name": "Boeing FSCA WHSE X28",
            "address": "348 Millenium Drive, BLDG 88-998, Orangburg, SC 29115, United States",
            "incoterms": "Incoterms 2010: EXW Tbilisi",
        },
        {
            "name": "GKN AEROSPACE",
            "address": "348 Millenium Dr, Orangeburg, SC 29115, United States",
            "incoterms": "Incoterms 2010: EXW Tbilisi",
        },
        {
            "name": "Elbit Systems Cyclone",
            "address": "Industrial Park Bar-Lev, P.O.B 114, Karmiel, Israel",
            "id": "520033374",
            "incoterms": "Incoterms 2010: EXW Tbilisi",
        },
        {
            "name": "Elmec INC.",
            "address": "9004 Sightline Drive SUITE N, Ladson ,SC, 29456, USA ",
            "incoterms": "Incoterms 2010: DDP",
        },
    ]

    project_list = ["D638", "D640", "D735", "D632", "D640-634", "D664", "NWD"]

    if request.method == "POST":
        shipped_to_name = request.POST.get("shipped_to")
        project = request.POST.get("project")
        file = request.FILES.get("excel_file")

        sold_to_key = request.POST.get("sold_to")
        soldto = sold_to_options.get(sold_to_key)

        if not soldto:
            messages.error(request, "⚠ Invalid 'Sold To' selection.")
            return redirect("generate_doc")

        # Build Sold To block
        sold_to_lines = [
            soldto["name"],
            f"ID: {soldto['id']}",
        ]
        for line in soldto["address_lines"]:
            sold_to_lines.append(line)
        if soldto.get("terms"):
            sold_to_lines.append(soldto["terms"])

        sold_to_block = "\n".join(sold_to_lines)

        if not file:
            messages.error(request, "⚠ Please upload an Excel file.")
            return redirect("generate_doc")

        try:
            xls = pd.ExcelFile(file)
        except Exception:
            messages.error(request, "⚠ Could not read Excel file. Make sure it's .xlsx or .xls")
            return redirect("generate_doc")

        # -------------------------
        # Sheet1 validation
        # -------------------------
        if "Sheet1" not in xls.sheet_names:
            messages.error(request, "⚠ Missing Sheet1 for items.")
            return redirect("generate_doc")

        df = pd.read_excel(xls, sheet_name="Sheet1")

        if list(df.columns) != EXPECTED_HEADERS:
            messages.error(request, "⚠ Sheet1 headers do not match expected format.")
            return redirect("generate_doc")

        if df["Serial/Lot Number"].duplicated().any():
            messages.error(request, "⚠ Serial number is duplicated in Sheet1.")
            return redirect("generate_doc")

        existing_serials = set(
            LineItem.objects.filter(
                serial_lot_number__in=df["Serial/Lot Number"].dropna().tolist()
            ).values_list("serial_lot_number", flat=True)
        )
        if existing_serials:
            messages.error(
                request,
                f"⚠ These serial numbers already exist in the database: {', '.join(existing_serials)}"
            )
            return redirect("generate_doc")

        # ✅ Sheet1: Box/Pallet validation
        if "Box #" not in df.columns or "Pallet #" not in df.columns:
            messages.error(request, "⚠ Sheet1 must contain both 'Box #' and 'Pallet #' columns.")
            return redirect("generate_doc")

        box = df["Box #"].astype(str).fillna("").str.strip().replace({"nan": ""})
        pallet = df["Pallet #"].astype(str).fillna("").str.strip().replace({"nan": ""})

        empty_boxes = box == ""
        if empty_boxes.any():
            rows = (empty_boxes[empty_boxes].index + 2)[:10]  # Excel row numbers (header=1)
            messages.error(
                request,
                f"⚠ Some rows have empty 'Box #' values (rows: {', '.join(map(str, rows))})."
            )
            return redirect("generate_doc")

        empty_pallets = pallet == ""
        if empty_pallets.any():
            rows = (empty_pallets[empty_pallets].index + 2)[:10]
            messages.error(
                request,
                f"⚠ Some rows have empty 'Pallet #' values (rows: {', '.join(map(str, rows))})."
            )
            return redirect("generate_doc")

        # Box # cannot belong to multiple pallets
        valid = (box != "") & (pallet != "")
        box_pallet_counts = df.loc[valid].groupby(box[valid])["Pallet #"].nunique()
        bad_boxes = box_pallet_counts[box_pallet_counts > 1].index.tolist()

        if bad_boxes:
            conflicts = (
                df.loc[valid & box.isin(bad_boxes), ["Box #", "Pallet #"]]
                .groupby("Box #")["Pallet #"]
                .unique()
                .to_dict()
            )
            msg = ", ".join(f"{b}: {', '.join(map(str, v))}" for b, v in conflicts.items())
            messages.error(request, f"⚠ Box numbers on multiple pallets: {msg}")
            return redirect("generate_doc")

        # -------------------------
        # Sheet2 validation
        # -------------------------
        if "Sheet2" not in xls.sheet_names:
            messages.error(request, "⚠ Missing Sheet2 with pallet information. Please add pallet data.")
            return redirect("generate_doc")

        df2 = pd.read_excel(xls, sheet_name="Sheet2")

        if df2.empty:
            messages.error(request, "⚠ Sheet2 (pallet information) is empty. Please provide pallet rows.")
            return redirect("generate_doc")

        if list(df2.columns) != EXPECTED_PALLET_HEADERS:
            messages.error(
                request,
                "⚠ Sheet2 headers do not match expected pallet format. Please use the correct pallet headers."
            )
            return redirect("generate_doc")

        # ✅ Normalize pallet numbers
        df2_pallet = df2["Pallet #"].astype(str).fillna("").str.strip().replace({"nan": ""})

        # ✅ Pallet # must not be empty
        empty_pallet_no = df2_pallet == ""
        if empty_pallet_no.any():
            rows = (empty_pallet_no[empty_pallet_no].index + 2)[:10]
            messages.error(
                request,
                f"⚠ Some rows in Sheet2 have empty 'Pallet #' values (rows: {', '.join(map(str, rows))})."
            )
            return redirect("generate_doc")

        # ✅ Pallet # in Sheet2 must be unique
        dup_mask = df2_pallet.duplicated(keep=False)
        if dup_mask.any():
            dup_vals = df2_pallet[dup_mask].unique().tolist()
            messages.error(
                request,
                f"⚠ Duplicate 'Pallet #' values in Sheet2: {', '.join(map(str, dup_vals))}. Each pallet must appear only once."
            )
            return redirect("generate_doc")

        # ✅ Validate pallet dimensions/weight not empty + must be numeric
        required_cols = ["Lenght (Cm)", "Width (Cm)", "Height (Cm)", "Gross Weight (Kg)"]

        # blank check
        blank_rows = []
        for idx, row in df2.iterrows():
            pallet_no = str(row.get("Pallet #", "")).strip()
            for col in required_cols:
                if _is_blank(row.get(col)):
                    blank_rows.append(idx)
                    break

        if blank_rows:
            rows = [str(i + 2) for i in blank_rows[:10]]
            messages.error(
                request,
                f"⚠ Sheet2 has missing pallet dimensions/weight for some rows (rows: {', '.join(rows)}). "
                "Please fill Lenght/Width/Height/Gross Weight for every pallet."
            )
            return redirect("generate_doc")

        # numeric check (coerce)
        for col in required_cols:
            tmp = pd.to_numeric(df2[col], errors="coerce")
            bad = tmp.isna()
            if bad.any():
                rows = (bad[bad].index + 2)[:10]
                messages.error(
                    request,
                    f"⚠ Sheet2 column '{col}' contains non-numeric values (rows: {', '.join(map(str, rows))})."
                )
                return redirect("generate_doc")

            # optional: disallow <= 0
            non_positive = tmp <= 0
            if non_positive.any():
                rows = (non_positive[non_positive].index + 2)[:10]
                messages.error(
                    request,
                    f"⚠ Sheet2 column '{col}' must be > 0 (rows: {', '.join(map(str, rows))})."
                )
                return redirect("generate_doc")

        # Ensure pallets referenced in Sheet1 exist in Sheet2
        pallets_in_lines = set(pallet.dropna().astype(str).str.strip().unique())
        pallets_in_sheet2 = set(df2_pallet.unique())
        missing_pallets = sorted(pallets_in_lines - pallets_in_sheet2)

        if missing_pallets:
            messages.error(
                request,
                f"⚠ The following pallet numbers are referenced in Sheet1 but missing in Sheet2: {', '.join(missing_pallets)}"
            )
            return redirect("generate_doc")

        # -------------------------
        # Build Shipped To block
        # -------------------------
        consignee = next((c for c in shipped_to_list if c["name"] == shipped_to_name), None)
        if not consignee:
            messages.error(request, "⚠ Invalid 'Shipped To' selection.")
            return redirect("generate_doc")

        lines = [consignee["name"]]
        if consignee.get("id"):
            lines.append(f"ID: {consignee['id']}")
        if consignee.get("address"):
            lines.append(consignee["address"])
        if consignee.get("incoterms"):
            lines.append(consignee["incoterms"])

        shipped_to_block = "\n".join(lines)

        # -------------------------
        # Create Export (after validations)
        # -------------------------
        export = Export.objects.create(
            seller=seller_info["name"],
            sold_to=sold_to_block,
            shipped_to=shipped_to_block,
            project_no=project,
        )

        # -------------------------
        # Save LineItems
        # -------------------------
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

        # -------------------------
        # Save Pallets (safe: validated, numeric, >0, unique)
        # -------------------------
        for _, row in df2.iterrows():
            Pallet.objects.create(
                export=export,
                pallet_number=str(row["Pallet #"]).strip(),
                length_cm=Decimal(str(row["Lenght (Cm)"])),
                width_cm=Decimal(str(row["Width (Cm)"])),
                height_cm=Decimal(str(row["Height (Cm)"])),
                gross_weight_kg=Decimal(str(row["Gross Weight (Kg)"])),
            )

        return render(request, "core/export_success.html", {
            "export": export,
            "rows": len(df)
        })

    # GET request → form
    return render(request, "core/generate_doc.html", {
        "seller": seller_info,
        "shipped_to_list": shipped_to_list,
        "project_list": project_list,
    })
