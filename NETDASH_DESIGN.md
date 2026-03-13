# NetDash - Network & System Dashboard
## Comprehensive High-Level & Low-Level Design Document

---

## 1. EXECUTIVE SUMMARY

NetDash is re-architected as a modern, real-time Network and System Control Center featuring:
- **Dynamic Dashboard Builder**: Drag-and-drop screen creation with customizable cards
- **Real-time Metrics**: WebSocket-based live updates with gauges, charts, and heatmaps
- **Modular Architecture**: Plugin-based card system for extensibility
- **Security-First**: Sandboxed command execution with RBAC
- **Responsive UX**: Progressive Web App (PWA) with offline capability

---

## 2. HIGH-LEVEL ARCHITECTURE (HLA)

### 2.1 Architecture Pattern: Micro-Frontend + Microservices

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Dashboard   │  │   Screen     │  │   Card       │  │   Admin      │    │
│  │   Builder    │  │   Manager    │  │   Renderer   │  │   Panel      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     WebSocket Client (Socket.io)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY LAYER                                 │
│         (Nginx / Traefik - Rate Limiting, SSL Termination, Auth)            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│   REST API        │    │  WebSocket        │    │   GraphQL         │
│   (FastAPI)       │    │  Gateway          │    │   (Optional)      │
│                   │    │  (Socket.io)      │    │                   │
└───────────────────┘    └───────────────────┘    └───────────────────┘
            │                         │                         │
            └─────────────────────────┼─────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SERVICE LAYER (Microservices)                     │
