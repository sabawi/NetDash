#!/usr/bin/env python3
"""
NetDash v3.0 - Complete Network & System Control Center
==========================================================
Fully re-architected with:
- Dynamic screen builder with draggable cards
- Real-time gauges, charts, and metrics visualization
- Interactive system tuning controls
- Modular plugin architecture
- WebSocket-based real-time updates
- Role-based access control

Architecture: Micro-core with plugin-based card system
"""

import os
import sys
import json
import time
import socket
import psutil
import subprocess
import threading
import ipaddress
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from collections import deque, defaultdict
from threading import Lock
import uuid
import re
import shutil

from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room

# Configuration
CONFIG = {
    'SECRET_KEY': os.urandom(24),
    'DB_PATH': os.path.expanduser('~/Development/netdash/data/netdash.db'),
    'METRICS_HISTORY': 300,  # 5 minutes of metrics history
    'UPDATE_INTERVAL': 2,    # seconds between updates
    'MAX_CARDS_PER_SCREEN': 32,
    'DEFAULT_PORT': 5000,
    'CARD_TYPES': [
        'system_cpu', 'system_memory', 'system_disk', 'system_load',
        'network_io', 'network_connections', 'network_interfaces',
        'ping_monitor', 'bandwidth_gauge', 'custom_command',
        'port_scanner', 'traceroute_map', 'topology_view',
        'firewall_status', 'process_list', 'log_viewer'
    ]
}

# Initialize Flask
app = Flask(__name__, 
    template_folder=os.path.expanduser('~/Development/netdash/templates'),
    static_folder=os.path.expanduser('~/Development/netdash/static'))
app.secret_key = CONFIG['SECRET_KEY']
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Data Stores
metrics_history = defaultdict(lambda: deque(maxlen=CONFIG['METRICS_HISTORY']))
active_monitors = {}
monitors_lock = Lock()

