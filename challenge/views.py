from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Submission
from .tasks import evaluate_submission


def leaderboard(request):
    submissions = Submission.objects.filter(is_public=True, status="SUCCESS").order_by(
        "-score", "created_at"
    )
    return render(request, "challenge/leaderboard.html", {"submissions": submissions})


@login_required
def submit_result(request):
    if request.method == "POST":
        json_file = request.FILES.get("result_json")
        if not json_file:
            messages.error(request, "Please upload a JSONL file.")
            return redirect("submit")

        if not json_file.name.endswith(".jsonl"):
            messages.error(request, "Only JSONL files are allowed.")
            return redirect("submit")

        submission = Submission.objects.create(
            user=request.user,
            result_json=json_file,
            is_public=request.POST.get("is_public") == "off",
        )

        # Trigger Celery Task
        evaluate_submission.delay(submission.id)

        messages.success(
            request,
            "Your submission has been received and is currently being evaluated!",
        )
        return redirect("my_submissions")

    return render(request, "challenge/submit.html")


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
