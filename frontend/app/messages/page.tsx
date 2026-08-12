"use client";

import { Suspense, useEffect, useState } from 'react';
import { getMessages, PaginatedMessages } from '@/lib/api';
import { SearchBar } from '@/components/SearchBar';
import { MessageCard } from '@/components/MessageCard';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { EmptyState } from '@/components/EmptyState';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { AlertCircle, Inbox, ChevronLeft, ChevronRight } from 'lucide-react';

function MessagesContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  
  const page = Number(searchParams?.get('page')) || 1;
  const actionFilter = searchParams?.get('action') || '';
  const search = searchParams?.get('search') || '';
  
  const [data, setData] = useState<PaginatedMessages | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const res = await getMessages({ page, limit: 20, action: actionFilter, search });
        setData(res);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load messages');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [page, actionFilter, search]);

  const setAction = (act: string) => {
    const params = new URLSearchParams(searchParams?.toString() || '');
    if (act) params.set('action', act);
    else params.delete('action');
    params.set('page', '1');
    router.push(`${pathname}?${params.toString()}`);
  };

  const setPage = (p: number) => {
    const params = new URLSearchParams(searchParams?.toString() || '');
    params.set('page', String(p));
    router.push(`${pathname}?${params.toString()}`);
  };

  const filters = [
    { id: '', label: 'All' },
    { id: 'notify', label: 'Notify' },
    { id: 'digest', label: 'Digest' },
    { id: 'mute', label: 'Mute' },
  ];

  return (
    <div className="p-6 md:p-10 space-y-6 h-full flex flex-col">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Messages</h1>
        <p className="text-sm text-zinc-500 mt-1">Browse and filter through processed messages</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
        <SearchBar />
        <div className="flex items-center space-x-2 bg-zinc-900 p-1 rounded-lg border border-zinc-800">
          {filters.map((f) => (
            <button
              key={f.id}
              onClick={() => setAction(f.id)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                actionFilter === f.id
                  ? 'bg-zinc-800 text-zinc-100'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        {error ? (
          <div className="p-8 text-center text-red-400">
            <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>{error}</p>
          </div>
        ) : loading ? (
          <LoadingSkeleton count={5} />
        ) : !data || data.messages.length === 0 ? (
          <div className="pt-20">
            <EmptyState icon={Inbox} title="No messages found" message="Try adjusting your filters or search terms." />
          </div>
        ) : (
          <div className="space-y-4 pb-4">
            {data.messages.map(msg => (
              <MessageCard key={msg.message_id} message={msg} />
            ))}
          </div>
        )}
      </div>

      {data && data.total > 0 && (
        <div className="pt-4 border-t border-zinc-800 flex items-center justify-between text-sm text-zinc-400 shrink-0">
          <div>
            Showing {((page - 1) * (data.limit || 20)) + 1} - {Math.min(page * (data.limit || 20), data.total)} of {data.total}
          </div>
          <div className="flex space-x-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
              className="p-2 rounded bg-zinc-900 border border-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-zinc-800 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              disabled={page * (data.limit || 20) >= data.total}
              onClick={() => setPage(page + 1)}
              className="p-2 rounded bg-zinc-900 border border-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-zinc-800 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function MessagesPage() {
  return (
    <Suspense fallback={<div className="p-6 md:p-10"><LoadingSkeleton count={5} /></div>}>
      <MessagesContent />
    </Suspense>
  );
}
