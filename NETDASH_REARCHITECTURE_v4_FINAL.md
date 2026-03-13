# NetDash v4.0 - Complete System Re-Architecture
## Full Stack Network & System Control Center

**Document Version:** 4.0  
**Date:** March 2025  
**Status:** Complete Re-Architecture  

---

## 1. EXECUTIVE SUMMARY

NetDash v4.0 is a comprehensive re-architecture transforming the basic network dashboard into a **professional System Control Center**. The new design emphasizes:

- **Dynamic Dashboard Canvas:** Drag-and-drop interface with configurable cards
- **Real-time Visualization:** Gauges, charts, and graphs using WebSockets
- **Screen Management:** Admin-defined monitoring screens for different operational contexts
- **System Integration:** Direct execution of tuning commands with safety controls
- **Plugin Architecture:** Extensible card types for custom metrics

---

## 2. HIGH-LEVEL ARCHITECTURE (HLA)

### 2.1 Architectural Pattern: **Micro-Frontend + Modular Backend**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │   React SPA  │ │    WebGL     │ │   D3.js      │ │   Monaco Editor      │ │
│  │   Dashboard  │ │   Gauges     │ │   Charts     │ │   (Config/Tuning)    │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│                         GATEWAY/API LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │   WebSocket  │ │   REST API   │ │   GraphQL    │ │   Auth Middleware    │ │
│  │   Server     │ │   Gateway    │ │   Endpoint   │ │   (JWT/RBAC)         │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│                        SERVICE LAYER (Domain)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │   Screen     │ │   Card       │ │   Metrics    │ │   Command            │ │
│  │   Service    │ │   Manager    │ │   Engine     │ │   Executor           │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │   Alert      │ │   Topology   │ │   Discovery  │ │   Performance        │ │
│  │   Service    │ │   Mapper     │ │   Engine     │ │   Analyzer           │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│                      DATA/INFRASTRUCTURE LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │   Redis      │ │   SQLite/    │ │   InfluxDB   │ │   System Command     │ │
│  │   (Pub/Sub)  │ │   Config DB  │ │   (TSDB)     │ │   Interface          │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Core Components

#### 2.2.1 Frontend (React + TypeScript)
- **Dashboard Canvas:** Grid-layout system for card placement
- **Component Library:** Reusable card types (gauges, charts, tables)
- **State Management:** Redux Toolkit + WebSocket middleware
- **Visualization:** 
  - Canvas/WebGL for high-performance gauges
  - Recharts/D3 for time-series data
  - react-grid-layout for card positioning

#### 2.2.2 Backend (Python FastAPI)
- **API Gateway:** RESTful endpoints + WebSocket for streaming
- **Service Layer:** Domain-driven design with clear bounded contexts
- **Security:** RBAC (Role-Based Access Control), command sandboxing
- **Async Processing:** Background tasks for long-running commands

#### 2.2.3 Data Layer
- **Time-Series Database:** InfluxDB for metrics retention
- **Configuration:** SQLite for dashboards, screens, and user preferences
- **Caching:** Redis for real-time pub/sub and session management

---

## 3. LOW-LEVEL DESIGN (LLD)

### 3.1 Domain Models

```typescript
// Screen (Dashboard Page)
interface Screen {
  id: string;
  name: string;
  description: string;
  layout: GridLayout;
  cards: Card[];
  refreshRate: number;      // Global refresh interval
  theme: 'dark' | 'light' | 'custom';
  accessLevel: 'viewer' | 'operator' | 'admin';
  createdBy: string;
  modifiedAt: Date;
}

// Card (Widget)
interface Card {
  id: string;
  type: CardType;
  title: string;
  position: GridPosition;
  size: GridSize;
  config: CardConfig;
  dataSource: DataSource;
  actions?: CardAction[];
  refreshRate?: number;     // Override global rate
}

type CardType = 
  | 'gauge'           // Circular/speedometer gauge
  | 'line-chart'      // Time-series line chart
  | 'bar-chart'       // Bar/histogram chart
  | 'pie-chart'       // Pie/donut chart
  | 'stat'            // Single stat with sparkline
  | 'table'           // Data table
  | 'topology'        // Network graph visualization
  | 'log-viewer'      // Real-time log tail
  | 'command'         // Execute command button/terminal
  | 'heatmap'         // Heatmap visualization
  | 'custom';         // Plugin-based custom card

// Data Source Configuration
interface DataSource {
  type: 'metric' | 'command' | 'api' | 'stream';
  config: MetricSource | CommandSource | ApiSource | StreamSource;
  transform?: DataTransform[];  // Optional data transformation pipeline
}

interface CommandSource {
  command: string;           // e.g., 'iostat', 'ss -tuln', 'nmap'
  args?: string[];
  parser: 'json' | 'regex' | 'csv' | 'custom';
  timeout: number;
  requiresSudo: boolean;
  confirmationRequired?: boolean;  // For destructive commands
}
```

