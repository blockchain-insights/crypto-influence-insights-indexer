from loguru import logger
from actors import run_actor, run_actor_async, ActorConfig
from datetime import datetime, timezone
import asyncio

class ApiDojoTweetScraper:
    """
    A class designed to query tweets based using the apidojo/tweet-scraper actor on the Apify platform.

    Attributes:
        actor_config (ActorConfig): Configuration settings specific to the Apify actor.
    """

    def __init__(self):
        """
        Initialize the ApiDojoTweetScraper.
        """
        self.actor_config = ActorConfig("61RPP7dywgiy0JPD0")
        self.actor_config.timeout_secs = 120


    async def searchBatch(self, urls: list):
        run_input = {
            "maxItems": len(urls),
            "maxTweetsPerQuery": 1,
            "onlyImage": False,
            "onlyQuote": False,
            "onlyTwitterBlue": False,
            "onlyVerifiedUsers": False,
            "onlyVideo": False,
            "startUrls": urls
        }
        results = await run_actor_async(self.actor_config, run_input)
        return results

    def searchByUrl(self, urls: list, max_tweets_per_url: int = 1):
        """
        Search for tweets by url.
        """

        results = asyncio.run(self.searchBatch(urls))
        return self.map(results)
    
    def format_date(self, date: datetime):
        date = date.replace(tzinfo=timezone.utc)
        return date.isoformat(sep=' ', timespec='seconds')

    def map_item(self, item) -> dict:
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

        Args:
            input (list): The data to potentially map or transform.

        Returns:
            list: The mapped or transformed data.
        """
        filtered_input = []
        for item in input:
            sn3_item = self.map_item(item)
            if sn3_item:
                filtered_input.append(sn3_item)

        return filtered_input


if __name__ == '__main__':
    # Initialize the tweet query mechanism
    query = ApiDojoTweetScraper()

    # Use the correct format for startUrls
    urls = [
        {"url": "https://x.com/search?q=%24PEPE&src=typed_query"}
    ]

    data_set = query.searchByUrl(urls=urls)

    verified_urls = [tweet['url'] for tweet in data_set]

    print(f"Verification returned {len(verified_urls)} tweets")

    if data_set:
        print(f"First tweet: {data_set[0]}")

    print(f"There are {len(set(verified_urls))} unique urls")

    unverified = set([url["url"] for url in urls]) - set(verified_urls)

    if len(unverified) > 0:
        print(f"Num unverified: {len(unverified)}: {unverified}, trying again")
        data_set2 = query.searchByUrl(urls=[{"url": u} for u in unverified])

        verified_urls2 = [tweet['url'] for tweet in data_set2]

        unverified = set([url["url"] for url in urls]) - set(verified_urls) - set(verified_urls2)

        print(f"Num unverified: {len(unverified)}: {unverified}")
    else:
        print("All verified!")
