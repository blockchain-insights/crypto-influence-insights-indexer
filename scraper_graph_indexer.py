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

    def create_nodes_and_edges(self, data):
        with self.driver.session() as session:
            try:
                for entry in data:
                    token = entry['token']
                    tweet = entry['tweet']
                    user_account = entry['user_account']
                    region = entry['region']
                    edges = entry['edges']

                    # Upsert Token node
                    result = session.run(
                        """
                        MERGE (t:Token {name: $token_name})
                        ON CREATE SET t.created_at = timestamp()
                        ON MATCH SET t.updated_at = timestamp()
                        RETURN t.name AS name, t.created_at AS created, t.updated_at AS updated
                        """,
                        token_name=token
                    )
                    for record in result:
                        if record["created"] == record["updated"]:
                            logger.info(f"Inserted new Token node: {token}")
                        else:
                            logger.info(f"Updated existing Token node: {token}")

                    # Upsert Tweet node
                    result = session.run(
                        """
                        MERGE (tw:Tweet {id: $tweet_id})
                        ON CREATE SET tw.url = $url, tw.text = $text, tw.likes = $likes, tw.timestamp = $timestamp
                        ON MATCH SET tw.url = $url, tw.text = $text, tw.likes = $likes, tw.timestamp = $timestamp, tw.updated_at = timestamp()
                        RETURN tw.id AS id, tw.timestamp AS created, tw.updated_at AS updated
                        """,
                        tweet_id=tweet['id'], url=tweet['url'], text=tweet['text'], likes=tweet['likes'], timestamp=tweet['timestamp']
                    )
                    for record in result:
                        if record["created"] == record["updated"]:
                            logger.info(f"Inserted new Tweet node: {tweet['id']}")
                        else:
                            logger.info(f"Updated existing Tweet node: {tweet['id']}")

                    # Upsert UserAccount node with new fields
                    result = session.run(
                        """
                        MERGE (ua:UserAccount {user_id: $user_id})
                        ON CREATE SET 
                            ua.username = $username,
                            ua.is_verified = $is_verified,
                            ua.follower_count = $follower_count,
                            ua.account_age = $account_age,
                            ua.engagement_level = $engagement_level,
                            ua.created_at = timestamp()
                        ON MATCH SET 
                            ua.username = $username,
                            ua.is_verified = $is_verified,
                            ua.follower_count = $follower_count,
                            ua.account_age = $account_age,
                            ua.engagement_level = $engagement_level,
                            ua.updated_at = timestamp()
                        RETURN ua.user_id AS user_id, ua.created_at AS created, ua.updated_at AS updated
                        """,
                        user_id=user_account['user_id'],
                        username=user_account['username'],
                        is_verified=user_account['is_verified'],
                        follower_count=user_account.get('follower_count', 0),
                        account_age=user_account.get('account_age', 0),
                        engagement_level=user_account.get('engagement_level', 0.0)
                    )
                    for record in result:
                        if record["created"] == record["updated"]:
                            logger.info(f"Inserted new UserAccount node: {user_account['user_id']}")
                        else:
                            logger.info(f"Updated existing UserAccount node: {user_account['user_id']}")

                    # Upsert Region node
                    if region.get('name') and region['name'] != "Unknown":
                        result = session.run(
                            """
                            MERGE (r:Region {name: $region_name})
                            ON CREATE SET r.created_at = timestamp()
                            ON MATCH SET r.updated_at = timestamp()
                            RETURN r.name AS name, r.created_at AS created, r.updated_at AS updated
                            """,
                            region_name=region['name']
                        )
                        for record in result:
                            if record["created"] == record["updated"]:
                                logger.info(f"Inserted new Region node: {region['name']}")
                            else:
                                logger.info(f"Updated existing Region node: {region['name']}")

                    # Upsert relationships
                    for edge in edges:
                        if edge['type'] == 'MENTIONS':
                            result = session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (t:Token {name: $token_name})
                                MERGE (ua)-[r:MENTIONS]->(t)
                                ON CREATE SET r.timestamp = $timestamp, r.hashtag_count = $hashtag_count
                                ON MATCH SET r.timestamp = $timestamp, r.hashtag_count = $hashtag_count
                                RETURN r.timestamp AS created, r.hashtag_count AS count
                                """,
                                user_id=user_account['user_id'], token_name=token, timestamp=edge['attributes']['timestamp'], hashtag_count=edge['attributes']['hashtag_count']
                            )
                            if result.single():
                                logger.info(f"MENTIONS relationship created or updated between UserAccount {user_account['user_id']} and Token {token}")

                        elif edge['type'] == 'POSTED':
                            result = session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (tw:Tweet {id: $tweet_id})
                                MERGE (ua)-[r:POSTED]->(tw)
                                ON CREATE SET r.timestamp = $timestamp, r.likes = $likes
                                ON MATCH SET r.timestamp = $timestamp, r.likes = $likes
                                RETURN r.timestamp AS created, r.likes AS likes
                                """,
                                user_id=user_account['user_id'], tweet_id=tweet['id'], timestamp=edge['attributes']['timestamp'], likes=edge['attributes']['likes']
                            )
                            if result.single():
                                logger.info(f"POSTED relationship created or updated between UserAccount {user_account['user_id']} and Tweet {tweet['id']}")

                        elif edge['type'] == 'LOCATED_IN' and region.get('name') != "Unknown":
                            result = session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (r:Region {name: $region_name})
                                MERGE (ua)-[rel:LOCATED_IN]->(r)
                                RETURN ua.user_id AS UserID, r.name AS RegionName
                                """,
                                user_id=user_account['user_id'], region_name=region['name']
                            )
                            if result.single():
                                logger.info(f"LOCATED_IN relationship created or updated between UserAccount {user_account['user_id']} and Region {region['name']}")

                        elif edge['type'] == 'MENTIONED_IN':
                            result = session.run(
                                """
                                MATCH (t:Token {name: $token_name}), (tw:Tweet {id: $tweet_id})
                                MERGE (t)-[rel:MENTIONED_IN]->(tw)
                                RETURN t.name AS TokenName, tw.id AS TweetID
                                """,
                                token_name=token, tweet_id=tweet['id']
                            )
                            if result.single():
                                logger.info(f"MENTIONED_IN relationship created or updated between Token {token} and Tweet {tweet['id']}")

                logger.info("Data successfully upserted into the graph database.")
            except Exception as e:
                logger.error("An error occurred while creating nodes and edges", extra={
                    "exception_type": e.__class__.__name__,
                    "exception_message": str(e),
                    "exception_args": e.args
                })
