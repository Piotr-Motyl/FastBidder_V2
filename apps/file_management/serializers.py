from rest_framework import serializers
from .models import UploadedFile


class FileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = ["file", "file_type"]

    def validate_file(self, value):
        # Walidacja formatu pliku (tylko .xlsx)
        if not value.name.endswith(".xlsx"):
            raise serializers.ValidationError(
                "Tylko pliki Excel (.xlsx) są akceptowane"
            )
        return value

    def validate_file_type(self, value):
        if value not in ["WF", "REF"]:
            raise serializers.ValidationError("Typ pliku musi być 'WF' lub 'REF'")
        return value
