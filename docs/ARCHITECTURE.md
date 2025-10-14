# System Architecture

**Project:** GPU Infrastructure Monitoring Stack  
**Version:** 1.0  
**Last Updated:** October 2025

---

## Overview

This monitoring stack demonstrates production-grade observability patterns for GPU infrastructure using Docker Compose. The architecture implements a complete metrics pipeline from collection through visualization, designed to mirror patterns used in large-scale GPU clusters.

---

## Design Principles

### 1. Service Isolation
Each component runs in its own container with defined resource boundaries and restart policies.

### 2. Data Persistence
Critical data (metrics, dashboards, database) stored in named Docker volumes that survive container restarts.

### 3. Network Security
All inter-container communication happens on an isolated bridge network. Only Grafana and Prometheus are exposed externally.

### 4. Observability First
Every component exposes metrics and can be monitored. The monitoring system monitors itself.

### 5. Resource Efficiency
Configured memory limits prevent OOM kills while maintaining performance.

---

## System Components

### Core Monitoring Layer

#### Prometheus (Port 9090)
**Purpose:** Time-series database and metrics collection engine

**Configuration:**
- Scrape interval: 15 seconds
- Evaluation interval: 15 seconds (for alert rules)
- Retention period: 30 days
- Storage: Named volume `prometheus_data`

**Key Features:**
- Automatic service discovery via static configuration
- PromQL query engine for flexible data analysis
- Alert rule evaluation
- HTTP API for integrations

**Resources:**
- Memory: ~110MB stable usage
- CPU: 2-3% average
- Disk: ~500MB for 30-day retention

#### Grafana (Port 3000)
**Purpose:** Visualization and dashboarding platform

**Configuration:**
- Provisioned datasource: Prometheus
- Auto-loaded dashboards
- 5-second refresh rate
- Storage: Named volume `grafana_data`

**Key Features:**
- Pre-configured CoreWeave Infrastructure dashboard
- Real-time metric visualization
- Alert management UI
- Dashboard version control

**Resources:**
- Memory: ~142MB stable usage
- CPU: 0.5-1% average

---

### System Exporters Layer

#### Node Exporter (Port 9100)
**Purpose:** Host system metrics collection

**Metrics Exposed:**
- CPU usage by core and mode
- Memory utilization and swap
- Disk I/O and filesystem usage
- Network interface statistics
- System load averages

**Labels:** `instance="monitoring-host"`, `role="infrastructure"`

#### cAdvisor (Port 8080)
**Purpose:** Container resource monitoring

**Metrics Exposed:**
- Per-container CPU usage
- Memory usage and limits
- Network I/O per container
- Filesystem usage per container
- Container lifecycle events

**Special Requirements:**
- Runs in privileged mode
- Mounts `/sys`, `/var/lib/docker`, `/var/run`
- Built-in health check endpoint

**Resources:**
- Memory: ~70MB
- CPU: 2-3% (higher due to container scanning)

---

### Application Stack Layer

#### Python Application (Port 8000)
**Purpose:** Custom metrics application with GPU simulation

**Endpoints:**
- `/metrics` - Prometheus metrics
- `/api/test` - Test endpoint
- `/health` - Health check

**Custom Metrics:**
- `app_requests_total` - Counter of HTTP requests
- `app_request_duration_seconds` - Histogram of request latency
- `app_active_connections` - Gauge of active connections

**Resource Limits:**
- Memory: 256MB max, 128MB reserved
- Prevents OOM kills experienced in early versions

#### Nginx (Port 80)
**Purpose:** Web server demonstrating frontend monitoring

**Nginx Exporter (Port 9113):**
- Connection statistics
- Request rates
- Active connections
- HTTP status code distribution

#### Redis (Port 6379)
**Purpose:** Cache layer demonstrating data store monitoring

**Redis Exporter (Port 9121):**
- Cache hit/miss ratios
- Memory usage
- Connected clients
- Command statistics
- Keyspace information

#### PostgreSQL (Port 5432)
**Purpose:** Database demonstrating SQL monitoring

**Postgres Exporter (Port 9187):**
- Database size and growth
- Active connections
- Transaction rates
- Table and index statistics
- Query performance metrics

**Credentials:** 
- Database: `metrics_db`
- User: `metrics_user`
- Password: Set via environment variable

---

### Simulation Layer

#### GPU Simulator (Port 9400)
**Purpose:** Simulates 8 GPU devices with realistic metrics

**Metrics Generated:**
- `gpu_utilization_percent` - Compute utilization per GPU
- `gpu_temperature_celsius` - Temperature tracking
- `gpu_memory_usage_bytes` - VRAM consumption
- `gpu_power_draw_watts` - Power usage
- `gpu_sm_clock_mhz` - GPU clock speeds
- `gpu_ecc_errors_total` - Error tracking

