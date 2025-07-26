from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views

urlpatterns = [
    path('', views.start_view, name='start'),  # start page
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('prediction/', views.prediction_view, name='prediction'),
    path('visualization/', views.visualization_view, name='visualization'),
    path('dataset/', views.dataset_view, name='dataset'),
    path('upload_data/', views.upload_file, name='upload_data'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
