# Influence Insights Indexer

### Hardware Requirements
- **Neo4j**: 2 CPU cores, 8 GB RAM, ~100 GB+ SSD storage
- **Scheduler (Indexer)**: 2 CPU cores, 2 GB RAM

### System Configuration

```diff
- Most users need only what is explained in this documentation. Editing the docker-compose files and the optional variables may create problems and is for advanced users only!
```

### Setup

#### Prerequisites

Make sure you have `pm2` installed from the miner [documentation](https://github.com/blockchain-insights/crypto-influence-insights/blob/main/MINER_SETUP.md#prerequisites)

#### Repository

Clone this repository:
```bash
git clone https://github.com/blockchain-insights/crypto-influence-insights-indexer.git
```

#### Environment Configuration

- Navigate to ```crypto-influence-insights-indexer``` and copy the example ```.env``` file:
```bash
cd crypto-influence-insights-indexer
cp .env.example ./ops/.env
```
 
- Edit the .env file to set appropriate configurations. At a minimum, set the following:

```
    GRAPH_DB_USER={put-here-your-username}
    GRAPH_DB_PASSWORD={put-here-your-password}
    REDIS_URL=redis://localhost:6379/0
    SCRAPE_TOKEN=PEPE
    INDEXER_INTERVAL_HOURS=24
    TRIGGER_IMMEDIATE=true
```
### Running Components

#### Running all components via docker compose

The system includes:
- Neo4j (Graph Database)
- Scheduler (Celery-based Indexer)
- Redis (Message Queue)
- Scheduler UI (Flower)

To start all required components, navigate to the ops directory and run:

```bash
docker compose up -d
```
  
This will start Neo4j, the scheduler, Redis, and the Flower UI.

#### Running the Indexer Manually 

The indexer is managed using Celery and automatically runs on the configured schedule. To manually run the indexer, use the following command:

```bash
cd src
celery -A scheduler worker --beat -E --loglevel=info
```
This will start the Twitter PEPE indexing process. The scheduler scrapes Twitter data for the PEPE token and updates the Neo4j database with relevant information about tweets, user accounts, and regions.

### Monitoring

You can monitor the system using Flower, a web-based Celery monitoring tool. Access it via: http://localhost:5555
Flower provides real-time updates on tasks and worker statuses.

Alternatively, you can check the logs for detailed insights:

```bash
docker logs -f scheduler
```
### Next Steps

Once the indexer is running and Neo4j is populated with data, you can integrate it with the miner to perform further analyses and validations. 
Follow the miner setup guide [start the miners](https://github.com/blockchain-insights/crypto-influence-insights/blob/main/MINER_SETUP.md).