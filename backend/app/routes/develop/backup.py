# -*- coding: utf-8 -*-
"""
Rotas de Backup - Endpoints administrativos para gerenciamento de backup
"""
import sys
from pathlib import Path

from flask import Blueprint, jsonify

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.middleware import requires_edit_auth  # noqa: E402
from scripts.backup.status import get_backup_health  # noqa: E402

backup_admin_bp = Blueprint('backup_admin', __name__, url_prefix='/api/admin/backup')


@backup_admin_bp.route('/health', methods=['GET'])
@requires_edit_auth
def backup_health():
    """
    Retorna health do sistema de backup

    GET /api/admin/backup/health

    Returns:
        JSON com health (OK/WARN/FAIL), status completo e issues
    """
    try:
        import os
        max_age_hours = int(os.environ.get('BACKUP_HEALTH_MAX_AGE_HOURS', '24'))

        health_data = get_backup_health(max_age_hours=max_age_hours)

        return jsonify({
            'success': True,
            'health': health_data['health'],
            'status': health_data['status'],
            'issues': health_data['issues'],
            'last_update': health_data['status'].get('last_backup_ok_at')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro ao obter health de backup: {str(e)}'
        }), 500

