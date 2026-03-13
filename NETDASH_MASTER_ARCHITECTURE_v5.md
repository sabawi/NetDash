# NetDash Master Architecture v5
## Complete High & Low Level Design Document

**Version:** 5.0  
**Date:** 2024  
**Status:** Production Ready Architecture  

---

## Executive Summary

NetDash is re-architected as a **modular, real-time Network and System Control Center** with a focus on:
- **Dynamic Dashboard Creation**: Drag-and-drop card-based screen builder
- **Real-time Metrics**: WebSocket-powered live gauges and charts
- **Extensible Architecture**: Plugin-based metric collectors
- **Security-First Design**: Role-based access with audit logging

---

## PART I: HIGH LEVEL DESIGN (HLD)

### 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │   Dashboard   │  │  Screen      │  │   Admin      │  │   Visualization  │ │
│  │   Viewer      │  │  Builder     │  │   Panel      │  │   Engine         │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘ │
└─────────┼─────────────────┼─────────────────┼──────────────────┼───────────┘
          │                 │                 │                  │
          └─────────────────┴─────────────────┴──────────────────┘
                                   │
                              WebSocket Bus
                                   │
┌─────────────────────────────────────────────────────────────────────────────┐
│                            APPLICATION LAYER                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                      API Gateway (FastAPI)                              ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    ││
│  │  │  Auth    │ │ Dashboard│ │  Metric  │ │ Network  │ │  System  │    ││
│  │  │  Service │ │  Service │ │  Service │ │  Service │ │  Service │    ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MESSAGING LAYER                                  │
│  ┌──────────────┐    ┌──────────────────────────────┐    ┌─────────────┐ │
│  │  Redis Pub   │◄──►│     Message Queue (Celery)     │◄──►│  Scheduler  │ │
│  │  /Sub        │    │     Background Jobs            │    │  (Cron)     │ │
│  └──────────────┘    └──────────────────────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │   PostgreSQL │  │   InfluxDB   │  │    Redis     │  │  Time-Series   │ │
│  │  (Metadata)  │  │  (Metrics)   │  │   (Cache)    │  │    Storage     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COLLECTOR LAYER                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │   System     │  │   Network    │  │   Process    │  │   Custom       │ │
│  │   Collector  │  │   Collector  │  │   Monitor    │  │   Plugins      │ │
│  │  (ps, iostat)│  │ (ping, nmap) │  │  (Docker,K8s)│  │  (User-defined)│ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Component Architecture

#### 2.1 Frontend Architecture (SPA - Single Page Application)

```
┌─────────────────────────────────────────────────────────────────┐
│                     NetDash Frontend                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Core Framework                            │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌────────────────────────┐ │ │
│  │  │   React 18  │ │  Redux      │ │   React Router v6      │ │ │
│  │  │  (UI Lib)   │ │  (State)    │ │   (Navigation)         │ │ │
│  │  └─────────────┘ └─────────────┘ └────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                 Visualization Layer                        │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌────────────────────────┐ │ │
│  │  │   D3.js     │ │  Chart.js   │ │   Gauge.js             │ │ │
│  │  │ (Topology)  │ │  (Charts)   │ │   (Gauges)             │ │ │
│  │  └─────────────┘ └─────────────┘ └────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Feature Modules                           │ │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐ │ │
│  │  │ Dashboard │ │  Screen   │ │  Builder  │ │  Network    │ │ │
│  │  │  Module   │ │  Module   │ │  Module   │ │  Module     │ │ │
│  │  └───────────┘ └───────────┘ └───────────┘ └─────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  Service Layer                               │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌────────────────────────┐ │ │
│  │  │   WebSocket │ │  REST API   │ │   State Management     │ │ │
│  │  │   Client    │ │   Client    │ │   (Redux Toolkit)      │ │ │
│  │  └─────────────┘ └─────────────┘ └────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2 Backend Architecture (Microservices-Ready)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        API Gateway                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │   Rate       │  │    JWT       │  │    Request Routing       │   │
│  │   Limiting   │  │   Auth       │  │    & Load Balancing      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
    │            │            │            │            │
    ▼            ▼            ▼            ▼            ▼
┌────────┐ ┌────────┐ ┌────────────┐ ┌────────┐ ┌────────────────┐
│  Auth  │ │Metrics │ │  Network   │ │ System │ │  Dashboard     │
│Service │ │Service │ │  Service   │ │Service │ │   Service      │
└────────┘ └────────┘ └────────────┘ └────────┘ └────────────────┘
```

