# NetDash System Control Center - Complete Re-Architecture v3.0

## Executive Summary

NetDash is re-architected as a **modular, real-time System & Network Control Center** featuring:
- **Dynamic Dashboard Builder**: Drag-and-drop card-based screen creation
- **Real-time Metrics Engine**: WebSocket-powered live data streaming
- **Advanced Visualization**: Gauge widgets, charts, heatmaps, and topology maps
- **Bi-directional Control**: Monitor AND configure system/network settings
- **Plugin Architecture**: Extensible metric collectors and control modules

---

## 1. HIGH-LEVEL ARCHITECTURE

### 1.1 Architectural Pattern: Event-Driven Microservices

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │  Dashboard   │  │ Screen       │  │   Metric     │  │  Control        │ │
│  │  Builder UI  │  │ Renderer     │  │   Cards      │  │  Panels         │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘ │
│         └──────────────────┴─────────────────┴──────────────────┘          │
│                              WebSocket/REST                                  │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────────┐
│                         API GATEWAY (FastAPI/Flask)                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │
│  │  Auth/JWT   │ │ Rate Limit  │ │   Routing   │ │   WebSocket Mgr       │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘  │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────────┐
│                      CORE SERVICES (Python Async)                           │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────────┐  │
│  │ Metrics Engine  │ │   Job Runner    │ │     Configuration Manager     │  │
│  │   (Celery)      │ │  (AsyncIO)      │ │        (Pydantic Models)       │  │
│  └────────┬────────┘ └────────┬────────┘ └─────────────────┬───────────────┘  │
│           │                   │                            │                  │
│  ┌────────▼────────┐ ┌────────▼────────┐ ┌────────────────▼───────────────┐  │
│  │ Alert Engine    │ │ Topology Mapper │ │      Plugin Registry           │  │
│  │ (Rule-based)    │ │  (NetworkX)     │ │   (Dynamic Loading)            │  │
│  └─────────────────┘ └─────────────────┘ └────────────────────────────────┘  │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────────┐
│                      DATA COLLECTORS (Plugins)                              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐  │
│  │ System     │ │ Network    │ │  Process   │ │   Disk     │ │  Custom  │  │
│  │ Collector  │ │ Collector  │ │  Monitor   │ │  I/O       │ │  Plugins │  │
│  │ (psutil)   │ │ (ip/ss/nm) │ │  (procfs)  │ │ (iostat)   │ │  (API)   │  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  Time-Series │  │   Screen     │  │   Config     │  │    Session      │  │
│  │  DB (TSDB)   │  │   Store      │  │   Store      │  │    Cache        │  │
│  │ (InfluxDB)   │  │  (SQLite)    │  │  (YAML/JSON) │  │   (Redis)       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React/Vue3 + TypeScript | Dynamic UI, component-based |
| Visualization | D3.js + Chart.js + Canvas Gauges | Charts, gauges, topology |
| State | Zustand/Redux + WebSocket | Real-time state management |
| Backend | FastAPI (Python) | High-performance async API |
| Workers | Celery + Redis | Background job processing |
| Database | InfluxDB (metrics) + SQLite (metadata) | Time-series + relational |
| Real-time | WebSocket (python-socketio) | Live metric streaming |
| Container | Docker + Docker Compose | Deployment |

---

## 2. LOW-LEVEL DESIGN

### 2.1 Data Models

#### Screen (Dashboard) Model
```python
class Screen(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    layout: LayoutType = LayoutType.GRID  # GRID, FREE, TABS
    cards: List[Card] = []
    refresh_rate: int = 5  # seconds
    created_at: datetime
    updated_at: datetime
    permissions: List[str] = ["admin"]
    theme: ThemeConfig = ThemeConfig()

class LayoutType(str, Enum):
    GRID = "grid"      # Responsive grid layout
    FREE = "free"      # Absolute positioning
    TABS = "tabs"      # Tabbed interface
    SPLIT = "split"    # Resizable panes

class Card(BaseModel):
    id: str
    type: CardType
    position: Position  # x, y, w, h (grid) or absolute
    title: str
    data_source: DataSource
    visualization: VisualizationConfig
    actions: List[Action] = []
    thresholds: List[Threshold] = []
    
class CardType(str, Enum):
    # System Metrics
    CPU_GAUGE = "cpu_gauge"
    CPU_CHART = "cpu_chart"
    CPU_HEATMAP = "cpu_heatmap"
    MEMORY_GAUGE = "memory_gauge"
    MEMORY_CHART = "memory_chart"
    DISK_GAUGE = "disk_gauge"
    DISK_IO_CHART = "disk_io_chart"
    LOAD_CHART = "load_chart"
    
    # Network Metrics
    NETWORK_TRAFFIC = "network_traffic"
    NETWORK_GAUGE = "network_gauge"
    BANDWIDTH_CHART = "bandwidth_chart"
    CONNECTIONS_TABLE = "connections_table"
    INTERFACE_STATUS = "interface_status"
    
    # Visualization
    LINE_CHART = "line_chart"
    AREA_CHART = "area_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    GAUGE = "gauge"
    DIGITAL_DISPLAY = "digital_display"
    SPARKLINE = "sparkline"
    
    # Composite
    TOPOLOGY_MAP = "topology_map"
    WORLD_MAP = "world_map"
    LOG_VIEWER = "log_viewer"
    TERMINAL = "terminal"
    
    # Custom
    CUSTOM_HTML = "custom_html"
    IFRAME = "iframe"

class DataSource(BaseModel):
    type: DataSourceType
    metric: str           # e.g., "system.cpu.percent"
    parameters: Dict[str, Any] = {}
    aggregation: AggregationType = AggregationType.LATEST
    interval: int = 5     # seconds
    
class DataSourceType(str, Enum):
    SYSTEM = "system"           # psutil-based
    NETWORK = "network"         # ip/ss commands
    COMMAND = "command"         # Custom shell command
    API = "api"                 # HTTP endpoint
    SNMP = "snmp"               # SNMP query
    DATABASE = "database"       # SQL query
    MQTT = "mqtt"               # MQTT topic
    PROMETHEUS = "prometheus"   # Prometheus endpoint

class VisualizationConfig(BaseModel):
    chart_type: Optional[str] = None
    colors: List[str] = []
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    units: str = ""
    decimals: int = 2
    thresholds: List[Threshold] = []
    legend: bool = True
    grid: bool = True
    animation: bool = True

class Threshold(BaseModel):
    value: float
    color: str
    label: str
    severity: str  # info, warning, critical
    action: Optional[str] = None  # Alert, email, webhook

class Action(BaseModel):
    name: str
    type: ActionType
    command: Optional[str] = None
    endpoint: Optional[str] = None
    payload: Optional[Dict] = None
    confirmation: bool = False
    
class ActionType(str, Enum):
    BUTTON = "button"
    TOGGLE = "toggle"
    SLIDER = "slider"
    DROPDOWN = "dropdown"
    REMOTE_COMMAND = "remote_command"
    API_CALL = "api_call"
    NAVIGATE = "navigate"
```

