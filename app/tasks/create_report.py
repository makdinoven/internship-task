# app/tasks/report_tasks.py
import asyncio

from redis import Redis

from app.celery import celery_app
from app.config import REDIS_URL
from app.db.sessions import async_session_maker
from app.services.analysis_service import (collect_52_weeks_report,
                                           convert_report_to_json,
                                           generate_excel_file)

redis_cache = Redis.from_url(REDIS_URL, db=1)

CACHE_TTL_SECONDS = 3600


@celery_app.task(name="generate_weekly_report")
def generate_weekly_report() -> bool:
    """
    Celery task to collect a report for the last 52 weeks.
    The results (JSON and Excel) are saved to Redis with a TTL of 1 hour.
    """
    loop = asyncio.get_event_loop()

    async def _collect_and_prepare() -> tuple[str, bytes]:
        # Open one asynchronous session for all 52 weeks
        async with async_session_maker() as session:
            report_data = await collect_52_weeks_report(session)
        # Serialize to JSON
        report_json = convert_report_to_json(report_data)
        # Generate Excel file
        excel_bytes = generate_excel_file(report_data)
        return report_json, excel_bytes

    # Execute the asynchronous function
    json_report, excel_report = loop.run_until_complete(_collect_and_prepare())

    # Save the results to Redis
    redis_cache.setex("weekly_report_json", CACHE_TTL_SECONDS, json_report)
    redis_cache.setex("weekly_report_excel", CACHE_TTL_SECONDS, excel_report)

    return True
