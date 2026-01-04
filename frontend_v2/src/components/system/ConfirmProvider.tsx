/**
 * Confirm Modal Provider
 * Unified confirmation dialogs using MUI Dialog
 */

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
} from '@mui/material';

interface ConfirmOptions {
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  confirmColor?: 'primary' | 'error' | 'warning' | 'info' | 'success' | 'secondary';
}

interface ConfirmContextType {
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const ConfirmContext = createContext<ConfirmContextType | undefined>(undefined);

interface ConfirmProviderProps {
  children: ReactNode;
}

export function ConfirmProvider({ children }: ConfirmProviderProps) {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const [resolvePromise, setResolvePromise] = useState<((value: boolean) => void) | null>(null);

  const confirm = useCallback((confirmOptions: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setOptions(confirmOptions);
      setResolvePromise(() => resolve);
      setOpen(true);
    });
  }, []);

  const handleClose = useCallback((confirmed: boolean) => {
    setOpen(false);
    if (resolvePromise) {
      resolvePromise(confirmed);
      setResolvePromise(null);
    }
    // Clear options after animation
    setTimeout(() => setOptions(null), 150);
  }, [resolvePromise]);

  const handleConfirm = useCallback(() => {
    handleClose(true);
  }, [handleClose]);

  const handleCancel = useCallback(() => {
    handleClose(false);
  }, [handleClose]);

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      {options && (
        <Dialog
          open={open}
          onClose={handleCancel}
          aria-labelledby="confirm-dialog-title"
          aria-describedby="confirm-dialog-description"
        >
          <DialogTitle id="confirm-dialog-title">{options.title}</DialogTitle>
          <DialogContent>
            <DialogContentText id="confirm-dialog-description">
              {options.description}
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCancel} color="inherit">
              {options.cancelText || 'Cancelar'}
            </Button>
            <Button
              onClick={handleConfirm}
              color={options.confirmColor || 'primary'}
              variant="contained"
              autoFocus
            >
              {options.confirmText || 'Confirmar'}
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </ConfirmContext.Provider>
  );
}

export function useConfirm(): (options: ConfirmOptions) => Promise<boolean> {
  const context = useContext(ConfirmContext);
  if (context === undefined) {
    throw new Error('useConfirm must be used within a ConfirmProvider');
  }
  return context.confirm;
}

