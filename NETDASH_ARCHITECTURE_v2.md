# NetDash - Complete System Re-Architecture
## High-Level Design (HLD) & Low-Level Design (LLD) Document

**Version:** 2.0  
**Date:** 2024  
**Classification:** System Control Center Architecture

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [High-Level Architecture](#high-level-architecture)
3. [System Components](#system-components)
4. [Data Flow Architecture](#data-flow-architecture)
5. [Real-Time Monitoring Pipeline](#real-time-monitoring-pipeline)
6. [Low-Level Design - Backend Services](#low-level-design---backend-services)
7. [Low-Level Design - Frontend](#low-level-design---frontend)
8. [Database Schema](#database-schema)
9. [API Specifications](#api-specifications)
10. [Security Architecture](#security-architecture)
11. [Deployment Architecture](#deployment-architecture)

---

## Executive Summary

NetDash is re-architected as a modern, scalable Network & System Control Center with:
- **Microservices-based backend** with dedicated collectors, processors, and API gateways
- **Real-time WebSocket streaming** for sub-second metric updates
- **Dynamic Dashboard Builder** allowing admins to create custom screens with drag-and-drop cards
- **Plugin-based metric sources** supporting system commands, SNMP, agent-based collectors, and cloud APIs
- **Time-series data storage** with automatic aggregation and retention policies

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Web Dashboard│  │  Mobile App  │  │  Large Screen│  │  API Clients │  │
│  │   (React)     │  │  (React Native)│   (Kiosk)    │  │   (Python)   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼─────────────────┼─────────────────┼─────────────────┼──────────┘
          │                 │                 │                 │
          └─────────────────┴─────────────────┴─────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │     LOAD BALANCER (Nginx)      │
                    │    SSL/TLS Termination         │
                    └───────────────┬───────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
┌─────────▼─────────┐    ┌───────────▼────────────┐   ┌───────▼────────┐
│   WebSocket       │    │    REST API Gateway    │   │  Static Assets │
│   Gateway         │    │    (Rate Limiting)     │   │   (CDN Cache)  │
│   (Socket.io)     │    │                        │   │                │
└─────────┬─────────┘    └───────────┬────────────┘   └────────────────┘
          │                          │
          │          ┌───────────────┼───────────────┐
          │          │               │               │
┌─────────▼──────────▼───┐  ┌────────▼────────┐  ┌───▼────────────┐
│   Real-Time Stream     │  │   Dashboard     │  │   System       │
│   Processing Service   │  │   Builder API   │  │   Control API  │
│   (Node.js/Go)         │  │   (Python/FastAPI)│  │   (Python)     │
└─────────┬──────────────┘  └────────┬────────┘  └────┬───────────┘
          │                          │                │
          │          ┌───────────────┼────────────────┘
          │          │               │
┌─────────▼──────────▼───┐  ┌────────▼────────┐  ┌──────────────┐
│   Metrics Collection   │  │   Configuration │  │   Alerting   │
│   Engine (Python)      │  │   Service       │  │   Engine     │
│                        │  │   (PostgreSQL)  │  │   (Celery)   │
└─────────┬──────────────┘  └─────────────────┘  └──────────────┘
          │
    ┌─────┴─────────────────────────────────────────────────────────┐
    │                     DATA LAYER                                │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
    │  │  Time-Series│  │   Cache     │  │   Message   │           │
    │  │  (InfluxDB) │  │  (Redis)    │  │   Queue     │           │
    │  │             │  │             │  │  (RabbitMQ) │           │
    │  └─────────────┘  └─────────────┘  └─────────────┘           │
    │                                                              │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
    │  │  Document   │  │   Search    │  │   Object    │           │
    │  │  (MongoDB)  │  │Elasticsearch│  │   Storage   │           │
    │  │             │  │             │  │  (MinIO)    │           │
    │  └─────────────┘  └─────────────┘  └─────────────┘           │
    └───────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼───────────────────────────────┐
    │                     COLLECTION LAYER                        │
    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐│
    │  │ System  │  │ Network │  │  SNMP   │  │  Agent  │  │ Cloud  ││
    │  │Commands │  │ Scanners│  │Queries  │  │   APIs  │  │  APIs  ││
    │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └────────┘│
    └───────────────────────────────────────────────────────────────┘
```

---

## System Components

### 1. Frontend Layer (React + TypeScript)

**Component: Dashboard Builder Core**
```typescript
interface DashboardBuilder {
  // Screen Management
  createScreen(config: ScreenConfig): Screen;
  deleteScreen(id: string): void;
  cloneScreen(id: string): Screen;
  
  // Card System
  addCard(screenId: string, card: CardConfig): void;
  removeCard(screenId: string, cardId: string): void;
  updateCardLayout(screenId: string, layout: GridLayout): void;
  
  // Real-time Updates
  subscribeToMetric(metricId: string): WebSocketStream;
  updateCardData(cardId: string, data: MetricData): void;
}

interface CardConfig {
  id: string;
  type: CardType;
  title: string;
  dataSource: DataSource;
  visualization: VisualizationConfig;
  refreshInterval: number; // milliseconds
  alerts: AlertConfig[];
}

type CardType = 
  | 'gauge'           // Circular/linear gauges
  | 'chart'           // Line, bar, area charts
  | 'metric'          // Single large number with trend
  | 'table'           // Sortable data tables
  | 'topology'        // Network graph visualization
  | 'heatmap'         // Density/performance heatmaps
  | 'log-stream'      // Real-time log tail
  | 'command'         // Interactive command executor
  | 'custom-html';    // User-defined HTML/JS
```

**Component: Visualization Library**
- **Gauge Cards:** D3.js-based circular gauges with configurable min/max, thresholds, color zones
- **Chart Cards:** Apache ECharts integration with real-time streaming updates
- **Topology Cards:** Cytoscape.js for interactive network topology diagrams
- **Heatmap Cards:** Custom canvas-based performance heatmaps

### 2. API Gateway Layer (FastAPI)

**Service: netdash-api-gateway**
```python
# Core Routers
/api/v1/dashboards      # CRUD for dashboard screens
/api/v1/cards           # Card template management
/api/v1/metrics         # Metric metadata and querying
/api/v1/data            # Time-series data queries
/api/v1/commands        # System command execution
/api/v1/alerts          # Alert configuration and history
/api/v1/topology        # Network topology operations
/api/v1/system          # System control operations

# WebSocket Endpoints
/ws/metrics/{stream_id}     # Real-time metric streams
/ws/events                  # System events/alerts
/ws/topology/{topology_id}  # Live topology updates
/ws/logs/{service_id}       # Real-time log streaming
```

### 3. Metrics Collection Engine

**Component: Metric Collector Service**
```python
class MetricCollector:
    """
    Pluggable metric collection framework
    """
    
    # Collection Strategies
    COLLECTORS = {
        'system': SystemCommandCollector(),      # vmstat, iostat, netstat, etc.
        'network': NetworkCommandCollector(),     # ping, traceroute, nmap, etc.
        'procfs': ProcFSCollector(),              # /proc filesystem parsing
        'sysfs': SysFSCollector(),                # /sys filesystem parsing
        'snmp': SNMPCollector(),                  # SNMP v1/v2c/v3 queries
        'ipmi': IPMICollector(),                  # Hardware sensor data
        'docker': DockerCollector(),              # Container metrics
        'kubernetes': K8sCollector(),             # K8s cluster metrics
        'custom': CustomScriptCollector(),        # User-defined scripts
    }
    
    async def collect_metric(self, metric_config: MetricConfig) -> MetricData:
        collector = self.COLLECTORS[metric_config.source]
        raw_data = await collector.fetch(metric_config.params)
        processed = self.processors[metric_config.type].transform(raw_data)
        return processed

class SystemCommandCollector:
    """
    Secure command execution with caching and rate limiting
    """
    ALLOWED_COMMANDS = {
        'cpu_usage': 'mpstat -P ALL 1 1',
        'memory_usage': 'free -m',
        'disk_usage': 'df -h',
        'network_io': 'cat /proc/net/dev',
        'active_connections': 'ss -tunap',
        'process_list': 'ps aux --sort=-%cpu',
        'interface_stats': 'ip -s link',
        'route_table': 'ip route',
        'arp_table': 'ip neigh',
    }
    
    async def execute(self, command_key: str, timeout: int = 30) -> dict:
        # Security validation
        if command_key not in self.ALLOWED_COMMANDS:
            raise SecurityError(f"Command {command_key} not allowed")
        
        # Execute with privilege dropping
        result = await self._run_sandboxed(self.ALLOWED_COMMANDS[command_key], timeout)
        return self._parse_output(command_key, result)
```

### 4. Time-Series Database (InfluxDB)

**Schema Design:**
```sql
-- Measurements (Tables)
CREATE MEASUREMENT system_cpu (
    time TIMESTAMP,
    host TAG,
    cpu_id TAG,           -- 'all' or specific core
    user FLOAT,
    system FLOAT,
    iowait FLOAT,
    steal FLOAT,
    idle FLOAT
);

CREATE MEASUREMENT system_memory (
    time TIMESTAMP,
    host TAG,
    total_bytes INT,
    used_bytes INT,
    free_bytes INT,
    cached_bytes INT,
    buffers_bytes INT,
    swap_total INT,
    swap_used INT
);

CREATE MEASUREMENT network_interface (
    time TIMESTAMP,
    host TAG,
    interface TAG,
    rx_bytes INT,
    tx_bytes INT,
    rx_packets INT,
    tx_packets INT,
    rx_errors INT,
    tx_errors INT,
    rx_dropped INT,
    tx_dropped INT
);

CREATE MEASUREMENT network_latency (
    time TIMESTAMP,
    source TAG,
    target TAG,
    latency_ms FLOAT,
    packet_loss FLOAT,
    jitter_ms FLOAT
);

CREATE MEASUREMENT process_stats (
    time TIMESTAMP,
    host TAG,
    pid TAG,
    name TAG,
    cpu_percent FLOAT,
    memory_percent FLOAT,
    memory_rss INT,
    threads INT
);

-- Retention Policies
CREATE RETENTION POLICY "raw_7d" ON netdash DURATION 7d REPLICATION 1 DEFAULT;
CREATE RETENTION POLICY "hourly_30d" ON netdash DURATION 30d REPLICATION 1;
CREATE RETENTION POLICY "daily_1y" ON netdash DURATION 52w REPLICATION 1;

-- Continuous Queries for Downsampling
CREATE CONTINUOUS QUERY "cq_hourly_cpu" ON netdash
BEGIN
    SELECT mean(user) AS user, mean(system) AS system
    INTO hourly_30d.system_cpu
    FROM system_cpu
    GROUP BY time(1h), host, cpu_id
END;
```

---

## Real-Time Monitoring Pipeline

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    REAL-TIME PIPELINE                               │
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │   Source     │────▶│   Stream     │────▶│   Time-Series│        │
│  │   Adapters   │     │   Processor  │     │   Database   │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│          │                   │                   │                  │
│          │                   │                   │                  │
│          ▼                   ▼                   ▼                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │  Command     │     │  Rule Engine │     │  Aggregation │        │
│  │  Collectors  │     │  (Alerts)    │     │  Engine      │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│                              │                                      │
│                              ▼                                      │
│                       ┌──────────────┐                               │
│                       │  WebSocket   │                               │
│                       │  Broadcast   │◄──────────────────────┐      │
│                       └──────────────┘                       │      │
│                              │                               │      │
└──────────────────────────────┼───────────────────────────────┼──────┘
                               │                               │
                               ▼                               ▼
                    ┌──────────────┐                  ┌──────────────┐
                    │   Dashboard  │                  │   Alert      │
                    │   Clients    │                  │   Notifiers  │
                    └──────────────┘                  └──────────────┘
```

### Stream Processing Logic

```python
class StreamProcessor:
    """
    Apache Kafka / Redis Streams based real-time processing
    """
    
    async def process_metric_stream(self):
        async for message in self.kafka_consumer:
            metric = Metric.parse(message.value)
            
            # 1. Normalize and enrich
            enriched = await self.enrich_metric(metric)
            
            # 2. Run through rule engine
            alerts = self.rule_engine.evaluate(enriched)
            
            # 3. Write to time-series DB
            await self.influxdb.write(enriched)
            
            # 4. Check real-time subscriptions
            await self.websocket_manager.broadcast(enriched)
            
            # 5. Trigger alerts if thresholds breached
            for alert in alerts:
                await self.alert_manager.trigger(alert)

class RuleEngine:
    """
    Complex event processing for alerting
    """
    
    RULE_TYPES = {
        'threshold': ThresholdRule,
        'anomaly': AnomalyDetectionRule,
        'trend': TrendAnalysisRule,
        'pattern': PatternMatchRule,
        'composite': CompositeRule,
    }
    
    def evaluate(self, metric: Metric) -> List[Alert]:
        applicable_rules = self.get_rules_for_metric(metric)
        triggered = []
        
        for rule in applicable_rules:
            if rule.evaluate(metric):
                triggered.append(Alert(
                    rule_id=rule.id,
                    severity=rule.severity,
                    message=rule.generate_message(metric),
                    context=metric.to_dict()
                ))
        
        return triggered
```

---

## Low-Level Design - Backend Services

### Service 1: Metrics API Service (Python/FastAPI)

**File Structure:**
```
netdash/
├── services/
│   ├── metrics-api/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py              # FastAPI application
│   │   │   ├── config.py            # Settings management
│   │   │   ├── dependencies.py      # Dependency injection
│   │   │   ├── routers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dashboards.py    # Dashboard CRUD
│   │   │   │   ├── cards.py         # Card operations
│   │   │   │   ├── metrics.py       # Metric metadata
│   │   │   │   ├── data.py          # Time-series queries
│   │   │   │   ├── commands.py      # Command execution
│   │   │   │   ├── topology.py      # Network topology
│   │   │   │   └── system.py        # System control
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── collector.py     # Metrics collection
│   │   │   │   ├── query_builder.py # InfluxDB query builder
│   │   │   │   ├── command_runner.py # Secure command exec
│   │   │   │   └── topology_mapper.py # Network discovery
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dashboard.py     # Pydantic models
│   │   │   │   ├── card.py
│   │   │   │   ├── metric.py
│   │   │   │   └── command.py
│   │   │   └── websocket/
│   │   │       ├── __init__.py
│   │   │       ├── manager.py       # Connection management
│   │   │       └── handlers.py      # Message handlers
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── pyproject.toml
```

**Key Implementation Details:**

```python
# services/metrics-api/app/routers/data.py
from fastapi import APIRouter, Query, Depends
from typing import List, Optional
from datetime import datetime, timedelta
from app.services.query_builder import InfluxQueryBuilder
from app.models.metric import MetricData, TimeRange

router = APIRouter(prefix="/api/v1/data", tags=["data"])

@router.get("/query")
async def query_metrics(
    measurement: str,
    fields: List[str] = Query(...),
    tags: Optional[dict] = None,
    time_range: TimeRange = Depends(),
    aggregation: Optional[str] = "mean",
    interval: Optional[str] = "1m",
    query_builder: InfluxQueryBuilder = Depends()
) -> MetricData:
    """
    Query time-series data with flexible aggregation
    """
    query = query_builder.build(
        measurement=measurement,
        fields=fields,
        tags=tags,
        time_range=time_range,
        aggregation=aggregation,
        interval=interval
    )
    
    result = await query_builder.execute(query)
    return MetricData.from_influx_result(result)

@router.get("/stats")
async def get_statistics(
    measurement: str,
    field: str,
    time_range: TimeRange = Depends(),
    stats: List[str] = Query(default=["mean", "min", "max", "stddev"])
) -> dict:
    """
    Get statistical summary for a metric
    """
    # Returns: {"mean": X, "min": Y, "max": Z, "stddev": W}
    pass
```

### Service 2: Collector Service (Python Asyncio)

**Architecture:**
```python
# services/collector/app/main.py
import asyncio
from typing import Dict, List
from dataclasses import dataclass
from croniter import croniter

@dataclass
class CollectionJob:
    id: str
    metric_type: str
    source: str
    interval: int  # seconds
    parameters: dict
    last_run: Optional[datetime]
    next_run: datetime

class CollectorEngine:
    def __init__(self):
        self.collectors: Dict[str, BaseCollector] = {}
        self.scheduler = AsyncIOScheduler()
        self.output_queue = asyncio.Queue()
        
    async def register_collector(self, collector: BaseCollector):
        self.collectors[collector.name] = collector
        
    async def schedule_job(self, job: CollectionJob):
        self.scheduler.add_job(
            self.execute_collection,
            trigger="interval",
            seconds=job.interval,
            args=[job],
            id=job.id,
            replace_existing=True
        )
        
    async def execute_collection(self, job: CollectionJob):
        try:
            collector = self.collectors[job.source]
            data = await collector.collect(job.parameters)
            
            await self.output_queue.put({
                "job_id": job.id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
                "status": "success"
            })
        except Exception as e:
            logger.error(f"Collection failed for {job.id}: {e}")
            await self.handle_collection_failure(job, e)
```

### Service 3: WebSocket Gateway (Node.js/Socket.io)

```javascript
// services/ws-gateway/src/server.ts
import { Server } from "socket.io";
import { createAdapter } from "@socket.io/redis-adapter";
import { createClient } from "redis";

interface MetricStreamConfig {
  metricId: string;
  aggregation: string;
  interval: number;
  filters?: Record<string, string>;
}

class WebSocketGateway {
  private io: Server;
  private redisPub: RedisClient;
  private redisSub: RedisClient;
  
  constructor() {
    this.io = new Server({
      cors: { origin: "*", methods: ["GET", "POST"] },
      pingTimeout: 60000,
      pingInterval: 25000,
    });
    
    // Redis adapter for horizontal scaling
    this.io.adapter(createAdapter(this.redisPub, this.redisSub));
  }
  
  private setupHandlers() {
    this.io.on("connection", (socket) => {
      console.log(`Client connected: ${socket.id}`);
      
      // Subscribe to metric streams
      socket.on("subscribe:metrics", (config: MetricStreamConfig) => {
        const roomId = `metric:${config.metricId}`;
        socket.join(roomId);
        
        // Send initial data
        this.sendHistoricalData(socket, config);
        
        // Set up real-time forwarding
        this.setupMetricForwarder(socket, config);
      });
      
      // Topology updates
      socket.on("subscribe:topology", (topologyId: string) => {
        socket.join(`topology:${topologyId}`);
      });
      
      // Log streaming
      socket.on("subscribe:logs", (serviceId: string) => {
        socket.join(`logs:${serviceId}`);
      });
      
      socket.on("disconnect", () => {
        console.log(`Client disconnected: ${socket.id}`);
      });
    });
  }
  
  // Broadcast to all subscribers of a metric
  public broadcastMetric(metricId: string, data: any) {
    this.io.to(`metric:${metricId}`).emit("metric:update", {
      timestamp: Date.now(),
      data: data
    });
  }
}
```

---

## Low-Level Design - Frontend

### Architecture: React + TypeScript + Zustand State Management

**Directory Structure:**
```
netdash-frontend/
├── src/
│   ├── components/
│   │   ├── ui/                    # Shadcn/ui base components
│   │   ├── cards/                 # Dashboard card implementations
│   │   │   ├── GaugeCard/
│   │   │   ├── ChartCard/
│   │   │   ├── MetricCard/
│   │   │   ├── TableCard/
│   │   │   ├── TopologyCard/
│   │   │   ├── HeatmapCard/
│   │   │   ├── LogStreamCard/
│   │   │   └── CommandCard/
│   │   ├── layout/
│   │   │   ├── DashboardGrid.tsx   # React-Grid-Layout wrapper
│   │   │   ├── ScreenTabs.tsx     # Screen navigation
│   │   │   ├── Header.tsx         # Top navigation bar
│   │   │   └── Sidebar.tsx        # Card palette
│   │   └── builder/
│   │       ├── CardPalette.tsx    # Draggable card types
│   │       ├── PropertyPanel.tsx  # Card configuration
│   │       └── ScreenSettings.tsx # Screen-level settings
│   ├── hooks/
│   │   ├── useWebSocket.ts        # Real-time connection management
│   │   ├── useMetrics.ts          # Metric data fetching
│   │   ├── useDashboard.ts        # Dashboard CRUD operations
│   │   └── useTopology.ts         # Topology visualization
│   ├── stores/
│   │   ├── dashboardStore.ts      # Zustand dashboard state
│   │   ├── metricStore.ts         # Real-time metric cache
│   │   └── uiStore.ts             # UI state (selections, modals)
│   ├── services/
│   │   ├── api.ts                 # REST API client (axios)
│   │   ├── websocket.ts           # WebSocket client manager
│   │   └── queries.ts             # TanStack Query definitions
│   ├── types/
│   │   ├── dashboard.ts
│   │   ├── cards.ts
│   │   ├── metrics.ts
│   │   └── api.ts
│   ├── lib/
│   │   ├── utils.ts               # Utility functions
│   │   ├── formatters.ts          # Data formatters (bytes, duration)
│   │   └── validators.ts          # Input validation
│   └── App.tsx
```

### Card Component Architecture

```typescript
// src/components/cards/GaugeCard/index.tsx
import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { useWebSocket } from '@/hooks/useWebSocket';
import { GaugeCardConfig } from '@/types/cards';

interface GaugeCardProps {
  config: GaugeCardConfig;
  isEditing: boolean;
}

export function GaugeCard({ config, isEditing }: GaugeCardProps) {
  const gaugeRef = useRef<SVGSVGElement>(null);
  const { data, isConnected } = useWebSocket(config.dataSource.metricId);
  
  useEffect(() => {
    if (!gaugeRef.current || !data) return;
    
    // D3 gauge rendering
    const svg = d3.select(gaugeRef.current);
    const width = gaugeRef.current.clientWidth;
    const height = gaugeRef.current.clientHeight;
    const radius = Math.min(width, height) / 2;
    
    // Clear previous
    svg.selectAll("*").remove();
    
    // Draw gauge arc
    const arc = d3.arc()
      .innerRadius(radius * 0.6)
      .outerRadius(radius * 0.9)
      .startAngle(-Math.PI / 2)
      .endAngle(Math.PI / 2);
    
    // Background arc
    svg.append("path")
      .attr("d", arc)
      .attr("fill", "#e5e7eb")
      .attr("transform", `translate(${width/2}, ${height/2})`);
    
    // Value arc with color zones
    const valueScale = d3.scaleLinear()
      .domain([config.min, config.max])
      .range([-Math.PI / 2, Math.PI / 2]);
    
    const valueArc = d3.arc()
      .innerRadius(radius * 0.6)
      .outerRadius(radius * 0.9)
      .startAngle(-Math.PI / 2)
      .endAngle(valueScale(data.value));
    
    const color = getColorForValue(data.value, config.thresholds);
    
    svg.append("path")
      .attr("d", valueArc)
      .attr("fill", color)
      .attr("transform", `translate(${width/2}, ${height/2})`)
      .transition()
      .duration(config.animationDuration || 750)
      .ease(d3.easeCubicOut);
    
    // Value text
    svg.append("text")
      .attr("x", width / 2)
      .attr("y", height / 2 + 5)
      .attr("text-anchor", "middle")
      .attr("font-size", "2rem")
      .attr("font-weight", "bold")
      .text(formatValue(data.value, config.unit));
      
  }, [data, config]);
  
  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">{config.title}</h3>
          <ConnectionStatus connected={isConnected} />
        </div>
      </CardHeader>
      <CardContent className="flex-1 relative">
        <svg ref={gaugeRef} className="w-full h-full" />
      </CardContent>
    </Card>
  );
}
```

### Dashboard Grid System

```typescript
// src/components/layout/DashboardGrid.tsx
import { useMemo } from 'react';
import GridLayout from 'react-grid-layout';
import { CardComponent } from './CardComponent';
import { useDashboardStore } from '@/stores/dashboardStore';
import 'react-grid-layout/css/styles.css';

const GRID_COLS = 12;
const ROW_HEIGHT = 60;

export function DashboardGrid({ screenId, isEditing }: DashboardGridProps) {
  const { screens, updateCardLayout } = useDashboardStore();
  const screen = screens[screenId];
  
  const layouts = useMemo(() => {
    return {
      lg: screen.cards.map(card => ({
        i: card.id,
        x: card.layout.x,
        y: card.layout.y,
        w: card.layout.w,
        h: card.layout.h,
        minW: card.layout.minW || 2,
        minH: card.layout.minH || 2,
        maxW: card.layout.maxW || 12,
        maxH: card.layout.maxH || 20,
      }))
    };
  }, [screen.cards]);
  
  const onLayoutChange = (layout: GridLayout.Layout[]) => {
    const updates = layout.map(item => ({
      cardId: item.i,
      layout: {
        x: item.x,
        y: item.y,
        w: item.w,
        h: item.h,
      }
    }));
    updateCardLayout(screenId, updates);
  };
  
  return (
    <GridLayout
      className="layout"
      layouts={layouts}
      cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
      rowHeight={ROW_HEIGHT}
      width={1200}
      isDraggable={isEditing}
      isResizable={isEditing}
      onLayoutChange={onLayoutChange}
      compactType="vertical"
      preventCollision={false}
    >
      {screen.cards.map(card => (
        <div key={card.id} className="bg-card rounded-lg border shadow-sm">
          <CardComponent
            type={card.type}
            config={card.config}
            isEditing={isEditing}
          />
        </div>
      ))}
    </GridLayout>
  );
}
```

---

## API Specifications

### Dashboard Management API

```yaml
# OpenAPI 3.0 Specification
openapi: 3.0.0
info:
  title: NetDash Dashboard API
  version: 2.0.0

paths:
  /api/v1/screens:
    get:
      summary: List all dashboard screens
      responses:
        200:
          description: List of screens
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Screen'
    
    post:
      summary: Create new screen
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ScreenCreate'
      responses:
        201:
          description: Created screen
          
  /api/v1/screens/{id}:
    get:
      summary: Get screen by ID
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
    
    put:
      summary: Update screen
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ScreenUpdate'
    
    delete:
      summary: Delete screen

  /api/v1/screens/{id}/cards:
    post:
      summary: Add card to screen
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CardCreate'
              
    put:
      summary: Update card layout (batch)
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                layouts:
                  type: array
                  items:
                    $ref: '#/components/schemas/CardLayoutUpdate'

components:
  schemas:
    Screen:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        refreshInterval:
          type: integer
          default: 5000
        layout:
          type: string
          enum: [grid, freeform, tabs]
        cards:
          type: array
          items:
            $ref: '#/components/schemas/Card'
        createdAt:
          type: string
          format: date-time
        updatedAt:
          type: string
          format: date-time
    
    Card:
      type: object
      properties:
        id:
          type: string
        type:
          type: string
          enum: [gauge, chart, metric, table, topology, heatmap, log-stream, command, custom-html]
        title:
          type: string
        dataSource:
          $ref: '#/components/schemas/DataSource'
        visualization:
          $ref: '#/components/schemas/VisualizationConfig'
        layout:
          $ref: '#/components/schemas/LayoutConfig'
        alerts:
          type: array
          items:
            $ref: '#/components/schemas/AlertConfig'
    
    DataSource:
      type: object
      properties:
        type:
          type: string
          enum: [metric, command, api, static]
        metricId:
          type: string
        command:
          type: string
        parameters:
          type: object
        refreshInterval:
          type: integer
          default: 5000
    
    LayoutConfig:
      type: object
      properties:
        x:
          type: integer
        y:
          type: integer
        w:
          type: integer
        h:
          type: integer
        minW:
          type: integer
        minH:
          type: integer
```

### Command Execution API

```yaml
paths:
  /api/v1/commands/execute:
    post:
      summary: Execute system command
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                command:
                  type: string
                  enum: [ping, traceroute, nslookup, dig, netstat, ss, nmap, tcpdump, custom]
                target:
                  type: string
                parameters:
                  type: object
                timeout:
                  type: integer
                  default: 30
      responses:
        202:
          description: Command accepted, returns job ID
          content:
            application/json:
              schema:
                type: object
                properties:
                  jobId:
                    type: string
                  status:
                    type: string
                    enum: [queued, running, completed, failed]
                  estimatedDuration:
                    type: integer

  /api/v1/commands/jobs/{jobId}:
    get:
      summary: Get command job status
      responses:
        200:
          description: Job status and results
          content:
            application/json:
              schema:
                type: object
                properties:
                  jobId:
                    type: string
                  status:
                    type: string
                  progress:
                    type: integer
                  result:
                    type: object
                  error:
                    type: string
                  startedAt:
                    type: string
                    format: date-time
                  completedAt:
                    type: string
                    format: date-time

  /api/v1/commands/stream/{jobId}:
    get:
      summary: Stream command output in real-time
      responses:
        200:
          description: Server-sent events stream
          content:
            text/event-stream:
              schema:
                type: string
```

---

## Security Architecture

### Authentication & Authorization

```
┌─────────────────────────────────────────────────────────────────┐
│                     SECURITY LAYERS                              │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Transport                                             │
│  - TLS 1.3 for all connections                                  │
│  - Certificate pinning for agents                             │
│  - HSTS headers                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: API Gateway                                           │
│  - JWT token validation                                         │
│  - Rate limiting (per-user, per-IP)                             │
│  - Request signing for internal services                      │
│  - CORS policy enforcement                                      │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Service-Level                                         │
│  - RBAC (Role-Based Access Control)                             │
│  - Permission matrix for commands                               │
│  - Resource ownership validation                              │
│  - Audit logging                                                │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: Command Execution                                     │
│  - Whitelist-only command execution                             │
│  - Sandboxed execution environment                              │
│  - Privilege dropping                                           │
│  - Output sanitization (MAC/IP masking)                         │
└─────────────────────────────────────────────────────────────────┘
```

**RBAC Model:**
```typescript
type Role = 'admin' | 'operator' | 'viewer';

interface Permission {
  resource: 'dashboard' | 'command' | 'system' | 'topology' | 'alert';
  action: 'read' | 'write' | 'execute' | 'delete' | 'admin';
  scope?: string; // specific resource ID or wildcard
}

const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  admin: [
    { resource: 'dashboard', action: 'admin' },
    { resource: 'command', action: 'admin' },
    { resource: 'system', action: 'admin' },
    { resource: 'topology', action: 'admin' },
    { resource: 'alert', action: 'admin' },
  ],
  operator: [
    { resource: 'dashboard', action: 'read' },
    { resource: 'dashboard', action: 'write' },
    { resource: 'command', action: 'execute' },
    { resource: 'system', action: 'read' },
    { resource: 'topology', action: 'read' },
    { resource: 'alert', action: 'read' },
    { resource: 'alert', action: 'write' },
  ],
  viewer: [
    { resource: 'dashboard', action: 'read' },
    { resource: 'system', action: 'read' },
    { resource: 'topology', action: 'read' },
    { resource: 'alert', action: 'read' },
  ],
};
```

### Command Security

```python
class SecureCommandExecutor:
    """
    Defense-in-depth command execution
    """
    
    ALLOWED_COMMANDS = {
        'ping': {
            'cmd': '/usr/bin/ping',
            'args': ['-c', '{count}', '{target}'],
            'max_count': 10,
            'timeout': 30,
            'requires_target': True,
        },
        'traceroute': {
            'cmd': '/usr/bin/traceroute',
            'args': ['-m', '{max_hops}', '{target}'],
            'max_hops': 30,
            'timeout': 60,
            'requires_target': True,
        },
        'nmap_fast': {
            'cmd': '/usr/bin/nmap',
            'args': ['-F', '-T4', '--open', '{target}'],
            'timeout': 300,
            'rate_limit': '1/m',  # Once per minute
        },
        # ... etc
    }
    
    async def execute(self, command_key: str, params: dict, user: User) -> Job:
        # 1. Verify user has permission
        if not self.authz.check(user, 'command', 'execute', command_key):
            raise UnauthorizedError()
        
        # 2. Validate command exists
        if command_key not in self.ALLOWED_COMMANDS:
            raise InvalidCommandError()
        
        config = self.ALLOWED_COMMANDS[command_key]
        
        # 3. Validate parameters
        if config['requires_target']:
            target = params.get('target')
            if not self._validate_target(target):
                raise InvalidTargetError()
        
        # 4. Apply rate limiting
        if not await self.rate_limiter.check(user.id, command_key, config.get('rate_limit')):
            raise RateLimitError()
        
        # 5. Build sanitized command
        cmd = self._build_command(config, params)
        
        # 6. Execute in sandboxed environment
        job = await self.sandbox.execute(cmd, timeout=config['timeout'])
        
        # 7. Sanitize output
        job.result = self._sanitize_output(job.result)
        
        # 8. Log audit trail
        await self.audit.log({
            'user': user.id,
            'command': command_key,
            'params': params,
            'job_id': job.id,
            'timestamp': datetime.utcnow(),
        })
        
        return job
    
    def _sanitize_output(self, output: str) -> str:
        """Remove sensitive information from output"""
        # Mask MAC addresses
        output = re.sub(r'([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', 'XX:XX:XX:XX:XX:XX', output)
        # Mask internal IPs (optional, based on security policy)
        # output = re.sub(r'\b192\.168\.\d+\.\d+\b', 'XXX.XXX.XXX.XXX', output)
        return output
```

---

## Deployment Architecture

### Docker Compose Setup (Development)

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Frontend
  netdash-ui:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - api-gateway

  # API Gateway
  api-gateway:
    build:
      context: ./services/metrics-api
    ports:
      - "8080:8080"
    environment:
      - INFLUXDB_URL=http://influxdb:8086
      - REDIS_URL=redis://redis:6379
      - POSTGRES_URL=postgresql://postgres:5432/netdash
    depends_on:
      - influxdb
      - redis
      - postgres

  # Metrics Collector
  collector:
    build:
      context: ./services/collector
    environment:
      - INFLUXDB_URL=http://influxdb:8086
      - KAFKA_BROKER=kafka:9092
    depends_on:
      - influxdb
      - kafka
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /var/run/docker.sock:/var/run/docker.sock
    privileged: true  # Required for some system metrics

  # WebSocket Gateway
  ws-gateway:
    build:
      context: ./services/ws-gateway
    ports:
      - "8081:8081"
    environment:
      - REDIS_URL=redis://redis:6379
      - KAFKA_BROKER=kafka:9092

  # Databases
  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    volumes:
      - influxdb-data:/var/lib/influxdb2
    environment:
      - INFLUXDB_DB=netdash
      - INFLUXDB_ADMIN_USER=admin
      - INFLUXDB_ADMIN_PASSWORD=admin123

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=netdash
      - POSTGRES_USER=netdash
      - POSTGRES_PASSWORD=netdash123
    volumes:
      - postgres-data:/var/lib/postgresql/data

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
    depends_on:
      - zookeeper

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

volumes:
  influxdb-data:
  redis-data:
  postgres-data:
```

### Kubernetes Deployment (Production)

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: netdash
  labels:
    app.kubernetes.io/name: netdash
    app.kubernetes.io/version: "2.0.0"

---
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: netdash-api
  namespace: netdash
spec:
  replicas: 3
  selector:
    matchLabels:
      app: netdash-api
  template:
    metadata:
      labels:
        app: netdash-api
    spec:
      containers:
        - name: api
          image: netdash/api:latest
          ports:
            - containerPort: 8080
          env:
            - name: INFLUXDB_URL
              valueFrom:
                secretKeyRef:
                  name: netdash-secrets
                  key: influxdb-url
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: netdash-secrets
                  key: redis-url
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: netdash-ingress
  namespace: netdash
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - netdash.example.com
      secretName: netdash-tls
  rules:
    - host: netdash.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: netdash-api
                port:
                  number: 8080
          - path: /ws
            pathType: Prefix
            backend:
              service:
                name: netdash-ws
                port:
                  number: 8081
          - path: /
            pathType: Prefix
            backend:
              service:
                name: netdash-ui
                port:
                  number: 80
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up project structure and Docker environment
- [ ] Implement core backend API (FastAPI)
- [ ] Set up InfluxDB and Redis
- [ ] Basic command execution framework
- [ ] Authentication system

### Phase 2: Data Collection (Weeks 3-4)
- [ ] Implement system metrics collectors
- [ ] Network command integration (ping, traceroute, nmap)
- [ ] Real-time streaming pipeline
- [ ] Time-series data storage optimization

### Phase 3: Dashboard Builder (Weeks 5-6)
- [ ] React frontend setup with TypeScript
- [ ] Grid layout system implementation
- [ ] Card component library (Gauge, Chart, Metric)
- [ ] WebSocket integration for real-time updates
- [ ] Dashboard CRUD operations

### Phase 4: Advanced Features (Weeks 7-8)
- [ ] Network topology visualization
- [ ] Custom card builder (HTML/JS)
- [ ] Alert system with rules engine
- [ ] Screen templates and cloning
- [ ] Export/Import functionality

### Phase 5: Production Readiness (Weeks 9-10)
- [ ] Security hardening
- [ ] Performance optimization
- [ ] Kubernetes deployment manifests
- [ ] Monitoring and logging
- [ ] Documentation and testing

---

## Appendix

### A. Metric Collection Intervals

| Metric Category | Collection Interval | Retention Policy |
|----------------|---------------------|------------------|
| CPU/Memory | 5 seconds | 7 days (raw), 30 days (1m avg), 1 year (1h avg) |
| Network IO | 5 seconds | 7 days (raw), 30 days (1m avg), 1 year (1h avg) |
| Disk Usage | 60 seconds | 30 days (raw), 1 year (daily) |
| Process Stats | 30 seconds | 7 days (raw), 30 days (top 50 processes) |
| Network Latency | Configurable (default 60s) | 30 days |
| Topology | On-demand / Event-driven | 90 days |

### B. Supported Card Types

| Card Type | Library | Features |
|-----------|---------|----------|
| Gauge | D3.js | Circular/linear, thresholds, animations |
| Chart | Apache ECharts | Line, bar, area, scatter, real-time streaming |
| Metric | Custom | Large number, sparkline, trend indicator |
| Table | TanStack Table | Sortable, filterable, virtual scrolling |
| Topology | Cytoscape.js | Force-directed, hierarchical, interactive |
| Heatmap | D3.js | Calendar, grid, density maps |
| Log Stream | React Virtuoso | Real-time tail, filtering, highlighting |
| Command | Xterm.js | Interactive terminal, output streaming |
| Custom HTML | iframe/sandbox | User-defined content |

### C. Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile Safari (iOS 14+)
- Chrome Android (90+)

---

**Document End**

*This architecture document provides the complete blueprint for implementing NetDash v2.0 as a production-ready network and system control center.*
