# NetDash - Full System Control Center
## High-Level & Low-Level Design Specification

---

## 1. EXECUTIVE SUMMARY

NetDash is re-architected from a simple network scanner into a comprehensive System Control Center providing real-time monitoring, dynamic visualization, and system/network tuning capabilities through customizable dashboard screens.

### Key Features
- **Dynamic Dashboard Engine**: Real-time gauges, charts, and metric cards
- **Screen Builder**: Drag-and-drop interface for creating custom monitoring views
- **Universal Metrics Collection**: CPU, Memory, Disk, Network, Process, Service metrics
- **Network Command Integration**: Built-in tools for network discovery and tuning
- **Alerting & Thresholds**: Configurable alerts with visual indicators
- **Multi-source Data**: System commands, /proc filesystem, sysstat, SNMP, agents

---

## 2. HIGH-LEVEL ARCHITECTURE

### 2.1 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐    │
│  │  React/Web  │  │   Screen    │  │    Dashboard Engine     │    │
│  │   Frontend  │  │   Builder   │  │  (Gauges/Charts/Cards)  │    │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘    │
└────────────────────────┬──────────────────────────────────────────┘
                         │ WebSocket/REST API
┌────────────────────────▼──────────────────────────────────────────┐
│                      API GATEWAY LAYER                             │
│         (FastAPI + Socket.IO for real-time communication)          │
└────────────────────────┬──────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼─────┐  ┌──────▼──────┐  ┌────▼──────────┐
│   METRICS    │  │   NETWORK   │  │    SYSTEM     │
│   ENGINE     │  │   ENGINE    │  │    TUNING     │
│              │  │             │  │    ENGINE     │
└────────┬─────┘  └──────┬──────┘  └────┬──────────┘
         │               │               │
┌────────▼───────────────▼───────────────▼────────────────────────┐
│                    DATA COLLECTION LAYER                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │  System  │ │  /proc   │ │  iostat  │ │  ethtool │ │  nmap   │ │
│  │ Commands │ │  Parser  │ │  vmstat  │ │  ss/net  │ │  ping   │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Architectural Patterns

1. **Micro-frontend Architecture**: Modular dashboard components
2. **Event-Driven Communication**: WebSocket for real-time updates
3. **Plugin System**: Extensible metric collectors
4. **Time-Series Storage**: Ring buffer for historical data
5. **Command Pattern**: System tuning via abstracted command interface

### 2.3 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| Dashboard Engine | Render gauges, charts, cards; manage layouts |
| Screen Builder | UI for creating/customizing screens |
| Metrics Engine | Collect, aggregate, store system metrics |
| Network Engine | Execute network commands, parse output |
| Tuning Engine | Safe execution of tuning commands |
| Alert Manager | Evaluate thresholds, trigger notifications |

---

## 3. LOW-LEVEL DESIGN

### 3.1 Data Models

#### Screen Configuration
```json
{
  "screen_id": "uuid",
  "name": "Production Servers",
  "layout": "grid",
  "columns": 3,
  "refresh_rate": 5,
  "cards": [
    {
      "card_id": "uuid",
      "type": "gauge|chart|metric|table|sparkline",
      "position": {"x": 0, "y": 0, "w": 1, "h": 1},
      "data_source": {
        "category": "cpu|memory|disk|network|process|custom",
        "metric": "usage|temperature|io|packets",
        "aggregation": "avg|max|min|sum",
        "time_range": "1m|5m|1h|24h"
      },
      "visual": {
        "title": "CPU Usage",
        "color_scheme": "blue|red|green|custom",
        "thresholds": {"warning": 70, "critical": 90},
        "unit": "percent|bytes|packets"
      }
    }
  ]
}
```

#### Metric Data Point
```json
{
  "timestamp": "ISO8601",
  "host": "hostname",
  "category": "system|network|disk|process",
  "metric_name": "cpu_usage",
  "value": 45.2,
  "unit": "percent",
  "tags": {"core": "0", "type": "user"},
  "ttl": 86400
}
```

#### Network Command
```json
{
  "command_id": "ping_host",
  "display_name": "Ping Host",
  "executable": "ping",
  "args": ["-c", "4", "{target}"],
  "params": [
    {"name": "target", "type": "ip|hostname", "required": true},
    {"name": "count", "type": "int", "default": 4}
  ],
  "parser": "ping_parser",
  "privilege": "user|sudo",
  "timeout": 30
}
```

