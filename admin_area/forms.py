# admin_area/forms.py
from django import forms

class ItemsUploadForm(forms.Form):
    file = forms.FileField(
        label="Excel file (.xlsx)",
        help_text="Upload an .xlsx file with the header row."
    )
    def clean_file(self):
        f = self.cleaned_data['file']
        if not f.name.lower().endswith('.xlsx'):
            raise forms.ValidationError("Please upload an .xlsx file.")
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File too large (max 10 MB).")
        return f


class VendorsUploadForm(forms.Form):
    file = forms.FileField(
        label="Excel file (.xlsx)",
        help_text="Upload an .xlsx with header row (requires: No., Name; optional: VAT Registration No.)."
    )
    def clean_file(self):
        f = self.cleaned_data['file']
        if not f.name.lower().endswith('.xlsx'):
            raise forms.ValidationError("Please upload an .xlsx file.")
        if f.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File too large (max 10 MB).")
        return f