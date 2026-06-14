import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';

interface SafeChartContainerProps {
  children: React.ReactNode;
  className: string;
  placeholder: string;
}

export const SafeChartContainer: React.FC<SafeChartContainerProps> = ({
  children,
  className,
  placeholder,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [hasStableSize, setHasStableSize] = useState(false);

  // Measure synchronously on first paint so the placeholder never flashes
  // on a pre-sized container (e.g. SSR-hydration or static layout).
  useLayoutEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    setHasStableSize(element.clientWidth > 0 && element.clientHeight > 0);
  }, []);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return;
    }

    const observer = new ResizeObserver(([entry]) => {
      if (!entry) {
        return;
      }
      const { width, height } = entry.contentRect;
      // Update synchronously (no rAF) so the chart unmounts before recharts
      // can measure a 0-px container and log "width/height=-1" warnings.
      setHasStableSize(width > 0 && height > 0);
    });

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, []);

  return (
    <div ref={containerRef} className={className} style={{ overflow: 'hidden' }}>
      {hasStableSize ? (
        children
      ) : (
        <div className="flex h-full min-h-[6rem] items-center justify-center rounded border border-slate-100 bg-slate-50 text-[10px] font-mono text-slate-500">
          {placeholder}
        </div>
      )}
    </div>
  );
};
