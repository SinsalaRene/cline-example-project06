import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, catchError, map, of, forkJoin } from 'rxjs';
import { Workload, CreateWorkloadRequest, UpdateWorkloadRequest } from '../models/workload.model';

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
}

export interface WorkloadRuleAssociation {
    workload_id: string;
    rule_id: string;
    association_type: 'include' | 'exclude';
    created_at: string;
}

export interface BulkOperationResult {
    success: number;
    failed: number;
    errors: Array<{ id: string; error: string }>;
}

const WORKLOADS_API_URL = '/api/v1/workloads';

@Injectable({
    providedIn: 'root'
})
export class WorkloadsService {

    constructor(private http: HttpClient) { }

    // Get all workloads (paginated)
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

    // Get a single workload by ID
    getWorkload(id: string): Observable<Workload> {
        return this.http.get<Workload>(`${WORKLOADS_API_URL}/${id}`);
    }

    // Create a new workload
    createWorkload(request: CreateWorkloadRequest): Observable<Workload> {
        return this.http.post<Workload>(WORKLOADS_API_URL, request);
    }

    // Update an existing workload
    updateWorkload(id: string, request: UpdateWorkloadRequest): Observable<Workload> {
        return this.http.put<Workload>(`${WORKLOADS_API_URL}/${id}`, request);
    }

    // Delete a workload
    deleteWorkload(id: string): Observable<void> {
        return this.http.delete<void>(`${WORKLOADS_API_URL}/${id}`);
    }

    // Bulk delete workloads
    bulkDelete(ids: string[]): Observable<BulkOperationResult> {
        const observables = ids.map(id =>
            this.deleteWorkload(id).pipe(
                map(() => ({ id, success: true })),
                catchError(error => of({ id, success: false, error: error.message }))
            )
        );

        return forkJoin(observables).pipe(
            map(results => {
                const success = results.filter(r => r.success).length;
                const failed = results.filter(r => !r.success).length;
                const errors = results.filter(r => !r.success).map(r => ({
                    id: (r as any).id,
                    error: (r as any).error
                }));
                return { success, failed, errors };
            })
        );
    }

    // Get rules associated with a workload
    getWorkloadRules(workloadId: string): Observable<Workload[]> {
        return this.http.get<Workload[]>(`${WORKLOADS_API_URL}/${workloadId}/rules`);
    }

    // Associate a rule with a workload
    associateRule(workloadId: string, ruleId: string, associationType: 'include' | 'exclude' = 'include'): Observable<WorkloadRuleAssociation> {
        return this.http.post<WorkloadRuleAssociation>(`${WORKLOADS_API_URL}/${workloadId}/rules`, {
            rule_id: ruleId,
            association_type: associationType
        });
    }

    // Disassociate a rule from a workload
    disassociateRule(workloadId: string, ruleId: string): Observable<void> {
        return this.http.delete<void>(`${WORKLOADS_API_URL}/${workloadId}/rules/${ruleId}`);
    }

    // Get all rules available for association (not associated with this workload)
    getAvailableRules(workloadId: string, search?: string): Observable<Workload[]> {
        let params = new HttpParams().set('workload_id', workloadId);
        if (search) {
            params = params.set('search', search);
        }
        return this.http.get<Workload[]>(`${WORKLOADS_API_URL}/${workloadId}/available-rules`, { params });
    }

    // Validate workload data
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

    // Get workload type options for forms
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

    // Get environment options for forms
    getEnvironmentOptions(): Array<{ value: string; label: string }> {
        return [
            { value: 'dev', label: 'Development' },
            { value: 'staging', label: 'Staging' },
            { value: 'prod', label: 'Production' }
        ];
    }

    // Get status options for forms
    getStatusOptions(): Array<{ value: string; label: string }> {
        return [
            { value: 'active', label: 'Active' },
            { value: 'pending', label: 'Pending' },
            { value: 'inactive', label: 'Inactive' },
            { value: 'deleted', label: 'Deleted' }
        ];
    }
}