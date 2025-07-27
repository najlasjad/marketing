import os
from django.db import models
import pandas as pd
from django.core.files.storage import default_storage


def upload_to_data_folder(instance, filename):
    return os.path.join('documents', filename)


class Document(models.Model):
    name = models.CharField(max_length=255, unique=True)
    file = models.FileField(upload_to=upload_to_data_folder)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    file_type = models.CharField(max_length=20, blank=True)
    file_size = models.CharField(max_length=50, blank=True)
    total_rows = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        # Set file type dan size sebelum simpan awal
        if self.file and not self.file_type:
            ext = os.path.splitext(self.file.name)[1].lower()
            self.file_type = ext.lstrip('.')

        if self.file and not self.file_size:
            size_bytes = self.file.size
            if size_bytes < 1024:
                self.file_size = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                self.file_size = f"{size_bytes / 1024:.2f} KB"
            else:
                self.file_size = f"{size_bytes / (1024 * 1024):.2f} MB"

        # Simpan dulu agar file tersedia secara fisik
        is_new = self._state.adding  # Cek apakah ini save pertama
        super().save(*args, **kwargs)

        # Setelah disimpan, baru proses isi file untuk hitung total_rows
        if is_new and self.file and self.total_rows == 0:
            try:
                file_path = self.file.path if hasattr(
                    self.file, 'path') else default_storage.path(self.file.name)
                ext = self.file_type.lower()

                if ext == 'csv':
                    df = pd.read_csv(file_path, delimiter=';',
                                     encoding='utf-8')
                elif ext in ['xlsx', 'xls']:
                    df = pd.read_excel(file_path)
                elif ext == 'json':
                    df = pd.read_json(file_path)
                else:
                    df = None

                if df is not None:
                    self.total_rows = len(df)
                    super().save(update_fields=['total_rows'])

            except Exception as e:
                print(f"❌ Gagal membaca file: {e}")
                self.total_rows = 0
                super().save(update_fields=['total_rows'])
