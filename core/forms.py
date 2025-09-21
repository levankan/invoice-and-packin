from django import forms
from .models import Export

class ExportForm(forms.ModelForm):
    class Meta:
        model = Export
        fields = ["invoice_number", "project_no", "export_number"]  
        # 👆 Add more fields if you want them editable in the form
