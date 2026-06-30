from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup_landing, name='signup_landing'),
    path('signup/candidate/', views.candidate_signup, name='candidate_signup'),
    path('signup/employer/', views.employer_signup, name='employer_signup'),
    path('login/', views.JobBoardLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
