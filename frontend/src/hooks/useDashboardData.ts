import { useEffect, useState } from 'react';

import { fetchDashboardSnapshot } from '../lib/api';
import type { DashboardSnapshot } from '../types';

interface DashboardDataState {
  data: DashboardSnapshot | null;
  isLoading: boolean;
  error: string | null;
}

const REFRESH_INTERVAL_MS = 60_000;

export function useDashboardData(): DashboardDataState {
  const [data, setData] = useState<DashboardSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadSnapshot(): Promise<void> {
      try {
        if (isMounted && data === null) {
          setIsLoading(true);
        }
        const snapshot = await fetchDashboardSnapshot();
        if (!isMounted) {
          return;
        }
        setData(snapshot);
        setError(null);
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : 'Unable to load dashboard data.');
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadSnapshot();
    const interval = window.setInterval(() => {
      void loadSnapshot();
    }, REFRESH_INTERVAL_MS);

    return () => {
      isMounted = false;
      window.clearInterval(interval);
    };
  }, []);

  return { data, isLoading, error };
}
