import uuid
from typing import List, Dict, Any, Optional
from django.db import transaction
from .models import ProcessingSession, WorkingFileDescription, ReferenceFileDescription
from .exceptions import StorageError


class ProcessingDataService:
    """Serwis do zarządzania przechowywaniem i pobieraniem danych przetwarzania."""

    @transaction.atomic
    def store_descriptions(
        self,
        working_file_data: List[Dict[str, Any]],
        reference_file_data: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Przechowuje opisy i powiązane dane wyekstrahowane z plików roboczego i referencyjnego.

        Implementacja metody opisanej w kontrakcie API.
        """
        # Walidacja danych wejściowych
        self._validate_working_file_data(working_file_data)
        self._validate_reference_file_data(reference_file_data)

        try:
            # Utworzenie lub pobranie sesji
            if session_id:
                session = ProcessingSession.objects.get(id=session_id)
            else:
                session = ProcessingSession.objects.create()

            # Przechowanie opisów z pliku roboczego
            working_descriptions = []
            for item in working_file_data:
                working_descriptions.append(
                    WorkingFileDescription(
                        session=session,
                        row_index=item["row_index"],
                        description=item["description"],
                    )
                )
            WorkingFileDescription.objects.bulk_create(working_descriptions)

            # Przechowanie opisów z pliku referencyjnego
            reference_descriptions = []
            for item in reference_file_data:
                reference_descriptions.append(
                    ReferenceFileDescription(
                        session=session,
                        row_index=item["row_index"],
                        description=item["description"],
                        price=item["price"],
                    )
                )
            ReferenceFileDescription.objects.bulk_create(reference_descriptions)

            return {
                "session_id": str(session.id),
                "working_file_count": len(working_descriptions),
                "reference_file_count": len(reference_descriptions),
            }

        except Exception as e:
            raise StorageError(f"Nie udało się przechować opisów: {str(e)}")

    def _validate_working_file_data(self, data: List[Dict[str, Any]]) -> None:
        """Waliduje format danych pliku roboczego."""
        if not isinstance(data, list):
            raise ValueError("Dane pliku roboczego muszą być listą")

        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"Element o indeksie {i} musi być słownikiem")

            if "row_index" not in item:
                raise ValueError(f"Element o indeksie {i} nie zawiera 'row_index'")

            if "description" not in item:
                raise ValueError(f"Element o indeksie {i} nie zawiera 'description'")

            if not isinstance(item["row_index"], int):
                raise ValueError(
                    f"'row_index' w elemencie {i} musi być liczbą całkowitą"
                )

            if not isinstance(item["description"], str):
                raise ValueError(
                    f"'description' w elemencie {i} musi być łańcuchem znaków"
                )

    def _validate_reference_file_data(self, data: List[Dict[str, Any]]) -> None:
        """Waliduje format danych pliku referencyjnego."""
        if not isinstance(data, list):
            raise ValueError("Dane pliku referencyjnego muszą być listą")

        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"Element o indeksie {i} musi być słownikiem")

            if "row_index" not in item:
                raise ValueError(f"Element o indeksie {i} nie zawiera 'row_index'")

            if "description" not in item:
                raise ValueError(f"Element o indeksie {i} nie zawiera 'description'")

            if "price" not in item:
                raise ValueError(f"Element o indeksie {i} nie zawiera 'price'")

            if not isinstance(item["row_index"], int):
                raise ValueError(
                    f"'row_index' w elemencie {i} musi być liczbą całkowitą"
                )

            if not isinstance(item["description"], str):
                raise ValueError(
                    f"'description' w elemencie {i} musi być łańcuchem znaków"
                )

            if not isinstance(item["price"], (int, float)):
                raise ValueError(f"'price' w elemencie {i} musi być liczbą")

    def store_matching_results(
        self, matching_results: List[Dict[str, Any]], session_id: str
    ) -> bool:
        """
        Przechowuje wyniki dopasowania w bazie danych i wiąże je z odpowiednią sesją przetwarzania.

        Proces zapisywania obejmuje:
        1. Weryfikację poprawności struktury przekazanych wyników dopasowania
        2. Sprawdzenie istnienia sesji o podanym identyfikatorze
        3. Zapisanie wyników w bazie danych z powiązaniem do odpowiedniej sesji

        Args:
            matching_results (List[Dict[str, Any]]): Lista słowników zawierających wyniki dopasowania,
                każdy dla jednego opisu z pliku WF. Każdy słownik powinien zawierać:
                - wf_row_index (int): Indeks wiersza w pliku WF
                - wf_description (str): Opis z pliku WF
                - matched (bool): Czy znaleziono dopasowanie
                - ref_row_index (int | None): Indeks wiersza w pliku REF (jeśli dopasowano)
                - ref_description (str | None): Opis z pliku REF (jeśli dopasowano)
                - similarity (float | None): Wartość podobieństwa (jeśli dopasowano)
                - price (float | None): Cena jednostkowa z REF (jeśli dopasowano)
                - matching_status (str): Status dopasowania ("matched", "no_match", "multiple_matches_best_selected")
            session_id (str): Identyfikator sesji przetwarzania, służący do powiązania wyników z odpowiednią sesją.

        Returns:
            bool: True jeśli zapisywanie się powiodło, False w przeciwnym razie

        Raises:
            ValueError: Gdy struktura matching_results jest nieprawidłowa
            DatabaseError: Gdy wystąpi problem z dostępem do bazy danych
            SessionNotFoundError: Gdy sesja o podanym identyfikatorze nie istnieje
        """
        pass

    def clear_data(self, session_id: str) -> bool:
        """
        Usuwa dane tymczasowe powiązane z sesją przetwarzania po zakończeniu procesu porównania.

        Proces obejmuje:
        1. Weryfikację czy wskazana sesja istnieje w bazie danych
        2. Usunięcie wszystkich opisów z pliku roboczego (WF) związanych z sesją
        3. Usunięcie wszystkich opisów z pliku referencyjnego (REF) związanych z sesją
        4. Usunięcie wyników dopasowania związanych z sesją
        5. Opcjonalnie: oznaczenie sesji jako zakończoną zamiast jej usuwania (dla celów audytu)

        Args:
            session_id (str): Identyfikator sesji przetwarzania, dla której mają zostać
                            usunięte dane tymczasowe. Musi być poprawnym UUID.

        Returns:
            bool: True jeśli czyszczenie się powiodło, False w przeciwnym razie

        Raises:
            ValueError: Gdy session_id jest nieprawidłowy
            DatabaseError: Gdy wystąpi problem z dostępem do bazy danych
            SessionNotFoundError: Gdy sesja o podanym identyfikatorze nie istnieje
        """
        pass