### 2.2 Metric Collection Architecture

#### Metric Pipeline
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Source    │ -> │  Collector  │ -> │  Processor  │ -> │   Storage   │ -> │  Streaming  │
│             │    │             │    │             │    │             │    │             │
│ /proc,      │    │ Python      │    │ Transform   │    │ InfluxDB    │    │ WebSocket   │
│ ip command, │    │ Async       │    │ Aggregate   │    │ (hot)       │    │ Broadcast   │
│ psutil,     │    │ Scheduler   │    │ Filter      │    │             │    │             │
│ ss, iostat  │    │             │    │             │    │ SQLite      │    │             │
│             │    │             │    │             │    │ (cold)      │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

#### Metric Schema (InfluxDB Line Protocol)
```
system_cpu,host=server1,cpu=cpu0 usage_user=15.2,usage_system=4.1,usage_idle=78.5 1699900000
system_memory,host=server1 used_percent=45.2,available=8589934592,total=17179869184 1699900000
network_io,host=server1,interface=eth0 bytes_sent=1024000,bytes_recv=2048000,packets_sent=5000 1699900000
network_connections,host=server1,state=established count=42 1699900000
```

### 2.3 API Design

#### REST Endpoints

```yaml
# Screen Management
GET    /api/v1/screens                    # List all screens
POST   /api/v1/screens                    # Create new screen
GET    /api/v1/screens/{id}              # Get screen config
PUT    /api/v1/screens/{id}              # Update screen
DELETE /api/v1/screens/{id}              # Delete screen
POST   /api/v1/screens/{id}/clone       # Duplicate screen

# Card Management
GET    /api/v1/screens/{id}/cards        # List cards
POST   /api/v1/screens/{id}/cards        # Add card
PUT    /api/v1/screens/{id}/cards/{cid}  # Update card
DELETE /api/v1/screens/{id}/cards/{cid}  # Remove card
POST   /api/v1/cards/{id}/data          # Get card data

# Metrics
GET    /api/v1/metrics                   # List available metrics
GET    /api/v1/metrics/{name}/history    # Historical data
GET    /api/v1/metrics/{name}/current    # Current value
POST   /api/v1/metrics/query             # Custom query

# System Commands
POST   /api/v1/commands/ping             # Execute ping
POST   /api/v1/commands/traceroute       # Execute traceroute
POST   /api/v1/commands/nmap             # Execute nmap scan
POST   /api/v1/commands/custom           # Execute custom command
GET    /api/v1/commands/{job_id}/status  # Check job status

# Network Configuration
GET    /api/v1/network/interfaces        # List interfaces
PUT    /api/v1/network/interfaces/{if}   # Configure interface
POST   /api/v1/network/interfaces/{if}/up    # Bring up
POST   /api/v1/network/interfaces/{if}/down  # Bring down
GET    /api/v1/network/routes            # Routing table
POST   /api/v1/network/routes            # Add route
GET    /api/v1/network/firewall          # Firewall rules
PUT    /api/v1/network/firewall          # Update rules
GET    /api/v1/network/dns               # DNS settings
PUT    /api/v1/network/dns               # Update DNS

# WebSocket Events
WS     /ws/v1/stream                     # Real-time metrics stream
# Events: metric.update, alert.triggered, job.completed
```

#### WebSocket Protocol
```javascript
// Client -> Server
{
  "type": "subscribe",
  "channels": ["metrics.system.cpu", "metrics.network.eth0"],
  "screen_id": "screen_123"
}

// Server -> Client
{
  "type": "metric.update",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "metric": "system.cpu.percent",
    "value": 23.5,
    "labels": {"cpu": "total"},
    "screen_cards": ["card_1", "card_2"]
  }
}

{
  "type": "alert.triggered",
  "alert": {
    "id": "alert_001",
    "severity": "critical",
    "message": "CPU usage above 90%",
    "metric": "system.cpu.percent",
    "value": 95.2,
    "threshold": 90.0
  }
}
```

