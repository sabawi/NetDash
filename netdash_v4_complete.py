#!/usr/bin/env python3
"""
NetDash v4 - Complete Network and System Control Center
Architecture: Modular, Real-time, Card-Based Dashboard
Features: WebSocket real-time metrics, drag-and-drop screen builder, 
          extensible card system, role-based access
"""

import os
import sys
import json
import time
import uuid
import asyncio
import threading
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import deque

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS

import psutil
import psutil

# ==============================================================================
# CONFIGURATION
# ==============================================================================

@dataclass
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or str(uuid.uuid4())
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000
    
    # Metrics Collection
    METRICS_INTERVAL = 2  # seconds
    HISTORY_LENGTH = 300  # 5 minutes at 2-second intervals
    
    # Card Types Registry
    CARD_TYPES = {
        'system_cpu': {'name': 'CPU Monitor', 'icon': 'cpu', 'category': 'system'},
        'system_memory': {'name': 'Memory Usage', 'icon': 'memory', 'category': 'system'},
        'system_disk': {'name': 'Disk I/O', 'icon': 'harddisk', 'category': 'system'},
        'system_network': {'name': 'Network I/O', 'icon': 'network', 'category': 'system'},
        'system_processes': {'name': 'Process List', 'icon': 'list', 'category': 'system'},
        'net_ping': {'name': 'Ping Monitor', 'icon': 'ping', 'category': 'network'},
        'net_bandwidth': {'name': 'Bandwidth Gauge', 'icon': 'gauge', 'category': 'network'},
        'net_connections': {'name': 'Active Connections', 'icon': 'connections', 'category': 'network'},
        'net_interfaces': {'name': 'Interface Status', 'icon': 'ethernet', 'category': 'network'},
        'custom_command': {'name': 'Custom Command', 'icon': 'terminal', 'category': 'custom'},
        'chart_line': {'name': 'Line Chart', 'icon': 'chart-line', 'category': 'visualization'},
        'chart_gauge': {'name': 'Gauge Chart', 'icon': 'gauge-high', 'category': 'visualization'},
    }

# ==============================================================================
# DATA MODELS
# ==============================================================================

@dataclass
class Dashboard:
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    cards: List[Dict[str, Any]]
    layout: Dict[str, Any]
    is_default: bool = False

@dataclass
class Card:
    id: str
    type: str
    title: str
    position: Dict[str, int]  # x, y, w, h in grid units
    config: Dict[str, Any]
    data: Optional[Dict[str, Any]] = None

@dataclass
class MetricPoint:
    timestamp: float
    value: float
    label: str = ''

# ==============================================================================
# METRICS COLLECTORS
# ==============================================================================

class MetricsCollector:
    """Base class for all metric collectors"""
    
    def __init__(self, name: str, interval: int = 2):
        self.name = name
        self.interval = interval
        self.history: deque = deque(maxlen=Config.HISTORY_LENGTH)
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._collect_loop, daemon=True)
            self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
    
    def _collect_loop(self):
        while self.running:
            try:
                data = self.collect()
                if data:
                    self.history.append({
                        'timestamp': time.time(),
                        'data': data
                    })
            except Exception as e:
                print(f"[{self.name}] Collection error: {e}")
            time.sleep(self.interval)
    
    def collect(self) -> Dict[str, Any]:
        """Override in subclasses"""
        return {}
    
    def get_latest(self) -> Optional[Dict[str, Any]]:
        if self.history:
            return self.history[-1]
        return None
    
    def get_history(self, points: int = 60) -> List[Dict[str, Any]]:
        return list(self.history)[-points:] if self.history else []


