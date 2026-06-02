import { useEffect, useState } from 'react';

import { fetchNewsImpactEvents, fetchNewsImpactReadiness } from '../lib/api';
import type { NewsImpactEvent, NewsImpactReadiness } from '../types';

interface NewsImpactDataState {
  events: NewsImpactEvent[];
  readiness: NewsImpactReadiness | null;
  isLoading: boolean;
  error: string | null;
}

export function useNewsImpactData(): NewsImpactDataState {
  const [events, setEvents] = useState<NewsImpactEvent[]>([]);
  const [readiness, setReadiness] = useState<NewsImpactReadiness | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadNewsImpact(): Promise<void> {
      try {
        setIsLoading(true);
        const [snapshot, readinessSnapshot] = await Promise.all([
          fetchNewsImpactEvents(),
          fetchNewsImpactReadiness(),
        ]);
        if (!isMounted) {
          return;
        }
        setEvents(snapshot);
        setReadiness(readinessSnapshot);
        setError(null);
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        setError(
          loadError instanceof Error
            ? loadError.message
            : 'Unable to load news impact data.',
        );
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadNewsImpact();

    return () => {
      isMounted = false;
    };
  }, []);

  return { events, readiness, isLoading, error };
}
