from django.urls import path
from . import api_views

urlpatterns = [
    path('courses/', api_views.CourseListAPIView.as_view(), name='api-course-list'),
    path('courses/<slug:slug>/', api_views.CourseDetailAPIView.as_view(), name='api-course-detail'),
    path('enrollments/', api_views.my_enrollments, name='api-my-enrollments'),
]
