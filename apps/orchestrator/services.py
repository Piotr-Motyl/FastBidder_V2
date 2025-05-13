import time
from typing import Any, Dict
from venv import logger
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
        The main method coordinating the entire file comparison process.

        Parameters:
            Request_data: Dictionary containing comparison parameters
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
                    "matching_threshold": int  # Similarity threshold (0-100)
                }

        Returns:
            Dictionary containing comparison results:
            {
                "status": str,  # "success" lub "error"
                "modified_file_path": str,  # Path to a modified file (if Success)
                "matching_summary": {  # Summary of fittings (if Success)
                    "total_items": int,  # Total number of items
                    "matched_items": int,  # Number of matching items
                    "unmatched_items": int  # Number of mismatched items
                },
                "error_message": str  # Komunikat błędu (jeśli status="error")
            }
        """
        # Measurement of the method of performing the method - Start
        start_time = time.time()

        try:
            # 1a Validation of input parameters using a series
            serializer = CompareFilesRequestSerializer(data=request_data)
            if not serializer.is_valid():
                return {
                    "status": "error",
                    "error_message": "Incorrect input parameters",
                    "validation_errors": serializer.errors,
                }

            # 1b. Downloads of freed data
            validated_data = serializer.validated_data
            working_file = validated_data["working_file"]
            reference_file = validated_data["reference_file"]
            matching_threshold = validated_data["matching_threshold"]

            # 2. File validation
            validation_result = self.file_service.validate_files(
                working_file["file_path"], reference_file["file_path"]
            )
            if not validation_result["valid"]:
                return {
                    "status": "error",
                    "error_message": f"Incorrect files: {', '.join(validation_result['errors'])}",
                }

            # 3. Downloading paths to files
            file_paths = self.file_service.get_file_paths(
                working_file["file_path"], reference_file["file_path"]
            )

            # 4. Data extraction from Excel files
            extracted_data = self.excel_service.extract_data(
                file_paths, working_file, reference_file
            )
            # We check if Extract_Data returned the correct data
            if (
                not isinstance(extracted_data, dict)
                or "working_file_data" not in extracted_data
                or "reference_file_data" not in extracted_data
            ):
                return {
                    "status": "error",
                    "error_message": "Error during data extraction",
                }

            wf_descriptions = extracted_data["working_file_data"]
            ref_descriptions = extracted_data["reference_file_data"]

            # 5. Storage of descriptions
            try:
                storage_result = self.processing_service.store_descriptions(
                    wf_descriptions, ref_descriptions
                )
                session_id = storage_result["session_id"]

            except Exception as e:
                return {
                    "status": "error",
                    "error_message": f"Error while storing descriptions: {str(e)}",
                }

            # 6. Generating embedding
            try:
                # Generation Embeddings an based on session_id
                embedding_result = self.semantic_service.generate_embeddings(session_id)
            except Exception as e:
                return {
                    "status": "error",
                    "error_message": f"Error while generating embedding: {str(e)}",
                }

            # 7. Adjusting descriptions
            try:
                matching_results = self.matching_service.match_descriptions(
                    session_id, matching_threshold
                )
            except Exception as e:
                return {
                    "status": "error",
                    "error_message": f"Error when adjusting the descriptions: {str(e)}",
                }

            # 8. Storage of matching results
            results_stored = self.processing_service.store_matching_results(
                matching_results, session_id
            )
            if not results_stored:
                return {
                    "status": "error",
                    "error_message": "Error while storing results",
                }

            # 9. Obtaining a path to save the resulting file
            result_file_path = self.file_service.get_result_file_path(
                working_file["file_path"]
            )

            # 10. PE file update
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
                    "error_message": "Error while updating the file",
                }

            # 11. Cleaning temporary data
            self.processing_service.clear_data(session_id)

            # 12. Return the result
            matched_count = sum(1 for result in matching_results if result["matched"])
            total_count = len(matching_results)

            # Measurement of the method of performing the method - End
            end_time = time.time()
            execution_time = end_time - start_time
            # TODO: Add time information on the frontend

            logger.info(
                f"Time of making the method compare_files(): {execution_time} sec."
            )

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
