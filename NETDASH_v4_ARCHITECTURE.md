# NetDash v4 - Complete Re-Architecture
## High-Level & Low-Level Design Document

---

## 1. EXECUTIVE SUMMARY

NetDash v4 transforms from a static network discovery tool into a **dynamic, extensible System & Network Control Center**. The new architecture supports:
- **Custom Dashboard Creation**: Admin-defined screens with drag-and-drop card placement
- **Real-time Gauges & Charts**: Interactive visualization of system and network metrics
- **Unified Monitoring**: Network diagnostics + System performance (CPU, Memory, Disk, Processes)
- **Card-Based Architecture**: Modular, reusable monitoring components
- **Real-time Updates**: WebSocket-based live data streaming

---

## 2. HIGH-LEVEL ARCHITECTURE (HLA)

### 2.1 Architectural Pattern: Micro-Frontend + Modular Backend

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Dynamic Dashboard Manager                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │  Screen 1   │  │  Screen 2   │  │  Screen 3   │  │   Admin    │ │   │
│  │  │ (Overview)  │  │ (Network)   │  │ (System)    │  │  Builder   │ │   │
│  │  │             │  │             │  │             │  │            │ │   │
│  │  │ ┌───┬───┐   │  │ ┌───┬───┐   │  │ ┌───┬───┐   │  │ ┌────────┐ │ │   │
│  │  │ │CPU│NET│   │  │ │ARP│TOP│   │  │ │IO │MEM│   │  │ │Toolbox │ │ │   │
│  │  │ │ChartGauge │  │ │CardCard│   │  │ │ChartGauge│   │  │ │Canvas  │ │ │   │
│  │  │ └───┴───┘   │  │ └───┴───┘   │  │ └───┴───┘   │  │ │Config  │ │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ WebSocket/HTTP
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Dashboard   │  │   Metrics    │  │   Command    │  │    Screen    │   │
│  │   Engine     │  │  Aggregator  │  │   Executor   │  │   Manager    │   │
│  │              │  │              │  │              │  │              │   │
│  │ • Card Inst  │  │ • Collector  │  │ • Sandbox    │  │ • CRUD       │   │
│  │ • Layout Mgr │  │ • Time Series│  │ • Streaming  │  │ • Templates  │   │
│  │ • State Sync │  │ • Anomaly Det│  │ • Safety     │  │ • Sharing    │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVICE LAYER                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   System     │  │   Network    │  │  Time-Series │  │   Config     │   │
│  │   Monitor    │  │   Scanner    │  │   Database   │  │   Service    │   │
│  │              │  │              │  │              │  │              │   │
│  │ • CPU/Mem    │  │ • ARP Scan   │  │ • InfluxDB   │  │ • Settings   │   │
│  │ • Disk I/O   │  │ • Port Scan  │  │ • Retention  │  │ • Auth       │   │
│  │ • Processes  │  │ • Topology   │  │ • Downsampling│  │ • Audit Log  │   │
│  │ • Network IO │  │ • DNS Tools  │  │              │  │              │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   SQLite/    │  │   InfluxDB   │  │    Redis     │  │   File       │   │
│  │   PostgreSQL │  │   (Metrics)  │  │   (Cache)    │  │   Storage    │   │
│  │              │  │              │  │              │  │              │   │
│  │ • Screens    │  │ • Time-series│  │ • Session    │  │ • Exports    │   │
│  │ • Cards      │  │ • Gauges     │  │ • Pub/Sub    │  │ • Reports    │   │
│  │ • Users      │  │ • Aggregates │  │ • Rate Limit │  │ • Topology   │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| **Dashboard Engine** | Card instantiation, layout management, real-time state synchronization | React/Vue.js + GridStack.js |
| **Metrics Aggregator** | Collect, normalize, and stream metrics from all sources | Python AsyncIO + Pydantic |
| **Command Executor** | Safe execution of system/network commands with sandboxing | Python subprocess + seccomp |
| **Screen Manager** | CRUD operations for dashboard screens, templates, sharing | FastAPI + SQLAlchemy |
| **System Monitor** | CPU, memory, disk, process metrics collection | psutil + py-cpuinfo |
| **Network Scanner** | ARP, port, topology, DNS discovery | python-nmap + scapy |
| **Time-Series DB** | High-frequency metric storage and querying | InfluxDB 2.x |
| **Config Service** | User preferences, authentication, audit logging | JWT + PostgreSQL |

