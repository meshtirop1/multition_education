from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('checkout/<slug:slug>/', views.checkout, name='checkout'),
    path('history/', views.payment_history, name='payment_history'),

    # Paystack
    path('paystack/pay/<slug:slug>/', views.paystack_initialize, name='paystack_pay'),
    path('paystack/callback/', views.paystack_callback, name='paystack_callback'),
    path('paystack/webhook/', views.paystack_webhook, name='paystack_webhook'),

    # M-Pesa Direct
    path('mpesa/pay/<slug:slug>/', views.mpesa_stk_push, name='mpesa_pay'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('mpesa/status/<uuid:payment_id>/', views.mpesa_check_status, name='mpesa_status'),
]