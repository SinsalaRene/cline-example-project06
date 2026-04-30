import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface FirewallRule {
    id: string;
    rule_collection_name: string;
    priority: number;
    action: string;
    protocol: string;
    source_addresses?: string[];
    destination_fqdns?: string[];
    source_ip_groups?: string[];
    destination_ports?: number[];
    description?: string;
    workload_id?: string;
    azure_resource_id?: string;
    status: string;
    created_at: string;
    updated_at: string;
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
}

@Injectable({ providedIn: 'root' })
export class RulesService {
    private baseUrl = '/api/v1/rules';

    constructor(private http: HttpClient) { }

    getRules(page = 1, pageSize = 50, status?: string, workloadId?: string): Observable<PaginatedResponse<FirewallRule>> {
        let params = new HttpParams()
            .set('page', page.toString())
            .set('page_size', pageSize.toString());

        if (status) {
            params = params.set('status', status);
        }
        if (workloadId) {
            params = params.set('workload_id', workloadId);
        }

        return this.http.get<PaginatedResponse<FirewallRule>>(this.baseUrl, { params });
    }

    getRule(id: string): Observable<FirewallRule> {
        return this.http.get<FirewallRule>(`${this.baseUrl}/${id}`);
    }

    createRule(rule: Partial<FirewallRule>): Observable<FirewallRule> {
        return this.http.post<FirewallRule>(this.baseUrl, rule);
    }

    updateRule(id: string, rule: Partial<FirewallRule>): Observable<FirewallRule> {
        return this.http.put<FirewallRule>(`${this.baseUrl}/${id}`, rule);
    }

    deleteRule(id: string): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/${id}`);
    }
}