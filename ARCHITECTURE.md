# System Architecture

## Overview

The Hypergraph Context Graph is an infrastructure layer for institutional memory in enterprise AI systems. It captures decision context using hypergraph-native storage and provides reasoning constraints for agentic AI platforms.

<img src="./architecture.png" alt="System Architecture" width="1000">

---

## Architecture Layers

### 1. Data Source Connectors

Pre-built connectors for enterprise systems that capture decision-relevant events in real-time.

| Connector | Data Captured | Decision Signals |
|-----------|---------------|------------------|
| **Salesforce Connector** | Deals, Accounts, Opportunities | Approvals, discount decisions, ownership changes |
| **Slack Connector** | Messages, Threads, Reactions | VP sign-offs, escalation discussions, team decisions |
| **Zendesk Connector** | Tickets, Comments, SLAs | Support escalations, SLA breaches, resolution paths |
| **PagerDuty Connector** | Incidents, Alerts, Runbooks | Severity decisions, on-call escalations, incident responses |
| **Snowflake Connector** | Metrics, Aggregates, Logs | Usage thresholds, health scores, churn signals |
| **Jira Connector** | Issues, Sprints, Comments | Priority changes, blockers, engineering decisions |
| **Google Drive Connector** | Docs, Sheets, Policies | Policy documents, SOPs, approval matrices |
| **HubSpot Connector** | Deals, Contacts, Activities | Pipeline decisions, engagement events |

#### Connector Framework

Each connector provides:
- **Authentication**: OAuth 2.0, API keys, or service accounts
- **Real-time Events**: Webhooks where available, polling fallback
- **Schema Mapping**: Transforms source events to unified format
- **Rate Limiting**: Respects API limits with exponential backoff
- **Error Handling**: Dead letter queues for failed events

#### Production Requirements

| Requirement | Implementation |
|-------------|----------------|
| **Authentication** | OAuth 2.0 with token refresh, secrets vault integration (HashiCorp Vault) |
| **Rate Limiting** | Per-connector limits, circuit breakers, backoff strategies |
| **Schema Evolution** | Avro schema registry for backward compatibility |
| **Monitoring** | Connector health dashboards, lag alerts, throughput metrics |
| **Reliability** | At-least-once delivery, idempotency keys for deduplication |

---

### 2. Ingestion Layer

Real-time streaming pipeline for capturing and ordering events across all connectors.

#### Components

| Component | Purpose | Production Choice |
|-----------|---------|-------------------|
| **CDC (Debezium)** | Captures database changes | Row-level changes with ordering |
| **Message Broker (Kafka)** | Event streaming | 100K+ events/sec throughput |
| **Stream Processor (Flink)** | Transformations | Sub-second latency processing |
| **Schema Registry** | Event versioning | Avro/Protobuf schemas |

#### Data Flow

```
Connectors → Kafka Topics → Flink Processing → Extraction Layer
                 │
                 └── Dead Letter Queue (failed events)
```

#### Production Requirements

| Requirement | Specification |
|-------------|---------------|
| **Throughput** | 100K+ events/second |
| **Latency** | P99 < 500ms end-to-end |
| **Ordering** | Per-entity ordering guarantees |
| **Durability** | Replication factor 3, min.insync.replicas=2 |
| **Retention** | 7 days hot, 90 days cold (tiered storage) |
| **Exactly-Once** | Kafka transactions + idempotent producers |

#### Scaling Tiers

| Scale | Events/min | Architecture |
|-------|------------|--------------|
| Startup | < 10K | Single Kafka broker |
| Growth | 10K - 100K | 3-node Kafka cluster |
| Enterprise | 100K - 1M | Multi-AZ Kafka + dedicated Flink |
| Large Enterprise | 1M+ | Regional clusters, Pulsar consideration |

---

### 3. Extraction Layer

Transforms raw events into structured decision events using LLM-powered extraction.

#### Dual-Pass Extraction Pipeline

```
Raw Event → Pre-filter → Coarse Pass → Fine Pass → Validation → Hypergraph
               │            │              │            │
          (Rule-based)  (Fast LLM)    (Strong LLM)  (Schema check)
               │            │              │
          Skip 70-80%   Decision?     Extract fields
          of events     (yes/no)      + confidence
```

| Pass | Model | Purpose | Cost |
|------|-------|---------|------|
| **Pre-filter** | Rules | Keyword matching, event type filtering | Free |
| **Coarse Pass** | Claude Haiku | Binary: is this a decision? | ~$0.001/event |
| **Fine Pass** | Claude Sonnet | Structured extraction with confidence | ~$0.01/decision |

