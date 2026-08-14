const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Matches the backend's SQLAlchemy Message model exactly
export interface Message {
  message_id: string;
  user_id: string;
  sender_user_id?: string;
  group_id?: string;
  business_id?: string;
  message_text?: string;
  media_type?: string;
  media_id?: string;
  conversation_type: string;
  forwarded_count: number;
  is_broadcast: number;
  created_at?: string;
}

// Matches the backend's RoutingDecision model
export interface Decision {
  id?: number;
  message_id: string;
  action: 'notify' | 'digest' | 'mute';
  message_type: string;
  reason: string;
  confidence: number;
  evidence_message_ids?: string;
}

// Matches the backend's ReasoningTrace model
export interface ReasoningTrace {
  id: number;
  message_id: string;
  step_order: number;
  step_type: string; // "gate_triggered", "tool_call", "decision_finalized"
  data: string; // JSON string
  created_at?: string;
}

export interface Stats {
  total: number;
  notify_count: number;
  digest_count: number;
  mute_count: number;
}

// Backend returns messages with decision nested inside
export interface MessageWithDecision extends Message {
  decision?: Decision;
}

export interface PaginatedMessages {
  messages: MessageWithDecision[];
  total: number;
  page: number;
  limit: number;
}

export async function getStats(): Promise<Stats> {
  const res = await fetch(`${API_BASE}/api/stats`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function getMessages(params: {
  page?: number;
  limit?: number;
  action?: string;
  search?: string;
  conversation_type?: string;
} = {}): Promise<PaginatedMessages> {
  const url = new URL(`${API_BASE}/api/messages`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      url.searchParams.append(key, String(value));
    }
  });
  const res = await fetch(url.toString(), { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch messages');
  return res.json();
}

export async function getMessage(id: string): Promise<MessageWithDecision & { sender_info?: Record<string, unknown> }> {
  const res = await fetch(`${API_BASE}/api/messages/${id}`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch message');
  return res.json();
}

export async function getTraces(id: string): Promise<ReasoningTrace[]> {
  const res = await fetch(`${API_BASE}/api/messages/${id}/traces`, { cache: 'no-store' });
  if (!res.ok) return [];
  return res.json();
}

export async function sendTestMessage(text: string): Promise<{ status: string; message_id: string }> {
  const msgId = `test_${Date.now()}`;
  const res = await fetch(`${API_BASE}/webhook/whatsapp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message_id: msgId,
      user_id: 'u1',
      sender_user_id: 'u2',
      group_id: null,
      business_id: null,
      message_text: text,
      media_type: null,
      media_id: null,
      conversation_type: 'personal',
      forwarded_count: 0,
      is_broadcast: 0,
      created_at: new Date().toISOString().replace('T', ' ').substring(0, 19),
    }),
  });
  if (!res.ok) throw new Error('Failed to send test message');
  return res.json();
}

export async function getDigestSummary(): Promise<{ summary: string }> {
  const res = await fetch(`${API_BASE}/api/digest/summary`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch digest summary');
  return res.json();
}
