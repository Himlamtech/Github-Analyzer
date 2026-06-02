import React, { useEffect, useRef, useState } from 'react';

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

  useEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return;
    }

    let animationFrameId: number | null = null;

    const updateSize = (width: number, height: number): void => {
      if (animationFrameId !== null) {
        window.cancelAnimationFrame(animationFrameId);
      }
      animationFrameId = window.requestAnimationFrame(() => {
        setHasStableSize(width > 0 && height > 0);
      });
    };

    const observer = new ResizeObserver(([entry]) => {
      if (!entry) {
        return;
      }
      updateSize(entry.contentRect.width, entry.contentRect.height);
    });

    observer.observe(element);
    updateSize(element.clientWidth, element.clientHeight);

    return () => {
      observer.disconnect();
      if (animationFrameId !== null) {
        window.cancelAnimationFrame(animationFrameId);
      }
    };
  }, []);

  return (
    <div ref={containerRef} className={className}>
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
