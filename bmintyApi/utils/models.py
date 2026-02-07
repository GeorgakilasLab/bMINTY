from django.db import models

class SQLiteSequence(models.Model):
    # these exactly match the sqlite_sequence DDL:
    name = models.CharField(max_length=255, primary_key=True)
    seq  = models.BigIntegerField()

    class Meta:
        db_table = 'sqlite_sequence'
        managed = False     # Django won’t try to CREATE or DELETE this table
        verbose_name = "SQLite Sequence"
        verbose_name_plural = "SQLite Sequences"

    def __str__(self):
        return f"{self.name} → {self.seq}"
