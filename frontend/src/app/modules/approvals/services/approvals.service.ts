import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, catchError, throwError } from 'rxjs';
import {
    ApprovalRequest,
    ApprovalListResponse,
    ApprovalFilter,
    ApproveRequest,
    RejectRequest,
    ApprovalComment
} from '../models/approval.model';

@Injectable({
    providedIn: 'root'
})
export class ApprovalsService {
    private baseUrl = '/api/v1/approvals';

    constructor(private http: HttpClient) { }

    /**
     * Get all approval requests with pagination and filtering
     */
    getApprovals(
        page: number = 1,
        pageSize: number = 20,
        filters?: ApprovalFilter
    ): Observable<ApprovalListResponse> {
        let params = new HttpParams()
            .set('page', page.toString())
            .set('page_size', pageSize.toString());

        if (filters) {
            if (filters.searchQuery) {
                params = params.set('search', filters.searchQuery);
            }
            if (filters.statusFilter) {
                params = params.set('status', filters.statusFilter);
            }
            if (filters.typeFilter) {
                params = params.set('type', filters.typeFilter);
            }
            if (filters.priorityFilter) {
                params = params.set('priority', filters.priorityFilter);
            }
        }

        return this.http.get<ApprovalListResponse>(this.baseUrl, { params });
    }

    /**
     * Get a single approval request by ID
     */
    getApproval(id: string): Observable<ApprovalRequest> {
        return this.http.get<ApprovalRequest>(`${this.baseUrl}/${id}`);
    }

    /**
     * Approve a request
     */
    approve(id: string, data?: ApproveRequest): Observable<ApprovalRequest> {
        return this.http.post<ApprovalRequest>(`${this.baseUrl}/${id}/approve`, data || {});
    }

    /**
     * Reject a request
     */
    reject(id: string, data?: RejectRequest): Observable<ApprovalRequest> {
        return this.http.post<ApprovalRequest>(`${this.baseUrl}/${id}/reject`, data || {});
    }

    /**
     * Add a comment to an approval request
     */
    addComment(approvalId: string, text: string): Observable<ApprovalComment> {
        return this.http.post<ApprovalComment>(`${this.baseUrl}/${approvalId}/comments`, {
            text
        });
    }

    /**
     * Get comments for an approval request
     */
    getComments(approvalId: string): Observable<ApprovalComment[]> {
        return this.http.get<ApprovalComment[]>(`${this.baseUrl}/${approvalId}/comments`);
    }

    /**
     * Delete a comment
     */
    deleteComment(approvalId: string, commentId: string): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/${approvalId}/comments/${commentId}`);
    }

    /**
     * Bulk approve approval requests
     */
    bulkApprove(ids: string[], comment?: string): Observable<BulkActionResult> {
        return this.http.post<BulkActionResult>(`${this.baseUrl}/bulk/approve`, {
            ids,
            comment
        });
    }

    /**
     * Bulk reject approval requests
     */
    bulkReject(ids: string[], reason: string, comment?: string): Observable<BulkActionResult> {
        return this.http.post<BulkActionResult>(`${this.baseUrl}/bulk/reject`, {
            ids,
            reason,
            comment
        });
    }

    /**
     * Check if an approval request is expired
     */
    isExpired(approval: ApprovalRequest): boolean {
        if (!approval.due_at) {
            return false;
        }
        const dueDate = new Date(approval.due_at);
        return new Date() > dueDate;
    }

    /**
     * Get formatted status for UI display
     */
    getStatusDisplay(status: string): { label: string; color: string; icon: string } {
        const statusMap: Record<string, { label: string; color: string; icon: string }> = {
            'pending': { label: 'Pending', color: '#ff9800', icon: 'schedule' },
            'approved': { label: 'Approved', color: '#4caf50', icon: 'check_circle' },
            'rejected': { label: 'Rejected', color: '#f44336', icon: 'cancel' },
            'expired': { label: 'Expired', color: '#9e9e9e', icon: 'hourglass_empty' },
            'timeout': { label: 'Timed Out', color: '#9e9e9e', icon: 'timer' }
        };
        return statusMap[status] || { label: status, color: '#9e9e9e', icon: 'help' };
    }

    /**
     * Get formatted priority for UI display
     */
    getPriorityDisplay(priority: string): { label: string; color: string; icon: string } {
        const priorityMap: Record<string, { label: string; color: string; icon: string }> = {
            'low': { label: 'Low', color: '#2196f3', icon: 'arrow_downward' },
            'medium': { label: 'Medium', color: '#ff9800', icon: 'remove' },
            'high': { label: 'High', color: '#f44336', icon: 'arrow_upward' },
            'urgent': { label: 'Urgent', color: '#d50000', icon: 'priority_high' }
        };
        return priorityMap[priority] || { label: priority, color: '#9e9e9e', icon: 'help' };
    }

    /**
     * Format a timestamp for display
     */
    formatDate(dateString: string): string {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }

    /**
     * Get relative time string
     */
    getRelativeTime(dateString: string): string {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMinutes = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMinutes < 1) return 'just now';
        if (diffMinutes < 60) return `${diffMinutes}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return `${diffDays}d ago`;
    }
}

export interface BulkActionResult {
    success: number;
    failed: number;
    errors: Array<{ id: string; error: string }>;
}