### 3.2 Card Type Specifications

#### 3.2.1 Gauge Card
```typescript
interface GaugeConfig {
  min: number;
  max: number;
  units: string;           // 'MB/s', '°C', '%'
  thresholds: Threshold[]; // Color zones
  needleColor?: string;
  digitalDisplay?: boolean;
  decimals?: number;
}

interface Threshold {
  value: number;
  color: string;           // CSS color or hex
  label?: string;          // 'Warning', 'Critical'
}

// Examples:
// - CPU Usage: 0-100%, thresholds at 70% (yellow), 90% (red)
// - Memory: 0-64GB, thresholds at 80%, 95%
// - Network I/O: Auto-scaling with current max
```

#### 3.2.2 Line Chart Card
```typescript
interface LineChartConfig {
  xAxis: AxisConfig;       // Usually time
  yAxis: AxisConfig;
  series: SeriesConfig[];  // Multiple lines
  legend: boolean;
  tooltip: 'simple' | 'detailed';
  zoom: boolean;           // Enable zoom/pan
  realtime: boolean;       // Auto-scroll to latest
  historyDuration: string; // '1h', '24h', '7d'
}

interface SeriesConfig {
  name: string;
  color: string;
  metric: string;          // e.g., 'network.bytes_sent'
  aggregation: 'avg' | 'sum' | 'max' | 'min';
  lineType: 'solid' | 'dashed';
  fillArea?: boolean;
}
```

#### 3.2.3 Command Card (System Tuning)
```typescript
interface CommandCardConfig {
  command: string;
  displayType: 'button' | 'terminal' | 'form';
  buttonConfig?: {
    label: string;
    icon?: string;
    color: 'primary' | 'success' | 'danger' | 'warning';
    requireConfirmation: boolean;
    confirmationMessage?: string;
  };
  formConfig?: {
    fields: FormField[];   // Input parameters for command
  };
  terminalConfig?: {
    showOutput: boolean;
    autoScroll: boolean;
    saveHistory: boolean;
  };
  outputHandler: 'raw' | 'json' | 'table' | 'chart';
  // Security
  allowedUsers?: string[];
  auditLog: boolean;
}
```

### 3.3 API Endpoints

#### Screen Management
```http
# Screen CRUD
GET    /api/screens                    # List all screens
POST   /api/screens                    # Create new screen
GET    /api/screens/{id}               # Get screen config
PUT    /api/screens/{id}               # Update screen
DELETE /api/screens/{id}               # Delete screen
POST   /api/screens/{id}/duplicate     # Clone screen

# Card Management
POST   /api/screens/{id}/cards         # Add card
PUT    /api/screens/{id}/cards/{cid}  # Update card
DELETE /api/screens/{id}/cards/{cid}  # Remove card
POST   /api/screens/{id}/layout        # Update grid layout

# Real-time Data
WS     /ws/screens/{id}                # WebSocket for live updates
GET    /api/cards/{id}/data            # Poll data for card
POST   /api/cards/{id}/execute         # Execute card command
```

#### Metrics & Commands
```http
GET    /api/metrics                    # List available metrics
GET    /api/metrics/{name}/history     # Get historical data
POST   /api/metrics/query             # PromQL-style query

GET    /api/commands                  # List allowed commands
POST   /api/commands/execute          # Execute with safety check
GET    /api/commands/{id}/status       # Check async job status
POST   /api/commands/{id}/cancel      # Cancel running command
```

---

## 4. SYSTEM METRICS REFERENCE

### 4.1 Network Metrics (Built-in Cards)

