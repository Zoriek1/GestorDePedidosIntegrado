/**
 * Toast/Notification Provider
 * Unified toast notifications using MUI Snackbar
 */

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { Snackbar, Alert, AlertColor } from '@mui/material';

interface ToastContextType {
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  warning: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

interface ToastMessage {
  id: number;
  message: string;
  severity: AlertColor;
}

interface ToastProviderProps {
  children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  const [, setToasts] = useState<ToastMessage[]>([]);
  const [open, setOpen] = useState(false);
  const [currentToast, setCurrentToast] = useState<ToastMessage | null>(null);

  const showToast = useCallback((message: string, severity: AlertColor) => {
    const id = Date.now();
    const newToast: ToastMessage = { id, message, severity };
    setToasts((prev) => [...prev, newToast]);
    setCurrentToast(newToast);
    setOpen(true);
  }, []);

  const handleClose = useCallback((_event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }
    setOpen(false);
    
    // Process next toast in queue after a short delay
    setTimeout(() => {
      setToasts((prev) => {
        const next = prev.slice(1);
        if (next.length > 0) {
          setCurrentToast(next[0]);
          setOpen(true);
        } else {
          setCurrentToast(null);
        }
        return next;
      });
    }, 150);
  }, []);

  const success = useCallback((message: string) => showToast(message, 'success'), [showToast]);
  const error = useCallback((message: string) => showToast(message, 'error'), [showToast]);
  const info = useCallback((message: string) => showToast(message, 'info'), [showToast]);
  const warning = useCallback((message: string) => showToast(message, 'warning'), [showToast]);

  return (
    <ToastContext.Provider value={{ success, error, info, warning }}>
      {children}
      {currentToast && (
        <Snackbar
          open={open}
          autoHideDuration={6000}
          onClose={handleClose}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <Alert onClose={handleClose} severity={currentToast.severity} sx={{ width: '100%' }}>
            {currentToast.message}
          </Alert>
        </Snackbar>
      )}
    </ToastContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastContextType {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

