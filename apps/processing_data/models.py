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


class MatchingResult(models.Model):
    """Przechowuje wyniki dopasowania opisów z pliku roboczego do pliku referencyjnego."""

    session = models.ForeignKey(
        ProcessingSession, on_delete=models.CASCADE, related_name="matching_results"
    )
    wf_row_index = models.IntegerField()
    wf_description = models.TextField()
    matched = models.BooleanField(default=False)
    ref_row_index = models.IntegerField(null=True, blank=True)
    ref_description = models.TextField(null=True, blank=True)
    similarity = models.FloatField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    matching_status = models.CharField(max_length=50)

    def __str__(self):
        return (
            f"Match Result [WF Row {self.wf_row_index}, Status: {self.matching_status}]"
        )

    class Meta:
        unique_together = ("session", "wf_row_index")