---

## 3. LOW-LEVEL DESIGN (LLD)

### 3.1 Database Schema

```sql
-- Screens (Dashboard Pages)
CREATE TABLE screens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    layout_config JSONB NOT NULL DEFAULT '{}',
    is_default BOOLEAN DEFAULT false,
    refresh_interval INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100)
);

-- Cards (Monitoring Widgets)
CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    screen_id UUID REFERENCES screens(id) ON DELETE CASCADE,
    card_type VARCHAR(50) NOT NULL, -- 'gauge', 'chart', 'table', 'topology', 'terminal'
    title VARCHAR(255),
    position_x INTEGER NOT NULL DEFAULT 0,
    position_y INTEGER NOT NULL DEFAULT 0,
    width INTEGER NOT NULL DEFAULT 4,
    height INTEGER NOT NULL DEFAULT 4,
    config JSONB NOT NULL DEFAULT '{}',
    data_source VARCHAR(100), -- 'system', 'network', 'custom'
    metric_path VARCHAR(255), -- dot notation: system.cpu.percent
    refresh_interval INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Metric Definitions
CREATE TABLE metric_definitions (
    id VARCHAR(100) PRIMARY KEY,
    category VARCHAR(50) NOT NULL, -- 'system', 'network', 'process'
    name VARCHAR(100) NOT NULL,
    unit VARCHAR(50),
    description TEXT,
    command_template TEXT, -- shell command template
    parser_type VARCHAR(50), -- 'json', 'regex', 'csv', 'table'
    is_active BOOLEAN DEFAULT true
);

-- Time-series data stored in InfluxDB
-- measurement: system_metrics
-- tags: host, metric_name
-- fields: value_float, value_int, value_str

-- Audit Logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(100),
    action VARCHAR(100),
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    details JSONB
);
```

### 3.2 API Endpoints

```yaml
# Dashboard Management
GET    /api/v1/screens                    # List all screens
POST   /api/v1/screens                    # Create new screen
GET    /api/v1/screens/{id}               # Get screen with cards
PUT    /api/v1/screens/{id}               # Update screen
DELETE /api/v1/screens/{id}               # Delete screen
POST   /api/v1/screens/{id}/duplicate     # Clone screen

# Card Management
GET    /api/v1/cards                      # List available card types
POST   /api/v1/screens/{id}/cards         # Add card to screen
PUT    /api/v1/cards/{id}                 # Update card config/position
DELETE /api/v1/cards/{id}                 # Remove card

# Real-time Metrics
GET    /api/v1/metrics/definitions        # Available metrics catalog
GET    /api/v1/metrics/current            # Current values (snapshot)
GET    /api/v1/metrics/history            # Historical data (query params)
WS     /ws/v1/metrics                     # WebSocket live stream

# System Commands
POST   /api/v1/execute                    # Execute safe command
GET    /api/v1/execute/{job_id}/status    # Command status
GET    /api/v1/execute/{job_id}/output    # Command output stream

# Network Operations
POST   /api/v1/network/scan               # Start network scan
POST   /api/v1/network/discovery          # ARP/discovery sweep
GET    /api/v1/network/hosts              # Discovered hosts
GET    /api/v1/network/topology           # Network topology

# Data Export
POST   /api/v1/export/screens/{id}      # Export screen config
POST   /api/v1/export/metrics             # Export metric data (CSV/JSON)
```