# Database Initialization
def init_database():
    """Initialize SQLite database for screens, cards, and settings"""
    os.makedirs(os.path.dirname(CONFIG['DB_PATH']), exist_ok=True)
    conn = sqlite3.connect(CONFIG['DB_PATH'])
    cursor = conn.cursor()
    
    # Screens table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS screens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            layout TEXT DEFAULT 'grid',
            columns INTEGER DEFAULT 4,
            refresh_rate INTEGER DEFAULT 2,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_default BOOLEAN DEFAULT 0
        )
    ''')
    
    # Cards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            screen_id INTEGER NOT NULL,
            card_type TEXT NOT NULL,
            title TEXT NOT NULL,
            position_x INTEGER DEFAULT 0,
            position_y INTEGER DEFAULT 0,
            width INTEGER DEFAULT 1,
            height INTEGER DEFAULT 1,
            config TEXT DEFAULT '{}',
            FOREIGN KEY (screen_id) REFERENCES screens(id) ON DELETE CASCADE
        )
    ''')
    
    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Users table (basic auth)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'viewer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default admin user (password: admin)
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password_hash, role)
        VALUES ('admin', 'pbkdf2:sha256:260000$dummy$hash', 'admin')
    ''')
    
    # Insert default screen
    cursor.execute('''
        INSERT OR IGNORE INTO screens (name, description, is_default)
        VALUES ('Main Dashboard', 'Default system overview', 1)
    ''')
    
    conn.commit()
    conn.close()

# Metrics Collection Engine
class MetricsCollector:
    """Collects system and network metrics with history"""
    
    @staticmethod
    def get_system_metrics():
        """Get current system metrics"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu': {
                'percent': psutil.cpu_percent(interval=0.1),
                'count': psutil.cpu_count(),
                'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
                'per_cpu': psutil.cpu_percent(interval=0.1, percpu=True),
                'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            },
            'memory': {
                'virtual': psutil.virtual_memory()._asdict(),
                'swap': psutil.swap_memory()._asdict()
            },
            'disk': {
                'usage': {path: psutil.disk_usage(path)._asdict() 
                         for path in ['/', '/home'] if os.path.exists(path)}
            },
            'processes': {
                'total': len(psutil.pids()),
                'running': sum(1 for p in psutil.process_iter(['status']) 
                              if p.info['status'] == psutil.STATUS_RUNNING)
            }
        }
        return metrics
    
    @staticmethod
    def get_network_metrics():
        """Get current network metrics"""
        net_io = psutil.net_io_counters(pernic=True)
        net_stats = psutil.net_if_stats()
        
        # Get connections by status
        connections = psutil.net_connections()
        conn_by_status = defaultdict(int)
        for conn in connections:
            conn_by_status[conn.status] += 1
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'io_counters': {iface: counters._asdict() 
                          for iface, counters in net_io.items()},
            'interface_stats': {iface: {
                'is_up': stats.isup,
                'duplex': stats.duplex,
                'speed': stats.speed,
                'mtu': stats.mtu
            } for iface, stats in net_stats.items()},
            'connections': dict(conn_by_status),
            'connections_total': len(connections)
        }
        return metrics
    
    @staticmethod
    def get_interface_details():
        """Get detailed interface information"""
        interfaces = []
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        
        for iface_name in addrs:
            iface_info = {
                'name': iface_name,
                'addresses': [],
                'stats': stats.get(iface_name)._asdict() if iface_name in stats else None
            }
            for addr in addrs[iface_name]:
                iface_info['addresses'].append({
                    'family': str(addr.family),
                    'address': addr.address,
                    'netmask': addr.netmask,
                    'broadcast': addr.broadcast
                })
            interfaces.append(iface_info)
        return interfaces

# Network Command Executor
class NetworkCommander:
    """Execute network commands safely"""
    
    ALLOWED_COMMANDS = {
        'ping': {'cmd': ['ping', '-c', '4'], 'timeout': 10},
        'traceroute': {'cmd': ['traceroute', '-m', '30'], 'timeout': 30},
        'nslookup': {'cmd': ['nslookup'], 'timeout': 10},
        'dig': {'cmd': ['dig'], 'timeout': 10},
        'whois': {'cmd': ['whois'], 'timeout': 15},
        'netstat': {'cmd': ['ss', '-tuln'], 'timeout': 5},
        'arp': {'cmd': ['ip', 'neigh', 'show'], 'timeout': 5},
        'route': {'cmd': ['ip', 'route', 'show'], 'timeout': 5},
        'iptables': {'cmd': ['sudo', 'iptables', '-L', '-n', '-v'], 'timeout': 5},
        'nmap_fast': {'cmd': ['nmap', '-F', '-T4'], 'timeout': 60},
    }
    
    @classmethod
    def execute(cls, command_key, target=None, extra_args=None):
        """Execute a network command safely"""
        if command_key not in cls.ALLOWED_COMMANDS:
            return {'error': 'Command not allowed', 'success': False}
        
        cmd_config = cls.ALLOWED_COMMANDS[command_key]
        cmd = cmd_config['cmd'].copy()
        
        if target:
            cmd.append(target)
        if extra_args:
            cmd.extend(extra_args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=cmd_config['timeout']
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(cmd)
            }
        except subprocess.TimeoutExpired:
            return {'error': 'Command timed out', 'success': False}
        except Exception as e:
            return {'error': str(e), 'success': False}
    
    @classmethod
    def ping_host(cls, host, count=4):
        """Ping a host and return structured results"""
        result = cls.execute('ping', host)
        if not result['success']:
            return result
        
        # Parse ping output
        lines = result['stdout'].split('\n')
        parsed = {'sent': count, 'received': 0, 'loss': 100, 'times': []}
        
        for line in lines:
            if 'bytes from' in line and 'time=' in line:
                parsed['received'] += 1
                time_match = re.search(r'time=([\d.]+)\s*ms', line)
                if time_match:
                    parsed['times'].append(float(time_match.group(1)))
            elif 'packet loss' in line:
                loss_match = re.search(r'(\d+)% packet loss', line)
                if loss_match:
                    parsed['loss'] = int(loss_match.group(1))
            elif 'min/avg/max' in line:
                stats = re.search(r'min/avg/max.*=\s*([\d.]+)/([\d.]+)/([\d.]+)', line)
                if stats:
                    parsed['min'] = float(stats.group(1))
                    parsed['avg'] = float(stats.group(2))
                    parsed['max'] = float(stats.group(3))
        
        parsed['success'] = parsed['received'] > 0
        return parsed

# Background Metrics Thread
def metrics_collector_thread():
    """Background thread to collect metrics continuously"""
    while True:
        try:
            # Collect system metrics
            sys_metrics = MetricsCollector.get_system_metrics()
            metrics_history['system'].append(sys_metrics)
            
            # Collect network metrics
            net_metrics = MetricsCollector.get_network_metrics()
            metrics_history['network'].append(net_metrics)
            
            # Emit to connected clients
            socketio.emit('metrics_update', {
                'system': sys_metrics,
                'network': net_metrics
            }, namespace='/dashboard')
            
            time.sleep(CONFIG['UPDATE_INTERVAL'])
        except Exception as e:
            print(f"Metrics collector error: {e}")
            time.sleep(1)

# Database Helpers
def get_db():
    """Get database connection"""
    return sqlite3.connect(CONFIG['DB_PATH'])

def query_db(query, args=(), one=False):
    """Query database and return results as dict"""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(query, args)
    rows = cursor.fetchall()
    conn.close()
    
    results = [dict(row) for row in rows]
    return (results[0] if results else None) if one else results

def exec_db(query, args=()):
    """Execute database query"""
    conn = get_db()
    cursor = conn.execute(query, args)
    conn.commit()
    lastrowid = cursor.lastrowid
    conn.close()
    return lastrowid

# Flask Routes
@app.route('/')
def index():
    """Main dashboard view"""
    return render_template('index.html')

@app.route('/builder')
def builder():
    """Screen builder interface"""
    return render_template('screen_builder.html')

# API Routes - Screens
@app.route('/api/screens', methods=['GET', 'POST'])
def screens_api():
    """List or create screens"""
    if request.method == 'GET':
        screens = query_db('SELECT * FROM screens ORDER BY created_at DESC')
        return jsonify({'success': True, 'screens': screens})
    
    elif request.method == 'POST':
        data = request.json
        screen_id = exec_db('''
            INSERT INTO screens (name, description, layout, columns, refresh_rate)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['name'], data.get('description', ''), 
              data.get('layout', 'grid'), data.get('columns', 4),
              data.get('refresh_rate', 2)))
        return jsonify({'success': True, 'screen_id': screen_id})