class SystemMetricsCollector(MetricsCollector):
    """Collects system-wide metrics: CPU, Memory, Disk, Network"""
    
    def __init__(self):
        super().__init__('system', Config.METRICS_INTERVAL)
        self._net_io_prev = None
        self._disk_io_prev = None
        self._prev_time = None
    
    def collect(self) -> Dict[str, Any]:
        current_time = time.time()
        
        # CPU Metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
        cpu_freq = psutil.cpu_freq()
        cpu_stats = psutil.cpu_stats()
        
        # Memory Metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk Metrics
        disk_usage = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        disk_io_delta = {}
        if self._disk_io_prev and self._prev_time:
            time_delta = current_time - self._prev_time
            if time_delta > 0:
                for attr in ['read_bytes', 'write_bytes', 'read_count', 'write_count']:
                    prev_val = getattr(self._disk_io_prev, attr, 0)
                    curr_val = getattr(disk_io, attr, 0)
                    disk_io_delta[f'{attr}_per_sec'] = (curr_val - prev_val) / time_delta
        self._disk_io_prev = disk_io
        
        # Network Metrics
        net_io = psutil.net_io_counters()
        net_io_delta = {}
        if self._net_io_prev and self._prev_time:
            time_delta = current_time - self._prev_time
            if time_delta > 0:
                for attr in ['bytes_sent', 'bytes_recv', 'packets_sent', 'packets_recv']:
                    prev_val = getattr(self._net_io_prev, attr, 0)
                    curr_val = getattr(net_io, attr, 0)
                    net_io_delta[f'{attr}_per_sec'] = (curr_val - prev_val) / time_delta
        self._net_io_prev = net_io
        self._prev_time = current_time
        
        # Process count
        process_count = len(psutil.pids())
        
        # Load average (Unix-like systems)
        load_avg = None
        try:
            load_avg = os.getloadavg()
        except AttributeError:
            pass
        
        return {
            'timestamp': current_time,
            'cpu': {
                'percent': cpu_percent,
                'per_core': cpu_per_core,
                'core_count': len(cpu_per_core),
                'frequency': cpu_freq._asdict() if cpu_freq else None,
                'stats': cpu_stats._asdict() if cpu_stats else None,
            },
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
                'free': memory.free,
                'buffers': getattr(memory, 'buffers', 0),
                'cached': getattr(memory, 'cached', 0),
                'swap_total': swap.total,
                'swap_used': swap.used,
                'swap_percent': swap.percent,
            },
            'disk': {
                'total': disk_usage.total,
                'used': disk_usage.used,
                'free': disk_usage.free,
                'percent': disk_usage.percent,
                'io': disk_io_delta if disk_io_delta else disk_io._asdict() if disk_io else {},
            },
            'network': {
                'io': net_io_delta if net_io_delta else net_io._asdict() if net_io else {},
            },
            'processes': {
                'total': process_count,
                'load_avg': load_avg,
            },
            'boot_time': psutil.boot_time(),
        }


class NetworkMetricsCollector(MetricsCollector):
    """Collects network interface metrics and connection stats"""
    
    def __init__(self):
        super().__init__('network', Config.METRICS_INTERVAL)
    
    def collect(self) -> Dict[str, Any]:
        interfaces = {}
        
        # Get all network interfaces
        for name, addrs in psutil.net_if_addrs().items():
            interfaces[name] = {
                'addresses': [],
                'stats': None,
            }
            for addr in addrs:
                interfaces[name]['addresses'].append({
                    'family': str(addr.family),
                    'address': addr.address,
                    'netmask': addr.netmask,
                    'broadcast': addr.broadcast,
                })
        
        # Get interface stats
        for name, stats in psutil.net_if_stats().items():
            if name in interfaces:
                interfaces[name]['stats'] = {
                    'isup': stats.isup,
                    'duplex': stats.duplex,
                    'speed': stats.speed,
                    'mtu': stats.mtu,
                }
        
        # Get active connections summary
        connections = []
        try:
            for conn in psutil.net_connections(kind='inet')[:50]:  # Limit to top 50
                if conn.status:
                    connections.append({
                        'fd': conn.fd,
                        'family': str(conn.family),
                        'type': str(conn.type),
                        'laddr': conn.laddr,
                        'raddr': conn.raddr if conn.raddr else None,
                        'status': conn.status,
                        'pid': conn.pid,
                    })
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        
        return {
            'timestamp': time.time(),
            'interfaces': interfaces,
            'connections': connections,
            'connection_count': len(connections),
        }


