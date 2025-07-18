from datetime import date
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from django.db import transaction
from django.http import JsonResponse

from api.models import (
    ApprovalStatus,
    EmployerInvitation,
    EmployerInvitationStatus,
    ProgressStatus,
    StudentPractice,
    StudentUser,
    Practice,
)
from .serializers import (
    EmployerInvitationApprovalSerializer,
    StudentPracticeSerializer,
    ListStudentPracticeSerializer,
    StudentPracticeStatusSerializer,
)


class EmployerInvitationApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Schválí nebo zamítne employer_invitation a případně vytvoří StudentPractice záznam
        """
        serializer = EmployerInvitationApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        invitation_id = serializer.validated_data['invitation_id']
        action = serializer.validated_data['action']
        
        try:
            # Najdi invitation
            invitation = EmployerInvitation.objects.get(
                invitation_id=invitation_id,
                user=request.user
            )
        except EmployerInvitation.DoesNotExist:
            return Response(
                {"detail": "Pozvánka nebyla nalezena nebo k ní nemáte přístup."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Zkontroluj, že invitation je ve stavu PENDING
        if invitation.status != EmployerInvitationStatus.PENDING:
            return Response(
                {"detail": "Pozvánka již byla zpracována."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            if action == 'accept':
                # Změň status invitation na ACCEPTED
                invitation.status = EmployerInvitationStatus.ACCEPTED
                invitation.save()
                
                # Vytvoř StudentPractice záznam
                student_practice = StudentPractice.objects.create(
                    user=request.user,
                    practice=invitation.practice,
                    application_date=date.today(),
                    approval_status=ApprovalStatus.APPROVED,  # Automaticky schváleno
                    progress_status=ProgressStatus.IN_PROGRESS,  # Probíhá
                    hours_completed=0,
                    year=date.today().year
                )
                
                return Response({
                    "detail": "Pozvánka byla přijata a praxe byla zahájena.",
                    "student_practice_id": student_practice.student_practice_id
                }, status=status.HTTP_200_OK)
                
            elif action == 'reject':
                invitation.status = EmployerInvitationStatus.REJECTED
                invitation.save()
                
                return Response({
                    "detail": "Pozvánka byla zamítnuta."
                }, status=status.HTTP_200_OK)
        
        return Response(
            {"detail": "Neplatná akce."},
            status=status.HTTP_400_BAD_REQUEST
        )


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
