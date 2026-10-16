from django.urls import path
from game import views

urlpatterns = [
    path('api/session/', views.session),
    path('api/register/', views.register),
    path('api/login/', views.sign_in),
    path('api/logout/', views.sign_out),
    path('api/slots/', views.slots),
    path('api/slots/<int:slot_id>/', views.slot_detail),
    path('api/slots/<int:slot_id>/command/', views.command),
    path('api/slots/<int:slot_id>/applications/', views.applications),
    path('api/slots/<int:slot_id>/loadout/', views.loadout),
    path('api/slots/<int:slot_id>/route/', views.route),
    path('api/slots/<int:slot_id>/directory/', views.directory),
    path('api/slots/<int:slot_id>/restart/', views.restart),
    path('api/slots/<int:slot_id>/contracts/', views.contract_action),
    path('api/slots/<int:slot_id>/accept/', views.legacy_action),
    path('api/slots/<int:slot_id>/upgrade/', views.legacy_action),
]
