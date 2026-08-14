"use client";

import { useEffect, useState } from 'react';
import { getStats, getMessages, getDigestSummary, Stats, MessageWithDecision } from '@/lib/api';
import { StatCard } from '@/components/StatCard';
import { MessageCard } from '@/components/MessageCard';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { Inbox, BellRing, BookOpen, VolumeX, AlertCircle, X, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recent, setRecent] = useState<MessageWithDecision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [showDigestModal, setShowDigestModal] = useState(false);
  const [digestSummary, setDigestSummary] = useState<string | null>(null);
  const [loadingDigest, setLoadingDigest] = useState(false);

  const fetchDigest = async () => {
    setShowDigestModal(true);
    setLoadingDigest(true);
    try {
      const res = await getDigestSummary();
      setDigestSummary(res.summary);
    } catch {
      setDigestSummary("Failed to load summary. Try again later.");
    } finally {
      setLoadingDigest(false);
    }
  };

  useEffect(() => {
    async function loadData() {
      try {
        const [statsData, messagesData] = await Promise.all([
          getStats(),
          getMessages({ limit: 5 })
        ]);
        setStats(statsData);
        setRecent(messagesData.messages);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (error) {
    return (
      <div className="p-8 h-full flex items-center justify-center">
        <div className="text-center text-red-400">
          <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>{error}</p>
        </div>
      </div>
    );
  }

  const notifyPct = stats?.total ? ((stats.notify_count / stats.total) * 100) : 0;
  const digestPct = stats?.total ? ((stats.digest_count / stats.total) * 100) : 0;
  const mutePct = stats?.total ? ((stats.mute_count / stats.total) * 100) : 0;

  return (
    <div className="p-6 md:p-10 space-y-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Dashboard</h1>
        <p className="text-sm text-zinc-500 mt-1">Overview of your automated message routing</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <LoadingSkeleton count={4} type="stat" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard label="Total Processed" value={stats?.total || 0} icon={Inbox} colorClass="text-zinc-200" delay={0} />
          <StatCard label="Notified" value={stats?.notify_count || 0} icon={BellRing} colorClass="text-red-500" delay={0.1} />
          <StatCard label="Digested" value={stats?.digest_count || 0} icon={BookOpen} colorClass="text-blue-500" delay={0.2} onClick={fetchDigest} />
          <StatCard label="Muted" value={stats?.mute_count || 0} icon={VolumeX} colorClass="text-zinc-500" delay={0.3} />
        </div>
      )}

      {stats && stats.total > 0 && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
          className="space-y-3"
        >
          <div className="flex justify-between items-center text-sm">
            <h3 className="font-medium text-zinc-300">Action Distribution</h3>
            <span className="text-zinc-500">{stats.total} total messages</span>
          </div>
          <div className="h-3 w-full bg-zinc-900 rounded-full overflow-hidden flex">
            <div style={{ width: `${notifyPct}%` }} className="bg-red-500/80 transition-all duration-1000" />
            <div style={{ width: `${digestPct}%` }} className="bg-blue-500/80 transition-all duration-1000" />
            <div style={{ width: `${mutePct}%` }} className="bg-zinc-600/80 transition-all duration-1000" />
          </div>
          <div className="flex space-x-6 text-xs text-zinc-400">
            <div className="flex items-center"><div className="w-2 h-2 rounded-full bg-red-500/80 mr-2" /> Notify ({notifyPct.toFixed(1)}%)</div>
            <div className="flex items-center"><div className="w-2 h-2 rounded-full bg-blue-500/80 mr-2" /> Digest ({digestPct.toFixed(1)}%)</div>
            <div className="flex items-center"><div className="w-2 h-2 rounded-full bg-zinc-600/80 mr-2" /> Mute ({mutePct.toFixed(1)}%)</div>
          </div>
        </motion.div>
      )}

      <div>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-zinc-100">Recent Activity</h2>
          <a href="/messages" className="text-sm text-violet-400 hover:text-violet-300 transition-colors">View all</a>
        </div>
        
        {loading ? (
          <div className="space-y-4"><LoadingSkeleton count={3} /></div>
        ) : recent.length > 0 ? (
          <div className="grid grid-cols-1 gap-4">
            {recent.map((msg, i) => (
              <motion.div key={msg.message_id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 + i * 0.1 }}>
                <MessageCard message={msg} />
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="text-center py-10 text-zinc-500 border border-dashed border-zinc-800 rounded-xl bg-zinc-900/30">
            No messages processed yet.
          </div>
        )}
      </div>

      {showDigestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl"
          >
            <div className="flex items-center justify-between p-5 border-b border-zinc-800 bg-zinc-900/50">
              <h2 className="text-lg font-semibold text-zinc-100 flex items-center">
                <Sparkles className="w-5 h-5 text-blue-400 mr-2" />
                Digest Summary
              </h2>
              <button onClick={() => setShowDigestModal(false)} className="text-zinc-400 hover:text-zinc-200 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 min-h-[150px]">
              {loadingDigest ? (
                <div className="flex flex-col items-center justify-center h-full text-zinc-500 space-y-3">
                  <div className="w-6 h-6 border-2 border-zinc-600 border-t-blue-500 rounded-full animate-spin" />
                  <p className="text-sm">AI is summarizing your digested messages...</p>
                </div>
              ) : (
                <div className="text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap">
                  {digestSummary}
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
