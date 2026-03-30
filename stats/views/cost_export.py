#stats/views/cost_export.py
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

from stats.cost_services import build_cost_analysis


def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


@login_required
def export_cost_analysis_excel(request):
    date_from_str = request.GET.get("date_from", "")
    date_to_str = request.GET.get("date_to", "")
    vendor_name = request.GET.get("vendor_name", "").strip()
    item_no = request.GET.get("item_no", "").strip()

    date_from = parse_date(date_from_str)
    date_to = parse_date(date_to_str)

    analysis = build_cost_analysis(
        date_from=date_from,
        date_to=date_to,
        vendor_name=vendor_name,
        item_no=item_no,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Cost Analysis"

    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin", color="D9E2F3")

    # Title
    ws["A1"] = "Transportation Cost Analysis"
    ws["A1"].font = Font(size=14, bold=True)

    # Filters
    ws["A3"] = "Date From"
    ws["B3"] = date_from_str or "-"
    ws["C3"] = "Date To"
    ws["D3"] = date_to_str or "-"
    ws["E3"] = "Vendor Name"
    ws["F3"] = vendor_name or "-"
    ws["G3"] = "Item Number"
    ws["H3"] = item_no or "-"

    # Summary section
    ws["A5"] = "Summary"
    ws["A5"].font = Font(bold=True, size=12)

    summary_headers = ["Metric", "Value"]
    summary_data = [
        ["All Shipments", analysis["cards"]["all"]],
        ["Air", analysis["cards"]["air"]],
        ["Sea", analysis["cards"]["sea"]],
        ["Road", analysis["cards"]["road"]],
        ["Courier", analysis["cards"]["courier"]],
        ["Other", analysis["cards"]["other"]],
        ["Total Goods Value (USD)", analysis["summary"]["total_goods_usd"]],
        ["Total Transport Cost (USD)", analysis["summary"]["total_transport_usd"]],
        ["Transport %", f'{analysis["summary"]["overall_percent"]}%'],
    ]

    start_row = 7
    for col_num, value in enumerate(summary_headers, 1):
        cell = ws.cell(row=start_row, column=col_num, value=value)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
        cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for row_index, row_data in enumerate(summary_data, start_row + 1):
        for col_num, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_index, column=col_num, value=value)
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 15
    ws.column_dimensions["D"].width = 15
    ws.column_dimensions["E"].width = 20
    ws.column_dimensions["F"].width = 25
    ws.column_dimensions["G"].width = 15
    ws.column_dimensions["H"].width = 20

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="cost_analysis.xlsx"'

    wb.save(response)
    return response