### 3.3 Card Type Specifications

```typescript
// Base Card Interface
interface BaseCard {
  id: string;
  type: 'gauge' | 'chart' | 'table' | 'topology' | 'terminal' | 'metric-bar';
  title: string;
  position: { x: number; y: number; w: number; h: number };
  dataSource: {
    category: 'system' | 'network' | 'process' | 'custom';
    metric: string;
    interval: number;
    aggregation?: 'avg' | 'max' | 'min' | 'last';
  };
  styling: {
    colorScheme: string;
    thresholds?: { value: number; color: string }[];
    showLabels: boolean;
  };
}

// Gauge Card - Circular/Linear progress gauge
interface GaugeCard extends BaseCard {
  type: 'gauge';
  config: {
    min: number;
    max: number;
    unit: string;
    gaugeType: 'circular' | 'linear' | 'radial';
    thresholds: { value: number; color: string; label?: string }[];
    showValue: boolean;
    decimalPlaces: number;
  };
}

// Chart Card - Time-series visualization
interface ChartCard extends BaseCard {
  type: 'chart';
  config: {
    chartType: 'line' | 'area' | 'bar' | 'pie' | 'doughnut';
    timeRange: '1m' | '5m' | '15m' | '1h' | '6h' | '24h' | 'custom';
    showLegend: boolean;
    stacked: boolean;
    fill: boolean;
    yAxisMin?: number;
    yAxisMax?: number;
    multiMetrics?: string[]; // For multi-line charts
  };
}

// Table Card - Sortable, filterable data grid
interface TableCard extends BaseCard {
  type: 'table';
  config: {
    columns: { field: string; header: string; width?: number; sortable?: boolean }[];
    pageSize: number;
    filterable: boolean;
    exportable: boolean;
    refreshMode: 'poll' | 'push';
  };
}

// Topology Card - Network graph visualization
interface TopologyCard extends BaseCard {
  type: 'topology';
  config: {
    layout: 'force' | 'hierarchical' | 'circular';
    showLabels: boolean;
    edgeLabels: boolean;
    physics: boolean;
    groupBy: 'subnet' | 'vendor' | 'status';
  };
}

// Terminal Card - Interactive command execution
interface TerminalCard extends BaseCard {
  type: 'terminal';
  config: {
    command: string;
    args: string[];
    autoRun: boolean;
    allowedCommands: string[];
    shell: string;
  };
}

// Metric Bar - Horizontal progress bars
interface MetricBarCard extends BaseCard {
  type: 'metric-bar';
  config: {
    bars: { label: string; metric: string; max: number; unit: string }[];
    orientation: 'horizontal' | 'vertical';
    showPercent: boolean;
  };
}
```

### 3.4 Backend Class Structure

