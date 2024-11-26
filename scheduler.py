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

# Get the schedule interval from an environment variable or default to 1 hour
INDEXER_INTERVAL_HOURS = int(os.getenv('INDEXER_INTERVAL_HOURS', 24))

# Celery application instance
scheduler_app = Celery('tasks', broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

# Import tasks to register them with Celery
from twitter_token_indexer import run_index_tweets

# Beat schedule for periodic tasks
scheduler_app.conf.beat_schedule = {
    'run-indexer-every-x-hours': {
        'task': 'twitter_token_indexer.run_index_tweets',
        'schedule': crontab(hour=f'*/{INDEXER_INTERVAL_HOURS}'),
        'options': {'immediate': True},
    },
}

scheduler_app.conf.timezone = 'UTC'
scheduler_app.conf.broker_connection_retry_on_startup = True
scheduler_app.conf.worker_proc_alive_timeout = 60

# Trigger immediate execution if specified in the environment variable
if os.getenv('TRIGGER_IMMEDIATE', 'false').lower() == 'true':
    logger.info("Triggering immediate execution of `run_index_tweets` task.")
    scheduler_app.send_task('twitter_token_indexer.run_index_tweets')

# Allow manual execution outside Docker
if __name__ == '__main__':
    scheduler_app.start(['worker', '-B', '--loglevel=info'])
