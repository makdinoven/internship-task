from celery import Celery

from app.config import BROKER_URL, REDIS_URL

celery_app = Celery(
    "app", broker=BROKER_URL, backend=REDIS_URL, include=["app.tasks.update_rates", "app.tasks.create_report"]
)

celery_app.conf.beat_schedule = {
    "refresh-rates-hourly": {"task": "app.tasks.update_rates.update_rates", "schedule": 3600.0}  # 3600 seconds = 1 hour
}
celery_app.conf.timezone = "UTC"