```python
# Core Classes

class DashboardEngine:
    """Manages screen lifecycle and card orchestration"""
    def __init__(self):
        self.screens: Dict[UUID, Screen] = {}
        self.card_registry: CardRegistry
        self.websocket_manager: WebSocketManager
    
    async def create_screen(self, config: ScreenConfig) -> Screen:
    async def delete_screen(self, screen_id: UUID) -> bool
    async def update_layout(self, screen_id: UUID, layout: LayoutConfig)
    async def broadcast_metric(self, metric: Metric)

class Screen:
    """Represents a dashboard page containing cards"""
    def __init__(self, id: UUID, config: ScreenConfig):
        self.id = id
        self.cards: Dict[UUID, Card] = {}
        self.layout = GridLayout(config.layout)
        self.subscribers: Set[WebSocket] = set()
    
    def add_card(self, card: Card) -> bool
    def remove_card(self, card_id: UUID) -> bool
    def get_card_positions(self) -> List[CardPosition]
    async def refresh_all_cards(self)

class Card(ABC):
    """Abstract base for all monitoring cards"""
    def __init__(self, id: UUID, config: CardConfig):
        self.id = id
        self.config = config
        self.data_source: DataSource
        self.last_value: Any = None
        self.update_interval = config.refresh_interval or 5
    
    @abstractmethod
    async def fetch_data(self) -> MetricData
    @abstractmethod
    def render_config(self) -> Dict[str, Any]
    
    async def subscribe_to_updates(self, callback: Callable)

class GaugeCard(Card):
    """Circular or linear gauge widget"""
    async def fetch_data(self) -> MetricData:
        value = await self.data_source.get_current_value()
        return GaugeData(
            value=value,
            min=self.config.min,
            max=self.config.max,
            thresholds=self.config.thresholds
        )

class ChartCard(Card):
    """Time-series chart widget"""
    async def fetch_data(self) -> MetricData:
        time_range = self.config.time_range
        points = await self.data_source.get_history(
            since=time_range.start,
            interval=self.config.resolution
        )
        return ChartData(points=points, series=self.config.metrics)

class MetricsCollector:
    """Collects system and network metrics"""
    def __init__(self):
        self.system_provider = SystemMetricsProvider()
        self.network_provider = NetworkMetricsProvider()
        self.influx_client = InfluxDBClient()
        self.cache = Redis()
    
    async def collect_system_metrics(self) -> Dict[str, Any]:
        return {
            'cpu': await self.system_provider.get_cpu_stats(),
            'memory': await self.system_provider.get_memory_stats(),
            'disk': await self.system_provider.get_disk_stats(),
            'network_io': await self.system_provider.get_network_io(),
            'processes': await self.system_provider.get_top_processes()
        }
    
    async def collect_network_metrics(self) -> Dict[str, Any]:
        return {
            'interfaces': await self.network_provider.get_interface_stats(),
            'connections': await self.network_provider.get_connection_stats(),
            'arp_table': await self.network_provider.get_arp_table()
        }
    
    async def store_metric(self, name: str, value: float, tags: Dict):
        await self.influx_client.write(
            measurement='system_metrics',
            fields={'value': value},
            tags=tags,
            timestamp=datetime.utcnow()
        )

class CommandExecutor:
    """Safely executes system commands"""
    ALLOWED_COMMANDS = {
        'ping': ['/usr/bin/ping', '-c', '4'],
        'traceroute': ['/usr/bin/traceroute'],
        'nslookup': ['/usr/bin/nslookup'],
        'dig': ['/usr/bin/dig'],
        'ip': ['/sbin/ip'],
        'ss': ['/usr/sbin/ss'],
        'netstat': ['/usr/bin/netstat'],
        'nmap': ['/usr/bin/nmap', '-sn'],  # Limited to ping scan
    }
    
    async def execute(self, command: str, args: List[str]) -> CommandResult:
        if not self._validate_command(command, args):
            raise SecurityError(f"Command '{command}' not allowed")
        
        proc = await asyncio.create_subprocess_exec(
            self.ALLOWED_COMMANDS[command][0],
            *self._sanitize_args(args),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return CommandResult(
            returncode=proc.returncode,
            stdout=stdout.decode(),
            stderr=stderr.decode()
        )
    
    def _validate_command(self, cmd: str, args: List[str]) -> bool
    def _sanitize_args(self, args: List[str]) -> List[str]

# Data Providers

class SystemMetricsProvider:
    """psutil-based system metrics"""
    async def get_cpu_stats(self) -> CPUStats:
        return CPUStats(
            percent=psutil.cpu_percent(interval=1),
            per_cpu=psutil.cpu_percent(percpu=True),
            freq=psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            load_avg=os.getloadavg()
        )
    
    async def get_memory_stats(self) -> MemoryStats:
        virtual = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return MemoryStats(
            total=virtual.total,
            available=virtual.available,
            percent=virtual.percent,
            swap_total=swap.total,
            swap_used=swap.used
        )
    
    async def get_disk_stats(self) -> List[DiskStats]:
        partitions = psutil.disk_partitions()
        return [
            DiskStats(
                mount=p.mountpoint,
                total=psutil.disk_usage(p.mountpoint).total,
                used=psutil.disk_usage(p.mountpoint).used,
                percent=psutil.disk_usage(p.mountpoint).percent
            )
            for p in partitions
        ]

class NetworkMetricsProvider:
    """Network interface and connection monitoring"""
    async def get_interface_stats(self) -> List[InterfaceStats]:
        stats = psutil.net_io_counters(pernic=True)
        addrs = psutil.net_if_addrs()
        return [
            InterfaceStats(
                name=name,
                bytes_sent=s.bytes_sent,
                bytes_recv=s.bytes_recv,
                packets_sent=s.packets_sent,
                packets_recv=s.packets_recv,
                addresses=[a.address for a in addrs.get(name, [])]
            )
            for name, s in stats.items()
        ]
```

