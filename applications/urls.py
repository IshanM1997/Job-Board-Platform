from django.urls import path

from . import views

app_name = 'applications'

urlpatterns = [
    path('apply/<int:job_pk>/', views.apply_to_job, name='apply_to_job'),
    path('<int:pk>/', views.application_detail, name='application_detail'),
    path('<int:pk>/status/', views.update_status, name='update_status'),
    path('pipeline/<int:job_pk>/', views.pipeline, name='pipeline'),
]