#### Entity Resolution

Resolves different representations of the same entity:

- "Acme Corp" = "Acme Corporation" = "ACME" = `customer_acme`

| Similarity Score | Action |
|-----------------|--------|
| ≥ 0.95 | Auto-merge |
| 0.85 - 0.95 | Human review queue |
| < 0.85 | Create new entity |

#### Production Requirements

| Requirement | Implementation |
|-------------|----------------|
| **LLM Provider** | Anthropic API with Azure OpenAI fallback |
| **Vector Database** | Pinecone (managed) or Qdrant (self-hosted) |
| **Embedding Model** | text-embedding-3-large (1536 dims) |
| **Batch Processing** | 50 events per batch, async calls |
| **Confidence Threshold** | ≥ 0.85 for auto-acceptance |
| **Human-in-the-Loop** | Review queue for low-confidence extractions |
| **Cost Control** | Budget alerts, token tracking, model routing |

---

### 4. Hypergraph Core

The central storage and query engine for n-ary relationships.

#### Storage Layer

| Component | Purpose | Production Choice |
|-----------|---------|-------------------|
| **Node Store** | Entity storage | PostgreSQL + Citus (sharded) |
| **Hyperedge Store** | Decision events | PostgreSQL with JSONB |
| **Incidence Index** | Node ↔ Edge mapping | Inverted index in Redis |
| **Vector Store** | Embeddings | Qdrant or pgvector |

**Key Design Principle**: Unlike pairwise graphs, a single hyperedge captures the full decision context (all participants, policies, and outcomes together).

#### Query Layer

**IS ≥ 2 Constraint (Intersection Size)**

The core innovation: adjacent hyperedges must share ≥2 nodes to form valid paths.

- Eliminates spurious paths through unrelated decisions
- Ensures contextual relevance in traversals
- Implemented via inverted index for O(1) lookups

**Traversal Algorithms**

| Algorithm | Purpose | Use Case |
|-----------|---------|----------|
| **BFS with IS constraint** | Shortest path | "How are X and Y connected?" |
| **Yen K-Paths** | K diverse paths | "Show all ways X relates to Y" |
| **S-Walk** | Connectivity analysis | "What's the decision neighborhood?" |

#### Analysis Layer

| Analysis | Purpose | Output |
|----------|---------|--------|
| **S-Components** | Find decision clusters | Higher S = stable patterns |
| **Rich Club** | Detect concentration | Are hubs over-connected? |
| **Hub Detection** | Identify key entities | Power law distribution |

#### Production Requirements

| Requirement | Specification |
|-------------|---------------|
| **Database** | PostgreSQL 15+ with Citus extension |
| **Sharding** | By tenant_id, 32+ shards |
| **Replication** | Streaming replication, 2 read replicas |
| **Cache** | Redis Cluster for hot paths (64GB+) |
| **Query Latency** | P99 < 100ms for path queries |
| **Backup** | Continuous WAL archiving to S3 |

#### Scaling Tiers

| Nodes | Hyperedges | Architecture |
|-------|------------|--------------|
| < 1M | < 5M | Single PostgreSQL |
| 1M - 10M | 5M - 50M | Citus (8 shards) |
| 10M - 100M | 50M - 500M | Citus (32 shards) + Redis |
| 100M+ | 500M+ | Custom distributed store |

---

### 5. Agent System

Multi-agent architecture for decision reasoning with strict security boundaries.

#### Agent Roles

```
                    ┌──────────────┐
                    │  User Query  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   Context    │  ← ONLY agent with hypergraph access
                    │    Agent     │  ← Security boundary
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
    │  Executive  │ │ Governance  │ │   Memory   │
    │    Agent    │ │    Agent    │ │   Store    │
    │             │ │             │ │            │
    │ Interprets  │ │  Validates  │ │  Session   │
    │   paths     │ │  compliance │ │   state    │
    └─────────────┘ └─────────────┘ └────────────┘
```

| Agent | Responsibility | Access |
|-------|----------------|--------|
| **Context Agent** | Finds hypergraph paths | Graph read-only |
| **Executive Agent** | Mechanistic interpretation | Paths only (no graph) |
| **Governance Agent** | Compliance validation | Paths + policy lookup |
| **Agent Memory** | Session state | Redis cache |

#### Production Requirements