**Simulation Logic:**
- Random utilization between 20-90%
- Temperature correlated with utilization
- Realistic power draw curves
- Occasional error injection (0.1% rate)

**Labels:** 
- `gpu_id` - GPU identifier (gpu0-gpu7)
- `gpu_model` - "NVIDIA-A100-40GB"

#### ML Workload Simulator (Port 9500)
**Purpose:** Simulates ML training/inference patterns

**Metrics Generated:**
- `inference_latency_seconds` - Model inference timing
- `ml_job_queue_depth` - Queue depth tracking
- `training_accuracy` - Training progress
- `training_loss` - Loss values
- `batch_processing_time_seconds` - Batch timing
- `checkpoint_saves_total` - Checkpoint counter

**Patterns:**
- Realistic training curves
- Queue depth fluctuations
- Inference latency distributions

#### Load Generator
**Purpose:** Creates realistic HTTP traffic for testing

**Configuration:**
- Target URLs: nginx, python-app
- Request interval: ~5 seconds
- Mix of successful (200) and error (500) responses
- Random endpoint selection

---

## Network Architecture

### Docker Bridge Network

```
Network: monitoring-project_monitoring
Driver: bridge
Subnet: 172.18.0.0/16 (Docker default)
Gateway: 172.18.0.1

DNS Resolution:
  prometheus.monitoring → Container IP
  grafana.monitoring → Container IP
  All containers accessible by name
```

### Service Discovery

Prometheus discovers targets via static configuration:

```yaml
scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['prometheus:9090']
  
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
  
  # ... additional jobs
```

### External Access

**Exposed Ports:**
- `3000` - Grafana dashboard (LoadBalancer)
- `9090` - Prometheus UI (LoadBalancer)

**Firewall Configuration:**
- Source IP restricted to operator's IP
- All other ports internal-only

---

## Data Flow Pipeline

```
┌─────────────────────────────────────────────────────────┐
│                    Metrics Generation                    │
│  Applications → /metrics endpoints                       │
│  System → Node Exporter                                 │
│  Containers → cAdvisor                                  │
│  GPUs → GPU Simulator                                   │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP GET /metrics (every 15s)
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Prometheus Scraper                      │
│  • Discovers targets from config                        │
│  • Scrapes metrics via HTTP                             │
│  • Applies relabeling rules                             │
│  • Validates and parses metrics                         │
└────────────────────┬────────────────────────────────────┘
                     │ Write to TSDB
                     ▼
┌─────────────────────────────────────────────────────────┐
│             Prometheus Time-Series Database              │
│  • Stores metrics in chunks                             │
│  • Compacts old data                                    │
│  • Applies retention policy (30 days)                   │
│  • Indexes for fast queries                             │
└────────────────────┬────────────────────────────────────┘
                     │ PromQL Queries
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   Grafana Dashboard                      │
│  • Queries Prometheus every 5 seconds                   │
│  • Renders visualizations                               │
│  • Evaluates alert conditions                           │
│  • Serves dashboard to user                             │
└─────────────────────────────────────────────────────────┘
```

---

## Storage Architecture

### Volume Management

```yaml
Named Volumes:
  prometheus_data:
    - Time-series database
    - 30-day retention
    - ~500MB after 1 week

  grafana_data:
    - Dashboard configurations
    - User settings
    - ~50MB typical

  postgres_data:
    - Database persistence
    - Application data
    - ~25MB typical
```

### Data Retention Strategy

**Prometheus:**
- Retention time: 30 days
- Retention size: No limit (could add 10GB max)
- Compact frequency: 2-hour blocks
- Cleanup frequency: Daily

**Logs:**
- Docker json-file driver (default)
- No log rotation configured (could add)
- Logs accessible via `docker logs`

---

## Metrics Architecture

### Metric Types

**Counters** (monotonically increasing):
- `app_requests_total` - HTTP request count
- `node_cpu_seconds_total` - CPU time
- `gpu_ecc_errors_total` - GPU errors
- `checkpoint_saves_total` - Checkpoint saves

**Gauges** (can increase or decrease):
- `gpu_utilization_percent` - GPU usage
- `gpu_temperature_celsius` - Temperature
- `job_queue_size` - Queue depth
- `app_active_connections` - Connections
- `node_memory_MemAvailable_bytes` - Available memory

**Histograms** (distribution tracking):
- `app_request_duration_seconds` - Request latency
- `inference_latency_seconds` - Inference timing
- `batch_processing_time_seconds` - Batch timing

### Label Strategy

**Standard Labels:**
- `instance` - Unique identifier for the target
- `job` - Scrape job name
- `role` - Functional classification

