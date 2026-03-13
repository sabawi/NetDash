#!/usr/bin/env python3
"""
NetDash v2.0 - Re-architected Network & System Dashboard
Features: Dynamic card-based dashboards, real-time WebSocket metrics,
customizable screens, gauges/charts, modular plugin architecture.
"""

import os
import re
import json
import asyncio
import sqlite3
import socket
import subprocess
import threading
import ipaddress
import uuid
import time
import psutil
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from collections import deque
from flask import Flask, render_template, jsonify, request, g
from flask_cors import CORS
from flask_sock import Sock
from functools import wraps

# ============================================
# CONFIGURATION
# ============================================

DATABASE_PATH = os.environ.get('NETDASH_DB', '/home/sabawi/Development/netdash/netdash.db')
MAX_HISTORY_POINTS = 100
WS_UPDATE_INTERVAL = 2  # seconds

# ============================================
# DATA MODELS
# ============================================

@dataclass
class Dashboard:
    """Dashboard configuration model."""
    id: str
    name: str
    description: str
    layout: str  # 'grid', 'list', 'split'
    created_at: str
    updated_at: str
    is_default: bool = False
    refresh_interval: int = 5  # seconds
    theme: str = 'dark'
    
    def to_dict(self):
        return asdict(self)

@dataclass
class Card:
    """Card/Widget configuration model."""
    id: str
    dashboard_id: str
    title: str
    card_type: str  # 'gauge', 'chart', 'table', 'text', 'sparkline', 'donut'
    data_source: str  # 'cpu', 'memory', 'network', 'disk', 'custom', 'ping', 'bandwidth'
    position_x: int
    position_y: int
    width: int  # grid units (1-12)
    height: int  # grid units (1-12)
    config: Dict[str, Any]  # type-specific config
    created_at: str
    updated_at: str
    
    def to_dict(self):
        result = asdict(self)
        result['config'] = json.loads(json.dumps(self.config))
        return result

@dataclass
class MetricData:
    """Real-time metric data point."""
    timestamp: float
    value: float
    label: str
    unit: str
    alert_level: str = 'normal'  # normal, warning, critical

# ============================================
# DATABASE LAYER
# ============================================

