import { useContext } from 'react';
import { OfflineContext, type OfflineContextType } from './OfflineContext';

export function useOffline(): OfflineContextType {
  const context = useContext(OfflineContext);
  if (!context) {
    throw new Error('useOffline must be used within OfflineProvider');
  }
  return context;
}
