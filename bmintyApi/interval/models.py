from django.db import models
from assembly.models import Assembly

class Interval(models.Model):
    # “id INTEGER PRIMARY KEY AUTOINCREMENT” → Django’s default `id` field

    external_id  = models.CharField(max_length=255)                  # TEXT NOT NULL
    parental_id  = models.CharField(max_length=255,                 # TEXT NULL
                                     blank=True,
                                     null=True)
    name         = models.CharField(max_length=255,                 # TEXT NULL
                                     blank=True,
                                     null=True)
    type         = models.CharField(max_length=255)                  # TEXT NOT NULL
    biotype      = models.CharField(max_length=255,                 # TEXT NULL
                                     blank=True,
                                     null=True)
    chromosome   = models.CharField(max_length=255)                  # TEXT NOT NULL
    start        = models.IntegerField()                             # INTEGER NOT NULL
    end          = models.IntegerField(blank=True,                   # INTEGER NULL
                                       null=True)
    strand       = models.CharField(max_length=255)                  # TEXT NOT NULL
    summit       = models.IntegerField(blank=True,                   # INTEGER NULL
                                        null=True)
    assembly     = models.ForeignKey(                                # FOREIGN KEY … ON DELETE CASCADE
        Assembly,
        on_delete=models.CASCADE,
        related_name='intervals'
    )

    class Meta:
        db_table = 'interval'
        ordering = ['id']

    def __str__(self):
        return self.external_id
