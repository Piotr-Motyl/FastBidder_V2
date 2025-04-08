from django.db import models
import uuid
import os


class UploadedFile(models.Model):
    FILE_TYPES = (
        ("WF", "Working File"),
        ("REF", "Reference File"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to="uploads/")
    file_type = models.CharField(max_length=3, choices=FILE_TYPES)
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def get_file_path(self):
        return self.file.path
