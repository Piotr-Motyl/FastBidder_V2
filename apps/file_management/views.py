from django.http import JsonResponse
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from .services import FileManagementService


@api_view(["POST"])
@parser_classes([MultiPartParser])
def upload_file(request):
    """
    Endpoint do wgrywania plików Excel (WF lub REF)
    """
    if "file" not in request.FILES:
        return JsonResponse(
            {"error": "Brak pliku w żądaniu"}, status=status.HTTP_400_BAD_REQUEST
        )

    file_type = request.data.get("file_type")
    if file_type not in ["WF", "REF"]:
        return JsonResponse(
            {"error": "Nieprawidłowy typ pliku. Dozwolone wartości: 'WF' lub 'REF'"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        service = FileManagementService()
        result = service.upload_file(request.FILES["file"], file_type)
        return JsonResponse(result, status=status.HTTP_201_CREATED)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except IOError as e:
        return JsonResponse(
            {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return JsonResponse(
            {"error": f"Wystąpił nieoczekiwany błąd: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