---

## 4. FRONTEND ARCHITECTURE

### 4.1 Component Hierarchy

```
App
├── DashboardShell (main layout with sidebar)
│   ├── NavigationMenu (screen list + create button)
│   └── ScreenContainer
│       ├── ScreenHeader (title, actions, settings)
│       └── GridLayout (react-grid-layout)
│           └── CardWrapper (resizable container)
│               ├── GaugeCard
│               │   ├── CircularGauge (d3/echarts)
│               │   └── LinearGauge
│               ├── ChartCard
│               │   └── TimeSeriesChart (echarts/apexcharts)
│               ├── TableCard
│               │   └── DataTable (ag-grid/tanstack)
│               ├── TopologyCard
│               │   └── NetworkGraph (vis-network/cytoscape)
│               ├── TerminalCard
│               │   └── XTerm.js terminal
│               └── MetricBarCard
│                   └── ProgressBars
├── CardLibrarySidebar (drag-and-drop card creation)
│   └── CardTemplateList
├── ScreenBuilderModal (admin configuration)
│   ├── LayoutEditor
│   ├── CardConfigPanel
│   └── DataSourceSelector
└── GlobalStatusBar (connection status, alerts)
```

### 4.2 State Management

```typescript
// Redux Store Structure
interface DashboardState {
  screens: {
    byId: Record<string, Screen>;
    allIds: string[];
    activeScreenId: string | null;
    loading: boolean;
    error: string | null;
  };
  cards: {
    byId: Record<string, Card>;
    definitions: CardDefinition[]; // Available card types
  };
  metrics: {
    current: Record<string, MetricValue>; // metricId -> value
    history: Record<string, MetricPoint[]>; // metricId -> time series
    streaming: boolean;
    lastUpdate: Date;
  };
  layout: {
    isEditing: boolean;
    draggedItem: CardDefinition | null;
    breakpoints: Breakpoints;
  };
}

// WebSocket Message Types
interface MetricUpdate {
  type: 'METRIC_UPDATE';
  payload: {
    metricId: string;
    value: number | string;
    timestamp: number;
    tags: Record<string, string>;
  };
}

interface BatchUpdate {
  type: 'BATCH_UPDATE';
  payload: MetricUpdate['payload'][];
}

interface CommandOutput {
  type: 'COMMAND_OUTPUT';
  payload: {
    jobId: string;
    chunk: string;
    isComplete: boolean;
  };
}
```

### 4.3 Real-time Data Flow

```
┌─────────────┐     WebSocket      ┌─────────────┐     HTTP/WS      ┌─────────────┐
│   Browser   │◄──────────────────►│   Backend   │◄────────────────►│   Sources   │
│             │  1. Subscribe to   │             │   2. Aggregate  │             │
│  ┌───────┐  │     metrics        │  ┌───────┐  │      metrics    │  ┌───────┐  │
│  │ Store │  │                    │  │ WS    │  │                 │  │ psutil│  │
│  │       │  │◄── 3. Push updates ─┤  │ Mgr   │◄─┼── 4. Collect ───┤  │ nmap  │  │
│  └───────┘  │                    │  └───────┘  │                 │  │ net   │  │
│  ┌───────┐  │                    │  ┌───────┐  │                 │  └───────┘  │
│  │ React │  │◄── 4. Re-render  ──┤  │Metrics│  │                 │             │
│  │ Card  │  │     components     │  │Coll.  │  │                 │             │
│  └───────┘  │                    │  └───────┘  │                 │             │
└─────────────┘                    └─────────────┘                 └─────────────┘
```