| Metric | Command | Card Type | Refresh |
|--------|---------|-----------|---------|
| Interface Throughput | `ss -i` / `/proc/net/dev` | Line Chart | 1s |
| Connection States | `ss -tan` | Pie Chart | 5s |
| Port Utilization | `lsof -i` | Heatmap | 10s |
| DNS Query Time | `dig` + timestamp | Gauge | 60s |
| Network Latency | `ping -c 1` | Gauge + Sparkline | 5s |
| ARP Table Size | `ip neigh show | wc -l` | Stat | 30s |
| Route Table | `ip route` | Table | Manual |
| Firewall Rules | `iptables -L -n` | Table | Manual |
| Socket Buffer | `ss -mem` | Gauge | 5s |
| TCP Retransmits | `cat /proc/net/snmp` | Line Chart | 5s |

### 4.2 System Metrics (Built-in Cards)

| Metric | Source | Card Type | Refresh |
|--------|--------|-----------|---------|
| CPU Usage | `/proc/stat` | Gauge | 1s |
| Memory Utilization | `/proc/meminfo` | Gauge + Stacked Chart | 1s |
| Disk I/O | `iostat` | Line Chart | 2s |
| Disk Usage | `df -h` | Bar Chart | 60s |
| Process Count | `ps aux | wc -l` | Stat | 5s |
| Load Average | `/proc/loadavg` | Gauge | 5s |
| Temperature | `sensors` | Gauge | 10s |
| Uptime | `/proc/uptime` | Stat | 60s |
| Top Processes | `ps` | Table | 5s |
| Kernel Messages | `dmesg -w` | Log Viewer | Stream |
| Journal Logs | `journalctl -f` | Log Viewer | Stream |

### 4.3 Network Discovery Cards

| Function | Command | Output |
|----------|---------|--------|
| Host Discovery | `nmap -sn` | Topology Graph |
| Port Scan | `nmap -sS` | Port Table |
| Service Detection | `nmap -sV` | Service Table |
| OS Fingerprint | `nmap -O` | OS Badge |
| Traceroute | `traceroute` | Path Visualization |
| DNS Lookup | `dig +short` | Record Table |
| WHOIS | `whois` | Info Panel |

---

## 5. UX/UI SPECIFICATIONS

### 5.1 Dashboard Canvas Layout

```
┌────────────────────────────────────────────────────────────────┐
│  NetDash     [Screen: Production]          [Add Card] [Settings] │
├────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │ CPU Gauge       │  │ Memory      │  │ Network I/O     │   │
│  │ [     45%    ]  │  │ [Chart]     │  │ [Line Graph]    │   │
│  │                 │  │             │  │                 │   │
│  └─────────────────┘  └─────────────┘  └─────────────────┘   │
│  ┌─────────────────────────────┐  ┌─────────────────────────┐  │
│  │ Active Connections Table    │  │ System Load History     │  │
│  │ [Sortable, Filtered]        │  │ [Multi-series Chart]    │  │
│  │                             │  │                         │  │
│  └─────────────────────────────┘  └─────────────────────────┘  │
│  ┌─────────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │ Quick Commands  │  │ Disk Usage  │  │ Recent Alerts   │   │
│  │ [Button Grid]   │  │ [Bar Chart] │  │ [List]          │   │
│  │                 │  │             │  │                 │   │
│  └─────────────────┘  └─────────────┘  └─────────────────┘   │
│                                                                 │
│  [+ Add Screen]  [Duplicate]  [Export]  [Import]              │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 Card Design System

#### Visual Hierarchy
- **Cards:** 12-column grid, resizable (min 2x2, max 12x8)
- **Header:** Title (14px), drag handle, settings menu, refresh button
- **Content:** Visualization area with responsive scaling
- **Footer:** Timestamp, data source indicator, status dot

#### Color Palette (Dark Theme - Default)
```css
--bg-primary: #0d1117;      /* Main background */
--bg-secondary: #161b22;    /* Card background */
--bg-tertiary: #21262d;     /* Input/controls */
--border: #30363d;          /* Borders */
--text-primary: #c9d1d9;    /* Main text */
--text-secondary: #8b949e;  /* Labels */
--accent-primary: #58a6ff;  /* Primary actions */
--accent-success: #238636;  /* Success/OK */
--accent-warning: #f0883e;  /* Warning */
--accent-danger: #f85149;   /* Danger/Critical */
```

#### Gauge Specifications
```
CPU Gauge Example:
┌─────────────────────┐
│   CPU Utilization   │
│                     │
│      ╭───╮         │
│     /  ↑  \        │  ← Needle pointing to 67%
│    │  67%  │       │  ← Digital readout
│     \_____/        │
│  0%  [===|====] 100│  ← Gradient bar
│                     │
│  ▓ User: 45%       │
│  ░ System: 22%     │
└─────────────────────┘

