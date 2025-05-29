'''
TaskFlow - Sistema de gestión de tareas con interfaz unificada
'''

import json
import os
import sys
import requests
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string, redirect, url_for

# Definimos la ruta del archivo 'tasks.json' dentro de la carpeta del proyecto
TASKS_FILE = os.path.join(os.path.dirname(__file__), 'tasks.json')

app = Flask(__name__)
start_time = datetime.now()

# Función para registrar eventos en el servicio de logs
def log_event(message):
    try:
        requests.post("http://localhost:5003/log", json={"message": message}, timeout=1)
    except:
        pass

def load_tasks():
    """
    Carga las tareas desde el archivo JSON. Si el archivo no existe o tiene un formato incorrecto, retorna una lista vacía.
    Filtra las tareas que no contienen el campo 'title' y asegura que todas tengan 'completed'.
    """
    if not os.path.exists(TASKS_FILE):
        return []

    with open(TASKS_FILE, "r") as file:
        try:
            tasks = json.load(file)
            valid_tasks = []
            for task in tasks:
                if isinstance(task, dict) and 'title' in task:
                    if 'completed' not in task:
                        task['completed'] = False
                    valid_tasks.append(task)
            return valid_tasks
        except json.JSONDecodeError:
            return []


def save_tasks(tasks):
    """
    Guarda las tareas en el archivo JSON.
    """
    with open(TASKS_FILE, "w") as file:
        json.dump(tasks, file, indent=4)


