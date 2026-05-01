/**
 * Audit Service
 *
 * Provides methods for retrieving, filtering, searching, and exporting audit logs.
 *
 * # Features
 *
 * - Retrieve paginated audit log entries
 * - Filter by date range, action, resource type, severity, user, and success status
 * - Search audit entries by query text
 * - Get audit entry details
 * - Export audit logs in multiple formats (CSV, JSON)
 * - Get audit summary statistics
 * - Format timestamps and display values
 *
 * # Usage
 *
 * ```typescript
 * import { AuditService } from './services/audit.service';
 *
 * constructor(private auditService: AuditService) { }
 *
 * // Get audit entries
 * this.auditService.getAuditLogs(filters).subscribe(entries => { ... });
 *
 * // Export audit logs
 * this.auditService.exportAuditLogs(params).subscribe(result => { ... });
 * ```
 */

import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpHandler } from '@angular/common/http';
import { Observable, catchError, throwError, of, lastValueFrom } from 'rxjs';
import {
    AuditEntry,
    AuditFilter,
    AuditListResponse,
    AuditExportFormat,
    AuditExportParams,
    AuditSummary,
    AuditAction,
    AuditResourceType,
    AuditSeverity
} from '../models/audit.model';

@Injectable({
    providedIn: 'root'
})
export class AuditService {
    private readonly baseUrl = '/api/v1/audit';

    constructor(private http: HttpClient) { }

    /**
     * Get paginated audit log entries with optional filters.
     *
     * @param page - Page number (1-based)
     * @param pageSize - Number of items per page
     * @param filters - Optional filter criteria
     * @returns Observable of paginated audit entries
     */
    getAuditLogs(
        page: number = 1,
        pageSize: number = 20,
        filters?: AuditFilter
    ): Observable<AuditListResponse> {
        let params = new HttpParams()
            .set('page', page.toString())
            .set('page_size', pageSize.toString());

        if (filters) {
            if (filters.searchQuery) {
                params = params.set('search', filters.searchQuery);
            }
            if (filters.dateFrom) {
                params = params.set('date_from', filters.dateFrom);
            }
            if (filters.dateTo) {
                params = params.set('date_to', filters.dateTo);
            }
            if (filters.actionFilter?.length) {
                params = params.set('actions', filters.actionFilter.join(','));
            }
            if (filters.resourceTypeFilter?.length) {
                params = params.set('resource_types', filters.resourceTypeFilter.join(','));
            }
            if (filters.severityFilter?.length) {
                params = params.set('severity', filters.severityFilter.join(','));
            }
            if (filters.userFilter?.length) {
                params = params.set('users', filters.userFilter.join(','));
            }
            if (filters.successFilter !== undefined) {
                params = params.set('success', filters.successFilter.toString());
            }
            if (filters.resourceIdFilter) {
                params = params.set('resource_id', filters.resourceIdFilter);
            }
        }

        return this.http.get<AuditListResponse>(this.baseUrl, { params });
    }

    /**
     * Get a single audit entry by ID.
     *
     * @param id - The audit entry ID
     * @returns Observable of the audit entry
     */
    getAuditEntry(id: string): Observable<AuditEntry> {
        return this.http.get<AuditEntry>(`${this.baseUrl}/${id}`);
    }

    /**
     * Search audit entries with a query string.
     *
     * @param query - Search query string
     * @param limit - Maximum number of results
     * @returns Observable of matching audit entries
     */
    searchAuditLogs(query: string, limit: number = 50): Observable<AuditEntry[]> {
        return this.http.get<AuditEntry[]>(`${this.baseUrl}/search`, {
            params: { query, limit: limit.toString() }
        });
    }

    /**
     * Get audit summary statistics.
     *
     * @param dateFrom - Start date for statistics (ISO 8601)
     * @param dateTo - End date for statistics (ISO 8601)
     * @returns Observable of audit summary
     */
    getAuditSummary(dateFrom?: string, dateTo?: string): Observable<AuditSummary> {
        let params = new HttpParams();
        if (dateFrom) params = params.set('date_from', dateFrom);
        if (dateTo) params = params.set('date_to', dateTo);

        return this.http.get<AuditSummary>(`${this.baseUrl}/summary`, { params });
    }

    /**
     * Export audit logs to the specified format.
     *
     * @param params - Export parameters including format and filters
     * @returns Observable of the exported data
     */
    exportAuditLogs(params: AuditExportParams): Observable<Blob> {
        const format = params.format || 'csv';
        const url = `${this.baseUrl}/export/${format}`;

        const queryParams: Record<string, string> = {};
        if (params.filters) {
            if (params.filters.searchQuery) queryParams.search = params.filters.searchQuery;
            if (params.filters.dateFrom) queryParams.date_from = params.filters.dateFrom;
            if (params.filters.dateTo) queryParams.date_to = params.filters.dateTo;
            if (params.filters.actionFilter?.length) queryParams.actions = params.filters.actionFilter.join(',');
            if (params.filters.resourceTypeFilter?.length) queryParams.resource_types = params.filters.resourceTypeFilter.join(',');
            if (params.filters.severityFilter?.length) queryParams.severity = params.filters.severityFilter.join(',');
        }

        if (params.dateFrom) queryParams.date_from = params.dateFrom;
        if (params.dateTo) queryParams.date_to = params.dateTo;
        if (params.title) queryParams.title = params.title;

        return this.http.get(url, {
            params: new HttpParams({ fromObject: queryParams }),
            responseType: 'blob'
        });
    }

