from celery import shared_task
from .models import Submission
import json
import time
import random
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task
def evaluate_submission(submission_id):

    logger.error("start task")
    from .evaluate_nlp import evaluate
    import numpy as np

    NPZ_FOLDER = "/home/fgiuliari/Documents/Projects/Research-Projects/MaGE/ECCV_Mage_Evaluation/annotations"
    GT_FILE = "/home/fgiuliari/Documents/Projects/Research-Projects/MaGE/ECCV_Mage_Evaluation/test_GT.json"

    try:
        submission = Submission.objects.get(id=submission_id)
        submission.status = "EVALUATING"
        submission.save()

        # Simulate evaluation delay
        logger.error("asd")
        print(submission.result_json.path)

        results = evaluate(str(submission.result_json.path), GT_FILE, NPZ_FOLDER)

        # Read file

        # # Mock Evaluation Metric (Example: read 'accuracy' key or just random score)
        # # For a real CV challenge, you would run your models or compare against ground truth here.
        # score = data.get('accuracy', 0.0) # mock

        # score = random.random() * 100

        submission.score = np.mean(results["Easy"]["SR-P"])
        submission.status = "SUCCESS"
        submission.save()

    except Exception as e:
        if "submission" in locals():
            print(e)
            submission.status = "FAILED"
            submission.error_message = str(e)
            submission.save()
