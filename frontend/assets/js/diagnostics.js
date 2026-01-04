/**
 * Plante Uma Flor - PWA v3.0
 * Diagnostics Module - Diagnostic UI for Phase 0
 */

const Diagnostics = {
    /**
     * Show diagnostics modal
     */
    async show() {
        try {
            // Gather diagnostic information
            const info = await this.gatherInfo();
            const logs = await this.getRecentLogs();

            // Create modal content
            const content = this.createModalContent(info, logs);

            // Show modal
            if (typeof Modal !== 'undefined' && Modal.custom) {
                Modal.custom(content, null);
            } else {
                console.error('Modal component not available');
            }
        } catch (error) {
            console.error('[Diagnostics] Error showing diagnostics:', error);
            if (typeof Notification !== 'undefined') {
                Notification.error('Erro ao abrir diagnóstico');
            }
        }
    },

    /**
     * Gather diagnostic information
     */
    async gatherInfo() {
        const info = {
            appVersion: typeof App !== 'undefined' ? App.version : 'unknown',
            online: typeof Utils !== 'undefined' ? Utils.isOnline() : navigator.onLine,
            swStatus: this.getServiceWorkerStatus(),
            dbHealth: null
        };

        // Get DB health
        if (typeof DB !== 'undefined' && DB.dbHealthCheck) {
            try {
                info.dbHealth = await DB.dbHealthCheck();
            } catch (error) {
                info.dbHealth = { ok: false, error: error.message };
            }
        }

        return info;
    },

    /**
     * Get Service Worker status
     */
    getServiceWorkerStatus() {
        if (!('serviceWorker' in navigator)) {
            return { supported: false, registered: false };
        }

        const status = {
            supported: true,
            registered: false,
            controlling: false,
            waiting: false,
            installing: false
        };

        if (typeof App !== 'undefined' && App._swRegistration) {
            status.registered = true;
            status.controlling = !!navigator.serviceWorker.controller;
            
            const reg = App._swRegistration;
            if (reg.installing) status.installing = true;
            if (reg.waiting) status.waiting = true;
        } else if (navigator.serviceWorker.controller) {
            status.registered = true;
            status.controlling = true;
        }

        return status;
    },

    /**
     * Get recent logs
     */
    async getRecentLogs() {
        if (typeof Telemetry !== 'undefined' && Telemetry.getLogs) {
            try {
                return await Telemetry.getLogs(50);
            } catch (error) {
                console.error('[Diagnostics] Error getting logs:', error);
                return [];
            }
        }
        return [];
    },

    /**
     * Create modal content HTML
     */
    createModalContent(info, logs) {
        const swStatusText = this.formatSWStatus(info.swStatus);
        const dbHealthText = this.formatDBHealth(info.dbHealth);
        const onlineText = info.online ? '<span class="text-green-600 font-semibold">Online</span>' : '<span class="text-red-600 font-semibold">Offline</span>';

        const logsTable = this.createLogsTable(logs);

        return `
            <div class="p-6 max-w-4xl mx-auto">
                <h2 class="text-2xl font-bold text-gray-800 mb-6">
                    <i class="fas fa-stethoscope text-primary mr-2"></i>
                    Diagnóstico do Sistema
                </h2>

                <!-- System Info -->
                <div class="bg-gray-50 rounded-lg p-4 mb-6">
                    <h3 class="text-lg font-semibold text-gray-700 mb-4">Informações do Sistema</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <span class="text-gray-600">Versão do App:</span>
                            <span class="ml-2 font-semibold">${info.appVersion}</span>
                        </div>
                        <div>
                            <span class="text-gray-600">Status de Conexão:</span>
                            <span class="ml-2">${onlineText}</span>
                        </div>
                        <div>
                            <span class="text-gray-600">Service Worker:</span>
                            <span class="ml-2">${swStatusText}</span>
                        </div>
                        <div>
                            <span class="text-gray-600">IndexedDB:</span>
                            <span class="ml-2">${dbHealthText}</span>
                        </div>
                    </div>
                </div>

                <!-- Logs -->
                <div class="mb-6">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-700">Últimos 50 Logs</h3>
                        <div class="flex gap-2">
                            <button 
                                id="btn-export-logs" 
                                class="px-4 py-2 bg-primary text-white rounded hover:bg-secondary transition"
                            >
                                <i class="fas fa-download mr-2"></i>Exportar Logs
                            </button>
                            <button 
                                id="btn-clear-logs" 
                                class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition"
                            >
                                <i class="fas fa-trash mr-2"></i>Limpar Logs
                            </button>
                        </div>
                    </div>
                    ${logsTable}
                </div>

                <!-- Actions -->
                <div class="flex justify-end gap-2 mt-6">
                    <button 
                        data-modal-close
                        class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition"
                    >
                        Fechar
                    </button>
                </div>
            </div>
        `;
    },

    /**
     * Format Service Worker status
     */
    formatSWStatus(status) {
        if (!status.supported) {
            return '<span class="text-gray-500">Não suportado</span>';
        }
        if (!status.registered) {
            return '<span class="text-yellow-600">Não registrado</span>';
        }
        
        const parts = [];
        if (status.controlling) parts.push('<span class="text-green-600">Controlando</span>');
        if (status.waiting) parts.push('<span class="text-yellow-600">Aguardando</span>');
        if (status.installing) parts.push('<span class="text-blue-600">Instalando</span>');
        
        return parts.length > 0 ? parts.join(', ') : '<span class="text-gray-500">Registrado</span>';
    },

    /**
     * Format DB health
     */
    formatDBHealth(health) {
        if (!health) {
            return '<span class="text-gray-500">N/A</span>';
        }
        if (health.ok) {
            return `<span class="text-green-600">OK (${health.dbName || 'N/A'}, v${health.version || 'N/A'})</span>`;
        }
        return `<span class="text-red-600">Erro: ${health.lastError || health.error || 'Desconhecido'}</span>`;
    },

    /**
     * Create logs table HTML
     */
    createLogsTable(logs) {
        if (!logs || logs.length === 0) {
            return '<p class="text-gray-500 text-center py-4">Nenhum log disponível</p>';
        }

        const formatTimestamp = (ts) => {
            const date = new Date(ts);
            return date.toLocaleString('pt-BR', { 
                day: '2-digit', 
                month: '2-digit', 
                year: 'numeric',
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
            });
        };

        const getLevelColor = (level) => {
            switch (level) {
                case 'error': return 'text-red-600';
                case 'warn': return 'text-yellow-600';
                case 'info': return 'text-blue-600';
                default: return 'text-gray-600';
            }
        };

        const rows = logs.map(log => {
            const levelColor = getLevelColor(log.level);
            const contextStr = log.context ? JSON.stringify(log.context).substring(0, 100) : '';
            
            return `
                <tr class="border-b border-gray-200 hover:bg-gray-50">
                    <td class="px-3 py-2 text-sm text-gray-600">${formatTimestamp(log.ts)}</td>
                    <td class="px-3 py-2 text-sm"><span class="${levelColor} font-semibold">${log.level.toUpperCase()}</span></td>
                    <td class="px-3 py-2 text-sm text-gray-700">${log.area || '-'}</td>
                    <td class="px-3 py-2 text-sm text-gray-700">${log.action || '-'}</td>
                    <td class="px-3 py-2 text-sm text-gray-600">${(log.message || '').substring(0, 80)}${log.message && log.message.length > 80 ? '...' : ''}</td>
                    <td class="px-3 py-2 text-sm text-gray-500">${contextStr ? contextStr.substring(0, 50) + '...' : '-'}</td>
                </tr>
            `;
        }).join('');

        return `
            <div class="overflow-x-auto border border-gray-200 rounded-lg">
                <table class="w-full text-left">
                    <thead class="bg-gray-100">
                        <tr>
                            <th class="px-3 py-2 text-sm font-semibold text-gray-700">Timestamp</th>
                            <th class="px-3 py-2 text-sm font-semibold text-gray-700">Level</th>
                            <th class="px-3 py-2 text-sm font-semibold text-gray-700">Área</th>
                            <th class="px-3 py-2 text-sm font-semibold text-gray-700">Ação</th>
                            <th class="px-3 py-2 text-sm font-semibold text-gray-700">Mensagem</th>
                            <th class="px-3 py-2 text-sm font-semibold text-gray-700">Contexto</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}
                    </tbody>
                </table>
            </div>
        `;
    },

    /**
     * Bind event handlers after modal is shown
     */
    bindHandlers() {
        // Export logs button
        const exportBtn = document.getElementById('btn-export-logs');
        if (exportBtn) {
            exportBtn.addEventListener('click', async () => {
                if (typeof Telemetry !== 'undefined' && Telemetry.exportLogs) {
                    try {
                        await Telemetry.exportLogs();
                        if (typeof Notification !== 'undefined') {
                            Notification.success('Logs exportados com sucesso');
                        }
                    } catch (error) {
                        console.error('[Diagnostics] Export error:', error);
                        if (typeof Notification !== 'undefined') {
                            Notification.error('Erro ao exportar logs');
                        }
                    }
                }
            });
        }

        // Clear logs button
        const clearBtn = document.getElementById('btn-clear-logs');
        if (clearBtn) {
            clearBtn.addEventListener('click', async () => {
                if (typeof Modal !== 'undefined' && Modal.confirm) {
                    const confirmed = await Modal.confirm({
                        title: 'Limpar Logs',
                        message: 'Tem certeza que deseja limpar todos os logs? Esta ação não pode ser desfeita.',
                        confirmText: 'Limpar',
                        cancelText: 'Cancelar',
                        confirmClass: 'btn-danger'
                    });

                    if (confirmed && typeof Telemetry !== 'undefined' && Telemetry.clearLogs) {
                        try {
                            await Telemetry.clearLogs();
                            if (typeof Notification !== 'undefined') {
                                Notification.success('Logs limpos com sucesso');
                            }
                            // Refresh modal
                            setTimeout(() => this.show(), 500);
                        } catch (error) {
                            console.error('[Diagnostics] Clear error:', error);
                            if (typeof Notification !== 'undefined') {
                                Notification.error('Erro ao limpar logs');
                            }
                        }
                    }
                }
            });
        }
    }
};

// Override show to bind handlers after modal is created
const originalShow = Diagnostics.show;
Diagnostics.show = async function() {
    await originalShow.call(this);
    // Bind handlers after a short delay to ensure DOM is ready
    setTimeout(() => this.bindHandlers(), 100);
};

