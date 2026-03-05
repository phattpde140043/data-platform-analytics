# data-platform-analytics

End-to-end data platform that simulates e-commerce marketplace traffic, streams events through an ETL pipeline, stores them in a data warehouse, and exposes analytics via a GraphQL API.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        E-Commerce Data Platform                         │
│                                                                         │
│  ┌──────────────┐    ┌─────────────────┐    ┌────────────────────────┐ │
│  │  Simulator   │───▶│    Streaming    │───▶│     ETL Pipeline       │ │
│  │              │    │  (LocalQueue /  │    │  (Extract-Transform-   │ │
│  │ EventGenerator│   │   Kafka-compat) │    │   Load)                │ │
│  │  Simulator   │    │  EventProducer  │    │  ETLPipeline           │ │
│  └──────────────┘    └─────────────────┘    └──────────┬─────────────┘ │
│                                                         │               │
│                                                         ▼               │
│                                              ┌────────────────────────┐ │
│                                              │    Data Warehouse      │ │
│                                              │    (DuckDB)            │ │
│                                              │                        │ │
│                                              │ • user_activity        │ │
│                                              │ • product_interactions │ │
│                                              │ • sales_transactions   │ │
│                                              └──────────┬─────────────┘ │
│                                                         │               │
│                                                         ▼               │
│                                              ┌────────────────────────┐ │
│                                              │    GraphQL API         │ │
│                                              │    (FastAPI +          │ │
│                                              │     Strawberry)        │ │
│                                              │                        │ │
│                                              │ /graphql               │ │
│                                              │ /health                │ │
│                                              └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
User Activity Events
       │
       ▼
┌─────────────────┐
│   Simulator     │  Generates synthetic events:
│                 │   user_login, product_view,
│  EventGenerator │   product_search, add_to_cart,
│  + Simulator    │   checkout_purchase
└────────┬────────┘
         │ publish(topic, event)
         ▼
┌─────────────────┐
│  LocalQueue     │  Thread-safe in-process queue
│  (or Kafka)     │  compatible with Kafka's
│                 │  produce/consume interface
└────────┬────────┘
         │ consume(topic)
         ▼
┌─────────────────┐
│  ETL Pipeline   │  Route events to the right tables:
│                 │   • All events  → user_activity
│  ETLPipeline    │   • views/carts → product_interactions
│                 │   • purchases   → sales_transactions
└────────┬────────┘
         │ INSERT OR IGNORE
         ▼
┌─────────────────┐
│  DuckDB         │  Analytics-optimised tables
│  DataWarehouse  │   • user_activity
│                 │   • product_interactions
│                 │   • sales_transactions
└────────┬────────┘
         │ SQL queries
         ▼
┌─────────────────┐
│  GraphQL API    │  Queries available:
│                 │   • mostViewedProducts
│  /graphql       │   • topSellingProducts
│                 │   • conversionRate
│                 │   • revenueByCategory
└─────────────────┘
```

---

## Project Structure

```
data-platform-analytics/
├── src/
│   ├── simulator/
│   │   ├── __init__.py
│   │   ├── event_generator.py   # Generates realistic e-commerce events
│   │   └── simulator.py         # Drives the generator at a configurable rate
│   ├── streaming/
│   │   ├── __init__.py
│   │   ├── queue.py             # Thread-safe local queue (Kafka-compatible API)
│   │   └── producer.py          # Background-thread event producer
│   ├── etl/
│   │   ├── __init__.py
│   │   └── pipeline.py          # ETL pipeline (consume → transform → load)
│   ├── warehouse/
│   │   ├── __init__.py
│   │   └── schema.py            # DuckDB schema + analytics query helpers
│   └── api/
│       ├── __init__.py
│       └── graphql_api.py       # FastAPI + Strawberry GraphQL API
├── tests/
│   ├── test_simulator.py
│   ├── test_streaming.py
│   ├── test_etl.py
│   ├── test_warehouse.py
│   └── test_api.py
├── requirements.txt
├── setup.py
└── README.md
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the simulator and ETL pipeline locally

```python
from src.streaming.queue import LocalQueue
from src.warehouse.schema import DataWarehouse
from src.simulator.simulator import Simulator
from src.etl.pipeline import ETLPipeline

# Create the shared queue and warehouse
queue = LocalQueue()
wh = DataWarehouse(db_path="warehouse.duckdb")

# Seed the warehouse with 500 synthetic events (no sleep)
sim = Simulator(queue=queue, num_users=500)
sim.run_burst(total_events=500)

# Run the ETL pipeline to load events into the warehouse
pipeline = ETLPipeline(queue=queue, warehouse=wh)
pipeline.process_batch()
print(f"Processed {pipeline.processed_count} events")
```

### 3. Start the background producer + continuous ETL

```python
import threading
from src.streaming.queue import LocalQueue
from src.warehouse.schema import DataWarehouse
from src.streaming.producer import EventProducer
from src.etl.pipeline import ETLPipeline

stop = threading.Event()
q = LocalQueue()
wh = DataWarehouse(db_path="warehouse.duckdb")

producer = EventProducer(queue=q, events_per_second=20)
producer.start()

pipeline = ETLPipeline(queue=q, warehouse=wh)
pipeline.run_continuous(poll_interval=1.0, stop_event=stop)
# Press Ctrl-C or set stop.set() to stop
```

### 4. Start the GraphQL API server

```bash
# Point at an existing warehouse file (or :memory: for a fresh one)
export WAREHOUSE_DB_PATH=warehouse.duckdb
uvicorn src.api.graphql_api:app --reload --host 0.0.0.0 --port 8000
```

Open the interactive GraphiQL playground at: <http://localhost:8000/graphql>

### 5. Example GraphQL queries

```graphql
# Most viewed products
{
  mostViewedProducts(limit: 5) {
    productId
    productName
    category
    viewCount
  }
}

# Top selling products
{
  topSellingProducts(limit: 5) {
    productId
    productName
    unitsSold
    totalRevenue
  }
}

# Overall session conversion rate
{
  conversionRate {
    rate
  }
}

# Revenue broken down by category
{
  revenueByCategory {
    category
    totalRevenue
    transactionCount
  }
}
```

---

## Running tests

```bash
pytest tests/ -v
```

---

## Configuration

| Environment Variable  | Default          | Description                          |
|-----------------------|------------------|--------------------------------------|
| `WAREHOUSE_DB_PATH`   | `warehouse.duckdb` | Path to the DuckDB database file.  |

---

## Simulated Events

| Event Type           | Key Fields                                                   |
|----------------------|--------------------------------------------------------------|
| `user_login`         | user_id, session_id, timestamp, device                       |
| `product_view`       | user_id, session_id, product_id, category, price, timestamp  |
| `product_search`     | user_id, session_id, query, results_count, timestamp         |
| `add_to_cart`        | user_id, session_id, product_id, category, price, quantity   |
| `checkout_purchase`  | user_id, session_id, product_id, order_id, total_amount, payment_method |

---

## Analytics Tables

| Table                   | Description                                  |
|-------------------------|----------------------------------------------|
| `user_activity`         | Login, search, and browse events per session |
| `product_interactions`  | Product views and cart additions             |
| `sales_transactions`    | Completed purchases with order details       |

