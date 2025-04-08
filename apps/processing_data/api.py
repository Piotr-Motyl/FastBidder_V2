# processing_data/api.py
from typing import List, Dict, Any, Optional
from .services import ProcessingDataService
from .exceptions import StorageError

# Utworzenie instancji serwisu typu singleton
_service = ProcessingDataService()


def store_descriptions(
    working_file_data: List[Dict[str, Any]],
    reference_file_data: List[Dict[str, Any]],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Przechowuje opisy i powiązane dane wyekstrahowane z plików roboczego i referencyjnego.

    Parametry:
        working_file_data: Lista słowników z danymi z pliku roboczego.
            Każdy słownik musi zawierać:
            - 'row_index' (int): Indeks wiersza w pliku Excel
            - 'description' (str): Pełny tekst opisu

        reference_file_data: Lista słowników z danymi z pliku referencyjnego.
            Każdy słownik musi zawierać:
            - 'row_index' (int): Indeks wiersza w pliku Excel
            - 'description' (str): Pełny tekst opisu
            - 'price' (float): Cena powiązana z opisem

        session_id: Opcjonalny identyfikator bieżącej sesji przetwarzania.
                   Jeśli None, zostanie wygenerowany nowy identyfikator sesji.

    Zwraca:
        Słownik z informacjami o sesji:
        {
            'session_id': str,  # Identyfikator tej sesji przetwarzania
            'working_file_count': int,  # Liczba przechowywanych opisów z pliku roboczego
            'reference_file_count': int,  # Liczba przechowywanych opisów z pliku referencyjnego
        }

    Zgłasza:
        ValueError: Jeśli dane wejściowe są nieprawidłowe lub brakuje wymaganych pól.
        StorageError: Jeśli wystąpi problem z systemem przechowywania.
    """
    return _service.store_descriptions(
        working_file_data, reference_file_data, session_id
    )
