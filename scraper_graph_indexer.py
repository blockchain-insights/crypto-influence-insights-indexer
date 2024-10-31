import os
from neo4j import GraphDatabase
from loguru import logger

class ScraperGraphIndexer:
    def __init__(self, graph_db_url: str = None, graph_db_user: str = None, graph_db_password: str = None):
        """
        Initialize the connection to the Neo4j database.
        """
        self.graph_db_url = graph_db_url or os.environ.get("GRAPH_DB_URL", "bolt://localhost:7687")
        self.graph_db_user = graph_db_user or os.environ.get("GRAPH_DB_USER", "neo4j")
        self.graph_db_password = graph_db_password or os.environ.get("GRAPH_DB_PASSWORD", "password")
        self.driver = GraphDatabase.driver(self.graph_db_url, auth=(self.graph_db_user, self.graph_db_password))

    def close(self):
        self.driver.close()

    def create_nodes_and_edges(self, data):
        """
        Insert nodes and relationships for Token, Tweet, UserAccount, and Region, as well as MENTIONS, POSTED, and LOCATED_IN relationships.
        """
        with self.driver.session() as session:
            try:
                for entry in data:
                    token = entry['token']
                    tweet = entry['tweet']
                    user_account = entry['user_account']
                    region = entry['region']
                    edges = entry['edges']

                    # Create or merge Token node
                    session.run(
                        """
                        MERGE (t:Token {name: $token_name})
                        """,
                        token_name=token
                    )
                    logger.info(f"Token node created or merged: {token}")

                    # Create or merge Tweet node
                    session.run(
                        """
                        MERGE (tw:Tweet {id: $tweet_id})
                        SET tw.url = $url, tw.text = $text, tw.likes = $likes, tw.timestamp = $timestamp
                        """,
                        tweet_id=tweet['id'],
                        url=tweet['url'],
                        text=tweet['text'],
                        likes=tweet['likes'],
                        timestamp=tweet['timestamp']
                    )
                    logger.info(f"Tweet node created or merged: {tweet['id']}")

                    # Create or merge UserAccount node
                    session.run(
                        """
                        MERGE (ua:UserAccount {user_id: $user_id})
                        SET ua.username = $username, ua.is_verified = $is_verified
                        """,
                        user_id=user_account['user_id'],
                        username=user_account['username'],
                        is_verified=user_account['is_verified']
                    )
                    logger.info(f"UserAccount node created or merged: {user_account['user_id']}")

                    # Create or merge Region node (if available)
                    if region.get('name') and region['name'] != "Unknown":
                        session.run(
                            """
                            MERGE (r:Region {name: $region_name})
                            """,
                            region_name=region['name']
                        )
                        logger.info(f"Region node created or merged: {region['name']}")

                    # Insert relationships (edges) based on edge types in data
                    for edge in edges:
                        if edge['type'] == 'MENTIONS':
                            session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (t:Token {name: $token_name})
                                MERGE (ua)-[:MENTIONS {timestamp: $timestamp, hashtag_count: $hashtag_count}]->(t)
                                """,
                                user_id=user_account['user_id'],
                                token_name=token,
                                timestamp=edge['attributes']['timestamp'],
                                hashtag_count=edge['attributes']['hashtag_count']
                            )
                            logger.info(f"MENTIONS edge created between UserAccount {user_account['user_id']} and Token {token}")

                        elif edge['type'] == 'POSTED':
                            session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (tw:Tweet {id: $tweet_id})
                                MERGE (ua)-[:POSTED {timestamp: $timestamp, likes: $likes}]->(tw)
                                """,
                                user_id=user_account['user_id'],
                                tweet_id=tweet['id'],
                                timestamp=edge['attributes']['timestamp'],
                                likes=edge['attributes']['likes']
                            )
                            logger.info(f"POSTED edge created between UserAccount {user_account['user_id']} and Tweet {tweet['id']}")

                        elif edge['type'] == 'LOCATED_IN' and region.get('name') != "Unknown":
                            session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (r:Region {name: $region_name})
                                MERGE (ua)-[:LOCATED_IN]->(r)
                                """,
                                user_id=user_account['user_id'],
                                region_name=region['name']
                            )
                            logger.info(f"LOCATED_IN edge created between UserAccount {user_account['user_id']} and Region {region['name']}")

                logger.info("Data successfully inserted into the graph database.")

            except Exception as e:
                logger.error("An error occurred while creating nodes and edges", extra={
                    "exception_type": e.__class__.__name__,
                    "exception_message": str(e),
                    "exception_args": e.args
                })

# Example usage
if __name__ == '__main__':
    # Initialize graph indexer
    graph_indexer = ScraperGraphIndexer()

    # Mock data structure representing scraped data
    scraped_data = [
        {
            'token': 'PEPE',
            'tweet': {
                'id': '12345',
                'url': 'https://twitter.com/example_tweet',
                'text': 'Check out $PEPE!',
                'likes': 100,
                'timestamp': '2024-01-01 00:00:00'
            },
            'user_account': {
                'username': 'crypto_user',
                'user_id': 'u123',
                'is_verified': True
            },
            'region': {
                'name': 'USA'
            },
            'edges': [
                {
                    'type': 'MENTIONS',
                    'attributes': {
                        'timestamp': '2024-01-01 00:00:00',
                        'hashtag_count': 2
                    }
                },
                {
                    'type': 'POSTED',
                    'attributes': {
                        'timestamp': '2024-01-01 00:00:00',
                        'likes': 100
                    }
                },
                {
                    'type': 'LOCATED_IN'
                }
            ]
        }
    ]

    # Insert data into Neo4j
    graph_indexer.create_nodes_and_edges(scraped_data)

    # Close connection
    graph_indexer.close()
