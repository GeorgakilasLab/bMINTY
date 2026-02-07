from django.db import models
from studies.models import Study
from pipelines.models import Pipeline

class Assay(models.Model):
    # id → “id INTEGER PRIMARY KEY AUTOINCREMENT”
    external_id = models.CharField(
        max_length=255,                   # TEXT NOT NULL
    )
    type = models.CharField(
        max_length=255,                   # TEXT NOT NULL
    )
    target = models.CharField(
        max_length=255,                   # TEXT NULL
        blank=True,
        null=True,
    )
    name = models.CharField(
        max_length=255,                   # TEXT NOT NULL
    )
    tissue = models.CharField(
        max_length=255,                   # TEXT NULL
        blank=True,
        null=True,
    )
    cell_type = models.CharField(
        max_length=255,                   # TEXT NULL
        blank=True,
        null=True,
    )
    treatment = models.TextField(
        # TEXT NOT NULL
    )
    date = models.CharField(
        max_length=255,                   # TEXT NULL
        blank=True,
        null=True,
    )
    platform = models.CharField(
        max_length=255,                   # TEXT NOT NULL
    )
    kit = models.CharField(
        max_length=255,                   # TEXT NULL
        blank=True,
        null=True,
    )
    description = models.TextField(
        blank=True,                       # TEXT NULL
        null=True,
    )
    availability = models.BooleanField(
        default=True,
        null=False,
        blank=False,
    )

    study = models.ForeignKey(
        Study,                            # FOREIGN KEY (study_id) … ON DELETE CASCADE
        on_delete=models.CASCADE,
        related_name='assays'
    )
    pipeline = models.ForeignKey(
        Pipeline,                         # FOREIGN KEY (pipeline_id) … ON DELETE CASCADE
        on_delete=models.CASCADE,
        related_name='assays'
    )
    
    note = models.TextField(
        blank=True,                       # TEXT NULL
        null=True,
    )

    # Assembly reference(s) - stores CSV of assembly names/IDs for easy reference
    assemblies = models.TextField(
        blank=True,                       # TEXT NULL
        null=True,
        help_text="CSV list of assemblies used in this assay"
    )

    # Auto-generated metrics (set by import wizard, not user-facing inputs)
    interval_count = models.IntegerField(null=True, blank=True)
    # Signal and cell counters
    signal_nonzero = models.IntegerField(null=True, blank=True)
    signal_zero    = models.IntegerField(null=True, blank=True)
    cell_total     = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'assay'
        ordering = ['id']

    def __str__(self):
        return self.name
