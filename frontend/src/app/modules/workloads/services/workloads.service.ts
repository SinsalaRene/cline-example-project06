/**
 * WorkloadsService - Provides data access for workload entities via the backend API.
 *
 * @class WorkloadsService
 * @description Handles all HTTP communication with the workload management API,
 * including CRUD operations, rule associations, and bulk operations.
 *
 * @example
 * ```typescript
 * constructor(private workloadsService: WorkloadsService) {}
 *
 * loadWorkloads() {
 *   this.workloadsService.getWorkloads().subscribe(workloads => {
 *     console.log(workloads);
 *   });
 * }
 * ```
 */
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, catchError, map, of, forkJoin } from 'rxjs';
import { Workload, CreateWorkloadRequest, UpdateWorkloadRequest } from '../models/workload.model';

/**
 * Paginated response wrapper for list endpoints.
 *
 * @interface PaginatedResponse
 * @description Used by the backend to return paginated workload lists with metadata
 * about total count, page number, and page size.
 */
export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
}

/**
 * Represents an association between a workload and a firewall rule.
 *
 * @interface WorkloadRuleAssociation
 * @description Defines how a firewall rule is linked to a workload, either as 'include'
 * (rule applies to workload traffic) or 'exclude' (rule is skipped for workload traffic).
 */
export interface WorkloadRuleAssociation {
    workload_id: string;
    rule_id: string;
    association_type: 'include' | 'exclude';
    created_at: string;
}

/**
 * Result of a bulk delete operation across multiple workloads.
 *
 * @interface BulkOperationResult
 * @description Contains counts of successful and failed deletions along with
 * detailed error information for each failed operation.
 */
export interface BulkOperationResult {
    success: number;
    failed: number;
    errors: Array<{ id: string; error: string }>;
}

/** API base URL for workload endpoints. */
const WORKLOADS_API_URL = '/api/v1/workloads';

/**
 * WorkloadsService - Provides data access for workload entities via the backend API.
 */
@Injectable({
    providedIn: 'root'
})
export class WorkloadsService {

    /**
     * Creates an instance of WorkloadsService.
     * @param http - Angular's HttpClient for making HTTP requests.
     */
    constructor(private http: HttpClient) { }

    /**
     * Retrieves all workloads with optional pagination and filtering.
     *
     * @param page - Page number (1-based).
     * @param pageSize - Number of items per page.
     * @param status - Optional status filter (active, pending, inactive, deleted).
     * @param search - Optional search query for workload names.
     * @returns Observable of paginated workload response.
     */
    getWorkloads(page = 1, pageSize = 50, status?: string, search?: string): Observable<PaginatedResponse<Workload>> {
        let params = new HttpParams()
            .set('page', page.toString())
            .set('page_size', pageSize.toString());

        if (status) {
            params = params.set('status', status);
        }
        if (search) {
            params = params.set('search', search);
        }

        return this.http.get<PaginatedResponse<Workload>>(WORKLOADS_API_URL, { params });
    }

    /**
     * Retrieves a single workload by its unique identifier.
     *
     * @param id - The unique workload identifier.
     * @returns Observable of the workload entity.
     */
    getWorkload(id: string): Observable<Workload> {
        return this.http.get<Workload>(`${WORKLOADS_API_URL}/${id}`);
    }

    /**
     * Creates a new workload via the backend API.
     *
     * @param request - The workload creation payload.
     * @returns Observable of the created workload with its assigned ID.
     */
    createWorkload(request: CreateWorkloadRequest): Observable<Workload> {
        return this.http.post<Workload>(WORKLOADS_API_URL, request);
    }

    /**
     * Updates an existing workload with the provided data.
     *
     * @param id - The unique workload identifier.
     * @param request - The fields to update.
     * @returns Observable of the updated workload.
     */
    updateWorkload(id: string, request: UpdateWorkloadRequest): Observable<Workload> {
        return this.http.put<Workload>(`${WORKLOADS_API_URL}/${id}`, request);
    }

    /**
     * Deletes a workload by its unique identifier.
     *
     * @param id - The unique workload identifier.
     * @returns Observable that emits void upon successful deletion.
     */
    deleteWorkload(id: string): Observable<void> {
        return this.http.delete<void>(`${WORKLOADS_API_URL}/${id}`);
    }

    /**
     * Deletes multiple workloads in a single operation.
     *
     * @param ids - Array of workload identifiers to delete.
     * @returns Observable of the bulk operation result with success/failure counts.
     */
    bulkDelete(ids: string[]): Observable<BulkOperationResult> {
        const observables = ids.map(id =>
            this.deleteWorkload(id).pipe(
                map(() => ({ id, success: true })),
                catchError(error => of({ id, success: false, error: error.message }))
            )
        );

        return forkJoin(observables).pipe(
            map(results => {
                const success = results.filter((r: any) => r.success).length;
                const failed = results.filter((r: any) => !r.success).length;
                const errors = results.filter((r: any) => !r.success).map((r: any) => ({
                    id: r.id,
                    error: r.error
                }));
                return { success, failed, errors };
            })
        );
    }

