from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),

    # Student
    path('student/', views.student_dashboard, name='student_dashboard'),

    # Mentor
    path('mentor/', views.mentor_dashboard, name='mentor_dashboard'),
    path('mentor/course/<slug:slug>/', views.mentor_course_detail, name='mentor_course_detail'),
    path('mentor/grade/<int:submission_id>/', views.grade_submission, name='grade_submission'),
    path('mentor/approve/<int:enrollment_id>/', views.approve_completion, name='approve_completion'),
    path('mentor/course/<slug:slug>/students/', views.mentor_students, name='mentor_students'),
    path('mentor/course/<slug:slug>/announce/', views.mentor_announcements, name='mentor_announcements'),
    path('mentor/course/<slug:slug>/bulk-grade/', views.mentor_bulk_grade, name='mentor_bulk_grade'),
    path('mentor/course/<slug:slug>/analytics/', views.mentor_course_analytics, name='mentor_course_analytics'),

    # Admin
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/students/', views.admin_students, name='admin_students'),
    path('admin-panel/students/<int:pk>/approve/', views.admin_approve_student, name='admin_approve_student'),
    path('admin-panel/students/<int:pk>/reject/', views.admin_reject_student, name='admin_reject_student'),
    path('admin-panel/mentors/', views.admin_mentors, name='admin_mentors'),
    path('admin-panel/mentors/create/', views.admin_create_mentor, name='admin_create_mentor'),
    path('admin-panel/courses/', views.admin_courses, name='admin_courses'),
    path('admin-panel/courses/create/', views.admin_create_course, name='admin_create_course'),
    path('admin-panel/courses/<slug:slug>/edit/', views.admin_edit_course, name='admin_edit_course'),
    path('admin-panel/courses/<slug:slug>/modules/add/', views.admin_add_module, name='admin_add_module'),
    path('admin-panel/courses/<slug:slug>/modules/<int:module_id>/edit/', views.admin_edit_module, name='admin_edit_module'),
    path('admin-panel/courses/<slug:slug>/modules/<int:module_id>/exercises/add/', views.admin_add_exercise, name='admin_add_exercise'),
    path('admin-panel/courses/<slug:slug>/modules/<int:module_id>/exercises/<int:exercise_id>/edit/', views.admin_edit_exercise, name='admin_edit_exercise'),
    path('admin-panel/payments/', views.admin_payments, name='admin_payments'),
]
