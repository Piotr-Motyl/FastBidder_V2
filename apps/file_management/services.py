import uuid
from django.conf import settings
import os
from pathlib import Path
import mimetypes
from django.core.exceptions import ValidationError
from openpyxl import load_workbook
import magic  # python-magic do weryfikacji typu plików
from .models import UploadedFile


class FileManagementService:

    def upload_file(self, file, file_type):
        """
        Obsługuje wgrywanie pliku i zapisuje go w odpowiednim katalogu.

        Parametry:
            file: Obiekt pliku z request.FILES
            file_type: Typ pliku ('WF' lub 'REF')

        Zwraca:
            Słownik zawierający informacje o wgranym pliku
                {
                    "file_id": str,
                    "file_path": str,
                    "original_filename": str
                }
        """
        pass

    def validate_uploaded_file(self, file):
        """
        Waliduje wgrany plik (format, rozmiar, itp.)

        Parametry:
            file: Obiekt pliku z request.FILES

        Zwraca:
            True jeśli plik jest prawidłowy, False w przeciwnym razie
        """
        pass

    def get_upload_directory(self, file_type):
        """
        Zwraca ścieżkę do katalogu, w którym ma być zapisany plik.

        Parametry:
            file_type: Typ pliku ('WF' lub 'REF')

        Zwraca:
            Ścieżka do katalogu
        """
        pass

    def generate_unique_filename(self, original_filename, file_type):
        """
        Generuje unikalną nazwę pliku w oparciu o oryginalną nazwę i typ.

        Parametry:
            original_filename: Oryginalna nazwa pliku
            file_type: Typ pliku ('WF' lub 'REF')

        Zwraca:
            Unikalna nazwa pliku
        """
        pass

    def validate_files(self, working_file_path: str, reference_file_path: str) -> bool:
        """
        Waliduje czy pliki istnieją i mają poprawny format Excel (.xlsx).

        Parametry:
            working_file_path (str): Ścieżka do pliku WF (Working File)
            reference_file_path (str): Ścieżka do pliku REF (Reference File)

        Zwraca:
            dict: Słownik zawierający wynik walidacji
                {
                    "valid": bool,  # True jeśli oba pliki są prawidłowe
                    "errors": list  # Lista błędów, pusta jeśli valid=True
                }

        Zgłasza:
            FileNotFoundError: Jeśli któryś z plików nie istnieje
            ValidationError: Jeśli któryś z plików ma nieprawidłowy format
        """
        validation_result = {"valid": True, "errors": []}

        # Sprawdzenie, czy obie ścieżki są niepuste
        if not working_file_path or not reference_file_path:
            validation_result["valid"] = False
            validation_result["errors"].append("Ścieżki do plików nie mogą być puste")
            return validation_result

        # Lista plików do walidacji
        files_to_validate = [
            {"path": working_file_path, "type": "Working File (WF)"},
            {"path": reference_file_path, "type": "Reference File (REF)"},
        ]

        # Walidacja każdego pliku
        for file_info in files_to_validate:
            file_path = file_info["path"]
            file_type = file_info["type"]

            # Sprawdzenie czy plik istnieje
            if not self._file_exists(file_path):
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"Plik {file_type} nie istnieje: {file_path}"
                )
                continue

            # Sprawdzenie czy plik ma właściwy format
            if not self._is_valid_excel_file(file_path):
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"Plik {file_type} nie jest prawidłowym plikiem Excel: {file_path}"
                )
                continue

            # Sprawdzenie czy plik można otworzyć
            if not self._can_open_excel_file(file_path):
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"Nie można otworzyć pliku {file_type}: {file_path}"
                )
                continue

        return validation_result

    def _file_exists(self, file_path):
        """
        Sprawdza czy plik istnieje w systemie plików.

        Parametry:
            file_path (str): Ścieżka do pliku

        Zwraca:
            bool: True jeśli plik istnieje, False w przeciwnym razie
        """
        return os.path.isfile(file_path)

    def _is_valid_excel_file(self, file_path):
        """
        Sprawdza czy plik jest prawidłowym plikiem Excel (.xlsx).

        Parametry:
            file_path (str): Ścieżka do pliku

        Zwraca:
            bool: True jeśli plik jest prawidłowym plikiem Excel, False w przeciwnym razie
        """
        # Sprawdzenie rozszerzenia pliku
        if not file_path.lower().endswith(".xlsx"):
            return False

        # Sprawdzenie typu MIME
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)
        valid_excel_types = [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/zip",  # Excel .xlsx pliki są zaszyfrowanymi archiwami ZIP
        ]

        return file_type in valid_excel_types

    def _can_open_excel_file(self, file_path):
        """
        Sprawdza czy plik Excel można otworzyć (nie jest uszkodzony ani zablokowany).

        Parametry:
            file_path (str): Ścieżka do pliku

        Zwraca:
            bool: True jeśli plik można otworzyć, False w przeciwnym razie
        """
        try:
            # Próba otwarcia pliku za pomocą openpyxl
            workbook = load_workbook(filename=file_path, read_only=True)
            workbook.close()
            return True
        except Exception:
            return False

    def get_file_paths(self, working_file_identifier, reference_file_identifier):
        """
        Zwraca pełne ścieżki do plików WF i REF na podstawie ich identyfikatorów.

        Identyfikator może być:
        - UUID pliku w bazie danych (jako string lub obiekt UUID)
        - Ścieżką do pliku (relatywną lub absolutną)

        Parametry:
            working_file_identifier (str/UUID): Identyfikator pliku WF
            reference_file_identifier (str/UUID): Identyfikator pliku REF

        Zwraca:
            dict: Słownik zawierający ścieżki do plików
                {
                    "working_file_path": str,  # Pełna ścieżka do pliku WF
                    "reference_file_path": str  # Pełna ścieżka do pliku REF
                }

        Zgłasza:
            FileNotFoundError: Jeśli któryś z plików nie istnieje
            ValueError: Jeśli identyfikator jest nieprawidłowy
        """
        result = {}

        # Pobierz ścieżki do plików
        result["working_file_path"] = self._resolve_file_path(
            working_file_identifier, "WF"
        )
        result["reference_file_path"] = self._resolve_file_path(
            reference_file_identifier, "REF"
        )

        # Weryfikacja istnienia plików
        for key, path in result.items():
            if not os.path.isfile(path):
                file_type = (
                    "Working File" if key == "working_file_path" else "Reference File"
                )
                raise FileNotFoundError(f"{file_type} nie istnieje pod ścieżką: {path}")

        return result

    def _resolve_file_path(self, file_identifier, file_type):
        """
        Metoda pomocnicza rozwiązująca ścieżkę do pliku na podstawie identyfikatora.

        Parametry:
            file_identifier (str/UUID): Identyfikator pliku
            file_type (str): Typ pliku ('WF' lub 'REF')

        Zwraca:
            str: Pełna ścieżka do pliku

        Zgłasza:
            ValueError: Jeśli identyfikator jest nieprawidłowy lub nie można znaleźć pliku
        """
        # Sprawdź czy identyfikator jest pusty
        if not file_identifier:
            raise ValueError(f"Identyfikator pliku {file_type} nie może być pusty")

        # Sprawdź czy to bezpośrednia ścieżka do pliku
        if isinstance(file_identifier, str) and os.path.isfile(file_identifier):
            return os.path.abspath(file_identifier)

        # Spróbuj zinterpretować jako UUID i znaleźć plik w bazie danych
        try:
            if isinstance(file_identifier, str):
                file_id = uuid.UUID(file_identifier)
            else:
                file_id = file_identifier

            file_obj = UploadedFile.objects.get(id=file_id, file_type=file_type)
            return file_obj.get_file_path()
        except (ValueError, UploadedFile.DoesNotExist):
            pass

        # Sprawdź czy to nazwa pliku, i znajdź plik w odpowiednim katalogu
        if isinstance(file_identifier, str):
            base_dir = self.get_upload_directory(file_type)
            potential_path = os.path.join(base_dir, file_identifier)
            if os.path.isfile(potential_path):
                return potential_path

        # Jeśli dotarliśmy tutaj, nie udało się znaleźć pliku
        raise ValueError(
            f"Nie można znaleźć pliku {file_type} o identyfikatorze: {file_identifier}"
        )

    def get_result_file_path(self, working_file_path: str) -> str:
        """
        Generuje ścieżkę do pliku wynikowego na podstawie ścieżki do pliku roboczego.

        Proces obejmuje:
        1. Walidację ścieżki do pliku roboczego
        2. Utworzenie nowej ścieżki dla pliku wynikowego, zazwyczaj w tym samym katalogu
        co plik roboczy, ale z dodatkowym oznaczeniem (np. suffixem "_result")
        3. Zapewnienie, że katalog docelowy istnieje i jest dostępny do zapisu

        Args:
            working_file_path (str): Ścieżka do oryginalnego pliku roboczego (WF)

        Returns:
            str: Ścieżka do pliku wynikowego, gdzie zostanie zapisany zmodyfikowany plik WF

        Raises:
            ValueError: Gdy ścieżka do pliku roboczego jest nieprawidłowa
            PermissionError: Gdy brak uprawnień do zapisu w katalogu docelowym
            IOError: Gdy wystąpi inny problem z systemem plików
        """
        pass