---

## 3. DYNAMIC DASHBOARD BUILDER UI

### 3.1 Builder Interface Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Header: NetDash Builder                              [Save] [Preview] [×]   │
├──────────────┬────────────────────────────────────────┬─────────────────────┤
│              │                                        │                     │
│  PALETTE     │         CANVAS (Grid/Free)             │   PROPERTIES        │
│              │                                        │                     │
│  ┌────────┐  │   ┌────────┐  ┌────────┐  ┌────────┐  │   ┌───────────────┐ │
│  │Search  │  │   │  CPU   │  │Memory  │  │Network │  │   │ Card: CPU_1   │ │
│  │Cards...│  │   │ Gauge  │  │ Chart  │  │Traffic │  │   ├───────────────┤ │
│  └────────┘  │   │        │  │        │  │        │  │   │ Title: [CPU   │ │
│              │   │  45%   │  │ [////] │  │ ~~~    │  │   │ Usage     ]   │ │
│  ──────────  │   │   ▲    │  │        │  │        │  │   │               │ │
│  CATEGORIES  │   └────────┘  └────────┘  └────────┘  │   │ Data Source:  │ │
│              │                                        │   │ [System     ▼] │ │
│  ▶ System    │   ┌────────────────────────┐  ┌─────┐  │   │ Metric:       │ │
│    □ Gauges  │   │    Network Topology    │  │Load │  │   │ [cpu.percent ▼]│ │
│    □ Charts  │   │         [MAP]          │  │ 2.5 │  │   │               │ │
│    □ Tables  │   │                        │  │     │  │   │ Refresh: [5s▼] │ │
│  ▶ Network   │   └────────────────────────┘  └─────┘  │   │               │ │
│    □ Traffic │                                        │   │ Thresholds:   │ │
│    □ Status  │   Grid: 12 columns × 8 rows            │   │ [+ Warning]   │ │
│    □ Scan    │                                        │   │ [+ Critical]  │ │
│  ▶ Custom    │                                        │   │               │ │
│    □ HTML    │   [+] Add Row    [−] Remove Row       │   │ Actions:      │ │
│    □ iFrame  │                                        │   │ [+ Button]    │ │
│              │                                        │   │ [+ Toggle]    │ │
└──────────────┴────────────────────────────────────────┴─────────────────────┘
```

### 3.2 Card Types Specification

#### 3.2.1 Gauge Card
```typescript
interface GaugeCardConfig {
  type: "gauge";
  min: number;           // Default: 0
  max: number;           // Default: 100
  value: number;         // Current value
  unit: string;        // "%", "MB/s", "°C"
  decimals: number;    // Decimal places
  
  // Visual styling
  startAngle: number;  // -90 to 90 (semi-circle)
  endAngle: number;    // 90 to 270
  colorStops: Array<{  // Gradient segments
    value: number;
    color: string;     // Hex color
  }>;
  
  // Thresholds
  thresholds: Array<{
    value: number;
    color: string;
    severity: "info" | "warning" | "critical";
  }>;
  
  // Animation
  animationDuration: number;
  needle: boolean;     // Show needle or fill
  digitalDisplay: boolean; // Show numeric value
}

// Example: CPU Gauge
{
  "type": "gauge",
  "min": 0,
  "max": 100,
  "unit": "%",
  "value": 45.2,
  "colorStops": [
    {"value": 0, "color": "#22c55e"},
    {"value": 60, "color": "#eab308"},
    {"value": 80, "color": "#ef4444"}
  ],
  "thresholds": [
    {"value": 80, "color": "#ef4444", "severity": "critical"},
    {"value": 60, "color": "#eab308", "severity": "warning"}
  ],
  "needle": true,
  "digitalDisplay": true
}
```

#### 3.2.2 Real-time Chart Card
```typescript
interface ChartCardConfig {
  type: "line_chart" | "area_chart" | "bar_chart";
  dataSource: DataSource;
  
  // Time window
  timeRange: "1m" | "5m" | "15m" | "1h" | "6h" | "24h" | "custom";
  refreshInterval: number; // seconds
  
  // Series configuration
  series: Array<{
    name: string;
    metric: string;
    color: string;
    aggregation: "avg" | "max" | "min" | "sum" | "last";
    lineStyle: "solid" | "dashed" | "dotted";
    fill: boolean;       // For area charts
    fillOpacity: number; // 0-1
  }>;
  
  // Y-axis
  yAxis: {
    min?: number;
    max?: number;
    label: string;
    unit: string;
  };
  
  // Interactivity
  zoom: boolean;
  tooltip: boolean;
  legend: boolean;
  crosshair: boolean;
}

// Example: Network Traffic Chart
{
  "type": "area_chart",
  "timeRange": "5m",
  "refreshInterval": 2,
  "series": [
    {
      "name": "Download",
      "metric": "network.eth0.bytes_recv",
      "color": "#3b82f6",
      "aggregation": "avg",
      "lineStyle": "solid",
      "fill": true,
      "fillOpacity": 0.3
    },
    {
      "name": "Upload",
      "metric": "network.eth0.bytes_sent",
      "color": "#22c55e",
      "aggregation": "avg",
      "lineStyle": "solid",
      "fill": true,
      "fillOpacity": 0.3
    }
  ],
  "yAxis": {
    "label": "Bandwidth",
    "unit": "MB/s"
  },
  "zoom": true,
  "tooltip": true
}
```

#### 3.2.3 Network Topology Card
```typescript
interface TopologyCardConfig {
  type: "topology_map";
  
  // Discovery
  autoDiscover: boolean;
  scanInterval: number; // seconds between scans
  
  // Display
  layout: "force" | "hierarchical" | "radial" | "circular";
  
  // Node styling
  nodeTypes: {
    router: { icon: string; color: string; size: number };
    switch: { icon: string; color: string; size: number };
    server: { icon: string; color: string; size: number };
    workstation: { icon: string; color: string; size: number };
    unknown: { icon: string; color: string; size: number };
  };
  
  // Interactions
  showLabels: boolean;
  showTraffic: boolean;   // Animate traffic on links
  trafficScale: number;   // Scale factor for line width
  
  // Actions
  onNodeClick: Action;
  onLinkClick: Action;
}
```

#### 3.2.4 System Control Card
```typescript
interface ControlCardConfig {
  type: "control_panel";
  
  // Service controls
  services: Array<{
    name: string;
    service_id: string;
    actions: ["start", "stop", "restart", "status"];
  }>;
  
  // Network controls
  interfaces: Array<{
    name: string;
    ifname: string;
    actions: ["up", "down", "configure"];
    showStats: boolean;
  }>;
  
  // Quick commands
  commands: Array<{
    label: string;
    command: string;
    confirmation: boolean;
    icon?: string;
  }>;
}
```

---

## 4. METRIC COLLECTOR SPECIFICATIONS

### 4.1 System Metrics Collector

```python
class SystemMetricsCollector:
    """
    Collects system metrics using psutil and /proc filesystem
    """
    
    METRICS = {
        # CPU Metrics
        "system.cpu.percent": {
            "type": "gauge",
            "unit": "%",
            "interval": 1,
            "source": lambda: psutil.cpu_percent(interval=1),
            "labels": ["cpu"]
        },
        "system.cpu.times.user": {
            "type": "counter",
            "unit": "seconds",
            "interval": 5,
            "source": "psutil.cpu_times().user"
        },
        "system.cpu.freq": {
            "type": "gauge",
            "unit": "MHz",
            "source": "psutil.cpu_freq().current"
        },
        "system.cpu.load_1": {
            "type": "gauge",
            "source": "os.getloadavg()[0]"
        },
        
        # Memory Metrics
        "system.memory.used": {
            "type": "gauge",
            "unit": "bytes",
            "source": "psutil.virtual_memory().used"
        },
        "system.memory.percent": {
            "type": "gauge",
            "unit": "%",
            "source": "psutil.virtual_memory().percent"
        },
        "system.memory.available": {
            "type": "gauge",
            "unit": "bytes",
            "source": "psutil.virtual_memory().available"
        },
        "system.swap.used": {
            "type": "gauge",
            "unit": "bytes",
            "source": "psutil.swap_memory().used"
        },
        
        # Disk Metrics
        "system.disk.used": {
            "type": "gauge",
            "unit": "bytes",
            "source": "psutil.disk_usage('/').used",
            "labels": ["mountpoint"]
        },
        "system.disk.percent": {
            "type": "gauge",
            "unit": "%",
            "source": "psutil.disk_usage('/').percent"
        },
        "system.disk.io.read_bytes": {
            "type": "counter",
            "unit": "bytes",
            "source": "psutil.disk_io_counters().read_bytes"
        },
        "system.disk.io.write_bytes": {
            "type": "counter",
            "unit": "bytes",
            "source": "psutil.disk_io_counters().write_bytes"
        },
        
        # Process Metrics
        "system.processes.count": {
            "type": "gauge",
            "source": "len(psutil.pids())"
        },
        "system.threads.count": {
            "type": "gauge",
            "source": "sum(p.num_threads() for p in psutil.process_iter())"
        },
        
        # Boot/Time
        "system.boot_time": {
            "type": "gauge",
            "source": "psutil.boot_time()"
        },
        "system.uptime": {
            "type": "gauge",
            "unit": "seconds",
            "source": "time.time() - psutil.boot_time()"
        }
    }
```

### 4.2 Network Metrics Collector

```python
class NetworkMetricsCollector:
    """
    Collects network metrics using ip, ss, and /proc/net
    """
    
    METRICS = {
        # Interface Metrics
        "network.interface.bytes_sent": {
            "type": "counter",
            "unit": "bytes",
            "source": "read_netdev",
            "labels": ["interface"],
            "interval": 5
        },
        "network.interface.bytes_recv": {
            "type": "counter",
            "unit": "bytes",
            "source": "read_netdev",
            "labels": ["interface"]
        },
        "network.interface.packets_sent": {
            "type": "counter",
            "source": "read_netdev",
            "labels": ["interface"]
        },
        "network.interface.packets_recv": {
            "type": "counter",
            "source": "read_netdev",
            "labels": ["interface"]
        },
        "network.interface.errors_in": {
            "type": "counter",
            "source": "read_netdev",
            "labels": ["interface"]
        },
        "network.interface.errors_out": {
            "type": "counter",
            "source": "read_netdev",
            "labels": ["interface"]
        },
        "network.interface.drops_in": {
            "type": "counter",
            "source": "read_netdev",
            "labels": ["interface"]
        },
        "network.interface.drops_out": {
            "type": "counter",
            "source": "read_netdev",
            "labels": ["interface"]
        },
        
        # Connection Metrics
        "network.connections.total": {
            "type": "gauge",
            "source": "len(psutil.net_connections())"
        },
        "network.connections.established": {
            "type": "gauge",
            "source": "count_by_state('ESTABLISHED')"
        },
        "network.connections.listening": {
            "type": "gauge",
            "source": "count_by_state('LISTEN')"
        },
        "network.connections.time_wait": {
            "type": "gauge",
            "source": "count_by_state('TIME_WAIT')"
        },
        "network.connections.close_wait": {
            "type": "gauge",
            "source": "count_by_state('CLOSE_WAIT')"
        },
        
        # Socket Statistics
        "network.sockets.tcp_in_use": {
            "type": "gauge",
            "source": "read_sockstat_tcp_inuse"
        },
        "network.sockets.udp_in_use": {
            "type": "gauge",
            "source": "read_sockstat_udp_inuse"
        },
        
        # Routing
        "network.routes.count": {
            "type": "gauge",
            "source": "len(read_routes())"
        },
        
        # ARP Table
        "network.arp.entries": {
            "type": "gauge",
            "source": "len(read_arp_table())"
        }
    }
    
    COMMANDS = {
        "ip_addr": "ip -j addr show",
        "ip_link": "ip -j link show",
        "ip_route": "ip -j route show",
        "ss_connections": "ss -tunap --json",
        "arp_table": "ip -j neigh show",
        "netstat_stats": "cat /proc/net/snmp",
        "netdev_stats": "cat /proc/net/dev"
    }
```

### 4.3 Command Executor Service

```python
class CommandExecutor:
    """
    Secure command execution with validation and sandboxing
    """
    
    ALLOWED_COMMANDS = {
        # Discovery
        "ping": {
            "cmd": "ping",
            "args": ["-c", "{count}", "-W", "{timeout}"],
            "params": {"count": "4", "timeout": "2"},
            "max_duration": 30,
            "requires_target": True
        },
        "fping": {
            "cmd": "fping",
            "args": ["-a", "-g", "{subnet}", "-t", "{timeout}"],
            "max_duration": 60,
            "requires_target": True
        },
        "traceroute": {
            "cmd": "traceroute",
            "args": ["-m", "{max_hops}", "-w", "{wait}"],
            "params": {"max_hops": "30", "wait": "5"},
            "max_duration": 60
        },
        "nmap_fast": {
            "cmd": "nmap",
            "args": ["-F", "-T4", "-sS"],
            "max_duration": 120,
            "requires_sudo": True
        },
        "nmap_full": {
            "cmd": "nmap",
            "args": ["-sS", "-sV", "-O", "-p-", "-T4"],
            "max_duration": 600,
            "requires_sudo": True
        },
        "arp_scan": {
            "cmd": "arp-scan",
            "args": ["--localnet", "-q"],
            "max_duration": 30,
            "requires_sudo": True
        },
        "dig": {
            "cmd": "dig",
            "args": ["+noall", "+answer"],
            "max_duration": 10
        },
        "whois": {
            "cmd": "whois",
            "args": [],
            "max_duration": 15
        },
        "nslookup": {
            "cmd": "nslookup",
            "args": [],
            "max_duration": 10
        },
        
        # System Info
        "lshw": {
            "cmd": "lshw",
            "args": ["-json"],
            "max_duration": 10,
            "requires_sudo": True
        },
        "dmidecode": {
            "cmd": "dmidecode",
            "args": [],
            "max_duration": 10,
            "requires_sudo": True
        },
        "lspci": {
            "cmd": "lspci",
            "args": ["-vmm"],
            "max_duration": 5
        },
        "lsusb": {
            "cmd": "lsusb",
            "args": [],
            "max_duration": 5
        },
        
        # Network Config
        "ethtool": {
            "cmd": "ethtool",
            "args": ["{interface}"],
            "max_duration": 5
        },
        "ethtool_stats": {
            "cmd": "ethtool",
            "args": ["-S", "{interface}"],
            "max_duration": 5
        },
        "tc_show": {
            "cmd": "tc",
            "args": ["qdisc", "show"],
            "max_duration": 5,
            "requires_sudo": True
        }
    }
    
    async def execute(self, command_key: str, target: str = None, 
                      params: dict = None, user: str = None) -> Job:
        """Execute a whitelisted command with validation"""
        # Validate command exists
        # Validate target (IP/hostname/domain)
        # Check user permissions
        # Create async job
        # Execute with timeout
        # Stream output via WebSocket
        pass
```

---

## 5. FRONTEND COMPONENT ARCHITECTURE

### 5.1 Component Hierarchy

```
App
├── LayoutManager
│   ├── Header (Screen selector, global controls)
│   ├── Sidebar (Collapsible palette)
│   └── MainContent
│       ├── DashboardBuilder (Edit mode)
│       │   ├── Canvas (Grid/Free layout)
│       │   │   └── CardContainer (Draggable, resizable)
│       │   │       └── CardWrapper
│       │   │           ├── CardHeader (Title, controls)
│       │   │           ├── CardContent
│       │   │           │   ├── GaugeCard
│       │   │           │   ├── ChartCard
│       │   │           │   ├── TableCard
│       │   │           │   ├── TopologyCard
│       │   │           │   ├── LogViewerCard
│       │   │           │   └── ControlCard
│       │   │           └── CardFooter (Last update, status)
│       │   └── PropertiesPanel (Selected card config)
│       └── DashboardViewer (Runtime mode)
│           └── CardContainer (Read-only)
├── MetricProvider (WebSocket context)
├── AlertManager (Toast notifications)
└── CommandTerminal (Global terminal overlay)
```

### 5.2 Gauge Component Implementation

```typescript
// React component with Canvas API
interface GaugeProps {
  value: number;
  min?: number;
  max?: number;
  unit?: string;
  thresholds?: Threshold[];
  animation?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const Gauge: React.FC<GaugeProps> = ({
  value,
  min = 0,
  max = 100,
  unit = '%',
  thresholds = [],
  animation = true,
  size = 'md'
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [currentValue, setCurrentValue] = useState(min);
  
  // Animate value changes
  useEffect(() => {
    if (!animation) {
      setCurrentValue(value);
      return;
    }
    
    const duration = 1000; // ms
    const start = currentValue;
    const delta = value - start;
    const startTime = Date.now();
    
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      setCurrentValue(start + delta * eased);
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    
    requestAnimationFrame(animate);
  }, [value]);
  
  // Draw gauge on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw background arc
    drawArc(ctx, canvas, min, max, '#e5e7eb', 0.3);
    
    // Draw colored segments based on thresholds
    thresholds.forEach((t, i) => {
      const nextThreshold = thresholds[i + 1]?.value || max;
      drawArc(ctx, canvas, t.value, nextThreshold, t.color, 0.8);
    });
    
    // Draw value arc
    const percentage = (currentValue - min) / (max - min);
    drawValueArc(ctx, canvas, percentage);
    
    // Draw needle
    drawNeedle(ctx, canvas, percentage);
    
    // Draw digital display
    drawDigitalDisplay(ctx, canvas, currentValue, unit);
  }, [currentValue]);
  
  return (
    <canvas
      ref={canvasRef}
      width={size === 'lg' ? 300 : size === 'md' ? 200 : 150}
      height={size === 'lg' ? 180 : size === 'md' ? 120 : 90}
      className="gauge-canvas"
    />
  );
};
```

### 5.3 Real-time Chart Component

```typescript
interface RealtimeChartProps {
  metrics: string[];        // Metric names to display
  timeWindow: number;       // Seconds of history
  refreshRate: number;      // Seconds between updates
  type: 'line' | 'area' | 'bar';
}

const RealtimeChart: React.FC<RealtimeChartProps> = ({
  metrics,
  timeWindow = 300, // 5 minutes
  refreshRate = 5,
  type = 'line'
}) => {
  const { subscribe, unsubscribe, getHistory } = useMetricStream();
  const [data, setData] = useState<DataPoint[]>([]);
  const chartRef = useRef<Chart | null>(null);
  
  useEffect(() => {
    // Subscribe to metrics
    const channels = metrics.map(m => `metrics.${m}`);
    const handleUpdate = (update: MetricUpdate) => {
      setData(prev => {
        const newData = [...prev, {
          time: update.timestamp,
          ...update.values
        }];
        // Keep only data within time window
        const cutoff = Date.now() - (timeWindow * 1000);
        return newData.filter(d => d.time > cutoff);
      });
    };
    
    channels.forEach(channel => subscribe(channel, handleUpdate));
    
    // Load initial history
    loadHistory();
    
    return () => {
      channels.forEach(channel => unsubscribe(channel, handleUpdate));
    };
  }, [metrics]);
  
  // Initialize/update Chart.js
  useEffect(() => {
    if (!chartRef.current) {
      chartRef.current = new Chart(canvasRef.current, {
        type: type === 'area' ? 'line' : type,
        data: { datasets: [] },
        options: {
          responsive: true,
          animation: false, // Disable for performance
          scales: {
            x: {
              type: 'realtime',
              realtime: {
                duration: timeWindow * 1000,
                refresh: refreshRate * 1000,
                delay: 0
              }
            },
            y: { beginAtZero: true }
          },
          plugins: {
            streaming: { frameRate: 30 }
          }
        }
      });
    }
    
    // Update datasets
    chartRef.current.data.datasets = metrics.map((metric, i) => ({
      label: metric,
      data: data.map(d => ({ x: d.time, y: d[metric] })),
      borderColor: COLORS[i % COLORS.length],
      backgroundColor: type === 'area' ? 
        COLORS[i % COLORS.length] + '33' : undefined,
      fill: type === 'area',
      tension: 0.4
    }));
    
    chartRef.current.update('none'); // Efficient update
  }, [data, type]);
  
  return <canvas ref={canvasRef} />;
};
```

---

## 6. NETWORK TOPOLOGY MODULE

### 6.1 Discovery Engine

```python
class TopologyDiscovery:
    """
    Multi-layer network topology discovery
    """
    
    DISCOVERY_METHODS = [
        "arp_scan",
        "ping_sweep", 
        "snmp_scan",
        "route_analysis",
        "connection_tracking"
    ]
    
    async def discover(self, subnet: str = None) -> Topology:
        """
        1. ARP scan for local devices
        2. SNMP discovery for managed switches
        3. Analyze routing table for gateways
        4. Track connections to map relationships
        5. OS fingerprinting for device types
        """
        nodes = []
        edges = []
        
        # Local subnet discovery
        local_subnet = subnet or self.get_local_subnet()
        arp_results = await self.arp_scan(local_subnet)
        
        for ip, mac, vendor in arp_results:
            node = Node(
                id=ip,
                ip=ip,
                mac=mac,
                vendor=vendor,
                type=self.classify_device(ip, mac),
                properties=await self.probe_device(ip)
            )
            nodes.append(node)
        
        # Gateway detection
        gateway = self.get_default_gateway()
        if not any(n.ip == gateway for n in nodes):
            nodes.append(Node(
                id=gateway,
                ip=gateway,
                type="router",
                properties={"role": "gateway"}
            ))
        
        # Build connections
        for node in nodes:
            if node.type == "router":
                # Find connected subnets
                routes = await self.get_routes_via(node.ip)
                for route in routes:
                    edges.append(Edge(
                        source=node.id,
                        target=route.subnet,
                        type="route",
                        properties=route
                    ))
        
        return Topology(nodes=nodes, edges=edges)
```

### 6.2 Topology Visualization (D3.js)

```javascript
// D3 force-directed graph
const TopologyGraph = ({ topology, onNodeClick }) => {
  const svgRef = useRef();
  const simulationRef = useRef();
  
  useEffect(() => {
    const svg = d3.select(svgRef.current);
    const width = svg.node().parentElement.clientWidth;
    const height = svg.node().parentElement.clientHeight;
    
    // Clear previous
    svg.selectAll("*").remove();
    
    // Create simulation
    simulationRef.current = d3.forceSimulation(topology.nodes)
      .force("link", d3.forceLink(topology.edges).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(50));
    
    // Draw links
    const link = svg.append("g")
      .selectAll("line")
      .data(topology.edges)
      .join("line")
      .attr("stroke", d => d.type === 'route' ? '#3b82f6' : '#9ca3af')
      .attr("stroke-width", d => d.bandwidth ? Math.log10(d.bandwidth) : 2);
    
    // Draw nodes
    const node = svg.append("g")
      .selectAll("g")
      .data(topology.nodes)
      .join("g")
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));
    
    // Node icons based on type
    node.append("circle")
      .attr("r", 25)
      .attr("fill", d => {
        const colors = {
          router: '#ef4444',
          switch: '#f59e0b',
          server: '#3b82f6',
          workstation: '#10b981',
          unknown: '#6b7280'
        };
        return colors[d.type] || colors.unknown;
      })
      .attr("stroke", '#fff')
      .attr("stroke-width", 2);
    
    // Labels
    node.append("text")
      .text(d => d.ip.split('.').pop())
      .attr("text-anchor", "middle")
      .attr("dy", 5)
      .attr("fill", "white")
      .attr("font-size", "12px");
    
    // Hostnames below
    node.append("text")
      .text(d => d.hostname || '')
      .attr("text-anchor", "middle")
      .attr("dy", 40)
      .attr("fill", "#374151")
      .attr("font-size", "11px");
    
    // Traffic animation on links
    const traffic = svg.append("g")
      .selectAll("circle")
      .data(topology.edges.filter(e => e.bandwidth))
      .join("circle")
      .attr("r", 3)
      .attr("fill", '#22c55e');
    
    // Animate traffic
    function animateTraffic() {
      traffic
        .transition()
        .duration(d => 1000 / (d.bandwidth / 1000000 || 1))
        .ease(d3.easeLinear)
        .attrTween("transform", function(d) {
          return function(t) {
            const x = d.source.x + (d.target.x - d.source.x) * t;
            const y = d.source.y + (d.target.y - d.source.y) * t;
            return `translate(${x},${y})`;
          };
        })
        .on("end", animateTraffic);
    }
    animateTraffic();
    
    // Update positions on tick
    simulationRef.current.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);
      
      node.attr("transform", d => `translate(${d.x},${d.y})`);
    });
  }, [topology]);
  
  return <svg ref={svgRef} className="topology-graph" />;
};
```

---

## 7. SECURITY & ACCESS CONTROL

### 7.1 Permission Model

```python
class Permission(str, Enum):
    # Dashboard permissions
    DASHBOARD_VIEW = "dashboard:view"
    DASHBOARD_EDIT = "dashboard:edit"
    DASHBOARD_CREATE = "dashboard:create"
    DASHBOARD_DELETE = "dashboard:delete"
    DASHBOARD_SHARE = "dashboard:share"
    
    # Metric permissions
    METRICS_VIEW = "metrics:view"
    METRICS_EXPORT = "metrics:export"
    
    # Command permissions
    COMMAND_EXECUTE_READ = "command:execute:read"    # Safe commands
    COMMAND_EXECUTE_WRITE = "command:execute:write"  # Network config
    COMMAND_EXECUTE_SYSTEM = "command:execute:system" # System commands
    
    # Network configuration
    NET_CONFIG_VIEW = "net:config:view"
    NET_CONFIG_EDIT = "net:config:edit"
    NET_CONFIG_APPLY = "net:config:apply"
    
    # Administration
    ADMIN_USERS = "admin:users"
    ADMIN_SETTINGS = "admin:settings"
    ADMIN_LOGS = "admin:logs"

