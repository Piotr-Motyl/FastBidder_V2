from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import CompareFilesRequestSerializer
from .services import OrchestratorService


@api_view(["POST"])
def compare_files(request):
    """
    Endpoint do porównywania plików.
    """
    serializer = CompareFilesRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    orchestrator = OrchestratorService()
    result = orchestrator.compare_files(serializer.validated_data)

    return Response(result)