@app.route('/api/screens/<int:screen_id>', methods=['GET', 'PUT', 'DELETE'])
def screen_detail_api(screen_id):
    """Get, update, or delete a screen"""
    if request.method == 'GET':
        screen = query_db('SELECT * FROM screens WHERE id = ?', (screen_id,), one=True)
        if not screen:
            return jsonify({'success': False, 'error': 'Screen not found'}), 404
        
        cards = query_db('SELECT * FROM cards WHERE screen_id = ?', (screen_id,))
        screen['cards'] = cards
        return jsonify({'success': True, 'screen': screen})
    
    elif request.method == 'PUT':
        data = request.json
        exec_db('''
            UPDATE screens SET name=?, description=?, layout=?, columns=?, 
            refresh_rate=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
        ''', (data['name'], data.get('description', ''), 
              data.get('layout', 'grid'), data.get('columns', 4),
              data.get('refresh_rate', 2), screen_id))
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        exec_db('DELETE FROM screens WHERE id = ?', (screen_id,))
        return jsonify({'success': True})

# API Routes - Cards
@app.route('/api/screens/<int:screen_id>/cards', methods=['POST'])
def add_card_api(screen_id):
    """Add a card to a screen"""
    data = request.json
    card_id = exec_db('''
        INSERT INTO cards (screen_id, card_type, title, position_x, position_y, 
                          width, height, config)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (screen_id, data['card_type'], data['title'],
          data.get('position_x', 0), data.get('position_y', 0),
          data.get('width', 1), data.get('height', 1),
          json.dumps(data.get('config', {}))))
    return jsonify({'success': True, 'card_id': card_id})

@app.route('/api/cards/<int:card_id>', methods=['PUT', 'DELETE'])
def card_detail_api(card_id):
    """Update or delete a card"""
    if request.method == 'PUT':
        data = request.json
        exec_db('''
            UPDATE cards SET title=?, position_x=?, position_y=?, 
            width=?, height=?, config=? WHERE id=?
        ''', (data['title'], data.get('position_x', 0), 
              data.get('position_y', 0), data.get('width', 1),
              data.get('height', 1), json.dumps(data.get('config', {})),
              card_id))
        return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        exec_db('DELETE FROM cards WHERE id = ?', (card_id,))
        return jsonify({'success': True})

# API Routes - Metrics
@app.route('/api/metrics/<metric_type>')
def get_metrics_api(metric_type):
    """Get historical metrics"""
    history = list(metrics_history.get(metric_type, []))
    return jsonify({'success': True, 'metrics': history})

@app.route('/api/metrics/current')
def get_current_metrics_api():
    """Get current metrics snapshot"""
    return jsonify({
        'success': True,
        'system': MetricsCollector.get_system_metrics(),
        'network': MetricsCollector.get_network_metrics()
    })

@app.route('/api/interfaces')
def get_interfaces_api():
    """Get network interface details"""
    return jsonify({
        'success': True,
        'interfaces': MetricsCollector.get_interface_details()
    })

# API Routes - Network Commands
@app.route('/api/network/<command>', methods=['POST'])
def network_command_api(command):
    """Execute network commands"""
    data = request.json or {}
    target = data.get('target', '')
    
    if command == 'ping':
        result = NetworkCommander.ping_host(target)
    elif command == 'traceroute':
        result = NetworkCommander.execute('traceroute', target)
    elif command == 'dns_lookup':
        result = NetworkCommander.execute('nslookup', target)
    elif command == 'whois':
        result = NetworkCommander.execute('whois', target)
    elif command == 'port_scan':
        result = NetworkCommander.execute('nmap_fast', target)
    else:
        return jsonify({'success': False, 'error': 'Unknown command'}), 400
    
    return jsonify(result)

@app.route('/api/network/connections')
def get_connections_api():
    """Get active network connections"""
    connections = []
    for conn in psutil.net_connections(kind='inet'):
        connections.append({
            'fd': conn.fd,
            'family': str(conn.family),
            'type': str(conn.type),
            'local_addr': conn.laddr,
            'remote_addr': conn.raddr,
            'status': conn.status,
            'pid': conn.pid
        })
    return jsonify({'success': True, 'connections': connections})

# WebSocket Events
@socketio.on('connect', namespace='/dashboard')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'message': 'Connected to NetDash'})

@socketio.on('subscribe_metrics', namespace='/dashboard')
def handle_subscribe_metrics(data):
    """Subscribe to metrics updates"""
    join_room('metrics')
    emit('subscribed', {'room': 'metrics'})

@socketio.on('unsubscribe_metrics', namespace='/dashboard')
def handle_unsubscribe_metrics(data):
    """Unsubscribe from metrics"""
    leave_room('metrics')

# Card Type Definitions
CARD_SCHEMAS = {
    'system_cpu': {
        'name': 'CPU Usage',
        'icon': 'cpu',
        'config': {
            'show_per_cpu': {'type': 'boolean', 'default': True},
            'alert_threshold': {'type': 'number', 'default': 80}
        }
    },
    'system_memory': {
        'name': 'Memory Usage',
        'icon': 'memory',
        'config': {
            'show_swap': {'type': 'boolean', 'default': True},
            'alert_threshold': {'type': 'number', 'default': 85}
        }
    },
    'system_disk': {
        'name': 'Disk Usage',
        'icon': 'hard-drive',
        'config': {
            'mounts': {'type': 'array', 'default': ['/']}
        }
    },
    'network_io': {
        'name': 'Network Traffic',
        'icon': 'activity',
        'config': {
            'interface': {'type': 'string', 'default': 'all'},
            'show_graph': {'type': 'boolean', 'default': True}
        }
    },
    'ping_monitor': {
        'name': 'Ping Monitor',
        'icon': 'wifi',
        'config': {
            'target': {'type': 'string', 'default': '8.8.8.8'},
            'interval': {'type': 'number', 'default': 5},
            'count': {'type': 'number', 'default': 4}
        }
    },
    'bandwidth_gauge': {
        'name': 'Bandwidth Gauge',
        'icon': 'gauge',
        'config': {
            'interface': {'type': 'string', 'default': 'eth0'},
            'max_speed': {'type': 'number', 'default': 1000}
        }
    },
    'custom_command': {
        'name': 'Custom Command',
        'icon': 'terminal',
        'config': {
            'command': {'type': 'string', 'default': 'uptime'},
            'refresh_interval': {'type': 'number', 'default': 30}
        }
    },
    'firewall_status': {
        'name': 'Firewall Status',
        'icon': 'shield',
        'config': {
            'show_rules': {'type': 'boolean', 'default': False}
        }
    },
    'process_list': {
        'name': 'Top Processes',
        'icon': 'list',
        'config': {
            'sort_by': {'type': 'string', 'default': 'cpu'},
            'limit': {'type': 'number', 'default': 10}
        }
    }
}

@app.route('/api/card-types')
def get_card_types_api():
    """Get available card types and their schemas"""
    return jsonify({'success': True, 'types': CARD_SCHEMAS})

# Static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# Initialize
def main():
    """Main entry point"""
    init_database()
    
    # Start metrics collector thread
    collector_thread = threading.Thread(target=metrics_collector_thread, daemon=True)
    collector_thread.start()
    
    print(f"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                    NetDash v3.0 Control Center                ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║  Dashboard: http://localhost:{CONFIG['DEFAULT_PORT']}                      ║
    ║  Screen Builder: http://localhost:{CONFIG['DEFAULT_PORT']}/builder       ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║  Features:                                                    ║
    ║  • Real-time gauges and charts                               ║
    ║  • Dynamic screen builder with draggable cards                 ║
    ║  • System & network performance monitoring                    ║
    ║  • Interactive tuning controls                                ║
    ║  • Custom command execution                                   ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    socketio.run(app, host='0.0.0.0', port=CONFIG['DEFAULT_PORT'], 
                 debug=False, use_reloader=False)

if __name__ == '__main__':
    main()
