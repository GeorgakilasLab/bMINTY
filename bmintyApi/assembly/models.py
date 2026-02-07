from django.db import models

class Assembly(models.Model):
    name    = models.CharField(max_length=255)           # TEXT NOT NULL
    version = models.CharField(max_length=255)           # TEXT NOT NULL
    species = models.CharField(
                  max_length=255,                       # TEXT NULL
                  blank=True,
                  null=True,
              )

    class Meta:
        db_table = 'assembly'
        ordering = ['id']

    def __str__(self):
        return f"{self.name} - {self.version}"
