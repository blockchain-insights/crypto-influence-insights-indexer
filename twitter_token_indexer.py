import asyncio
from datetime import datetime
from celery import shared_task
from apify.apidojo_tweet_scraper import ApiDojoTweetScraper
from loguru import logger
from helpers.ipfs_utils import upload_file_to_ipfs
from database.models.dataset_links import DatasetLinkManager
from settings import settings

@shared_task
def run_index_tweets():
    """Run the asynchronous tweet indexing task."""
    asyncio.run(index_tweets())


async def index_tweets(token=None, miner_key=None):
    """
    Scrape tweets for a given token, upload results to IPFS, and store the link in the database.

    Args:
        token (str): Token to scrape tweets for.
        miner_key (str): Miner key to include in the file name.
    """
    token = token or settings.SCRAPE_TOKEN
    miner_key = miner_key or "default_miner"  # This can also be part of settings if needed
    scrape_start_date = settings.SCRAPE_START_DATE
    scrape_end_date = datetime.utcnow().strftime("%Y-%m-%d")

    tweet_scraper = ApiDojoTweetScraper(token)

    try:
        # Scrape tweets
        logger.info(f"Scraping tweets for token: {token} from {scrape_start_date} to {scrape_end_date}")
        scraped_data = await tweet_scraper.search_token_mentions()
        if not scraped_data:
            logger.warning("No tweets scraped.")
            return

        # Generate file name with the new format
        current_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_name = f"{miner_key}_tweets_{token}_{scrape_start_date}_to_{scrape_end_date}_{current_timestamp}.json"

        # Export tweets to JSON
        tweet_scraper.export_to_json(scraped_data, file_name)
        logger.info(f"Exported tweets to {file_name}")

        # Upload JSON file to IPFS
        with open(file_name, "r") as file:
            file_content = file.read()
        ipfs_response = upload_file_to_ipfs(
            file_name,
            file_content,
            settings.PINATA_API_KEY,
            settings.PINATA_SECRET_API_KEY
        )

        if "error" in ipfs_response:
            logger.error(ipfs_response["error"])
            return

        ipfs_link = ipfs_response.get("ipfs_link")
        logger.info(f"Uploaded to IPFS: {ipfs_link}")

        # Store IPFS link in the database
        dataset_manager = DatasetLinkManager()
        await dataset_manager.store_latest_link(token=token, ipfs_link=ipfs_link)
        logger.info(f"Stored IPFS link for token {token} in the database.")

    except Exception as e:
        logger.error(f"Error during indexing: {e}")


async def main():
    """
    Main function to initialize and run the tweet indexing.
    """
    token = settings.SCRAPE_TOKEN  # Default token from settings
    miner_key = "default_miner"  # Can also be configured in settings
    await index_tweets(token, miner_key)


if __name__ == "__main__":
    asyncio.run(main())
