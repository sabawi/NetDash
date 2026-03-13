#!/usr/bin/env python3
"""
NetDash - Network and System Control Center
Complete implementation: real-time metrics, network tools, dashboard management.
Version: 1.0.0
"""

import os
import re
import json
import time
import uuid
import socket
import platform
import subprocess
import threading
import ipaddress

IS_MACOS = platform.system() == "Darwin"
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Any, Optional
from collections import deque
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import psutil

__version__ = "1.0.4"

# ==============================================================================
# CONFIGURATION
# ==============================================================================

PORT = 8123
HOST = "0.0.0.0"
DEBUG = False
METRICS_INTERVAL = 2      # seconds between metric collection
HISTORY_LENGTH = 300       # 10 minutes at 2-second intervals

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(DATA_DIR, exist_ok=True)

# Whitelisted network/system commands
ALLOWED_COMMANDS = {
    "ping":         {"cmd": "ping",       "args": ["-c", "4"],                   "needs_target": True,  "timeout": 15},
    "ping_quick":   {"cmd": "ping",       "args": ["-c", "1", "-W", "2"],        "needs_target": True,  "timeout": 5},
    "traceroute":   {"cmd": "traceroute", "args": ["-m", "20", "-w", "2"],       "needs_target": True,  "timeout": 60},
    "nmap_ping":    {"cmd": "nmap",       "args": ["-sn", "-T4"],                "needs_target": True,  "timeout": 60},
    "nmap_fast":    {"cmd": "nmap",       "args": ["-F", "-T4"],                 "needs_target": True,  "timeout": 90},
    "nmap_ports":   {"cmd": "nmap",       "args": ["-p", "1-1000", "-T4"],       "needs_target": True,  "timeout": 120},
    "nmap_svc":     {"cmd": "nmap",       "args": ["-sV", "-F", "-T4"],          "needs_target": True,  "timeout": 120},
    "dns_lookup":   {"cmd": "nslookup",   "args": [],                            "needs_target": True,  "timeout": 10},
    "dig":          {"cmd": "dig",        "args": ["+noall", "+answer"],          "needs_target": True,  "timeout": 10},
    "reverse_dns":  {"cmd": "dig",        "args": ["-x"],                        "needs_target": True,  "timeout": 10},
    "whois":        {"cmd": "whois",      "args": [],                            "needs_target": True,  "timeout": 15},
    # Socket / connection listing
    "ss":       {"cmd": "netstat" if IS_MACOS else "ss",
                 "args": ["-an", "-p", "tcp"] if IS_MACOS else ["-tuln"],
                 "needs_target": False, "timeout": 5},
    "ss_all":   {"cmd": "lsof"    if IS_MACOS else "ss",
                 "args": ["-i", "-n", "-P"]   if IS_MACOS else ["-tunap"],
                 "needs_target": False, "timeout": 5},
    # Interface / routing info
    "ip_addr":  {"cmd": "ifconfig" if IS_MACOS else "ip",
                 "args": []                    if IS_MACOS else ["-j", "addr", "show"],
                 "needs_target": False, "timeout": 5},
    "ip_route": {"cmd": "netstat" if IS_MACOS else "ip",
                 "args": ["-rn"]               if IS_MACOS else ["-j", "route", "show"],
                 "needs_target": False, "timeout": 5},
    "ip_neigh": {"cmd": "arp"     if IS_MACOS else "ip",
                 "args": ["-an"]               if IS_MACOS else ["-j", "neigh", "show"],
                 "needs_target": False, "timeout": 5},
    # Disk / memory
    "df":       {"cmd": "df",     "args": ["-h"],                                "needs_target": False, "timeout": 5},
    "free":     {"cmd": "vm_stat" if IS_MACOS else "free",
                 "args": []                    if IS_MACOS else ["-h"],
                 "needs_target": False, "timeout": 5},
    # General
    "uptime":   {"cmd": "uptime", "args": [],                                    "needs_target": False, "timeout": 5},
    "who":      {"cmd": "who",    "args": [],                                    "needs_target": False, "timeout": 5},
    "ps_cpu":   {"cmd": "ps",     "args": ["aux", "-r"]         if IS_MACOS else ["aux", "--sort=-%cpu"], "needs_target": False, "timeout": 5},
    "ps_mem":   {"cmd": "ps",     "args": ["aux", "-m"]         if IS_MACOS else ["aux", "--sort=-%mem"], "needs_target": False, "timeout": 5},
    # System logs / services
    "systemctl_failed": {
        "cmd":  "launchctl"  if IS_MACOS else "systemctl",
        "args": ["list"]     if IS_MACOS else ["--failed"],
        "needs_target": False, "timeout": 10},
    "journalctl": {
        "cmd":  "log"        if IS_MACOS else "journalctl",
        "args": ["show", "--last", "1h", "--style", "syslog"] if IS_MACOS else ["-n", "50", "--no-pager"],
        "needs_target": False, "timeout": 15},
    "dmesg": {
        "cmd":  "dmesg",
        "args": []           if IS_MACOS else ["-T", "--level=err,warn", "-x", "--no-pager"],
        "needs_target": False, "timeout": 10},
}