│                                                                             │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────┐ │
│  │ Metrics        │ │ Command        │ │ Screen         │ │ Card         │ │
│  │ Collector      │ │ Executor       │ │ Management     │ │ Registry     │ │
│  │ Service        │ │ Service        │ │ Service        │ │ Service      │ │
│  └────────────────┘ └────────────────┘ └────────────────┘ └──────────────┘ │
│                                                                             │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────┐ │
│  │ Discovery      │ │ Alert          │ │ User           │ │ Plugin       │ │
│  │ Engine         │ │ Manager        │ │ Management     │ │ Manager      │ │
│  └────────────────┘ └────────────────┘ └────────────────┘ └──────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│   Time-Series     │    │   Job Queue       │    │   Configuration   │
│   Database        │    │   (Redis/Rabbit)  │    │   Store (etcd)    │
│   (InfluxDB/Prometheus)│                   │    │                   │
└───────────────────┘    └───────────────────┘    └───────────────────┘
```

### 2.2 Core Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | React 18 + TypeScript + Vite | SPA with component-based architecture |
| **State Management** | Zustand + React Query | Client state and server cache |
| **Charts/Gauges** | D3.js + Recharts + Custom SVG | Data visualization |
| **Backend API** | FastAPI (Python 3.11+) | Async REST API with auto-generated OpenAPI |
| **WebSocket** | Socket.io / python-socketio | Real-time bidirectional communication |
| **Metrics Storage** | InfluxDB 2.x | Time-series metrics data |
| **Job Queue** | Redis + Celery | Async task processing |
| **Authentication** | JWT + OAuth2 | Secure access control |

---

## 3. LOW-LEVEL DESIGN (LLD)

### 3.1 Data Models

#### 3.1.1 Screen (Dashboard Configuration)
```json
{
  "id": "uuid",
  "name": "Network Overview",
  "description": "Main network monitoring dashboard",
  "layout": {
    "type": "grid",
    "columns": 12,
    "rowHeight": 80,
    "gap": 16
  },
  "cards": [
    {
      "id": "card-uuid",
      "type": "system_metrics",
      "position": {"x": 0, "y": 0, "w": 4, "h": 3},
      "configuration": {
        "refreshInterval": 5000,
        "metrics": ["cpu", "memory", "disk"],
        "displayMode": "gauge"
      },
      "styling": {
        "background": "#1e1e2e",
        "borderColor": "#313244",
        "titleColor": "#cdd6f4"
      }
    }
  ],
  "permissions": {
    "view": ["admin", "operator"],
    "edit": ["admin"]
  },
  "isDefault": true,
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T14:20:00Z"
}
```

#### 3.1.2 Card Types Registry
```json
{
  "cardTypes": [
    {
      "id": "system_metrics",
      "name": "System Metrics",
      "category": "System",
      "icon": "Cpu",
      "description": "CPU, Memory, Disk usage gauges",
      "dataSource": {
        "type": "command",
        "commands": ["vmstat", "df", "free"],
        "parser": "system_metrics_parser"
      },
      "configSchema": {
        "properties": {
          "metrics": {
            "type": "array",
            "enum": ["cpu", "memory", "disk", "load", "uptime"]
          },
          "displayMode": {
            "type": "string",
            "enum": ["gauge", "chart", "text", "sparkline"]
          }
        }
      }
    },
    {
      "id": "network_traffic",
      "name": "Network Traffic",
      "category": "Network",
      "icon": "Activity",
      "dataSource": {
        "type": "command",
        "commands": ["ifstat", "ss", "/proc/net/dev"],
        "parser": "network_traffic_parser"
      }
    },
    {
      "id": "interface_status",
      "name": "Interface Status",
      "category": "Network",
      "icon": "Ethernet",
      "dataSource": {
        "type": "command",
        "commands": ["ip", "ethtool"],
        "parser": "interface_parser"
      }
    },
    {
      "id": "connection_table",
      "name": "Active Connections",
      "category": "Network",
      "icon": "Globe",
      "dataSource": {
        "type": "command",
        "commands": ["ss", "netstat"],
        "parser": "connections_parser"
      }
    },
    {
      "id": "port_scanner",
      "name": "Port Scanner",
      "category": "Tools",
      "icon": "Search",
      "isInteractive": true,
      "dataSource": {
        "type": "async_job",
        "commands": ["nmap", "masscan"],
        "parser": "port_scan_parser"
      }
    },
    {
      "id": "host_discovery",
      "name": "Host Discovery",
      "category": "Tools",
      "icon": "Radar",
      "isInteractive": true,
      "dataSource": {
        "type": "async_job",
        "commands": ["nmap", "arp-scan"],
        "parser": "host_discovery_parser"
      }
    },
    {
      "id": "dns_tool",
      "name": "DNS Lookup",
      "category": "Tools",
      "icon": "Globe2",
      "isInteractive": true,
      "dataSource": {
        "type": "command",
        "commands": ["dig", "nslookup", "host"],
        "parser": "dns_parser"
      }
    },
    {
      "id": "log_viewer",
      "name": "System Logs",
      "category": "System",
      "icon": "FileText",
      "dataSource": {
        "type": "file",
        "paths": ["/var/log/syslog", "/var/log/messages"],
        "parser": "log_parser"
      }
    },
    {
      "id": "custom_command",
      "name": "Custom Command",
      "category": "Advanced",
      "icon": "Terminal",
      "isInteractive": true,
      "dataSource": {
        "type": "custom",
        "whitelist": ["ping", "traceroute", "curl", "whois"],
        "blacklist": ["rm", "dd", "mkfs", "shutdown"]
      }
    }
  ]
}
```

#### 3.1.3 Metric Data Point
```json
{
  "timestamp": "2024-01-15T14:30:45.123Z",
  "source": "system_metrics_card",
  "metric": "cpu_usage",
  "value": 45.2,
  "unit": "percent",
  "tags": {
    "host": "server-01",
    "core": "all",
    "screen": "overview"
  }
}
```

#### 3.1.4 Async Job
```json
{
  "id": "job-uuid",
  "type": "nmap_scan",
  "status": "running",
  "progress": 45,
  "target": "192.168.1.0/24",
  "parameters": {
    "ports": "1-1000",
    "scanType": "syn"
  },
  "createdAt": "2024-01-15T14:30:00Z",
  "startedAt": "2024-01-15T14:30:02Z",
  "completedAt": null,
  "result": null,
  "error": null
}
```

---

### 3.2 API Endpoints

#### Screen Management
```
GET    /api/v1/screens                    # List all screens
POST   /api/v1/screens                    # Create new screen
GET    /api/v1/screens/{id}               # Get screen by ID
PUT    /api/v1/screens/{id}               # Update screen
DELETE /api/v1/screens/{id}               # Delete screen
POST   /api/v1/screens/{id}/duplicate     # Clone screen
PUT    /api/v1/screens/{id}/layout        # Update card positions
```

#### Card Operations
```
GET    /api/v1/card-types                 # List available card types
GET    /api/v1/card-types/{id}/schema     # Get card config schema
POST   /api/v1/screens/{id}/cards         # Add card to screen
PUT    /api/v1/screens/{id}/cards/{cid}   # Update card config
DELETE /api/v1/screens/{id}/cards/{cid}   # Remove card
POST   /api/v1/cards/{id}/refresh         # Force data refresh
```

#### Real-time Data
```
WebSocket: /ws/metrics                    # Subscribe to metric streams
WebSocket: /ws/jobs                     # Job progress updates
WebSocket: /ws/alerts                   # Alert notifications

