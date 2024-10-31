from loguru import logger
from .actors import run_actor_async, ActorConfig
from datetime import datetime, timezone
import asyncio
import json

class ApiDojoTweetScraper:
    """
    A class designed to query tweets using the apidojo/tweet-scraper actor on the Apify platform.
    This version includes Region as a separate entity and captures edges between entities.
    """

    def __init__(self, tokens):
        """
        Initialize the ApiDojoTweetScraper with a list of tokens to monitor.
        """
        self.tokens = tokens
        self.actor_config = ActorConfig("61RPP7dywgiy0JPD0")
        self.actor_config.timeout_secs = 120

    async def search_token_mentions(self):
        """
        Run the actor for each token in self.tokens to retrieve tweet data.
        """
        all_data = []
        for token in self.tokens:
            url = f"https://twitter.com/search?q=%24{token}"
            logger.info(f"Scraping data for token: ${token}")
            results = await self.searchBatch(url)
            mapped_data = self.map(results, token)
            all_data.extend(mapped_data)
        return all_data

    async def searchBatch(self, url: str):
        """
        Run the actor with a dynamic URL for the search query.
        """
        run_input = {
            "includeSearchTerms": False,
            "maxItems": 1000,
            "minimumFavorites": 5,
            "minimumReplies": 5,
            "minimumRetweets": 5,
            "onlyImage": False,
            "onlyQuote": False,
            "onlyTwitterBlue": False,
            "onlyVerifiedUsers": False,
            "onlyVideo": False,
            "sort": "Latest",
            "start": "2021-07-01",
            "startUrls": [url],
            "tweetLanguage": "en",
            "proxyConfiguration": {
                "useApifyProxy": True,
                "groups": ["RESIDENTIAL"]
            }
        }
        results = await run_actor_async(self.actor_config, run_input)
        return results

    def format_date(self, date: datetime):
        """
        Format the date to ISO format with UTC timezone.
        """
        date = date.replace(tzinfo=timezone.utc)
        return date.isoformat(sep=' ', timespec='seconds')

    def map_item(self, item, token) -> dict:
        """
        Map the raw tweet data to a structured dictionary format with Region as a separate entity and edges.
        """
        try:
            hashtags = ["#" + x["text"] for x in item.get("entities", {}).get('hashtags', [])]
            images = []

            # Handling media items
            extended_entities = item.get("extendedEntities")
            if extended_entities:
                media_urls = {m["media_key"]: m["media_url_https"] for m in extended_entities["media"] if m.get("media_url_https")}
                for media in item.get("entities", {}).get('media', []):
                    media_key = media.get("media_key")
                    if media_key:
                        images.append(media_urls[media_key])

            # Parsing and formatting the date
            date_format = "%a %b %d %H:%M:%S %z %Y"
            parsed_date = datetime.strptime(item["createdAt"], date_format)

            # Structuring entities
            tweet = {
                'id': item['id'],
                'url': item['twitterUrl'],
                'text': item.get('text'),
                'likes': item['likeCount'],
                'images': images,
                'timestamp': self.format_date(parsed_date)
            }

            user_account = {
                'username': item['author']['userName'],
                'user_id': item['author']['id'],
                'is_verified': item['author']['isVerified']
            }

            region = {
                'name': item['author'].get('location', 'Unknown')  # Default to 'Unknown' if no location
            }

            # Define edges and relationships between entities
            edges = [
                {
                    'type': 'POSTED',
                    'from': user_account['user_id'],
                    'to': tweet['id'],
                    'attributes': {
                        'timestamp': tweet['timestamp'],
                        'likes': tweet['likes']
                    }
                },
                {
                    'type': 'MENTIONS',
                    'from': user_account['user_id'],
                    'to': token,
                    'attributes': {
                        'timestamp': tweet['timestamp'],
                        'hashtag_count': len(hashtags)
                    }
                }
            ]

            return {
                'token': token,
                'tweet': tweet,
                'user_account': user_account,
                'region': region,
                'hashtags': hashtags,
                'edges': edges
            }
        except Exception as e:
            logger.error(f"❌ Error while converting tweet to structured format: {e}, tweet = {item}")
            return {}

    def map(self, input: list, token: str) -> list:
        """
        Map the input data to the structured format for ingestion.
        """
        structured_data = []
        for item in input:
            structured_item = self.map_item(item, token)
            if structured_item:
                structured_data.append(structured_item)
        return structured_data

    def export_to_json(self, data: list, filename: str):
        """
        Export the structured data to a JSON file.
        """
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Data successfully exported to {filename}")
        except Exception as e:
            logger.error(f"❌ Error exporting data to JSON: {e}")

if __name__ == '__main__':
    # Tokens to monitor
    tokens = ["PEPE"]

    # Initialize the tweet query mechanism
    scraper = ApiDojoTweetScraper(tokens)

    # Search tweets for each token and collect the structured data
    data_set = asyncio.run(scraper.search_token_mentions())

    # Display results for verification
    for data in data_set[:5]:  # Displaying first 5 entries for brevity
        print(data)

    # Export results to JSON
    scraper.export_to_json(data_set, "tweets_data.json")
