import { useEffect, useState } from 'react';

import { fetchRepoTimeseries } from '../lib/api';
import type { RepoTimeseriesPoint } from '../types';

interface RepoTimeseriesState {
  points: RepoTimeseriesPoint[];
  isLoading: boolean;
  error: string | null;
}

export function useRepoTimeseries(repoName: string | null): RepoTimeseriesState {
  const [points, setPoints] = useState<RepoTimeseriesPoint[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    if (!repoName) {
      setPoints([]);
      setIsLoading(false);
      setError(null);
      return () => {
        isMounted = false;
      };
    }

    async function loadTimeseries(): Promise<void> {
      try {
        setIsLoading(true);
        const targetRepoName = repoName;
        if (targetRepoName === null) {
          return;
        }
        const rows = await fetchRepoTimeseries(targetRepoName);
        if (!isMounted) {
          return;
        }
        setPoints(rows);
        setError(null);
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : 'Unable to load repository history.');
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadTimeseries();

    return () => {
      isMounted = false;
    };
  }, [repoName]);

  return { points, isLoading, error };
}
