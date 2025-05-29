from flask import Flask, request, Response, render_template_string
import requests
import random
import time
import threading
import logging
import json
from datetime import datetime, timedelta
from collections import defaultdict, deque

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("balancer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("balanceador")

app = Flask(__name__)

# Lista de servidores backend
SERVERS = [
    "http://localhost:5001",
    "http://localhost:5002"
]

# Configuración
RETRY_INTERVAL = 30
HEALTH_CHECK_INTERVAL = 5
MAX_REQUEST_HISTORY = 1000

class LoadBalancerState:
    def __init__(self):
        self.failed_servers = {}
        self.server_stats = defaultdict(lambda: {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'last_response_time': 0,
            'uptime_start': datetime.now()
        })
        self.request_history = deque(maxlen=MAX_REQUEST_HISTORY)
        self.total_requests = 0
        self.start_time = datetime.now()
        
    def add_request(self, server, success, response_time, path):
        self.total_requests += 1
        self.server_stats[server]['total_requests'] += 1
        self.server_stats[server]['last_response_time'] = response_time
        
        if success:
            self.server_stats[server]['successful_requests'] += 1
        else:
            self.server_stats[server]['failed_requests'] += 1
            
        stats = self.server_stats[server]
        total = stats['successful_requests']
        if total > 0:
            current_avg = stats['avg_response_time']
            stats['avg_response_time'] = ((current_avg * (total - 1)) + response_time) / total
            
        self.request_history.append({
            'timestamp': datetime.now(),
            'server': server,
            'success': success,
            'response_time': response_time,
            'path': path
        })

state = LoadBalancerState()

def check_server_health(server):
    """Verificar si un servidor está activo"""
    try:
        start_time = time.time()
        response = requests.get(f"{server}/health", timeout=3)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            state.add_request(server, True, response_time, '/health')
            return True
        else:
            state.add_request(server, False, response_time, '/health')
            return False
    except Exception as e:
        logger.warning(f"Error en health check para {server}: {str(e)}")
        state.add_request(server, False, 0, '/health')
        return False

def get_active_servers():
    """Retorna lista de servidores activos basado en el estado actual"""
    current_time = time.time()
    active_servers = []

    for server in SERVERS:
        if server not in state.failed_servers or current_time - state.failed_servers[server] > RETRY_INTERVAL:
            active_servers.append(server)

    if active_servers:
        active_servers.sort(key=lambda s: state.server_stats[s]['total_requests'])
        return active_servers

    logger.error("¡ALERTA! No hay servidores activos disponibles. Intentando con todos.")
    return SERVERS

def health_check_loop():
    """Función que verifica periódicamente el estado de los servidores"""
    while True:
        for server in SERVERS:
            is_healthy = check_server_health(server)

            if is_healthy and server in state.failed_servers:
                del state.failed_servers[server]
                state.server_stats[server]['uptime_start'] = datetime.now()
                logger.info(f"⚡ Health check: Servidor {server} recuperado y vuelve a estar activo")
            elif not is_healthy and server not in state.failed_servers:
                state.failed_servers[server] = time.time()
                logger.warning(f"❌ Health check: Servidor {server} detectado como caído")

        time.sleep(HEALTH_CHECK_INTERVAL)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(path):
    if path == 'lb-status':
        return dashboard()
    elif path == 'lb-api/stats':
        return api_stats()
    elif path == 'lb-health':
        return health_status()
    
    active_servers = get_active_servers()
    last_error = None

    for server in active_servers:
        url = f"{server}/{path}"
        method = request.method
        headers = {k: v for k, v in request.headers if k != 'Host'}
        data = request.get_data()

        try:
            start_time = time.time()
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                cookies=request.cookies,
                params=request.args,
                allow_redirects=False,
                stream=True,
                timeout=5
            )
            
            response_time = time.time() - start_time
            state.add_request(server, True, response_time, f"/{path}")
            
            logger.info(f"✅ Solicitud exitosa a: {url} ({response_time:.3f}s)")

            if server in state.failed_servers:
                del state.failed_servers[server]
                state.server_stats[server]['uptime_start'] = datetime.now()
                logger.info(f"⚡ Servidor {server} recuperado")

            response = Response(
                resp.content,
                resp.status_code,
                [
                    (k, v) for k, v in resp.headers.items()
                    if k.lower() not in ('transfer-encoding', 'content-encoding', 'content-length')
                ]
            )

            response.headers['X-Upstream-Server'] = server
            response.headers['X-Response-Time'] = f"{response_time:.3f}s"
            response.headers['X-Load-Balancer'] = "TaskFlow-LB/2.0"

            return response

        except Exception as e:
            response_time = time.time() - start_time
            state.add_request(server, False, response_time, f"/{path}")
            last_error = e
            logger.error(f"❌ Error al conectar con {server}: {str(e)}")
            state.failed_servers[server] = time.time()

    error_response = "🚫 Servicio temporalmente no disponible. Todos los servidores están caídos."
    logger.critical(f"TODOS LOS SERVIDORES FALLARON. Último error: {str(last_error)}")
    return error_response, 503

