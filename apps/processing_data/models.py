import uuid
from django.db import models


class ProcessingSession(models.Model):
    """Reprezentuje pojedynczą sesję przetwarzania porównania plików."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="processing")

    def __str__(self):
        return f"Session {self.id} ({self.status})"


class WorkingFileDescription(models.Model):
    """Przechowuje dane opisów z pliku roboczego."""

    session = models.ForeignKey(
        ProcessingSession, on_delete=models.CASCADE, related_name="working_descriptions"
    )
    row_index = models.IntegerField()
    description = models.TextField()
    embedding = models.BinaryField(null=True, blank=True)

    def __str__(self):
        return f"WF Description [Row {self.row_index}]"

    class Meta:
        unique_together = ("session", "row_index")


class ReferenceFileDescription(models.Model):
    """Przechowuje dane opisów i cen z pliku referencyjnego."""

    session = models.ForeignKey(
        ProcessingSession,
        on_delete=models.CASCADE,
        related_name="reference_descriptions",
    )
    row_index = models.IntegerField()
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    embedding = models.BinaryField(null=True, blank=True)

    def __str__(self):
        return f"REF Description [Row {self.row_index}]"

    class Meta:
        unique_together = ("session", "row_index")