### 3. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + TypeScript | UI Framework |
| **State** | Redux Toolkit + RTK Query | State Management |
| **Styling** | Tailwind CSS + Headless UI | Component Styling |
| **Charts** | Chart.js + D3.js + Gauge.js | Visualizations |
| **Backend** | FastAPI (Python 3.11+) | API Framework |
| **WebSocket** | Socket.IO | Real-time Communication |
| **Database** | PostgreSQL 15 | Relational Data |
| **Time-Series** | InfluxDB 2.x | Metrics Storage |
| **Cache** | Redis 7 | Session & Real-time Data |
| **Queue** | Celery + Redis | Background Jobs |
| **Container** | Docker + Docker Compose | Deployment |

---

## PART II: LOW LEVEL DESIGN (LLD)

### 4. Database Schema Design

#### 4.1 PostgreSQL Schema (Metadata & Configuration)

```sql
-- Users and Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'viewer', -- admin, editor, viewer
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Dashboard Screens
CREATE TABLE screens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    layout JSONB NOT NULL, -- Grid layout configuration
    refresh_interval INTEGER DEFAULT 30, -- seconds
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_public BOOLEAN DEFAULT false
);

-- Metric Cards
CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    screen_id UUID REFERENCES screens(id) ON DELETE CASCADE,
    card_type VARCHAR(50) NOT NULL, -- gauge, chart, table, text, topology
    title VARCHAR(100) NOT NULL,
    position JSONB NOT NULL, -- {x, y, w, h} for grid
    configuration JSONB NOT NULL, -- Card-specific config
    data_source JSONB NOT NULL, -- {type, endpoint, params}
    refresh_interval INTEGER, -- Override screen default
    alert_rules JSONB, -- Thresholds and notifications
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Network Hosts Discovery
CREATE TABLE hosts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ip_address INET NOT NULL,
    mac_address MACADDR,
    hostname VARCHAR(255),
    alias VARCHAR(100),
    os_fingerprint VARCHAR(100),
    is_monitored BOOLEAN DEFAULT true,
    discovery_method VARCHAR(50),
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- System Configuration
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, key)
);

-- Audit Log
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL, -- login, screen_create, card_update, etc.
    resource_type VARCHAR(50), -- screen, card, host, etc.
    resource_id UUID,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alert History
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID REFERENCES cards(id),
    severity VARCHAR(20) NOT NULL, -- info, warning, critical
    message TEXT NOT NULL,
    metric_value DECIMAL,
    threshold_value DECIMAL,
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_by UUID REFERENCES users(id),
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);
```

#### 4.2 InfluxDB Schema (Time-Series Metrics)

```
Measurement: system_metrics
├── Tags:
│   ├── host (string)
│   ├── metric_type (cpu, memory, disk, network, load)
│   └── instance (cpu0, cpu1, eth0, sda1, etc.)
└── Fields:
    ├── value (float)
    ├── percent (float)
    └── status (string)

Measurement: network_metrics
├── Tags:
│   ├── source_host (string)
│   ├── target_host (string)
│   ├── protocol (tcp, udp, icmp)
│   └── port (integer)
└── Fields:
    ├── latency_ms (float)
    ├── packet_loss (float)
    ├── bandwidth_bps (float)
    └── connection_count (integer)

Measurement: custom_metrics
├── Tags:
│   ├── source (string)
│   ├── metric_name (string)
│   └── unit (string)
└── Fields:
    └── value (float)
```

### 5. API Design

#### 5.1 REST API Endpoints