Thresholds:
- 0-60%:   Green gradient (#238636 → #2ea043)
- 60-80%:  Yellow gradient (#f0883e → #f9c513)
- 80-100%: Red gradient (#f85149 → #ff7b72)
```

### 5.3 Interaction Patterns

#### Card Editing
1. **Hover:** Settings icon appears in top-right
2. **Click Settings:** Modal opens with tabs:
   - **Data:** Select metric/command, configure refresh
   - **Display:** Chart type, colors, thresholds
   - **Actions:** Define click behaviors, alerts
   - **Advanced:** Transform pipelines, custom CSS

#### Screen Builder Workflow
1. User clicks "New Screen"
2. Empty canvas appears with grid overlay
3. "Add Card" button opens card library sidebar
4. Drag card type to canvas or click to add at next position
5. Resize by dragging bottom-right corner
6. Rearrange by dragging header
7. Configure by clicking settings
8. Save with name and access level

#### Command Execution Flow
```
User clicks [Flush DNS] button on card
        ↓
Modal appears: "Execute: sudo systemd-resolve --flush-caches?"
        ↓
User confirms → Backend validates user has 'operator' role
        ↓
Command submitted to sandboxed executor with timeout
        ↓
Real-time output streams to card terminal area
        ↓
Result logged to audit log, notification sent
```

---

## 6. BACKEND IMPLEMENTATION

### 6.1 FastAPI Application Structure

```python
# Project Structure
netdash_v4/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Pydantic settings
│   │   ├── dependencies.py      # DI container
│   │   ├── core/
│   │   │   ├── security.py      # JWT, RBAC
│   │   │   ├── events.py        # Event system
│   │   │   └── exceptions.py    # Custom exceptions
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── screens.py   # Screen endpoints
│   │   │   │   ├── cards.py     # Card endpoints
│   │   │   │   ├── metrics.py   # Metrics endpoints
│   │   │   │   ├── commands.py  # Command endpoints
│   │   │   │   └── websocket.py # WS endpoints
│   │   ├── services/
│   │   │   ├── screen_service.py
│   │   │   ├── card_service.py
│   │   │   ├── metrics_service.py
│   │   │   ├── command_service.py
│   │   │   └── streaming_service.py
│   │   ├── domain/
│   │   │   ├── models.py        # SQLAlchemy models
│   │   │   ├── schemas.py       # Pydantic schemas
│   │   │   └── enums.py         # Domain enums
│   │   ├── infrastructure/
│   │   │   ├── database.py      # DB connection
│   │   │   ├── redis_client.py    # Redis pub/sub
│   │   │   ├── influx_client.py   # Time-series DB
│   │   │   └── command_runner.py  # Sandboxed execution
│   │   └── plugins/
│   │       ├── __init__.py
│   │       └── base.py          # Plugin interface
│   ├── requirements.txt
│   └── alembic/                 # DB migrations
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── cards/           # Card implementations
│   │   │   ├── layout/          # Grid, Header, Sidebar
│   │   │   └── common/          # Reusable UI
│   │   ├── hooks/               # React hooks
│   │   ├── services/            # API clients
│   │   ├── store/               # Redux slices
│   │   └── types/               # TypeScript types
│   └── package.json
└── docker-compose.yml
```

### 6.2 Key Services

#### Command Service (Sandboxed Execution)
```python
class CommandService:
    """
    Executes system commands with security controls:
    - Whitelist validation
    - Timeout enforcement
    - Sudo escalation (if permitted)
    - Output sanitization
    - Audit logging
    """
    
    ALLOWED_COMMANDS = {
        'ping': {'args': ['-c', '4'], 'timeout': 10},
        'ss': {'args': ['-tuln'], 'timeout': 5},
        'iostat': {'args': ['-x', '1', '1'], 'timeout': 3},
        'systemctl': {'args': ['status'], 'timeout': 5},
        # ... more commands
    }
    
    async def execute(
        self,
        command: str,
        args: list[str],
        user: User,
        timeout: int = 30,
        require_sudo: bool = False
    ) -> CommandResult:
        # Validate against whitelist
        # Check user permissions
        # Execute in subprocess
        # Stream output via Redis
        # Log to audit table
        pass
```

#### Metrics Collection Service
```python
class MetricsService:
    """
    Collects system metrics and stores in InfluxDB.
    Supports both pull (polling) and push (webhook) models.
    """
    
    async def get_metric_history(
        self,
        metric_name: str,
        start: datetime,
        end: datetime,
        interval: str = '1s',
        aggregation: str = 'mean'
    ) -> list[MetricPoint]:
        # Query InfluxDB
        pass
    
    async def start_collection(self, card: Card):
        # Begin background collection for real-time card
        pass
```

#### Streaming Service (WebSocket)
```python
class StreamingService:
    """
    Manages WebSocket connections for real-time updates.
    Uses Redis pub/sub for multi-instance scaling.
    """
    
    async def subscribe_to_screen(
        self,
        screen_id: str,
        websocket: WebSocket
    ):
        # Subscribe to Redis channel
        # Stream card updates to client
        pass
```

### 6.3 Database Schema

```sql
-- Screens table
CREATE TABLE screens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    layout_config JSONB NOT NULL DEFAULT '{}',
    refresh_rate INTEGER DEFAULT 5000, -- milliseconds
    theme VARCHAR(50) DEFAULT 'dark',
    access_level VARCHAR(50) DEFAULT 'viewer',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Cards table
CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    screen_id UUID REFERENCES screens(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255),
    position_x INTEGER NOT NULL,
    position_y INTEGER NOT NULL,
    width INTEGER NOT NULL DEFAULT 4,
    height INTEGER NOT NULL DEFAULT 4,
    config JSONB NOT NULL DEFAULT '{}',
    data_source JSONB NOT NULL DEFAULT '{}',
    refresh_rate INTEGER, -- Override screen default
    created_at TIMESTAMP DEFAULT NOW()
);

-- Users and RBAC
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) DEFAULT 'viewer', -- viewer, operator, admin
    hashed_password VARCHAR(255),
    is_active BOOLEAN DEFAULT true
);