class RBACPolicy:
    ROLES = {
        "viewer": [
            Permission.DASHBOARD_VIEW,
            Permission.METRICS_VIEW
        ],
        "operator": [
            Permission.DASHBOARD_VIEW,
            Permission.DASHBOARD_EDIT,
            Permission.DASHBOARD_CREATE,
            Permission.METRICS_VIEW,
            Permission.METRICS_EXPORT,
            Permission.COMMAND_EXECUTE_READ,
            Permission.NET_CONFIG_VIEW
        ],
        "admin": [
            # All permissions
        ]
    }
```

### 7.2 Command Security

```python
class SecureCommandExecutor:
    """
    Multi-layer security for command execution
    """
    
    SECURITY_LAYERS = [
        # 1. Whitelist validation
        "validate_command_in_whitelist",
        
        # 2. Parameter sanitization
        "sanitize_parameters",
        
        # 3. Target validation (IP/hostname safe)
        "validate_target",
        
        # 4. Rate limiting
        "check_rate_limit",
        
        # 5. Privilege check
        "verify_sudo_privileges",
        
        # 6. Resource limits
        "set_resource_limits",  # timeout, memory
        
        # 7. Output filtering
        "sanitize_output"  # Remove sensitive data
    ]
    
    DANGEROUS_PATTERNS = [
        r";.*",           # Command chaining
        r"\|.*",          # Pipes
        r"`.*`",          # Backticks
        r"\$\(.*\)",      # Command substitution
        r"<.*",           # Input redirection
        r">.*",           # Output redirection
        r"&",             # Background
        r"rm\s+-rf",
        r"dd\s+if=",
        r"mkfs",
        r"fdisk",
        r"iptables\s+-F"
    ]
