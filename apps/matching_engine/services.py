import logging
from typing import Any, Dict, List
import numpy as np
import pickle
import uuid
from django.db.models import QuerySet

from apps.processing_data.models import (
    ProcessingSession,
    WorkingFileDescription,
    ReferenceFileDescription,
)


class EmbeddingError(Exception):
    """Wyjątek zgłaszany przy problemach z embeddingami."""

    pass


class MatchingEngineService:
    def __init__(self):
        self.Logger = logging.getLogger(__name__)

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
        # Sprawdzenie czy session_id jest poprawnym UUID
        try:
            uuid.UUID(session_id)
        except ValueError:
            raise ValueError(f"Nieprawidłowy format session_id: {session_id}")

        # Sprawdzenie zakresu matching_threshold i konwersja do zakresu 0-1
        if not (0 <= matching_threshold <= 100):
            raise ValueError(
                f"Próg dopasowania musi być w zakresie 0-100, otrzymano: {matching_threshold}"
            )

        # Konwersja progu podobieństwa z zakresu 0-100 do 0-1
        threshold = matching_threshold

        # Pobranie opisów z bazy danych
        try:
            # Sprawdzenie czy sesja istnieje
            session = ProcessingSession.objects.filter(id=session_id).first()
            if not session:
                raise ValueError(f"Nie znaleziono sesji o id: {session_id}")

            # Pobranie opisów WF z embeddingami
            wf_descriptions = WorkingFileDescription.objects.filter(
                session_id=session_id
            )
            # Pobranie opisów REF z cenami i embeddingami
            ref_descriptions = ReferenceFileDescription.objects.filter(
                session_id=session_id
            )

            if not wf_descriptions:
                raise ValueError(f"Nie znaleziono opisów WF dla sesji: {session_id}")
            if not ref_descriptions:
                raise ValueError(f"Nie znaleziono opisów REF dla sesji: {session_id}")

            # Sprawdzenie czy wszystkie opisy mają embeddingi
            if any(desc.embedding is None for desc in wf_descriptions):
                raise EmbeddingError(
                    "Niektóre opisy WF nie mają wygenerowanych embeddingów"
                )
            if any(desc.embedding is None for desc in ref_descriptions):
                raise EmbeddingError(
                    "Niektóre opisy REF nie mają wygenerowanych embeddingów"
                )

            # Przygotowanie wyników dopasowania
            matching_results = self._calculate_embeddings_similarity(
                wf_descriptions, ref_descriptions, threshold
            )

            # Logowanie wyników dopasowania
            matched_count = sum(1 for result in matching_results if result["matched"])
            self.logger.info(
                f"Znaleziono dopasowania dla {matched_count} z {len(matching_results)} opisów"
            )

            return matching_results

        except Exception as e:
            # Propagowanie błędów w górę
            if isinstance(e, (ValueError, EmbeddingError)):
                raise
            raise Exception(f"Błąd podczas dopasowywania opisów: {str(e)}")

    def _calculate_embeddings_similarity(
        self, wf_descriptions: QuerySet, ref_descriptions: QuerySet, threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Oblicza podobieństwo między embeddingami opisów WF i REF,
        znajduje najlepsze dopasowania i tworzy listę wyników.

        Args:
            wf_descriptions: QuerySet z opisami WF
            ref_descriptions: QuerySet z opisami REF
            threshold: Próg podobieństwa (0-100)

        Returns:
            Lista wyników dopasowania
        """
        # Deserializacja embeddingów
        wf_embeddings = []
        ref_embeddings = []

        # Przygotowanie danych dla opisów WF
        wf_data = []
        for wf in wf_descriptions:
            wf_data.append(
                {"wf_row_index": wf.row_index, "wf_description": wf.description}
            )
            wf_embeddings.append(pickle.loads(wf.embedding))

        # Przygotowanie danych dla opisów REF
        ref_data = []
        for ref in ref_descriptions:
            ref_data.append(
                {
                    "ref_row_index": ref.row_index,
                    "ref_description": ref.description,
                    "price": float(ref.price),
                }
            )
            ref_embeddings.append(pickle.loads(ref.embedding))

        # Konwersja list embeddingów na tablice numpy dla efektywności
        wf_emb_array = np.array(wf_embeddings)
        ref_emb_array = np.array(ref_embeddings)

        # Normalizacja embeddingów dla podobieństwa kosinusowego
        wf_emb_norm = wf_emb_array / np.linalg.norm(wf_emb_array, axis=1, keepdims=True)
        ref_emb_norm = ref_emb_array / np.linalg.norm(
            ref_emb_array, axis=1, keepdims=True
        )

        # Obliczenie podobieństwa kosinusowego między wszystkimi parami embeddingów
        # Wynik to macierz podobieństwa [liczba_wf x liczba_ref]
        # Wartości podobieństwa są w zakresie 0-1, więc mnożymy przez 100 dla uzyskania zakresu 0-100
        similarity_matrix = np.dot(wf_emb_norm, ref_emb_norm.T) * 100
        # Zaokrąglenie do 2 miejsc po przecinku dla czytelności
        similarity_matrix = np.round(similarity_matrix, 2)

        # Przygotowanie listy wyników
        matching_results = []

        # Dla każdego opisu WF znajdź najlepsze dopasowanie
        for i, wf in enumerate(wf_data):
            # Pobranie podobieństw dla aktualnego opisu WF
            similarities = similarity_matrix[i]

            # Inicjalizacja wyniku
            result = {
                "wf_row_index": wf["wf_row_index"],
                "wf_description": wf["wf_description"],
                "matched": False,
                "ref_row_index": None,
                "ref_description": None,
                "similarity": None,
                "price": None,
                "matching_status": "no_match",
            }

            # Sprawdzenie czy istnieją dopasowania powyżej progu
            matches_indices = np.where(similarities >= threshold)[0]

            if len(matches_indices) > 0:
                # Znaleziono co najmniej jedno dopasowanie
                # Znajdź indeks najlepszego dopasowania
                best_match_idx = matches_indices[
                    np.argmax(similarities[matches_indices])
                ]
                best_similarity = similarities[best_match_idx]

                # Sprawdź czy istnieje więcej dopasowań z taką samą wartością podobieństwa
                best_matches = np.where(similarities == best_similarity)[0]

                # FIX: Priorytetyzuj dokładne dopasowania (100% podobieństwa) lub dokładne dopasowanie tekstu
                exact_text_match = None
                for idx in best_matches:
                    if (
                        similarities[idx] == 100.0
                        or wf["wf_description"].strip()
                        == ref_data[idx]["ref_description"].strip()
                    ):
                        exact_text_match = idx
                        break

                # Jeśli znaleziono dokładne dopasowanie tekstu, użyj go zamiast pierwszego najlepszego
                ref_idx = (
                    exact_text_match if exact_text_match is not None else best_match_idx
                )

                # Log istotne informacje dla debugowania
                if len(best_matches) > 1:
                    self.logger.debug(
                        f"Znaleziono {len(best_matches)} dopasowań z podobieństwem {best_similarity}% "
                        f"dla opisu WF: '{wf['wf_description']}', wiersz {wf['wf_row_index']}"
                    )
                    for idx in best_matches:
                        self.logger.debug(
                            f"  Dopasowanie REF {idx}: '{ref_data[idx]['ref_description']}', "
                            f"wiersz {ref_data[idx]['ref_row_index']}, cena: {ref_data[idx]['price']}"
                        )

                ref_match = ref_data[ref_idx]

                result.update(
                    {
                        "matched": True,
                        "ref_row_index": ref_match["ref_row_index"],
                        "ref_description": ref_match["ref_description"],
                        "similarity": float(
                            best_similarity
                        ),  # Konwersja z numpy.float do Python float
                        "price": ref_match["price"],
                        "matching_status": (
                            "multiple_matches_best_selected"
                            if len(best_matches) > 1
                            else "matched"
                        ),
                    }
                )

            matching_results.append(result)

        return matching_results
