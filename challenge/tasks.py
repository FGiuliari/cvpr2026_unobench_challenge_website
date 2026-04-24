from celery import shared_task
from .models import Submission
import json
import time
import random
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task
def evaluate_submission(submission_id):

    logger.info("start task")
    from .evaluate_nlp import evaluate
    import numpy as np

    NPZ_FOLDER = "/home/fgiuliari/Documents/Projects/Research-Projects/MaGE/ECCV_Mage_Evaluation/annotations"
    GT_FILE = "/home/fgiuliari/Documents/Projects/Research-Projects/MaGE/ECCV_Mage_Evaluation/test_GT.json"

    try:
        submission = Submission.objects.get(id=submission_id)
        submission.status = "EVALUATING"
        submission.save()

        # Simulate evaluation delay
        # logger.error("asd")
        # logger.error('result_json path: ' + str(submission.result_json.path))

        results = evaluate(str(submission.result_json.path), GT_FILE, NPZ_FOLDER)
        logger.warning(results.keys())

        # Read file

        # # Mock Evaluation Metric (Example: read 'accuracy' key or just random score)
        # # For a real CV challenge, you would run your models or compare against ground truth here.
        # score = data.get('accuracy', 0.0) # mock

        # score = random.random() * 100

        # res[gt["difficulty"]]["SR-P"].append(p)
        # res[gt["difficulty"]]["SR-R"].append(r)
        # res[gt["difficulty"]]["SR-F1"].append(f1)
        # submission.score = np.mean(results["Easy"]["SR-P"])
        submission.score_path_noOcc_SRR = np.mean(results["No-Occ"]["SR-R"])
        submission.score_path_noOcc_SRP = np.mean(results["No-Occ"]["SR-P"])
        submission.score_path_noOcc_SRF1 = np.mean(results["No-Occ"]["SR-F1"])

        no_occ = results["No-Occ"]
        easy = results["Easy"]
        medium = results["Medium"]
        hard = results["Hard"]
        mean = np.mean

        # ---- Path-based metrics ----
        submission.score_path_noOcc_SR = mean(no_occ["SR-P"])
        submission.score_path_noOcc_MPNED = mean(no_occ["MP_NED"])

        submission.score_path_easy_SR_P = mean(easy["SR-P"])
        submission.score_path_easy_SR_R = mean(easy["SR-R"])
        submission.score_path_easy_SR_F1 = mean(easy["SR-F1"])
        submission.score_path_easy_MPNED = mean(easy["MP_NED"])

        submission.score_path_medium_SR_P = mean(medium["SR-P"])
        submission.score_path_medium_SR_R = mean(medium["SR-R"])
        submission.score_path_medium_SR_F1 = mean(medium["SR-F1"])
        submission.score_path_medium_MPNED = mean(medium["MP_NED"])

        submission.score_path_hard_SR_P = mean(hard["SR-P"])
        submission.score_path_hard_SR_R = mean(hard["SR-R"])
        submission.score_path_hard_SR_F1 = mean(hard["SR-F1"])
        submission.score_path_hard_MPNED = mean(hard["MP_NED"])

        submission.score_path_average_SR_P = mean(
            [
                submission.score_path_easy_SR_P,
                submission.score_path_medium_SR_P,
                submission.score_path_hard_SR_P,
            ]
        )
        submission.score_path_average_SR_R = mean(
            [
                submission.score_path_easy_SR_R,
                submission.score_path_medium_SR_R,
                submission.score_path_hard_SR_R,
            ]
        )
        submission.score_path_average_SR_F1 = mean(
            [
                submission.score_path_easy_SR_F1,
                submission.score_path_medium_SR_F1,
                submission.score_path_hard_SR_F1,
            ]
        )
        submission.score_path_average_MPNED = mean(
            [
                submission.score_path_noOcc_MPNED,
                submission.score_path_easy_MPNED,
                submission.score_path_medium_MPNED,
                submission.score_path_hard_MPNED,
            ]
        )

        # ---- Pairwise metrics ----
        submission.score_object_easy_OP = mean(easy["OP"])
        submission.score_object_easy_OR = mean(easy["OR"])
        submission.score_object_easy_F1 = mean(easy["F1"])

        submission.score_object_medium_OP = mean(medium["OP"])
        submission.score_object_medium_OR = mean(medium["OR"])
        submission.score_object_medium_F1 = mean(medium["F1"])

        submission.score_object_hard_OP = mean(hard["OP"])
        submission.score_object_hard_OR = mean(hard["OR"])
        submission.score_object_hard_F1 = mean(hard["F1"])

        submission.score_object_average_OP = mean(
            [
                submission.score_object_easy_OP,
                submission.score_object_medium_OP,
                submission.score_object_hard_OP,
            ]
        )
        submission.score_object_average_OR = mean(
            [
                submission.score_object_easy_OR,
                submission.score_object_medium_OR,
                submission.score_object_hard_OR,
            ]
        )
        submission.score_object_average_F1 = mean(
            [
                submission.score_object_easy_F1,
                submission.score_object_medium_F1,
                submission.score_object_hard_F1,
            ]
        )

        submission.status = "SUCCESS"
        submission.save()

    except Exception as e:
        if "submission" in locals():
            print(e)
            submission.status = "FAILED"
            submission.error_message = str(e)
            submission.save()
