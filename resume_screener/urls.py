"""resume_screener/urls.py"""
from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('',                                views.landing,             name='landing'),
    path('register/',                       views.register_view,       name='register'),
    path('login/',                          views.login_view,          name='login'),
    path('logout/',                         views.logout_view,         name='logout'),
    path('dashboard/',                      views.dashboard_view,      name='dashboard'),

    # Recruiter
    path('recruiter/',                      views.recruiter_dashboard,  name='recruiter_dashboard'),
    path('jobs/new/',                       views.job_create,           name='job_create'),
    path('jobs/<int:job_id>/edit/',         views.job_edit,             name='job_edit'),
    path('jobs/<int:job_id>/applicants/',   views.job_applicants,       name='job_applicants'),
    path('applications/<int:app_id>/',      views.application_detail,   name='application_detail'),

    # Candidate
    path('candidate/',                      views.candidate_dashboard,  name='candidate_dashboard'),
    path('jobs/<int:job_id>/apply/',        views.apply_job,            name='apply_job'),
    path('my-applications/',               views.my_applications,      name='my_applications'),
]