---

## 5. KEY FEATURES IMPLEMENTATION

### 5.1 Dynamic Screen Creation

**User Flow:**
1. Click "+ New Screen" in sidebar
2. Choose template (Blank, System Overview, Network Monitor, Custom)
3. Enter screen name and description
4. Land on new screen with edit mode enabled
5. Drag cards from Card Library onto grid
6. Configure each card's data source and visualization
7. Save layout (persisted to database)

**Grid Layout System:**
- 12-column responsive grid (react-grid-layout)
- Cards snap to grid with configurable sizes
- Drag-and-drop repositioning
- Resize handles on each card
- Auto-save layout changes

### 5.2 Card System

**Card Lifecycle:**
1. **Instantiation**: Card registered with unique ID, type, and position
2. **Configuration**: Admin sets data source, thresholds, styling
3. **Data Binding**: Card subscribes to metric stream
4. **Rendering**: React component renders based on type
5. **Updates**: Real-time updates via WebSocket
6. **Cleanup**: Unsubscribe on card removal

**Built-in Card Types:**
- **System Gauge**: CPU, Memory, Disk usage with color thresholds
- **Network Traffic**: Real-time bandwidth charts (in/out)
- **Process Table**: Top processes by CPU/memory with sorting
- **Network Topology**: Interactive graph of discovered hosts
- **Port Scanner**: Embedded nmap interface with results table
- **Terminal**: Interactive shell for quick commands
- **Log Viewer**: Streaming log display with filtering
- **Alert Panel**: System notifications and thresholds

### 5.3 Real-time Metrics Pipeline

```python
# Async metrics collection pipeline
async def metrics_pipeline():
    """Continuously collect and broadcast metrics"""
    collector = MetricsCollector()
    broadcaster = WebSocketBroadcaster()
    
    while True:
        start_time = time.time()
        
        # Gather all metrics concurrently
        results = await asyncio.gather(
            collector.collect_system_metrics(),
            collector.collect_network_metrics(),
            collector.collect_process_metrics(),
            return_exceptions=True
        )
        
        # Normalize and store
        metrics_package = normalize_metrics(results)
        await store_in_influxdb(metrics_package)
        
        # Broadcast to subscribers
        await broadcaster.broadcast(metrics_package)
        
        # Maintain consistent interval
        elapsed = time.time() - start_time
        await asyncio.sleep(max(0, INTERVAL - elapsed))
```

### 5.4 Safe Command Execution

```python
class SecureExecutor:
    """Execute system commands in sandboxed environment"""
    
    def __init__(self):
        self.active_jobs: Dict[str, subprocess.Process] = {}
        self.output_buffers: Dict[str, List[str]] = {}
    
    async def execute(self, command: str, args: List[str], 
                     timeout: int = 60) -> AsyncIterator[str]:
        """Stream command output safely"""
        
        # Validate command against whitelist
        if not self._is_allowed(command, args):
            raise SecurityError("Command not in whitelist")
        
        # Create subprocess with restricted environment
        proc = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            limit=1024 * 1024,  # 1MB buffer limit
            env=self._get_restricted_env()
        )
        
        job_id = str(uuid.uuid4())
        self.active_jobs[job_id] = proc
        
        try:
            async for line in proc.stdout:
                yield line.decode('utf-8', errors='replace')
        finally:
            if proc.returncode is None:
                proc.terminate()
                await proc.wait()
            del self.active_jobs[job_id]
```