```

---

## 8. DEPLOYMENT ARCHITECTURE

### 8.1 Docker Compose Configuration

```yaml
version: '3.8'

services:
  netdash:
    build: .
    ports:
      - "5000:5000"
      - "5001:5001"  # WebSocket
    environment:
      - INFLUXDB_URL=http://influxdb:8086
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=${JWT_SECRET}
    volumes:
      - ./data:/app/data
      - ./screens:/app/screens
      - /var/run/docker.sock:/var/run/docker.sock  # For container metrics
    networks:
      - netdash-net
    depends_on:
      - influxdb
      - redis
      - postgres
    cap_add:
      - NET_ADMIN      # For network config
      - NET_RAW        # For packet capture
      - SYS_ADMIN      # For system metrics
  
  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    environment:
      - INFLUXDB_DB=netdash
      - INFLUXDB_ADMIN_USER=admin
      - INFLUXDB_ADMIN_PASSWORD=${INFLUX_ADMIN_PASSWORD}
    volumes:
      - influxdb-data:/var/lib/influxdb2
    networks:
      - netdash-net
  
  redis:
    image: redis:7-alpine
    networks:
      - netdash-net
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=netdash
      - POSTGRES_USER=netdash
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - netdash-net
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - netdash
    networks:
      - netdash-net

