import React from 'react';
import { LucideIcon } from 'lucide-react';

export function EmptyState({ icon: Icon, title, message }: { icon: LucideIcon; title: string; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-zinc-900/30 border border-zinc-800/50 rounded-xl border-dashed">
      <div className="w-12 h-12 rounded-full bg-zinc-800/50 flex items-center justify-center mb-4">
        <Icon className="w-6 h-6 text-zinc-500" />
      </div>
      <h3 className="text-sm font-medium text-zinc-200 mb-1">{title}</h3>
      <p className="text-sm text-zinc-500 max-w-sm">{message}</p>
    </div>
  );
}
