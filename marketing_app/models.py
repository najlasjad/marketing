from django.db import models


class RegistrationData(models.Model):
    idregistrantdata = models.BigIntegerField()
    groupreg = models.IntegerField()
    regtype = models.IntegerField()
    iddataregkhusustype = models.IntegerField()
    idschooltypedata = models.IntegerField()
    idschooljurusandata = models.IntegerField()
    email = models.EmailField()
    idmajordata = models.IntegerField()
    idcountrydata = models.IntegerField()
    iddataprovences = models.IntegerField()
    iddataregencies = models.IntegerField()
    ispaid = models.IntegerField()
    paymentamount = models.BigIntegerField()

    def __str__(self):
        return f"Registrant {self.idregistrantdata} - {self.email}"