class Database:
    """SQLite database manager for dashboards and cards."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS dashboards (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    layout TEXT DEFAULT 'grid',
                    created_at TEXT,
                    updated_at TEXT,
                    is_default INTEGER DEFAULT 0,
                    refresh_interval INTEGER DEFAULT 5,
                    theme TEXT DEFAULT 'dark'
                );
                
                CREATE TABLE IF NOT EXISTS cards (
                    id TEXT PRIMARY KEY,
                    dashboard_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    card_type TEXT NOT NULL,
                    data_source TEXT NOT NULL,
                    position_x INTEGER DEFAULT 0,
                    position_y INTEGER DEFAULT 0,
                    width INTEGER DEFAULT 3,
                    height INTEGER DEFAULT 3,
                    config TEXT,  -- JSON
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (dashboard_id) REFERENCES dashboards(id) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS metrics_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_source TEXT,
                    timestamp REAL,
                    value REAL,
                    label TEXT,
                    unit TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_cards_dashboard ON cards(dashboard_id);
                CREATE INDEX IF NOT EXISTS idx_metrics_source ON metrics_history(data_source, timestamp);
            """)
            conn.commit()
            
            # Create default dashboard if none exists
            cursor = conn.execute("SELECT COUNT(*) FROM dashboards")
            if cursor.fetchone()[0] == 0:
                self._create_default_dashboards(conn)
    
    def _create_default_dashboards(self, conn):
        """Create sample dashboards with cards."""
        dash_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        
        conn.execute("""
            INSERT INTO dashboards (id, name, description, layout, created_at, updated_at, is_default, theme)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (dash_id, 'System Overview', 'Main system monitoring dashboard', 'grid', now, now, 1, 'dark'))
        
        # Add sample cards
        cards = [
            (str(uuid.uuid4())[:8], dash_id, 'CPU Usage', 'gauge', 'cpu', 0, 0, 3, 3, 
             json.dumps({'max': 100, 'thresholds': [60, 80, 95], 'colors': ['#4ade80', '#facc15', '#ef4444']}), now, now),
            (str(uuid.uuid4())[:8], dash_id, 'Memory Usage', 'gauge', 'memory', 3, 0, 3, 3,
             json.dumps({'max': 100, 'thresholds': [70, 85, 95], 'colors': ['#4ade80', '#facc15', '#ef4444']}), now, now),
            (str(uuid.uuid4())[:8], dash_id, 'Network Traffic', 'chart', 'network', 6, 0, 6, 4,
             json.dumps({'chart_type': 'line', 'show_legend': True, 'fill': True}), now, now),
            (str(uuid.uuid4())[:8], dash_id, 'Disk Usage', 'donut', 'disk', 0, 3, 3, 3,
             json.dumps({'show_percent': True}), now, now),
            (str(uuid.uuid4())[:8], dash_id, 'Active Connections', 'sparkline', 'connections', 3, 3, 3, 2,
             json.dumps({'color': '#60a5fa'}), now, now),
            (str(uuid.uuid4())[:8], dash_id, 'System Load', 'text', 'load', 6, 4, 3, 2,
             json.dumps({'format': 'float', 'prefix': 'Load: '}), now, now),
        ]
        
        conn.executemany("""
            INSERT INTO cards (id, dashboard_id, title, card_type, data_source, position_x, position_y, 
                             width, height, config, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, cards)
        
        # Network dashboard
        net_dash = str(uuid.uuid4())[:8]
        conn.execute("""
            INSERT INTO dashboards (id, name, description, layout, created_at, updated_at, theme)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (net_dash, 'Network Monitor', 'Network-specific monitoring', 'grid', now, now, 'dark'))
        
        net_cards = [
            (str(uuid.uuid4())[:8], net_dash, 'Interface Status', 'table', 'interfaces', 0, 0, 6, 4,
             json.dumps({'columns': ['name', 'ip', 'status', 'speed']}), now, now),
            (str(uuid.uuid4())[:8], net_dash, 'Bandwidth RX', 'gauge', 'bandwidth_rx', 6, 0, 3, 3,
             json.dumps({'unit': 'MB/s', 'max': 100}), now, now),
            (str(uuid.uuid4())[:8], net_dash, 'Bandwidth TX', 'gauge', 'bandwidth_tx', 9, 0, 3, 3,
             json.dumps({'unit': 'MB/s', 'max': 100}), now, now),
            (str(uuid.uuid4())[:8], net_dash, 'Ping Latency', 'chart', 'ping', 0, 4, 6, 3,
             json.dumps({'target': '8.8.8.8', 'chart_type': 'bar'}), now, now),
        ]
        
        conn.executemany("""
            INSERT INTO cards (id, dashboard_id, title, card_type, data_source, position_x, position_y, 
                             width, height, config, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, net_cards)
        
        conn.commit()
    
    def get_dashboards(self) -> List[Dashboard]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM dashboards ORDER BY created_at").fetchall()
            return [self._row_to_dashboard(r) for r in rows]
    
    def get_dashboard(self, dash_id: str) -> Optional[Dashboard]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM dashboards WHERE id = ?", (dash_id,)).fetchone()
            return self._row_to_dashboard(row) if row else None
    
    def create_dashboard(self, name: str, description: str = '', layout: str = 'grid') -> Dashboard:
        dash_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        dash = Dashboard(dash_id, name, description, layout, now, now)
        
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO dashboards (id, name, description, layout, created_at, updated_at, is_default, theme)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (dash.id, dash.name, dash.description, dash.layout, dash.created_at, dash.updated_at, 
                  int(dash.is_default), dash.theme))
            conn.commit()
        return dash
    
    def get_cards(self, dashboard_id: str) -> List[Card]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM cards WHERE dashboard_id = ? ORDER BY position_y, position_x", 
                (dashboard_id,)
            ).fetchall()
            return [self._row_to_card(r) for r in rows]
    
    def create_card(self, dashboard_id: str, title: str, card_type: str, data_source: str,
                    x: int, y: int, width: int, height: int, config: Dict) -> Card:
        card_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        card = Card(card_id, dashboard_id, title, card_type, data_source, x, y, width, height, config, now, now)
        
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO cards (id, dashboard_id, title, card_type, data_source, position_x, position_y,
                                 width, height, config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (card.id, card.dashboard_id, card.title, card.card_type, card.data_source,
                  card.position_x, card.position_y, card.width, card.height, 
                  json.dumps(card.config), card.created_at, card.updated_at))
            conn.commit()
        return card
    
    def update_card_position(self, card_id: str, x: int, y: int, width: int, height: int):
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE cards SET position_x = ?, position_y = ?, width = ?, height = ?, updated_at = ?
                WHERE id = ?
            """, (x, y, width, height, datetime.now().isoformat(), card_id))
            conn.commit()
    
    def delete_card(self, card_id: str):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
            conn.commit()
    
    def save_metric(self, source: str, value: float, label: str, unit: str):
        """Save metric to history."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO metrics_history (data_source, timestamp, value, label, unit)
                VALUES (?, ?, ?, ?, ?)
            """, (source, time.time(), value, label, unit))
            # Keep only recent history
            conn.execute("""
                DELETE FROM metrics_history 
                WHERE data_source = ? AND id NOT IN (
                    SELECT id FROM metrics_history 
                    WHERE data_source = ? 
                    ORDER BY timestamp DESC LIMIT ?
                )
            """, (source, source, MAX_HISTORY_POINTS))
            conn.commit()
    
    def get_metric_history(self, source: str, limit: int = 50) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM metrics_history 
                WHERE data_source = ? 
                ORDER BY timestamp DESC LIMIT ?
            """, (source, limit)).fetchall()
            return [{'timestamp': r['timestamp'], 'value': r['value'], 
                    'label': r['label'], 'unit': r['unit']} for r in reversed(rows)]
    
    def _row_to_dashboard(self, row: sqlite3.Row) -> Dashboard:
        return Dashboard(
            id=row['id'], name=row['name'], description=row['description'],
            layout=row['layout'], created_at=row['created_at'], updated_at=row['updated_at'],
            is_default=bool(row['is_default']), refresh_interval=row['refresh_interval'],
            theme=row['theme']
        )
    
    def _row_to_card(self, row: sqlite3.Row) -> Card:
        return Card(
            id=row['id'], dashboard_id=row['dashboard_id'], title=row['title'],
            card_type=row['card_type'], data_source=row['data_source'],
            position_x=row['position_x'], position_y=row['position_y'],
            width=row['width'], height=row['height'],
            config=json.loads(row['config']) if row['config'] else {},
            created_at=row['created_at'], updated_at=row['updated_at']
        )