    /**
     * Export audit logs as CSV format.
     *
     * @param filters - Filter criteria
     * @returns Observable of CSV blob
     */
    exportAsCsv(filters: AuditFilter): Observable<Blob> {
        return this.exportAuditLogs({
            format: 'csv',
            filters: filters,
            title: 'Audit Log Report'
        });
    }

    /**
     * Export audit logs as JSON format.
     *
     * @param filters - Filter criteria
     * @returns Observable of JSON blob
     */
    exportAsJson(filters: AuditFilter): Observable<Blob> {
        return this.exportAuditLogs({
            format: 'json',
            filters: filters,
            title: 'Audit Log Report'
        });
    }

    /**
     * Filter audit entries locally (for client-side filtering).
     *
     * @param entries - Array of audit entries to filter
     * @param filters - Filter criteria
     * @returns Filtered array of audit entries
     */
    filterAuditEntries(entries: AuditEntry[], filters: Partial<AuditFilter>): AuditEntry[] {
        let filtered = [...entries];

        // Filter by search query
        if (filters.searchQuery) {
            const query = filters.searchQuery.toLowerCase();
            filtered = filtered.filter(entry =>
                this.matchesSearch(entry, query)
            );
        }

        // Filter by date range
        if (filters.dateFrom || filters.dateTo) {
            filtered = filtered.filter(entry => {
                const entryDate = new Date(entry.timestamp).getTime();
                if (filters.dateFrom) {
                    const fromDate = new Date(filters.dateFrom!).getTime();
                    if (entryDate < fromDate) return false;
                }
                if (filters.dateTo) {
                    const toDate = new Date(filters.dateTo).getTime();
                    if (entryDate > toDate) return false;
                }
                return true;
            });
        }

        // Filter by action types
        if (filters.actionFilter?.length) {
            const actions = filters.actionFilter.map(a => a.toLowerCase());
            filtered = filtered.filter(entry =>
                actions.includes(entry.action.toLowerCase())
            );
        }

        // Filter by resource type
        if (filters.resourceTypeFilter?.length) {
            const resourceTypes = filters.resourceTypeFilter.map(r => r.toLowerCase());
            filtered = filtered.filter(entry =>
                resourceTypes.includes(entry.resourceType.toLowerCase())
            );
        }

        // Filter by severity
        if (filters.severityFilter?.length) {
            const severities = filters.severityFilter.map(s => s.toLowerCase());
            filtered = filtered.filter(entry =>
                severities.includes(entry.severity.toLowerCase())
            );
        }

        // Filter by user
        if (filters.userFilter?.length) {
            filtered = filtered.filter(entry =>
                filters.userFilter!.some(u =>
                    entry.user.toLowerCase().includes(u.toLowerCase()) ||
                    entry.displayName?.toLowerCase().includes(u.toLowerCase())
                )
            );
        }

        // Filter by success status
        if (filters.successFilter !== undefined) {
            filtered = filtered.filter(entry => entry.success === filters.successFilter);
        }

        // Filter by resource ID
        if (filters.resourceIdFilter) {
            filtered = filtered.filter(entry =>
                entry.resourceId === filters.resourceIdFilter
            );
        }

        return filtered;
    }

    /**
     * Check if an audit entry matches a search query.
     */
    private matchesSearch(entry: AuditEntry, query: string): boolean {
        const searchableFields = [
            entry.id,
            entry.description,
            entry.user,
            entry.displayName,
            entry.resourceType,
            entry.action,
            entry.ipAddress,
            entry.path
        ].filter(Boolean);

        return searchableFields.some(field =>
            field?.toLowerCase().includes(query)
        );
    }

    /**
     * Format audit severity for display.
     */
    getSeverityDisplay(severity: AuditSeverity): { label: string; color: string; icon: string; cssClass: string } {
        const severityMap: Record<string, { label: string; color: string; icon: string; cssClass: string }> = {
            'info': { label: 'Info', color: '#2196f3', icon: 'info', cssClass: 'audit-severity-info' },
            'warning': { label: 'Warning', color: '#ff9800', icon: 'warning', cssClass: 'audit-severity-warning' },
            'error': { label: 'Error', color: '#f44336', icon: 'error', cssClass: 'audit-severity-error' },
            'success': { label: 'Success', color: '#4caf50', icon: 'check_circle', cssClass: 'audit-severity-success' }
        };

        return severityMap[severity] || {
            label: severity,
            color: '#9e9e9e',
            icon: 'help',
            cssClass: 'audit-severity-default'
        };
    }