GET    /api/v1/metrics?card={id}&since={ts}  # Historical metrics
GET    /api/v1/metrics/current            # Current snapshot
```

#### Command Execution
```
POST   /api/v1/commands/execute          # Execute whitelisted command
POST   /api/v1/commands/jobs            # Start async command job
GET    /api/v1/commands/jobs/{id}        # Get job status
POST   /api/v1/commands/jobs/{id}/cancel  # Cancel running job
```

---

### 3.3 Component Designs

#### 3.3.1 Card Component Hierarchy
```
Screen (Container)
├── Header (Title, Actions, Time Range Selector)
└── GridLayout (react-grid-layout)
    └── CardWrapper
        ├── CardHeader (Title, Menu, Drag Handle)
        ├── CardContent
        │   ├── LoadingState
        │   ├── ErrorState
        │   └── DataDisplay
        │       ├── GaugeCard (Circular/Linear gauges)
        │       ├── ChartCard (Line/Bar/Area charts)
        │       ├── TableCard (Sortable, filterable)
        │       ├── TextCard (Logs, plain text)
        │       ├── MapCard (Network topology)
        │       └── InteractiveCard (Forms, scan results)
        └── CardFooter (Last updated, Refresh button)
```

#### 3.3.2 Gauge Components
```typescript
// Gauge Types
interface GaugeProps {
  value: number;
  min?: number;
  max?: number;
  unit?: string;
  thresholds?: {
    warning: number;
    critical: number;
  };
  colors?: {
    normal: string;
    warning: string;
    critical: string;
  };
  animation?: boolean;
}

// Circular Gauge
<CircularGauge
  value={75}
  max={100}
  unit="%"
  thresholds={{ warning: 60, critical: 85 }}
  size={200}
  showValue={true}
/>

// Linear Gauge
<LinearGauge
  value={45}
  max={100}
  orientation="horizontal"
  segments={[
    { start: 0, end: 60, color: '#2ecc71' },
    { start: 60, end: 85, color: '#f39c12' },
    { start: 85, end: 100, color: '#e74c3c' }
  ]}
/>
```

#### 3.3.3 Chart Components
```typescript
// Real-time Line Chart
<RealtimeChart
  data={metricStream}
  type="area"
  xAxis="timestamp"
  yAxis="value"
  smoothing={true}
  showGrid={true}
  timeRange="1h"
  refreshInterval={5000}
/>

// Heatmap
<NetworkHeatmap
  nodes={discoveredHosts}
  connections={activeConnections}
  layout="force-directed"
/>

// Multi-metric Chart
<MultiMetricChart
  metrics={['cpu', 'memory', 'disk']}
  correlationMode={true}