# ============================================
# METRIC COLLECTORS
# ============================================

class MetricCollector:
    """Collects system and network metrics."""
    
    def __init__(self, db: Database):
        self.db = db
        self._last_net_io = psutil.net_io_counters()
        self._last_net_time = time.time()
        self._running = True
        self._lock = threading.Lock()
    
    def get_cpu_metrics(self) -> Dict:
        """Get CPU metrics."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        
        return {
            'cpu_percent': round(cpu_percent, 1),
            'cpu_count': cpu_count,
            'load_1m': round(load_avg[0], 2),
            'load_5m': round(load_avg[1], 2),
            'load_15m': round(load_avg[2], 2),
            'per_cpu': psutil.cpu_percent(interval=0.1, percpu=True)
        }
    
    def get_memory_metrics(self) -> Dict:
        """Get memory metrics."""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'total': mem.total,
            'available': mem.available,
            'percent': mem.percent,
            'used': mem.used,
            'free': mem.free,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_percent': swap.percent
        }
    
    def get_disk_metrics(self) -> Dict:
        """Get disk metrics."""
        partitions = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partitions.append({
                    'device': part.device,
                    'mountpoint': part.mountpoint,
                    'fstype': part.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except PermissionError:
                continue
        
        return {'partitions': partitions}
    
    def get_network_metrics(self) -> Dict:
        """Get network metrics with bandwidth calculation."""
        net_io = psutil.net_io_counters()
        now = time.time()
        
        with self._lock:
            time_delta = now - self._last_net_time
            if time_delta > 0:
                rx_speed = (net_io.bytes_recv - self._last_net_io.bytes_recv) / time_delta / 1024 / 1024  # MB/s
                tx_speed = (net_io.bytes_sent - self._last_net_io.bytes_sent) / time_delta / 1024 / 1024
            else:
                rx_speed = tx_speed = 0
            
            self._last_net_io = net_io
            self._last_net_time = now
        
        # Interface details
        interfaces = []
        for name, addrs in psutil.net_if_addrs().items():
            stats = psutil.net_if_stats().get(name)
            if stats:
                ip_addrs = [a.address for a in addrs if a.family == socket.AF_INET]
                interfaces.append({
                    'name': name,
                    'ip': ip_addrs[0] if ip_addrs else '-',
                    'is_up': stats.isup,
                    'speed': stats.speed,  # Mbps
                    'mtu': stats.mtu
                })
        
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'rx_speed_mbps': round(rx_speed, 2),
            'tx_speed_mbps': round(tx_speed, 2),
            'interfaces': interfaces
        }
    
    def get_connections_metrics(self) -> Dict:
        """Get active connections."""
        try:
            conns = psutil.net_connections()
            by_status = {}
            for c in conns:
                status = c.status if c.status else 'UNKNOWN'
                by_status[status] = by_status.get(status, 0) + 1
            
            return {
                'total': len(conns),
                'by_status': by_status,
                'listening': by_status.get('LISTEN', 0),
                'established': by_status.get('ESTABLISHED', 0)
            }
        except PermissionError:
            return {'total': 0, 'by_status': {}, 'listening': 0, 'established': 0, 'error': 'Permission denied'}
    
    def get_ping_metrics(self, target: str = '8.8.8.8') -> Dict:
        """Ping a target and return latency."""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', target],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                match = re.search(r'time=([\d.]+) ms', result.stdout)
                if match:
                    return {'reachable': True, 'latency_ms': float(match.group(1)), 'target': target}
            return {'reachable': False, 'latency_ms': None, 'target': target}
        except Exception as e:
            return {'reachable': False, 'latency_ms': None, 'target': target, 'error': str(e)}
    
    def collect_all(self) -> Dict[str, Any]:
        """Collect all metrics."""
        timestamp = time.time()
        metrics = {
            'timestamp': timestamp,
            'cpu': self.get_cpu_metrics(),
            'memory': self.get_memory_metrics(),
            'disk': self.get_disk_metrics(),
            'network': self.get_network_metrics(),
            'connections': self.get_connections_metrics(),
            'ping': self.get_ping_metrics()
        }
        
        # Save to history
        self.db.save_metric('cpu', metrics['cpu']['cpu_percent'], 'CPU Usage', '%')
        self.db.save_metric('memory', metrics['memory']['percent'], 'Memory Usage', '%')
        self.db.save_metric('network_rx', metrics['network']['rx_speed_mbps'], 'RX Speed', 'MB/s')
        self.db.save_metric('network_tx', metrics['network']['tx_speed_mbps'], 'TX Speed', 'MB/s')
        self.db.save_metric('connections', metrics['connections']['total'], 'Connections', 'count')
        
        if metrics['ping']['reachable']:
            self.db.save_metric('ping', metrics['ping']['latency_ms'], 'Latency', 'ms')
        
        return metrics

# ============================================
# WEBSOCKET MANAGER
# ============================================

class WebSocketManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.clients: set = set()
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def register(self, ws):
        self.clients.add(ws)
    
    def unregister(self, ws):
        self.clients.discard(ws)
    
    def broadcast(self, message: Dict):
        """Send message to all connected clients."""
        disconnected = set()
        for ws in self.clients:
            try:
                ws.send(json.dumps(message))
            except Exception:
                disconnected.add(ws)
        
        # Clean up disconnected clients
        self.clients -= disconnected
    
    def start_broadcasting(self):
        """Start background thread for metric broadcasting."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self._thread.start()
    
    def _broadcast_loop(self):
        """Continuously collect and broadcast metrics."""
        while self._running:
            try:
                metrics = self.collector.collect_all()
                self.broadcast({
                    'type': 'metrics_update',
                    'data': metrics,
                    'timestamp': time.time()
                })
                time.sleep(WS_UPDATE_INTERVAL)
            except Exception as e:
                print(f"Broadcast error: {e}")
                time.sleep(1)

