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
    APIFY_API_KEY={put-your-apify-key-value-here}
    POSTGRES_DB=indexer_db
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD={your-password}
    POSTGRES_HOST=localhost
    POSTGRES_PORT=5432
    DATABASE_URL=postgresql+asyncpg://postgres:{your-password}$@localhost:5432/indexer_db
    SCRAPE_START_DATE="2024-07-01"
    MAX_ITEMS=1200
    SCRAPE_TOKEN=PEPE
    REDIS_URL=redis://localhost:6379/0
    INDEXER_INTERVAL_HOURS=24
    TRIGGER_IMMEDIATE=true
    PINATA_API_KEY={your-pinata-api-key}
    PINATA_SECRET_API_KEY={your-pinata-secret-api-key}
    MINER_KEY={your-miner-key-address}

```
### Running Components

#### Running all components via docker compose

The system includes:
- Postgres (For storing links to IPFS JSON datasets with scraped data)
- Scheduler (Celery-based Indexer)
- Redis (Message Queue)
- Scheduler UI (Flower)

To start all required components, navigate to the ops directory and run:

```bash
docker compose up -d
```
  
This will start Postgres, the scheduler, Redis, and the Flower UI.

#### Running the Indexer Manually 

The indexer is managed using Celery and automatically runs on the configured schedule. To manually run the indexer, use the following command:

```bash
cd src
celery -A scheduler worker --beat -E --loglevel=info
```
This will start the Twitter PEPE indexing process. The scheduler scrapes Twitter data for the PEPE token and updates the Postgres database with an IPFS link to the JSON dataset with scraped data.

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