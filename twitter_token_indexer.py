import os
import asyncio
from celery import shared_task
from apify.apidojo_tweet_scraper import ApiDojoTweetScraper  # Ensure this is the correct path
from scraper_graph_indexer import ScraperGraphIndexer  # Ensure this is the correct path
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

@shared_task
def run_index_tweets():
    """Run the asynchronous tweet indexing task."""
    asyncio.run(index_tweets())

async def index_tweets(token=None):
    """Indexes tweets for a given token."""
    token = token or os.getenv("SCRAPE_TOKEN", "PEPE")
    tweet_scraper = ApiDojoTweetScraper(token)
    graph_indexer = None

    try:
        # Scrape tweets
        logger.info(f"Scraping tweets for token: {token}")
        scraped_data = await tweet_scraper.search_token_mentions()
        tweet_scraper.export_to_json(scraped_data, "tweets.json")
        if not scraped_data:
            logger.warning("No tweets scraped.")
            return

        # Insert into Neo4j
        logger.info("Inserting scraped tweets into Neo4j.")
        graph_indexer = ScraperGraphIndexer()
        graph_indexer.create_nodes_and_edges(scraped_data, token)

    except Exception as e:
        logger.error(f"Error during indexing: {e}")

    finally:
        if graph_indexer:
            graph_indexer.close()

# Define the main function
async def main():
    # Read token from environment variable, defaulting to "PEPE" if not set
    token = os.getenv("SCRAPE_TOKEN", "PEPE")

    # Call the indexing function with the token
    await index_tweets(token)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
