from django.db import models
from assay.models import Assay
from interval.models import Interval
from django.core.exceptions import ValidationError

class Cell(models.Model):
    # SQLite has “id INTEGER PRIMARY KEY AUTOINCREMENT”
    # so we just let Django use its default `id = AutoField(primary_key=True)`
    name         = models.CharField(max_length=255)
    # Mandatory cell kind: 'cell' (single cell) or 'spot' (SRT)
    TYPE_CELL = 'cell'
    TYPE_SPOT = 'spot'
    TYPE_CHOICES = (
        (TYPE_CELL, 'cell'),
        (TYPE_SPOT, 'spot'),
    )
    type         = models.CharField(max_length=16, choices=TYPE_CHOICES)
    # Optional experimental label (e.g., CD4+ T cell)
    label        = models.CharField(max_length=255, null=True, blank=True)
    x_coordinate = models.IntegerField(null=True, blank=True)
    y_coordinate = models.IntegerField(null=True, blank=True)
    z_coordinate = models.IntegerField(null=True, blank=True)

    # SQLite: “assay_id INTEGER NOT NULL … ON DELETE CASCADE”
    assay = models.ForeignKey(
        Assay,
        on_delete=models.CASCADE,
        related_name='cells'
    )

    class Meta:
        db_table = 'cell'        
        ordering = ['id']

    def __str__(self):
        return f"{self.name} (#{self.id})"


class Signal(models.Model):
    # SQLite: “id INTEGER PRIMARY KEY AUTOINCREMENT”
    # again, we rely on Django’s automatic `id` field

    # SQLite: “signal DOUBLE NOT NULL”
    signal = models.FloatField()

    # SQLite: “p_value DOUBLE” and “padj_value DOUBLE”
    p_value    = models.FloatField(null=True, blank=True)
    padj_value = models.FloatField(null=True, blank=True)

    # SQLite: “assay_id INTEGER NOT NULL … ON DELETE CASCADE”
    assay = models.ForeignKey(
        Assay,
        on_delete=models.CASCADE,
        related_name='signals'
    )

    # SQLite: “interval_id INTEGER NOT NULL … ON DELETE CASCADE”
    interval = models.ForeignKey(
        Interval,
        on_delete=models.CASCADE,
        related_name='signals'
    )

    # SQLite: “cell_id INTEGER” (nullable) with no CASCADE
    cell = models.ForeignKey(
        Cell,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='signals'
    )

    class Meta:
        db_table = 'signal'        
        ordering = ['id']

    def __str__(self):
        return f"Signal {self.id}: {self.signal}"

    def clean(self):
        # Normalize numeric fields to handle European formats
        def _normalize_float(val, required=False):
            if val is None:
                if required:
                    raise ValidationError("signal cannot be null")
                return None
            if isinstance(val, (int, float)):
                return float(val)
            s = str(val).strip()
            if not s:
                if required:
                    raise ValidationError("signal cannot be empty")
                return None
            if s.upper() in ("NA", "N/A", "NULL"):
                if required:
                    raise ValidationError("signal cannot be NA")
                return None
            s = s.replace(" ", "")
            if "," in s:
                s = s.replace(".", "")
                s = s.replace(",", ".")
                return float(s)
            if s.count('.') > 1:
                s = s.replace('.', '')
                return float(s)
            return float(s)

        # Apply normalization
        self.signal = _normalize_float(self.signal, required=True)
        try:
            self.p_value = _normalize_float(self.p_value, required=False)
        except ValidationError:
            self.p_value = None
        try:
            self.padj_value = _normalize_float(self.padj_value, required=False)
        except ValidationError:
            self.padj_value = None

    def save(self, *args, **kwargs):
        # Ensure normalization occurs on any save/create path
        try:
            self.clean()
        except ValidationError as e:
            # Re-raise to prevent invalid save
            raise e
        super().save(*args, **kwargs)