# ============================================
# FLASK APPLICATION
# ============================================

app = Flask(__name__, 
            static_folder='/home/sabawi/Development/netdash/static',
            template_folder='/home/sabawi/Development/netdash/templates')
CORS(app)
sock = Sock(app)

# Initialize components
db = Database(DATABASE_PATH)
collector = MetricCollector(db)
ws_manager = WebSocketManager(collector)

# Start background broadcasting
ws_manager.start_broadcasting()

# ============================================
# ROUTES
# ============================================

@app.route('/')
def index():
    return render_template('index_v2.html')

@app.route('/api/dashboards')
def get_dashboards():
    return jsonify([d.to_dict() for d in db.get_dashboards()])

@app.route('/api/dashboards', methods=['POST'])
def create_dashboard():
    data = request.json
    dash = db.create_dashboard(
        name=data.get('name', 'New Dashboard'),
        description=data.get('description', ''),
        layout=data.get('layout', 'grid')
    )
    return jsonify(dash.to_dict())

@app.route('/api/dashboards/<dash_id>/cards')
def get_cards(dash_id):
    return jsonify([c.to_dict() for c in db.get_cards(dash_id)])

@app.route('/api/dashboards/<dash_id>/cards', methods=['POST'])
def create_card_route(dash_id):
    data = request.json
    card = db.create_card(
        dashboard_id=dash_id,
        title=data.get('title', 'New Card'),
        card_type=data.get('card_type', 'text'),
        data_source=data.get('data_source', 'custom'),
        x=data.get('position_x', 0),
        y=data.get('position_y', 0),
        width=data.get('width', 3),
        height=data.get('height', 3),
        config=data.get('config', {})
    )
    return jsonify(card.to_dict())