```yaml
openapi: 3.0.0
info:
  title: NetDash API
  version: 5.0.0

paths:
  # Authentication
  /api/v5/auth/login:
    post:
      summary: User login
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                username: {type: string}
                password: {type: string}
      responses:
        200:
          description: JWT token returned

  /api/v5/auth/refresh:
    post:
      summary: Refresh JWT token

  # Screens (Dashboards)
  /api/v5/screens:
    get:
      summary: List all screens
      parameters:
        - name: limit
          in: query
          schema: {type: integer, default: 20}
        - name: offset
          in: query
          schema: {type: integer, default: 0}
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  total: {type: integer}
                  screens:
                    type: array
                    items:
                      $ref: '#/components/schemas/Screen'

    post:
      summary: Create new screen
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ScreenInput'

  /api/v5/screens/{id}:
    get:
      summary: Get screen with cards
    put:
      summary: Update screen
    delete:
      summary: Delete screen

  # Cards
  /api/v5/screens/{screen_id}/cards:
    get:
      summary: Get cards for screen
    post:
      summary: Add card to screen

  /api/v5/cards/{id}:
    get: {summary: Get card details}
    put: {summary: Update card}
    delete: {summary: Delete card}
    patch: {summary: Update card position/layout}

  # Metrics
  /api/v5/metrics/current:
    get:
      summary: Get current metric values
      parameters:
        - name: types
          in: query
          schema: {type: string}  # comma-separated: cpu,memory,network
        - name: hosts
          in: query
          schema: {type: string}  # comma-separated host IDs

  /api/v5/metrics/history:
    get:
      summary: Get historical metrics
      parameters:
        - name: metric
          in: query
          required: true
          schema: {type: string}
        - name: start
          in: query
          required: true
          schema: {type: string, format: date-time}
        - name: end
          in: query
          schema: {type: string, format: date-time}
        - name: aggregation
          in: query
          schema: {type: string, enum: [raw, 1m, 5m, 1h]}

  # Network Operations
  /api/v5/network/discover:
    post:
      summary: Discover network hosts
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                subnet: {type: string, example: "192.168.1.0/24"}
                method: {type: string, enum: [ping, arp, nmap]}
                async: {type: boolean, default: true}

  /api/v5/network/hosts:
    get:
      summary: List discovered hosts
    delete:
      summary: Remove host

  /api/v5/network/scan:
    post:
      summary: Port scan target
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                target: {type: string}
                ports: {type: string, example: "1-1000,8080,8443"}
                scan_type: {type: string, enum: [syn, connect, udp]}

  /api/v5/network/ping:
    post:
      summary: Ping target
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                target: {type: string}
                count: {type: integer, default: 4}

  /api/v5/network/traceroute:
    post:
      summary: Traceroute to target
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                target: {type: string}
                max_hops: {type: integer, default: 30}

  # System Operations
  /api/v5/system/interfaces:
    get:
      summary: List network interfaces

  /api/v5/system/connections:
    get:
      summary: List active connections

  /api/v5/system/processes:
    get:
      summary: List system processes
      parameters:
        - name: sort_by
          in: query
          schema: {type: string, enum: [cpu, memory, pid]}

  /api/v5/system/command:
    post:
      summary: Execute system command (admin only)
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                command: {type: string}
                args: {type: array, items: {type: string}}
                timeout: {type: integer, default: 30}

components:
  schemas:
    Screen:
      type: object
      properties:
        id: {type: string, format: uuid}
        name: {type: string}
        description: {type: string}
        layout: {type: object}
        refresh_interval: {type: integer}
        created_by: {type: string}
        created_at: {type: string, format: date-time}
        cards_count: {type: integer}

    ScreenInput:
      type: object
      required: [name]
      properties:
        name: {type: string}
        description: {type: string}
        layout:
          type: object
          properties:
            columns: {type: integer, default: 12}
            row_height: {type: integer, default: 80}
        refresh_interval: {type: integer, default: 30}
        is_public: {type: boolean, default: false}
```

#### 5.2 WebSocket Events

