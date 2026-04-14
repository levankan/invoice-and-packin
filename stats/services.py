from django.db.models import Q, Count
from imports.models import Import


def _apply_date_range(qs, date_from=None, date_to=None):
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return qs


def _apply_extra_filters(qs, vendor_name=None, item_no=None):
    if vendor_name:
        qs = qs.filter(vendor_name__icontains=vendor_name)

    if item_no:
        qs = qs.filter(lines__item_no__icontains=item_no)

    return qs.distinct()


def _shipping_method_filter(method_name):
    method_name = (method_name or "").lower().strip()

    if method_name == "air":
        return Q(shipping_method__icontains="air")

    if method_name == "sea":
        return (
            Q(shipping_method__icontains="sea") |
            Q(shipping_method__icontains="ocean") |
            Q(shipping_method__icontains="vessel")
        )

    if method_name == "road":
        return (
            Q(shipping_method__icontains="road") |
            Q(shipping_method__icontains="truck") |
            Q(shipping_method__icontains="land")
        )

    if method_name == "courier":
        return (
            Q(shipping_method__icontains="fedex") |
            Q(shipping_method__icontains="dhl") |
            Q(shipping_method__icontains="ups") |
            Q(shipping_method__icontains="tnt") |
            Q(shipping_method__icontains="courier")
        )

    if method_name == "other":
        return ~(
            _shipping_method_filter("air") |
            _shipping_method_filter("sea") |
            _shipping_method_filter("road") |
            _shipping_method_filter("courier")
        )

    return Q()


def _status_filter(status_name):
    status_name = (status_name or "").lower().strip()

    if status_name == "planned":
        return (
            Q(shipment_status__iexact="planned") |
            Q(shipment_status__icontains="plan")
        )

    if status_name == "in_transit":
        return (
            Q(shipment_status__iexact="in transit") |
            Q(shipment_status__iexact="in_transit") |
            Q(shipment_status__icontains="transit")
        )

    if status_name == "at_customs":
        return (
            Q(shipment_status__iexact="at customs") |
            Q(shipment_status__iexact="at_customs") |
            Q(shipment_status__icontains="customs")
        )

    if status_name == "delivered":
        return (
            Q(shipment_status__iexact="delivered") |
            Q(shipment_status__icontains="deliver")
        )

    return Q()


def _count_shipments(base_qs, status=None, shipping_method=None):
    qs = base_qs

    if status:
        qs = qs.filter(_status_filter(status))

    if shipping_method:
        qs = qs.filter(_shipping_method_filter(shipping_method))

    return qs.distinct().count()


def add_percentages(stats):
    total = stats["total_registered"]["all"] or 1

    methods = ["air", "sea", "road", "courier", "other"]
    sections = ["total_registered", "planned", "in_transit", "at_customs", "delivered"]

    for key in sections:
        for method in methods:
            value = stats[key][method]
            percent = (value / total) * 100
            stats[key][f"{method}_percent"] = round(percent, 1)

    return stats


