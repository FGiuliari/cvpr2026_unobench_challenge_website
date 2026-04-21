from django.urls import path
from . import views

urlpatterns = [
    path('', views.leaderboard, name='leaderboard'),
    path('submit/', views.submit_result, name='submit'),
    path('my-submissions/', views.my_submissions, name='my_submissions'),
    path('submission/<int:submission_id>/toggle/', views.toggle_visibility, name='toggle_visibility'),
]
