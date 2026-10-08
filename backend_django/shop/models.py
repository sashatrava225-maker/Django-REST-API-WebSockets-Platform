from django.db import models

class Item(models.Model):
    name = models.CharField(max_length=255)
    quantity = models.IntegerField()
    is_bought = models.BooleanField(default=False)
    user_id = models.IntegerField()

    def __str__(self):
        return self.name
