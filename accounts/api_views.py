from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import CustomUser
from .serializers import UserSerializer, StudentListSerializer, UserStatusUpdateSerializer
from notifications.utils import create_notification


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_student_status(request, pk):
    """Admin: Approve/Reject/Suspend student."""
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    serializer = UserStatusUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        student = CustomUser.objects.get(pk=pk, role='student')
    except CustomUser.DoesNotExist:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

    new_status = serializer.validated_data['status']
    student.status = new_status
    student.save()

    # Send notification to student
    status_messages = {
        'approved': 'Your account has been approved! You can now enroll in courses.',
        'rejected': 'Your account registration has been declined.',
        'suspended': 'Your account has been suspended.',
    }
    create_notification(
        recipient=student,
        title=f'Account {new_status.title()}',
        message=status_messages.get(new_status, ''),
        notification_type='success' if new_status == 'approved' else 'warning',
        link='/dashboard/' if new_status == 'approved' else None
    )

    return Response({
        'message': f'Student {new_status} successfully.',
        'student': StudentListSerializer(student).data
    })
