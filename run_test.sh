#!/bin/bash
# script to run all components for testing
cd /home/fgiuliari/Documents/Projects/Research-Projects/MaGE/Challenge-website/cv_challenge

# Run Celery in background
uv run celery -A cv_challenge_project worker -l INFO &
CELERY_PID=$!

# Run Django in background
uv run python manage.py runserver 127.0.0.1:8000 &
DJANGO_PID=$!

echo "Servers started."
echo "Visit http://127.0.0.01:8000"
echo "Press Ctrl+C to stop servers."

# Wait for interrupt
trap "kill $CELERY_PID $DJANGO_PID" EXIT
wait