-- Audit log for command execution
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    command TEXT NOT NULL,
    args JSONB,
    exit_code INTEGER,
    output TEXT,
    executed_at TIMESTAMP DEFAULT NOW(),
    duration_ms INTEGER
);

-- Time-series metrics stored in InfluxDB (not SQL)
-- measurement: network_io, fields: bytes_sent, bytes_recv
-- measurement: cpu_usage, fields: user, system, idle
```

---

## 7. FRONTEND IMPLEMENTATION

### 7.1 Component Hierarchy

```
App
├── AuthProvider
│   └── LoginScreen / Dashboard
├── Dashboard (Authenticated)
│   ├── Header
│   │   ├── ScreenSelector (dropdown)
│   │   ├── GlobalActions (add screen, settings)
│   │   └── UserMenu
│   ├── Sidebar (conditional)
│   │   └── CardLibrary (draggable card types)
│   ├── GridCanvas
│   │   └── ResponsiveGridLayout
│   │       └── CardWrapper (per card)
│   │           ├── CardHeader (title, controls)
│   │           ├── CardContent
│   │           │   └── DynamicCardComponent
│   │           │       ├── GaugeCard
│   │           │       ├── LineChartCard
│   │           │       ├── TableCard
│   │           │       ├── CommandCard
│   │           │       └── ...
│   │           └── CardFooter (timestamp, status)
│   └── Modals
│       ├── CardConfigModal
│       ├── ScreenSettingsModal
│       └── CommandConfirmationModal
└── WebSocketManager (global connection)
```

### 7.2 State Management (Redux)

```typescript
// Store slices
interface RootState {
  auth: {
    user: User | null;
    token: string | null;
  };
  screens: {
    list: Screen[];
    currentScreen: Screen | null;
    isLoading: boolean;
  };
  cards: {
    byScreen: Record<string, Card[]>;
    data: Record<string, any>; // Cached card data
    loading: Record<string, boolean>;
  };
  metrics: {
    history: Record<string, MetricPoint[]>;
    realtime: Record<string, MetricPoint>; // Latest values
  };
  websocket: {
    connected: boolean;
    subscriptions: string[]; // Screen IDs
  };
}