---

## 6. TECHNOLOGY STACK

### 6.1 Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | FastAPI | Async API endpoints, auto OpenAPI docs |
| Database ORM | SQLAlchemy 2.0 + asyncpg | PostgreSQL async operations |
| Time-Series DB | InfluxDB 2.x | High-frequency metrics storage |
| Cache | Redis | Session store, pub/sub, rate limiting |
| WebSockets | fastapi-socketio | Real-time bidirectional comm |
| Task Queue | Celery + Redis | Background job processing |
| Security | JWT + passlib | Authentication/authorization |
| Metrics | prometheus-client | Self-monitoring |

### 6.2 Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | React 18 + TypeScript | Component-based UI |
| State Management | Redux Toolkit + RTK Query | Global state, API caching |
| Grid Layout | react-grid-layout | Draggable, resizable cards |
| Charts | Apache ECharts | Time-series, gauges, complex viz |
| Tables | TanStack Table | Sortable, filterable data grids |
| Network Graph | Cytoscape.js | Topology visualization |
| Terminal | XTerm.js | In-browser terminal emulator |
| Styling | Tailwind CSS + Headless UI | Utility-first CSS |
| Icons | Lucide React | Consistent iconography |
| Build | Vite | Fast dev server, optimized builds |

### 6.3 System Integration
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Process Info | psutil | Cross-platform system metrics |
| Network Scan | python-nmap, scapy | Host discovery, port scanning |
| Packet Capture | pyshark | Network protocol analysis |
| Speed Test | speedtest-cli | Internet bandwidth testing |

---

## 7. DEPLOYMENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                        REVERSE PROXY                            │
│                     (Nginx/Caddy)                               │
│        • SSL termination • Rate limiting • Static assets        │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼──────┐      ┌─────────▼─────────┐   ┌────────▼────────┐
│  Static Files │      │   FastAPI App     │   │   WebSocket     │
│  (React SPA)  │      │   (API Server)    │   │   Endpoint      │
└───────────────┘      └─────────┬─────────┘   └─────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
    ┌───────▼──────┐    ┌────────▼────────┐   ┌──────▼──────┐
    │  PostgreSQL  │    │    InfluxDB     │   │    Redis    │
    │   (Screens,  │    │   (Time-series) │   │  (Cache,    │
    │    Cards)    │    │                 │   │   Pub/Sub)  │
    └──────────────┘    └─────────────────┘   └─────────────┘