```javascript
// Client -> Server Events
{
  "subscribe_screen": "screen_uuid",     // Subscribe to screen updates
  "unsubscribe_screen": "screen_uuid",   // Unsubscribe
  "execute_command": {                   // Execute and stream output
    "command_id": "uuid",
    "command": "ping",
    "args": ["-c", "4", "8.8.8.8"]
  },
  "cancel_job": "job_id"                 // Cancel running background job
}

// Server -> Client Events
{
  "metric_update": {                     // Real-time metric push
    "timestamp": "2024-01-15T10:30:00Z",
    "screen_id": "uuid",
    "card_id": "uuid",
    "metric": {
      "type": "cpu_usage",
      "value": 45.2,
      "unit": "%",
      "trend": "up|down|stable"
    }
  },
  "alert_triggered": {                   // Alert notification
    "alert_id": "uuid",
    "severity": "warning|critical",
    "message": "CPU usage above 90%",
    "card_id": "uuid",
    "screen_id": "uuid",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "command_output": {                    // Stream command output
    "command_id": "uuid",
    "output": "line of text",
    "is_complete": false,
    "exit_code": null  // Set when complete
  },
  "job_status": {                        // Background job update
    "job_id": "uuid",
    "status": "running|completed|failed",
    "progress": 75,  // percentage
    "result": {}     // Final result when completed
  },
  "host_discovered": {                   // New host found
    "host_id": "uuid",
    "ip_address": "192.168.1.100",
    "mac_address": "aa:bb:cc:dd:ee:ff",
    "hostname": "new-device.local"
  }
}
```

### 6. Frontend Component Design

#### 6.1 Component Hierarchy

```
App
├── Layout
│   ├── Sidebar
│   │   ├── NavigationMenu
│   │   └── ScreenList
│   ├── TopBar
│   │   ├── GlobalSearch
│   │   ├── NotificationCenter
│   │   └── UserMenu
│   └── MainContent
│
├── Views
│   ├── DashboardView
│   │   ├── ScreenCanvas (Grid Layout)
│   │   │   └── CardWrapper (Droppable)
│   │   │       └── CardComponents
│   │   │           ├── GaugeCard
│   │   │           ├── LineChartCard
│   │   │           ├── BarChartCard
│   │   │           ├── PieChartCard
│   │   │           ├── TableCard
│   │   │           ├── TopologyCard
│   │   │           ├── TextCard
│   │   │           └── CustomCard
│   │   ├── TimeRangeSelector
│   │   └── RefreshControls
│   │
│   ├── BuilderView
│   │   ├── BuilderCanvas (React-Grid-Layout)
│   │   ├── CardPalette (Draggable Cards)
│   │   ├── PropertyPanel
│   │   │   ├── DataSourceConfig
│   │   │   ├── VisualConfig
│   │   │   └── AlertConfig
│   │   └── Toolbar
│   │       ├── SaveButton
│   │       ├── PreviewToggle
│   │       └── LayoutPresets
│   │
│   ├── NetworkDiscoveryView
│   │   ├── DiscoveryToolbar
│   │   ├── HostsTable
│   │   ├── NetworkTopology (D3.js)
│   │   └── HostDetailModal
│   │
│   ├── SystemMonitorView
│   │   ├── ProcessTable
│   │   ├── ResourceUsageCharts
│   │   └── InterfaceStatus
│   │
│   └── AdminView
│       ├── UserManagement
│       ├── SystemSettings
│       └── AuditLogs
│
├── SharedComponents
│   ├── DataTable
│   ├── MetricCard
│   ├── ChartContainer
│   ├── GaugeComponent
│   ├── StatusBadge
│   ├── Modal
│   ├── FormInputs
│   └── LoadingSpinner
│
└── Hooks
    ├── useWebSocket
    ├── useMetrics
    ├── useScreen
    ├── useNetworkDiscovery
    └── useSystemCommands
```

#### 6.2 Card Component Interface