// Actions
- screens/fetchAll
- screens/setCurrent
- screens/createScreen
- cards/updateLayout
- cards/updateConfig
- cards/receiveData
- metrics/fetchHistory
- ws/connect
- ws/subscribe
```

### 7.3 Card Component Example (Gauge)

```typescript
// components/cards/GaugeCard.tsx
import { useGaugeConfig } from '@/hooks/useCardConfig';
import { useRealtimeMetric } from '@/hooks/useMetrics';
import { CanvasGauge } from '@/components/visualizations';

interface GaugeCardProps {
  cardId: string;
  config: GaugeConfig;
  dataSource: DataSource;
}

export const GaugeCard: React.FC<GaugeCardProps> = ({
  cardId,
  config,
  dataSource
}) => {
  const { value, loading, error } = useRealtimeMetric(
    dataSource,
    cardId
  );
  
  return (
    <div className="gauge-card">
      <CanvasGauge
        value={value}
        min={config.min}
        max={config.max}
        units={config.units}
        thresholds={config.thresholds}
        needleColor={config.needleColor}
        showDigital={config.digitalDisplay}
        decimals={config.decimals}
        isLoading={loading}
      />
      {error && <ErrorBadge message={error.message} />}
    </div>
  );
};
```

### 7.4 WebSocket Hook

```typescript
// hooks/useWebSocket.ts
export const useScreenWebSocket = (screenId: string) => {
  const dispatch = useDispatch();
  const [connected, setConnected] = useState(false);
  
  useEffect(() => {
    const ws = new WebSocket(`wss://api/netdash/ws/screens/${screenId}`);
    
    ws.onopen = () => setConnected(true);
    ws.onmessage = (event) => {
      const message: WSMessage = JSON.parse(event.data);
      
      switch (message.type) {
        case 'card_update':
          dispatch(cardsActions.receiveData({
            cardId: message.cardId,
            data: message.payload
          }));
          break;
        case 'metric_batch':
          dispatch(metricsActions.receiveBatch(message.payload));
          break;
      }
    };
    
    return () => ws.close();
  }, [screenId, dispatch]);
  
  return { connected };
};
```

---

## 8. SECURITY ARCHITECTURE

### 8.1 Authentication & Authorization

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────→│  JWT Auth   │────→│   RBAC      │
│             │     │   (HS256)   │     │ Middleware  │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                         ┌─────────────────────┼─────────────────────┐
                         ↓                     ↓                     ↓
                   ┌──────────┐         ┌──────────┐         ┌──────────┐
                   │  VIEWER  │         │ OPERATOR │         │  ADMIN   │
                   │          │         │          │         │          │
                   │ - View   │         │ - View   │         │ - View   │
                   │ - Export │         │ - Execute│         │ - Execute│
                   │          │         │   approved│        │ - Modify │
                   │          │         │   commands│        │ - Create │
                   │          │         │          │         │ - Delete │
                   └──────────┘         └──────────┘         └──────────┘
```

### 8.2 Command Sandbox

```python
class CommandSandbox:
    """
    Sandboxed command execution with multiple security layers:
    1. Whitelist validation (command + args)
    2. Path restrictions (no /etc, /root access)
    3. Timeout enforcement (kill after N seconds)
    4. Resource limits (CPU, memory)
    5. Output size limits (prevent DoS)
    6. Audit logging
    """
    
    RESTRICTED_PATHS = ['/etc/shadow', '/root', '/var/lib/private']
    MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB
    
    async def execute_sandboxed(
        self,
        command: str,
        args: list,
        timeout: int = 30
    ) -> SafeResult:
        # Run in isolated subprocess with resource limits
        # Use systemd-run or firejail if available
        # Validate no restricted paths in args
        # Capture output with size limit
        pass
```

### 8.3 Network Isolation

- Backend runs with minimal privileges
- Commands requiring elevated permissions use sudo with explicit whitelist
- Database credentials isolated in environment variables
- CORS restricted to dashboard origin only
- Rate limiting on API endpoints

---

## 9. DEPLOYMENT ARCHITECTURE

### 9.1 Docker Compose (Development)

