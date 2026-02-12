from django.urls import path
from . import api_views

urlpatterns = [
    path('accounts/me/', api_views.CurrentUserView.as_view(), name='api-current-user'),
    path('accounts/students/<int:pk>/status/', api_views.update_student_status, name='api-student-status'),
]