```

### Docker Compose Configuration
```yaml
version: '3.8'
services:
  netdash:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres/netdash
      - INFLUXDB_URL=http://influxdb:8086
      - REDIS_URL=redis://redis:6379
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # For container monitoring
    cap_add:
      - NET_ADMIN  # For network scanning
      - NET_RAW
  
  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  influxdb:
    image: influxdb:2.7
    volumes:
      - influxdb_data:/var/lib/influxdb2
  
  redis:
    image: redis:7-alpine
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./static:/usr/share/nginx/html
```

---

## 8. SECURITY CONSIDERATIONS

1. **Command Whitelisting**: Only pre-approved commands can be executed
2. **Sandboxing**: Commands run in restricted environment with limited privileges
3. **Input Sanitization**: All user inputs validated with Pydantic schemas
4. **Rate Limiting**: API endpoints protected against abuse
5. **Authentication**: JWT-based auth with refresh tokens
6. **Authorization**: Role-based access (Admin vs Viewer)
7. **Audit Logging**: All actions logged with user attribution
8. **Network Isolation**: Containerized deployment with minimal privileges

---

## 9. EXTENSIBILITY POINTS

### Adding New Card Types
1. Create React component in `frontend/src/cards/{Type}Card.tsx`
2. Add card definition to `CardRegistry`
3. Implement corresponding backend data provider if needed
4. Update TypeScript types

### Adding New Data Sources
1. Implement provider class extending `BaseMetricsProvider`
2. Register in `MetricsCollector`
3. Add metric definitions to database
4. Frontend automatically discovers via `/api/v1/metrics/definitions`

### Custom Commands
1. Add to `ALLOWED_COMMANDS` whitelist with argument constraints
2. Create card type that uses terminal component
3. Map output parser for structured results

---

## 10. IMPLEMENTATION ROADMAP

### Phase 1: Core Infrastructure (Week 1)
- [ ] Database schema setup
- [ ] FastAPI project structure
- [ ] Docker compose environment
- [ ] Basic CRUD for screens/cards

### Phase 2: Metrics Pipeline (Week 2)
- [ ] System metrics collector (psutil)
- [ ] Network metrics collector
- [ ] InfluxDB integration
- [ ] WebSocket broadcasting

### Phase 3: Frontend Foundation (Week 3)
- [ ] React + Vite setup
- [ ] Dashboard shell layout
- [ ] Grid layout system
- [ ] Card wrapper components

### Phase 4: Card Implementation (Week 4)
- [ ] Gauge card (circular/linear)
- [ ] Chart card (time-series)
- [ ] Table card (sortable)
- [ ] Terminal card

### Phase 5: Advanced Features (Week 5)
- [ ] Topology visualization
- [ ] Screen builder modal
- [ ] Card library sidebar
- [ ] Import/export functionality

### Phase 6: Polish & Security (Week 6)
- [ ] Authentication/authorization
- [ ] Audit logging
- [ ] Command sandboxing
- [ ] Documentation

---

## 11. FILE STRUCTURE

```
netdash/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app factory
│   │   ├── config.py            # Settings management
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── screens.py   # Screen CRUD endpoints
│   │   │   │   ├── cards.py     # Card management
│   │   │   │   ├── metrics.py   # Metrics API
│   │   │   │   ├── commands.py  # Safe command execution
│   │   │   │   └── network.py   # Network operations
│   │   │   └── deps.py          # Dependencies (DB, auth)
│   │   ├── core/
│   │   │   ├── security.py      # Auth, JWT, permissions
│   │   │   ├── executor.py      # Safe command execution
│   │   │   └── websocket.py     # WebSocket manager
│   │   ├── models/
│   │   │   ├── database.py      # SQLAlchemy models
│   │   │   └── schemas.py       # Pydantic schemas
│   │   ├── services/
│   │   │   ├── dashboard.py     # Dashboard business logic
│   │   │   ├── metrics.py       # Metrics aggregation
│   │   │   ├── collector.py     # Data collection pipeline
│   │   │   └── network.py       # Network scanning
│   │   └── providers/
│   │       ├── system.py        # psutil provider
│   │       ├── network.py       # network tools provider
│   │       └── base.py          # Abstract base
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DashboardShell.tsx
│   │   │   ├── ScreenContainer.tsx
│   │   │   ├── GridLayout.tsx
│   │   │   ├── CardWrapper.tsx
│   │   │   ├── CardLibrary.tsx
│   │   │   └── ScreenBuilder/
│   │   ├── cards/
│   │   │   ├── GaugeCard.tsx
│   │   │   ├── ChartCard.tsx
│   │   │   ├── TableCard.tsx
│   │   │   ├── TopologyCard.tsx
│   │   │   ├── TerminalCard.tsx
│   │   │   └── MetricBarCard.tsx
│   │   ├── store/
│   │   │   ├── index.ts
│   │   │   ├── screensSlice.ts
│   │   │   ├── metricsSlice.ts
│   │   │   └── websocketMiddleware.ts
│   │   ├── hooks/
│   │   │   ├── useMetrics.ts
│   │   │   ├── useCards.ts
│   │   │   └── useWebSocket.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── vite.config.ts
├── docker-compose.yml
├── nginx.conf
└── README.md
```

---

**Document Version**: 4.0  
**Last Updated**: 2024  
**Author**: Agent-oo1 Architecture Team