### 3.2 API Specification

#### REST Endpoints

```
GET    /api/v1/screens              # List all screens
POST   /api/v1/screens              # Create new screen
GET    /api/v1/screens/{id}         # Get screen config
PUT    /api/v1/screens/{id}         # Update screen
DELETE /api/v1/screens/{id}         # Delete screen

GET    /api/v1/metrics              # Query metrics (time range, aggregation)
GET    /api/v1/metrics/categories   # Available metric categories
GET    /api/v1/metrics/{category}   # Metrics in category

POST   /api/v1/commands/execute    # Execute network/system command
GET    /api/v1/commands/history     # Command execution history
GET    /api/v1/commands/templates   # Available command templates

POST   /api/v1/tuning              # Apply system tuning
GET    /api/v1/tuning/presets      # Available tuning presets
GET    /api/v1/tuning/status       # Current tuning status
```

#### WebSocket Events

```javascript
// Client -> Server
'subscribe_metrics': {categories: ['cpu', 'memory'], interval: 5}
'unsubscribe_metrics': {categories: ['cpu']}
'execute_command': {command_id: 'ping', params: {target: '8.8.8.8'}}
'update_card': {screen_id: 'xxx', card_id: 'yyy', config: {...}}

// Server -> Client
'metrics_update': {timestamp, category, metrics: [{name, value, unit}]}
'command_output': {command_id, stdout, stderr, status, progress}
'alert_triggered': {alert_id, severity, message, metric, threshold}
'system_notification': {type, message, timestamp}
```

### 3.3 Module Specifications

#### 3.3.1 Metrics Collector Service
```python
class MetricsCollector:
    - collectors: Dict[str, BaseCollector]
    - buffer: RingBuffer[MetricPoint]
    - subscribers: List[WebSocket]
    
    + register_collector(category, collector)
    + start_collection(interval)
    + stop_collection()
    + get_metrics(category, time_range, aggregation)
    + subscribe(ws, categories)
    
class BaseCollector(ABC):
    + collect() -> List[MetricPoint]
    + get_capabilities() -> List[str]
    
class CPUCollector(BaseCollector):
    - sources: [/proc/stat, /proc/cpuinfo, psutil]
    + collect(): CPU usage per core, frequency, temperature, load avg
    
class MemoryCollector(BaseCollector):
    - sources: [/proc/meminfo, /proc/slabinfo]
    + collect(): Total, used, free, buffers, cached, swap
    
class DiskCollector(BaseCollector):
    - sources: [/proc/diskstats, iostat, df]
    + collect(): I/O ops, throughput, latency, space usage
    
class NetworkCollector(BaseCollector):
    - sources: [/proc/net/dev, ss, ethtool, ifconfig]
    + collect(): RX/TX bytes, packets, errors, connections, interface stats
    
class ProcessCollector(BaseCollector):
    - sources: [/proc/[pid]/stat, ps, top]
    + collect(): Top processes by CPU/MEM, process tree, thread count
```

#### 3.3.2 Dashboard Card System
```javascript
class CardEngine {
    registry: Map<string, CardRenderer>
    
    register(type, renderer)
    render(card_config, container)
    update(card_id, data)
    destroy(card_id)
}

interface CardRenderer {
    render(config, container): HTMLElement
    update(element, data)
    resize(element, width, height)
    destroy(element)
}

class GaugeRenderer implements CardRenderer {
    // Circular/semicircular gauge with needle
    // Uses D3.js or Chart.js
}

class LineChartRenderer implements CardRenderer {
    // Time-series line chart
    // Real-time updates with sliding window
}

class BarChartRenderer implements CardRenderer {
    // Comparative bar charts
}

class MetricCardRenderer implements CardRenderer {
    // Big number display with trend indicator
}

class TableRenderer implements CardRenderer {
    // Sortable, filterable data tables
}

class SparklineRenderer implements CardRenderer {
    // Mini inline charts
}

class TopologyRenderer implements CardRenderer {
    // Network topology visualization
    // Force-directed graph using D3
}
```

#### 3.3.3 Screen Builder
```javascript
class ScreenBuilder {
    canvas: HTMLElement
    grid: GridStack | MuuriGrid
    toolbar: Toolbar
    propertyPanel: PropertyPanel
    
    init()
    addCard(type, position)
    removeCard(card_id)
    moveCard(card_id, new_position)
    resizeCard(card_id, new_size)
    configureCard(card_id, properties)
    exportConfig(): ScreenConfig
    importConfig(config)
    previewMode()
    editMode()
}

// Drag and drop from component palette
// Grid-based layout system (responsive)
// Real-time preview while editing
```