```typescript
// Base Card Interface
interface CardBase {
  id: string;
  screenId: string;
  type: 'gauge' | 'line_chart' | 'bar_chart' | 'pie_chart' | 'table' | 'topology' | 'text';
  title: string;
  position: {
    x: number;
    y: number;
    w: number;  // grid units (1-12)
    h: number;  // grid units
  };
  configuration: CardConfig;
  dataSource: DataSourceConfig;
  refreshInterval?: number;
  alertRules?: AlertRule[];
}

// Data Source Configuration
interface DataSourceConfig {
  type: 'system_metric' | 'network_metric' | 'custom_api' | 'command';
  endpoint: string;
  params: Record<string, any>;
  transform?: string;  // JavaScript function body for data transformation
}

// Card-specific Configurations
interface GaugeConfig {
  min: number;
  max: number;
  unit: string;
  thresholds: {
    warning: number;
    critical: number;
  };
  colors: {
    normal: string;
    warning: string;
    critical: string;
  };
}

interface ChartConfig {
  series: SeriesConfig[];
  xAxis: AxisConfig;
  yAxis: AxisConfig;
  legend: LegendConfig;
  tooltip: TooltipConfig;
  stacking?: boolean;
}

interface TableConfig {
  columns: ColumnConfig[];
  pagination: { enabled: boolean; pageSize: number };
  sorting: { enabled: boolean; defaultColumn?: string };
  filtering: { enabled: boolean };
}
```

### 7. Real-Time Data Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Data Collection Flow                             │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Collector  │    │   Parser     │    │   Enricher   │    │   Router     │
│   (Python)   │───►│   (Pydantic) │───►│   (Redis)    │───►│   (Socket.IO)│
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                  │
                    ┌──────────────────────────────────────────────┼────────┐
                    │                                              │        │
                    ▼                                              ▼        ▼
            ┌──────────────┐                              ┌──────────────┐ ┌──────────────┐
            │   InfluxDB   │                              │  WebSocket   │ │   Cache      │
            │   (Store)    │                              │  Broadcast   │ │   (TTL)      │
            └──────────────┘                              └──────────────┘ └──────────────┘

Collection Interval:
- System Metrics: 5 seconds
- Network Metrics: 10 seconds
- Process List: 30 seconds
- Discovery Scans: Configurable (default 1 hour)
```

### 8. Security Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Security Layers                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                      Authentication                              ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐  ││
│  │  │   JWT       │  │   Session   │  │   MFA (Optional)       │  ││
│  │  │   Tokens    │  │   Redis     │  │   TOTP                 │  ││
│  │  └─────────────┘  └─────────────┘  └────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────┘│
│                              │                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                      Authorization                               ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐  ││
│  │  │   RBAC      │  │   Resource  │  │   Audit Logging        │  ││
│  │  │   Roles:    │  │   Level     │  │   All Actions          │  ││
│  │  │   Admin,    │  │   Perms     │  │   Tracked              │  ││
│  │  │   Editor,   │  │             │  │                        │  ││
│  │  │   Viewer    │  │             │  │                        │  ││
│  │  └─────────────┘  └─────────────┘  └────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────┘│
│                              │                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    Input Validation                              ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐  ││
│  │  │   Pydantic  │  │   Command   │  │   SQL Injection        │  ││
│  │  │   Schemas   │  │   Sanitizer │  │   Prevention           │  ││
│  │  └─────────────┘  └─────────────┘  └────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────┘│
│                              │                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    Network Security                                ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐  ││
│  │  │   HTTPS     │  │   CORS      │  │   Rate Limiting        │  ││
│  │  │   TLS 1.3   │  │   Config    │  │   (100 req/min)        │  ││
│  │  └─────────────┘  └─────────────┘  └────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 9. Deployment Architecture

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Frontend
  netdash-ui:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    depends_on:
      - netdash-api

  # Backend API
  netdash-api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://netdash:secret@postgres:5432/netdash
      - REDIS_URL=redis://redis:6379
      - INFLUX_URL=http://influxdb:8086
    depends_on:
      - postgres
      - redis
      - influxdb

  # Background Workers
  netdash-worker:
    build: ./backend
    command: celery -A netdash.tasks worker --loglevel=info
    depends_on:
      - redis
      - postgres

  # Scheduler
  netdash-scheduler:
    build: ./backend
    command: celery -A netdash.tasks beat --loglevel=info
    depends_on:
      - redis

  # Databases
  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=netdash
      - POSTGRES_PASSWORD=secret
      - POSTGRES_DB=netdash

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  influxdb:
    image: influxdb:2.7
    volumes:
      - influxdb_data:/var/lib/influxdb2
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=netdash
      - DOCKER_INFLUXDB_INIT_PASSWORD=secret
      - DOCKER_INFLUXDB_INIT_ORG=netdash
      - DOCKER_INFLUXDB_INIT_BUCKET=metrics

volumes:
  postgres_data:
  redis_data:
  influxdb_data:
```

