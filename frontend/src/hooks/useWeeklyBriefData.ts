import { useEffect, useState } from 'react';

import { fetchWeeklyBriefSnapshot } from '../lib/api';
import type { WeeklyBriefSnapshot } from '../types';

interface WeeklyBriefDataState {
  data: WeeklyBriefSnapshot | null;
  isLoading: boolean;
  error: string | null;
}

export function useWeeklyBriefData(): WeeklyBriefDataState {
  const [data, setData] = useState<WeeklyBriefSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadWeeklyBrief(): Promise<void> {
      try {
        setIsLoading(true);
        const snapshot = await fetchWeeklyBriefSnapshot();
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
            : 'Unable to load weekly brief data.',
        );
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadWeeklyBrief();

    return () => {
      isMounted = false;
    };
  }, []);

  return { data, isLoading, error };
}
