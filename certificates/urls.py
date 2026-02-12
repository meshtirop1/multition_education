from django.urls import path
from . import views

app_name = 'certificates'

urlpatterns = [
    path('', views.my_certificates, name='list'),
    path('download/<uuid:certificate_id>/', views.download_certificate, name='download'),
    path('verify/<uuid:certificate_id>/', views.verify_certificate, name='verify'),
]
