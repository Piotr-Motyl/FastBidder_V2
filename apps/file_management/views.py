from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import FileUploadSerializer
from .services import FileManagementService


@api_view(["POST"])
def upload_file(request):
    """
    Endpoint do wgrywania plików Excel.
    """
    serializer = FileUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    file_service = FileManagementService()
    result = file_service.upload_file(
        serializer.validated_data["file"], serializer.validated_data["file_type"]
    )

    return Response(result, status=status.HTTP_201_CREATED)
