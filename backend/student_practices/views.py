from api.models import Practice, StudentPractice
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated

from .serializers import ListStudentPracticeSerializer


class StudentPracticeListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ListStudentPracticeSerializer

    def get_queryset(self):
        # Tohle má být probíhajících praxí po prokliknutí na specifickou praxi
        practice_id = self.kwargs.get("practice_id")

        if not practice_id:
            return JsonResponse({"error": "practice_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        practice = Practice.objects.filter(practice_id=practice_id).first()
        if not practice:
            return JsonResponse({"error": "Practice not found"}, status=status.HTTP_404_NOT_FOUND)

            # Filter student practices by practice_id
        return StudentPractice.objects.filter(practice=practice).all()
