// Mirrors backend/app/schemas.py — Waiting List schemas.
// Keep in sync whenever the API response shape changes.

export type WaitingListEntryStatus = 'pending' | 'notified' | 'cancelled';

export interface WaitingListEntry {
  id: number;
  product_id: number;
  user_id: number;
  joined_at: string;       // ISO datetime string
  notified_at: string | null;
  status: WaitingListEntryStatus;
  queue_position: number | null;
}

export interface WaitingListStatus {
  on_list: boolean;
  entry: WaitingListEntry | null;
  pending_count: number;
}

/** Request body when joining the waiting list */
export interface WaitingListJoinRequest {
  user_email?: string;
}
