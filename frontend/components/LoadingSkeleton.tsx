import React from 'react';

export function LoadingSkeleton({ count = 1, type = 'card' }: { count?: number; type?: 'card' | 'stat' }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={`animate-pulse bg-zinc-900 rounded-xl border border-zinc-800 p-5 ${type === 'stat' ? 'h-28' : 'h-36'}`}>
          <div className="flex justify-between mb-4">
            <div className="flex space-x-3">
              <div className="w-10 h-10 bg-zinc-800 rounded-full" />
              <div className="space-y-2">
                <div className="h-4 w-24 bg-zinc-800 rounded" />
                <div className="h-3 w-16 bg-zinc-800 rounded" />
              </div>
            </div>
            <div className="h-6 w-16 bg-zinc-800 rounded-full" />
          </div>
          <div className="space-y-2">
            <div className="h-4 w-3/4 bg-zinc-800 rounded" />
            <div className="h-4 w-1/2 bg-zinc-800 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}
