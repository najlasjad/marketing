from django import forms
from .models import Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['name', 'file']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['name'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Enter dataset name',
            'id': 'fileName'
        })

        self.fields['file'].widget.attrs.update({
            'class': 'form-file-input',
            'id': 'fileInput',
            'style': 'display: none;',
            'accept': '.csv,.xlsx,.xls,.json,.txt',
        })
