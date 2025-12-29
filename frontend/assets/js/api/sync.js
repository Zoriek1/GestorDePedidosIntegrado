/**
 * Sync Manager - Camada de sincronização offline
 * Gerencia IndexedDB ↔ API
 */

class SyncManager {
    constructor(apiClient, dbName = 'PlanteUmaFlorDB') {
        this.api = apiClient;
        this.dbName = dbName;
        this.db = null;
        this.syncing = false;
    }

    async init() {
        if (this.db) return this.db;
        
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, 2);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve(this.db);
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
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
                
                // Store para fila de sincronização
                if (!db.objectStoreNames.contains('syncQueue')) {
                    const syncStore = db.createObjectStore('syncQueue', {
                        keyPath: 'id',
                        autoIncrement: true
                    });
                    syncStore.createIndex('timestamp', 'timestamp', { unique: false });
                }
            };
        });
    }

    async saveOffline(entity, storeName) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.put({
                ...entity,
                timestamp: Date.now()
            });
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async getOffline(storeName, key) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.get(key);
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async getAllOffline(storeName) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.getAll();
            
            request.onsuccess = () => resolve(request.result || []);
            request.onerror = () => reject(request.error);
        });
    }

    async addToSyncQueue(operation) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['syncQueue'], 'readwrite');
            const store = transaction.objectStore('syncQueue');
            
            const item = {
                ...operation,
                timestamp: Date.now(),
                status: 'pending'
            };
            
            const request = store.add(item);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async sync() {
        if (this.syncing || !navigator.onLine) return;
        
        this.syncing = true;
        
        try {
            if (!this.db) await this.init();
            
            const transaction = this.db.transaction(['syncQueue'], 'readwrite');
            const store = transaction.objectStore('syncQueue');
            const queue = await this.getAllOffline('syncQueue');
            
            for (const item of queue) {
                if (item.status === 'synced') continue;
                
                try {
                    let result;
                    switch (item.operation) {
                        case 'create':
                            result = await this.api.createPedido(item.data);
                            break;
                        case 'update':
                            result = await this.api.updatePedido(item.entityId, item.data);
                            break;
                        case 'delete':
                            result = await this.api.deletePedido(item.entityId);
                            break;
                        default:
                            console.warn('Operação desconhecida:', item.operation);
                            continue;
                    }
                    
                    if (result.success) {
                        // Marcar como sincronizado
                        item.status = 'synced';
                        const updateRequest = store.put(item);
                        await new Promise((resolve, reject) => {
                            updateRequest.onsuccess = () => resolve();
                            updateRequest.onerror = () => reject(updateRequest.error);
                        });
                    }
                } catch (error) {
                    console.error('Erro ao sincronizar item:', error);
                    item.status = 'failed';
                    item.error = error.message;
                    store.put(item);
                }
            }
        } finally {
            this.syncing = false;
        }
    }

    async clearSyncQueue() {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['syncQueue'], 'readwrite');
            const store = transaction.objectStore('syncQueue');
            const request = store.clear();
            
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }
}

// Exportar instância global
const syncManager = new SyncManager(apiClient);

// Auto-sync quando online
if (typeof window !== 'undefined') {
    window.addEventListener('online', () => {
        syncManager.sync();
    });
}

