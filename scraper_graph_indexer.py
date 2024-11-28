import os
from neo4j import GraphDatabase
from loguru import logger

class ScraperGraphIndexer:
    def __init__(self, graph_db_url: str = None, graph_db_user: str = None, graph_db_password: str = None):
        self.graph_db_url = graph_db_url or os.environ.get("GRAPH_DB_URL", "bolt://localhost:7687")
        self.graph_db_user = graph_db_user or os.environ.get("GRAPH_DB_USER", "ops/neo4j")
        self.graph_db_password = graph_db_password or os.environ.get("GRAPH_DB_PASSWORD", "password")
        self.driver = GraphDatabase.driver(self.graph_db_url, auth=(self.graph_db_user, self.graph_db_password))

    def close(self):
        self.driver.close()

    def cleanup_old_token_data(self, current_user_ids: list, scrape_token: str):
        """
        Cleans up old data related to the given token, including UserAccount nodes not in the current scraping results,
        their related Tweets, orphaned Region nodes, and orphaned relationships.

        :param current_user_ids: List of user_ids returned by the new scraping process.
        :param scrape_token: The token for which the data is being cleaned up.
        """
        with self.driver.session() as session:
            try:
                # Step 1: Remove old UserAccount nodes not in the current scraping results
                session.run(
                    """
                    MATCH (ua:UserAccount)-[:MENTIONS]->(:Token {name: $scrape_token})
                    WHERE NOT ua.user_id IN $current_user_ids
                    DETACH DELETE ua
                    """,
                    current_user_ids=current_user_ids,
                    scrape_token=scrape_token
                )
                logger.info(
                    f"Deleted old UserAccount nodes for {scrape_token} users not in the current scraping results.")

                # Step 2: Remove old Tweet nodes related to the removed UserAccount nodes
                session.run(
                    """
                    MATCH (tw:Tweet)<-[:POSTED]-(ua:UserAccount)
                    WHERE NOT (ua)-[:MENTIONS]->(:Token {name: $scrape_token})
                    DETACH DELETE tw
                    """,
                    scrape_token=scrape_token
                )
                logger.info(f"Deleted old Tweet nodes related to removed {scrape_token} UserAccount nodes.")

                # Step 3: Remove orphaned Region nodes
                session.run(
                    """
                    MATCH (r:Region)
                    WHERE NOT EXISTS { MATCH (ua:UserAccount)-[:LOCATED_IN]->(r) }
                    DETACH DELETE r
                    """
                )
                logger.info(f"Deleted orphaned Region nodes without LOCATED_IN relationships.")

                # Step 4: Remove orphaned relationships (not attached to valid nodes)
                session.run(
                    """
                    MATCH ()-[rel]->()
                    WHERE NOT EXISTS { MATCH (startNode)-[rel]->() }
                       OR NOT EXISTS { MATCH ()-[rel]->(endNode) }
                    DELETE rel
                    """
                )
                logger.info(f"Deleted orphaned relationships that no longer have valid start or end nodes.")
            except Exception as e:
                logger.error("An error occurred during the cleanup process", extra={
                    "exception_type": e.__class__.__name__,
                    "exception_message": str(e),
                    "exception_args": e.args
                })

    def create_nodes_and_edges(self, data, scrape_token: str):
        """
        Creates nodes and edges in the graph database based on the scraped data and cleans up old data.

        :param data: List of scraped data entries.
        :param scrape_token: The token for which the data is being indexed and cleaned.
        """
        with self.driver.session() as session:
            try:
                current_user_ids = []  # Keep track of user_ids from the new scraping process

                for entry in data:
                    token = entry['token']
                    tweet = entry['tweet']
                    user_account = entry['user_account']
                    region = entry['region']
                    edges = entry['edges']

                    # Upsert Token node
                    session.run(
                        """
                        MERGE (t:Token {name: $token_name})
                        ON CREATE SET t.created_at = timestamp()
                        ON MATCH SET t.updated_at = timestamp()
                        """,
                        token_name=token
                    )
                    logger.debug(f"Processed Token node for: {token}")

                    # Upsert Tweet node
                    session.run(
                        """
                        MERGE (tw:Tweet {id: $tweet_id})
                        ON CREATE SET tw.url = $url, tw.text = $text, tw.likes = $likes, tw.timestamp = $timestamp
                        ON MATCH SET tw.url = $url, tw.text = $text, tw.likes = $likes, tw.timestamp = $timestamp, tw.updated_at = timestamp()
                        """,
                        tweet_id=tweet['id'], url=tweet['url'], text=tweet['text'], likes=tweet['likes'],
                        timestamp=tweet['timestamp']
                    )
                    logger.debug(f"Processed Tweet node for ID: {tweet['id']}")

                    # Upsert UserAccount node with `total_tweets`
                    session.run(
                        """
                        MERGE (ua:UserAccount {user_id: $user_id})
                        ON CREATE SET 
                            ua.username = $username,
                            ua.is_verified = $is_verified,
                            ua.follower_count = $follower_count,
                            ua.account_age = $account_age,
                            ua.engagement_level = $engagement_level,
                            ua.total_tweets = $total_tweets,
                            ua.created_at = timestamp()
                        ON MATCH SET 
                            ua.username = $username,
                            ua.is_verified = $is_verified,
                            ua.follower_count = $follower_count,
                            ua.account_age = $account_age,
                            ua.engagement_level = $engagement_level,
                            ua.total_tweets = $total_tweets,
                            ua.updated_at = timestamp()
                        """,
                        user_id=user_account['user_id'],
                        username=user_account['username'],
                        is_verified=user_account['is_verified'],
                        follower_count=user_account.get('follower_count', 0),
                        account_age=user_account.get('account_age', 0),
                        engagement_level=user_account.get('engagement_level', 0.0),
                        total_tweets=user_account.get('total_tweets', 0)  # New field with a default value
                    )
                    logger.debug(f"Processed UserAccount node for user_id: {user_account['user_id']}")

                    # Collect current user IDs for cleanup
                    current_user_ids.append(user_account['user_id'])

                    # Upsert Region node
                    if region.get('name') and region['name'] != "Unknown":
                        session.run(
                            """
                            MERGE (r:Region {name: $region_name})
                            ON CREATE SET r.created_at = timestamp()
                            ON MATCH SET r.updated_at = timestamp()
                            """,
                            region_name=region['name']
                        )
                        logger.debug(f"Processed Region node for: {region['name']}")

                    # Upsert relationships
                    for edge in edges:
                        if edge['type'] == 'MENTIONS':
                            session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (t:Token {name: $token_name})
                                MERGE (ua)-[r:MENTIONS]->(t)
                                ON CREATE SET r.timestamp = $timestamp, r.hashtag_count = $hashtag_count
                                ON MATCH SET r.timestamp = $timestamp, r.hashtag_count = $hashtag_count
                                """,
                                user_id=user_account['user_id'], token_name=token,
                                timestamp=edge['attributes']['timestamp'],
                                hashtag_count=edge['attributes']['hashtag_count']
                            )
                            logger.debug(
                                f"Processed MENTIONS relationship for UserAccount {user_account['user_id']} and Token {token}")

                        elif edge['type'] == 'POSTED':
                            session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (tw:Tweet {id: $tweet_id})
                                MERGE (ua)-[r:POSTED]->(tw)
                                ON CREATE SET r.timestamp = $timestamp, r.likes = $likes
                                ON MATCH SET r.timestamp = $timestamp, r.likes = $likes
                                """,
                                user_id=user_account['user_id'], tweet_id=tweet['id'],
                                timestamp=edge['attributes']['timestamp'], likes=edge['attributes']['likes']
                            )
                            logger.debug(
                                f"Processed POSTED relationship for UserAccount {user_account['user_id']} and Tweet {tweet['id']}")

                        elif edge['type'] == 'LOCATED_IN' and region.get('name') != "Unknown":
                            session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (r:Region {name: $region_name})
                                MERGE (ua)-[rel:LOCATED_IN]->(r)
                                """,
                                user_id=user_account['user_id'], region_name=region['name']
                            )
                            logger.debug(
                                f"Processed LOCATED_IN relationship for UserAccount {user_account['user_id']} and Region {region['name']}")

                        elif edge['type'] == 'MENTIONED_IN':
                            session.run(
                                """
                                MATCH (t:Token {name: $token_name}), (tw:Tweet {id: $tweet_id})
                                MERGE (t)-[rel:MENTIONED_IN]->(tw)
                                """,
                                token_name=token, tweet_id=tweet['id']
                            )
                            logger.debug(
                                f"Processed MENTIONED_IN relationship for Token {token} and Tweet {tweet['id']}")

                    # Log progress for the current entry
                    logger.info(f"Finished processing entry for user_id: {user_account['user_id']}")

                # Cleanup old token data after processing all new data
                self.cleanup_old_token_data(current_user_ids, scrape_token)
                logger.info(f"Completed cleanup for old data related to token: {scrape_token}")

            except Exception as e:
                logger.error("An error occurred while creating nodes and edges", extra={
                    "exception_type": e.__class__.__name__,
                    "exception_message": str(e),
                    "exception_args": e.args
                })