@app.route('/lb-api/stats')
def api_stats():
    """API endpoint para obtener estadísticas en JSON"""
    uptime = datetime.now() - state.start_time
    
    server_status = {}
    for server in SERVERS:
        stats = state.server_stats[server]
        is_active = server not in state.failed_servers
        
        server_uptime = datetime.now() - stats['uptime_start'] if is_active else timedelta(0)
        
        server_status[server] = {
            "status": "UP" if is_active else "DOWN",
            "total_requests": stats['total_requests'],
            "successful_requests": stats['successful_requests'],
            "failed_requests": stats['failed_requests'],
            "success_rate": (stats['successful_requests'] / max(stats['total_requests'], 1)) * 100,
            "avg_response_time": round(stats['avg_response_time'] * 1000, 2),
            "last_response_time": round(stats['last_response_time'] * 1000, 2),
            "uptime_seconds": int(server_uptime.total_seconds())
        }
        
        if not is_active:
            downtime = time.time() - state.failed_servers[server]
            server_status[server]["downtime_seconds"] = int(downtime)
            server_status[server]["retry_in"] = max(0, int(RETRY_INTERVAL - downtime))

    return {
        "balancer_uptime": str(uptime),
        "total_requests": state.total_requests,
        "active_servers": len([s for s in SERVERS if s not in state.failed_servers]),
        "total_servers": len(SERVERS),
        "servers": server_status,
        "recent_requests": [
            {
                "timestamp": req["timestamp"].strftime("%H:%M:%S"),
                "server": req["server"].split(":")[-1],
                "success": req["success"],
                "response_time": round(req["response_time"] * 1000, 1),
                "path": req["path"]
            }
            for req in list(state.request_history)[-10:]
        ]
    }

@app.route('/lb-health')
def health_status():
    """Endpoint de salud para el load balancer"""
    active_count = len([s for s in SERVERS if s not in state.failed_servers])
    
    if active_count > 0:
        return {"status": "healthy", "active_servers": active_count, "total_servers": len(SERVERS)}, 200
    else:
        return {"status": "unhealthy", "active_servers": 0, "total_servers": len(SERVERS)}, 503

