/**
 * Workload model representing a workload entity in the firewall management system.
 */
export interface Workload {
    id: string;
    name: string;
    description?: string;
    workload_type: string;
    resource_group?: string;
    azure_resource_id?: string;
    environment: string;
    status: string;
    owner?: string;
    contact_email?: string;
    tags?: Record<string, string>;
    created_at: string;
    updated_at: string;
    rule_count?: number;
}

export interface CreateWorkloadRequest {
    name: string;
    description?: string;
    workload_type: string;
    resource_group?: string;
    azure_resource_id?: string;
    environment: string;
    owner?: string;
    contact_email?: string;
    tags?: Record<string, string>;
}

export interface UpdateWorkloadRequest {
    name?: string;
    description?: string;
    workload_type?: string;
    resource_group?: string;
    azure_resource_id?: string;
    environment?: string;
    owner?: string;
    contact_email?: string;
    tags?: Record<string, string>;
}

/**
 * Workload status enum for type-safe status management.
 */
export enum WorkloadStatus {
    ACTIVE = 'active',
    PENDING = 'pending',
    INACTIVE = 'inactive',
    DELETED = 'deleted'
}

/**
 * Workload type enum for type-safe type management.
 */
export enum WorkloadType {
    VM = 'vm',
    APP_SERVICE = 'app_service',
    CONTAINER = 'container',
    FUNCTION = 'function',
    STORAGE = 'storage',
    DATABASE = 'database',
    OTHER = 'other'
}