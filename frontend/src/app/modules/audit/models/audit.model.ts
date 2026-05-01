/**
 * Audit Model
 *
 * Defines interfaces and types for audit log entries, filters, and responses.
 *
 * # Types
 *
 * - `AuditAction`: Enum of possible audit actions (CREATE, UPDATE, DELETE, READ, etc.)
 * - `AuditResourceType`: Types of resources that can be audited
 * - `AuditSeverity`: Severity level of the audit entry
 * - `AuditEntry`: Main audit log entry interface
 * - `AuditFilter`: Filter options for searching audit logs
 * - `AuditListResponse`: Paginated response structure
 */

/**
 * Possible audit actions that can be logged.
 */
export type AuditAction =
    | 'CREATE'
    | 'UPDATE'
    | 'DELETE'
    | 'READ'
    | 'LOGIN'
    | 'LOGOUT'
    | 'APPROVE'
    | 'REJECT'
    | 'IMPORT'
    | 'EXPORT'
    | 'CONFIGURE'
    | 'DEPLOY'
    | 'TEST'
    | 'EXECUTE';

/**
 * Types of resources that can be audited.
 */
export type AuditResourceType =
    | 'FIREWALL_RULE'
    | 'ACCESS_RULE'
    | 'THRESHOLD'
    | 'WORKSPACE'
    | 'USER'
    | 'CONFIGURATION'
    | 'DEPLOYMENT'
    | 'APPROVAL'
    | 'RULE_EVALUATION'
    | 'BATCH_OPERATION'
    | 'WEBHOOK'
    | 'NOTIFICATION';

/**
 * Severity levels for audit entries.
 */
export type AuditSeverity = 'info' | 'warning' | 'error' | 'success';

/**
 * Audit log entry - represents a single auditable event.
 */
export interface AuditEntry {
    /** Unique identifier for this audit entry. */
    id: string;

    /** Timestamp when the event occurred (ISO 8601 format). */
    timestamp: string;

    /** User who performed the action. */
    user: string;

    /** User's display name or email. */
    displayName?: string;

    /** IP address from which the action was performed. */
    ipAddress?: string;

    /** HTTP method used (GET, POST, PUT, DELETE, etc.). */
    httpMethod?: string;

    /** Request path or endpoint. */
    path?: string;

    /** HTTP status code returned. */
    statusCode?: number;

    /** Action that was performed. */
    action: AuditAction;

    /** Type of resource affected. */
    resourceType: AuditResourceType;

    /** Unique identifier of the resource. */
    resourceId?: string;

    /** Human-readable description of the event. */
    description: string;

    /** Additional details about the event. */
    details?: AuditDetails;

    /** Severity level of the event. */
    severity: AuditSeverity;

    /** Whether the operation was successful. */
    success: boolean;

    /** Duration of the operation in milliseconds. */
    durationMs?: number;

    /** Request ID for correlation. */
    requestId?: string;

    /** Additional metadata. */
    metadata?: Record<string, any>;

    /** Change details for UPDATE/CREATE/DELETE actions. */
    changes?: AuditChange[];

    /** Result of the operation. */
    result?: AuditResult;
}

/**
 * Details for a specific audit event.
 */
export interface AuditDetails {
    /** Request body or parameters. */
    requestBody?: Record<string, any>;

    /** Response body or result. */
    responseBody?: Record<string, any>;

    /** Query parameters. */
    queryParams?: Record<string, string>;

    /** Headers from the request. */
    headers?: Record<string, string>;

    /** Browser or client information. */
    userAgent?: string;

    /** Additional contextual information. */
    context?: Record<string, any>;
}

/**
 * Represents a single change in an audit entry (for UPDATE operations).
 */
export interface AuditChange {
    /** Field that was changed. */
    field: string;

    /** Previous value before the change. */
    oldValue?: any;

    /** New value after the change. */
    newValue?: any;

    /** Description of the change. */
    description?: string;
}

/**
 * Result of an audit operation.
 */
export interface AuditResult {
    /** Whether the operation succeeded. */
    success: boolean;

    /** Error message if the operation failed. */
    errorMessage?: string;

    /** Number of items affected. */
    affectedCount?: number;

    /** ID of the operation for tracing. */
    operationId?: string;
}

/**
 * Filter options for searching audit logs.
 */
export interface AuditFilter {
    /** Text to search in description, user, resource, etc. */
    searchQuery: string;

    /** Filter by date range start (ISO 8601). */
    dateFrom?: string;

    /** Filter by date range end (ISO 8601). */
    dateTo?: string;

    /** Filter by specific action types. */
    actionFilter?: AuditAction[];

    /** Filter by resource types. */
    resourceTypeFilter?: AuditResourceType[];

    /** Filter by severity levels. */
    severityFilter?: AuditSeverity[];

    /** Filter by user(s). */
    userFilter?: string[];

    /** Filter by success/failure. */
    successFilter?: boolean;

    /** Filter by specific resource ID. */
    resourceIdFilter?: string;

    /** Page number for pagination (1-based). */
    page?: number;

    /** Page size for pagination. */
    pageSize?: number;
}

/**
 * Paginated response for audit log entries.
 */
export interface AuditListResponse {
    /** Array of audit entries. */
    items: AuditEntry[];

    /** Total number of audit entries matching the filter. */
    total: number;

    /** Current page number. */
    page: number;

    /** Number of items per page. */
    pageSize: number;

    /** Total number of pages. */
    totalPages: number;
}

/**
 * Export format for audit logs.
 */
export type AuditExportFormat = 'csv' | 'json' | 'pdf' | 'xml';

/**
 * Parameters for exporting audit logs.
 */
export interface AuditExportParams {
    /** The export format. */
    format: AuditExportFormat;

    /** Filters applied to the export. */
    filters: AuditFilter;

    /** Title for the export document. */
    title?: string;

    /** Date range start. */
    dateFrom?: string;

    /** Date range end. */
    dateTo?: string;
}

/**
 * Summary statistics for audit data.
 */
export interface AuditSummary {
    /** Total count of audit entries. */
    totalCount: number;

    /** Count by action type. */
    byAction: Record<string, number>;

    /** Count by resource type. */
    byResourceType: Record<string, number>;

    /** Count by severity. */
    bySeverity: Record<string, number>;

    /** Count by success status. */
    bySuccess: Record<string, number>;

    /** Count by user. */
    byUser: Record<string, number>;

    /** Entries per day for the last 7 days. */
    recentActivity: Array<{ date: string; count: number }>;

    /** Top users performing actions. */
    topUsers: Array<{ user: string; count: number }>;
}