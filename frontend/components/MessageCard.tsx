import Link from 'next/link';
import { MessageWithDecision } from '@/lib/api';
import { stripEmojis } from '@/lib/utils';
import { ActionBadge } from './ActionBadge';
import { MessageCircle, Shield } from 'lucide-react';

function formatTimeAgo(timestamp?: string) {
  if (!timestamp) return '';
  try {
    // If timestamp doesn't end with Z, append it to parse as UTC
    const utcTimestamp = timestamp.endsWith('Z') ? timestamp : `${timestamp}Z`;
    const date = new Date(utcTimestamp);
    const diff = Date.now() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  } catch {
    return timestamp;
  }
}

export function MessageCard({ message }: { message: MessageWithDecision }) {
  const isBusiness = message.conversation_type === 'business';
  const senderId = message.sender_user_id || message.business_id || message.user_id || 'Unknown';

  const displayName = senderId.startsWith('u_') ? `User ${senderId.replace('u_', '')}` : senderId;
  const init = displayName.slice(0, 2).toUpperCase();
  
  // Generate a deterministic color based on senderId
  const colors = ['bg-rose-500/20 text-rose-400', 'bg-blue-500/20 text-blue-400', 'bg-emerald-500/20 text-emerald-400', 'bg-amber-500/20 text-amber-400', 'bg-violet-500/20 text-violet-400'];
  const colorIndex = senderId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % colors.length;
  const avatarClass = colors[colorIndex];

  return (
    <Link href={`/messages/${message.message_id}`}>
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 hover:bg-zinc-800/50 hover:border-zinc-700 transition-all duration-200 cursor-pointer group">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center space-x-3">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center border border-zinc-700/50 flex-shrink-0 group-hover:border-violet-500/50 transition-colors ${avatarClass}`}>
              <span className="font-medium text-sm">
                {init}
              </span>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-medium text-zinc-200 text-sm">{displayName}</span>
                {isBusiness ? (
                  <Shield className="w-3.5 h-3.5 text-blue-400" />
                ) : null}
              </div>
              <div className="text-xs text-zinc-500 mt-0.5">
                {formatTimeAgo(message.created_at)}
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {message.decision?.message_type && (
              <span className="px-2 py-0.5 rounded text-[10px] uppercase font-semibold bg-zinc-800 text-zinc-400 border border-zinc-700/50 hidden sm:inline-block">
                {message.decision.message_type}
              </span>
            )}
            {message.decision ? (
              <ActionBadge action={message.decision.action} />
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium border bg-amber-500/10 text-amber-500 border-amber-500/20 uppercase tracking-wider flex items-center">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse mr-1.5" />
                Processing
              </span>
            )}
          </div>
        </div>
        <p className="text-zinc-300 text-sm line-clamp-2 leading-relaxed">
          {message.message_text ? stripEmojis(message.message_text) : '[Media Message]'}
        </p>
        <div className="mt-4 flex items-center justify-between border-t border-zinc-800/50 pt-3">
           <div className="flex items-center text-xs text-zinc-500">
             <MessageCircle className="w-3.5 h-3.5 mr-1.5" />
             {message.conversation_type || 'direct'}
           </div>
           {message.decision && (
             <div className="text-xs text-zinc-500 flex items-center">
                Conf: <span className="text-zinc-300 ml-1 font-medium">{Math.round((message.decision.confidence || 0) * 100)}%</span>
             </div>
           )}
        </div>
      </div>
    </Link>
  );
}
