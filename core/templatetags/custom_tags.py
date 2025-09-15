from django import template

register = template.Library()

@register.filter
def calc_total_weight(pallets):
    return sum(p.gross_weight_kg for p in pallets)
