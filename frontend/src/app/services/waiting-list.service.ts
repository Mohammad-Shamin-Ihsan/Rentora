import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  WaitingListEntry,
  WaitingListJoinRequest,
  WaitingListStatus,
} from '../models/waiting-list.model';

/**
 * Service for Module 2 / Part 4 — Waiting List Management.
 *
 * Connects to flat endpoints:
 *   POST   /waiting-list/join?product_id={id}          → join
 *   GET    /waiting-list/position?product_id={id}      → status / position
 *   DELETE /waiting-list/cancel?product_id={id}        → cancel / leave
 */
@Injectable({ providedIn: 'root' })
export class WaitingListService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(private http: HttpClient) {}

  /** Check if the current user is on the waiting list for a product and their position. */
  getStatus(productId: number, userId: number): Observable<WaitingListStatus> {
    return this.http.get<WaitingListStatus>(
      `${this.baseUrl}/waiting-list/position?product_id=${productId}`,
      { headers: this.authHeaders(userId) }
    );
  }

  /** Join the waiting list. */
  join(
    productId: number,
    userId: number,
    payload: WaitingListJoinRequest = {}
  ): Observable<WaitingListEntry> {
    return this.http.post<WaitingListEntry>(
      `${this.baseUrl}/waiting-list/join?product_id=${productId}`,
      payload,
      { headers: this.authHeaders(userId) }
    );
  }

  /** Leave / cancel from the waiting list. */
  cancel(productId: number, userId: number): Observable<{ message: string; id: number }> {
    return this.http.delete<{ message: string; id: number }>(
      `${this.baseUrl}/waiting-list/cancel?product_id=${productId}`,
      { headers: this.authHeaders(userId) }
    );
  }

  /** Admin/staff: list all pending entries for a product. */
  listAll(productId: number): Observable<WaitingListEntry[]> {
    return this.http.get<WaitingListEntry[]>(
      `${this.baseUrl}/products/${productId}/waiting-list`
    );
  }

  /**
   * Admin/staff: trigger notifications to all waiting users when a product
   * becomes available.
   */
  notifyAll(productId: number): Observable<{ notified: number; message: string }> {
    return this.http.post<{ notified: number; message: string }>(
      `${this.baseUrl}/products/${productId}/waiting-list/notify`,
      {}
    );
  }

  private authHeaders(userId: number): HttpHeaders {
    return new HttpHeaders({ 'X-Debug-User-Id': String(userId) });
  }
}
