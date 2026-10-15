from django.urls import path
from game import views
urlpatterns = [path('api/session/', views.session), path('api/register/', views.register), path('api/login/', views.sign_in), path('api/logout/', views.sign_out), path('api/slots/', views.slots), path('api/slots/<int:slot_id>/', views.slot_detail), path('api/slots/<int:slot_id>/accept/', views.accept), path('api/slots/<int:slot_id>/command/', views.command), path('api/slots/<int:slot_id>/upgrade/', views.upgrade)]
