from django.urls import path
from . import views

app_name = 'studybot'

urlpatterns = [
    path('<slug:slug>/', views.chat_home, name='home'),
    path('<slug:slug>/new/', views.new_session, name='new_session'),
    path('<slug:slug>/session/<int:session_id>/', views.chat_session, name='session'),
    path('<slug:slug>/session/<int:session_id>/send/', views.send_message, name='send_message'),
    path('<slug:slug>/session/<int:session_id>/delete/', views.delete_session, name='delete_session'),
]
