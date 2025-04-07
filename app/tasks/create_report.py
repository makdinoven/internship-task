# app/tasks/report_tasks.py
import asyncio

from redis import Redis

from app.celery import celery_app
from app.config import REDIS_URL
from app.services.analysis_service import collect_all_weeks_report

redis_cache = Redis.from_url(REDIS_URL, db=1)

CACHE_TTL_SECONDS = 3600


@celery_app.task(name="generate_weekly_report")
def generate_weekly_report() -> bool:
    """
    Celery task to collect a report for the last 52 weeks.
    The results (JSON and Excel) are saved to Redis with a TTL of 1 hour.
    """

    # Execute the asynchronous function
    json_report, excel_report = asyncio.run(collect_all_weeks_report())

    # Save the results to Redis
    redis_cache.setex("weekly_report_json", CACHE_TTL_SECONDS, json_report)
    redis_cache.setex("weekly_report_excel", CACHE_TTL_SECONDS, excel_report)

    return True