**Application Labels:**
- `app` - Application name
- `tier` - Architecture tier (frontend/cache/database)
- `endpoint` - API endpoint path
- `status` - HTTP status code

**GPU Labels:**
- `gpu_id` - GPU identifier (gpu0-gpu7)
- `gpu_model` - Model type
- `component` - Component type (gpu/ml)

**Best Practices Applied:**
- High-cardinality labels avoided
- Consistent naming across metrics
- Labels used for filtering, not aggregation

---

## Performance Characteristics

### Query Performance
- Average query response: ~40ms
- P95 query response: <100ms
- Dashboard load time: <2 seconds
- Concurrent queries supported: 10+

### Resource Usage
```
Total Stack:
  CPU: ~5% of 2 vCPUs
  Memory: 520MB / 3.8GB (13%)
  Disk I/O: <10MB/s
  Network: ~1MB/s during scrapes

Per Component:
  Prometheus: 110MB RAM, 2% CPU
  Grafana: 142MB RAM, 0.5% CPU
  cAdvisor: 70MB RAM, 2.5% CPU
  All others: <20MB RAM each
```

### Scalability Limits

**Current Configuration Supports:**
- Up to 20 scrape targets
- ~2,000 metrics per target
- 15-second minimum scrape interval
- Single-host deployment only

**To Scale Beyond:**
- Migrate to Kubernetes
- Implement Prometheus federation
- Use remote write to long-term storage
- Add Thanos or Cortex

---

## High Availability Considerations

### Current Implementation
- Single point of failure (one host)
- Container restart policy: `unless-stopped`
- Data survives container restarts via volumes
- No automatic failover

### Production Improvements Needed
1. **Prometheus HA**
   - Deploy 2+ Prometheus instances
   - Use Thanos for deduplication
   - Remote write to centralized storage

2. **Grafana HA**
   - Multiple Grafana instances
   - Shared database backend
   - Load balancer in front

3. **Storage HA**
   - Replicated volumes
   - Cloud storage backends
   - Regular backups to object storage

---

## Security Architecture

### Network Security
- Docker bridge network isolation
- Only Grafana/Prometheus exposed
- No database ports externally accessible
- Firewall rules restrict source IPs

### Access Control
- Grafana: Username/password authentication
- Prometheus: No authentication (internal only)
- Databases: Password protected

### Future Security Enhancements
- Implement OAuth for Grafana
- Add authentication proxy for Prometheus
- Enable TLS for all endpoints
- Implement RBAC
- Add network policies

---

## Monitoring Best Practices Demonstrated

### 1. Four Golden Signals
- **Latency:** Request duration histograms
- **Traffic:** Request rate counters
- **Errors:** Error rate by endpoint
- **Saturation:** Queue depth, GPU utilization

### 2. USE Method (Resources)
- **Utilization:** CPU, memory, GPU usage
- **Saturation:** Queue depth
- **Errors:** GPU errors, HTTP 5xx

### 3. RED Method (Services)
- **Rate:** Request rate tracking
- **Errors:** Error rate percentages
- **Duration:** Latency percentiles (p95, p99)

---

## Technology Choices

### Why Prometheus?
- Industry standard for metrics
- Powerful query language (PromQL)
- Efficient storage format
- Large ecosystem of exporters
- Pull-based model (good for ephemeral workloads)

### Why Grafana?
- Best-in-class visualization
- Strong Prometheus integration
- Dashboard provisioning
- Alerting capabilities
- Open source with large community

### Why Docker Compose?
- Rapid prototyping
- Simple orchestration
- Easy local development
- Good for learning
- Clear migration path to Kubernetes

---

## Lessons Learned

### What Worked Well
- Service isolation prevented cascading failures
- Memory limits prevented OOM kills
- Static configuration simple to debug
- Volume persistence worked reliably

### What Would Be Better in Kubernetes
- Auto-scaling based on metrics
- Service discovery for dynamic targets
- Better resource management
- High availability patterns
- Declarative configuration

---

## Future Architecture Evolution

### Phase 2: Kubernetes Migration
- StatefulSets for Prometheus/Grafana
- DaemonSet for node-exporter
- ServiceMonitors for auto-discovery
- Helm charts for deployment
- Ingress for traffic routing

### Phase 3: Production Hardening
- Thanos for unlimited retention
- AlertManager integration
- Grafana Loki for logs
- Distributed tracing (Jaeger)
- Multi-cluster federation

---

## Conclusion

This architecture successfully demonstrates production-grade monitoring patterns using industry-standard tools. While Docker Compose has limitations for production workloads, it provided an excellent foundation for understanding observability concepts before transitioning to Kubernetes.