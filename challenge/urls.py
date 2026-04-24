from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("challenge-1/", views.challenge_1, name="challenge_1"),
    path("challenge-2/", views.challenge_2, name="challenge_2"),
    path("submit_results/", views.submit_results, name="submit_results"),
    path("my-submissions/", views.my_submissions, name="my_submissions"),
    path(
        "submission/<int:submission_id>/toggle/",
        views.toggle_visibility,
        name="toggle_visibility",
    ),
    path(
        "submission/<int:submission_id>/delete/",
        views.delete_submission,
        name="delete_submission",
    ),
]
