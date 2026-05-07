/**
 * Workload model representing a workload entity in the firewall management system.
 *
 * @interface Workload
 * @description Represents a workload (e.g., Azure VM, App Service, Container) that is managed
 * by the firewall rule system. Each workload can have associated firewall rules for traffic control.
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

/**
 * Request payload for creating a new workload.
 *
 * @interface CreateWorkloadRequest
 * @description All fields except `name` and `environment` are optional. The `name` must be unique
 * across the system and `environment` determines the deployment tier (dev/staging/prod).
 */
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

/**
 * Request payload for updating an existing workload.
 *
 * @interface UpdateWorkloadRequest
 * @description All fields are optional. Only provided fields will be updated on the server.
 */
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