# Template HTML unificado
def get_unified_template():
    return '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskFlow - Gestión de Tareas</title>
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
            --gray-200: #e5e7eb;
            --gray-300: #d1d5db;
            --gray-400: #9ca3af;
            --gray-500: #6b7280;
            --gray-600: #4b5563;
            --gray-700: #374151;
            --gray-800: #1f2937;
            --gray-900: #111827;
            --space-xs: 0.25rem;
            --space-sm: 0.5rem;
            --space-md: 1rem;
            --space-lg: 1.5rem;
            --space-xl: 2rem;
            --space-2xl: 3rem;
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --radius-xl: 24px;
            --radius-full: 9999px;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            --shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            --transition-fast: 0.15s ease;
            --transition-normal: 0.3s ease;
            --transition-slow: 0.5s ease;
            --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --font-size-xs: 0.75rem;
            --font-size-sm: 0.875rem;
            --font-size-base: 1rem;
            --font-size-lg: 1.125rem;
            --font-size-xl: 1.25rem;
            --font-size-2xl: 1.5rem;
            --font-size-3xl: 1.875rem;
            --font-size-4xl: 2.25rem;
            --font-size-5xl: 3rem;
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
            padding: var(--space-lg);
            color: var(--gray-800);
            line-height: 1.6;
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
            color: var(--gray-700);
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

        .container {
            max-width: 600px;
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
            color: var(--white);
            font-size: var(--font-size-4xl);
            font-weight: 700;
            letter-spacing: -0.02em;
            position: relative;
            z-index: 1;
            text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }

        .subtitle {
            color: rgba(255,255,255,0.9);
            font-size: var(--font-size-lg);
            margin-top: var(--space-sm);
            position: relative;
            z-index: 1;
        }

        .form-container {
            padding: var(--space-2xl);
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }

        .task-form {
            display: flex;
            gap: var(--space-md);
            align-items: stretch;
        }

        .task-input {
            flex: 1;
            padding: var(--space-lg) var(--space-xl);
            border: 2px solid rgba(0,0,0,0.06);
            border-radius: var(--radius-lg);
            font-size: var(--font-size-base);
            font-family: inherit;
            background: rgba(255,255,255,0.8);
            transition: var(--transition-normal);
            outline: none;
        }

        .task-input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
            background: var(--white);
            transform: translateY(-1px);
        }

        .add-btn {
            padding: var(--space-lg) var(--space-xl);
            background: var(--primary-gradient);
            color: var(--white);
            border: none;
            border-radius: var(--radius-lg);
            font-size: var(--font-size-base);
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition-normal);
            box-shadow: var(--shadow-lg);
        }

        .add-btn:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-xl);
        }

        .add-btn:active {
            transform: translateY(0);
        }

        .tasks-container {
            padding: 0 var(--space-2xl) var(--space-2xl);
        }

        .tasks-list {
            list-style: none;
        }

        .task-item {
            display: flex;
            align-items: center;
            padding: var(--space-xl);
            margin-bottom: var(--space-md);
            background: var(--white);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-md);
            transition: var(--transition-normal);
            border: 1px solid rgba(0,0,0,0.03);
            animation: taskSlideIn 0.4s ease-out;
        }

        @keyframes taskSlideIn {
            from {
                opacity: 0;
                transform: translateX(-20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        .task-item:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }

        .task-checkbox {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            border: 2px solid var(--gray-300);
            background: var(--white);
            cursor: pointer;
            position: relative;
            transition: var(--transition-normal);
            flex-shrink: 0;
        }

        .task-checkbox.completed {
            background: var(--success-gradient);
            border-color: #4CAF50;
        }

        .task-checkbox.completed::after {
            content: '✓';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: var(--white);
            font-size: 14px;
            font-weight: bold;
        }

        .task-title {
            flex: 1;
            margin-left: var(--space-lg);
            font-size: var(--font-size-base);
            color: var(--gray-800);
            transition: var(--transition-normal);
            line-height: 1.4;
        }

        .task-title.completed {
            text-decoration: line-through;
            color: var(--gray-500);
            opacity: 0.7;
        }

        .task-actions {
            display: flex;
            gap: var(--space-sm);
            opacity: 0;
            transition: var(--transition-normal);
        }

        .task-item:hover .task-actions {
            opacity: 1;
        }

        .action-btn {
            padding: var(--space-sm) var(--space-md);
            border: none;
            border-radius: var(--radius-md);
            font-size: var(--font-size-sm);
            font-weight: 500;
            cursor: pointer;
            transition: var(--transition-normal);
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .complete-btn {
            background: var(--success-gradient);
            color: var(--white);
        }

        .complete-btn:hover {
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }

        .delete-btn {
            background: var(--danger-gradient);
            color: var(--white);
        }

        .delete-btn:hover {
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }

        .empty-state {
            text-align: center;
            padding: var(--space-2xl) var(--space-lg);
            color: var(--gray-600);
        }

        .empty-icon {
            font-size: 3rem;
            margin-bottom: var(--space-lg);
            opacity: 0.5;
        }

        .empty-text {
            font-size: var(--font-size-lg);
            font-weight: 500;
            margin-bottom: var(--space-sm);
        }

        .empty-subtext {
            font-size: var(--font-size-sm);
            opacity: 0.7;
        }

        .server-info {
            margin: var(--space-lg) var(--space-2xl) var(--space-2xl);
            padding: var(--space-lg);
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
            border-radius: var(--radius-lg);
            border: 1px solid rgba(102, 126, 234, 0.1);
            text-align: center;
        }

        .server-badge {
            display: inline-flex;
            align-items: center;
            gap: var(--space-sm);
            background: rgba(102, 126, 234, 0.1);
            padding: var(--space-sm) var(--space-lg);
            border-radius: var(--radius-full);
            font-size: var(--font-size-sm);
            font-weight: 500;
            color: #667eea;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background: #4CAF50;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        @media (max-width: 640px) {
            .container {
                margin: var(--space-md);
                border-radius: var(--radius-lg);
            }
            
            .header h1 {
                font-size: var(--font-size-3xl);
            }
            
            .form-container, .tasks-container, .server-info {
                padding-left: var(--space-lg);
                padding-right: var(--space-lg);
            }

            .nav-system {
                position: static;
                justify-content: center;
                margin-bottom: var(--space-lg);
            }
        }
    </style>
</head>
<body>
    <nav class="nav-system">
        <a href="/" class="nav-item active">📝 Tareas</a>
        <a href="/lb-status" class="nav-item">⚖️ Balanceador</a>
        <a href="/system-info" class="nav-item">📊 Sistema</a>
        <a href="/health" class="nav-item">💚 Estado</a>
    </nav>

    <div class="container">
        <div class="header">
            <h1>✨ TaskFlow</h1>
            <p class="subtitle">Organiza tu día con estilo</p>
        </div>

        <div class="form-container">
            <form action="/tasks/add" method="post" class="task-form">
                <input type="text" name="title" class="task-input" placeholder="¿Qué necesitas hacer hoy?" required>
                <button type="submit" class="add-btn">+ Agregar</button>
            </form>
        </div>

        <div class="tasks-container">
            <ul class="tasks-list">
                {% if tasks %}
                    {% for task in tasks %}
                    <li class="task-item">
                        <div class="task-checkbox {% if task.completed %}completed{% endif %}"></div>
                        <span class="task-title {% if task.completed %}completed{% endif %}">
                            {{ task.title }}
                        </span>
                        <div class="task-actions">
                            {% if not task.completed %}
                            <form action="/tasks/{{ loop.index0 }}/complete" method="post" style="display: inline;">
                                <button type="submit" class="action-btn complete-btn">
                                    ✓ Completar
                                </button>
                            </form>
                            {% endif %}
                            <form action="/tasks/{{ loop.index0 }}/delete" method="post" style="display: inline;">
                                <button type="submit" class="action-btn delete-btn">
                                    🗑 Eliminar
                                </button>
                            </form>
                        </div>
                    </li>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        <div class="empty-icon">📝</div>
                        <div class="empty-text">¡Perfecto! No tienes tareas pendientes</div>
                        <div class="empty-subtext">Agrega una nueva tarea para comenzar</div>
                    </div>
                {% endif %}
            </ul>
        </div>

        <div class="server-info">
            <div class="server-badge">
                <div class="status-dot"></div>
                <strong>Servidor:</strong> Puerto {{ server_port }}
            </div>
        </div>
    </div>

    <script>
        function checkServerInfo() {
            fetch('/info')
                .then(response => response.json())
                .then(data => {
                    console.log('📡 Información del servidor:', data);
                })
                .catch(err => console.log('⚠️ Error de conexión:', err));
        }

        setInterval(checkServerInfo, 5000);

        const input = document.querySelector('.task-input');
        input.addEventListener('focus', () => {
            input.parentElement.style.transform = 'scale(1.02)';
        });
        
        input.addEventListener('blur', () => {
            input.parentElement.style.transform = 'scale(1)';
        });

        document.addEventListener('DOMContentLoaded', () => {
            const tasks = document.querySelectorAll('.task-item');
            tasks.forEach((task, index) => {
                task.style.animationDelay = `${index * 0.1}s`;
            });
        });

        // Confetti al completar tareas
        document.querySelectorAll('.complete-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                createConfetti();
            });
        });

        function createConfetti() {
            const colors = ['#667eea', '#764ba2', '#4CAF50', '#ff6b6b', '#ff9800'];
            for (let i = 0; i < 50; i++) {
                const confetti = document.createElement('div');
                confetti.style.position = 'fixed';
                confetti.style.width = '10px';
                confetti.style.height = '10px';
                confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
                confetti.style.left = Math.random() * window.innerWidth + 'px';
                confetti.style.top = '-10px';
                confetti.style.borderRadius = '50%';
                confetti.style.pointerEvents = 'none';
                confetti.style.zIndex = '9999';
                confetti.style.animation = `fall ${Math.random() * 2 + 1}s linear forwards`;
                document.body.appendChild(confetti);
                
                setTimeout(() => confetti.remove(), 3000);
            }
        }

        const style = document.createElement('style');
        style.textContent = `
            @keyframes fall {
                to {
                    transform: translateY(${window.innerHeight + 50}px) rotate(360deg);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    </script>
</body>
</html>
    '''


# Ruta principal - Muestra la interfaz de usuario
@app.route('/')
def index():
    tasks = load_tasks()
    server_port = request.host.split(':')[1] if ':' in request.host else '5000'
    return render_template_string(get_unified_template(), tasks=tasks, server_port=server_port)


# Información del servidor
@app.route('/info')
def server_info():
    return jsonify({
        'version': '2.0.0',
        'server_port': request.host.split(':')[1] if ':' in request.host else '5000',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'uptime': str(datetime.now() - start_time),
        'tasks_count': len(load_tasks())
    })

# Información del sistema
@app.route('/system-info')
def system_info():
    tasks = load_tasks()
    completed_tasks = len([t for t in tasks if t.get('completed', False)])
    pending_tasks = len(tasks) - completed_tasks
    
    system_template = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskFlow - Información del Sistema</title>
    <style>
        :root {
            --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --white: #ffffff;
            --gray-600: #4b5563;
            --gray-800: #1f2937;
            --space-md: 1rem;
            --space-lg: 1.5rem;
            --space-xl: 2rem;
            --space-2xl: 3rem;
            --radius-lg: 16px;
            --radius-xl: 24px;
            --radius-full: 9999px;
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            --transition-normal: 0.3s ease;
            --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --font-size-lg: 1.125rem;
            --font-size-2xl: 1.5rem;
            --font-size-4xl: 2.25rem;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: var(--font-family);
            background: var(--primary-gradient);
            min-height: 100vh;
            padding: var(--space-lg);
            color: var(--gray-800);
            line-height: 1.6;
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

        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: var(--radius-xl);
            box-shadow: var(--shadow-2xl);
            overflow: hidden;
            animation: slideIn 0.6s ease-out;
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .header {
            background: var(--primary-gradient);
            padding: var(--space-2xl);
            text-align: center;
            color: var(--white);
        }

        .header h1 {
            font-size: var(--font-size-4xl);
            font-weight: 700;
        }

        .section {
            padding: var(--space-2xl);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: var(--space-lg);
            margin-bottom: var(--space-2xl);
        }

        .stat-card {
            background: var(--white);
            padding: var(--space-xl);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-lg);
            text-align: center;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--gray-800);
        }

        .stat-label {
            font-size: var(--font-size-lg);
            color: var(--gray-600);
            margin-top: var(--space-md);
        }

        @media (max-width: 768px) {
            .nav-system { position: static; justify-content: center; margin-bottom: var(--space-lg); }
        }
    </style>
</head>
<body>
    <nav class="nav-system">
        <a href="/" class="nav-item">📝 Tareas</a>
        <a href="/lb-status" class="nav-item">⚖️ Balanceador</a>
        <a href="/system-info" class="nav-item active">📊 Sistema</a>
        <a href="/health" class="nav-item">💚 Estado</a>
    </nav>

    <div class="container">
        <div class="header">
            <h1>📊 Información del Sistema</h1>
        </div>

        <div class="section">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{{ total_tasks }}</div>
                    <div class="stat-label">Total de Tareas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ completed_tasks }}</div>
                    <div class="stat-label">Completadas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ pending_tasks }}</div>
                    <div class="stat-label">Pendientes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ server_port }}</div>
                    <div class="stat-label">Puerto del Servidor</div>
                </div>
            </div>

            <h3>Información del Servidor</h3>
            <ul style="list-style: none; margin-top: 1rem;">
                <li><strong>Versión:</strong> TaskFlow v2.0</li>
                <li><strong>Puerto:</strong> {{ server_port }}</li>
                <li><strong>Uptime:</strong> {{ uptime }}</li>
                <li><strong>Timestamp:</strong> {{ timestamp }}</li>
            </ul>
        </div>
    </div>
</body>
</html>
    '''
    
    return render_template_string(
        system_template,
        total_tasks=len(tasks),
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        server_port=request.host.split(':')[1] if ':' in request.host else '5000',
        uptime=str(datetime.now() - start_time),
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

# Endpoint para health check
@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint para verificar si el servidor está activo"""
    return jsonify({
        "status": "ok",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "tasks_count": len(load_tasks())
    }), 200

# API - Obtener todas las tareas
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks = load_tasks()
    return jsonify(tasks)

# API - Agregar una nueva tarea
@app.route('/api/tasks', methods=['POST'])
def add_task():
    tasks = load_tasks()
    data = request.json

    if 'title' in data:
        new_task = {'title': data['title'], 'completed': False}
        tasks.append(new_task)
        save_tasks(tasks)
        log_event(f"API: Nueva tarea añadida: {data['title']}")
        return jsonify(new_task), 201
    return jsonify({"error": "El título de la tarea es requerido"}), 400

# API - Marcar una tarea como completada
@app.route('/api/tasks/<int:task_id>/complete', methods=['PUT'])
def complete_task(task_id):
    tasks = load_tasks()

    if 0 <= task_id < len(tasks):
        tasks[task_id]['completed'] = True
        save_tasks(tasks)
        log_event(f"API: Tarea completada: {tasks[task_id]['title']}")
        return jsonify(tasks[task_id])
    return jsonify({"error": "Tarea no encontrada"}), 404

# API - Eliminar una tarea
@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    tasks = load_tasks()

    if 0 <= task_id < len(tasks):
        deleted_task = tasks.pop(task_id)
        save_tasks(tasks)
        log_event(f"API: Tarea eliminada: {deleted_task['title']}")
        return jsonify(deleted_task)
    return jsonify({"error": "Tarea no encontrada"}), 404

# Rutas web para interacción desde el navegador
@app.route('/tasks/add', methods=['POST'])
def web_add_task():
    tasks = load_tasks()
    title = request.form.get('title')

    if title:
        new_task = {'title': title, 'completed': False}
        tasks.append(new_task)
        save_tasks(tasks)
        log_event(f"WEB: Nueva tarea añadida: {title} (servidor {request.host})")

    return redirect(url_for('index'))

@app.route('/tasks/<int:task_id>/complete', methods=['POST'])
def web_complete_task(task_id):
    tasks = load_tasks()

    if 0 <= task_id < len(tasks):
        task_title = tasks[task_id]['title']
        tasks[task_id]['completed'] = True
        save_tasks(tasks)
        log_event(f"WEB: Tarea completada: {task_title} (servidor {request.host})")

    return redirect(url_for('index'))

@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
def web_delete_task(task_id):
    tasks = load_tasks()

    if 0 <= task_id < len(tasks):
        task_title = tasks[task_id]['title']
        tasks.pop(task_id)
        save_tasks(tasks)
        log_event(f"WEB: Tarea eliminada: {task_title} (servidor {request.host})")

    return redirect(url_for('index'))

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"🚀 TaskFlow Server v2.0 iniciado en puerto: {port}")
    print(f"📝 Interfaz principal: http://localhost:{port}")
    print(f"📊 Información del sistema: http://localhost:{port}/system-info")
    print(f"💚 Health check: http://localhost:{port}/health")
    app.run(host='0.0.0.0', port=port, debug=True)