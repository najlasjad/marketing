import os
from django.db import models


def upload_to_data_folder(instance, filename):
    # Simpan file di folder "document/" dengan nama asli user
    return os.path.join('documents', filename)


class Document(models.Model):
    name = models.CharField(max_length=255, unique=True)
    file = models.FileField(upload_to=upload_to_data_folder)
    uploaded_at = models.DateTimeField(auto_now_add=True)