@app.route('/api/cards/<card_id>', methods=['DELETE'])
def delete_card_route(card_id):
    db.delete_card(card_id)
    return jsonify({'success': True})

@app.route('/api/cards/<card_id>/position', methods=['PUT'])
def update_card_position(card_id):
    data = request.json
    db.update_card_position(
        card_id, 
        data.get('x', 0), 
        data.get('y', 0),
        data.get('width', 3),
        data.get('height', 3)
    )
    return jsonify({'success': True})

@app.route('/api/metrics/current')
def get_current_metrics():
    return jsonify(collector.collect_all())

@app.route('/api/metrics/history/<source>')
def get_metric_history_route(source):
    limit = request.args.get('limit', 50, type=int)
    return jsonify(db.get_metric_history(source, limit))

@app.route('/api/network/scan', methods=['POST'])
def network_scan():
    """Async network scan endpoint."""
    data = request.json
    subnet = data.get('subnet', '192.168.1.0/24')
    
    try:
        result = subprocess.run(
            ['nmap', '-sn', subnet],
            capture_output=True, text=True, timeout=60
        )
        hosts = []
        for line in result.stdout.split('\n'):
            if 'Nmap scan report for' in line:
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if ip_match:
                    hosts.append({'ip': ip_match.group(1), 'status': 'up'})
        
        return jsonify({'hosts': hosts, 'count': len(hosts)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/commands')
def list_commands():
    """List available system commands."""
    return jsonify({
        'commands': [
            {'key': 'ping', 'name': 'Ping Test', 'params': ['target']},
            {'key': 'traceroute', 'name': 'Traceroute', 'params': ['target']},
            {'key': 'nslookup', 'name': 'DNS Lookup', 'params': ['domain']},
            {'key': 'netstat', 'name': 'Netstat', 'params': []},
            {'key': 'ss', 'name': 'Socket Statistics', 'params': []},
            {'key': 'ip_addr', 'name': 'IP Address', 'params': []},
            {'key': 'ip_route', 'name': 'IP Route', 'params': []},
        ]
    })

@app.route('/api/system/exec', methods=['POST'])
def exec_command():
    """Execute whitelisted system command."""
    data = request.json
    cmd_key = data.get('command')
    target = data.get('target', '')
    
    # Whitelist of safe commands
    allowed = {
        'ping': ['ping', '-c', '4', target],
        'traceroute': ['traceroute', '-m', '30', target],
        'nslookup': ['nslookup', target],
        'netstat': ['netstat', '-tuln'],
        'ss': ['ss', '-tuln'],
        'ip_addr': ['ip', '-j', 'addr', 'show'],
        'ip_route': ['ip', '-j', 'route', 'show'],
    }
    
    if cmd_key not in allowed:
        return jsonify({'error': 'Command not allowed'}), 403
    
    try:
        result = subprocess.run(
            allowed[cmd_key], 
            capture_output=True, text=True, timeout=30
        )
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# WEBSOCKET ROUTE
# ============================================

@sock.route('/ws')
def websocket(ws):
    """WebSocket endpoint for real-time metrics."""
    ws_manager.register(ws)
    try:
        # Send initial data
        ws.send(json.dumps({
            'type': 'connected',
            'message': 'Connected to NetDash metrics stream'
        }))
        
        # Keep connection alive and handle client messages
        while True:
            msg = ws.receive()
            if msg is None:
                break
            
            try:
                data = json.loads(msg)
                if data.get('action') == 'get_metrics':
                    metrics = collector.collect_all()
                    ws.send(json.dumps({
                        'type': 'metrics_update',
                        'data': metrics
                    }))
            except json.JSONDecodeError:
                pass
                
    finally:
        ws_manager.unregister(ws)

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print(f"NetDash v2.0 starting...")
    print(f"Database: {DATABASE_PATH}")
    print(f"WebSocket: ws://localhost:5555/ws")
    
    # Use threaded=True but not reloader for WebSocket compatibility
    app.run(
        host='0.0.0.0', 
        port=5555, 
        threaded=True,
        use_reloader=False
    )
