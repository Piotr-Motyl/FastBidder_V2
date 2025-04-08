from typing import Any, Dict
from apps.file_management.services import FileManagementService
from apps.excel_processing.services import ExcelProcessingService
from apps.orchestrator.serializers import CompareFilesRequestSerializer
from apps.semantic_analysis.services import SemanticAnalysisService
from apps.matching_engine.services import MatchingEngineService
from apps.processing_data.services import ProcessingDataService


class OrchestratorService:
    def __init__(self):
        self.file_service = FileManagementService()
        self.excel_service = ExcelProcessingService()
        self.semantic_service = SemanticAnalysisService()
        self.matching_service = MatchingEngineService()
        self.processing_service = ProcessingDataService()

    def compare_files(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Główna metoda koordynująca cały proces porównania plików.

        Parametry:
            request_data: Słownik zawierający parametry porównania
                {
                    "working_file": {
                        "file_path": str,
                        "description_column": str,
                        "description_range": {"start": str, "end": str},
                        "price_target_column": str,
                        "matching_report_column": str
                    },
                    "reference_file": {
                        "file_path": str,
                        "description_column": str,
                        "description_range": {"start": str, "end": str},
                        "price_source_column": str
                    },
                    "matching_threshold": int  # Próg podobieństwa (0-100)
                }

        Zwraca:
            Słownik zawierający wyniki porównania:
            {
                "status": str,  # "success" lub "error"
                "modified_file_path": str,  # Ścieżka do zmodyfikowanego pliku (jeśli success)
                "matching_summary": {  # Podsumowanie dopasowań (jeśli success)
                    "total_items": int,  # Łączna liczba pozycji
                    "matched_items": int,  # Liczba dopasowanych pozycji
                    "unmatched_items": int  # Liczba niedopasowanych pozycji
                },
                "error_message": str  # Komunikat błędu (jeśli status="error")
            }
        """
        try:
            # 1a. Walidacja parametrów wejściowych za pomocą serializatora
            serializer = CompareFilesRequestSerializer(data=request_data)
            if not serializer.is_valid():
                return {
                    "status": "error",
                    "error_message": "Nieprawidłowe parametry wejściowe",
                    "validation_errors": serializer.errors,
                }

            # 1b. Pobranie zwalidowanych danych
            validated_data = serializer.validated_data
            working_file = validated_data["working_file"]
            reference_file = validated_data["reference_file"]
            matching_threshold = validated_data["matching_threshold"]

            # 2. Walidacja plików
            validation_result = self.file_service.validate_files(
                working_file["file_path"], reference_file["file_path"]
            )
            if not validation_result["valid"]:
                return {
                    "status": "error",
                    "error_message": f"Nieprawidłowe pliki: {', '.join(validation_result['errors'])}",
                }

            # 3. Pobranie ścieżek do plików
            file_paths = self.file_service.get_file_paths(
                working_file["file_path"], reference_file["file_path"]
            )

            # 4. Ekstrakcja danych z plików Excel
            extracted_data = self.excel_service.extract_data(
                file_paths, working_file, reference_file
            )
            # Sprawdzamy czy extract_data zwróciło poprawne dane
            if (
                not isinstance(extracted_data, dict)
                or "working_file_data" not in extracted_data
                or "reference_file_data" not in extracted_data
            ):
                return {
                    "status": "error",
                    "error_message": "Błąd podczas ekstrakcji danych",
                }

            wf_descriptions = extracted_data["working_file_data"]
            ref_descriptions = extracted_data["reference_file_data"]

            # 5. Przechowanie opisów
            try:
                storage_result = self.processing_service.store_descriptions(
                    wf_descriptions, ref_descriptions
                )
                session_id = storage_result["session_id"]

            except Exception as e:
                return {
                    "status": "error",
                    "error_message": f"Błąd podczas przechowywania opisów: {str(e)}",
                }

            # 6. Generowanie embeddingów
            try:
                # Generowanie embeddings an podstawie session_id
                embedding_result = self.semantic_service.generate_embeddings(session_id)
            except Exception as e:
                return {
                    "status": "error",
                    "error_message": f"Błąd podczas generowania embeddingów: {str(e)}",
                }

            # 7. Dopasowanie opisów
            try:
                matching_results = self.matching_service.match_descriptions(
                    session_id, matching_threshold
                )
            except Exception as e:
                return {
                    "status": "error",
                    "error_message": f"Błąd podczas dopasowywania opisów: {str(e)}",
                }

            # 8. Przechowanie wyników dopasowania
            results_stored = self.processing_service.store_matching_results(
                matching_results, session_id
            )
            if not results_stored:
                return {
                    "status": "error",
                    "error_message": "Błąd podczas przechowywania wyników",
                }

            # 9. Uzyskanie ścieżki do zapisania wynikowego pliku
            result_file_path = self.file_service.get_result_file_path(
                working_file["file_path"]
            )

            # 10. Aktualizacja pliku WF
            file_updated = self.excel_service.update_working_file(
                matching_results,
                file_paths["working_file_path"],
                result_file_path,
                working_file["price_target_column"],
                working_file["matching_report_column"],
            )
            if not file_updated:
                return {
                    "status": "error",
                    "error_message": "Błąd podczas aktualizacji pliku",
                }

            # 11. Wyczyszczenie danych tymczasowych
            self.processing_service.clear_data(session_id)

            # 12. Zwrócenie wyniku
            matched_count = sum(1 for result in matching_results if result["matched"])
            total_count = len(matching_results)

            return {
                "status": "success",
                "modified_file_path": result_file_path,
                "matching_summary": {
                    "total_items": total_count,
                    "matched_items": matched_count,
                    "unmatched_items": total_count - matched_count,
                },
            }
        except Exception as e:
            return {"status": "error", "error_message": str(e)}