class ProcessMetricsCollector(MetricsCollector):
    """Collects top process information"""
    
    def __init__(self):
        super().__init__('processes', 5)  # Slower interval for processes
    
    def collect(self) -> Dict[str, Any]:
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 
                                          'memory_info', 'status', 'create_time']):
            try:
                pinfo = proc.info
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu_percent': pinfo['cpu_percent'],
                    'memory_percent': pinfo['memory_percent'],
                    'memory_rss': pinfo['memory_info'].rss if pinfo['memory_info'] else 0,
                    'status': pinfo['status'],
                    'created': pinfo['create_time'],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        
        return {
            'timestamp': time.time(),
            'top_cpu': processes[:10],
            'top_memory': sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:10],
            'total_count': len(processes),
        }


# ==============================================================================
# PERSISTENCE
# ==============================================================================

class DashboardStore:
    """Simple JSON file-based dashboard storage"""
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.dashboards: Dict[str, Dashboard] = {}
        self._load_all()
        
        # Create default dashboard if none exists
        if not self.dashboards:
            self._create_default_dashboard()
    
    def _get_path(self, dashboard_id: str) -> str:
        return os.path.join(self.data_dir, f'dashboard_{dashboard_id}.json')
    
    def _load_all(self):
        """Load all saved dashboards"""
        for filename in os.listdir(self.data_dir):
            if filename.startswith('dashboard_') and filename.endswith('.json'):
                try:
                    with open(os.path.join(self.data_dir, filename), 'r') as f:
                        data = json.load(f)
                        dash = Dashboard(**data)
                        self.dashboards[dash.id] = dash
                except Exception as e:
                    print(f"Error loading dashboard {filename}: {e}")
    
    def _create_default_dashboard(self):
        """Create a default dashboard with essential monitoring cards"""
        default_cards = [
            {
                'id': str(uuid.uuid4())[:8],
                'type': 'system_cpu',
                'title': 'CPU Usage',
                'position': {'x': 0, 'y': 0, 'w': 3, 'h': 2},
                'config': {'show_cores': True, 'alert_threshold': 80}
            },
            {
                'id': str(uuid.uuid4())[:8],
                'type': 'system_memory',
                'title': 'Memory Usage',
                'position': {'x': 3, 'y': 0, 'w': 3, 'h': 2},
                'config': {'show_swap': True, 'alert_threshold': 90}
            },
            {
                'id': str(uuid.uuid4())[:8],
                'type': 'system_network',
                'title': 'Network I/O',
                'position': {'x': 6, 'y': 0, 'w': 3, 'h': 2},
                'config': {'show_graph': True, 'interfaces': 'all'}
            },
            {
                'id': str(uuid.uuid4())[:8],
                'type': 'chart_line',
                'title': 'System History',
                'position': {'x': 0, 'y': 2, 'w': 6, 'h': 3},
                'config': {'metrics': ['cpu', 'memory'], 'time_range': '5m'}
            },
            {
                'id': str(uuid.uuid4())[:8],
                'type': 'net_interfaces',
                'title': 'Network Interfaces',
                'position': {'x': 6, 'y': 2, 'w': 3, 'h': 3},
                'config': {'show_inactive': False}
            },
        ]
        
        default = Dashboard(
            id='default',
            name='System Overview',
            description='Default system monitoring dashboard',
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            cards=default_cards,
            layout={'columns': 9, 'rowHeight': 60},
            is_default=True
        )
        
        self.dashboards['default'] = default
        self.save('default')
    
    def save(self, dashboard_id: str):
        """Save a dashboard to disk"""
        if dashboard_id in self.dashboards:
            dash = self.dashboards[dashboard_id]
            dash.updated_at = datetime.now().isoformat()
            with open(self._get_path(dashboard_id), 'w') as f:
                json.dump(asdict(dash), f, indent=2)
    
    def create(self, name: str, description: str = '') -> Dashboard:
        """Create a new dashboard"""
        dash_id = str(uuid.uuid4())[:8]
        dash = Dashboard(
            id=dash_id,
            name=name,
            description=description,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            cards=[],
            layout={'columns': 9, 'rowHeight': 60},
            is_default=False
        )
        self.dashboards[dash_id] = dash
        self.save(dash_id)
        return dash
    
    def get(self, dashboard_id: str) -> Optional[Dashboard]:
        return self.dashboards.get(dashboard_id)
    
    def get_all(self) -> List[Dashboard]:
        return list(self.dashboards.values())
    
    def delete(self, dashboard_id: str) -> bool:
        if dashboard_id in self.dashboards:
            del self.dashboards[dashboard_id]
            path = self._get_path(dashboard_id)
            if os.path.exists(path):
                os.remove(path)
            return True
        return False
    
    def update_cards(self, dashboard_id: str, cards: List[Dict]):
        if dashboard_id in self.dashboards:
            self.dashboards[dashboard_id].cards = cards
            self.save(dashboard_id)


