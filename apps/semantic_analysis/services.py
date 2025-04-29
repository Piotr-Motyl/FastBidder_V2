import uuid
import pickle
import logging
from typing import Dict, Any, List, Tuple
from django.db import transaction
from fastembed import TextEmbedding
from django.db.utils import DatabaseError
import numpy as np

from apps.processing_data.models import (
    ProcessingSession,
    WorkingFileDescription,
    ReferenceFileDescription,
)
from .exceptions import EmbeddingGenerationError

logger = logging.getLogger(__name__)


class SemanticAnalysisService:
    """
    Serwis odpowiedzialny za analizę semantyczną opisów i generowanie embeddingów.
    """

    def __init__(self):
        """
        Inicjalizuje serwis SemanticAnalysisService.
        Model embeddingów jest inicjalizowany przy pierwszym użyciu (lazy loading).
        """
        self._embedding_model = None
        self._model_name = "BAAI/bge-small-en-v1.5"
        self._batch_size = 32  # Rozmiar wsadowy dla przetwarzania wsadowego

    @property
    def embedding_model(self):
        """
        Właściwość zapewniająca lazy-loading modelu embeddingów.
        Model jest ładowany tylko wtedy, gdy jest potrzebny.

        Returns:
            TextEmbedding: Załadowany model embeddingów
        """
        if self._embedding_model is None:
            logger.info(f"Inicjalizacja modelu embeddingów: {self._model_name}")
            self._embedding_model = TextEmbedding(self._model_name)
        return self._embedding_model

    def generate_embeddings(self, session_id: str) -> Dict[str, Any]:
        """
        Generuje embeddingi dla opisów z plików WF i REF na podstawie identyfikatora sesji
        i zapisuje je w bazie danych.

        Proces obejmuje:
        1. Pobieranie opisów z bazy danych dla danej sesji przetwarzania
        2. Generowanie embeddingów dla każdego opisu przy użyciu modelu NLP
        3. Zapisywanie wygenerowanych embeddingów w bazie danych

        Args:
            session_id (str): Identyfikator sesji przetwarzania, służący do pobierania
                            opisów z bazy danych. Musi być poprawnym UUID.

        Returns:
            Dict[str, Any]: Słownik z informacjami o wygenerowanych embeddingach:
                {
                    "status": str,  # "success" lub "partial_success"
                    "embeddings_generated": int,  # Całkowita liczba wygenerowanych embeddingów
                    "model_info": str,  # Informacja o użytym modelu
                }

        Raises:
            ValueError: Gdy session_id jest nieprawidłowe lub nie istnieje w bazie danych.
            DatabaseError: Gdy wystąpi problem z dostępem do bazy danych.
            EmbeddingGenerationError: Gdy nie udało się wygenerować embeddingów.
        """
        try:
            # Konwersja session_id na UUID jeśli podano jako string
            session_uuid = self._validate_session_id(session_id)

            # Pobieranie sesji i sprawdzenie czy istnieje
            session = self._get_session(session_uuid)

            # Pobieranie opisów z bazy danych
            working_descriptions, reference_descriptions = self._get_descriptions(
                session
            )

            if not working_descriptions and not reference_descriptions:
                raise ValueError(f"Brak opisów w bazie danych dla sesji: {session_id}")

            # Generowanie i zapisywanie embeddingów dla opisów z pliku roboczego
            wf_success_count = self._process_working_descriptions(working_descriptions)

            # Generowanie i zapisywanie embeddingów dla opisów z pliku referencyjnego
            ref_success_count = self._process_reference_descriptions(
                reference_descriptions
            )

            # Ustalenie statusu operacji
            total_success = wf_success_count + ref_success_count
            total_descriptions = len(working_descriptions) + len(reference_descriptions)

            status = "success"
            if total_success < total_descriptions:
                status = "partial_success"
                logger.warning(
                    f"Niektóre embeddingi nie zostały wygenerowane. "
                    f"Sukces: {total_success}/{total_descriptions}"
                )

            return {
                "status": status,
                "embeddings_generated": total_success,
                "model_info": self._model_name,
            }

        except ValueError as ve:
            logger.error(f"Błąd walidacji: {str(ve)}")
            raise
        except DatabaseError as dbe:
            logger.error(f"Błąd bazy danych: {str(dbe)}")
            raise
        except Exception as e:
            logger.error(f"Błąd podczas generowania embeddingów: {str(e)}")
            raise EmbeddingGenerationError(
                f"Nie udało się wygenerować embeddingów: {str(e)}"
            )

    def _validate_session_id(self, session_id: str) -> uuid.UUID:
        """
        Waliduje i konwertuje identyfikator sesji na obiekt UUID.

        Args:
            session_id: Identyfikator sesji jako string lub UUID

        Returns:
            uuid.UUID: Zwalidowany obiekt UUID

        Raises:
            ValueError: Jeśli session_id jest nieprawidłowym UUID
        """
        try:
            if isinstance(session_id, str):
                return uuid.UUID(session_id)
            elif isinstance(session_id, uuid.UUID):
                return session_id
            else:
                raise ValueError(
                    f"Identyfikator sesji musi być typu str lub uuid.UUID, otrzymano: {type(session_id)}"
                )
        except ValueError:
            raise ValueError(f"Nieprawidłowy format UUID: {session_id}")

    def _get_session(self, session_uuid: uuid.UUID) -> ProcessingSession:
        """
        Pobiera sesję przetwarzania z bazy danych.

        Args:
            session_uuid: Identyfikator sesji jako UUID

        Returns:
            ProcessingSession: Obiekt sesji przetwarzania

        Raises:
            ValueError: Jeśli sesja o podanym ID nie istnieje
        """
        try:
            return ProcessingSession.objects.get(id=session_uuid)
        except ProcessingSession.DoesNotExist:
            raise ValueError(f"Sesja o ID {session_uuid} nie istnieje")

    def _get_descriptions(
        self, session: ProcessingSession
    ) -> Tuple[List[WorkingFileDescription], List[ReferenceFileDescription]]:
        """
        Pobiera opisy z plików roboczego i referencyjnego dla danej sesji.

        Args:
            session: Obiekt sesji przetwarzania

        Returns:
            Tuple[List[WorkingFileDescription], List[ReferenceFileDescription]]:
                Krotka z listami opisów z plików WF i REF
        """
        working_descriptions = list(
            WorkingFileDescription.objects.filter(session=session)
        )
        reference_descriptions = list(
            ReferenceFileDescription.objects.filter(session=session)
        )

        return working_descriptions, reference_descriptions

    def _generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generuje embeddingi dla wsadu tekstów.

        Args:
            texts: Lista tekstów do przetworzenia

        Returns:
            List[np.ndarray]: Lista wektorów embeddingów dla podanych tekstów
        """
        # Wywołanie modelu do generowania embeddingów
        embeddings = list(self.embedding_model.embed(texts))
        return embeddings

    def _serialize_embedding(self, embedding: np.ndarray) -> bytes:
        """
        Serializuje wektor embeddingu do formatu binarnego.

        Args:
            embedding: Wektor embeddingu jako tablica numpy

        Returns:
            bytes: Serializowany embedding
        """
        return pickle.dumps(embedding)

    def _process_working_descriptions(
        self, descriptions: List[WorkingFileDescription]
    ) -> int:
        """
        Przetwarza opisy z pliku roboczego wsadowo, generuje embeddingi i zapisuje je w bazie danych.

        Args:
            descriptions: Lista obiektów opisów z pliku roboczego

        Returns:
            int: Liczba opisów, dla których pomyślnie wygenerowano embeddingi
        """
        success_count = 0

        # Przetwarzanie partiami, aby zmniejszyć zużycie pamięci
        for i in range(0, len(descriptions), self._batch_size):
            batch = descriptions[i : i + self._batch_size]
            texts = [desc.description for desc in batch]

            try:
                # Generowanie embeddingów dla wsadu
                embeddings = self._generate_embeddings_batch(texts)

                # Zapisanie embeddingów w bazie danych
                with transaction.atomic():
                    for j, desc in enumerate(batch):
                        if j < len(
                            embeddings
                        ):  # Zabezpieczenie przed niezgodnością długości list
                            desc.embedding = self._serialize_embedding(embeddings[j])
                            desc.save(update_fields=["embedding"])
                            success_count += 1
            except Exception as e:
                logger.error(
                    f"Błąd podczas przetwarzania wsadu WF {i}-{i+len(batch)}: {str(e)}"
                )
                # Kontynuujemy z kolejnymi wsadami mimo błędu

        return success_count

    def _process_reference_descriptions(
        self, descriptions: List[ReferenceFileDescription]
    ) -> int:
        """
        Przetwarza opisy z pliku referencyjnego wsadowo, generuje embeddingi i zapisuje je w bazie danych.

        Args:
            descriptions: Lista obiektów opisów z pliku referencyjnego

        Returns:
            int: Liczba opisów, dla których pomyślnie wygenerowano embeddingi
        """
        success_count = 0

        # Przetwarzanie partiami, aby zmniejszyć zużycie pamięci
        for i in range(0, len(descriptions), self._batch_size):
            batch = descriptions[i : i + self._batch_size]
            texts = [desc.description for desc in batch]

            try:
                # Generowanie embeddingów dla wsadu
                embeddings = self._generate_embeddings_batch(texts)

                # Zapisanie embeddingów w bazie danych
                with transaction.atomic():
                    for j, desc in enumerate(batch):
                        if j < len(
                            embeddings
                        ):  # Zabezpieczenie przed niezgodnością długości list
                            desc.embedding = self._serialize_embedding(embeddings[j])
                            desc.save(update_fields=["embedding"])
                            success_count += 1
            except Exception as e:
                logger.error(
                    f"Błąd podczas przetwarzania wsadu REF {i}-{i+len(batch)}: {str(e)}"
                )
                # Kontynuujemy z kolejnymi wsadami mimo błędu

        return success_count
