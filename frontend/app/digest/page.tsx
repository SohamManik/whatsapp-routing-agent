"use client";

import { useEffect, useState } from 'react';
import { getDigestSummary } from '@/lib/api';
import { Sparkles, RefreshCw, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';

export default function DigestPage() {
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDigest = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDigestSummary();
      setSummary(res.summary);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load summary');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDigest();
  }, []);

  return (
    <div className="p-6 md:p-10 max-w-4xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100 flex items-center">
            <Sparkles className="w-6 h-6 mr-3 text-blue-400" />
            Digest Summary
          </h1>
          <p className="text-sm text-zinc-500 mt-1">AI-generated summary of your low-priority messages.</p>
        </div>
        <button 
          onClick={fetchDigest}
          disabled={loading}
          className="flex items-center px-4 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-sm text-zinc-300 hover:bg-zinc-800 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 min-h-[300px] shadow-lg">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full min-h-[250px] text-zinc-500 space-y-4">
            <div className="w-8 h-8 border-2 border-zinc-600 border-t-blue-500 rounded-full animate-spin" />
            <p>Analyzing and summarizing messages...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full min-h-[250px] text-red-400 space-y-4">
            <AlertCircle className="w-8 h-8 opacity-50" />
            <p>{error}</p>
          </div>
        ) : (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="prose prose-invert prose-blue max-w-none"
          >
            <div className="text-zinc-300 leading-relaxed whitespace-pre-wrap text-base">
              {summary}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
