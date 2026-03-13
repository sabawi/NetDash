/**
 * Network Dashboard - Complete Frontend Application
 * Fully functional UI with tabs, loading indicators, results display, and user guidance
 */

class NetworkDashboard {
    constructor() {
        this.apiBase = '/api';
        this.activeJobs = new Map();
        this.currentTab = 'discovery';
        this.pollingInterval = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadNetworkInfo();
        this.startPolling();
        this.showWelcomeGuide();
        this.checkBackendStatus();
    }

    // ============================================
    // EVENT BINDINGS
    // ============================================
    bindEvents() {
        // Tab navigation
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Discovery tab buttons
        document.getElementById('btn-discover')?.addEventListener('click', () => this.discoverHosts());
        document.getElementById('btn-arp')?.addEventListener('click', () => this.arpScan());
        document.getElementById('btn-ping-sweep')?.addEventListener('click', () => this.pingSweep());
        document.getElementById('host-filter')?.addEventListener('input', (e) => this.filterHosts(e.target.value));
        document.getElementById('btn-export-hosts')?.addEventListener('click', () => this.exportHostsCSV());

        // Interfaces tab
        document.getElementById('btn-refresh-interfaces')?.addEventListener('click', () => this.loadInterfaces());

        // Connections tab
        document.getElementById('btn-refresh-connections')?.addEventListener('click', () => this.loadConnections());
        document.getElementById('conn-filter')?.addEventListener('change', () => this.loadConnections());

        // Port Scanner tab
        document.getElementById('btn-scan')?.addEventListener('click', () => this.portScan());
        document.getElementById('scan-preset')?.addEventListener('change', (e) => this.updatePortRange(e.target.value));

        // DNS Tools tab
        document.getElementById('btn-dns-lookup')?.addEventListener('click', () => this.dnsLookup());
        document.getElementById('btn-reverse-dns')?.addEventListener('click', () => this.reverseDNS());
        document.getElementById('btn-whois')?.addEventListener('click', () => this.whoisLookup());
        document.getElementById('btn-dig')?.addEventListener('click', () => this.digLookup());

        // Topology tab
        document.getElementById('btn-refresh-topology')?.addEventListener('click', () => this.loadTopology());
        document.getElementById('btn-export-topology')?.addEventListener('click', () => this.exportTopology());

        // Quick actions
        document.getElementById('btn-quick-ping')?.addEventListener('click', () => this.quickPing());
        document.getElementById('btn-quick-traceroute')?.addEventListener('click', () => this.quickTraceroute());
        document.getElementById('btn-clear-results')?.addEventListener('click', () => this.clearResults());

        // Help system
        document.getElementById('btn-help')?.addEventListener('click', () => this.toggleHelp());
        document.getElementById('btn-close-help')?.addEventListener('click', () => this.toggleHelp());
        document.querySelectorAll('.help-icon').forEach(icon => {
            icon.addEventListener('click', (e) => this.showTooltip(e));
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    // ============================================
    // TAB NAVIGATION
    // ============================================
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === tabName);
        });

        this.currentTab = tabName;

        // Load tab-specific data
        switch(tabName) {
            case 'interfaces':
                this.loadInterfaces();
                break;
            case 'connections':
                this.loadConnections();
                break;
            case 'topology':
                this.loadTopology();
                break;
        }