    /**
     * Format audit action for display.
     */
    getActionDisplay(action: AuditAction): string {
        const actionMap: Record<string, string> = {
            'CREATE': 'Created',
            'UPDATE': 'Updated',
            'DELETE': 'Deleted',
            'READ': 'Viewed',
            'LOGIN': 'Logged In',
            'LOGOUT': 'Logged Out',
            'APPROVE': 'Approved',
            'REJECT': 'Rejected',
            'IMPORT': 'Imported',
            'EXPORT': 'Exported',
            'CONFIGURE': 'Configured',
            'DEPLOY': 'Deployed',
            'TEST': 'Tested',
            'EXECUTE': 'Executed'
        };

        return actionMap[action] || action;
    }

    /**
     * Format resource type for display.
     */
    getResourceTypeDisplay(resourceType: AuditResourceType): string {
        const typeMap: Record<string, string> = {
            'FIREWALL_RULE': 'Firewall Rule',
            'ACCESS_RULE': 'Access Rule',
            'THRESHOLD': 'Threshold',
            'WORKSPACE': 'Workspace',
            'USER': 'User',
            'CONFIGURATION': 'Configuration',
            'DEPLOYMENT': 'Deployment',
            'APPROVAL': 'Approval',
            'RULE_EVALUATION': 'Rule Evaluation',
            'BATCH_OPERATION': 'Batch Operation',
            'WEBHOOK': 'Webhook',
            'NOTIFICATION': 'Notification'
        };

        return typeMap[resourceType] || resourceType;
    }

    /**
     * Format timestamp for display.
     */
    formatTimestamp(dateString: string): string {
        const date = new Date(dateString);
        return date.toLocaleString();
    }

    /**
     * Get relative time string for an audit entry.
     */
    getRelativeTime(dateString: string): string {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMinutes = Math.floor(Math.abs(diffMs) / 60000);
        const diffHours = Math.floor(Math.abs(diffMs) / 3600000);
        const diffDays = Math.floor(Math.abs(diffMs) / 86400000);

        if (diffMs < 0) return 'in the future';
        if (diffMinutes < 1) return 'just now';
        if (diffMinutes < 60) return `${diffMinutes}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
        return `${Math.floor(diffDays / 30)}m ago`;
    }

    /**
     * Format duration in milliseconds to human-readable string.
     */
    formatDuration(ms: number): string {
        if (ms < 1000) return `${ms}ms`;
        if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
        return `${(ms / 60000).toFixed(2)}min`;
    }

    /**
     * Get icon for a specific action type.
     */
    getActionIcon(action: AuditAction): string {
        const iconMap: Record<string, string> = {
            'CREATE': 'add',
            'UPDATE': 'edit',
            'DELETE': 'delete',
            'READ': 'visibility',
            'LOGIN': 'login',
            'LOGOUT': 'logout',
            'APPROVE': 'check',
            'REJECT': 'close',
            'IMPORT': 'file_download',
            'EXPORT': 'file_upload',
            'CONFIGURE': 'settings',
            'DEPLOY': 'publish_trail',
            'TEST': 'bug_report',
            'EXECUTE': 'play_arrow'
        };

        return iconMap[action] || 'article';
    }

    /**
     * Get icon for a specific resource type.
     */
    getResourceTypeIcon(resourceType: AuditResourceType): string {
        const iconMap: Record<string, string> = {
            'FIREWALL_RULE': 'network_internet',
            'ACCESS_RULE': 'key',
            'THRESHOLD': 'tune',
            'WORKSPACE': 'workspace_premium',
            'USER': 'person',
            'CONFIGURATION': 'build',
            'DEPLOYMENT': 'rocket_launch',
            'APPROVAL': 'done_all',
            'RULE_EVALUATION': 'gavel',
            'BATCH_OPERATION': 'hub',
            'WEBHOOK': 'hub',
            'NOTIFICATION': 'notifications'
        };

        return iconMap[resourceType] || 'description';
    }

    /**
     * Check if an audit entry is recent (within the last hour).
     */
    isRecent(entry: AuditEntry): boolean {
        const entryDate = new Date(entry.timestamp);
        const oneHourAgo = new Date(Date.now() - 3600000);
        return entryDate > oneHourAgo;
    }

    /**
     * Get unique users from audit entries.
     */
    getUniqueUsers(entries: AuditEntry[]): string[] {
        const users = new Set(entries.map(e => e.user));
        return Array.from(users).sort();
    }

    /**
     * Get unique resource types from audit entries.
     */
    getUniqueResourceTypes(entries: AuditEntry[]): AuditResourceType[] {
        const types = new Set(entries.map(e => e.resourceType));
        return Array.from(types);
    }

    /**
     * Get unique actions from audit entries.
     */
    getUniqueActions(entries: AuditEntry[]): AuditAction[] {
        const actions = new Set(entries.map(e => e.action));
        return Array.from(actions) as AuditAction[];
    }
}

export * from '../models/audit.model';