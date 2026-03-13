#!/usr/bin/env python3
"""
Network Dashboard Backend - Improved UX/UI Support
Features: Async job tracking, progress indicators, comprehensive API endpoints,
CORS support, and real-time status polling.
"""

import os
import re
import json
import socket
import subprocess
import threading
import ipaddress
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS

# Configure template directory with absolute path to fix TemplateNotFound error
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
CORS(app)

# Thread pool for async network operations
executor = ThreadPoolExecutor(max_workers=10)

# Job tracking for async operations
jobs = {}
jobs_lock = threading.Lock()

# Allowed network commands (security whitelist)
ALLOWED_COMMANDS = {
    'ping': {'cmd': 'ping', 'args': ['-c', '4'], 'requires_target': True, 'duration': '10s'},
    'ping_sweep': {'cmd': 'fping', 'args': ['-a', '-g'], 'requires_target': True, 'duration': '30s'},
    'traceroute': {'cmd': 'traceroute', 'args': ['-m', '30'], 'requires_target': True, 'duration': '60s'},
    'nmap_fast': {'cmd': 'nmap', 'args': ['-F', '-T4'], 'requires_target': True, 'duration': '60s'},
    'nmap_full': {'cmd': 'nmap', 'args': ['-p', '1-1000', '-sV', '-T4'], 'requires_target': True, 'duration': '300s'},
    'nmap_os': {'cmd': 'nmap', 'args': ['-O', '--osscan-guess'], 'requires_target': True, 'duration': '120s'},
    'dns_lookup': {'cmd': 'nslookup', 'args': [], 'requires_target': True, 'duration': '10s'},
    'reverse_dns': {'cmd': 'dig', 'args': ['-x'], 'requires_target': True, 'duration': '10s'},
    'whois': {'cmd': 'whois', 'args': [], 'requires_target': True, 'duration': '15s'},
    'dig': {'cmd': 'dig', 'args': ['+noall', '+answer'], 'requires_target': True, 'duration': '10s'},
    'netstat': {'cmd': 'ss', 'args': ['-tuln'], 'requires_target': False, 'duration': '5s'},
    'connections': {'cmd': 'ss', 'args': ['-tunap'], 'requires_target': False, 'duration': '5s'},
    'ip_addr': {'cmd': 'ip', 'args': ['-j', 'addr', 'show'], 'requires_target': False, 'duration': '5s'},
    'ip_route': {'cmd': 'ip', 'args': ['-j', 'route', 'show'], 'requires_target': False, 'duration': '5s'},
    'arp': {'cmd': 'ip', 'args': ['-j', 'neigh', 'show'], 'requires_target': False, 'duration': '5s'},
    'arp_scan': {'cmd': 'arp-scan', 'args': ['--localnet', '-q'], 'requires_target': False, 'duration': '30s'},
    'bandwidth': {'cmd': 'cat', 'args': ['/proc/net/dev'], 'requires_target': False, 'duration': '2s'},
}

def create_job_id():
    """Generate unique job ID."""
    return str(uuid.uuid4())[:8]

def update_job_status(job_id, status, progress=0, message='', result=None):
    """Update job status in thread-safe manner."""
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id]['status'] = status
            jobs[job_id]['progress'] = progress
            jobs[job_id]['message'] = message
            if result is not None:
                jobs[job_id]['result'] = result
            jobs[job_id]['updated'] = datetime.now().isoformat()

def validate_target(target):
    """Validate that target is a valid IP, hostname, or domain."""
    if not target:
        return False
    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        pass
    try:
        ipaddress.ip_network(target, strict=False)
        return True
    except ValueError:
        pass
    hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    if re.match(hostname_pattern, target):
        return True
    return False

def sanitize_output(output):
    """Remove potentially sensitive info from command output."""
    if isinstance(output, str):
        output = re.sub(r'([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', 'XX:XX:XX:XX:XX:XX', output)
    return output

def run_network_command(job_id, command_key, target=None, extra_args=None):
    """Run network command with progress tracking."""
    if command_key not in ALLOWED_COMMANDS:
        update_job_status(job_id, 'error', 0, f'Unknown command: {command_key}')
        return
    
    cmd_info = ALLOWED_COMMANDS[command_key]
    
    if cmd_info['requires_target'] and not validate_target(target):
        update_job_status(job_id, 'error', 0, 'Invalid target specified')
        return
    
    update_job_status(job_id, 'running', 10, f'Starting {command_key}...')
    
    try:
        args = cmd_info['args'].copy()
        if extra_args:
            args.extend(extra_args)
        if target:
            if command_key == 'reverse_dns':
                args = ['-x', target]
            else:
                args.append(target)
        
        update_job_status(job_id, 'running', 30, 'Executing command...')
        
        result = subprocess.run(
            [cmd_info['cmd']] + args,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        update_job_status(job_id, 'running', 80, 'Processing results...')
        
        output = result.stdout if result.returncode == 0 else result.stderr
        sanitized_output = sanitize_output(output)
        
        update_job_status(
            job_id,
            'completed' if result.returncode == 0 else 'error',
            100,
            'Command completed' if result.returncode == 0 else f'Exit code: {result.returncode}',
            {'output': sanitized_output, 'exit_code': result.returncode}
        )
    except subprocess.TimeoutExpired:
        update_job_status(job_id, 'error', 0, 'Command timed out')
    except Exception as e:
        update_job_status(job_id, 'error', 0, f'Error: {str(e)}')

@app.route('/')
def index():
    """Render the main dashboard page."""
    return render_template('index.html')

@app.route('/api/jobs', methods=['POST'])
def create_job():
    """Create a new network job."""
    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({'error': 'Command required'}), 400
    
    command_key = data['command']
    target = data.get('target')
    extra_args = data.get('args', [])
    
    if command_key not in ALLOWED_COMMANDS:
        return jsonify({'error': f'Unknown command: {command_key}'}), 400
    
    job_id = create_job_id()
    with jobs_lock:
        jobs[job_id] = {
            'id': job_id,
            'command': command_key,
            'target': target,
            'status': 'pending',
            'progress': 0,
            'message': 'Job queued',
            'result': None,
            'created': datetime.now().isoformat(),
            'updated': datetime.now().isoformat()
        }
    
    executor.submit(run_network_command, job_id, command_key, target, extra_args)
    return jsonify({'job_id': job_id, 'status': 'pending'}), 202

@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get job status and results."""
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs."""
    with jobs_lock:
        job_list = list(jobs.values())
    return jsonify(job_list)

@app.route('/api/commands', methods=['GET'])
def list_commands():
    """List available commands."""
    return jsonify({
        k: {
            'requires_target': v['requires_target'],
            'duration': v['duration']
        } for k, v in ALLOWED_COMMANDS.items()
    })

@app.route('/api/network/info', methods=['GET'])
def network_info():
    """Get basic network information."""
    try:
        hostname = socket.gethostname()
        addresses = []
        for addr in socket.getaddrinfo(hostname, None):
            if addr[0] == socket.AF_INET:
                addresses.append(addr[4][0])
        return jsonify({
            'hostname': hostname,
            'addresses': list(set(addresses)),
            'status': 'ok'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
