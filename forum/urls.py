from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    path('', views.forum_home, name='home'),
    path('new/', views.create_thread, name='create_thread'),
    path('search/', views.search_threads, name='search'),
    path('my-threads/', views.my_threads, name='my_threads'),
    path('category/<slug:slug>/', views.category_detail, name='category'),
    path('thread/<slug:slug>/', views.thread_detail, name='thread'),
    path('post/<int:post_id>/vote/', views.vote_post, name='vote'),
    path('post/<int:post_id>/solution/', views.mark_solution, name='mark_solution'),
    path('thread/<int:thread_id>/bookmark/', views.toggle_bookmark, name='bookmark'),
    path('thread/<int:thread_id>/pin/', views.toggle_pin, name='pin'),
    path('thread/<int:thread_id>/lock/', views.toggle_lock, name='lock'),
]