def get_import_statistics(date_from=None, date_to=None, vendor_name=None, item_no=None):
    base_qs = Import.objects.all()
    base_qs = _apply_date_range(base_qs, date_from, date_to)
    base_qs = _apply_extra_filters(base_qs, vendor_name=vendor_name, item_no=item_no)

    # Build Q objects once and reuse across all 30 Count annotations.
    planned_q    = _status_filter("planned")
    in_transit_q = _status_filter("in_transit")
    at_customs_q = _status_filter("at_customs")
    delivered_q  = _status_filter("delivered")

    air_q     = _shipping_method_filter("air")
    sea_q     = _shipping_method_filter("sea")
    road_q    = _shipping_method_filter("road")
    courier_q = _shipping_method_filter("courier")
    other_q   = _shipping_method_filter("other")

    # Replace 30 separate COUNT queries with a single aggregate call.
    # Count("id", filter=..., distinct=True) maps to
    # COUNT(DISTINCT CASE WHEN <cond> THEN id ELSE NULL END) in SQL,
    # which correctly handles the lines JOIN introduced by item_no filtering.
    agg = base_qs.aggregate(
        # total_registered — no status filter
        tr_all     = Count("id", distinct=True),
        tr_air     = Count("id", filter=air_q,     distinct=True),
        tr_sea     = Count("id", filter=sea_q,     distinct=True),
        tr_road    = Count("id", filter=road_q,    distinct=True),
        tr_courier = Count("id", filter=courier_q, distinct=True),
        tr_other   = Count("id", filter=other_q,   distinct=True),
        # planned
        pl_all     = Count("id", filter=planned_q,             distinct=True),
        pl_air     = Count("id", filter=planned_q & air_q,     distinct=True),
        pl_sea     = Count("id", filter=planned_q & sea_q,     distinct=True),
        pl_road    = Count("id", filter=planned_q & road_q,    distinct=True),
        pl_courier = Count("id", filter=planned_q & courier_q, distinct=True),
        pl_other   = Count("id", filter=planned_q & other_q,   distinct=True),
        # in_transit
        it_all     = Count("id", filter=in_transit_q,             distinct=True),
        it_air     = Count("id", filter=in_transit_q & air_q,     distinct=True),
        it_sea     = Count("id", filter=in_transit_q & sea_q,     distinct=True),
        it_road    = Count("id", filter=in_transit_q & road_q,    distinct=True),
        it_courier = Count("id", filter=in_transit_q & courier_q, distinct=True),
        it_other   = Count("id", filter=in_transit_q & other_q,   distinct=True),
        # at_customs
        ac_all     = Count("id", filter=at_customs_q,             distinct=True),
        ac_air     = Count("id", filter=at_customs_q & air_q,     distinct=True),
        ac_sea     = Count("id", filter=at_customs_q & sea_q,     distinct=True),
        ac_road    = Count("id", filter=at_customs_q & road_q,    distinct=True),
        ac_courier = Count("id", filter=at_customs_q & courier_q, distinct=True),
        ac_other   = Count("id", filter=at_customs_q & other_q,   distinct=True),
        # delivered
        dl_all     = Count("id", filter=delivered_q,             distinct=True),
        dl_air     = Count("id", filter=delivered_q & air_q,     distinct=True),
        dl_sea     = Count("id", filter=delivered_q & sea_q,     distinct=True),
        dl_road    = Count("id", filter=delivered_q & road_q,    distinct=True),
        dl_courier = Count("id", filter=delivered_q & courier_q, distinct=True),
        dl_other   = Count("id", filter=delivered_q & other_q,   distinct=True),
    )

    stats = {
        "total_registered": {
            "all":     agg["tr_all"],
            "air":     agg["tr_air"],
            "sea":     agg["tr_sea"],
            "road":    agg["tr_road"],
            "courier": agg["tr_courier"],
            "other":   agg["tr_other"],
        },
        "planned": {
            "all":     agg["pl_all"],
            "air":     agg["pl_air"],
            "sea":     agg["pl_sea"],
            "road":    agg["pl_road"],
            "courier": agg["pl_courier"],
            "other":   agg["pl_other"],
        },
        "in_transit": {
            "all":     agg["it_all"],
            "air":     agg["it_air"],
            "sea":     agg["it_sea"],
            "road":    agg["it_road"],
            "courier": agg["it_courier"],
            "other":   agg["it_other"],
        },
        "at_customs": {
            "all":     agg["ac_all"],
            "air":     agg["ac_air"],
            "sea":     agg["ac_sea"],
            "road":    agg["ac_road"],
            "courier": agg["ac_courier"],
            "other":   agg["ac_other"],
        },
        "delivered": {
            "all":     agg["dl_all"],
            "air":     agg["dl_air"],
            "sea":     agg["dl_sea"],
            "road":    agg["dl_road"],
            "courier": agg["dl_courier"],
            "other":   agg["dl_other"],
        },
    }

    return add_percentages(stats)