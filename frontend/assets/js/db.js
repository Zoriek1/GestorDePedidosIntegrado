/**
 * Plante Uma Flor - PWA v3.0
 * IndexedDB Manager - Armazenamento local para funcionalidade offline
 */

const DB = {
    name: 'PlanteUmaFlorDB',
    version: 2,
    db: null,

    /**
     * Inicializa o banco de dados IndexedDB
     */
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.name, this.version);

            request.onerror = () => {
                console.error('Erro ao abrir IndexedDB:', request.error);
                // Log error (Phase 0)
                if (typeof Telemetry !== 'undefined') {
                    Telemetry.logError('db', 'init', request.error, {
                        dbName: this.name,
                        version: this.version
                    });
                }
                reject(request.error);
            };

            request.onsuccess = () => {
                this.db = request.result;
                // Log success (Phase 0)
                if (typeof Telemetry !== 'undefined') {
                    Telemetry.logInfo('db', 'init', 'IndexedDB initialized', {
                        dbName: this.name,
                        version: this.version
                    });
                }
                resolve(this.db);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                const oldVersion = event.oldVersion;
                const newVersion = event.newVersion;

                // Log upgrade (Phase 0)
                if (typeof Telemetry !== 'undefined') {
                    Telemetry.logInfo('db', 'upgrade', 'IndexedDB schema upgrade', {
                        dbName: this.name,
                        oldVersion,
                        newVersion
                    });
                }

                // Store para pedidos pendentes (offline)
                if (!db.objectStoreNames.contains('pendingPedidos')) {
                    const pendingStore = db.createObjectStore('pendingPedidos', {
                        keyPath: 'id',
                        autoIncrement: true
                    });
                    pendingStore.createIndex('timestamp', 'timestamp', { unique: false });
                }

                // Store para cache de pedidos
                if (!db.objectStoreNames.contains('pedidosCache')) {
                    const cacheStore = db.createObjectStore('pedidosCache', {
                        keyPath: 'id'
                    });
                    cacheStore.createIndex('updated_at', 'updated_at', { unique: false });
                }

                console.log('✅ Estrutura do IndexedDB criada');
            };
        });
    },

    /**
     * Salva pedido pendente (offline)
     */
    async savePendingPedido(pedidoData) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['pendingPedidos'], 'readwrite');
            const store = transaction.objectStore('pendingPedidos');

            const pedido = {
                ...pedidoData,
                timestamp: Date.now(),
                synced: false
            };

            const request = store.add(pedido);

            request.onsuccess = () => {
                // Log write (Phase 0)
                if (typeof Telemetry !== 'undefined') {
                    Telemetry.logInfo('db', 'write', 'Pedido pendente salvo', {
                        store: 'pendingPedidos',
                        id: request.result
                    });
                }
                resolve(request.result);
            };

            request.onerror = () => {
                console.error('Erro ao salvar pedido offline:', request.error);
                // Log error (Phase 0)
                if (typeof Telemetry !== 'undefined') {
                    Telemetry.logError('db', 'write', request.error, {
                        store: 'pendingPedidos',
                        operation: 'savePendingPedido'
                    });
                }
                reject(request.error);
            };
        });
    },

    /**
     * Obtém todos os pedidos pendentes
     */
    async getPendingPedidos() {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['pendingPedidos'], 'readonly');
            const store = transaction.objectStore('pendingPedidos');
            const request = store.getAll();

            request.onsuccess = () => {
                // Log read (Phase 0)
                if (typeof Telemetry !== 'undefined') {
                    Telemetry.logInfo('db', 'read', 'Pedidos pendentes lidos', {
                        store: 'pendingPedidos',
                        count: request.result.length
                    });
                }
                resolve(request.result);
            };

            request.onerror = () => {
                // Log error (Phase 0)
                if (typeof Telemetry !== 'undefined') {
                    Telemetry.logError('db', 'read', request.error, {
                        store: 'pendingPedidos',
                        operation: 'getPendingPedidos'
                    });
                }
                reject(request.error);
            };
        });
    },

    /**
     * Remove pedido pendente após sincronização
     */
    async removePendingPedido(id) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['pendingPedidos'], 'readwrite');
            const store = transaction.objectStore('pendingPedidos');
            const request = store.delete(id);

            request.onsuccess = () => {
                console.log('✅ Pedido pendente removido:', id);
                resolve();
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    },

    /**
     * Sincroniza pedidos pendentes com o servidor
     */
    async syncPendingPedidos() {
        const pending = await this.getPendingPedidos();

        if (pending.length === 0) {
            return { success: true, synced: 0 };
        }

        // Log sync start (Phase 0)
        if (typeof Telemetry !== 'undefined') {
            Telemetry.logInfo('db', 'sync', 'Iniciando sincronização de pedidos pendentes', {
                pendingCount: pending.length
            });
        }

        let syncedCount = 0;
        const errors = [];

        for (const pedido of pending) {
            try {
                // Remove campos internos antes de enviar
                const { id, timestamp, synced, ...pedidoData } = pedido;

                const result = await API.createPedido(pedidoData);

                if (result.success) {
                    await this.removePendingPedido(id);
                    syncedCount++;
                } else {
                    errors.push({ pedido: id, error: result.error });
                }
            } catch (error) {
                console.error('Erro ao sincronizar pedido:', error);
                errors.push({ pedido: pedido.id, error: error.message });
            }
        }

        // Log sync result (Phase 0)
        if (typeof Telemetry !== 'undefined') {
            Telemetry.logInfo('db', 'sync', 'Sincronização concluída', {
                synced: syncedCount,
                errors: errors.length,
                total: pending.length
            });
        }

        if (syncedCount > 0) {
            Notification.show(`${syncedCount} pedido(s) sincronizado(s)`, 'success');
        }

        if (errors.length > 0) {
            Notification.show(`${errors.length} pedido(s) falharam na sincronização`, 'error');
        }

        return { success: errors.length === 0, synced: syncedCount, errors };
    },

    /**
     * Salva pedidos no cache local
     */
    async cachePedidos(pedidos) {
        if (!this.db) await this.init();
        
        // Validar entrada
        if (!Array.isArray(pedidos)) {
            console.error('[DB] cachePedidos recebeu dados inválidos:', pedidos);
            return Promise.reject(new Error('Pedidos deve ser um array'));
        }

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['pedidosCache'], 'readwrite');
            const store = transaction.objectStore('pedidosCache');

            // Limpar cache antigo
            store.clear();

            // Salvar novos pedidos
            pedidos.forEach(pedido => {
                store.put({
                    ...pedido,
                    cached_at: Date.now()
                });
            });

            transaction.oncomplete = () => {
                console.log(`✅ ${pedidos.length} pedidos cacheados`);
                // Log cache (Phase 0)
                if (typeof Telemetry !== 'undefined') {
                    Telemetry.logInfo('db', 'cache', 'Pedidos cacheados', {
                        store: 'pedidosCache',
                        count: pedidos.length
                    });
                }
                resolve();
            };

            transaction.onerror = () => {
                console.error('[DB] Erro ao cachear pedidos:', transaction.error);
                // Log error (Phase 0)
                if (typeof Telemetry !== 'undefined') {
                    Telemetry.logError('db', 'cache', transaction.error, {
                        store: 'pedidosCache',
                        operation: 'cachePedidos'
                    });
                }
                reject(transaction.error);
            };
        });
    },

    /**
     * Obtém pedidos do cache
     */
    async getCachedPedidos() {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['pedidosCache'], 'readonly');
            const store = transaction.objectStore('pedidosCache');
            const request = store.getAll();

            request.onsuccess = () => {
                resolve(request.result);
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    },

    /**
     * Limpa todo o cache
     */
    async clearCache() {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['pedidosCache'], 'readwrite');
            const store = transaction.objectStore('pedidosCache');
            const request = store.clear();

            request.onsuccess = () => {
                resolve();
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    },

    /**
     * Limpa todos os dados do IndexedDB
     */
    async clearAll() {
        if (!this.db) await this.init();

        try {
            await this.clearCache();
            
            const transaction = this.db.transaction(['pendingPedidos'], 'readwrite');
            const store = transaction.objectStore('pendingPedidos');
            await store.clear();

            console.log('✅ Todos os dados do IndexedDB limpos');
            Notification.show('Dados locais limpos', 'success');
        } catch (error) {
            console.error('Erro ao limpar dados:', error);
            Notification.show('Erro ao limpar dados locais', 'error');
        }
    },

    /**
     * Health check do banco de dados (Phase 0)
     */
    async dbHealthCheck() {
        try {
            if (!this.db) {
                await this.init();
            }

            const health = {
                ok: true,
                dbName: this.name,
                version: this.version,
                lastError: null
            };

            // Test read operation
            try {
                const testTransaction = this.db.transaction(['pedidosCache'], 'readonly');
                const testStore = testTransaction.objectStore('pedidosCache');
                await new Promise((resolve, reject) => {
                    const testRequest = testStore.count();
                    testRequest.onsuccess = () => resolve();
                    testRequest.onerror = () => reject(testRequest.error);
                });
            } catch (testError) {
                health.ok = false;
                health.lastError = testError.message || String(testError);
            }

            return health;
        } catch (error) {
            return {
                ok: false,
                dbName: this.name,
                version: this.version,
                lastError: error.message || String(error)
            };
        }
    }
};

// Inicializar DB quando a página carregar
document.addEventListener('DOMContentLoaded', () => {
    DB.init().catch(error => {
        console.error('Erro ao inicializar IndexedDB:', error);
    });
});

// Sincronizar pedidos pendentes quando voltar online
window.addEventListener('online', () => {
    setTimeout(() => {
        DB.syncPendingPedidos().catch(error => {
            console.error('Erro ao sincronizar pedidos:', error);
        });
    }, 1000);
});