# ==============================================================================
# FLASK APP SETUP
# ==============================================================================

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.config['SECRET_KEY'] = Config.SECRET_KEY
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize components
dashboard_store = DashboardStore()

# Initialize collectors
collector_system = SystemMetricsCollector()
collector_network = NetworkMetricsCollector()
collector_processes = ProcessMetricsCollector()

# Start collectors
collector_system.start()
collector_network.start()
collector_processes.start()

# ==============================================================================
# WEB ROUTES
# ==============================================================================

@app.route('/')
def index():
    return send_from_directory('static', 'dashboard.html')

@app.route('/<path:path>')
def static_file(path):
    return send_from_directory('static', path)

# ==============================================================================
# API ROUTES
# ==============================================================================

@app.route('/api/dashboards', methods=['GET'])
def api_dashboards_list():
    dashboards = dashboard_store.get_all()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'description': d.description,
        'is_default': d.is_default,
        'card_count': len(d.cards),
        'updated_at': d.updated_at
    } for d in dashboards])

@app.route('/api/dashboards/<dashboard_id>', methods=['GET'])
def api_dashboard_get(dashboard_id):
    dashboard = dashboard_store.get(dashboard_id)
    if not dashboard:
        return jsonify({'error': 'Dashboard not found'}), 404
    return jsonify(asdict(dashboard))

@app.route('/api/dashboards', methods=['POST'])
def api_dashboard_create():
    data = request.json
    name = data.get('name', 'New Dashboard')
    description = data.get('description', '')
    dashboard = dashboard_store.create(name, description)
    return jsonify(asdict(dashboard)), 201

@app.route('/api/dashboards/<dashboard_id>/cards', methods=['PUT'])
def api_dashboard_update_cards(dashboard_id):
    data = request.json
    cards = data.get('cards', [])
    dashboard_store.update_cards(dashboard_id, cards)
    return jsonify({'success': True, 'card_count': len(cards)})

@app.route('/api/dashboards/<dashboard_id>', methods=['DELETE'])
def api_dashboard_delete(dashboard_id):
    if dashboard_store.delete(dashboard_id):
        return jsonify({'success': True})
    return jsonify({'error': 'Dashboard not found'}), 404

@app.route('/api/card-types', methods=['GET'])
def api_card_types():
    return jsonify(Config.CARD_TYPES)

@app.route('/api/metrics/system', methods=['GET'])
def api_metrics_system():
    latest = collector_system.get_latest()
    if latest:
        return jsonify(latest['data'])
    return jsonify({})

