from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Course, Enrollment
from .serializers import CourseListSerializer, CourseSerializer, EnrollmentSerializer


class CourseListAPIView(generics.ListAPIView):
    serializer_class = CourseListSerializer
    permission_classes = []

    def get_queryset(self):
        qs = Course.objects.filter(is_published=True)
        category = self.request.query_params.get('category')
        level = self.request.query_params.get('level')
        if category:
            qs = qs.filter(category=category)
        if level:
            qs = qs.filter(level=level)
        return qs


class CourseDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CourseSerializer
    permission_classes = []
    lookup_field = 'slug'
    queryset = Course.objects.filter(is_published=True)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_enrollments(request):
    enrollments = Enrollment.objects.filter(student=request.user, is_active=True)
    serializer = EnrollmentSerializer(enrollments, many=True)
    return Response(serializer.data)