@app.route('/lb-status')
def dashboard():
    """Dashboard web unificado del balanceador"""
    
    dashboard_html = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskFlow Load Balancer - Dashboard</title>
    <style>
        :root {
            --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --secondary-gradient: linear-gradient(135deg, #ff6b6b, #ee5a6f);
            --success-gradient: linear-gradient(135deg, #4CAF50, #45a049);
            --warning-gradient: linear-gradient(135deg, #ff9800, #f57c00);
            --danger-gradient: linear-gradient(135deg, #f44336, #d32f2f);
            --white: #ffffff;
            --gray-50: #f9fafb;
            --gray-100: #f3f4f6;
            --gray-600: #4b5563;
            --gray-800: #1f2937;
            --space-sm: 0.5rem;
            --space-md: 1rem;
            --space-lg: 1.5rem;
            --space-xl: 2rem;
            --space-2xl: 3rem;
            --radius-lg: 16px;
            --radius-xl: 24px;
            --radius-full: 9999px;
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            --shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            --transition-normal: 0.3s ease;
            --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --font-size-base: 1rem;
            --font-size-lg: 1.125rem;
            --font-size-xl: 1.25rem;
            --font-size-2xl: 1.5rem;
            --font-size-4xl: 2.25rem;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: var(--font-family);
            background: var(--primary-gradient);
            min-height: 100vh;
            color: var(--gray-800);
            line-height: 1.6;
            padding: var(--space-lg);
        }

        .nav-system {
            position: fixed;
            top: var(--space-lg);
            right: var(--space-lg);
            z-index: 1000;
            display: flex;
            gap: var(--space-md);
        }

        .nav-item {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            padding: var(--space-md) var(--space-lg);
            border-radius: var(--radius-full);
            text-decoration: none;
            color: var(--gray-600);
            font-weight: 500;
            transition: var(--transition-normal);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .nav-item:hover {
            background: var(--white);
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }

        .nav-item.active {
            background: var(--primary-gradient);
            color: var(--white);
        }

        .dashboard {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: var(--radius-xl);
            box-shadow: var(--shadow-2xl);
            overflow: hidden;
            animation: slideIn 0.6s ease-out;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .header {
            background: var(--primary-gradient);
            padding: var(--space-2xl);
            text-align: center;
            color: var(--white);
            position: relative;
            overflow: hidden;
        }

        .header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            animation: rotate 20s linear infinite;
        }

        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        .header h1 {
            font-size: var(--font-size-4xl);
            font-weight: 700;
            letter-spacing: -0.02em;
            position: relative;
            z-index: 1;
            text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }

        .subtitle {
            font-size: var(--font-size-lg);
            margin-top: var(--space-sm);
            opacity: 0.9;
            position: relative;
            z-index: 1;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: var(--space-lg);
            padding: var(--space-2xl);
        }

        .stat-card {
            background: var(--white);
            padding: var(--space-xl);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-lg);
            border: 1px solid rgba(0,0,0,0.05);
            transition: var(--transition-normal);
        }

        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow-xl);
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--gray-800);
            margin-bottom: var(--space-sm);
        }

        .stat-label {
            font-size: var(--font-size-base);
            color: var(--gray-600);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .section {
            padding: 0 var(--space-2xl) var(--space-2xl);
        }

        .section-title {
            font-size: var(--font-size-2xl);
            font-weight: 600;
            margin-bottom: var(--space-lg);
            color: var(--gray-800);
        }

        .server-card {
            background: var(--white);
            border-radius: var(--radius-lg);
            padding: var(--space-xl);
            margin-bottom: var(--space-lg);
            box-shadow: var(--shadow-lg);
            border-left: 4px solid transparent;
            transition: var(--transition-normal);
        }

        .server-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-xl);
        }

        .server-up {
            border-left-color: #4CAF50;
        }

        .server-down {
            border-left-color: #f44336;
        }

        .server-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--space-lg);
        }

        .server-name {
            font-size: var(--font-size-xl);
            font-weight: 600;
            color: var(--gray-800);
        }

        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-sm) var(--space-lg);
            border-radius: var(--radius-full);
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .status-up {
            background: rgba(76, 175, 80, 0.1);
            color: #2e7d32;
            border: 1px solid rgba(76, 175, 80, 0.2);
        }

        .status-down {
            background: rgba(244, 67, 54, 0.1);
            color: #c62828;
            border: 1px solid rgba(244, 67, 54, 0.2);
        }

        .pulse {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        .pulse-green {
            background: #4CAF50;
        }

        .pulse-red {
            background: #f44336;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.1); }
        }

        .server-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: var(--space-lg);
            margin-top: var(--space-lg);
        }

        .metric {
            text-align: center;
        }

        .metric-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--gray-800);
        }

        .metric-label {
            font-size: 0.8rem;
            color: var(--gray-600);
            margin-top: 4px;
        }

        .request-log {
            background: var(--gray-50);
            border-radius: var(--radius-lg);
            padding: var(--space-lg);
            max-height: 300px;
            overflow-y: auto;
        }

        .request-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: var(--space-sm) 0;
            border-bottom: 1px solid #eee;
            font-size: 0.9rem;
        }

        .request-item:last-child {
            border-bottom: none;
        }

        .request-success {
            color: #4CAF50;
        }

        .request-failed {
            color: #f44336;
        }

        .auto-refresh {
            position: fixed;
            bottom: var(--space-lg);
            right: var(--space-lg);
            background: rgba(102, 126, 234, 0.9);
            color: var(--white);
            padding: var(--space-md) var(--space-lg);
            border-radius: var(--radius-full);
            font-size: 0.9rem;
            backdrop-filter: blur(10px);
        }

        @media (max-width: 768px) {
            .stats-grid { grid-template-columns: 1fr; }
            .nav-system { position: static; justify-content: center; margin-bottom: var(--space-lg); }
        }
    </style>
