from loguru import logger
from .actors import run_actor_async, ActorConfig
from datetime import datetime, timezone
import asyncio
import json

class ApiDojoTweetScraper:
    def __init__(self, tokens):
        self.tokens = tokens
        self.actor_config = ActorConfig("61RPP7dywgiy0JPD0")
        self.actor_config.timeout_secs = 120

    async def search_token_mentions(self):
        all_data = []
        for token in self.tokens:
            url = f"https://twitter.com/search?q=%24{token}"
            logger.info(f"Scraping data for token: ${token}")
            results = await self.searchBatch(url)
            mapped_data = self.map(results, token)
            all_data.extend(mapped_data)
        return all_data

    async def searchBatch(self, url: str):
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
            "proxyConfiguration": {"useApifyProxy": True, "groups": ["RESIDENTIAL"]}
        }
        results = await run_actor_async(self.actor_config, run_input)
        return results

    def format_date(self, date_str: str):
        """
        Format the date from Twitter's createdAt format to ISO format with UTC timezone.
        """
        try:
            parsed_date = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
            return parsed_date.astimezone(timezone.utc).isoformat(sep=' ', timespec='seconds')
        except ValueError as e:
            logger.error(f"Error parsing date '{date_str}': {e}")
            return None

    def map_item(self, item, token) -> dict:
        """
        Map a raw tweet data item to a structured dictionary format.
        """
        try:
            hashtags = ["#" + x["text"] for x in item.get("entities", {}).get('hashtags', [])]
            images = []
            extended_entities = item.get("extendedEntities")
            if extended_entities:
                media_urls = {m["media_key"]: m["media_url_https"] for m in extended_entities["media"] if m.get("media_url_https")}
                for media in item.get("entities", {}).get('media', []):
                    media_key = media.get("media_key")
                    if media_key:
                        images.append(media_urls[media_key])

            # Parse the tweet's creation date
            tweet_timestamp = self.format_date(item.get("createdAt", ""))

            tweet = {
                'id': item['id'],
                'url': item['twitterUrl'],
                'text': item.get('text'),
                'likes': item['likeCount'],
                'images': images,
                'timestamp': tweet_timestamp
            }

            user_account = {
                'username': item['author']['userName'],
                'user_id': item['author']['id'],
                'is_verified': item['author']['isVerified'],
                'follower_count': item['author'].get('followers', 0),
                'account_age': self.format_date(item['author'].get('createdAt', "")),
                'engagement_level': item.get('likeCount', 0) + item.get('retweetCount', 0)
            }

            region = {
                'name': item['author'].get('location', 'Unknown')
            }

            # Define edges and relationships between entities
            edges = [
                {'type': 'POSTED', 'from': user_account['user_id'], 'to': tweet['id'], 'attributes': {'timestamp': tweet['timestamp'], 'likes': tweet['likes']}},
                {'type': 'MENTIONS', 'from': user_account['user_id'], 'to': token, 'attributes': {'timestamp': tweet['timestamp'], 'hashtag_count': len(hashtags)}},
                {'type': 'LOCATED_IN', 'from': user_account['user_id'], 'to': region['name']},
                {'type': 'MENTIONED_IN', 'from': token, 'to': tweet['id']}
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
        Convert all tweet items in input to structured data format for the given token.
        """
        structured_data = []
        for item in input:
            structured_item = self.map_item(item, token)
            if structured_item:
                structured_data.append(structured_item)
        return structured_data

    def export_to_json(self, data: list, filename: str):
        """
        Export the mapped data to a JSON file.
        """
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Data successfully exported to {filename}")
        except Exception as e:
            logger.error(f"❌ Error exporting data to JSON: {e}")

# Ensure graph_indexer is only closed if instantiated
if __name__ == '__main__':
    # Tokens to monitor
    tokens = ["PEPE"]

    # Initialize the tweet query mechanism
    scraper = ApiDojoTweetScraper(tokens)

    try:
        # Search tweets for each token and collect the structured data
        data_set = asyncio.run(scraper.search_token_mentions())

        # Display results for verification
        if data_set:
            for data in data_set[:5]:  # Displaying first 5 entries for brevity
                print(data)

            # Export results to JSON
            scraper.export_to_json(data_set, "tweets.json")
        else:
            logger.warning("No data scraped; exiting.")

    except Exception as e:
        logger.error(f"An error occurred during scraping: {e}")
