import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv
from loguru import logger
import sys

# Load environment variables
load_dotenv()

# Configure logging
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

# Load schedule interval from the environment
INDEXER_INTERVAL_HOURS = int(os.getenv('INDEXER_INTERVAL_HOURS', 24))

# Ensure interval is valid
if INDEXER_INTERVAL_HOURS <= 0 or INDEXER_INTERVAL_HOURS > 24:
    logger.error("Invalid INDEXER_INTERVAL_HOURS. Must be between 1 and 24.")
    sys.exit(1)

# Celery application instance
scheduler_app = Celery(
    'tasks',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Import tasks to register them with Celery
from twitter_token_indexer import run_index_tweets

# Define the beat schedule
scheduler_app.conf.beat_schedule = {
    'run-indexer-every-x-hours': {
        'task': 'twitter_token_indexer.run_index_tweets',
        'schedule': crontab(minute=0, hour=f'*/{INDEXER_INTERVAL_HOURS}'),
    },
}

# Celery configuration
scheduler_app.conf.timezone = 'UTC'
scheduler_app.conf.broker_connection_retry_on_startup = True
scheduler_app.conf.worker_proc_alive_timeout = 60

# Trigger immediate execution if the environment variable is set
if os.getenv('TRIGGER_IMMEDIATE', 'false').lower() == 'true':
    logger.info("Triggering immediate execution of `run_index_tweets` task.")
    try:
        scheduler_app.send_task('twitter_token_indexer.run_index_tweets')
    except Exception as e:
        logger.error(f"Failed to trigger immediate task: {e}")

# Allow manual execution outside Docker
if __name__ == '__main__':
    # Start Celery with specified concurrency to avoid multiple workers running the same task
    scheduler_app.start(argv=['worker', '-B', '--loglevel=info', '--concurrency=1'])
