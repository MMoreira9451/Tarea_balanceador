# TaskFlow y Load Balancer

Este proyecto contiene una aplicación Flask para la gestión de tareas y un balanceador de carga que distribuye las peticiones entre varias instancias de dicha aplicación.

## Requisitos

Instala las dependencias utilizando:

```bash
pip install -r requirements.txt
```

## Ejecución del gestor de tareas

Levanta una instancia indicando el puerto como argumento (por defecto utiliza `5000`):

```bash
python app.py 5001
```

Puedes iniciar varias instancias en distintos puertos (`5001`, `5002`, ...).

Accede a la interfaz web en `http://localhost:<PUERTO>` y a la API REST bajo la ruta `/api`.

## Ejecución del balanceador de carga

Una vez iniciadas las instancias de `app.py`, ejecuta:

```bash
python load_balancer.py
```

El balanceador expondrá los siguientes servicios:

- Aplicación en `http://localhost:8080` (redirecciona a los servidores disponibles).
- Dashboard de estado en `http://localhost:8080/lb-status`.
- API de estadísticas en `http://localhost:8080/lb-api/stats`.

## Ejemplos de uso

Agregar una tarea mediante la API:

```bash
curl -X POST -H "Content-Type: application/json" -d '{"title": "nueva tarea"}' http://localhost:8080/api/tasks
```

Consultar las tareas registradas:

```bash
curl http://localhost:8080/api/tasks
```

