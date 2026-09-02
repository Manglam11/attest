from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('ask/', views.ask, name='ask'),
    path('history/', views.history, name='history'),
    path('history/<int:pk>/', views.history_detail, name='history_detail'),
    path('trust/', views.trust, name='trust'),
]
