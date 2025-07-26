from django import forms
from .models import Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['name', 'file']


# class UploadCSVForm(forms.Form):
#     file = forms.FileField(label='Upload CSV File')
