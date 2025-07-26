import os
from django.db import models


# class RegistrationData(models.Model):
#     idregistrantdata = models.IntegerField()
#     groupreg = models.IntegerField()
#     regtype = models.IntegerField()
#     iddataregkhusustype = models.IntegerField()
#     idschooltypedata = models.IntegerField()
#     idschooljurusandata = models.IntegerField()
#     email = models.EmailField()
#     idmajordata = models.IntegerField()
#     idcountrydata = models.IntegerField()
#     iddataprovinces = models.IntegerField()
#     iddataregencies = models.IntegerField()
#     ispaid = models.BooleanField()  # Dulu BooleanField → sekarang IntegerField
#     paymentamount = models.IntegerField()  # Karena CSV-nya integer, bukan decimal

#     def __str__(self):
#         return str(self.idregistrantdata)


def upload_to_data_folder(instance, filename):
    # Simpan file di folder "document/" dengan nama asli user
    return os.path.join('documents', filename)


class Document(models.Model):
    name = models.CharField(max_length=255, unique=True)
    file = models.FileField(upload_to=upload_to_data_folder)
    uploaded_at = models.DateTimeField(auto_now_add=True)
