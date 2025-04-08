# /apps/matching_engine/services.py
from typing import Any, Dict, List


class MatchingEngineService:
    def match_descriptions(
        self, session_id: str, matching_threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Dopasowuje opisy z pliku roboczego (WF) do opisów z pliku referencyjnego (REF)
        na podstawie ich embeddingów i zwraca listę wyników dopasowania.

        Proces dopasowania obejmuje:
        1. Pobranie opisów i embeddingów dla danej sesji z bazy danych
        2. Obliczenie podobieństwa semantycznego między opisami z WF i REF
        3. Znalezienie najlepszych dopasowań spełniających próg podobieństwa
        4. Przypisanie cen jednostkowych z REF do pozycji w WF na podstawie dopasowań

        Args:
            session_id (str): Identyfikator sesji przetwarzania, służący do pobierania
                            opisów i embeddingów z bazy danych. Musi być poprawnym UUID.
            matching_threshold (float): Próg podobieństwa (0 - 100) wymagany do uznania dopasowania.
                                    Opisy o podobieństwie niższym niż próg nie będą dopasowane.

        Returns:
            List[Dict[str, Any]]: Lista słowników zawierających wyniki dopasowania,
                                każdy dla jednego opisu z WF:
                [
                    {
                        "wf_row_index": int,  # Indeks wiersza w pliku WF
                        "wf_description": str,  # Opis z pliku WF
                        "matched": bool,  # Czy znaleziono dopasowanie
                        "ref_row_index": int | None,  # Indeks wiersza w pliku REF (jeśli dopasowano)
                        "ref_description": str | None,  # Opis z pliku REF (jeśli dopasowano)
                        "similarity": float | None,  # Wartość podobieństwa (jeśli dopasowano)
                        "price": float | None,  # Cena jednostkowa z REF (jeśli dopasowano)
                        "matching_status": str,  # Status dopasowania ("matched", "no_match", "multiple_matches_best_selected")
                    },
                    ...
                ]

        Raises:
            ValueError: Gdy session_id jest nieprawidłowe lub nie istnieje w bazie danych.
            ValueError: Gdy matching_threshold jest poza zakresem 0.0-1.0.
            DatabaseError: Gdy wystąpi problem z dostępem do bazy danych.
            EmbeddingError: Gdy brakuje embeddingów dla opisów w bazie danych.
        """
        pass
