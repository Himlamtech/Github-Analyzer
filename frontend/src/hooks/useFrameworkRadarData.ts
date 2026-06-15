import { useEffect, useState } from 'react';

import { fetchFrameworkRadarSnapshot } from '../lib/api';
import type { FrameworkRadarSnapshot } from '../types';

interface FrameworkRadarDataState {
  data: FrameworkRadarSnapshot | null;
  isLoading: boolean;
  error: string | null;
}

export function useFrameworkRadarData(enabled = true): FrameworkRadarDataState {
  const [data, setData] = useState<FrameworkRadarSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(enabled);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || data) {
      setIsLoading(false);
      return undefined;
    }

    let isMounted = true;

    async function loadFrameworkRadar(): Promise<void> {
      try {
        setIsLoading(true);
        const snapshot = await fetchFrameworkRadarSnapshot();
        if (!isMounted) {
          return;
        }
        setData(snapshot);
        setError(null);
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        setError(
          loadError instanceof Error
            ? loadError.message
            : 'Unable to load framework radar data.',
        );
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadFrameworkRadar();

    return () => {
      isMounted = false;
    };
  }, [data, enabled]);

  return { data, isLoading, error };
}
