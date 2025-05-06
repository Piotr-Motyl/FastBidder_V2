import logging
import uuid
from typing import List, Dict, Any, Optional
from django.db import transaction, DatabaseError
from .models import (
    ProcessingSession,
    WorkingFileDescription,
    ReferenceFileDescription,
    MatchingResult,
)
from .exceptions import StorageError


class SessionNotFoundError(Exception):
    """Wyjątek rzucany, gdy nie znaleziono sesji o podanym identyfikatorze."""

    pass


class ProcessingDataService:
    """
    Serwis odpowiedzialny za zarządzanie tymczasowymi danymi w procesie dopasowania.
    Obsługuje zapisywanie, pobieranie i czyszczenie danych opisów oraz wyników dopasowania.
    """

    @transaction.atomic
    def store_descriptions(
        self,
        working_file_data: List[Dict[str, Any]],
        reference_file_data: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Przechowuje opisy i powiązane dane wyekstrahowane z plików roboczego i referencyjnego.

        Parametry:
            working_file_data: Lista słowników z danymi z pliku roboczego. Każdy słownik musi zawierać:
                - 'row_index' (int): Indeks wiersza w pliku Excel
                - 'description' (str): Pełny tekst opisu
            reference_file_data: Lista słowników z danymi z pliku referencyjnego. Każdy słownik musi zawierać:
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

        # Walidacja danych wejściowych
        self._validate_working_file_data(working_file_data)
        self._validate_reference_file_data(reference_file_data)

        try:
            # Walidacja danych wejściowych
            self._validate_descriptions_data(working_file_data, reference_file_data)

            # Utworzenie lub pobranie sesji
            session = self._get_or_create_session(session_id)

            # Zapisanie opisów z pliku roboczego
            self._store_working_file_descriptions(working_file_data, session)

            # Zapisanie opisów z pliku referencyjnego
            self._store_reference_file_descriptions(reference_file_data, session)

            # Przygotowanie wynikowego słownika
            result = {
                "session_id": str(session.id),
                "working_file_count": len(working_file_data),
                "reference_file_count": len(reference_file_data),
            }

            return result

        except ValueError as ve:
            # Przekazanie dalej błędów walidacji
            raise ve
        except Exception as e:
            # Konwersja innych wyjątków na StorageError
            raise StorageError(f"Błąd podczas zapisywania opisów: {str(e)}")

    def _validate_descriptions_data(
        self,
        working_file_data: List[Dict[str, Any]],
        reference_file_data: List[Dict[str, Any]],
    ) -> None:
        """
        Sprawdza poprawność danych wejściowych dla opisów.

        Parametry:
            working_file_data: Lista słowników z danymi z pliku roboczego
            reference_file_data: Lista słowników z danymi z pliku referencyjnego

        Zgłasza:
            ValueError: Jeśli dane są nieprawidłowe lub niekompletne
        """
        # Sprawdzenie czy listy nie są puste
        if not working_file_data:
            raise ValueError("Lista opisów z pliku roboczego jest pusta")

        if not reference_file_data:
            raise ValueError("Lista opisów z pliku referencyjnego jest pusta")

        # Sprawdzenie wymaganych pól w każdym rekordzie pliku roboczego
        for i, item in enumerate(working_file_data):
            if "row_index" not in item:
                raise ValueError(f"Brak pola 'row_index' w opisie {i} pliku roboczego")
            if "description" not in item:
                raise ValueError(
                    f"Brak pola 'description' w opisie {i} pliku roboczego"
                )

        # Sprawdzenie wymaganych pól w każdym rekordzie pliku referencyjnego
        for i, item in enumerate(reference_file_data):
            if "row_index" not in item:
                raise ValueError(
                    f"Brak pola 'row_index' w opisie {i} pliku referencyjnego"
                )
            if "description" not in item:
                raise ValueError(
                    f"Brak pola 'description' w opisie {i} pliku referencyjnego"
                )
            if "price" not in item:
                raise ValueError(f"Brak pola 'price' w opisie {i} pliku referencyjnego")

    def _get_or_create_session(
        self, session_id: Optional[str] = None
    ) -> ProcessingSession:
        """
        Tworzy nową sesję przetwarzania lub pobiera istniejącą na podstawie ID.

        Parametry:
            session_id: Opcjonalny identyfikator sesji do pobrania

        Zwraca:
            Obiekt ProcessingSession

        Zgłasza:
            ValueError: Jeśli podany session_id jest nieprawidłowy
        """
        if session_id is None:
            # Utworzenie nowej sesji
            return ProcessingSession.objects.create()
        else:
            try:
                # Konwersja string na UUID jeśli to konieczne
                if isinstance(session_id, str):
                    session_uuid = uuid.UUID(session_id)
                else:
                    session_uuid = session_id

                # Pobranie istniejącej sesji
                return ProcessingSession.objects.get(id=session_uuid)
            except (ValueError, ProcessingSession.DoesNotExist):
                raise ValueError(f"Nieprawidłowy identyfikator sesji: {session_id}")

    def _store_working_file_descriptions(
        self, working_file_data: List[Dict[str, Any]], session: ProcessingSession
    ) -> None:
        """
        Zapisuje opisy z pliku roboczego do bazy danych.

        Parametry:
            working_file_data: Lista słowników z danymi z pliku roboczego
            session: Obiekt sesji przetwarzania
        """
        # Przygotowanie listy obiektów do utworzenia
        working_descriptions = [
            WorkingFileDescription(
                session=session,
                row_index=item["row_index"],
                description=item["description"],
            )
            for item in working_file_data
        ]

        # Zapisanie wszystkich obiektów za jednym razem dla wydajności
        WorkingFileDescription.objects.bulk_create(working_descriptions)

    def _store_reference_file_descriptions(
        self, reference_file_data: List[Dict[str, Any]], session: ProcessingSession
    ) -> None:
        """
        Zapisuje opisy z pliku referencyjnego do bazy danych.

        Parametry:
            reference_file_data: Lista słowników z danymi z pliku referencyjnego
            session: Obiekt sesji przetwarzania
        """
        # Przygotowanie listy obiektów do utworzenia
        reference_descriptions = [
            ReferenceFileDescription(
                session=session,
                row_index=item["row_index"],
                description=item["description"],
                price=item["price"],
            )
            for item in reference_file_data
        ]

        # Zapisanie wszystkich obiektów za jednym razem dla wydajności
        ReferenceFileDescription.objects.bulk_create(reference_descriptions)

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

    @transaction.atomic
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

        # Konfiguracja prostego logowania
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger = logging.getLogger(__name__)

        try:

            # Sprawdzenie czy sesja istnieje
            try:
                session = ProcessingSession.objects.get(id=session_id)
            except ProcessingSession.DoesNotExist:
                raise SessionNotFoundError(f"Nie znaleziono sesji o id: {session_id}")

            # Walidacja struktury matching_results
            if not isinstance(matching_results, list):
                raise ValueError("matching_results musi być listą")

            if not matching_results:
                logger.warning(
                    f"Przekazano pustą listę wyników dopasowania dla sesji {session_id}"
                )
                return True  # Pusta lista to też sukces (brak danych do zapisania)

            # Usuń istniejące wyniki dopasowania dla tej sesji (na wszelki wypadek)
            # W normalnym przepływie nie powinno być żadnych istniejących wyników
            existing_results = MatchingResult.objects.filter(session_id=session_id)
            if existing_results.exists():
                logger.warning(
                    f"Znaleziono istniejące wyniki dopasowania dla sesji {session_id}. Zostaną usunięte."
                )
                existing_results.delete()

            # Lista do przechowywania obiektów MatchingResult do zbiorczego zapisania
            matching_objects = []

            # Walidacja i przygotowanie obiektów do zapisania
            for idx, result in enumerate(matching_results):
                try:
                    # Walidacja wymaganych pól
                    required_fields = [
                        "wf_row_index",
                        "wf_description",
                        "matched",
                        "matching_status",
                    ]
                    for field in required_fields:
                        if field not in result:
                            raise ValueError(
                                f"Brak wymaganego pola '{field}' w wyniku dopasowania o indeksie {idx}"
                            )

                    # Walidacja pól warunkowych
                    if result["matched"]:
                        conditional_fields = [
                            "ref_row_index",
                            "ref_description",
                            "similarity",
                            "price",
                        ]
                        for field in conditional_fields:
                            if field not in result or result[field] is None:
                                raise ValueError(
                                    f"Brak wymaganego pola '{field}' dla dopasowanego wyniku o indeksie {idx}"
                                )

                    # Tworzenie obiektu MatchingResult
                    matching_result = MatchingResult(
                        session=session,
                        wf_row_index=result["wf_row_index"],
                        wf_description=result["wf_description"],
                        matched=result["matched"],
                        matching_status=result["matching_status"],
                    )

                    # Dodanie pól warunkowych
                    if result["matched"]:
                        matching_result.ref_row_index = result["ref_row_index"]
                        matching_result.ref_description = result["ref_description"]
                        matching_result.similarity = result["similarity"]
                        matching_result.price = result["price"]

                    matching_objects.append(matching_result)

                except Exception as e:
                    logger.error(
                        f"Błąd podczas przetwarzania wyniku dopasowania o indeksie {idx}: {str(e)}"
                    )
                    # Kontynuujemy z pozostałymi wynikami

            # Zapisanie wszystkich wyników jednocześnie
            if matching_objects:
                MatchingResult.objects.bulk_create(matching_objects)
                logger.info(
                    f"Zapisano {len(matching_objects)} wyników dopasowania dla sesji {session_id}"
                )
            else:
                logger.warning(
                    f"Nie zapisano żadnych wyników dopasowania dla sesji {session_id}"
                )

            return True

        except SessionNotFoundError:
            logger.error(f"Nie znaleziono sesji o id: {session_id}")
            raise
        except ValueError as e:
            logger.error(f"Błąd walidacji danych: {str(e)}")
            raise
        except DatabaseError as e:
            logger.error(
                f"Błąd bazy danych podczas zapisywania wyników dopasowania: {str(e)}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd podczas zapisywania wyników dopasowania: {str(e)}"
            )
            return False

    @transaction.atomic
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
            session_id (str): Identyfikator sesji przetwarzania, dla której mają zostać usunięte dane tymczasowe.
                            Musi być poprawnym UUID.

        Returns:
            bool: True jeśli czyszczenie się powiodło, False w przeciwnym razie

        Raises:
            ValueError: Gdy session_id jest nieprawidłowy
            DatabaseError: Gdy wystąpi problem z dostępem do bazy danych
            SessionNotFoundError: Gdy sesja o podanym identyfikatorze nie istnieje
        """

        # Konfiguracja prostego logowania
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger = logging.getLogger(__name__)

        try:
            # Walidacja session_id - czy jest poprawnym UUID
            try:
                if isinstance(session_id, str):
                    session_uuid = uuid.UUID(session_id)
                else:
                    session_uuid = session_id
            except ValueError:
                logger.error(f"Nieprawidłowy format UUID dla session_id: {session_id}")
                raise ValueError(
                    f"Nieprawidłowy format identyfikatora sesji: {session_id}. Musi być poprawnym UUID."
                )

            # Sprawdzenie czy sesja istnieje
            try:
                session = ProcessingSession.objects.get(id=session_uuid)
            except ProcessingSession.DoesNotExist:
                logger.error(f"Nie znaleziono sesji o id: {session_id}")
                raise SessionNotFoundError(f"Nie znaleziono sesji o id: {session_id}")

            # W ramach transakcji usuwamy wszystkie powiązane dane
            # Django automatycznie usunie powiązane dane dzięki kaskadowemu usuwaniu (on_delete=models.CASCADE)
            # w definicji modeli, ale możemy też jawnie usunąć dane dla większej przejrzystości

            # Usunięcie opisów z pliku roboczego
            session.working_descriptions.all().delete()

            # Usunięcie opisów z pliku referencyjnego
            session.reference_descriptions.all().delete()

            # Usunięcie wyników dopasowania
            session.matching_results.all().delete()

            # W MVP usuwamy sesję całkowicie
            # W przyszłości można rozważyć zmianę statusu sesji na "completed" zamiast usuwania
            session.delete()
            logger.info(f"Usunięto sesję {session_id}")

            return True

        except ValueError as e:
            # Przekazujemy dalej błędy walidacji
            logger.error(f"Błąd walidacji: {str(e)}")
            raise
        except SessionNotFoundError as e:
            # Przekazujemy dalej informację o braku sesji
            logger.error(f"Błąd sesji: {str(e)}")
            raise
        except DatabaseError as e:
            # Przekazujemy dalej błędy bazy danych
            logger.error(f"Błąd bazy danych podczas czyszczenia danych: {str(e)}")
            raise
        except Exception as e:
            # Logujemy nieoczekiwane błędy, ale zwracamy False
            logger.error(
                f"Nieoczekiwany błąd podczas czyszczenia danych sesji {session_id}: {str(e)}"
            )
            return False
