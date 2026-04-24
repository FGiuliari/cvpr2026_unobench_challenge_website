import challenge
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Submission
from .tasks import evaluate_submission

import logging
logger = logging.getLogger(__name__)

def leaderboard(request):
    submissions = Submission.objects.filter(is_public=True, status="SUCCESS").order_by(
         "created_at"
    )
    return render(request, "challenge/leaderboard.html", {"submissions": submissions})


def home(request):
    return render(request, "challenge/home.html")


def challenge_1(request):
    submissions = Submission.objects.filter(is_public=True, challenge_type=1).order_by(
         "created_at"
    )
    return render(request, "challenge/challenge_1.html", {"submissions": submissions})


def challenge_2(request):
    # submissions = Submission.objects.filter(is_public=True, status="SUCCESS").order_by(
    #     "-score", "created_at"
    # )
    submissions = Submission.objects.filter(is_public=True, challenge_type=2).order_by(
         "created_at"
    )
    return render(request, "challenge/challenge_2.html", {"submissions": submissions})


@login_required
def submit_results(request):
    if request.method == "POST":
        # messages.error(request, "ERROR 1")
        # messages.error(request, "ERROR 2")
        # return redirect("submit_results")

        challenge_type = request.POST.get("challenge_type")
        if challenge_type not in ["1", "2"]:
            messages.error(request, "Please select a valid challenge type.")
            return redirect("submit_results")

        json_file = request.FILES.get("result_json")
        if not json_file:
            messages.error(request, "Please upload a JSONL file.")
            return redirect("submit_results")

        if not json_file.name.endswith(".jsonl"):
            messages.error(request, "Only JSONL files are allowed.")
            return redirect("submit_results")

        logger.error('result_json path: ' + str(json_file))
        submission = Submission.objects.create(
            user=request.user,
            result_json=json_file,
            is_public=False,
            challenge_type=challenge_type,
        )
        submission.save()

        # Trigger Celery Task
        if request.POST.get("skip_upload"):
            submission.status = "SKIPPED"
            submission.save()

        else:
            evaluate_submission.delay(submission.id)

        messages.success(
            request,
            "Your submission has been received and is currently being evaluated!",
        )
        return redirect("my_submissions")

    return render(request, "challenge/submit_results.html")


@login_required
def my_submissions(request):
    submissions = Submission.objects.filter(user=request.user).order_by("-created_at")
    return render(
        request, "challenge/my_submissions.html", {"submissions": submissions}
    )


@login_required
def toggle_visibility(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id, user=request.user)
    if request.method == "POST":
        submission.is_public = not submission.is_public
        submission.save()
        messages.success(
            request,
            f'Visibility changed to {"Public" if submission.is_public else "Private"}.',
        )
    return redirect("my_submissions")


@login_required
def delete_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id, user=request.user)
    if request.method == "POST":
        submission.delete()
    return redirect("my_submissions")