---

## PART III: UX/UI SPECIFICATIONS

### 10. Dashboard Design System

#### 10.1 Color Palette
```css
:root {
  /* Primary Colors */
  --primary-50: #e3f2fd;
  --primary-100: #bbdefb;
  --primary-500: #2196f3;
  --primary-700: #1976d2;
  --primary-900: #0d47a1;

  /* Semantic Colors */
  --success: #4caf50;
  --warning: #ff9800;
  --danger: #f44336;
  --info: #00bcd4;

  /* Status Colors */
  --status-online: #4caf50;
  --status-offline: #9e9e9e;
  --status-warning: #ff9800;
  --status-error: #f44336;

  /* Neutral */
  --bg-primary: #0a0e17;
  --bg-secondary: #111827;
  --bg-tertiary: #1f2937;
  --text-primary: #f9fafb;
  --text-secondary: #9ca3af;
  --border-color: #374151;
}
```

#### 10.2 Typography
```css
:root {
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-sans: 'Inter', system-ui, sans-serif;

  /* Sizes */
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;
  --text-3xl: 1.875rem;

  /* Weights */
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
}
```

#### 10.3 Component Specifications

**Gauge Card:**
- Size: 2x2 grid units minimum
- Colors: Gradient from primary-500 to danger based on value
- Animation: Smooth needle transition (300ms ease-out)
- Labels: Min/max values, current value, unit

**Line Chart:**
- Size: 4x2 grid units minimum
- Features: Zoom, pan, tooltip on hover
- Series: Up to 5 lines with toggleable visibility
- X-axis: Time-based, auto-scaling

**Topology Card:**
- Size: 4x3 grid units minimum
- Interaction: Zoom, pan, node selection
- Layout: Force-directed or hierarchical
- Status: Color-coded nodes by health

