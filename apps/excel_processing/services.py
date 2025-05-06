from venv import logger
import pandas as pd
from typing import Dict, List, Any
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

            logger.info("extract_data: Rozpoczynanie ekstrakcji danych z plików Excel")

            # Ekstrakcja danych z Working File (WF)
            working_file_data = self._extract_working_file_data(
                file_paths["working_file_path"],
                working_file["description_column"],
                working_file["description_range"],
            )
            result["working_file_data"] = working_file_data

            logger.info(
                f"extract_data: Wyekstrahowano {len(working_file_data)} rekordów z pliku roboczego WF"
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
                f"extract_data: Wyekstrahowano {len(reference_file_data)} rekordów z pliku referencyjnego REF"
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
            logger.info(
                f"_extract_working_file_data: Wczytywanie pliku roboczego: {file_path}"
            )
            df = pd.read_excel(
                file_path
            )  # typ DataFrame - wczytanie pliku excel, len(df) to ile rzędów danych wczytał Pandas z excela, 5 = 5 niepustcyh kolumn
            logger.warning(
                f"_extract_working_file_data: długość df: {len(df)} - PM: len(df)"
            )

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

            # Upewnienie się, że zakres wierszy nie wychodzi poza ramy pliku
            if end_row > len(df):
                logger.warning(
                    f"_extract_working_file_data: Zakres wierszy w WF przekracza rozmiar pliku. Dostosowano do rozmiaru: {len(df)}"
                )
                end_row = len(df)

            # Sprawdzenie czy indeks kolumny jest poprawny
            if col_index >= len(df.columns):
                raise ValueError(f"Kolumna {description_column} nie istnieje w pliku")

            # Ekstrakcja danych
            logger.info(
                f"_extract_working_file_data: Rozpoczęcie Ekstrakcja danych, zakres: {str(range(start_row, end_row))}"
            )
            result = []
            for i in range(start_row, end_row):
                # Pobieranie wartości z komórki
                cell_value = df.iloc[i - 1, col_index]

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
                    logger.info(
                        f"WF: z for+in: row_index: i+1={i+1};\n"
                        f"WF: description: {description}"
                    )

            return result

        except Exception as e:
            logger.error(
                f"Błąd podczas ekstrakcji danych z pliku roboczego WF: {str(e)}"
            )
            raise ValueError(
                f"Błąd podczas ekstrakcji danych z pliku roboczego WF: {str(e)}"
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
            logger.warning(
                f"_extract_reference_file_data: długość df w REF: {len(df)} - PM: len(df)"
            )

            # Konwersja liter kolumn na indeksy
            desc_col_index = self._column_letter_to_index(description_column)
            price_col_index = self._column_letter_to_index(price_column)

            # Konwersja zakresów na indeksy (odejmujemy 1, bo Excel zaczyna od 1, a Python od 0)
            start_row = int(description_range["start"]) - 1
            end_row = int(description_range["end"])

            # Walidacja zakresów
            if start_row < 0:
                raise ValueError(
                    f"_extract_reference_file_data: Nieprawidłowy zakres wierszy: {description_range['start']}"
                )

            # Upewnienie się, że zakres wierszy nie wychodzi poza ramy pliku
            if end_row - start_row > len(df):
                logger.warning(
                    f"_extract_reference_file_data: Zakres wierszy w pliku REF przekracza rozmiar pliku (end_row > len(df)). Dostosowano do rozmiaru: {len(df)}"
                )
                # end_row = len(df) # - chyba niepotrzebne

            # Sprawdzenie czy indeksy kolumn są poprawne
            if desc_col_index >= len(df.columns):
                raise ValueError(
                    f"Kolumna opisu {description_column} nie istnieje w pliku"
                )

            if price_col_index >= len(df.columns):
                raise ValueError(f"Kolumna ceny {price_column} nie istnieje w pliku")

            # Ekstrakcja danych
            logger.info(
                f"_extract_reference_file_data: Rozpoczęcie Ekstrakcja danych, zakres: {str(range(start_row, end_row))}"
            )
            result = []
            for i in range(start_row, end_row):
                # Pobieranie wartości z komórek
                desc_value = df.iloc[i - 1, desc_col_index]
                price_value = df.iloc[i - 1, price_col_index]

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
                        logger.info(
                            f"REF: row_index: i={i}; description: {description} - price: {price}"
                        )

                except (ValueError, TypeError):
                    logger.warning(
                        f"Nieudana konwersja ceny w wierszu {i+1}: {price_value}"
                    )
                    continue

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
            logger.info(
                f"update_working_file: Rozpoczęcie aktualizacji pliku roboczego: {source_file_path}"
            )

            # Odczyt pliku Excel
            df = pd.read_excel(source_file_path)

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

            # Sprawdź maksymalny indeks wiersza w wynikach dopasowania
            if matching_results:
                max_row_idx = max(result["wf_row_index"] for result in matching_results)

                # Dodaj brakujące wiersze jeśli to konieczne
                if max_row_idx >= len(df):
                    missing_rows = max_row_idx - len(df) + 1
                    logger.info(
                        f"update_working_file: Dodawanie {missing_rows} brakujących wierszy do DataFrame"
                    )

                    # Utworzenie nowych wierszy
                    for _ in range(missing_rows):
                        # Utwórz nowy wiersz z tą samą liczbą kolumn co DataFrame
                        new_row = pd.Series(
                            [np.nan] * len(df.columns), index=df.columns
                        )
                        # Dodaj wiersz do DataFrame
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

            # Upewnij się, że kolumna raportu ma typ object (string) zamiast float64
            # To zapobiega ostrzeżeniom o niezgodności typów przy zapisie tekstu
            # Najpierw pobieramy nazwę kolumny na podstawie indeksu
            if report_col_idx < len(df.columns):
                report_col_name = df.columns[report_col_idx]
                # Konwertowanie kolumny na typ object (string)
                df[report_col_name] = df[report_col_name].astype("object")

            # Aktualizacja cen i raportów dopasowania
            updated_rows = 0

            # TODO: TYMCZASOWE ROZWIĄZANIE - KOREKCJA PRZESUNIĘCIA INDEKSÓW
            # Problem: Istnieje niezgodność między indeksami w matching_results a faktycznymi
            # pozycjami w DataFrame. Indeksy w matching_results są przesunięte o 1 względem
            # faktycznych pozycji w DataFrame, co powoduje, że dane są zapisywane w niewłaściwych wierszach.
            #
            # Przyczyna: Prawdopodobnie algorytm generujący matching_results pomija dwa wiersze nagłówkowe,
            # ale faktycznie zaczyna liczenie od indeksu 0 dla pierwszego wiersza danych (co odpowiada
            # indeksowi 3 w DataFrame, ponieważ zawiera on nagłówki).
            #
            # Tymczasowe rozwiązanie: Odejmowanie 2 od każdego indeksu z matching_results przed użyciem go
            # w DataFrame.
            #
            # Docelowe rozwiązanie:
            # 1. Ujednolicić sposób indeksowania w całym systemie - albo wszystkie indeksy powinny
            #    uwzględniać nagłówki, albo wszystkie powinny je pomijać
            # 2. Zaimplementować mechanizm wykrywania struktury pliku (np. liczby wierszy nagłówkowych)
            #    i dynamicznie dostosowywać indeksy
            # 3. Jasno dokumentować i komunikować konwencje indeksowania używane w różnych częściach systemu

            index_offset = 2  # Wartość przesunięcia do korekcji

            for result in matching_results:
                # Pobranie oryginalnego indeksu wiersza
                original_row_idx = result["wf_row_index"]

                # Zastosowanie korekcji przesunięcia
                row_idx = original_row_idx - index_offset

                logger.info(
                    f"skorygowany/oryginalny row_idx: {row_idx}/{original_row_idx};\n"
                    f"result: {result}"
                )

                if (
                    row_idx < len(df) and row_idx >= 0
                ):  # Dodatkowe zabezpieczenie przed indeksem ujemnym
                    if result["matched"]:
                        # Aktualizacja ceny
                        df.iat[row_idx, price_col_idx] = result["price"]

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

                        # Aktualizacja raportu dopasowania (używamy iat zamiast iloc dla pojedynczych wartości)
                        report_text = (
                            f"{status_text} (podobieństwo: {similarity_formatted})"
                        )
                        # Konwertujemy wartość na string przed zapisem
                        df.iat[row_idx, report_col_idx] = report_text
                    else:
                        df.iat[row_idx, report_col_idx] = "Brak dopasowania"

                    updated_rows += 1
                else:
                    logger.warning(
                        f"update_working_file: Pominięto wiersz {row_idx} (oryginalny {original_row_idx}) - "
                        f"poza zakresem danych lub ujemny indeks"
                    )

            logger.info(
                f"update_working_file: Zaktualizowano {updated_rows} wierszy w pliku"
            )

            # Zapisanie zmodyfikowanego pliku
            df.to_excel(target_file_path, index=False)
            logger.info(
                f"update_working_file: Plik wynikowy zapisany pomyślnie pod ścieżką: {target_file_path}"
            )

            return True

        except FileNotFoundError as e:
            logger.error(f"Nie znaleziono pliku: {str(e)}")
            return False
        except PermissionError as e:
            logger.error(f"Brak uprawnień do odczytu/zapisu pliku: {str(e)}")
            return False
        except Exception as e:
            logger.error(
                f"update_working_file: Błąd podczas aktualizacji pliku roboczego: {str(e)}"
            )
            return False
