"""
Backup Package - Servidor de Backup com Failover Automático.

Exporta:
- BackupServer: Classe de monitoramento e failover
"""

from .monitor import BackupServer

__all__ = ['BackupServer']
