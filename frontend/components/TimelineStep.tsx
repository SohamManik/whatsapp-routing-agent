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
      return `Action: ${parsedData.action || 'N/A'}\nReason: ${parsedData.reason || 'N/A'}`;
    }
    if (trace.step_type === 'tool_call') {
      return `Arguments: ${JSON.stringify(parsedData.args || {}, null, 2)}`;
    }
    if (trace.step_type === 'decision_finalized') {
      return `Type: ${parsedData.message_type || 'N/A'}\nReason: ${parsedData.reason || 'N/A'}\nConfidence: ${parsedData.confidence || 'N/A'}`;
    }
    return JSON.stringify(parsedData, null, 2);
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
        <pre className="text-zinc-400 text-sm whitespace-pre-wrap font-mono leading-relaxed">
          {getContent()}
        </pre>
      </div>
    </motion.div>
  );
}