# ==============================================================================
# METRICS COLLECTORS
# ==============================================================================

class MetricsCollector:
    def __init__(self, name: str, interval: int = METRICS_INTERVAL):
        self.name = name
        self.interval = interval
        self.history: deque = deque(maxlen=HISTORY_LENGTH)
        self.running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                data = self.collect()
                if data:
                    self.history.append({"ts": time.time(), "data": data})
            except Exception as exc:
                print(f"[{self.name}] collection error: {exc}")
            time.sleep(self.interval)

    def collect(self) -> Dict[str, Any]:
        return {}

    def latest(self) -> Optional[Dict[str, Any]]:
        return self.history[-1]["data"] if self.history else None

    def get_history(self, n: int = 60) -> List[Dict[str, Any]]:
        items = list(self.history)[-n:]
        return [{"ts": e["ts"], **e["data"]} for e in items]


class SystemCollector(MetricsCollector):
    def __init__(self):
        super().__init__("system", METRICS_INTERVAL)
        self._prev_net = None
        self._prev_disk = None
        self._prev_time = None

    def collect(self) -> Dict[str, Any]:
        now = time.time()

        cpu_pct = psutil.cpu_percent(interval=None)
        cpu_cores = psutil.cpu_percent(interval=None, percpu=True)
        cpu_freq = psutil.cpu_freq()
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage("/")
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()

        # Compute deltas
        net_delta = {}
        disk_delta = {}
        if self._prev_time:
            dt = now - self._prev_time
            if dt > 0 and self._prev_net:
                net_delta = {
                    "bytes_recv_ps": (net_io.bytes_recv - self._prev_net.bytes_recv) / dt,
                    "bytes_sent_ps": (net_io.bytes_sent - self._prev_net.bytes_sent) / dt,
                }
            if dt > 0 and self._prev_disk and disk_io:
                disk_delta = {
                    "read_bps": (disk_io.read_bytes - self._prev_disk.read_bytes) / dt,
                    "write_bps": (disk_io.write_bytes - self._prev_disk.write_bytes) / dt,
                }

        self._prev_net = net_io
        self._prev_disk = disk_io
        self._prev_time = now

        load_avg = None
        try:
            load_avg = list(os.getloadavg())
        except AttributeError:
            pass

        return {
            "cpu": {
                "percent": cpu_pct,
                "cores": cpu_cores,
                "core_count": len(cpu_cores),
                "freq_mhz": cpu_freq.current if cpu_freq else None,
            },
            "memory": {
                "total": mem.total,
                "used": mem.used,
                "available": mem.available,
                "percent": mem.percent,
                "swap_total": swap.total,
                "swap_used": swap.used,
                "swap_percent": swap.percent,
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
                "read_bps": disk_delta.get("read_bps", 0),
                "write_bps": disk_delta.get("write_bps", 0),
            },
            "network": {
                "bytes_recv": net_io.bytes_recv if net_io else 0,
                "bytes_sent": net_io.bytes_sent if net_io else 0,
                "bytes_recv_ps": net_delta.get("bytes_recv_ps", 0),
                "bytes_sent_ps": net_delta.get("bytes_sent_ps", 0),
            },
            "load_avg": load_avg,
            "uptime": time.time() - psutil.boot_time(),
            "process_count": len(psutil.pids()),
        }


class NetworkCollector(MetricsCollector):
    def __init__(self):
        super().__init__("network", METRICS_INTERVAL)

    def collect(self) -> Dict[str, Any]:
        interfaces = {}
        if_addrs = psutil.net_if_addrs()
        if_stats = psutil.net_if_stats()
        if_io = psutil.net_io_counters(pernic=True)

        for name, addrs in if_addrs.items():
            ipv4 = next((a.address for a in addrs if a.family == socket.AF_INET), None)
            mac = next((a.address for a in addrs if a.family == psutil.AF_LINK), None)
            stats = if_stats.get(name)
            io = if_io.get(name)
            interfaces[name] = {
                "name": name,
                "ipv4": ipv4,
                "mac": mac,
                "is_up": stats.isup if stats else False,
                "speed_mbps": stats.speed if stats else 0,
                "mtu": stats.mtu if stats else 0,
                "bytes_sent": io.bytes_sent if io else 0,
                "bytes_recv": io.bytes_recv if io else 0,
            }

        connections = []
        try:
            for conn in psutil.net_connections(kind="inet")[:100]:
                if conn.laddr:
                    connections.append({
                        "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "",
                        "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "",
                        "status": conn.status or "",
                        "pid": conn.pid,
                    })
        except (psutil.AccessDenied, Exception):
            pass

        return {
            "interfaces": interfaces,
            "connections": connections,
            "connection_count": len(connections),
        }


