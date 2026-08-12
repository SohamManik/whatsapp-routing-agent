import React from 'react';
import { motion } from 'framer-motion';

export function StatCard({ label, value, icon: Icon, colorClass, delay = 0 }: { label: string; value: string | number; icon: any; colorClass: string; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 hover:border-zinc-700 transition-all duration-200"
    >
      <div className="flex justify-between items-start mb-4">
        <span className="text-zinc-400 font-medium text-sm">{label}</span>
        <div className={`p-2 rounded-lg bg-zinc-800/50 ${colorClass}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <div className="text-3xl font-semibold text-zinc-100">{value}</div>
    </motion.div>
  );
}
