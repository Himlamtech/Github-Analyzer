import { useEffect, useState } from 'react';

import { fetchRotationCategories } from '../lib/api';
import type { EcosystemCategory } from '../types';

interface RotationDataState {
  categories: EcosystemCategory[];
  isLoading: boolean;
  error: string | null;
}

export function useRotationData(enabled = true): RotationDataState {
  const [categories, setCategories] = useState<EcosystemCategory[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(enabled);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || categories.length > 0) {
      setIsLoading(false);
      return undefined;
    }

    let isMounted = true;

    async function loadRotation(): Promise<void> {
      try {
        setIsLoading(true);
        const rows = await fetchRotationCategories();
        if (!isMounted) {
          return;
        }
        setCategories(rows);
        setError(null);
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        setError(
          loadError instanceof Error ? loadError.message : 'Unable to load ecosystem rotation.',
        );
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadRotation();

    return () => {
      isMounted = false;
    };
  }, [categories.length, enabled]);

  return { categories, isLoading, error };
}
