from typing import Dict, Any, Optional
from rest_framework import serializers


class FileParametersSerializer(serializers.Serializer):
    """
    Serializator do walidacji parametrów pliku Excel.

    Atrybuty:
        file_path (str): Ścieżka do pliku Excel.
        description_column (str): Kolumna zawierająca opisy pozycji.
        description_range (Dict[str, str]): Zakres wierszy z opisami ("start" i "end").
        price_target_column (Optional[str]): Kolumna docelowa dla cen (tylko dla pliku roboczego).
        price_source_column (Optional[str]): Kolumna źródłowa cen (tylko dla pliku referencyjnego).
        matching_report_column (Optional[str]): Kolumna do zapisania raportu dopasowania (tylko dla pliku roboczego).
    """

    file_path = serializers.CharField(max_length=255)
    description_column = serializers.CharField(max_length=50)
    description_range = serializers.DictField()
    price_target_column = serializers.CharField(max_length=50, required=False)
    price_source_column = serializers.CharField(max_length=50, required=False)
    matching_report_column = serializers.CharField(max_length=50, required=False)

    def validate_description_range(self, value: Dict[str, str]) -> Dict[str, str]:
        """
        Sprawdza poprawność zakresu opisów.

        Args:
            value: Słownik zawierający klucze "start" i "end" określające zakres.

        Returns:
            Zwalidowany słownik zakresu.

        Raises:
            serializers.ValidationError: Gdy zakres nie zawiera wymaganych kluczy.
        """
        if "start" not in value or "end" not in value:
            raise serializers.ValidationError("Zakres musi zawierać 'start' i 'end'")
        return value


class CompareFilesRequestSerializer(serializers.Serializer):
    """
    Serializator do walidacji pełnego żądania porównania plików.

    Atrybuty:
        working_file (FileParametersSerializer): Parametry pliku roboczego.
        reference_file (FileParametersSerializer): Parametry pliku referencyjnego.
        matching_threshold (int): Próg podobieństwa dla dopasowania (0-100).
    """

    working_file = FileParametersSerializer()
    reference_file = FileParametersSerializer()
    matching_threshold = serializers.IntegerField(min_value=0, max_value=100)

    def validate_working_file(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sprawdza wymagane pola dla pliku roboczego.

        Args:
            value: Słownik parametrów pliku roboczego.

        Returns:
            Zwalidowane parametry pliku roboczego.

        Raises:
            serializers.ValidationError: Gdy brakuje wymaganych pól.
        """
        if "price_target_column" not in value or not value["price_target_column"]:
            raise serializers.ValidationError(
                "Brak wymaganego pola 'price_target_column' dla pliku roboczego"
            )

        if "matching_report_column" not in value or not value["matching_report_column"]:
            raise serializers.ValidationError(
                "Brak wymaganego pola 'matching_report_column' dla pliku roboczego"
            )

        return value

    def validate_reference_file(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sprawdza wymagane pola dla pliku referencyjnego.

        Args:
            value: Słownik parametrów pliku referencyjnego.

        Returns:
            Zwalidowane parametry pliku referencyjnego.

        Raises:
            serializers.ValidationError: Gdy brakuje wymaganych pól.
        """
        if "price_source_column" not in value or not value["price_source_column"]:
            raise serializers.ValidationError(
                "Brak wymaganego pola 'price_source_column' dla pliku referencyjnego"
            )

        return value
