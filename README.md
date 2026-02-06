# Hypergraph Context Graph

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeDB](https://img.shields.io/badge/TypeDB-3.x-green.svg)](https://typedb.com/)


**Production-ready Enterprise Context Graph using Hypergraphs and TypeDB**

This project implements a hypergraph-based context graph system for enterprise decision-making, 

## Why Hypergraphs?

Traditional knowledge graphs use pairwise edges (connecting exactly 2 nodes). But enterprise decisions are **n-ary** – they involve multiple entities simultaneously:

> "When a renewal agent proposes a 20% discount, it doesn't just pull from the CRM. It pulls from PagerDuty for incident history, Zendesk for escalation threads, Slack for VP approval from last quarter, Salesforce for the deal record, Snowflake for usage data, and the semantic layer for the definition of 'healthy customer'."

**Hypergraphs** solve this by allowing edges (hyperedges) to connect 3+ nodes, preserving the full context of enterprise decisions.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ENTERPRISE DATA SOURCES                   │
├─────────┬─────────┬─────────┬─────────┬─────────┬──────────┤
│Salesforce│ Zendesk │  Slack  │PagerDuty│Snowflake│  Custom  │
└────┬────┴────┬────┴────┬────┴────┬────┴────┬────┴────┬─────┘
     │         │         │         │         │         │
     └─────────┴─────────┴────┬────┴─────────┴─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   LLM-Powered     │
                    │   Entity          │  ◄── Claude / GPT-4
                    │   Extraction      │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │     TypeDB        │
                    │   Hypergraph      │  ◄── Native n-ary relations
                    │   Database        │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐    ┌───────▼───────┐    ┌───────▼───────┐
│ ContextAgent  │    │ExecutiveAgent │    │GovernanceAgent│
│ (Traversal)   │    │ (Reasoning)   │    │ (Compliance)  │
└───────────────┘    └───────────────┘    └───────────────┘
```

## Features

- **TypeDB Backend**: Native hypergraph storage with inference rules
- **Enterprise Connectors**: Salesforce, Zendesk, Slack, PagerDuty, Snowflake
- **LLM Integration**: Anthropic Claude, OpenAI GPT-4, Together AI
- **Entity Extraction**: LLM-powered extraction pipeline
- **Multi-Agent Reasoning**: Context, Executive, and Governance agents
- **Path Finding**: BFS and Yen's K-shortest paths with intersection constraints

## Quick Start

### Prerequisites

- Python 3.11+
- TypeDB (Cloud or Community Edition)
- API keys for LLM providers (Anthropic, OpenAI)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/hypergraph-context-graph.git
cd hypergraph-context-graph

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[all]"

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

### Start TypeDB

```bash
# Using Docker
docker run -d --name typedb -p 1729:1729 typedb/typedb:latest

# Or download from https://typedb.com/docs/home/install/ce
```

### Load Schema

```bash
python scripts/load_schema.py
```

### Run the API

```bash
uvicorn src.api.main:app --reload
```

## Configuration

Create a `.env` file with:

```env
# TypeDB
TYPEDB_HOST=localhost
TYPEDB_PORT=1729
TYPEDB_DATABASE=context_graph

# LLM Providers
LLM_ANTHROPIC_API_KEY=sk-ant-...
LLM_OPENAI_API_KEY=sk-...

# Connectors (optional)
CONNECTOR_SALESFORCE_USERNAME=...
CONNECTOR_SLACK_BOT_TOKEN=xoxb-...
```

## Usage

### Python API

```python
from src.typedb.client import TypeDBClient
from src.extraction.pipeline import EntityExtractionPipeline
from src.llm.anthropic import AnthropicConnector

# Connect to TypeDB
async with TypeDBClient() as db:
    # Insert an entity
    entity_id = await db.insert_entity(
        entity_type="customer",
        attributes={
            "entity-id": "cust_001",
            "entity-name": "Acme Corp",
            "health-score": 72.0,
            "tier": "enterprise",
        }
    )
    
    # Query the hypergraph
    results = await db.query("""
        match
            $c isa customer, has entity-name $name;
            $d isa deal;
            (involved-entity: $c, involved-entity: $d) isa decision-event;
        fetch $c: entity-name; $d: deal-value;
    """)
```

### REST API

```bash
# Query the context graph
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Why was Acme Corp given a 20% discount?"}'

# Insert an entity
curl -X POST http://localhost:8000/api/v1/entities \
  -H "Content-Type: application/json" \
  -d '{"type": "customer", "name": "Acme Corp", "attributes": {"tier": "enterprise"}}'
```

## Project Structure

```
hypergraph-context-graph/
├── src/
│   ├── typedb/           # TypeDB client and schema
│   ├── connectors/       # Enterprise data connectors
│   ├── llm/              # LLM provider integrations
│   ├── extraction/       # Entity extraction pipeline
│   ├── agents/           # Multi-agent reasoning system
│   ├── api/              # FastAPI application
│   └── models/           # Pydantic data models
├── tests/
├── scripts/
├── docs/
└── docker/
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/

# Type checking
mypy src/
```

## Roadmap

- [x] Phase 1: TypeDB Integration
- [ ] Phase 2: Enterprise Connectors
- [ ] Phase 3: LLM Connectors
- [ ] Phase 4: Multi-Agent System
- [ ] Phase 5: Production Deployment

See [ARCHITECTURE_PLAN.md](ARCHITECTURE_PLAN.md) for detailed roadmap.

## References


2. [TypeDB Documentation](https://typedb.com/docs)


## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit PRs.
