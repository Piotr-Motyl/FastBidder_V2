from venv import logger
import pandas as pd
from typing import Dict, List, Any, Optional
import numpy as np
import logging
import string


class ExcelProcessingService:
    """Serwis do przetwarzania plików Excel w aplikacji FastBidder."""

    # Konfiguracja podstawowego logowania
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    def extract_data(
        self,
        file_paths: Dict[str, str],
        working_file: Dict[str, Any],
        reference_file: Dict[str, Any],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Ekstrahuje dane z plików Excel (WF i REF) na podstawie określonych parametrów.

        Parametry:
            file_paths: Słownik ze ścieżkami do plików
                {
                    "working_file_path": str,
                    "reference_file_path": str
                }
            working_file: Parametry dla pliku roboczego
                {
                    "description_column": str,
                    "description_range": {"start": str, "end": str},
                    "price_target_column": str,
                    "matching_report_column": str
                }
            reference_file: Parametry dla pliku referencyjnego
                {
                    "description_column": str,
                    "description_range": {"start": str, "end": str},
                    "price_source_column": str
                }

        Zwraca:
            Dict zawierający listy słowników z wyekstrahowanymi danymi
            {
                "working_file_data": [
                    {
                        "row_index": int,
                        "description": str
                    },
                    ...
                ],
                "reference_file_data": [
                    {
                        "row_index": int,
                        "description": str,
                        "price": float
                    },
                    ...
                ]
            }

        Zgłasza:
            ValueError: Jeśli struktura pliku Excel jest nieprawidłowa
            FileNotFoundError: Jeśli plik nie istnieje
            PermissionError: Jeśli brak dostępu do pliku
        """
        try:
            result = {"working_file_data": [], "reference_file_data": []}

            logger.info(f"Rozpoczynanie ekstrakcji danych z plików Excel")

            # Ekstrakcja danych z Working File (WF)
            working_file_data = self._extract_working_file_data(
                file_paths["working_file_path"],
                working_file["description_column"],
                working_file["description_range"],
            )
            result["working_file_data"] = working_file_data

            logger.info(
                f"Wyekstrahowano {len(working_file_data)} rekordów z pliku roboczego"
            )

            # Ekstrakcja danych z Reference File (REF)
            reference_file_data = self._extract_reference_file_data(
                file_paths["reference_file_path"],
                reference_file["description_column"],
                reference_file["description_range"],
                reference_file["price_source_column"],
            )
            result["reference_file_data"] = reference_file_data

            logger.info(
                f"Wyekstrahowano {len(reference_file_data)} rekordów z pliku referencyjnego"
            )

            return result

        except Exception as e:
            logger.error(f"Błąd podczas ekstrakcji danych z plików Excel: {str(e)}")
            raise ValueError(f"Błąd podczas ekstrakcji danych z plików Excel: {str(e)}")

    def _extract_working_file_data(
        self, file_path: str, description_column: str, description_range: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Ekstrahuje dane z pliku roboczego (WF).

        Parametry:
            file_path: Ścieżka do pliku Excel
            description_column: Litera kolumny z opisami (np. "A", "B")
            description_range: Zakres wierszy do ekstrakcji {"start": str, "end": str}

        Zwraca:
            Lista słowników zawierających row_index i description.

        Zgłasza:
            ValueError: Jeśli struktura pliku Excel jest nieprawidłowa
        """
        try:
            # Wczytanie pliku Excel
            logger.info(f"Wczytywanie pliku roboczego: {file_path}")
            df = pd.read_excel(file_path)

            # Konwersja litery kolumny na indeks
            col_index = self._column_letter_to_index(description_column)

            # Konwersja zakresów na indeksy (odejmujemy 1, bo Excel zaczyna od 1, a Python od 0)
            start_row = int(description_range["start"]) - 1
            end_row = int(description_range["end"])

            # Walidacja zakresów
            if start_row < 0:
                raise ValueError(
                    f"Nieprawidłowy zakres wierszy: {description_range['start']}"
                )

            # Upewnienie się, że zakres nie wychodzi poza ramy pliku
            if end_row > len(df):
                logger.warning(
                    f"Zakres wierszy przekracza rozmiar pliku. Dostosowano do rozmiaru: {len(df)}"
                )
                end_row = len(df)

            # Sprawdzenie czy indeks kolumny jest poprawny
            if col_index >= len(df.columns):
                raise ValueError(f"Kolumna {description_column} nie istnieje w pliku")

            # Ekstrakcja danych
            result = []
            for i in range(start_row, end_row):
                # Pobieranie wartości z komórki
                cell_value = df.iloc[i, col_index]

                # Konwersja na string z obsługą wartości null
                if pd.isna(cell_value):
                    continue

                description = str(cell_value).strip()

                # Dodanie do wyników tylko niepustych wartości
                if description:
                    result.append(
                        {
                            "row_index": i
                            + 1,  # Dodajemy 1, aby wrócić do numeracji Excela
                            "description": description,
                        }
                    )

            logger.info(f"Wyekstrahowano {len(result)} opisów z pliku roboczego")
            return result

        except Exception as e:
            logger.error(f"Błąd podczas ekstrakcji danych z pliku roboczego: {str(e)}")
            raise ValueError(
                f"Błąd podczas ekstrakcji danych z pliku roboczego: {str(e)}"
            )

    def _extract_reference_file_data(
        self,
        file_path: str,
        description_column: str,
        description_range: Dict[str, str],
        price_column: str,
    ) -> List[Dict[str, Any]]:
        """
        Ekstrahuje dane z pliku referencyjnego (REF).

        Parametry:
            file_path: Ścieżka do pliku Excel
            description_column: Litera kolumny z opisami (np. "A", "B")
            description_range: Zakres wierszy do ekstrakcji {"start": str, "end": str}
            price_column: Litera kolumny z cenami (np. "D", "E")

        Zwraca:
            Lista słowników zawierających row_index, description i price.

        Zgłasza:
            ValueError: Jeśli struktura pliku Excel jest nieprawidłowa
        """
        try:
            # Wczytanie pliku Excel
            logger.info(f"Wczytywanie pliku referencyjnego: {file_path}")
            df = pd.read_excel(file_path)

            # Konwersja liter kolumn na indeksy
            desc_col_index = self._column_letter_to_index(description_column)
            price_col_index = self._column_letter_to_index(price_column)

            # Konwersja zakresów na indeksy (odejmujemy 1, bo Excel zaczyna od 1, a Python od 0)
            start_row = int(description_range["start"]) - 1
            end_row = int(description_range["end"])

            # Walidacja zakresów
            if start_row < 0:
                raise ValueError(
                    f"Nieprawidłowy zakres wierszy: {description_range['start']}"
                )

            # Upewnienie się, że zakres nie wychodzi poza ramy pliku
            if end_row > len(df):
                logger.warning(
                    f"Zakres wierszy przekracza rozmiar pliku. Dostosowano do rozmiaru: {len(df)}"
                )
                end_row = len(df)

            # Sprawdzenie czy indeksy kolumn są poprawne
            if desc_col_index >= len(df.columns):
                raise ValueError(
                    f"Kolumna opisu {description_column} nie istnieje w pliku"
                )

            if price_col_index >= len(df.columns):
                raise ValueError(f"Kolumna ceny {price_column} nie istnieje w pliku")

            # Ekstrakcja danych
            result = []
            for i in range(start_row, end_row):
                # Pobieranie wartości z komórek
                desc_value = df.iloc[i, desc_col_index]
                price_value = df.iloc[i, price_col_index]

                # Konwersja opisu na string z obsługą wartości null
                if pd.isna(desc_value):
                    continue

                description = str(desc_value).strip()

                # Próba konwersji ceny na float
                if pd.isna(price_value):
                    continue

                try:
                    price = float(price_value)

                    # Dodanie do wyników tylko niepustych wartości
                    if description:
                        result.append(
                            {
                                "row_index": i
                                + 1,  # Dodajemy 1, aby wrócić do numeracji Excela
                                "description": description,
                                "price": price,
                            }
                        )
                except (ValueError, TypeError):
                    logger.warning(
                        f"Nieudana konwersja ceny w wierszu {i+1}: {price_value}"
                    )
                    continue

            logger.info(f"Wyekstrahowano {len(result)} opisów z pliku referencyjnego")
            return result

        except Exception as e:
            logger.error(
                f"Błąd podczas ekstrakcji danych z pliku referencyjnego: {str(e)}"
            )
            raise ValueError(
                f"Błąd podczas ekstrakcji danych z pliku referencyjnego: {str(e)}"
            )

    def _column_letter_to_index(self, column_letter: str) -> int:
        """
        Konwertuje literę kolumny Excel (A, B, C, ..., Z, AA, AB, ...) na indeks numeryczny (0, 1, 2, ...).

        Parametry:
            column_letter: Litera kolumny (np. "A", "B", "AA")

        Zwraca:
            Indeks kolumny (0-based)
        """
        column_letter = column_letter.upper()
        result = 0

        for char in column_letter:
            # Sprawdź czy znak jest literą
            if char not in string.ascii_uppercase:
                raise ValueError(f"Nieprawidłowy znak w oznaczeniu kolumny: {char}")

            # Dodaj wartość aktualnej litery do wyniku
            result = result * 26 + (ord(char) - ord("A") + 1)

        return result - 1  # Odejmujemy 1, bo indeksowanie w pandas zaczyna się od 0

    def update_working_file(
        self,
        matching_results: List[Dict[str, Any]],
        source_file_path: str,
        target_file_path: str,
        price_target_column: str,
        matching_report_column: str,
    ) -> bool:
        """
        Aktualizuje plik roboczy (WF) na podstawie wyników dopasowania, dodając ceny jednostkowe
        i raport z dopasowania do odpowiednich kolumn.

        Args:
            matching_results: Lista wyników dopasowania, każdy element zawiera:
                - wf_row_index (int): Indeks wiersza w pliku WF (0-based)
                - wf_description (str): Opis z pliku WF
                - matched (bool): Czy znaleziono dopasowanie
                - ref_row_index (int | None): Indeks wiersza w pliku REF (jeśli dopasowano)
                - ref_description (str | None): Opis z pliku REF (jeśli dopasowano)
                - similarity (float | None): Wartość podobieństwa w procentach 0-100 (jeśli dopasowano)
                - price (float | None): Cena jednostkowa z REF (jeśli dopasowano)
                - matching_status (str): Status dopasowania
            source_file_path: Ścieżka do oryginalnego pliku roboczego (WF)
            target_file_path: Ścieżka, pod którą ma być zapisany zmodyfikowany plik WF
            price_target_column: Symbol kolumny, w której mają być zapisane ceny jednostkowe (np. "F")
            matching_report_column: Symbol kolumny, w której ma być zapisany raport z dopasowania (np. "AB")

        Returns:
            bool: True jeśli aktualizacja się powiodła, False w przeciwnym razie
        """
        try:
            logger.info(f"Rozpoczęcie aktualizacji pliku roboczego: {source_file_path}")

            # Odczyt pliku Excel
            df = pd.read_excel(source_file_path)
            logger.info(f"Plik wejściowy wczytany pomyślnie, wymiary: {df.shape}")

            # Konwersja liter kolumn na indeksy
            try:
                price_col_idx = self._column_letter_to_index(price_target_column)
                report_col_idx = self._column_letter_to_index(matching_report_column)
                logger.info(
                    f"Kolumna ceny: {price_target_column} (indeks: {price_col_idx}), "
                    f"kolumna raportu: {matching_report_column} (indeks: {report_col_idx})"
                )
            except ValueError as e:
                logger.error(f"Błąd podczas konwersji liter kolumn: {str(e)}")
                return False

            # Dodanie kolumn jeśli nie istnieją
            if price_col_idx >= df.shape[1]:
                for i in range(df.shape[1], price_col_idx + 1):
                    col_name = f"Col_{i}"
                    df[col_name] = np.nan
                logger.info(
                    f"Dodano brakujące kolumny do indeksu ceny: {price_col_idx}"
                )

            if report_col_idx >= df.shape[1]:
                for i in range(df.shape[1], report_col_idx + 1):
                    col_name = f"Col_{i}"
                    if col_name not in df.columns:
                        df[col_name] = np.nan
                logger.info(
                    f"Dodano brakujące kolumny do indeksu raportu: {report_col_idx}"
                )

            # Aktualizacja cen i raportów dopasowania
            updated_rows = 0
            for result in matching_results:
                row_idx = result[
                    "wf_row_index"
                ]  # Już jest 0-based zgodnie z odpowiedzią

                if row_idx < len(df):
                    if result["matched"]:
                        # Aktualizacja ceny
                        df.iloc[row_idx, price_col_idx] = result["price"]

                        # Formatowanie statusu dopasowania
                        status_text = (
                            result["matching_status"].replace("_", " ").capitalize()
                        )

                        # Formatowanie wartości podobieństwa
                        similarity_value = result["similarity"]
                        if similarity_value is not None:
                            similarity_formatted = f"{similarity_value:.1f}%"
                        else:
                            similarity_formatted = "N/A"

                        # Aktualizacja raportu dopasowania
                        df.iloc[row_idx, report_col_idx] = (
                            f"{status_text} (podobieństwo: {similarity_formatted})"
                        )
                    else:
                        df.iloc[row_idx, report_col_idx] = "Brak dopasowania"

                    updated_rows += 1
                else:
                    logger.warning(f"Pominięto wiersz {row_idx} - poza zakresem danych")

            logger.info(f"Zaktualizowano {updated_rows} wierszy w pliku")

            # Zapisanie zmodyfikowanego pliku
            df.to_excel(target_file_path, index=False)
            logger.info(
                f"Plik wynikowy zapisany pomyślnie pod ścieżką: {target_file_path}"
            )

            return True

        except FileNotFoundError as e:
            logger.error(f"Nie znaleziono pliku: {str(e)}")
            return False
        except PermissionError as e:
            logger.error(f"Brak uprawnień do odczytu/zapisu pliku: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji pliku roboczego: {str(e)}")
            return False
