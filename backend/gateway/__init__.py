"""
Gateway Package - Web Gateway Flask/SocketIO.

Exporta:
- app: Instância Flask
- socketio: Instância SocketIO
- run_app: Função para iniciar a aplicação
"""

from .app import app, socketio, run_app

__all__ = ['app', 'socketio', 'run_app']
