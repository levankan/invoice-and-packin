from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Max
from decimal import Decimal

# -----------------------------
# User with Roles
# -----------------------------
class User(AbstractUser):
    ROLE_CHOICES = [
        ('warehouse', 'Warehouse'),
        ('logistic', 'Logistic'),
        ('employee', 'Other Employee'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


# -----------------------------
# Auto number generators
# -----------------------------
def next_export_number():
    latest = Export.objects.aggregate(m=Max('export_number'))['m']
    if latest:
        try:
            return f"EXP{int(latest.replace('EXP', '')) + 1:06d}"
        except ValueError:
            pass
    return "EXP000001"


def next_invoice_number():
    latest = Export.objects.aggregate(m=Max('invoice_number'))['m']
    if latest and latest.startswith("P_"):
        try:
            return f"P_{int(latest.replace('P_', '')) + 1:06d}"
        except ValueError:
            pass
    return "P_000001"


def next_packing_list_number():
    latest = Export.objects.aggregate(m=Max('packing_list_number'))['m']
    if latest and latest.startswith("PL-"):
        try:
            return f"PL-{int(latest.replace('PL-', '')) + 1:06d}"
        except ValueError:
            pass
    return "PL-000001"


# -----------------------------
# Export Document
# -----------------------------
class Export(models.Model):
    export_number = models.CharField(max_length=20, unique=True, default=next_export_number)
    invoice_number = models.CharField(max_length=20, unique=True, default=next_invoice_number)
    packing_list_number = models.CharField(max_length=20, unique=True, default=next_packing_list_number)

    seller = models.CharField(max_length=255)
    sold_to = models.CharField(max_length=255)
    shipped_to = models.CharField(max_length=255)
    project_no = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.export_number} / {self.invoice_number} / {self.packing_list_number}"

    @property
    def total_gross_weight(self):
        """Sum of all pallet weights"""
        return sum(p.gross_weight_kg for p in self.pallets.all())


# -----------------------------
# Line Items
# -----------------------------
class LineItem(models.Model):
    export = models.ForeignKey(Export, on_delete=models.CASCADE, related_name="items")

    serial_lot_number = models.CharField(max_length=100)
    document_number = models.CharField(max_length=100, blank=True, null=True)
    item_number = models.CharField(max_length=100, blank=True, null=True)
    cross_reference = models.CharField(max_length=100, blank=True, null=True)
    qty = models.IntegerField(default=0)
    unit_of_measure = models.CharField(max_length=50, blank=True, null=True)
    box_number = models.CharField(max_length=100, blank=True, null=True)
    commercial_invoice_number = models.CharField(max_length=100, blank=True, null=True)
    posting_date = models.DateField(blank=True, null=True)
    shipment_number = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    carbon_qty = models.DecimalField(max_digits=12, decimal_places=5, blank=True, null=True)
    carbon_lot = models.CharField(max_length=100, blank=True, null=True)
    customer_po = models.CharField(max_length=100, blank=True, null=True)
    po_line = models.CharField(max_length=100, blank=True, null=True)
    sales_order = models.CharField(max_length=100, blank=True, null=True)
    sales_order_line = models.CharField(max_length=100, blank=True, null=True)
    pallet_number = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    lu = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.export.export_number} - {self.serial_lot_number}"


# -----------------------------
# Pallet Data (Sheet2)
# -----------------------------
class Pallet(models.Model):
    export = models.ForeignKey(Export, related_name="pallets", on_delete=models.CASCADE)
    pallet_number = models.CharField(max_length=50)
    length_cm = models.DecimalField(max_digits=10, decimal_places=2)
    width_cm = models.DecimalField(max_digits=10, decimal_places=2)
    height_cm = models.DecimalField(max_digits=10, decimal_places=2)
    gross_weight_kg = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Pallet {self.pallet_number} ({self.gross_weight_kg} Kg)"
