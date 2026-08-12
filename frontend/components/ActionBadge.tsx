import React from 'react';

export function ActionBadge({ action }: { action: 'notify' | 'digest' | 'mute' | string }) {
  const styles = {
    notify: 'bg-red-500/10 text-red-500 border-red-500/20',
    digest: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    mute: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
  };

  const style = styles[action as keyof typeof styles] || 'bg-zinc-800 text-zinc-300 border-zinc-700';

  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${style} uppercase tracking-wider`}>
      {action}
    </span>
  );
}