volumes:
  influxdb-data:
  postgres-data:

networks:
  netdash-net:
    driver: bridge
```

### 8.2 Systemd Service

```ini
# /etc/systemd/system/netdash.service
[Unit]
Description=NetDash Network Control Center
After=network.target

[Service]
Type=simple
User=netdash
Group=netdash
WorkingDirectory=/opt/netdash
Environment=PATH=/opt/netdash/venv/bin
Environment=CONFIG_PATH=/etc/netdash/config.yml
Environment=JWT_SECRET_FILE=/etc/netdash/jwt_secret
ExecStart=/opt/netdash/venv/bin/python -m netdash.server
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/netdash/data
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_RAW
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_RAW

[Install]
WantedBy=multi-user.target
```

---

## 9. IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up FastAPI backend with WebSocket support
- [ ] Implement metric collection system (psutil wrapper)
- [ ] Set up InfluxDB for time-series storage
- [ ] Create basic card models and API

### Phase 2: Dashboard Builder (Weeks 3-4)
- [ ] Implement drag-and-drop canvas (react-grid-layout)
- [ ] Build card palette with categories
- [ ] Create properties panel for configuration
- [ ] Implement screen save/load functionality

### Phase 3: Visualization (Weeks 5-6)
- [ ] Implement Gauge component with Canvas API
- [ ] Integrate Chart.js for real-time charts
- [ ] Add sparkline mini-charts
- [ ] Create digital display cards

### Phase 4: Network Features (Weeks 7-8)
- [ ] Build network topology discovery
- [ ] Implement topology visualization (D3.js)
- [ ] Add connection table with filtering
- [ ] Create interface status cards

### Phase 5: Control Features (Weeks 9-10)
- [ ] Implement secure command executor
- [ ] Add network configuration panels
- [ ] Create service control cards
- [ ] Build terminal overlay component

### Phase 6: Polish (Week 11-12)
- [ ] Add dark/light theme support
- [ ] Implement responsive layouts
- [ ] Add export/import functionality
- [ ] Performance optimization

---

## 10. KEY TECHNICAL DECISIONS

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend Framework | FastAPI | Async support, auto OpenAPI, high performance |
| Frontend Framework | React + TypeScript | Component ecosystem, type safety |
| State Management | Zustand + WebSocket | Lightweight, real-time sync |
| Charts | Chart.js + D3.js | Canvas performance + custom viz |
| Time-Series DB | InfluxDB | Downsampling, retention policies, queries |
| Real-time | WebSocket (socket.io) | Fallback support, room management |
| Security | RBAC + JWT | Granular permissions, stateless auth |
| Job Queue | Celery + Redis | Background tasks, retries, monitoring |

---

**Document Version**: 3.0  
**Last Updated**: 2024  
**Status**: Ready for Implementation
