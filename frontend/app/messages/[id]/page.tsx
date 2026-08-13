"use client";

import { useEffect, useState } from 'react';
import { getMessage, getTraces, MessageWithDecision, Decision, ReasoningTrace } from '@/lib/api';
import { stripEmojis } from '@/lib/utils';
import { ActionBadge } from '@/components/ActionBadge';
import { TimelineStep } from '@/components/TimelineStep';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { ArrowLeft, User, Users, Calendar, AlertCircle, FileText } from 'lucide-react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { use } from 'react';

export default function MessageDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [data, setData] = useState<(MessageWithDecision & { sender_info?: Record<string, unknown> }) | null>(null);
  const [traces, setTraces] = useState<ReasoningTrace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [msgData, traceData] = await Promise.all([
          getMessage(id),
          getTraces(id)
        ]);
        setData(msgData);
        setTraces(traceData);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load message details');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (error) {
    return (
      <div className="p-8 h-full flex flex-col items-center justify-center">
        <AlertCircle className="w-12 h-12 text-red-400 mb-4 opacity-50" />
        <p className="text-red-400 mb-6">{error}</p>
        <Link href="/messages" className="px-4 py-2 bg-zinc-900 border border-zinc-800 rounded-lg hover:bg-zinc-800 transition-colors">
          Back to Messages
        </Link>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="p-6 md:p-10 max-w-4xl mx-auto space-y-6">
        <div className="h-8 w-32 bg-zinc-900 animate-pulse rounded mb-8" />
        <LoadingSkeleton count={1} />
        <div className="h-8 w-48 bg-zinc-900 animate-pulse rounded mt-12 mb-6" />
        <LoadingSkeleton count={3} />
      </div>
    );
  }

  const decision = data.decision;
  const confidencePct = decision ? Math.round(decision.confidence * 100) : 0;
  const senderId = data.sender_user_id || data.business_id || data.user_id || 'Unknown';

  return (
    <div className="p-6 md:p-10 max-w-4xl mx-auto space-y-8">
      <Link href="/messages" className="inline-flex items-center text-sm text-zinc-400 hover:text-zinc-200 transition-colors group">
        <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" />
        Back to messages
      </Link>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Message Content */}
        <div className="md:col-span-2 space-y-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3 text-sm text-zinc-400">
                <div className="flex items-center">
                  <User className="w-4 h-4 mr-1.5" />
                  <span className="text-zinc-200">{senderId}</span>
                </div>
                {data.group_id && (
                  <div className="flex items-center">
                    <Users className="w-4 h-4 mr-1.5" />
                    <span>{data.group_id}</span>
                  </div>
                )}
              </div>
              {data.created_at && (
                <div className="flex items-center text-xs text-zinc-500">
                  <Calendar className="w-3.5 h-3.5 mr-1.5" />
                  {data.created_at}
                </div>
              )}
            </div>
            
            <div className="p-4 bg-zinc-950 rounded-xl border border-zinc-800/50">
              <p className="text-zinc-200 whitespace-pre-wrap leading-relaxed">
                {data.message_text ? stripEmojis(data.message_text) : '[Media Message]'}
              </p>
            </div>

            <div className="mt-4 flex gap-3 text-xs text-zinc-500">
              <span className="px-2 py-1 bg-zinc-800 rounded">{data.conversation_type}</span>
              {data.forwarded_count > 0 && <span className="px-2 py-1 bg-zinc-800 rounded">Forwarded ×{data.forwarded_count}</span>}
              {data.media_type && <span className="px-2 py-1 bg-zinc-800 rounded">{data.media_type}</span>}
            </div>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-zinc-100 mb-6 flex items-center">
              <FileText className="w-5 h-5 mr-2 text-violet-500" />
              Reasoning Timeline
            </h2>
            {traces.length > 0 ? (
              <div className="ml-2">
                {traces.map((trace, i) => (
                  <TimelineStep key={trace.id} trace={trace} index={i} />
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-zinc-500 bg-zinc-900/30 border border-zinc-800 border-dashed rounded-xl">
                No reasoning trace available for this message.
              </div>
            )}
          </div>
        </div>

        {/* Decision Sidebar */}
        <div className="space-y-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 sticky top-6">
            <h3 className="text-sm font-medium text-zinc-400 uppercase tracking-wider mb-4">Routing Decision</h3>
            
            {decision ? (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <span className="text-zinc-300">Action</span>
                  <ActionBadge action={decision.action} />
                </div>
                
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-zinc-300">Confidence</span>
                    <span className="text-zinc-100 font-medium">{confidencePct}%</span>
                  </div>
                  <div className="h-2 bg-zinc-950 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${confidencePct}%` }}
                      transition={{ duration: 0.8, delay: 0.3 }}
                      className={`h-full rounded-full ${
                        confidencePct > 80 ? 'bg-emerald-500' : confidencePct > 50 ? 'bg-amber-500' : 'bg-red-500'
                      }`} 
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <span className="text-sm text-zinc-300">Message Type</span>
                  <div className="inline-block px-2.5 py-1 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-300 capitalize">
                    {decision.message_type.replace('_', ' ')}
                  </div>
                </div>

                <div className="pt-4 border-t border-zinc-800/50">
                  <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider block mb-2">Reason</span>
                  <p className="text-sm text-zinc-300 leading-relaxed">
                    {decision.reason}
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-sm text-zinc-500 italic">
                Decision pending or not available.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