| Requirement | Implementation |
|-------------|----------------|
| **LLM** | Claude Sonnet for reasoning agents |
| **Orchestration** | LangGraph or custom state machine |
| **Memory** | Redis with 1-hour TTL per session |
| **Timeout** | 60s total, 30s per agent |
| **Fallback** | Graceful degradation if agent fails |
| **Observability** | Trace each agent call, log reasoning |

---

### 6. Platform Layer

External interfaces for consuming the hypergraph.

#### API Gateway

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/query` | POST | Natural language query |
| `/v1/paths/{start}/{end}` | GET | Find paths between entities |
| `/v1/entities/{id}` | GET | Entity details and connections |
| `/v1/decisions` | GET | List decisions with filters |
| `/v1/decisions/{id}/explain` | GET | Decision explanation |

#### SDKs

- **Python**: `pip install hypergraph-context`
- **JavaScript**: `npm install @hypergraph/context`
- **Go**: `go get github.com/hypergraph/context-go`

#### Webhooks

Real-time notifications for:
- `decision.created` — New decision captured
- `entity.merged` — Entities resolved
- `alert.triggered` — Governance alerts

#### Explorer UI

- Visual graph exploration
- Path highlighting
- Decision timeline
- Search and filter

#### Production Requirements

| Requirement | Implementation |
|-------------|----------------|
| **Authentication** | OAuth 2.0 / JWT / API keys |
| **Rate Limiting** | Per-tenant limits (1000 req/min default) |
| **Caching** | CDN for static, Redis for dynamic |
| **Documentation** | OpenAPI spec, interactive docs |

---

## Enterprise Requirements

### Multi-Tenancy

| Layer | Isolation Method |
|-------|------------------|
| **API** | tenant_id in JWT, request validation |
| **Kafka** | Separate topics per tenant |
| **Database** | Row-level security + tenant_id sharding |
| **Redis** | Key prefix: `{tenant_id}:...` |
| **Vector Store** | Namespace per tenant |

### Security & Compliance

| Requirement | Implementation |
|-------------|----------------|
| **Authentication** | SAML 2.0, OIDC, OAuth 2.0 |
| **Authorization** | RBAC with row-level security |
| **Encryption at Rest** | AES-256 |
| **Encryption in Transit** | TLS 1.3 |
| **Audit Logging** | All queries and mutations logged |
| **Data Residency** | Regional deployment (US, EU, APAC) |
| **SOC 2 Type II** | Annual certification |
| **GDPR** | Right to deletion, data export |
| **HIPAA** | BAA available for healthcare |

### Observability

| Component | Tool |
|-----------|------|
| **Metrics** | Prometheus + Grafana |
| **Logging** | Loki or Elasticsearch |
| **Tracing** | Jaeger or Honeycomb |
| **Alerting** | PagerDuty integration |

**Key Metrics:**
- Ingestion lag (target: < 1 min)
- Extraction latency P99 (target: < 5s)
- Query latency P99 (target: < 2s)
- Agent response P99 (target: < 10s)
- LLM costs per tenant

---

## Data Flow Summary

```
1. Salesforce deal updated
      ↓
2. Salesforce Connector captures via Streaming API
      ↓
3. Event published to Kafka (tenant partition)
      ↓
4. Pre-filter: Is this a decision event?
      ↓
5. Coarse pass: Claude Haiku confirms candidate
      ↓
6. Fine pass: Claude Sonnet extracts DecisionEvent
      ↓
7. Entity resolution: Match or create entities
      ↓
8. Hyperedge created: {deal, vp, customer, policy}
      ↓
9. Indexes updated: IS constraint cache refreshed
      ↓
10. Query: "Why did Customer Z get 20% discount?"
      ↓
11. Context Agent: BFS finds path through incident + approval
      ↓
12. Executive Agent: "SLA breach → VP approved retention discount"
      ↓
13. Governance Agent: "Compliant with policy, precedent exists"
```

---

## Key Differentiators

| Traditional Graph | Hypergraph Context Graph |
|-------------------|--------------------------|
| Pairwise edges (A→B) | N-ary hyperedges ({A,B,C,D}) |
| Loses context in expansion | Preserves full decision context |
| No intersection constraints | IS ≥ 2 eliminates spurious paths |
| Post-hoc governance | In-path compliance validation |
| Probabilistic hops | Structural necessity |
| Slow n-way joins | O(1) inverted index lookups |

---

## References

1. [GitHub Repository](https://github.com/vibhavjoshi123/Hypergraph-for-Context-Graph)