### 3.4 Database Schema

#### Time-Series Metrics (InfluxDB/TimescaleDB style)
```sql
-- Metric values table (time-series optimized)
CREATE TABLE metrics (
    time TIMESTAMPTZ NOT NULL,
    host TEXT NOT NULL,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    value DOUBLE PRECISION,
    tags JSONB,
    PRIMARY KEY (time, host, category, name)
);

CREATE INDEX idx_metrics_time ON metrics (time DESC);
CREATE INDEX idx_metrics_category ON metrics (category, name);
CREATE INDEX idx_metrics_host ON metrics (host);

-- Aggregated rollups for fast querying
CREATE MATERIALIZED VIEW metrics_5min AS
SELECT 
    time_bucket('5 minutes', time) as bucket,
    host, category, name,
    avg(value) as avg_val,
    max(value) as max_val,
    min(value) as min_val
FROM metrics
GROUP BY bucket, host, category, name;

-- Screen configurations
CREATE TABLE screens (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    config JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Command execution history
CREATE TABLE command_history (
    id UUID PRIMARY KEY,
    command TEXT NOT NULL,
    params JSONB,
    stdout TEXT,
    stderr TEXT,
    exit_code INTEGER,
    execution_time INTERVAL,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. UX/UI SPECIFICATIONS

### 4.1 Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  NetDash              [Home] [Screens▼] [Tools▼] [Settings] [?] │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  SCREEN SELECTOR  │  ADD CARD  │  EDIT MODE  │  REFRESH   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌──────────┐ ┌──────────────────────────┐ ┌──────────┐         │
│  │  ┌────┐  │ │  ╭────────────────────╮  │ │  ┌────┐  │         │
│  │  │ 75%│  │ │  │  ▲               ▲ │  │ │  │TOP │  │         │
│  │  │CPU │  │ │  │ ▲                ▲ │  │ │  │PROC│  │         │
│  │  │ 🔥 │  │ │  │    LINE CHART       │  │ │  │    │  │         │
│  │  └────┘  │ │  ╰────────────────────╯  │ │  └────┘  │         │
│  │ GAUGE    │ │    NETWORK TRAFFIC       │ │  TABLE   │         │
│  └──────────┘ └──────────────────────────┘ └──────────┘         │
│                                                                  │
│  ┌──────────────────┐ ┌──────────┐ ┌──────────────────┐       │
│  │  SPARKLINE ROW   │ │  BIG     │ │  BAR CHART       │       │
│  │  ▁▂▃▅▆▇█▇▆▅▃▂▁  │ │  NUMBER  │ │  ▓▓▓▓▓▓▓░░░     │       │
│  └──────────────────┘ │  2.4GB   │ └──────────────────┘       │
│                       └──────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Card Types Specification

#### Gauge Card
- **Types**: Circular, Semicircular, Linear bar
- **Features**: 
  - Color zones (green/yellow/red)
  - Needle animation
  - Digital readout in center
  - Min/max markers
  - Configurable ticks

#### Chart Card
- **Types**: Line, Area, Bar, Pie, Donut
- **Features**:
  - Multiple series overlay
  - Zoom/pan on historical data
  - Real-time streaming updates
  - Legend with toggle
  - Tooltip on hover
  - Y-axis auto-scaling

#### Metric Card
- **Display**: Large numeric value
- **Features**:
  - Trend indicator (↑↓)
  - Percentage change
  - Sparkline background
  - Color coding by threshold
  - Subtext for context

#### Table Card
- **Features**:
  - Sortable columns
  - Filter/search
  - Pagination
  - Row selection
  - Color-coded cells
  - Live updates

#### Topology Card
- **Display**: Force-directed graph
- **Features**:
  - Nodes: hosts, switches, routers
  - Edges: connections with status
  - Zoom/pan
  - Node details on click
  - Status coloring

### 4.3 Screen Builder Interface

```
┌─────────────────────────────────────────────────────────────────┐
│  SCREEN BUILDER                                    [Save] [X]  │
├──────────────────┬─────────────────────────────┬────────────────┤
│                  │                             │                │
│  COMPONENTS      │      CANVAS (Grid)          │  PROPERTIES    │
│  ═══════════     │                             │  ═══════════   │
│                  │  ┌─────┐ ┌─────────┐        │                │
│  □ Gauge         │  │     │ │         │        │  Title: [____] │
│  □ Line Chart    │  │  A  │ │    B    │        │                │
│  □ Bar Chart     │  │     │ │         │        │  Data Source:  │
│  □ Pie Chart     │  └─────┘ └─────────┘        │  [CPU ▼]       │
│  □ Metric        │                             │                │
│  □ Table         │  ┌─────────────────┐        │  Metric:       │
│  □ Sparkline     │  │                 │        │  [Usage ▼]     │
│  □ Topology      │  │        C        │        │                │
│  □ Custom        │  │                 │        │  Refresh:      │
│                  │  └─────────────────┘        │  [5s ▼]        │
│  [Drag to add]   │                             │                │
│                  │                             │  Thresholds:   │
│  LAYOUT          │  Grid: 3 cols x 2 rows      │  Warning: [70] │
│  ════════        │                             │  Critical:[90] │
│                  │  [+ Add Row] [- Remove]     │                │
│  [ ] Snap to     │                             │  Color: [🔵]   │
│      grid        │                             │                │
│                  │                             │  [Apply]       │
│  [ ] Auto-       │                             │                │
│      refresh     │                             │                │
│                  │                             │                │
└──────────────────┴─────────────────────────────┴────────────────┘
```

### 4.4 Color Scheme & Theming

```css
:root {
  /* Primary Colors */
  --primary: #2563eb;
  --primary-dark: #1d4ed8;
  --primary-light: #60a5fa;
  
  /* Status Colors */
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --info: #3b82f6;
  
  /* Neutral */
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-card: #334155;
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --border: #475569;
  
  /* Gauge Gradients */
  --gauge-safe: linear-gradient(90deg, #10b981, #3b82f6);
  --gauge-warning: linear-gradient(90deg, #f59e0b, #f97316);
  --gauge-danger: linear-gradient(90deg, #ef4444, #dc2626);
}
```

---

## 5. IMPLEMENTATION ROADMAP

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Set up FastAPI backend with WebSocket support
- [ ] Implement metrics collection service
- [ ] Create database schema and time-series storage
- [ ] Build API endpoints for screens and metrics

### Phase 2: Dashboard Engine (Week 3-4)
- [ ] Implement card rendering system
- [ ] Build gauge components (D3.js)
- [ ] Build chart components (Chart.js/ApexCharts)
- [ ] Create metric card and table components
- [ ] Implement real-time data streaming

### Phase 3: Screen Builder (Week 5-6)
- [ ] Grid layout system
- [ ] Drag-and-drop functionality
- [ ] Component palette
- [ ] Property panel
- [ ] Screen persistence

### Phase 4: Network Tools (Week 7)
- [ ] Command execution framework
- [ ] Network discovery (nmap, ping, arp)
- [ ] Connection monitoring
- [ ] Port scanning
- [ ] DNS tools integration

### Phase 5: System Tuning (Week 8)
- [ ] Safe command execution
- [ ] Tuning presets
- [ ] Parameter validation
- [ ] Rollback mechanism
- [ ] Audit logging

### Phase 6: Polish (Week 9)
- [ ] Dark/light themes
- [ ] Mobile responsiveness
- [ ] Performance optimization
- [ ] Documentation

---

## 6. TECHNOLOGY STACK

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript |
| State Management | Zustand |
| Charts | D3.js + ApexCharts |
| UI Components | Tailwind CSS + Headless UI |
| Grid Layout | React-Grid-Layout |
| Backend | FastAPI + Python 3.11 |
| WebSocket | Socket.IO |
| Database | TimescaleDB (PostgreSQL) |
| Caching | Redis |
| Process Management | Celery (for background tasks) |
| System Monitoring | psutil + custom parsers |

---

## 7. SECURITY CONSIDERATIONS

1. **Command Whitelisting**: Only pre-approved commands can be executed
2. **Sandboxing**: Network commands run in restricted environment
3. **Privilege Separation**: Read-only vs read-write operations
4. **Input Sanitization**: Strict validation of all user inputs
5. **Audit Logging**: All commands logged with user and timestamp
6. **Rate Limiting**: Prevent abuse of expensive operations

---

*Document Version: 2.0*
*Last Updated: 2024*
*Author: Agent-oo1*
