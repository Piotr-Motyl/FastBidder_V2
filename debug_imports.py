import sys
import os
import traceback

# Dodaj katalog projektu do ścieżki Pythona
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_import(module_name):
    try:
        print(f"Próba importu: {module_name}")
        __import__(module_name)
        print(f"Import udany: {module_name}")
        return True
    except Exception as e:
        print(f"Błąd importu {module_name}: {e}")
        traceback.print_exc()
        return False


# Sprawdź podstawowe moduły Django
test_import("django")
test_import("rest_framework")


# Sprawdź poszczególne klasy serwisów
modules_to_test = [
    "apps.file_management.services",
    "apps.excel_processing.services",
    "apps.semantic_analysis.services",
    "apps.matching_engine.services",
    "apps.processing_data.services",
]
print("START - for module in modules_to_test:")
for module in modules_to_test:
    test_import(module)
print("KONIEC - for module in modules_to_test:")


# Sprawdź moduły FastBidder
test_import("apps")
test_import("apps.orchestrator")
test_import("apps.orchestrator.services")