@app.route('/api/metrics/system/history', methods=['GET'])
def api_metrics_system_history():
    points = request.args.get('points', 60, type=int)
    history = collector_system.get_history(points)
    return jsonify([h['data'] for h in history])

@app.route('/api/metrics/network', methods=['GET'])
def api_metrics_network():
    latest = collector_network.get_latest()
    if latest:
        return jsonify(latest['data'])
    return jsonify({})

@app.route('/api/metrics/processes', methods=['GET'])
def api_metrics_processes():
    latest = collector_processes.get_latest()
    if latest:
        return jsonify(latest['data'])
    return jsonify({})

@app.route('/api/network/ping', methods=['POST'])
def api_network_ping():
    data = request.json
    target = data.get('target')
    count = data.get('count', 4)
    
    if not target:
        return jsonify({'error': 'Target required'}), 400
    
    try:
        result = subprocess.run(
            ['ping', '-c', str(count), target],
            capture_output=True,
            text=True,
            timeout=30
        )
        return jsonify({
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr,
            'target': target
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout', 'target': target}), 408
    except Exception as e:
        return jsonify({'error': str(e), 'target': target}), 500

@app.route('/api/system/command', methods=['POST'])
def api_system_command():
    """Execute whitelisted system commands"""
    data = request.json
    command = data.get('command')
    args = data.get('args', [])
    
    # Security: Whitelist of allowed commands
    ALLOWED_COMMANDS = ['df', 'free', 'uptime', 'who', 'w', 'netstat', 'ss', 'ip', 'ls', 'ps']
    
    if command not in ALLOWED_COMMANDS:
        return jsonify({'error': 'Command not allowed'}), 403
    
    try:
        result = subprocess.run(
            [command] + args,
            capture_output=True,
            text=True,
            timeout=10
        )
        return jsonify({
            'command': command,
            'args': args,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==============================================================================
# WEBSOCKET EVENTS
# ==============================================================================

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to NetDash v4'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

@socketio.on('subscribe_dashboard')
def handle_subscribe_dashboard(data):
    dashboard_id = data.get('dashboard_id', 'default')
    room = f"dashboard_{dashboard_id}"
    join_room(room)
    emit('subscribed', {'dashboard_id': dashboard_id, 'room': room})
    
    # Send initial data
    dashboard = dashboard_store.get(dashboard_id)
    if dashboard:
        emit('dashboard_data', asdict(dashboard))

@socketio.on('unsubscribe_dashboard')
def handle_unsubscribe_dashboard(data):
    dashboard_id = data.get('dashboard_id', 'default')
    room = f"dashboard_{dashboard_id}"
    leave_room(room)
    emit('unsubscribed', {'dashboard_id': dashboard_id})

def broadcast_metrics():
    """Background thread to broadcast metrics to all connected clients"""
    while True:
        try:
            # System metrics
            system_data = collector_system.get_latest()
            if system_data:
                socketio.emit('metrics_system', system_data['data'], namespace='/')
            
            # Network metrics
            network_data = collector_network.get_latest()
            if network_data:
                socketio.emit('metrics_network', network_data['data'], namespace='/')
            
            # Process metrics
            process_data = collector_processes.get_latest()
            if process_data:
                socketio.emit('metrics_processes', process_data['data'], namespace='/')
            
        except Exception as e:
            print(f"Broadcast error: {e}")
        
        time.sleep(Config.METRICS_INTERVAL)

# Start broadcast thread
broadcast_thread = threading.Thread(target=broadcast_metrics, daemon=True)
broadcast_thread.start()

# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("NetDash v4 - Network and System Control Center")
    print("=" * 60)
    print(f"Starting server on http://{Config.HOST}:{Config.PORT}")
    print(f"Dashboards loaded: {len(dashboard_store.dashboards)}")
    print(f"Metrics collectors: system, network, processes")
    print("=" * 60)
    
    socketio.run(app, host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
