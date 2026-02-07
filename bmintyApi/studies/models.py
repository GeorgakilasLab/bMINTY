from django.db import models

class Study(models.Model):
    external_id   = models.CharField(max_length=100, unique=True)
    external_repo = models.CharField(max_length=200, blank=True, null=True)
    name          = models.CharField(max_length=100)
    description   = models.TextField(blank=True, null=True)
    availability     = models.BooleanField(default=True)
    note        = models.TextField(blank=True, null=True)

    class Meta:
        db_table  = 'study'
        ordering = ['id']   # or ['name'], or whatever makes sense

    def __str__(self):
        return self.name
