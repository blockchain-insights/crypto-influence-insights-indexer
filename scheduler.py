import os

from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv
from loguru import logger
import sys

load_dotenv()

logger.remove()
logger.add(
    "../logs/scheduler.log",
    rotation="500 MB",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="DEBUG"
)

# Celery application instance
scheduler_app = Celery('tasks', broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

# Beat schedule for periodic tasks
from celery.schedules import crontab, timedelta

scheduler_app.conf.beat_schedule = {
    'task-index_tweets': {
        'task': 'tasks.index_tweets',
        'schedule': timedelta(minutes=15),  # Run every 15 minutes
        'options': {'immediate': True},  # Start immediately after the Docker container is loaded
        'args': []
    },
}

scheduler_app.conf.timezone = 'UTC'
scheduler_app.conf.broker_connection_retry_on_startup = True
scheduler_app.conf.worker_proc_alive_timeout = 60
