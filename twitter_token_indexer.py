import asyncio
from apify.apidojo_tweet_scraper import ApiDojoTweetScraper  # Ensure this is the correct path to ApiDojoTweetScraper
from scraper_graph_indexer import ScraperGraphIndexer  # Ensure this is the correct path to ScraperGraphIndexer
from loguru import logger

from dotenv import load_dotenv

load_dotenv()

# Define the main function
async def main():
    # Define tokens to monitor
    tokens = ["PEPE"]

    # Initialize the tweet scraper
    tweet_scraper = ApiDojoTweetScraper(tokens)

    try:
        # Scrape tweets for each token and collect the structured data
        scraped_data = await tweet_scraper.search_token_mentions()
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
        # Close the Neo4j driver connection
        graph_indexer.close()

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
