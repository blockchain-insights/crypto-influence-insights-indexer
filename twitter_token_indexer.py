import os
import asyncio
from apify.apidojo_tweet_scraper import ApiDojoTweetScraper  # Ensure this is the correct path to ApiDojoTweetScraper
from scraper_graph_indexer import ScraperGraphIndexer  # Ensure this is the correct path to ScraperGraphIndexer
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# Define the indexing function
async def index_tweets(tokens):
    # Ensure tokens are in list format
    if isinstance(tokens, str):
        tokens = [token.strip() for token in tokens.split(",")]

    # Initialize the tweet scraper with provided tokens
    tweet_scraper = ApiDojoTweetScraper(tokens)

    try:
        # Scrape tweets for each token and collect structured data
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
        # Ensure Neo4j driver connection is closed
        graph_indexer.close()

# Define the main function
async def main():
    # Read tokens from environment variable, defaulting to ["PEPE"] if not set
    tokens = os.getenv("SCRAPE_TOKENS", "PEPE")

    # Call the indexing function with tokens
    await index_tweets(tokens)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
