"""Production WSGI/Socket.IO entry point."""
from app import create_app, socketio, start_overdue_monitor

app = create_app()
start_overdue_monitor(app)

