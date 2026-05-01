export interface ApprovalRequest {
    id: string;
    rule_name: string;
    rule_id: string;
    requestor: string;
    request_type: 'create' | 'update' | 'delete' | 'enable' | 'disable';
    status: 'pending' | 'approved' | 'rejected' | 'expired' | 'timeout';
    description?: string;
    requested_at: string;
    due_at?: string;
    approved_by?: string;
    approved_at?: string;
    rejection_reason?: string;
    comments: ApprovalComment[];
    metadata: ApprovalMetadata;
    priority: 'low' | 'medium' | 'high' | 'urgent';
}

export interface ApprovalComment {
    id: string;
    author: string;
    text: string;
    created_at: string;
}

export interface ApprovalMetadata {
    rule_changes: RuleChangeDetails;
    workspace_id?: string;
    azure_resource_id?: string;
    source_ip?: string;
}

export interface RuleChangeDetails {
    field: string;
    old_value?: any;
    new_value?: any;
}

export interface ApprovalFilter {
    searchQuery: string;
    statusFilter: string;
    typeFilter: string;
    priorityFilter: string;
}

export interface ApprovalListResponse {
    items: ApprovalRequest[];
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
}

export interface ApproveRequest {
    comment?: string;
    metadata?: Record<string, any>;
}

export interface RejectRequest {
    reason: string;
    comment?: string;
    metadata?: Record<string, any>;
}