/>
```

---

### 3.4 Backend Services

#### 3.4.1 Metrics Collector Service
```python
class MetricsCollector:
    """
    Continuously collects system and network metrics
    Streams to WebSocket clients and stores in InfluxDB
    """
    
    collection_strategies = {
        'system': {
            'interval': 5,  # seconds
            'commands': {
                'cpu': 'cat /proc/stat',
                'memory': 'free -m',
                'disk': 'df -h',
                'load': 'uptime'
            },
            'parsers': SystemMetricParsers
        },
        'network': {
            'interval': 2,
            'commands': {
                'interfaces': 'ip -s link',
                'connections': 'ss -tuln',
                'routes': 'ip route',
                'traffic': 'cat /proc/net/dev'
            },
            'parsers': NetworkMetricParsers
        }
    }
    
    async def collect_and_broadcast(self):
        while True:
            for category, config in self.collection_strategies.items():
                metrics = await self.execute_commands(config['commands'])
                parsed = config['parsers'].parse(metrics)
                
                # Store to database
                await self.influxdb.write(parsed)
                
                # Broadcast to subscribers
                await self.websocket.broadcast({
                    'category': category,
                    'metrics': parsed,
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            await asyncio.sleep(config['interval'])
```

#### 3.4.2 Command Executor Service
```python
class CommandExecutor:
    """
    Secure command execution with sandboxing
    """
    
    ALLOWED_COMMANDS = {
        'ping': {
            'cmd': 'ping',
            'args': ['-c', '{count}', '{target}'],
            'timeout': 10,
            'requires_target': True,
            'target_validator': ip_or_hostname_validator
        },
        'nmap': {
            'cmd': 'nmap',
            'args': ['-p', '{ports}', '-sV', '{target}'],
            'timeout': 300,
            'requires_root': True,
            'async': True
        },
        'ss': {
            'cmd': 'ss',
            'args': ['-tuln'],
            'timeout': 5
        }
    }
    
    async def execute(self, command_key: str, params: dict, user: User):
        # RBAC check
        if not self.has_permission(user, command_key):
            raise PermissionError(f"User {user.id} cannot execute {command_key}")
        
        cmd_config = self.ALLOWED_COMMANDS[command_key]
        
        # Validate parameters
        if cmd_config.get('requires_target'):
            if not cmd_config['target_validator'](params.get('target')):
                raise ValueError("Invalid target")
        
        # Build command
        cmd = self.build_command(cmd_config, params)
        
        # Execute in sandbox
        if cmd_config.get('async'):
            return await self.execute_async(cmd, cmd_config)
        else:
            return await self.execute_sync(cmd, cmd_config)
    
    async def execute_async(self, cmd, config):
        job_id = str(uuid.uuid4())
        
        # Queue job
        await self.redis.publish('jobs', {
            'id': job_id,
            'command': cmd,
            'timeout': config['timeout']
        })
        
        return {'job_id': job_id, 'status': 'queued'}
```

#### 3.4.3 Card Registry Service
```python
class CardRegistry:
    """
    Manages available card types and their configurations
    Supports dynamic plugin loading
    """
    
    def __init__(self):
        self.cards: Dict[str, CardType] = {}
        self.load_builtin_cards()
        self.load_plugins()
    
    def load_builtin_cards(self):
        """Load all built-in card types"""
        builtin_cards = [
            SystemMetricsCard,
            NetworkTrafficCard,
            InterfaceStatusCard,
            ConnectionTableCard,
            PortScannerCard,
            HostDiscoveryCard,
            DNSToolCard,
            LogViewerCard
        ]
        
        for card_class in builtin_cards:
            instance = card_class()
            self.cards[instance.id] = instance
    
    def load_plugins(self):
        """Load custom card plugins from /plugins directory"""
        plugin_dir = Path(__file__).parent / 'plugins' / 'cards'
        
        for plugin_file in plugin_dir.glob('*.py'):
            if plugin_file.name.startswith('_'):
                continue
            
            spec = importlib.util.spec_from_file_location(
                plugin_file.stem, plugin_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, 'CardDefinition'):
                card = module.CardDefinition()
                self.cards[card.id] = card
    
    def get_card_schema(self, card_id: str) -> dict:
        """Return JSON schema for card configuration"""
        card = self.cards.get(card_id)
        return card.get_configuration_schema()
    
    def create_card_instance(self, card_id: str, config: dict) -> CardInstance:
        """Instantiate a card with given configuration"""
        card_type = self.cards.get(card_id)
        return CardInstance(type=card_type, config=config)
```

---

### 3.5 Frontend Architecture

#### 3.5.1 State Management
```typescript
// Zustand stores
interface DashboardStore {
  // Screen management
  screens: Screen[];
  activeScreen: string | null;
  createScreen: (screen: ScreenInput) => Promise<Screen>;
  updateScreen: (id: string, updates: Partial<Screen>) => void;
  deleteScreen: (id: string) => void;
  setActiveScreen: (id: string) => void;
  
  // Card management
  addCard: (screenId: string, card: CardInput) => void;
  updateCard: (screenId: string, cardId: string, updates: Partial<Card>) => void;
  removeCard: (screenId: string, cardId: string) => void;
  updateCardLayout: (screenId: string, layout: Layout[]) => void;
  
  // Real-time data
  metrics: Map<string, Metric[]>;
  subscribeToMetric: (cardId: string, metric: string) => void;
  unsubscribeFromMetric: (cardId: string, metric: string) => void;
  updateMetric: (metric: Metric) => void;
}

interface JobStore {
  jobs: Map<string, Job>;
  activeJobs: string[];
  startJob: (type: string, params: any) => Promise<string>;
  cancelJob: (jobId: string) => Promise<void>;
  updateJobProgress: (jobId: string, progress: number) => void;
  completeJob: (jobId: string, result: any) => void;
  failJob: (jobId: string, error: string) => void;
}
```

#### 3.5.2 Component System
```typescript
// Card Registry
const CardComponents: Record<string, LazyExoticComponent<FC<CardProps>>> = {
  system_metrics: lazy(() => import('./cards/SystemMetricsCard')),
  network_traffic: lazy(() => import('./cards/NetworkTrafficCard')),
  interface_status: lazy(() => import('./cards/InterfaceStatusCard')),
  connection_table: lazy(() => import('./cards/ConnectionTableCard')),
  port_scanner: lazy(() => import('./cards/PortScannerCard')),
  host_discovery: lazy(() => import('./cards/HostDiscoveryCard')),
  dns_tool: lazy(() => import('./cards/DNSToolCard')),
  log_viewer: lazy(() => import('./cards/LogViewerCard')),
};

// Dynamic Card Renderer
const DynamicCard: FC<{ card: Card }> = ({ card }) => {
  const CardComponent = CardComponents[card.type];
  const { data, isLoading, error, refresh } = useCardData(card);
  
  if (!CardComponent) {
    return <UnknownCardType type={card.type} />;
  }
  
  return (
    <ErrorBoundary fallback={<CardError card={card} />}>
      <Suspense fallback={<CardSkeleton />}>
        <CardWrapper 
          title={card.title}
          onRefresh={refresh}
          isLoading={isLoading}
        >
          <CardComponent 
            configuration={card.configuration}
            data={data}
            error={error}
          />
        </CardWrapper>
      </Suspense>
    </ErrorBoundary>
  );
};
```

#### 3.5.3 Real-time Data Hook
```typescript
// useRealtimeMetrics hook
const useRealtimeMetrics = (
  cardId: string,
  metrics: string[],
  options: RealtimeOptions = {}
) => {
  const socket = useSocket();
  const [data, setData] = useState<Map<string, Metric[]>>(new Map());
  const { interval = 5000, enabled = true } = options;
  
  useEffect(() => {
    if (!enabled || !socket) return;
    
    const handlers: (() => void)[] = [];
    
    metrics.forEach(metric => {
      const channel = `card:${cardId}:metric:${metric}`;
      
      const handler = (payload: MetricPayload) => {
        setData(prev => {
          const next = new Map(prev);
          const existing = next.get(metric) || [];
          next.set(metric, [...existing.slice(-100), payload]);
          return next;
        });
      };
      
      socket.on(channel, handler);
      socket.emit('subscribe', { channel, interval });
      
      handlers.push(() => {
        socket.off(channel, handler);
        socket.emit('unsubscribe', { channel });
      });
    });
    
    return () => {
      handlers.forEach(cleanup => cleanup());
    };
  }, [cardId, metrics.join(','), socket, enabled]);
  
  return {
    data,
    latest: metrics.reduce((acc, m) => {
      const arr = data.get(m);
      acc[m] = arr?.[arr.length - 1]?.value ?? null;
      return acc;
    }, {} as Record<string, number>)
  };
};
```

---

### 3.6 Database Schema

#### 3.6.1 PostgreSQL (Metadata)
```sql
-- Screens table
CREATE TABLE screens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    layout_config JSONB NOT NULL DEFAULT '{}',
    is_default BOOLEAN DEFAULT false,
    is_public BOOLEAN DEFAULT false,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cards table
CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    screen_id UUID REFERENCES screens(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL,
    title VARCHAR(255),
    position JSONB NOT NULL, -- {x, y, w, h}
    configuration JSONB NOT NULL DEFAULT '{}',
    styling JSONB DEFAULT '{}',
    refresh_interval INTEGER DEFAULT 5000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Card types registry
CREATE TABLE card_types (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    icon VARCHAR(100),
    is_interactive BOOLEAN DEFAULT false,
    config_schema JSONB NOT NULL,
    data_source_config JSONB NOT NULL
);

-- Jobs table
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    progress INTEGER DEFAULT 0,
    target VARCHAR(500),
    parameters JSONB DEFAULT '{}',
    result JSONB,
    error TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users and permissions
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) DEFAULT 'operator',
    permissions JSONB DEFAULT '[]',
    last_login TIMESTAMP WITH TIME ZONE
);

-- Screen permissions
CREATE TABLE screen_permissions (
    screen_id UUID REFERENCES screens(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    permission VARCHAR(50) NOT NULL, -- 'view', 'edit', 'admin'
    PRIMARY KEY (screen_id, user_id)
);
```

#### 3.6.2 InfluxDB (Time-series Metrics)
```
Bucket: netdash_metrics

Measurements:
- system_metrics: cpu_usage, memory_usage, disk_usage, load_average
  Tags: host, core, mount_point
  
- network_metrics: bytes_in, bytes_out, packets_in, packets_out, errors
  Tags: interface, host
  
- connection_metrics: active_connections, listening_ports
  Tags: protocol, state, host
  
- card_metrics: render_time, data_fetch_time, error_rate
  Tags: card_id, card_type, screen_id
```

---

### 3.7 Security Design

#### 3.7.1 Command Whitelist
```yaml
# security/commands.yml
allowed_commands:
  network_discovery:
    - name: nmap
      args_allowed: ['-sn', '-sS', '-sT', '-sU', '-sV', '-O', '-p', '--top-ports', '-T']
      requires_root: true
      max_duration: 300
    - name: arp-scan
      args_allowed: ['--localnet', '-I', '-q']
      requires_root: true
      
  system_info:
    - name: ip
      args_allowed: ['-s', 'link', 'show', '-j', 'addr', 'route', 'neigh']
      requires_root: false
    - name: ss
      args_allowed: ['-tuln', '-tunap', '-s']
      requires_root: false
      
  diagnostics:
    - name: ping
      args_allowed: ['-c', '-i', '-W']
      max_duration: 10
    - name: traceroute
      args_allowed: ['-m', '-T', '-U']
      max_duration: 60
      
blocked_patterns:
  - 'rm\s+-rf'
  - '>\s*/dev/[sh]da'
  - 'dd\s+if=.*of=/dev'
  - 'mkfs\.'
  - 'shutdown'
  - 'reboot'
  - 'init\s+0'
```

#### 3.7.2 RBAC Model
```
Roles:
├── admin
│   ├── screens: [create, read, update, delete, manage]
│   ├── cards: [create, read, update, delete]
│   ├── commands: [execute_all, whitelist_manage]
│   ├── jobs: [view_all, cancel_any]
│   └── users: [manage]
│
├── operator
│   ├── screens: [read, create_personal]
│   ├── cards: [create, read, update_own]
│   ├── commands: [execute_basic]
│   └── jobs: [view_own, cancel_own]
│
└── viewer
    ├── screens: [read_public]
    ├── cards: [read]
    └── commands: []
```

---

### 3.8 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Kubernetes Cluster                       │
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   Ingress       │    │   Ingress       │    │  Ingress    │ │
│  │   Controller    │    │   Controller    │    │  Controller │ │
│  │   (nginx)       │    │   (nginx)       │    │             │ │
│  └────────┬────────┘    └────────┬────────┘    └──────┬──────┘ │
│           └──────────────────────┴───────────────────┘         │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Services                              │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │  │
│  │  │  Frontend    │ │  API         │ │  WebSocket       │ │  │
│  │  │  (3 replicas)│ │  (3 replicas)│ │  (2 replicas)    │ │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────┘ │  │
│  │                                                            │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │  │
│  │  │  Metrics     │ │  Command     │ │  Job Worker      │ │  │
│  │  │  Collector   │ │  Executor    │ │  (Celery)        │ │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Data Layer                            │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │  │
│  │  │  PostgreSQL  │ │  Redis       │ │  InfluxDB        │ │  │
│  │  │  (Primary+   │ │  (Cluster)   │ │  (Time-series)   │ │  │
│  │  │   Replica)   │ │              │ │                  │ │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. USER INTERFACE SPECIFICATIONS

### 4.1 Dashboard Builder Interface

```
┌─────────────────────────────────────────────────────────────────┐
│  NetDash                                    [New Screen] [Profile]│
├─────────────────────────────────────────────────────────────────┤
│  Screens: [Overview ▼] [Network] [System] [+]                    │
├──────────┬──────────────────────────────────────────────────────┤
│          │                                                      │
│  CARD    │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  PALETTE │  │  CPU         │  │  Network     │  │          │ │
│          │  │  ┌────────┐  │  │  Traffic     │  │  Memory  │ │
│  ────────│  │  │  45%   │  │  │  ▃▄▆▇▃     │  │  ┌────┐  │ │
│  System  │  │  │  [====│  │  │  12 MB/s   │  │  │72% │  │ │
│  □ CPU   │  │  └────────┘  │  └──────────────┘  │  └────┘  │ │
│  □ Mem   │  │              │  ┌──────────────┐  └──────────┘ │
│  □ Disk  │  └──────────────┘  │  Connections │                │
│  □ Load  │                    │  ─────────── │                │
│          │  ┌──────────────┐  │  192.168.1.5 │  ┌──────────┐ │
│  Network │  │  Interface   │  │  10.0.0.1   │  │  Port    │ │
│  □ Iface │  │  Status      │  │  ...        │  │  Scanner │ │
│  □ Conn  │  │  [  eth0  ]  │  └──────────────┘  │  [==> ]  │ │
│  □ ARP   │  │  UP 1Gbps    │                    └──────────┘ │
│  □ Route │  └──────────────┘                                    │
│          │                                                      │
│  Tools   │  [Edit Layout] [Add Card] [Save] [Export]         │
│  □ Scan  │                                                      │
│  □ DNS   │                                                      │
│  □ Ping  │                                                      │
│  □ Trace │                                                      │
│          │                                                      │
└──────────┴──────────────────────────────────────────────────────┘
```

### 4.2 Card Configuration Modal

```
┌─────────────────────────────────────────────┐
│  Configure: System Metrics Card        [X]  │
├─────────────────────────────────────────────┤
│                                             │
│  Display Settings                           │
│  ┌─────────────────────────────────────┐   │
│  │ Title: [System Performance      ]  │   │
│  │                                     │   │
│  │ Metrics: [☑] CPU  [☑] Memory       │   │
│  │          [☑] Disk [ ] Load         │   │
│  │                                     │   │
│  │ Visualization: (•) Gauges          │   │
│  │                ( ) Charts          │   │
│  │                ( ) Sparklines       │   │
│  │                                     │   │
│  │ Refresh Interval: [ 5 ] seconds    │   │
│  │                                     │   │
│  │ Thresholds:                          │   │
│  │  Warning: [ 70 ]%  Critical: [ 85 ]% │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  [Cancel]                    [Save Changes] │
└─────────────────────────────────────────────┘
```

---

## 5. IMPLEMENTATION ROADMAP

### Phase 1: Core Foundation (Weeks 1-2)
- [ ] Set up FastAPI backend with WebSocket support
- [ ] Implement command executor with security whitelist
- [ ] Create InfluxDB schema and metrics collectors
- [ ] Build React frontend skeleton with routing

### Phase 2: Dashboard Engine (Weeks 3-4)
- [ ] Implement react-grid-layout for card positioning
- [ ] Create card registry system
- [ ] Build basic card components (System, Network)
- [ ] Implement screen CRUD operations

### Phase 3: Visualization (Weeks 5-6)
- [ ] Integrate D3.js for custom gauges
- [ ] Build real-time chart components
- [ ] Implement metric streaming via WebSocket
- [ ] Create heatmap and topology views

### Phase 4: Advanced Tools (Weeks 7-8)
- [ ] Async job system with progress tracking
- [ ] Port scanner and host discovery cards
- [ ] DNS tools and network diagnostics
- [ ] Log viewer with search/filter

### Phase 5: Polish & Production (Weeks 9-10)
- [ ] Authentication and RBAC
- [ ] PWA capabilities (offline mode)
- [ ] Kubernetes deployment manifests
- [ ] Documentation and testing

---

## 6. TECHNOLOGY STACK SUMMARY

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React + TypeScript | 18.x |
| Build Tool | Vite | 5.x |
| Styling | Tailwind CSS + Headless UI | 3.x |
| Charts | D3.js + Recharts | 7.x / 2.x |
| State | Zustand + React Query | 4.x / 5.x |
| Backend | FastAPI | 0.104+ |
| WebSocket | python-socketio | 5.x |
| Database | PostgreSQL | 15+ |
| Time-series | InfluxDB | 2.7+ |
| Queue | Redis + Celery | 7.x / 5.x |
| Container | Docker + Kubernetes | - |

---

**Document Version:** 1.0  
**Last Updated:** 2024-01-15  
**Author:** Agent-oo1 Architecture Team
