import React from 'react';
import { motion } from 'framer-motion';
import { Shield, Zap, Brain, CheckCircle } from 'lucide-react';
import { ReasoningTrace } from '@/lib/api';

export function TimelineStep({ trace, index }: { trace: ReasoningTrace; index: number }) {
  // Parse the JSON data string from the backend
  let parsedData: Record<string, unknown> = {};
  try {
    parsedData = typeof trace.data === 'string' ? JSON.parse(trace.data) : trace.data;
  } catch {
    parsedData = { raw: trace.data };
  }

  const getIcon = () => {
    switch (trace.step_type) {
      case 'gate_triggered': return <Shield className="w-5 h-5 text-blue-500" />;
      case 'tool_call': return <Zap className="w-5 h-5 text-amber-500" />;
      case 'decision_finalized': return <CheckCircle className="w-5 h-5 text-emerald-500" />;
      default: return <Brain className="w-5 h-5 text-violet-500" />;
    }
  };

  const getBorderColor = () => {
    switch (trace.step_type) {
      case 'gate_triggered': return 'border-blue-500/20';
      case 'tool_call': return 'border-amber-500/20';
      case 'decision_finalized': return 'border-emerald-500/20';
      default: return 'border-violet-500/20';
    }
  };

  const getLabel = () => {
    switch (trace.step_type) {
      case 'gate_triggered': return `Safety Gate: ${parsedData.gate || 'Unknown'}`;
      case 'tool_call': return `Tool: ${parsedData.tool || 'Unknown'}`;
      case 'decision_finalized': return `Decision: ${(parsedData.action as string || '').toUpperCase()}`;
      default: return trace.step_type.replace('_', ' ');
    }
  };

  const getContent = () => {
    if (trace.step_type === 'gate_triggered') {
      return (
        <div className="space-y-1">
          <div className="flex text-zinc-300"><span className="w-24 text-zinc-500">Action:</span> <span className="font-medium text-blue-400 capitalize">{String(parsedData.action || 'N/A')}</span></div>
          <div className="flex text-zinc-300"><span className="w-24 text-zinc-500">Reason:</span> <span>{String(parsedData.reason || 'N/A')}</span></div>
        </div>
      );
    }
    if (trace.step_type === 'tool_call') {
      const args = parsedData.args as Record<string, unknown>;
      return (
        <div className="space-y-1">
          <div className="text-zinc-500 mb-1">Arguments:</div>
          {Object.entries(args || {}).map(([key, val]) => (
            <div key={key} className="flex pl-2 border-l border-zinc-700/50">
              <span className="text-zinc-400 mr-2">{key}:</span>
              <span className="text-amber-400/90 break-all">{String(val)}</span>
            </div>
          ))}
        </div>
      );
    }
    if (trace.step_type === 'decision_finalized') {
      return (
        <div className="space-y-1">
          <div className="flex text-zinc-300"><span className="w-24 text-zinc-500">Type:</span> <span className="capitalize">{String(parsedData.message_type || 'N/A').replace('_', ' ')}</span></div>
          <div className="flex text-zinc-300"><span className="w-24 text-zinc-500">Confidence:</span> <span className="text-emerald-400 font-medium">{Math.round(Number(parsedData.confidence || 0) * 100)}%</span></div>
          <div className="flex text-zinc-300 mt-2"><span className="w-24 text-zinc-500">Reasoning:</span> <span className="italic">"{String(parsedData.reason || 'N/A')}"</span></div>
        </div>
      );
    }
    
    // Fallback for LLM reasoning text
    if (typeof trace.data === 'string' && trace.data.trim().length > 0 && trace.data[0] !== '{') {
      return <div className="text-zinc-300 leading-relaxed">{trace.data}</div>;
    }
    
    return <div className="text-zinc-500 italic">Processing completed.</div>;
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1, duration: 0.3 }}
      className="relative pl-8 pb-8 group last:pb-0"
    >
      <div className="absolute left-0 top-1 bottom-0 w-px bg-zinc-800 group-last:bg-transparent" />
      <div className="absolute left-[-11px] top-1 w-6 h-6 rounded-full bg-zinc-950 border border-zinc-800 flex items-center justify-center">
        {getIcon()}
      </div>
      <div className={`bg-zinc-900/50 border ${getBorderColor()} rounded-xl p-4 transition-all hover:bg-zinc-900`}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-zinc-200">{getLabel()}</span>
          {trace.created_at && (
            <span className="text-xs text-zinc-500">
              {new Date(trace.created_at).toLocaleTimeString()}
            </span>
          )}
        </div>
        <div className="text-sm">
          {getContent()}
        </div>
      </div>
    </motion.div>
  );
}
