import { useEffect, useState } from 'react';

import { fetchBreakoutRepositories } from '../lib/api';
import type { Repository } from '../types';

interface BreakoutDataState {
  repositories: Repository[];
  isLoading: boolean;
  error: string | null;
}

export function useBreakoutData(): BreakoutDataState {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadBreakout(): Promise<void> {
      try {
        setIsLoading(true);
        const rows = await fetchBreakoutRepositories();
        if (!isMounted) {
          return;
        }
        setRepositories(rows);
        setError(null);
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : 'Unable to load breakout data.');
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadBreakout();

    return () => {
      isMounted = false;
    };
  }, []);

  return { repositories, isLoading, error };
}
