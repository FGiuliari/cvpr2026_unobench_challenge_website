from django.db import models
from django.contrib.auth.models import User


class Submission(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("EVALUATING", "Evaluating"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("SKIPPED", "Skipped"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    result_json = models.FileField(upload_to="submissions/", null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True, null=True)
    challenge_type = models.IntegerField(
        choices=[(1, "challenge 1"), (2, "challenge 2")]
    )

    # ---- Path-based metrics ----
    score_path_noOcc_SR = models.FloatField(blank=True, null=True)
    score_path_noOcc_MPNED = models.FloatField(blank=True, null=True)

    score_path_easy_SR_P = models.FloatField(blank=True, null=True)
    score_path_easy_SR_R = models.FloatField(blank=True, null=True)
    score_path_easy_SR_F1 = models.FloatField(blank=True, null=True)
    score_path_easy_MPNED = models.FloatField(blank=True, null=True)

    score_path_medium_SR_P = models.FloatField(blank=True, null=True)
    score_path_medium_SR_R = models.FloatField(blank=True, null=True)
    score_path_medium_SR_F1 = models.FloatField(blank=True, null=True)
    score_path_medium_MPNED = models.FloatField(blank=True, null=True)

    score_path_hard_SR_P = models.FloatField(blank=True, null=True)
    score_path_hard_SR_R = models.FloatField(blank=True, null=True)
    score_path_hard_SR_F1 = models.FloatField(blank=True, null=True)
    score_path_hard_MPNED = models.FloatField(blank=True, null=True)

    score_path_average_SR_P = models.FloatField(blank=True, null=True)
    score_path_average_SR_R = models.FloatField(blank=True, null=True)
    score_path_average_SR_F1 = models.FloatField(blank=True, null=True)
    score_path_average_MPNED = models.FloatField(blank=True, null=True)

    # ---- Pairwise metrics ----
    score_object_easy_OP = models.FloatField(blank=True, null=True)
    score_object_easy_OR = models.FloatField(blank=True, null=True)
    score_object_easy_F1 = models.FloatField(blank=True, null=True)

    score_object_medium_OP = models.FloatField(blank=True, null=True)
    score_object_medium_OR = models.FloatField(blank=True, null=True)
    score_object_medium_F1 = models.FloatField(blank=True, null=True)

    score_object_hard_OP = models.FloatField(blank=True, null=True)
    score_object_hard_OR = models.FloatField(blank=True, null=True)
    score_object_hard_F1 = models.FloatField(blank=True, null=True)

    score_object_average_OP = models.FloatField(blank=True, null=True)
    score_object_average_OR = models.FloatField(blank=True, null=True)
    score_object_average_F1 = models.FloatField(blank=True, null=True)

    def __str__(self):

        return f"{self.user.username}'s submission - {self.score_path_average_SR_F1}"

    class Meta:
        ordering = ["-score_path_average_SR_F1", "created_at"]
