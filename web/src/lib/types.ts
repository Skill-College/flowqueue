export type Role = "user" | "admin";

export interface User {
  id: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Queue {
  id: string;
  name: string;
  owner_id: string | null;
  fifo_enabled: boolean;
  max_retries: number;
  retry_delay_seconds: number;
  retention_seconds: number;
  processed_retention_seconds: number;
  visibility_timeout_seconds: number;
  dlq_enabled: boolean;
  is_paused: boolean;
  metadata: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface QueueStats {
  queue_id: string;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  total_messages: number;
  consumer_count: number;
  max_consumer_lag_seconds: number | null;
}

export type ConsumerType = "http" | "webhook" | "sdk";

export type MatchMode = "any" | "all";

export interface RoutingRule {
  field: string;
  operator: string;
  value: unknown;
}

export interface Consumer {
  id: string;
  queue_id: string;
  name: string;
  type: ConsumerType;
  endpoint_url: string | null;
  routing_rules: RoutingRule[];
  match_mode: MatchMode;
  auto_complete: boolean;
  signing_secret: string | null;
  is_active: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Message {
  id: string;
  queue_id: string;
  payload: Record<string, unknown>;
  idempotency_key: string | null;
  sequence_num: number;
  published_at: string;
  scheduled_for: string | null;
  expires_at: string;
}

export type DeliveryStatus = "pending" | "processing" | "completed" | "failed" | "dead";

export interface Delivery {
  id: string;
  message_id: string;
  consumer_id: string;
  status: DeliveryStatus;
  attempt_count: number;
  visible_after: string;
  last_remark: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
}

export interface DeliveryLog {
  id: string;
  delivery_id: string;
  event_type: string;
  from_status: string | null;
  to_status: string | null;
  remark: string | null;
  metadata: Record<string, unknown>;
  context: Record<string, unknown>;
  created_at: string;
}

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiKeyCreated extends ApiKey {
  token: string;
}

export interface ReplayRequest {
  id: string;
  consumer_id: string;
  replay_type: string;
  status: string;
  messages_replayed: number;
  error_message: string | null;
  requested_at: string;
  completed_at: string | null;
}

export type FeedbackCategory = "bug" | "feature" | "general";

export interface Feedback {
  id: string;
  name: string | null;
  email: string;
  category: FeedbackCategory;
  message: string;
  user_id: string | null;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
