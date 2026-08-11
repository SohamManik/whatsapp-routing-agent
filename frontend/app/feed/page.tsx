"use client";

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Shield, Bot, Zap, MessageSquare } from 'lucide-react';

interface Decision {
  action: string;
  message_type: string;
  reason: string;
  confidence: number;
  evidence_message_ids: string;
}

interface Message {
  message_id: string;
  sender_user_id?: string;
  created_at?: string;
  message_text?: string;
}

interface MessageFeedItem {
  message: Message;
  decision?: Decision | null;
}

interface AgentLogEvent {
  type: string;
  data: {
    tool?: string;
    args?: any;
    gate?: string;
    action?: string;
    reason?: string;
    message_type?: string;
  };
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

export default function Feed() {
  const [messages, setMessages] = useState<MessageFeedItem[]>([]);
  const [selectedMessage, setSelectedMessage] = useState<MessageFeedItem | null>(null);
  const [agentLogs, setAgentLogs] = useState<AgentLogEvent[]>([]);

  useEffect(() => {
    // Fetch initial messages
    fetch(`${API_BASE_URL}/api/messages`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setMessages(data);
        }
      })
      .catch(console.error);

    // Connect WebSocket
    const ws = new WebSocket(`${WS_BASE_URL}/ws/agent-stream`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setAgentLogs(prev => [...prev, data]);
        
        if (data.type === 'decision_finalized') {
           // Refresh messages to get the new decision
           fetch(`${API_BASE_URL}/api/messages`)
            .then(res => res.json())
            .then(d => {
              if (Array.isArray(d)) setMessages(d);
            });
        }
      } catch (e) {
        console.error(e);
      }
    };
    return () => ws.close();
  }, []);

  return (
    <div className="flex h-screen bg-[#0f1115] text-white overflow-hidden font-sans">
      {/* Left Panel: Message Feed */}
      <div className="w-[45%] border-r border-white/10 p-8 overflow-y-auto custom-scrollbar">
        <h2 className="text-3xl font-bold mb-8 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-400 flex items-center gap-3">
          <MessageSquare size={28} className="text-blue-400" />
          Incoming Feed
        </h2>
        <div className="space-y-4">
          {messages.map((msg, idx) => (
            <motion.div 
              key={msg.message?.message_id || idx} 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className={`glass p-5 cursor-pointer transition-all duration-300 ${selectedMessage?.message?.message_id === msg.message?.message_id ? 'ring-2 ring-blue-500 bg-white/10 scale-[1.02]' : 'hover:bg-white/10'}`}
              onClick={() => {
                setSelectedMessage(msg);
                setAgentLogs([]); // Clear logs when switching
              }}
            >
              <div className="flex justify-between items-start mb-3">
                <span className="font-bold text-gray-200">{msg.message?.sender_user_id || 'Unknown Sender'}</span>
                <span className="text-xs text-gray-500 font-mono">{msg.message?.created_at?.split(' ')[1] || 'Just now'}</span>
              </div>
              <p className="text-gray-300 line-clamp-2">{msg.message?.message_text || '[Media Message]'}</p>
              
              {msg.decision && (
                <div className="mt-4 flex gap-2">
                  <span className={`px-3 py-1 rounded text-xs font-bold tracking-wider ${
                    msg.decision.action === 'notify' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                    msg.decision.action === 'mute' ? 'bg-gray-700/50 text-gray-400 border border-gray-600/50' :
                    'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  }`}>
                    {msg.decision.action.toUpperCase()}
                  </span>
                  <span className="px-3 py-1 bg-white/5 rounded text-xs border border-white/10 text-gray-400">
                    {msg.decision.message_type}
                  </span>
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </div>

      {/* Right Panel: Agent Inspector */}
      <div className="w-[55%] p-8 overflow-y-auto bg-gradient-to-br from-[#1a1c23] to-[#0f1115] relative">
        <div className="absolute top-0 right-0 w-[50%] h-[50%] bg-purple-600/10 blur-[100px] pointer-events-none" />
        
        <h2 className="text-3xl font-bold mb-8 flex items-center gap-3 relative z-10">
          <Bot className="text-purple-400" size={32} />
          Agent Inspector
        </h2>
        
        {!selectedMessage ? (
          <div className="h-[70%] flex items-center justify-center text-gray-500 font-medium text-lg relative z-10">
            Select a message to view the agent's thought process.
          </div>
        ) : (
          <div className="space-y-8 relative z-10">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="glass p-6 border-purple-500/30 shadow-[0_0_30px_rgba(168,85,247,0.1)]"
            >
              <h3 className="text-sm uppercase tracking-widest font-semibold mb-3 text-purple-300">Message Context</h3>
              <p className="text-gray-200 text-lg leading-relaxed">{selectedMessage.message?.message_text}</p>
            </motion.div>
            
            <h3 className="text-xl font-bold text-gray-300 mt-10 mb-6 flex items-center gap-2">
              <Zap className="text-yellow-400" size={20} />
              Reasoning Timeline
            </h3>
            
            <div className="relative border-l-2 border-white/10 ml-5 space-y-10 pb-10">
              {agentLogs.length === 0 && selectedMessage.decision && (
                 <div className="ml-8 glass p-5 border-white/5 bg-white/5">
                   <div className="text-gray-400 italic mb-3 flex items-center gap-2">
                     Historical decision (Live stream unavailable)
                   </div>
                   <div className="text-md text-gray-300 leading-relaxed"><span className="text-gray-500 font-semibold mr-2">Reason:</span>{selectedMessage.decision.reason}</div>
                 </div>
              )}
              
              <AnimatePresence>
                {agentLogs.map((log, i) => (
                  <motion.div 
                    key={i}
                    initial={{ opacity: 0, x: -30 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="relative ml-8"
                  >
                    {/* Timeline dot */}
                    <div className="absolute -left-[41px] top-4 w-4 h-4 rounded-full bg-[#1a1c23] border-2 border-purple-500 z-10 flex items-center justify-center">
                      <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
                    </div>
                    
                    <div className="glass p-6 hover:bg-white/10 transition-colors">
                      {log.type === 'tool_call' && (
                        <div>
                          <div className="flex items-center gap-2 text-blue-400 font-bold mb-3 text-lg">
                            <Zap size={20} /> Tool Invoked: {log.data.tool}
                          </div>
                          <pre className="text-sm bg-black/40 p-4 rounded-lg text-gray-300 overflow-x-auto border border-white/5">
                            {JSON.stringify(log.data.args, null, 2)}
                          </pre>
                        </div>
                      )}
                      
                      {log.type === 'gate_triggered' && (
                        <div>
                          <div className="flex items-center gap-2 text-yellow-400 font-bold mb-3 text-lg">
                            <Shield size={20} /> Safety Gate Triggered
                          </div>
                          <div className="bg-yellow-500/10 p-4 rounded-lg border border-yellow-500/20">
                            <p className="text-sm text-yellow-200/80 mb-2 font-mono">ACTION: {log.data.action} | TYPE: {log.data.gate}</p>
                            <p className="text-md text-yellow-100">{log.data.reason}</p>
                          </div>
                        </div>
                      )}
                      
                      {log.type === 'decision_finalized' && (
                        <div>
                          <div className="flex items-center gap-2 text-green-400 font-bold mb-4 text-lg">
                            <CheckCircle2 size={20} /> Decision Reached
                          </div>
                          <div className="flex gap-3 mb-4">
                            <span className={`px-4 py-1.5 rounded font-bold tracking-wider ${
                                log.data.action === 'notify' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                                log.data.action === 'mute' ? 'bg-gray-700/50 text-gray-400 border border-gray-600/50' :
                                'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                              }`}>
                              {log.data.action?.toUpperCase()}
                            </span>
                            <span className="px-4 py-1.5 bg-white/5 rounded border border-white/10 text-gray-300 font-medium tracking-wide">
                              {log.data.message_type}
                            </span>
                          </div>
                          <p className="text-gray-300 bg-white/5 p-4 rounded-lg leading-relaxed">{log.data.reason}</p>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
