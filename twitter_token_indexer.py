import os
import asyncio
from apify.apidojo_tweet_scraper import ApiDojoTweetScraper  # Ensure this is the correct path to ApiDojoTweetScraper
from scraper_graph_indexer import ScraperGraphIndexer  # Ensure this is the correct path to ScraperGraphIndexer
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# Define the indexing function
async def index_tweets(token):
    # Initialize the tweet scraper with provided token
    tweet_scraper = ApiDojoTweetScraper(token)
    graph_indexer = None  # Initialize to None to handle exceptions gracefully

    try:
        # Scrape tweets for the token and collect structured data
        scraped_data = await tweet_scraper.search_token_mentions()
        tweet_scraper.export_to_json(scraped_data, "tweets.json")
        if not scraped_data:
            logger.warning("No data scraped; exiting.")
            return

        # Initialize the graph indexer
        graph_indexer = ScraperGraphIndexer()

        # Insert scraped data into the Neo4j database
        logger.info("Inserting scraped data into the Neo4j database.")
        graph_indexer.create_nodes_and_edges(scraped_data)

    except Exception as e:
        logger.error(f"An error occurred: {e}")

    finally:
        # Ensure Neo4j driver connection is closed if graph_indexer was created
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
