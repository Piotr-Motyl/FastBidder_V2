from venv import logger
import pandas as pd
from typing import Dict, List, Any, Optional
import numpy as np


class ExcelProcessingService:
    """Serwis do przetwarzania plików Excel w aplikacji FastBidder."""

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
        result = {"working_file_data": [], "reference_file_data": []}

        # Ekstrakcja danych z Working File (WF)
        working_file_data = self._extract_working_file_data(
            file_paths["working_file_path"],
            working_file["description_column"],
            working_file["description_range"],
        )
        result["working_file_data"] = working_file_data

        # Ekstrakcja danych z Reference File (REF)
        reference_file_data = self._extract_reference_file_data(
            file_paths["reference_file_path"],
            reference_file["description_column"],
            reference_file["description_range"],
            reference_file["price_source_column"],
        )
        result["reference_file_data"] = reference_file_data

        return result

    def _extract_working_file_data(
        self, file_path: str, description_column: str, description_range: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Ekstrahuje dane z pliku roboczego (WF).

        Zwraca listę słowników zawierających row_index i description.
        """
        try:
            # Wczytanie pliku Excel
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
            if end_row > len(df):
                end_row = len(df)

            # Ekstrakcja danych
            result = []
            for i in range(start_row, end_row):
                description = str(df.iloc[i, col_index])

                # Sprawdzenie czy opis nie jest pusty
                if pd.notna(description) and description.strip():
                    result.append(
                        {
                            "row_index": i
                            + 1,  # Dodajemy 1, aby wrócić do numeracji Excela
                            "description": description.strip(),
                        }
                    )

            return result

        except Exception as e:
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

        Zwraca listę słowników zawierających row_index, description i price.
        """
        try:
            # Wczytanie pliku Excel
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
            if end_row > len(df):
                end_row = len(df)

            # Ekstrakcja danych
            result = []
            for i in range(start_row, end_row):
                description = str(df.iloc[i, desc_col_index])
                price_value = df.iloc[i, price_col_index]

                # Sprawdzenie czy opis i cena nie są puste
                if (
                    pd.notna(description)
                    and description.strip()
                    and pd.notna(price_value)
                ):
                    try:
                        # Próba konwersji ceny na float
                        price = float(price_value)
                        result.append(
                            {
                                "row_index": i
                                + 1,  # Dodajemy 1, aby wrócić do numeracji Excela
                                "description": description.strip(),
                                "price": price,
                            }
                        )
                    except (ValueError, TypeError):
                        # Ignorujemy nieprawidłowe ceny
                        continue

            return result

        except Exception as e:
            raise ValueError(
                f"Błąd podczas ekstrakcji danych z pliku referencyjnego: {str(e)}"
            )

    def _column_letter_to_index(self, column_letter: str) -> int:
        """
        Konwertuje literę kolumny Excel (A, B, C...) na indeks numeryczny (0, 1, 2...).
        """
        column_letter = column_letter.upper()
        result = 0
        for char in column_letter:
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
                - wf_row_index (int): Indeks wiersza w pliku WF
                - wf_description (str): Opis z pliku WF
                - matched (bool): Czy znaleziono dopasowanie
                - ref_row_index (int | None): Indeks wiersza w pliku REF (jeśli dopasowano)
                - ref_description (str | None): Opis z pliku REF (jeśli dopasowano)
                - similarity (float | None): Wartość podobieństwa (jeśli dopasowano)
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
            # Odczyt pliku Excel
            df = pd.read_excel(source_file_path)

            # Konwersja liter kolumn na indeksy
            price_col_idx = self._column_letter_to_index(price_target_column)
            report_col_idx = self._column_letter_to_index(matching_report_column)

            # Dodanie kolumn jeśli nie istnieją
            if price_col_idx >= df.shape[1]:
                for _ in range(price_col_idx - df.shape[1] + 1):
                    df[f"Col_{df.shape[1]}"] = np.nan

            if report_col_idx >= df.shape[1]:
                for _ in range(report_col_idx - df.shape[1] + 1):
                    df[f"Col_{df.shape[1]}"] = np.nan

            # Aktualizacja cen i raportów dopasowania
            for result in matching_results:
                # Dostosowanie do nowej struktury - wf_row_index zamiast wf_row
                row_idx = result["wf_row_index"] - 1  # Konwersja na indeksowanie od 0

                if row_idx < len(df):
                    if result["matched"]:
                        df.iloc[row_idx, price_col_idx] = result["price"]

                        # Dodanie bardziej szczegółowego raportu z uwzględnieniem status dopasowania
                        status_text = (
                            result["matching_status"].replace("_", " ").capitalize()
                        )
                        df.iloc[row_idx, report_col_idx] = (
                            f"{status_text} (podobieństwo: {result['similarity']:.1f}%)"
                        )
                    else:
                        df.iloc[row_idx, report_col_idx] = "Brak dopasowania"

            # Zapisanie zmodyfikowanego pliku
            df.to_excel(target_file_path, index=False)
            return True

        except Exception as e:
            # Lepiej użyć logowania zamiast print
            logger.error(f"Błąd podczas aktualizacji pliku roboczego: {str(e)}")
            return False