</head>
<body>
    <nav class="nav-system">
        <a href="/" class="nav-item">📝 Tareas</a>
        <a href="/lb-status" class="nav-item active">⚖️ Balanceador</a>
        <a href="/lb-health" class="nav-item">💚 Estado</a>
    </nav>

    <div class="dashboard">
        <div class="header">
            <h1>⚖️ TaskFlow Load Balancer</h1>
            <p class="subtitle">Dashboard de Monitoreo en Tiempo Real</p>
        </div>

        <div class="stats-grid" id="statsGrid">
            <!-- Las estadísticas se cargarán aquí -->
        </div>

        <div class="section">
            <h2 class="section-title">Estado de Servidores</h2>
            <div id="serversContainer">
                <!-- Los servidores se cargarán aquí -->
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">Requests Recientes</h2>
            <div class="request-log" id="requestLog">
                <!-- Los requests se cargarán aquí -->
            </div>
        </div>
    </div>

    <div class="auto-refresh">
        🔄 Actualización automática cada 2s
    </div>

    <script>
        async function loadStats() {
            try {
                const response = await fetch('/lb-api/stats');
                const data = await response.json();
                
                updateStatsGrid(data);
                updateServers(data);
                updateRequestLog(data);
                
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        function updateStatsGrid(data) {
            const grid = document.getElementById('statsGrid');
            grid.innerHTML = `
                <div class="stat-card">
                    <div class="stat-value">${data.total_requests}</div>
                    <div class="stat-label">Total Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.active_servers}/${data.total_servers}</div>
                    <div class="stat-label">Servidores Activos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.balancer_uptime.split('.')[0]}</div>
                    <div class="stat-label">Uptime</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${Object.values(data.servers).reduce((sum, s) => sum + s.successful_requests, 0)}</div>
                    <div class="stat-label">Requests Exitosos</div>
                </div>
            `;
        }

        function updateServers(data) {
            const container = document.getElementById('serversContainer');
            container.innerHTML = '';
            
            Object.entries(data.servers).forEach(([server, stats]) => {
                const isUp = stats.status === 'UP';
                const serverCard = document.createElement('div');
                serverCard.className = `server-card ${isUp ? 'server-up' : 'server-down'}`;
                
                serverCard.innerHTML = `
                    <div class="server-header">
                        <div class="server-name">${server}</div>
                        <div class="status-indicator ${isUp ? 'status-up' : 'status-down'}">
                            <div class="pulse ${isUp ? 'pulse-green' : 'pulse-red'}"></div>
                            ${isUp ? 'ACTIVO' : 'CAÍDO'}
                        </div>
                    </div>
                    <div class="server-metrics">
                        <div class="metric">
                            <div class="metric-value">${stats.total_requests}</div>
                            <div class="metric-label">Requests</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${stats.success_rate.toFixed(1)}%</div>
                            <div class="metric-label">Éxito</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${stats.avg_response_time}ms</div>
                            <div class="metric-label">Tiempo Resp</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${isUp ? Math.floor(stats.uptime_seconds / 60) : Math.floor((stats.downtime_seconds || 0) / 60)}m</div>
                            <div class="metric-label">${isUp ? 'Uptime' : 'Downtime'}</div>
                        </div>
                    </div>
                `;
                
                container.appendChild(serverCard);
            });
        }

        function updateRequestLog(data) {
            const log = document.getElementById('requestLog');
            log.innerHTML = '';
            
            data.recent_requests.reverse().forEach(req => {
                const item = document.createElement('div');
                item.className = 'request-item';
                item.innerHTML = `
                    <span>${req.timestamp}</span>
                    <span>Puerto ${req.server}</span>
                    <span>${req.path}</span>
                    <span class="${req.success ? 'request-success' : 'request-failed'}">
                        ${req.success ? '✅' : '❌'} ${req.response_time}ms
                    </span>
                `;
                log.appendChild(item);
            });
        }

        loadStats();
        setInterval(loadStats, 2000);
    </script>
</body>
</html>
    '''
    
    return dashboard_html

def check_servers_on_startup():
    """Verificar que los servidores estén activos al inicio"""
    logger.info("🚀 Verificando servidores al inicio...")
    for server in SERVERS:
        if check_server_health(server):
            logger.info(f"✅ Servidor {server} activo")
        else:
            state.failed_servers[server] = time.time()
            logger.warning(f"❌ Servidor {server} no responde al inicio")

if __name__ == '__main__':
    print("🎯 Iniciando TaskFlow Load Balancer v2.0...")
    
    check_servers_on_startup()

    health_thread = threading.Thread(target=health_check_loop, daemon=True)
    health_thread.start()

    logger.info("⚖️ Balanceador de carga iniciado en http://localhost:8080")
    logger.info("📊 Dashboard disponible en http://localhost:8080/lb-status")
    logger.info("🔗 API de estadísticas en http://localhost:8080/lb-api/stats")
    logger.info("💚 Health check en http://localhost:8080/lb-health")
    
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)