    /**
     * Retrieves firewall rules associated with a specific workload.
     *
     * @param workloadId - The workload identifier.
     * @returns Observable of associated workload rules.
     */
    getWorkloadRules(workloadId: string): Observable<Workload[]> {
        return this.http.get<Workload[]>(`${WORKLOADS_API_URL}/${workloadId}/rules`);
    }

    /**
     * Associates a firewall rule with a workload.
     *
     * @param workloadId - The workload identifier.
     * @param ruleId - The firewall rule identifier.
     * @param associationType - Whether the rule includes or excludes this workload's traffic.
     * @returns Observable of the association result.
     */
    associateRule(workloadId: string, ruleId: string, associationType: 'include' | 'exclude' = 'include'): Observable<WorkloadRuleAssociation> {
        return this.http.post<WorkloadRuleAssociation>(`${WORKLOADS_API_URL}/${workloadId}/rules`, {
            rule_id: ruleId,
            association_type: associationType
        });
    }

    /**
     * Removes an association between a firewall rule and a workload.
     *
     * @param workloadId - The workload identifier.
     * @param ruleId - The firewall rule identifier to disassociate.
     * @returns Observable that emits void upon successful disassociation.
     */
    disassociateRule(workloadId: string, ruleId: string): Observable<void> {
        return this.http.delete<void>(`${WORKLOADS_API_URL}/${workloadId}/rules/${ruleId}`);
    }

    /**
     * Retrieves firewall rules available for association with a workload.
     *
     * @param workloadId - The workload identifier.
     * @param search - Optional search query to filter available rules.
     * @returns Observable of available firewall rules.
     */
    getAvailableRules(workloadId: string, search?: string): Observable<Workload[]> {
        let params = new HttpParams().set('workload_id', workloadId);
        if (search) {
            params = params.set('search', search);
        }
        return this.http.get<Workload[]>(`${WORKLOADS_API_URL}/${workloadId}/available-rules`, { params });
    }

    /**
     * Validates workload data against business rules.
     *
     * @param data - Partial workload data to validate.
     * @returns Object containing validity flag and array of error messages.
     */
    validateWorkload(data: Partial<Workload>): { valid: boolean; errors: string[] } {
        const errors: string[] = [];

        if (!data.name) {
            errors.push('Workload name is required');
        }

        if (!data.workload_type) {
            errors.push('Workload type is required');
        }

        if (!data.environment) {
            errors.push('Environment is required');
        }

        if (!['dev', 'staging', 'prod'].includes(data.environment || '')) {
            errors.push('Environment must be dev, staging, or prod');
        }

        if (data.contact_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.contact_email)) {
            errors.push('Contact email must be a valid email address');
        }

        return {
            valid: errors.length === 0,
            errors
        };
    }

    /**
     * Returns available workload type options for use in form selects.
     *
     * @returns Array of workload type objects with value, label, and description.
     */
    getWorkloadTypeOptions(): Array<{ value: string; label: string; description: string }> {
        return [
            { value: 'vm', label: 'Virtual Machine', description: 'Azure Virtual Machine' },
            { value: 'app_service', label: 'App Service', description: 'Azure App Service' },
            { value: 'container', label: 'Container', description: 'Container App or AKS' },
            { value: 'function', label: 'Function App', description: 'Azure Function App' },
            { value: 'storage', label: 'Storage Account', description: 'Azure Storage Account' },
            { value: 'database', label: 'Database', description: 'Azure Database (SQL/NoSQL)' },
            { value: 'other', label: 'Other', description: 'Other workload type' }
        ];
    }

    /**
     * Returns available environment options for use in form selects.
     *
     * @returns Array of environment objects with value and label.
     */
    getEnvironmentOptions(): Array<{ value: string; label: string }> {
        return [
            { value: 'dev', label: 'Development' },
            { value: 'staging', label: 'Staging' },
            { value: 'prod', label: 'Production' }
        ];
    }

    /**
     * Returns available status options for use in form selects and filters.
     *
     * @returns Array of status objects with value and label.
     */
    getStatusOptions(): Array<{ value: string; label: string }> {
        return [
            { value: 'active', label: 'Active' },
            { value: 'pending', label: 'Pending' },
            { value: 'inactive', label: 'Inactive' },
            { value: 'deleted', label: 'Deleted' }
        ];
    }
}