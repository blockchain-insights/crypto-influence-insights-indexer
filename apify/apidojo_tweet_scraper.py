from loguru import logger
from actors import run_actor, run_actor_async, ActorConfig
from datetime import datetime, timezone
import asyncio
import json

class ApiDojoTweetScraper:
    """
    A class designed to query tweets using the apidojo/tweet-scraper actor on the Apify platform.
    """

    def __init__(self):
        """
        Initialize the ApiDojoTweetScraper with actor configuration.
        """
        self.actor_config = ActorConfig("61RPP7dywgiy0JPD0")
        self.actor_config.timeout_secs = 120

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
        # Run the actor with the configured input
        results = await run_actor_async(self.actor_config, run_input)
        return results

    def searchByUrl(self, url: str):
        """
        Perform a search using the specified URL and map the results.
        """
        results = asyncio.run(self.searchBatch(url))
        return self.map(results)

    def format_date(self, date: datetime):
        """
        Format the date to ISO format with UTC timezone.
        """
        date = date.replace(tzinfo=timezone.utc)
        return date.isoformat(sep=' ', timespec='seconds')

    def map_item(self, item) -> dict:
        """
        Map the raw tweet data to a structured dictionary format.
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

            date_format = "%a %b %d %H:%M:%S %z %Y"
            parsed_date = datetime.strptime(item["createdAt"], date_format)

            return {
                'id': item['id'],
                'url': item['twitterUrl'],
                'text': item.get('text'),
                'likes': item['likeCount'],
                'images': images,
                'username': item['author']['userName'],
                'hashtags': hashtags,
                'timestamp': self.format_date(parsed_date)
            }
        except Exception as e:
            logger.error(f"❌ Error while converting tweet to sn3 model: {e}, tweet = {item}")

    def map(self, input: list) -> list:
        """
        Map the input data to the expected sn3 format.
        """
        filtered_input = []
        for item in input:
            sn3_item = self.map_item(item)
            if sn3_item:
                filtered_input.append(sn3_item)
        return filtered_input

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

if __name__ == '__main__':
    # Initialize the tweet query mechanism
    query = ApiDojoTweetScraper()

    # Example URL to search
    url = "https://twitter.com/search?q=%24PEPE"

    # Search tweets using the specified URL
    data_set = query.searchByUrl(url=url)

    # Display verification results
    verified_urls = [tweet['url'] for tweet in data_set]
    print(f"Verification returned {len(verified_urls)} tweets")

    if data_set:
        print(f"First tweet: {data_set[0]}")
    print(f"There are {len(set(verified_urls))} unique URLs")

    # Export results to JSON
    query.export_to_json(data_set, "tweets_data.json")

    # Handle unverified URLs
    unverified = set([url]) - set(verified_urls)
    if len(unverified) > 0:
        print(f"Num unverified: {len(unverified)}: {unverified}, trying again")
        data_set2 = query.searchByUrl(url=url)
        verified_urls2 = [tweet['url'] for tweet in data_set2]
        unverified = set([url]) - set(verified_urls) - set(verified_urls2)
        print(f"Num unverified: {len(unverified)}: {unverified}")
    else:
        print("All verified!")
