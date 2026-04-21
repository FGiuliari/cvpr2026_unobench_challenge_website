from django.db import models
from django.contrib.auth.models import User

class Submission(models.fields.Field):
    pass # Wait, field? No, models.Model

class Submission(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('EVALUATING', 'Evaluating'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    result_json = models.FileField(upload_to='submissions/')
    score = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s submission - {self.score if self.score is not None else 'N/A'}"

    class Meta:
        ordering = ['-score', 'created_at']
