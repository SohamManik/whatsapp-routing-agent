"use client";

import { useEffect, useState, useRef } from 'react';
import { sendTestMessage } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Zap, Brain, CheckCircle, Activity, Send, AlertCircle } from 'lucide-react';

interface WSMessage {
  type: string;
  data: any;
}

export default function MonitorPage() {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<WSMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [testText, setTestText] = useState('Hello! Just testing the system.');
  const [wsUrl, setWsUrl] = useState('');

  useEffect(() => {
    let ws: WebSocket;
    
    // Fallback to determine WS URL
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const wsBase = API_URL.replace('http', 'ws');
    setWsUrl(`${wsBase}/ws/agent-stream`);

    function connect() {
      ws = new WebSocket(`${wsBase}/ws/agent-stream`);
      
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, 3000);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setEvents(prev => [data, ...prev].slice(0, 100)); // keep last 100
        } catch (e) {}
      };
      
      // Keep-alive ping to prevent Render from dropping idle connection
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);
      
      ws.addEventListener('close', () => clearInterval(pingInterval));
    }
    
    connect();
    
    return () => {
      if (ws) ws.close();
    };
  }, []);

  const handleSendTest = async () => {
    if (!testText.trim() || sending) return;
    setSending(true);
    try {
      await sendTestMessage(testText);
      setTestText('');
    } catch (e) {
      console.error(e);
    } finally {
      setSending(false);
    }
  };

  const getEventIcon = (type: string) => {
    if (type.includes('gate')) return <Shield className="w-5 h-5 text-blue-500" />;
    if (type.includes('tool')) return <Zap className="w-5 h-5 text-amber-500" />;
    if (type.includes('llm') || type.includes('reasoning')) return <Brain className="w-5 h-5 text-violet-500" />;
    if (type.includes('decision') || type.includes('finalized')) return <CheckCircle className="w-5 h-5 text-emerald-500" />;
    return <Activity className="w-5 h-5 text-zinc-500" />;
  };

  return (
    <div className="p-6 md:p-10 h-full flex flex-col">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 space-y-4 sm:space-y-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100 flex items-center">
            Live Monitor
            <div className={`ml-3 flex items-center px-2 py-1 rounded-full border text-[10px] uppercase tracking-wider font-semibold ${
              connected ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' : 'bg-red-500/10 text-red-500 border-red-500/20'
            }`}>
              <div className={`w-1.5 h-1.5 rounded-full mr-1.5 ${connected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
              {connected ? 'Live' : 'Disconnected'}
            </div>
          </h1>
          <p className="text-sm text-zinc-500 mt-1">Watch the AI process incoming messages live</p>
        </div>

        <div className="flex items-center space-x-2 bg-zinc-900 p-1.5 rounded-lg border border-zinc-800 w-full sm:w-auto">
          <input
            type="text"
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            placeholder="Type a test message..."
            className="bg-transparent border-none focus:ring-0 text-sm px-3 py-1 text-zinc-200 placeholder-zinc-500 w-full sm:w-64"
            onKeyDown={(e) => e.key === 'Enter' && handleSendTest()}
          />
          <button
            onClick={handleSendTest}
            disabled={sending || !testText.trim()}
            className="p-1.5 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:hover:bg-violet-600 rounded text-white transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden bg-zinc-900 border border-zinc-800 rounded-2xl flex flex-col">
        {!connected && events.length === 0 && (
           <div className="bg-amber-500/10 text-amber-500 p-3 text-sm flex items-center justify-center border-b border-amber-500/20">
             <AlertCircle className="w-4 h-4 mr-2" />
             Trying to connect to WebSocket at {wsUrl}...
           </div>
        )}
        
        <div className="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-sm">
          <AnimatePresence initial={false}>
            {events.length === 0 && connected && (
              <motion.div 
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="h-full flex items-center justify-center text-zinc-600 italic"
              >
                Waiting for incoming events...
              </motion.div>
            )}
            
            {events.map((ev, i) => (
              <motion.div
                key={`${ev.type}-${i}`}
                initial={{ opacity: 0, y: -20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                layout
                className="bg-zinc-950 border border-zinc-800/80 rounded-lg p-4 flex items-start space-x-4 shadow-sm"
              >
                <div className="mt-0.5 bg-zinc-900 p-2 rounded-md border border-zinc-800">
                  {getEventIcon(ev.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-zinc-300 font-semibold">{ev.type}</span>
                    <span className="text-xs text-zinc-600">{new Date().toLocaleTimeString()}</span>
                  </div>
                  <pre className="text-zinc-400 text-xs overflow-x-auto whitespace-pre-wrap bg-zinc-900/50 p-2 rounded border border-zinc-800/50">
                    {JSON.stringify(ev.data, null, 2)}
                  </pre>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
