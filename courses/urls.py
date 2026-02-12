from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='list'),
    path('<slug:slug>/', views.course_detail, name='detail'),
    path('<slug:slug>/enroll/', views.enroll_course, name='enroll'),
    path('<slug:slug>/module/<int:module_id>/', views.module_detail, name='module_detail'),
    path('<slug:slug>/module/<int:module_id>/exercise/<int:exercise_id>/', views.submit_exercise, name='submit_exercise'),
    path('<slug:slug>/module/<int:module_id>/exercise/<int:exercise_id>/result/', views.submission_result, name='submission_result'),
]