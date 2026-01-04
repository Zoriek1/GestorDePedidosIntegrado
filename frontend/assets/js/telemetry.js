/**
 * Plante Uma Flor - PWA v3.0
 * Telemetry Module - Centralized event and error logging
 * Phase 0: Freeze Behavior
 */

const Telemetry = {
    dbName: 'puf_telemetry',
    dbVersion: 1,
    storeName: 'telemetryLogs',
    maxLogs: 200,
    db: null,
    buffer: [],
    flushInterval: null,
    flushDelay: 750, // ms
    initialized: false,
    useLocalStorage: false,

    /**
     * Initialize telemetry system
     */
    async init() {
        if (this.initialized) return;

        try {
            // Try IndexedDB first
            await this.initIndexedDB();
            this.initialized = true;
            
            // Start flush interval
            this.startFlushInterval();
            
            this.logInfo('telemetry', 'init', 'Telemetry initialized', { db: 'indexeddb' });
        } catch (error) {
            console.warn('[Telemetry] IndexedDB failed, falling back to localStorage:', error);
            this.useLocalStorage = true;
            this.initialized = true;
            this.logInfo('telemetry', 'init', 'Telemetry initialized (localStorage fallback)', { error: error.message });
        }
    },

    /**
     * Initialize IndexedDB
     */
    async initIndexedDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onerror = () => {
                reject(request.error);
            };

            request.onsuccess = () => {
                this.db = request.result;
                resolve(this.db);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Create store if it doesn't exist
                if (!db.objectStoreNames.contains(this.storeName)) {
                    const store = db.createObjectStore(this.storeName, {
                        keyPath: 'id',
                        autoIncrement: true
                    });
                    store.createIndex('ts', 'ts', { unique: false });
                    store.createIndex('level', 'level', { unique: false });
                    store.createIndex('area', 'area', { unique: false });
                }
            };
        });
    },

    /**
     * Sanitize context data - remove sensitive information
     */
    sanitizeContext(context) {
        if (!context || typeof context !== 'object') return {};

        const sensitiveKeys = [
            'password', 'passwd', 'pwd', 'senha',
            'token', 'auth', 'authorization', 'bearer',
            'cookie', 'session', 'secret', 'key',
            'credential', 'credentialId'
        ];

        const sanitized = {};
        for (const [key, value] of Object.entries(context)) {
            const keyLower = key.toLowerCase();
            
            // Skip sensitive keys
            if (sensitiveKeys.some(sk => keyLower.includes(sk))) {
                sanitized[key] = '[REDACTED]';
                continue;
            }

            // Truncate long strings
            if (typeof value === 'string') {
                sanitized[key] = value.length > 200 ? value.substring(0, 200) + '...' : value;
            } else if (typeof value === 'object' && value !== null) {
                // Recursively sanitize nested objects (limited depth)
                sanitized[key] = this.sanitizeContext(value);
            } else {
                sanitized[key] = value;
            }
        }

        return sanitized;
    },

    /**
     * Core logging method
     */
    log(level, area, action, message, context = null, requestId = null) {
        if (!this.initialized) {
            // Queue logs until initialized
            setTimeout(() => this.log(level, area, action, message, context, requestId), 100);
            return;
        }

        const sanitizedContext = context ? this.sanitizeContext(context) : null;
        
        const logEntry = {
            ts: Date.now(),
            level,
            area,
            action,
            message: message || '',
            context: sanitizedContext,
            requestId: requestId || null
        };

        // Add to buffer
        this.buffer.push(logEntry);

        // Flush if buffer is large
        if (this.buffer.length >= 10) {
            this.flush();
        }
    },

    /**
     * Flush buffer to storage
     */
    async flush() {
        if (this.buffer.length === 0) return;

        const logsToFlush = [...this.buffer];
        this.buffer = [];

        try {
            if (this.useLocalStorage) {
                await this.flushToLocalStorage(logsToFlush);
            } else {
                await this.flushToIndexedDB(logsToFlush);
            }
        } catch (error) {
            console.error('[Telemetry] Flush error:', error);
            // Re-add to buffer on failure (limited retries)
            if (logsToFlush.length < 50) {
                this.buffer.unshift(...logsToFlush);
            }
        }
    },

    /**
     * Flush to IndexedDB
     */
    async flushToIndexedDB(logs) {
        if (!this.db) {
            await this.initIndexedDB();
        }

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);

            // Get current count to enforce maxLogs limit
            const countRequest = store.count();
            
            countRequest.onsuccess = () => {
                const currentCount = countRequest.result;
                const toAdd = logs.length;
                const toRemove = Math.max(0, currentCount + toAdd - this.maxLogs);

                if (toRemove > 0) {
                    // Remove oldest logs
                    const index = store.index('ts');
                    const range = IDBKeyRange.upperBound(Date.now());
                    const cursorRequest = index.openCursor(range);

                    let removed = 0;
                    cursorRequest.onsuccess = (e) => {
                        const cursor = e.target.result;
                        if (cursor && removed < toRemove) {
                            cursor.delete();
                            removed++;
                            cursor.continue();
                        } else {
                            // Now add new logs
                            this.addLogsToStore(store, logs, resolve, reject);
                        }
                    };
                } else {
                    this.addLogsToStore(store, logs, resolve, reject);
                }
            };

            countRequest.onerror = () => reject(countRequest.error);
        });
    },

    /**
     * Add logs to store
     */
    addLogsToStore(store, logs, resolve, reject) {
        let added = 0;
        const errors = [];

        logs.forEach((log, idx) => {
            const request = store.add(log);
            request.onsuccess = () => {
                added++;
                if (added === logs.length) {
                    if (errors.length > 0) {
                        console.warn('[Telemetry] Some logs failed to add:', errors);
                    }
                    resolve();
                }
            };
            request.onerror = () => {
                errors.push({ index: idx, error: request.error });
                added++;
                if (added === logs.length) {
                    if (errors.length > 0) {
                        console.warn('[Telemetry] Some logs failed to add:', errors);
                    }
                    resolve(); // Still resolve to not block
                }
            };
        });
    },

    /**
     * Flush to localStorage (fallback)
     */
    async flushToLocalStorage(logs) {
        try {
            const existing = JSON.parse(localStorage.getItem('puf_telemetry') || '[]');
            const combined = [...existing, ...logs];
            
            // Keep only last 50 in localStorage
            const trimmed = combined.slice(-50);
            
            localStorage.setItem('puf_telemetry', JSON.stringify(trimmed));
        } catch (error) {
            console.error('[Telemetry] localStorage flush error:', error);
            throw error;
        }
    },

    /**
     * Start periodic flush interval
     */
    startFlushInterval() {
        if (this.flushInterval) return;
        
        this.flushInterval = setInterval(() => {
            if (this.buffer.length > 0) {
                this.flush();
            }
        }, this.flushDelay);
    },

    /**
     * Stop flush interval
     */
    stopFlushInterval() {
        if (this.flushInterval) {
            clearInterval(this.flushInterval);
            this.flushInterval = null;
        }
    },

    /**
     * Helper: log info
     */
    logInfo(area, action, message, context = null, requestId = null) {
        this.log('info', area, action, message, context, requestId);
    },

    /**
     * Helper: log warning
     */
    logWarn(area, action, message, context = null, requestId = null) {
        this.log('warn', area, action, message, context, requestId);
    },

    /**
     * Helper: log error
     */
    logError(area, action, error, context = null, requestId = null) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        const errorStack = error instanceof Error ? (error.stack || '').substring(0, 500) : null;
        
        const errorContext = {
            ...(context || {}),
            errorType: error instanceof Error ? error.constructor.name : typeof error,
            errorMessage: errorMessage.substring(0, 200),
            ...(errorStack ? { stack: errorStack } : {})
        };

        this.log('error', area, action, errorMessage, errorContext, requestId);
    },

    /**
     * Get logs from storage
     */
    async getLogs(limit = 50) {
        // Flush buffer first
        await this.flush();

        try {
            if (this.useLocalStorage) {
                const logs = JSON.parse(localStorage.getItem('puf_telemetry') || '[]');
                return logs.slice(-limit).reverse(); // Most recent first
            } else {
                return await this.getLogsFromIndexedDB(limit);
            }
        } catch (error) {
            console.error('[Telemetry] Error getting logs:', error);
            return [];
        }
    },

    /**
     * Get logs from IndexedDB
     */
    async getLogsFromIndexedDB(limit) {
        if (!this.db) {
            await this.initIndexedDB();
        }

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readonly');
            const store = transaction.objectStore(this.storeName);
            const index = store.index('ts');
            
            const logs = [];
            const request = index.openCursor(null, 'prev'); // Reverse order (newest first)

            request.onsuccess = (e) => {
                const cursor = e.target.result;
                if (cursor && logs.length < limit) {
                    logs.push(cursor.value);
                    cursor.continue();
                } else {
                    resolve(logs);
                }
            };

            request.onerror = () => reject(request.error);
        });
    },

    /**
     * Clear all logs
     */
    async clearLogs() {
        // Clear buffer
        this.buffer = [];

        try {
            if (this.useLocalStorage) {
                localStorage.removeItem('puf_telemetry');
            } else {
                if (!this.db) {
                    await this.initIndexedDB();
                }

                return new Promise((resolve, reject) => {
                    const transaction = this.db.transaction([this.storeName], 'readwrite');
                    const store = transaction.objectStore(this.storeName);
                    const request = store.clear();

                    request.onsuccess = () => resolve();
                    request.onerror = () => reject(request.error);
                });
            }
        } catch (error) {
            console.error('[Telemetry] Error clearing logs:', error);
            throw error;
        }
    },

    /**
     * Export logs as JSON file
     */
    async exportLogs() {
        const logs = await this.getLogs(200);
        const exportData = {
            exportedAt: new Date().toISOString(),
            appVersion: typeof App !== 'undefined' ? App.version : 'unknown',
            logCount: logs.length,
            logs
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `puf-telemetry-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.logInfo('telemetry', 'export', 'Logs exported', { count: logs.length });
    }
};

// Auto-initialize on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => Telemetry.init());
} else {
    Telemetry.init();
}