### 11. Screen Builder Interface

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  NetDash Builder                                    [Save] [Preview] [Exit]  │
├──────────────────┬────────────────────────────────────┬─────────────────────┤
│                  │                                    │                     │
│  CARD PALETTE    │        CANVAS (12-Column Grid)    │   PROPERTIES       │
│                  │                                    │                     │
│  ┌────────────┐  │  ┌────┬────┬────┬────┬────┬────┐   │  ┌───────────────┐ │
│  │ 📊 Gauge   │  │  │    │    │    │    │    │    │   │  │ Card: CPU      │ │
│  └────────────┘  │  │    │  Line Chart      │    │   │  │ Type: Gauge    │ │
│  ┌────────────┐  │  │    │    │    │    │    │    │   │  ├───────────────┤ │
│  │ 📈 Line    │  │  └────┴────┴────┴────┴────┴────┘   │  │ Data Source    │ │
│  └────────────┘  │  ┌────┬────┬────┬────┬────┬────┐   │  │ • Metric: CPU  │ │
│  ┌────────────┐  │  │Gauge│   │    │Gauge│   │    │   │  │ • Interval: 5s │ │
│  │ 📊 Bar     │  │  │    │   │    │    │   │    │   │  ├───────────────┤ │
│  └────────────┘  │  └────┴────┴────┴────┴────┴────┘   │  │ Visual         │ │
│  ┌────────────┐  │  ┌────┬────┬────┬────┬────┬────┐   │  │ • Min: 0       │ │
│  │ 🥧 Pie     │  │  │    │    │Topology│   │    │   │  │ • Max: 100     │ │
│  └────────────┘  │  │    │    │    │   │    │    │   │  │ • Unit: %      │ │
│  ┌────────────┐  │  └────┴────┴────┴────┴────┴────┘   │  ├───────────────┤ │
│  │ 📋 Table   │  │                                    │  │ Alerts         │ │
│  └────────────┘  │                                    │  │ • > 80% Warn   │ │
│  ┌────────────┐  │                                    │  │ • > 95% Critical│ │
│  │ 🌐 Topology│  │                                    │  └───────────────┘ │
│  └────────────┘  │                                    │                    │
│  ┌────────────┐  │                                    │                    │
│  │ 📝 Text    │  │                                    │                    │
│  └────────────┘  │                                    │                    │
│                  │                                    │                    │
└──────────────────┴────────────────────────────────────┴─────────────────────┘
```

### 12. Implementation Roadmap

#### Phase 1: Core Infrastructure (Weeks 1-2)
- [ ] Database setup (PostgreSQL + InfluxDB)
- [ ] FastAPI project structure
- [ ] Authentication system
- [ ] Basic WebSocket setup

#### Phase 2: Data Collection (Weeks 3-4)
- [ ] System metrics collectors
- [ ] Network discovery implementation
- [ ] Background job system (Celery)
- [ ] Time-series data pipeline

#### Phase 3: Frontend Foundation (Weeks 5-6)
- [ ] React project setup with TypeScript
- [ ] Component library foundation
- [ ] State management (Redux)
- [ ] WebSocket client integration

#### Phase 4: Dashboard System (Weeks 7-8)
- [ ] Screen builder UI
- [ ] Card components (Gauge, Chart, Table)
- [ ] Grid layout system
- [ ] Real-time updates

#### Phase 5: Advanced Features (Weeks 9-10)
- [ ] Network topology visualization
- [ ] Alert system
- [ ] User management
- [ ] Export/Import functionality

#### Phase 6: Polish & Deploy (Weeks 11-12)
- [ ] UI/UX refinements
- [ ] Performance optimization
- [ ] Security audit
- [ ] Documentation
- [ ] Docker deployment

---

## Appendices

### A. Directory Structure
```
netdash/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v5/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── screens.py
│   │   │   │   │   ├── cards.py
│   │   │   │   │   ├── metrics.py
│   │   │   │   │   ├── network.py
│   │   │   │   │   └── system.py
│   │   │   │   └── deps.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── events.py
│   │   ├── collectors/
│   │   │   ├── system.py
│   │   │   ├── network.py
│   │   │   └── base.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── screen.py
│   │   │   └── metric.py
│   │   ├── services/
│   │   │   ├── screen_service.py
│   │   │   ├── metric_service.py
│   │   │   └── network_service.py
│   │   ├── tasks/
│   │   │   └── celery_tasks.py
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── cards/
│   │   │   ├── layout/
│   │   │   └── shared/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── dashboard/
│   │   │   ├── builder/
│   │   │   └── network/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── store/
│   │   ├── types/
│   │   └── App.tsx
│   ├── public/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

### B. API Response Examples

**Screen with Cards:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Production Dashboard",
  "description": "Main production system monitoring",
  "layout": {
    "columns": 12,
    "row_height": 80
  },
  "refresh_interval": 10,
  "cards": [
    {
      "id": "card-001",
      "type": "gauge",
      "title": "CPU Usage",
      "position": {"x": 0, "y": 0, "w": 3, "h": 3},
      "configuration": {
        "min": 0,
        "max": 100,
        "unit": "%",
        "thresholds": {"warning": 80, "critical": 95}
      },
      "data_source": {
        "type": "system_metric",
        "endpoint": "/api/v5/metrics/current",
        "params": {"metric": "cpu_percent"}
      }
    },
    {
      "id": "card-002",
      "type": "line_chart",
      "title": "Network Traffic",
      "position": {"x": 3, "y": 0, "w": 6, "h": 3},
      "configuration": {
        "series": [
          {"name": "RX", "color": "#4caf50"},
          {"name": "TX", "color": "#2196f3"}
        ]
      },
      "data_source": {
        "type": "network_metric",
        "endpoint": "/api/v5/metrics/history",
        "params": {"metric": "interface_bytes", "interface": "eth0"}
      }
    }
  ]
}
```

---

**END OF DOCUMENT**

This architecture provides a complete foundation for building NetDash as a professional-grade network and system monitoring dashboard with dynamic card-based interfaces, real-time metrics, and extensible design.