class ProcessCollector(MetricsCollector):
    def __init__(self):
        super().__init__("processes", 5)

    def collect(self) -> Dict[str, Any]:
        procs = []
        now = time.time()
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent",
                                       "memory_info", "status", "username", "create_time"]):
            try:
                ct = p.info.get("create_time") or now
                procs.append({
                    "pid": p.info["pid"],
                    "name": p.info["name"],
                    "cpu_pct": p.info["cpu_percent"] or 0.0,
                    "mem_pct": round(p.info["memory_percent"] or 0.0, 2),
                    "mem_rss": p.info["memory_info"].rss if p.info["memory_info"] else 0,
                    "status": p.info["status"],
                    "user": p.info["username"],
                    "age_secs": int(now - ct),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        by_cpu = sorted(procs, key=lambda x: x["cpu_pct"], reverse=True)[:15]
        by_mem = sorted(procs, key=lambda x: x["mem_pct"], reverse=True)[:15]

        return {
            "top_cpu": by_cpu,
            "top_mem": by_mem,
            "total": len(procs),
        }


# ==============================================================================
# DASHBOARD PERSISTENCE
# ==============================================================================

class DashboardStore:
    def __init__(self):
        self._dashboards: Dict[str, dict] = {}
        self._load_all()
        if not self._dashboards:
            self._create_default()

    def _path(self, dash_id: str) -> str:
        return os.path.join(DATA_DIR, f"dashboard_{dash_id}.json")

    def _load_all(self):
        for fname in os.listdir(DATA_DIR):
            if fname.startswith("dashboard_") and fname.endswith(".json"):
                try:
                    with open(os.path.join(DATA_DIR, fname)) as f:
                        d = json.load(f)
                        self._dashboards[d["id"]] = d
                except Exception as e:
                    print(f"Load error {fname}: {e}")

    def _create_default(self):
        default = {
            "id": "default",
            "name": "System Overview",
            "description": "Default monitoring dashboard",
            "is_default": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "layout": {"columns": 12, "row_height": 80},
            "cards": [
                {"id": "c1", "type": "system_cpu",     "title": "CPU Usage",     "position": {"x": 0, "y": 0, "w": 3, "h": 2}, "config": {}},
                {"id": "c2", "type": "system_memory",  "title": "Memory",        "position": {"x": 3, "y": 0, "w": 3, "h": 2}, "config": {}},
                {"id": "c3", "type": "system_network", "title": "Network I/O",   "position": {"x": 6, "y": 0, "w": 3, "h": 2}, "config": {}},
                {"id": "c4", "type": "system_disk",    "title": "Disk",          "position": {"x": 9, "y": 0, "w": 3, "h": 2}, "config": {}},
                {"id": "c5", "type": "chart_line",     "title": "CPU History",   "position": {"x": 0, "y": 2, "w": 6, "h": 3}, "config": {"metric": "cpu"}},
                {"id": "c6", "type": "chart_line",     "title": "Memory History","position": {"x": 6, "y": 2, "w": 6, "h": 3}, "config": {"metric": "memory"}},
            ],
        }
        self._dashboards["default"] = default
        self._save("default")

    def _save(self, dash_id: str):
        d = self._dashboards.get(dash_id)
        if d:
            d["updated_at"] = datetime.now().isoformat()
            with open(self._path(dash_id), "w") as f:
                json.dump(d, f, indent=2)

    def list(self) -> List[dict]:
        return list(self._dashboards.values())

    def get(self, dash_id: str) -> Optional[dict]:
        return self._dashboards.get(dash_id)

    def create(self, name: str, description: str = "", cards: list = None) -> dict:
        dash_id = str(uuid.uuid4())[:8]
        d = {
            "id": dash_id, "name": name, "description": description,
            "is_default": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "layout": {"columns": 12, "row_height": 80},
            "cards": cards if cards is not None else [],
        }
        self._dashboards[dash_id] = d
        self._save(dash_id)
        return d

    def update(self, dash_id: str, data: dict) -> Optional[dict]:
        if dash_id not in self._dashboards:
            return None
        allowed = {"name", "description", "layout", "cards"}
        for k in allowed:
            if k in data:
                self._dashboards[dash_id][k] = data[k]
        self._save(dash_id)
        return self._dashboards[dash_id]

    def delete(self, dash_id: str) -> bool:
        if dash_id in self._dashboards:
            del self._dashboards[dash_id]
            p = self._path(dash_id)
            if os.path.exists(p):
                os.remove(p)
            return True
        return False


# ==============================================================================
# ASYNC JOB TRACKER
# ==============================================================================

jobs: Dict[str, dict] = {}
jobs_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=8)


def new_job(command: str, target: str = None) -> dict:
    jid = str(uuid.uuid4())[:8]
    job = {
        "id": jid, "command": command, "target": target,
        "status": "pending", "progress": 0, "message": "Queued",
        "result": None, "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
    }
    with jobs_lock:
        jobs[jid] = job
    return job


def update_job(jid: str, **kwargs):
    with jobs_lock:
        if jid in jobs:
            jobs[jid].update(kwargs)
            jobs[jid]["updated"] = datetime.now().isoformat()


def validate_target(target: str) -> bool:
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
    # hostname or domain
    if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', target):
        return True
    return False


def _run_job(jid: str, command_key: str, target: str = None):
    if command_key not in ALLOWED_COMMANDS:
        update_job(jid, status="error", message=f"Unknown command: {command_key}")
        return

    cfg = ALLOWED_COMMANDS[command_key]
    if cfg["needs_target"] and not validate_target(target):
        update_job(jid, status="error", message="Invalid target")
        return

    update_job(jid, status="running", progress=20, message=f"Running {command_key}...")

    try:
        args = [cfg["cmd"]] + list(cfg["args"])
        if target:
            args.append(target)

        result = subprocess.run(
            args, capture_output=True, text=True, timeout=cfg["timeout"]
        )
        update_job(
            jid,
            status="completed" if result.returncode == 0 else "error",
            progress=100,
            message="Done" if result.returncode == 0 else f"Exit {result.returncode}",
            result={"output": result.stdout or result.stderr, "exit_code": result.returncode},
        )
    except subprocess.TimeoutExpired:
        update_job(jid, status="error", progress=0, message="Timed out")
    except FileNotFoundError:
        update_job(jid, status="error", message=f"Command not found: {cfg['cmd']}")
    except Exception as exc:
        update_job(jid, status="error", message=str(exc))


def _run_command_sync(command_key: str, target: str = None) -> dict:
    """Run command synchronously and return output."""
    if command_key not in ALLOWED_COMMANDS:
        return {"error": f"Unknown command: {command_key}", "output": ""}

    cfg = ALLOWED_COMMANDS[command_key]
    args = [cfg["cmd"]] + list(cfg["args"])
    if target:
        args.append(target)

    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=cfg["timeout"])
        return {
            "output": result.stdout or result.stderr,
            "exit_code": result.returncode,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Timed out", "output": ""}
    except FileNotFoundError:
        return {"error": f"Command not found: {cfg['cmd']}", "output": ""}
    except Exception as exc:
        return {"error": str(exc), "output": ""}


# ==============================================================================
# FLASK APPLICATION
# ==============================================================================

app = Flask(__name__, static_folder=STATIC_DIR)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", str(uuid.uuid4()))
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Initialize stores and collectors
store = DashboardStore()
sys_collector = SystemCollector()
net_collector = NetworkCollector()
proc_collector = ProcessCollector()

sys_collector.start()
net_collector.start()
proc_collector.start()


# ==============================================================================
# STATIC ROUTES
# ==============================================================================

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "dashboard.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(STATIC_DIR, path)


# ==============================================================================
# METRICS API
# ==============================================================================

@app.route("/api/metrics/system")
def api_system_metrics():
    return jsonify(sys_collector.latest() or {})

@app.route("/api/metrics/system/history")
def api_system_history():
    n = request.args.get("n", 60, type=int)
    return jsonify(sys_collector.get_history(n))

@app.route("/api/metrics/network")
def api_network_metrics():
    return jsonify(net_collector.latest() or {})

@app.route("/api/metrics/processes")
def api_process_metrics():
    return jsonify(proc_collector.latest() or {})


# ==============================================================================
# SYSTEM INFO API
# ==============================================================================

@app.route("/api/system/info")
def api_system_info():
    try:
        hostname = socket.gethostname()
        boot = psutil.boot_time()
        uptime_secs = time.time() - boot
        return jsonify({
            "hostname": hostname,
            "uptime_seconds": uptime_secs,
            "boot_time": datetime.fromtimestamp(boot).isoformat(),
            "python_version": __import__("sys").version,
            "netdash_version": __version__,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/system/interfaces")
def api_system_interfaces():
    net_data = net_collector.latest()
    if net_data:
        return jsonify(list(net_data.get("interfaces", {}).values()))
    return jsonify([])

@app.route("/api/system/connections")
def api_system_connections():
    net_data = net_collector.latest()
    if net_data:
        return jsonify(net_data.get("connections", []))
    return jsonify([])

@app.route("/api/system/disks")
def api_system_disks():
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            })
        except (PermissionError, OSError):
            pass
    return jsonify(disks)


# ==============================================================================
# DASHBOARD API
# ==============================================================================

@app.route("/api/dashboards", methods=["GET"])
def api_list_dashboards():
    return jsonify([{
        "id": d["id"], "name": d["name"],
        "description": d.get("description", ""),
        "is_default": d.get("is_default", False),
        "card_count": len(d.get("cards", [])),
        "updated_at": d.get("updated_at"),
    } for d in store.list()])

@app.route("/api/dashboards", methods=["POST"])
def api_create_dashboard():
    data = request.get_json() or {}
    name = data.get("name", "New Dashboard")
    desc = data.get("description", "")
    cards = data.get("cards")  # may be None (no cards key) or a list
    d = store.create(name, desc, cards)
    return jsonify(d), 201

@app.route("/api/dashboards/<dash_id>", methods=["GET"])
def api_get_dashboard(dash_id):
    d = store.get(dash_id)
    if not d:
        return jsonify({"error": "Not found"}), 404
    return jsonify(d)

@app.route("/api/dashboards/<dash_id>", methods=["PUT"])
def api_update_dashboard(dash_id):
    data = request.get_json() or {}
    d = store.update(dash_id, data)
    if not d:
        return jsonify({"error": "Not found"}), 404
    return jsonify(d)

@app.route("/api/dashboards/<dash_id>", methods=["DELETE"])
def api_delete_dashboard(dash_id):
    if store.delete(dash_id):
        return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404

@app.route("/api/card-types")
def api_card_types():
    return jsonify({
        "system_cpu":     {"name": "CPU Monitor",       "icon": "microchip",      "category": "system"},
        "system_memory":  {"name": "Memory Usage",      "icon": "memory",         "category": "system"},
        "system_disk":    {"name": "Disk Usage",        "icon": "hdd",            "category": "system"},
        "system_network": {"name": "Network I/O",       "icon": "network-wired",  "category": "system"},
        "system_procs":   {"name": "Process List",      "icon": "list",           "category": "system"},
        "chart_line":     {"name": "Line Chart",        "icon": "chart-line",     "category": "chart"},
        "chart_gauge":    {"name": "Gauge",             "icon": "tachometer-alt", "category": "chart"},
        "net_ping":       {"name": "Ping Monitor",      "icon": "satellite-dish", "category": "network"},
        "net_interfaces": {"name": "Interface Status",  "icon": "ethernet",       "category": "network"},
        "net_connections":{"name": "Active Connections","icon": "project-diagram","category": "network"},
        "cmd_output":     {"name": "Command Output",    "icon": "terminal",       "category": "tools"},
    })


# ==============================================================================
# ASYNC JOB API
# ==============================================================================

@app.route("/api/jobs", methods=["POST"])
def api_create_job():
    data = request.get_json() or {}
    command = data.get("command")
    target = data.get("target")

    if not command or command not in ALLOWED_COMMANDS:
        return jsonify({"error": f"Unknown command: {command}"}), 400

    job = new_job(command, target)
    executor.submit(_run_job, job["id"], command, target)
    return jsonify({"job_id": job["id"], "status": "pending"}), 202

@app.route("/api/jobs/<jid>", methods=["GET"])
def api_get_job(jid):
    with jobs_lock:
        job = jobs.get(jid)
    if not job:
        return jsonify({"error": "Not found"}), 404
    return jsonify(job)

@app.route("/api/jobs", methods=["GET"])
def api_list_jobs():
    with jobs_lock:
        return jsonify(list(jobs.values()))

@app.route("/api/commands")
def api_list_commands():
    return jsonify({k: {"needs_target": v["needs_target"], "timeout": v["timeout"]}
                    for k, v in ALLOWED_COMMANDS.items()})


# ==============================================================================
# NETWORK TOOLS API (synchronous, quick)
# ==============================================================================

@app.route("/api/network/ping", methods=["POST"])
def api_ping():
    data = request.get_json() or {}
    target = data.get("target", "")
    if not validate_target(target):
        return jsonify({"error": "Invalid target"}), 400
    res = _run_command_sync("ping", target)
    return jsonify({"target": target, **res})

@app.route("/api/network/traceroute", methods=["POST"])
def api_traceroute():
    data = request.get_json() or {}
    target = data.get("target", "")
    if not validate_target(target):
        return jsonify({"error": "Invalid target"}), 400
    job = new_job("traceroute", target)
    executor.submit(_run_job, job["id"], "traceroute", target)
    return jsonify({"job_id": job["id"]}), 202

@app.route("/api/network/scan", methods=["POST"])
def api_scan():
    data = request.get_json() or {}
    target = data.get("target", "")
    scan_type = data.get("type", "nmap_fast")
    if scan_type not in ("nmap_fast", "nmap_ports", "nmap_svc", "nmap_ping"):
        scan_type = "nmap_fast"
    if not validate_target(target):
        return jsonify({"error": "Invalid target"}), 400
    job = new_job(scan_type, target)
    executor.submit(_run_job, job["id"], scan_type, target)
    return jsonify({"job_id": job["id"]}), 202

@app.route("/api/network/dns", methods=["POST"])
def api_dns():
    data = request.get_json() or {}
    target = data.get("target", "")
    query_type = data.get("type", "dns_lookup")
    if query_type not in ("dns_lookup", "dig", "reverse_dns", "whois"):
        query_type = "dns_lookup"
    if not validate_target(target):
        return jsonify({"error": "Invalid target"}), 400
    res = _run_command_sync(query_type, target)
    return jsonify({"target": target, **res})


# ==============================================================================
# TOPOLOGY EXPLORER API
# ==============================================================================

def _get_local_subnets():
    subnets = []
    if_addrs = psutil.net_if_addrs()
    if_stats = psutil.net_if_stats()
    gateway = None
    try:
        if IS_MACOS:
            r = subprocess.run(["route", "-n", "get", "default"], capture_output=True, text=True, timeout=5)
            for line in r.stdout.splitlines():
                if "gateway:" in line:
                    gateway = line.split("gateway:")[-1].strip()
                    break
        else:
            r = subprocess.run(["ip", "-j", "route", "show"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                for route in json.loads(r.stdout or "[]"):
                    if route.get("dst") == "default":
                        gateway = route.get("gateway")
                        break
    except Exception:
        pass
    for iface, addrs in if_addrs.items():
        stats = if_stats.get(iface)
        if not stats or not stats.isup:
            continue
        for addr in addrs:
            if addr.family != socket.AF_INET:
                continue
            if addr.address.startswith("127."):
                continue
            try:
                net = ipaddress.ip_interface(f"{addr.address}/{addr.netmask}").network
                subnets.append({
                    "interface": iface,
                    "ip": addr.address,
                    "netmask": addr.netmask,
                    "subnet": str(net),
                    "gateway": gateway,
                    "prefix_len": net.prefixlen,
                    "host_count": net.num_addresses - 2,
                })
            except Exception:
                pass
    return subnets


def _parse_nmap_hosts(output: str) -> list:
    hosts = []
    current: dict = {}
    for line in output.splitlines():
        m = re.match(r'Nmap scan report for (.+)', line)
        if m:
            if current.get("ip"):
                hosts.append(current)
            raw = m.group(1).strip()
            hm = re.match(r'^(.+?)\s+\((\d+\.\d+\.\d+\.\d+)\)$', raw)
            if hm:
                current = {"hostname": hm.group(1), "ip": hm.group(2), "mac": "", "vendor": "", "state": "up"}
            else:
                current = {"hostname": "", "ip": raw, "mac": "", "vendor": "", "state": "up"}
        elif "Host is up" in line and current:
            current["state"] = "reachable"
        elif "Host is down" in line and current:
            current["state"] = "down"
        elif line.startswith("MAC Address:") and current:
            mm = re.match(r'MAC Address: ([0-9A-Fa-f:]+)\s*(?:\((.+?)\))?', line)
            if mm:
                current["mac"] = mm.group(1)
                current["vendor"] = mm.group(2) or ""
    if current.get("ip"):
        hosts.append(current)
    return hosts


def _parse_nmap_ports(output: str) -> list:
    ports = []
    for line in output.splitlines():
        m = re.match(r'(\d+)/(tcp|udp)\s+(open|filtered)\s+(\S+)(?:\s+(.+))?', line)
        if m:
            ports.append({
                "port": int(m.group(1)),
                "proto": m.group(2),
                "state": m.group(3),
                "service": m.group(4),
                "version": (m.group(5) or "").strip(),
            })
    return ports


def _enrich_with_arp(hosts: list) -> list:
    """Add MAC/vendor from kernel ARP cache for any hosts missing a MAC."""
    try:
        if IS_MACOS:
            r = subprocess.run(["arp", "-an"], capture_output=True, text=True, timeout=5)
            arp_map = {}
            for line in r.stdout.splitlines():
                m = re.match(r'\S+\s+\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-fA-F:]+)\s+on\s+(\S+)', line)
                if m:
                    arp_map[m.group(1)] = m.group(2)
        else:
            r = subprocess.run(["ip", "-j", "neigh", "show"], capture_output=True, text=True, timeout=5)
            arp_map = {}
            for n in json.loads(r.stdout or "[]"):
                if n.get("dst") and n.get("lladdr"):
                    arp_map[n["dst"]] = n["lladdr"]
        for h in hosts:
            if not h.get("mac") and h.get("ip") in arp_map:
                h["mac"] = arp_map[h["ip"]]
    except Exception:
        pass
    return hosts


def _topo_sweep_job(jid: str, subnet: str):
    update_job(jid, status="running", progress=10, message=f"Sweeping {subnet}...")
    try:
        r = subprocess.run(["nmap", "-sn", "-T4", subnet], capture_output=True, text=True, timeout=60)
        hosts = _parse_nmap_hosts(r.stdout)
        update_job(jid, status="running", progress=75, message=f"Found {len(hosts)} host(s), resolving MACs and names...")
        hosts = _enrich_with_arp(hosts)
        hosts = _resolve_hostnames(hosts)
        update_job(jid, status="completed", progress=100,
                   message=f"Found {len(hosts)} host(s)",
                   result={"hosts": hosts, "output": r.stdout})
    except subprocess.TimeoutExpired:
        update_job(jid, status="error", progress=0, message="Sweep timed out")
    except FileNotFoundError:
        # nmap not installed — fall back to ARP cache
        try:
            if IS_MACOS:
                r2 = subprocess.run(["arp", "-an"], capture_output=True, text=True, timeout=5)
                hosts = _parse_arp_an(r2.stdout)
            else:
                r2 = subprocess.run(["ip", "-j", "neigh", "show"], capture_output=True, text=True, timeout=5)
                neighbors = json.loads(r2.stdout or "[]")
                hosts = []
                for n in neighbors:
                    state = n.get("state", [])
                    if isinstance(state, list): state = state[0] if state else ""
                    if str(state).upper() in ("REACHABLE", "STALE", "DELAY", "PROBE", "PERMANENT"):
                        hosts.append({"ip": n.get("dst", ""), "hostname": "", "mac": n.get("lladdr", ""), "vendor": "", "state": str(state).lower()})
            update_job(jid, status="completed", progress=100,
                       message=f"Found {len(hosts)} host(s) (ARP cache only — install nmap for full sweep)",
                       result={"hosts": hosts, "output": "ARP cache fallback — nmap not installed"})
        except Exception as exc:
            update_job(jid, status="error", message=str(exc))
    except Exception as exc:
        update_job(jid, status="error", message=str(exc))


def _topo_portscan_job(jid: str, host: str, mode: str):
    args_map = {
        "fast":    ["nmap", "-F", "-T4", "--open", host],
        "full":    ["nmap", "-p", "1-1000", "-T4", "--open", host],
        "service": ["nmap", "-sV", "-F", "-T4", "--open", host],
    }
    args = args_map.get(mode, args_map["fast"])
    update_job(jid, status="running", progress=10, message=f"Scanning {host} ({mode} mode)...")
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=120)
        ports = _parse_nmap_ports(r.stdout)
        update_job(jid, status="completed", progress=100,
                   message=f"Found {len(ports)} open port(s)",
                   result={"ports": ports, "host": host, "output": r.stdout})
    except subprocess.TimeoutExpired:
        update_job(jid, status="error", progress=0, message="Scan timed out")
    except FileNotFoundError:
        update_job(jid, status="error", message="nmap not found — install with: sudo apt install nmap")
    except Exception as exc:
        update_job(jid, status="error", message=str(exc))


@app.route("/api/topology/subnets")
def api_topo_subnets():
    try:
        hostname = socket.gethostname()
        addrs = []
        for a in socket.getaddrinfo(hostname, None):
            if a[0] == socket.AF_INET:
                addrs.append(a[4][0])
        subnets = _get_local_subnets()
        return jsonify({"hostname": hostname, "addresses": list(set(addrs)), "subnets": subnets})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _resolve_hostnames(hosts: list) -> list:
    """Reverse-DNS each host IP concurrently; fills hostname if not already set."""
    def _rdns(h):
        if h.get("hostname"):
            return h
        try:
            name, _, _ = socket.gethostbyaddr(h["ip"])
            if name and name != h["ip"]:
                h["hostname"] = name
        except Exception:
            pass
        return h

    with ThreadPoolExecutor(max_workers=30) as ex:
        futures = {ex.submit(_rdns, h): h for h in hosts}
        resolved = []
        for fut, orig in futures.items():
            try:
                resolved.append(fut.result(timeout=2))
            except Exception:
                resolved.append(orig)
    return resolved


def _parse_arp_an(output: str) -> list:
    """Parse `arp -an` output (macOS/BSD format) into host list."""
    hosts = []
    for line in output.splitlines():
        # ? (192.168.1.1) at aa:bb:cc:dd:ee:ff on en0 ifscope [ethernet]
        m = re.match(r'\S+\s+\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-fA-F:]+)\s+on\s+(\S+)', line)
        if m and m.group(2).lower() not in ("(incomplete)", "ff:ff:ff:ff:ff:ff"):
            hosts.append({"ip": m.group(1), "mac": m.group(2), "dev": m.group(3),
                          "state": "reachable", "hostname": "", "vendor": ""})
    return hosts


@app.route("/api/topology/arp")
def api_topo_arp():
    try:
        if IS_MACOS:
            r = subprocess.run(["arp", "-an"], capture_output=True, text=True, timeout=5)
            hosts = _parse_arp_an(r.stdout)
        else:
            r = subprocess.run(["ip", "-j", "neigh", "show"], capture_output=True, text=True, timeout=5)
            neighbors = json.loads(r.stdout or "[]")
            hosts = []
            for n in neighbors:
                state = n.get("state", [])
                if isinstance(state, list): state = state[0] if state else ""
                if str(state).upper() in ("REACHABLE", "STALE", "DELAY", "PROBE", "PERMANENT"):
                    hosts.append({"ip": n.get("dst", ""), "mac": n.get("lladdr", ""),
                                  "dev": n.get("dev", ""), "state": str(state).lower(),
                                  "hostname": "", "vendor": ""})
        return jsonify(_resolve_hostnames(hosts))
    except Exception:
        return jsonify([])


@app.route("/api/topology/sweep", methods=["POST"])
def api_topo_sweep():
    data = request.get_json() or {}
    subnet = data.get("subnet", "")
    try:
        ipaddress.ip_network(subnet, strict=False)
    except ValueError:
        return jsonify({"error": "Invalid subnet"}), 400
    job = new_job("topo_sweep", subnet)
    executor.submit(_topo_sweep_job, job["id"], subnet)
    return jsonify({"job_id": job["id"]}), 202


@app.route("/api/topology/portscan", methods=["POST"])
def api_topo_portscan():
    data = request.get_json() or {}
    host = data.get("host", "")
    mode = data.get("mode", "fast")
    if not validate_target(host):
        return jsonify({"error": "Invalid host"}), 400
    if mode not in ("fast", "full", "service"):
        mode = "fast"
    job = new_job("topo_portscan", host)
    executor.submit(_topo_portscan_job, job["id"], host, mode)
    return jsonify({"job_id": job["id"]}), 202


# ==============================================================================
# COMMAND EXECUTION API
# ==============================================================================

@app.route("/api/system/command", methods=["POST"])
def api_exec_command():
    data = request.get_json() or {}
    cmd = data.get("command", "")
    if cmd not in ALLOWED_COMMANDS:
        return jsonify({"error": f"Command not allowed: {cmd}"}), 403
    res = _run_command_sync(cmd)
    return jsonify({"command": cmd, **res})


# ==============================================================================
# WEBSOCKET EVENTS
# ==============================================================================

@socketio.on("connect")
def ws_connect():
    emit("connected", {"version": __version__, "message": "NetDash connected"})

@socketio.on("disconnect")
def ws_disconnect():
    pass

@socketio.on("subscribe")
def ws_subscribe(data):
    room = data.get("room", "metrics")
    join_room(room)
    emit("subscribed", {"room": room})

@socketio.on("unsubscribe")
def ws_unsubscribe(data):
    room = data.get("room", "metrics")
    leave_room(room)

@socketio.on("ping_target")
def ws_ping(data):
    target = data.get("target", "")
    if not validate_target(target):
        emit("ping_result", {"error": "Invalid target"})
        return
    res = _run_command_sync("ping", target)
    emit("ping_result", {"target": target, **res})

@socketio.on("execute_command")
def ws_exec(data):
    cmd = data.get("command", "")
    target = data.get("target")
    if cmd not in ALLOWED_COMMANDS:
        emit("command_result", {"error": f"Not allowed: {cmd}"})
        return
    res = _run_command_sync(cmd, target)
    emit("command_result", {"command": cmd, **res})


def _broadcast_loop():
    """Background thread that pushes metrics to all connected clients every 2s."""
    while True:
        try:
            sys_data = sys_collector.latest()
            if sys_data:
                socketio.emit("metrics_system", sys_data, room="metrics")

            net_data = net_collector.latest()
            if net_data:
                socketio.emit("metrics_network", net_data, room="metrics")

        except Exception as exc:
            print(f"[broadcast] error: {exc}")
        time.sleep(METRICS_INTERVAL)


_broadcast_thread = threading.Thread(target=_broadcast_loop, daemon=True)
_broadcast_thread.start()


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print(f"NetDash v{__version__} - Network & System Control Center")
    print(f"Listening on http://{HOST}:{PORT}")
    print(f"Data directory: {DATA_DIR}")
    print(f"Dashboards loaded: {len(store.list())}")
    print("=" * 60)
    socketio.run(app, host=HOST, port=PORT, debug=DEBUG, allow_unsafe_werkzeug=True)
