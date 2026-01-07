import { createContext } from 'react';

export interface OfflineContextType {
  isOnline: boolean;
  outboxCount: number;
  flush: () => Promise<void>;
}

export const OfflineContext = createContext<OfflineContextType | undefined>(undefined);
