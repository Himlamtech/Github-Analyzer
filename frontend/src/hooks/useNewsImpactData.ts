import { useEffect, useState } from 'react';

import { fetchNewsImpactEvents, fetchNewsImpactReadiness } from '../lib/api';
import type { NewsImpactEvent, NewsImpactReadiness } from '../types';

interface NewsImpactDataState {
  events: NewsImpactEvent[];
  readiness: NewsImpactReadiness | null;
  isLoading: boolean;
  error: string | null;
}

export function useNewsImpactData(enabled = true): NewsImpactDataState {
  const [events, setEvents] = useState<NewsImpactEvent[]>([]);
  const [readiness, setReadiness] = useState<NewsImpactReadiness | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(enabled);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || events.length > 0 || readiness) {
      setIsLoading(false);
      return undefined;
    }

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
  }, [enabled, events.length, readiness]);

  return { events, readiness, isLoading, error };
}