```yaml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src
      
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///data/netdash.db
      - REDIS_URL=redis://redis:6379
      - INFLUX_URL=http://influx:8086
    volumes:
      - /var/log:/host/logs:ro
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    
  redis:
    image: redis:7-alpine
    
  influxdb:
    image: influxdb:2.0
    environment:
      - INFLUXDB_HTTP_AUTH_ENABLED=false
      - INFLUXDB_DB=netdash
```

### 9.2 Kubernetes (Production)

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: netdash-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: backend
        image: netdash/backend:v4.0
        securityContext:
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        envFrom:
        - secretRef:
            name: netdash-secrets
---
# For privileged monitoring, use DaemonSet on host network
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: netdash-node-exporter
spec:
  template:
    spec:
      hostNetwork: true
      containers:
      - name: node-agent
        image: netdash/node-agent:v4.0
        securityContext:
          privileged: true  # Required for network monitoring
```

---

## 10. IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-2)
- [ ] FastAPI backend setup with FastAPI
- [ ] SQLAlchemy models and Alembic migrations
- [ ] Basic JWT authentication
- [ ] Docker compose environment
- [ ] React frontend scaffolding (Vite + TypeScript)

### Phase 2: Core Dashboard (Weeks 3-4)
- [ ] Grid layout system (react-grid-layout)
- [ ] Card wrapper component
- [ ] Screen CRUD API
- [ ] Basic card types (stat, table)
- [ ] WebSocket connection manager

### Phase 3: Visualizations (Weeks 5-6)
- [ ] Gauge component (Canvas/WebGL)
- [ ] Line chart with time-series
- [ ] Real-time data streaming
- [ ] Chart.js or Recharts integration
- [ ] Dark/light theme system

### Phase 4: Metrics Engine (Weeks 7-8)
- [ ] InfluxDB integration
- [ ] Metrics collection agents
- [ ] Network metrics (ss, ping, nmap)
- [ ] System metrics (CPU, memory, disk)
- [ ] Historical data queries

### Phase 5: Command System (Weeks 9-10)
- [ ] Command whitelist framework
- [ ] Sandboxed execution
- [ ] Terminal component
- [ ] Audit logging
- [ ] RBAC implementation

### Phase 6: Polish (Weeks 11-12)
- [ ] Screen templates (presets)
- [ ] Card configuration UI
- [ ] Import/export screens
- [ ] Alerting system
- [ ] Documentation

---

## 11. API REFERENCE

### Authentication
```bash
# Get token
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded
username=admin&password=secret

Response:
{
  "access_token": "eyJ0...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Screen Operations
```bash
# Create screen
POST /api/v1/screens
Authorization: Bearer ${TOKEN}
Content-Type: application/json

{
  "name": "Production Overview",
  "layout": {"cols": 12, "rowHeight": 50},
  "refreshRate": 5000,
  "theme": "dark"
}

# Add card to screen
POST /api/v1/screens/{id}/cards
{
  "type": "gauge",
  "title": "CPU Usage",
  "position": {"x": 0, "y": 0},
  "size": {"w": 4, "h": 4},
  "config": {
    "min": 0,
    "max": 100,
    "units": "%",
    "thresholds": [
      {"value": 70, "color": "#f0883e"},
      {"value": 90, "color": "#f85149"}
    ]
  },
  "dataSource": {
    "type": "metric",
    "config": {
      "metric": "cpu.usage.total",
      "interval": "1s"
    }
  }
}
```

### WebSocket Protocol
```javascript
// Connect
const ws = new WebSocket('wss://api/netdash/ws/screens/123?token=JWT');

// Subscribe to card updates
ws.send(JSON.stringify({
  action: 'subscribe',
  cards: ['card-1', 'card-2']
}));

// Receive updates
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  // { type: 'metric', cardId: 'card-1', value: 45.2, timestamp: '...' }
};
```

---

## 12. CONCLUSION

This re-architecture transforms NetDash from a simple tabbed interface into a **professional-grade System Control Center**. Key improvements:

1. **Flexibility:** Drag-and-drop dashboard with configurable cards
2. **Extensibility:** Plugin architecture for custom card types
3. **Performance:** WebSocket streaming + time-series database
4. **Security:** Sandboxed commands with RBAC
5. **Usability:** Modern React UI with professional visualization

The modular design allows incremental deployment, starting with basic metrics and expanding to full system control capabilities.

---

**Document Maintainers:** NetDash Architecture Team  
**Review Cycle:** Quarterly  
**License:** MIT