        this.addNotification(`Switched to ${this.capitalize(tabName)} tab`, 'info');
    }

    // ============================================
    // NETWORK DISCOVERY
    // ============================================
    async discoverHosts() {
        const subnet = document.getElementById('subnet')?.value || '192.168.1.0/24';
        
        if (!this.validateSubnet(subnet)) {
            this.showError('Invalid subnet format. Use CIDR notation (e.g., 192.168.1.0/24)');
            return;
        }

        this.showLoading('discovery', 'Scanning network for hosts...');
        this.addNotification(`Starting network discovery on ${subnet}`, 'info');

        try {
            const response = await fetch(`${this.apiBase}/discover`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({subnet, method: 'nmap'})
            });

            const data = await response.json();
            
            if (data.job_id) {
                this.pollJobStatus(data.job_id, (result) => {
                    this.hideLoading('discovery');
                    this.displayHosts(result.hosts || []);
                    this.addNotification(`Discovered ${result.hosts?.length || 0} hosts`, 'success');
                });
            } else {
                this.hideLoading('discovery');
                this.displayHosts(data.hosts || []);
            }
        } catch (error) {
            this.hideLoading('discovery');
            this.showError('Network discovery failed: ' + error.message);
        }
    }

    async arpScan() {
        this.showLoading('discovery', 'Performing ARP scan...');
        
        try {
            const response = await fetch(`${this.apiBase}/arp-scan`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            
            const data = await response.json();
            this.hideLoading('discovery');
            this.displayHosts(data.hosts || [], 'ARP Scan Results');
            this.addNotification(`ARP scan found ${data.hosts?.length || 0} hosts`, 'success');
        } catch (error) {
            this.hideLoading('discovery');
            this.showError('ARP scan failed: ' + error.message);
        }
    }

    async pingSweep() {
        const subnet = document.getElementById('subnet')?.value || '192.168.1.0/24';
        
        this.showLoading('discovery', 'Performing ping sweep... This may take a minute.');
        this.addNotification('Ping sweep started...', 'info');

        try {
            const response = await fetch(`${this.apiBase}/ping-sweep`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({subnet})
            });
            
            const data = await response.json();
            
            if (data.job_id) {
                this.pollJobStatus(data.job_id, (result) => {
                    this.hideLoading('discovery');
                    this.displayHosts(result.hosts || [], 'Ping Sweep Results');
                    this.addNotification(`Ping sweep found ${result.hosts?.length || 0} responsive hosts`, 'success');
                });
            }
        } catch (error) {
            this.hideLoading('discovery');
            this.showError('Ping sweep failed: ' + error.message);
        }
    }

    displayHosts(hosts, title = 'Discovered Hosts') {
        const tbody = document.getElementById('hosts-body');
        const heading = document.querySelector('#discovery .results h3');
        
        if (heading) heading.textContent = title;
        
        if (!hosts || hosts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="no-results">No hosts discovered. Try a different subnet or check your network connection.</td></tr>';
            return;
        }

        tbody.innerHTML = hosts.map(host => `
            <tr data-ip="${host.ip}">
                <td>${host.ip}</td>
                <td>${host.mac || 'N/A'}</td>
                <td>${host.hostname || 'Unknown'}</td>
                <td><span class="status-badge ${host.status === 'up' ? 'online' : 'offline'}">${host.status}</span></td>
                <td>${host.response_time || 'N/A'}</td>
                <td>
                    <button class="btn-icon" onclick="dashboard.quickPing('${host.ip}')" title="Ping">🔍</button>
                    <button class="btn-icon" onclick="dashboard.portScanHost('${host.ip}')" title="Scan Ports">🚪</button>
                </td>
            </tr>
        `).join('');

        // Store for filtering
        this.currentHosts = hosts;
    }

    filterHosts(query) {
        const rows = document.querySelectorAll('#hosts-body tr');
        const lowerQuery = query.toLowerCase();
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(lowerQuery) ? '' : 'none';
        });
    }

    // ============================================
    // INTERFACES
    // ============================================
    async loadInterfaces() {
        this.showLoading('interfaces', 'Loading network interfaces...');
        
        try {
            const response = await fetch(`${this.apiBase}/interfaces`);
            const data = await response.json();
            
            this.hideLoading('interfaces');
            this.displayInterfaces(data.interfaces || []);
        } catch (error) {
            this.hideLoading('interfaces');
            this.showError('Failed to load interfaces: ' + error.message);
        }
    }

    displayInterfaces(interfaces) {
        const grid = document.getElementById('interfaces-grid');
        
        if (!interfaces || interfaces.length === 0) {
            grid.innerHTML = '<div class="no-results">No interfaces found.</div>';
            return;
        }

        grid.innerHTML = interfaces.map(iface => `
            <div class="interface-card ${iface.state === 'UP' ? 'up' : 'down'}">
                <div class="interface-header">
                    <h4>${iface.name}</h4>
                    <span class="state-badge ${iface.state === 'UP' ? 'up' : 'down'}">${iface.state}</span>
                </div>
                <div class="interface-details">
                    <div class="detail-row">
                        <span class="label">IP Address:</span>
                        <span class="value">${iface.ip || 'N/A'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">MAC:</span>
                        <span class="value">${iface.mac || 'N/A'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Gateway:</span>
                        <span class="value">${iface.gateway || 'N/A'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">RX:</span>
                        <span class="value">${this.formatBytes(iface.rx_bytes)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">TX:</span>
                        <span class="value">${this.formatBytes(iface.tx_bytes)}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // ============================================
    // CONNECTIONS
    // ============================================
    async loadConnections() {
        this.showLoading('connections', 'Loading active connections...');
        const filter = document.getElementById('conn-filter')?.value || 'all';
        
        try {
            const response = await fetch(`${this.apiBase}/connections?filter=${filter}`);
            const data = await response.json();
            
            this.hideLoading('connections');
            this.displayConnections(data.connections || []);
        } catch (error) {
            this.hideLoading('connections');
            this.showError('Failed to load connections: ' + error.message);
        }
    }

    displayConnections(connections) {
        const tbody = document.getElementById('connections-body');
        
        if (!connections || connections.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="no-results">No active connections found.</td></tr>';
            return;
        }

        tbody.innerHTML = connections.map(conn => `
            <tr>
                <td><span class="protocol-badge ${conn.protocol.toLowerCase()}">${conn.protocol}</span></td>
                <td>${conn.local_addr}</td>
                <td>${conn.remote_addr}</td>
                <td><span class="state-badge ${conn.state?.toLowerCase()}">${conn.state}</span></td>
                <td>${conn.pid || 'N/A'}</td>
                <td>${conn.process || 'Unknown'}</td>
            </tr>
        `).join('');
    }

    // ============================================
    // PORT SCANNER
    // ============================================
    async portScan() {
        const target = document.getElementById('scan-target')?.value.trim();
        const ports = document.getElementById('scan-ports')?.value || '1-1000';
        const scanType = document.getElementById('scan-type')?.value || 'tcp';
        
        if (!target) {
            this.showError('Please enter a target host or IP');
            return;
        }

        this.showLoading('ports', `Scanning ${target} ports ${ports}... This may take several minutes.`);
        this.addNotification(`Port scan started on ${target}`, 'info');

        try {
            const response = await fetch(`${this.apiBase}/port-scan`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({target, ports, type: scanType})
            });
            
            const data = await response.json();
            
            if (data.job_id) {
                this.pollJobStatus(data.job_id, (result) => {
                    this.hideLoading('ports');
                    this.displayPortResults(result);
                    this.addNotification(`Scan complete. Found ${result.open_ports?.length || 0} open ports.`, 'success');
                });
            }
        } catch (error) {
            this.hideLoading('ports');
            this.showError('Port scan failed: ' + error.message);
        }
    }

    updatePortRange(preset) {
        const portsInput = document.getElementById('scan-ports');
        const presets = {
            'common': '21,22,23,25,53,80,110,143,443,445,993,995,3306,3389,5900,8080',
            'quick': '1-1000',
            'full': '1-65535',
            'web': '80,443,8080,8443,3000,4200,5000,8000',
            'database': '3306,5432,1433,27017,6379,9200'
        };
        if (portsInput && presets[preset]) {
            portsInput.value = presets[preset];
        }
    }

    displayPortResults(result) {
        const container = document.getElementById('port-results');
        const ports = result.open_ports || [];
        
        if (ports.length === 0) {
            container.innerHTML = '<div class="no-results">No open ports found or host is unreachable.</div>';
            return;
        }

        container.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Port</th>
                        <th>Protocol</th>
                        <th>Service</th>
                        <th>Version</th>
                        <th>State</th>
                    </tr>
                </thead>
                <tbody>
                    ${ports.map(p => `
                        <tr>
                            <td>${p.port}</td>
                            <td>${p.protocol}</td>
                            <td>${p.service || 'Unknown'}</td>
                            <td>${p.version || 'N/A'}</td>
                            <td><span class="status-badge open">Open</span></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    // ============================================
    // DNS TOOLS
    // ============================================
    async dnsLookup() {
        const domain = document.getElementById('dns-target')?.value.trim();
        if (!domain) {
            this.showError('Please enter a domain name');
            return;
        }

        this.showLoading('dns', 'Looking up DNS records...');
        
        try {
            const response = await fetch(`${this.apiBase}/dns-lookup`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({domain, type: 'A'})
            });
            
            const data = await response.json();
            this.hideLoading('dns');
            this.displayDNSResults(data);
        } catch (error) {
            this.hideLoading('dns');
            this.showError('DNS lookup failed: ' + error.message);
        }
    }

    async reverseDNS() {
        const ip = document.getElementById('dns-target')?.value.trim();
        if (!ip || !this.validateIP(ip)) {
            this.showError('Please enter a valid IP address');
            return;
        }

        this.showLoading('dns', 'Performing reverse DNS lookup...');
        
        try {
            const response = await fetch(`${this.apiBase}/reverse-dns`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ip})
            });
            
            const data = await response.json();
            this.hideLoading('dns');
            this.displayDNSResults(data, 'Reverse DNS Results');
        } catch (error) {
            this.hideLoading('dns');
            this.showError('Reverse DNS lookup failed: ' + error.message);
        }
    }

    async whoisLookup() {
        const target = document.getElementById('dns-target')?.value.trim();
        if (!target) {
            this.showError('Please enter a domain or IP');
            return;
        }

        this.showLoading('dns', 'Performing WHOIS lookup...');
        
        try {
            const response = await fetch(`${this.apiBase}/whois`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({target})
            });
            
            const data = await response.json();
            this.hideLoading('dns');
            this.displayWHOISResults(data);
        } catch (error) {
            this.hideLoading('dns');
            this.showError('WHOIS lookup failed: ' + error.message);
        }
    }

    async digLookup() {
        const target = document.getElementById('dns-target')?.value.trim();
        if (!target) {
            this.showError('Please enter a domain name');
            return;
        }

        this.showLoading('dns', 'Performing DIG lookup...');
        
        try {
            const response = await fetch(`${this.apiBase}/dig`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({domain: target, type: 'ANY'})
            });
            
            const data = await response.json();
            this.hideLoading('dns');
            this.displayRawOutput(data.output || data);
        } catch (error) {
            this.hideLoading('dns');
            this.showError('DIG lookup failed: ' + error.message);
        }
    }

    displayDNSResults(data, title = 'DNS Lookup Results') {
        const container = document.getElementById('dns-results');
        container.innerHTML = `
            <h4>${title}</h4>
            <pre class="code-output">${JSON.stringify(data, null, 2)}</pre>
        `;
    }

    displayWHOISResults(data) {
        const container = document.getElementById('dns-results');
        container.innerHTML = `
            <h4>WHOIS Results</h4>
            <pre class="code-output">${data.output || JSON.stringify(data, null, 2)}</pre>
        `;
    }

    displayRawOutput(data) {
        const container = document.getElementById('dns-results');
        container.innerHTML = `<pre class="code-output">${typeof data === 'string' ? data : JSON.stringify(data, null, 2)}</pre>`;
    }

    // ============================================
    // TOPOLOGY
    // ============================================
    async loadTopology() {
        this.showLoading('topology', 'Mapping network topology...');
        
        try {
            const response = await fetch(`${this.apiBase}/topology`);
            const data = await response.json();
            
            this.hideLoading('topology');
            this.displayTopology(data);
        } catch (error) {
            this.hideLoading('topology');
            this.showError('Failed to load topology: ' + error.message);
        }
    }

    displayTopology(data) {
        const container = document.getElementById('topology-graph');
        const stats = document.getElementById('topology-stats');
        
        // Update stats
        if (stats) {
            stats.innerHTML = `
                <div class="stat-item"><span class="stat-value">${data.node_count || 0}</span> Nodes</div>
                <div class="stat-item"><span class="stat-value">${data.link_count || 0}</span> Links</div>
                <div class="stat-item"><span class="stat-value">${data.subnet_count || 0}</span> Subnets</div>
            `;
        }

        // Simple topology visualization using HTML/CSS
        const nodes = data.nodes || [];
        const links = data.links || [];
        
        if (nodes.length === 0) {
            container.innerHTML = '<div class="no-results">No topology data available. Run a network discovery first.</div>';
            return;
        }

        // Create a visual representation
        container.innerHTML = `
            <div class="topology-view">
                <svg id="topology-svg" viewBox="0 0 800 400">
                    ${links.map((link, i) => {
                        const source = nodes.find(n => n.id === link.source) || {x: 100, y: 200};
                        const target = nodes.find(n => n.id === link.target) || {x: 700, y: 200};
                        return `<line x1="${source.x || 100}" y1="${source.y || 200}" 
                                    x2="${target.x || 700}" y2="${target.y || 200}" 
                                    class="topology-link" />`;
                    }).join('')}
                    ${nodes.map((node, i) => `
                        <g transform="translate(${node.x || (100 + i * 100)}, ${node.y || 200})" class="topology-node">
                            <circle r="20" class="node-circle ${node.type || 'host'}" />
                            <text dy="35" text-anchor="middle" class="node-label">${node.label || node.id}</text>
                            <title>${node.ip || node.id}</title>
                        </g>
                    `).join('')}
                </svg>
                <div class="topology-legend">
                    <div class="legend-item"><span class="legend-icon router"></span> Router</div>
                    <div class="legend-item"><span class="legend-icon switch"></span> Switch</div>
                    <div class="legend-item"><span class="legend-icon host"></span> Host</div>
                </div>
            </div>
        `;
    }

    // ============================================
    // QUICK ACTIONS
    // ============================================
    async quickPing(target = null) {
        target = target || prompt('Enter host to ping:');
        if (!target) return;

        this.addNotification(`Pinging ${target}...`, 'info');
        
        try {
            const response = await fetch(`${this.apiBase}/ping`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({target, count: 4})
            });
            
            const data = await response.json();
            this.showModal('Ping Results', `<pre>${data.output || JSON.stringify(data, null, 2)}</pre>`);
        } catch (error) {
            this.showError('Ping failed: ' + error.message);
        }
    }

    async quickTraceroute(target = null) {
        target = target || prompt('Enter host for traceroute:');
        if (!target) return;

        this.addNotification(`Running traceroute to ${target}...`, 'info');
        this.showLoading('modal', 'Traceroute in progress...');
        
        try {
            const response = await fetch(`${this.apiBase}/traceroute`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({target})
            });
            
            const data = await response.json();
            this.hideLoading('modal');
            this.showModal('Traceroute Results', `<pre>${data.output || JSON.stringify(data, null, 2)}</pre>`);
        } catch (error) {
            this.hideLoading('modal');
            this.showError('Traceroute failed: ' + error.message);
        }
    }

    async portScanHost(ip) {
        this.switchTab('ports');
        document.getElementById('scan-target').value = ip;
        document.getElementById('scan-preset').value = 'common';
        this.updatePortRange('common');
        this.addNotification(`Port scan configured for ${ip}. Click Scan to start.`, 'info');
    }

    // ============================================
    // JOB POLLING & ASYNC OPERATIONS
    // ============================================
    pollJobStatus(jobId, callback) {
        const poll = async () => {
            try {
                const response = await fetch(`${this.apiBase}/job-status/${jobId}`);
                const data = await response.json();
                
                if (data.status === 'completed') {
                    callback(data.result);
                } else if (data.status === 'error') {
                    this.showError('Job failed: ' + data.error);
                } else {
                    // Still processing, poll again
                    setTimeout(poll, 2000);
                }
            } catch (error) {
                this.showError('Failed to check job status: ' + error.message);
            }
        };
        
        poll();
    }

    startPolling() {
        // Poll for connection status updates
        this.pollingInterval = setInterval(() => {
            this.updateConnectionStatus();
        }, 30000);
    }

    async updateConnectionStatus() {
        try {
            const response = await fetch(`${this.apiBase}/status`);
            const data = await response.json();
            
            const statusEl = document.getElementById('connection-status');
            const lastUpdateEl = document.getElementById('last-update');
            
            if (statusEl) {
                statusEl.textContent = data.status === 'ok' ? 'Connected' : 'Disconnected';
                statusEl.className = `status ${data.status === 'ok' ? 'connected' : 'disconnected'}`;
            }
            
            if (lastUpdateEl) {
                lastUpdateEl.textContent = `Last update: ${new Date().toLocaleTimeString()}`;
            }
        } catch (error) {
            const statusEl = document.getElementById('connection-status');
            if (statusEl) {
                statusEl.textContent = 'Disconnected';
                statusEl.className = 'status disconnected';
            }
        }
    }

    // ============================================
    // UI HELPERS
    // ============================================
    showLoading(context, message = 'Loading...') {
        // Create or update loading indicator for context
        const container = document.querySelector(`#${context} .results`) || document.body;
        let loader = container.querySelector('.loading-indicator');
        
        if (!loader) {
            loader = document.createElement('div');
            loader.className = 'loading-indicator';
            container.insertBefore(loader, container.firstChild);
        }
        
        loader.innerHTML = `
            <div class="spinner"></div>
            <p>${message}</p>
            <button class="btn secondary" onclick="dashboard.cancelOperation()">Cancel</button>
        `;
        loader.style.display = 'flex';
    }

    hideLoading(context) {
        const container = document.querySelector(`#${context} .results`) || document.body;
        const loader = container.querySelector('.loading-indicator');
        if (loader) {
            loader.style.display = 'none';
        }
    }

    showError(message) {
        this.addNotification(message, 'error');
        console.error(message);
    }

    addNotification(message, type = 'info') {
        const container = document.getElementById('notifications') || this.createNotificationsContainer();
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <span class="icon">${type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️'}</span>
            <span class="message">${message}</span>
            <button class="close" onclick="this.parentElement.remove()">×</button>
        `;
        
        container.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    createNotificationsContainer() {
        const container = document.createElement('div');
        container.id = 'notifications';
        container.className = 'notifications-container';
        document.body.appendChild(container);
        return container;
    }

    showModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="close" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">${content}</div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    showWelcomeGuide() {
        if (localStorage.getItem('netdash-welcome-shown')) return;
        
        this.showModal('Welcome to Network Dashboard', `
            <div class="welcome-guide">
                <p>This dashboard helps you explore and analyze your network.</p>
                <ul>
                    <li><strong>Discovery:</strong> Find hosts on your network using various scan methods</li>
                    <li><strong>Interfaces:</strong> View your network interfaces and their configuration</li>
                    <li><strong>Connections:</strong> Monitor active network connections</li>
                    <li><strong>Port Scanner:</strong> Scan for open ports on any host</li>
                    <li><strong>DNS Tools:</strong> Perform DNS lookups, WHOIS, and more</li>
                    <li><strong>Topology:</strong> Visualize your network structure</li>
                </ul>
                <label><input type="checkbox" id="dont-show-welcome"> Don't show this again</label>
            </div>
        `);
        
        document.getElementById('dont-show-welcome')?.addEventListener('change', (e) => {
            if (e.target.checked) {
                localStorage.setItem('netdash-welcome-shown', 'true');
            }
        });
    }

    toggleHelp() {
        document.getElementById('help-panel')?.classList.toggle('visible');
    }

    showTooltip(event) {
        const tooltip = event.target.dataset.tooltip;
        if (tooltip) {
            this.addNotification(tooltip, 'info');
        }
    }

    handleKeyboard(e) {
        // Ctrl+Number for tabs
        if (e.ctrlKey && e.key >= '1' && e.key <= '6') {
            const tabs = ['discovery', 'interfaces', 'connections', 'ports', 'dns', 'topology'];
            const index = parseInt(e.key) - 1;
            if (tabs[index]) {
                this.switchTab(tabs[index]);
            }
        }
        // Escape to close modals
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay').forEach(m => m.remove());
        }
    }

    async checkBackendStatus() {
        try {
            const response = await fetch(`${this.apiBase}/status`);
            if (!response.ok) throw new Error('Backend unavailable');
            this.addNotification('Connected to backend', 'success');
        } catch (error) {
            this.addNotification('Warning: Backend connection failed. Some features may not work.', 'error');
        }
    }

    async loadNetworkInfo() {
        try {
            const response = await fetch(`${this.apiBase}/network-info`);
            const data = await response.json();
            
            // Update header with network info
            const infoEl = document.getElementById('network-info');
            if (infoEl) {
                infoEl.innerHTML = `
                    <span>Host: ${data.hostname || 'Unknown'}</span>
                    <span>Local IP: ${data.local_ip || 'N/A'}</span>
                `;
            }
        } catch (error) {
            console.error('Failed to load network info:', error);
        }
    }

    clearResults() {
        if (confirm('Clear all results?')) {
            document.querySelectorAll('.results tbody').forEach(tb => tb.innerHTML = '');
            document.querySelectorAll('.results .no-results').forEach(el => el.remove());
            this.addNotification('Results cleared', 'info');
        }
    }

    exportHostsCSV() {
        if (!this.currentHosts || this.currentHosts.length === 0) {
            this.showError('No hosts to export');
            return;
        }
        
        const csv = [
            ['IP Address', 'MAC Address', 'Hostname', 'Status', 'Response Time'],
            ...this.currentHosts.map(h => [h.ip, h.mac || '', h.hostname || '', h.status, h.response_time || ''])
        ].map(row => row.join(',')).join('\n');
        
        const blob = new Blob([csv], {type: 'text/csv'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `hosts-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        
        this.addNotification('Hosts exported to CSV', 'success');
    }

    exportTopology() {
        this.addNotification('Topology export feature coming soon', 'info');
    }

    cancelOperation() {
        this.addNotification('Operation cancelled', 'info');
        // Hide all loading indicators
        document.querySelectorAll('.loading-indicator').forEach(el => el.style.display = 'none');
    }

    // ============================================
    // UTILITIES
    // ============================================
    validateSubnet(subnet) {
        const cidrPattern = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
        if (!cidrPattern.test(subnet)) return false;
        
        const [ip, mask] = subnet.split('/');
        if (parseInt(mask) > 32) return false;
        
        return ip.split('.').every(octet => {
            const num = parseInt(octet);
            return num >= 0 && num <= 255;
        });
    }

    validateIP(ip) {
        const pattern = /^(\d{1,3}\.){3}\d{1,3}$/;
        if (!pattern.test(ip)) return false;
        return ip.split('.').every(octet => {
            const num = parseInt(octet);
            return num >= 0 && num <= 255;
        });
    }

    formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
}

// ============================================
// INITIALIZE
// ============================================
const dashboard = new NetworkDashboard();
