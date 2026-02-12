from django.urls import path
from . import views

app_name = 'studygroups'

urlpatterns = [
    path('<slug:slug>/', views.group_list, name='list'),
    path('<slug:slug>/create/', views.create_group, name='create'),
    path('<slug:slug>/join/<int:group_id>/', views.join_group, name='join'),
    path('<slug:slug>/leave/<int:group_id>/', views.leave_group, name='leave'),
    path('<slug:slug>/chat/<int:group_id>/', views.group_chat, name='chat'),
    path('<slug:slug>/chat/<int:group_id>/send/', views.send_message, name='send'),
    path('<slug:slug>/chat/<int:group_id>/poll/', views.poll_messages, name='poll'),
]