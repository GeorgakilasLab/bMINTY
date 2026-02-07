from django.db import models

class Pipeline(models.Model):
    # Django will automatically create `id = AutoField(primary_key=True)` to match your
    # “id INTEGER PRIMARY KEY AUTOINCREMENT”

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # Matches "external_url TEXT NOT NULL"
    external_url = models.CharField(max_length=255)

    class Meta:
        db_table = 'pipeline'
        ordering = ['id']  # Optional: order by the auto `id` field

    def __str__(self):
        return f"{self.name} (#{self.id})"
