import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, forkJoin, of, catchError, map } from 'rxjs';
import { firstValueFrom } from 'rxjs';

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

export interface BulkOperationResult<T = void> {
    success: number;
    failed: number;
    errors: Array<{ id: string; error: string }>;
}

export interface ExportFormat {
    format: 'json' | 'csv';
    selectedIds?: string[];
    includeFields?: string[];
}

export interface ImportResult {
    imported: number;
    skipped: number;
    errors: string[];
}

@Injectable({ providedIn: 'root' })
export class RulesService {
    private baseUrl = '/api/v1/rules';

    constructor(private http: HttpClient) { }

    // Get all rules (paginated)
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

    // Get all rules (unpaginated, for export)
    getAllRules(): Observable<FirewallRule[]> {
        return this.http.get<PaginatedResponse<FirewallRule>>(this.baseUrl, {
            params: new HttpParams()
                .set('page', '1')
                .set('page_size', '1000')
        }).pipe(map((response: any) => response.items));
    }

    // Get a single rule by ID
    getRule(id: string): Observable<FirewallRule> {
        return this.http.get<FirewallRule>(`${this.baseUrl}/${id}`);
    }

    // Create a new rule
    createRule(rule: Partial<FirewallRule>): Observable<FirewallRule> {
        return this.http.post<FirewallRule>(this.baseUrl, rule);
    }

    // Update an existing rule
    updateRule(id: string, rule: Partial<FirewallRule>): Observable<FirewallRule> {
        return this.http.put<FirewallRule>(`${this.baseUrl}/${id}`, rule);
    }

    // Delete a rule
    deleteRule(id: string): Observable<void> {
        return this.http.delete<void>(`${this.baseUrl}/${id}`);
    }

    // Duplicate a rule
    duplicateRule(id: string, newName?: string): Observable<FirewallRule> {
        return this.http.post<FirewallRule>(`${this.baseUrl}/${id}/duplicate`, { name: newName });
    }

    // Bulk delete rules
    bulkDelete(ids: string[]): Observable<BulkOperationResult> {
        const observables = ids.map(id =>
            this.deleteRule(id)
        );

        return forkJoin(observables).pipe(
            map(() => ({
                success: ids.length,
                failed: 0,
                errors: []
            })),
            catchError((err) => of({
                success: 0,
                failed: ids.length,
                errors: ids.map(id => ({ id, error: err.message || 'Unknown error' }))
            }))
        );
    }

    // Bulk enable rules
    bulkEnable(ids: string[]): Observable<BulkOperationResult> {
        return this.bulkUpdateStatus(ids, 'active');
    }

    // Bulk disable rules
    bulkDisable(ids: string[]): Observable<BulkOperationResult> {
        return this.bulkUpdateStatus(ids, 'pending');
    }

    // Bulk update rule status
    private bulkUpdateStatus(ids: string[], status: string): Observable<BulkOperationResult> {
        const observables = ids.map(id => {
            return this.updateRule(id, { status: status as any } as Partial<FirewallRule>);
        });

        return forkJoin(observables).pipe(
            map(() => ({
                success: ids.length,
                failed: 0,
                errors: []
            })),
            catchError((err) => of({
                success: 0,
                failed: ids.length,
                errors: ids.map(id => ({ id, error: err.message || 'Unknown error' }))
            }))
        );
    }

    // Import rules from file content (sequential import)
    async importRules(rules: Partial<FirewallRule>[]): Promise<ImportResult> {
        let imported = 0;
        let skipped = 0;
        const errors: string[] = [];

        for (let i = 0; i < rules.length; i++) {
            try {
                await firstValueFrom(this.createRule(rules[i]));
                imported++;
            } catch (err: any) {
                skipped++;
                errors.push(`Rule ${i + 1}: ${err.message || 'Unknown error'}`);
            }
        }

        return {
            imported,
            skipped,
            errors
        };
    }

    // Export rules to JSON
    exportRules(rules: FirewallRule[], format: 'json' | 'csv' = 'json'): Observable<Blob> {
        let content: string;
        let mimeType: string;

        if (format === 'csv') {
            content = this.rulesToCSV(rules);
            mimeType = 'text/csv';
        } else {
            content = JSON.stringify(rules, null, 2);
            mimeType = 'application/json';
        }

        return of(new Blob([content], { type: mimeType }));
    }

    // Validate rule data
    validateRule(rule: Partial<FirewallRule>): { valid: boolean; errors: string[] } {
        const errors: string[] = [];

        if (!rule.rule_collection_name) {
            errors.push('Rule name is required');
        }

        if (rule.priority !== undefined && (rule.priority < 1 || rule.priority > 1000)) {
            errors.push('Priority must be between 1 and 1000');
        }

        if (!rule.action) {
            errors.push('Action is required');
        }

        if (rule.action && !['Allow', 'Deny'].includes(rule.action)) {
            errors.push('Action must be Allow or Deny');
        }

        if (!rule.protocol) {
            errors.push('Protocol is required');
        }

        return {
            valid: errors.length === 0,
            errors
        };
    }

    // Check for duplicate rules
    findDuplicates(rules: FirewallRule[], newRule: Partial<FirewallRule>): FirewallRule[] {
        return rules.filter(rule =>
            rule.rule_collection_name === newRule.rule_collection_name ||
            (rule.protocol === newRule.protocol &&
                rule.action === newRule.action &&
                rule.priority === newRule.priority)
        );
    }

    // Utility: Convert rules to CSV
    private rulesToCSV(rules: FirewallRule[]): string {
        const headers = ['Name', 'Priority', 'Action', 'Protocol', 'Description', 'Status'];
        const rows = rules.map(rule => [
            rule.rule_collection_name,
            rule.priority,
            rule.action,
            rule.protocol,
            rule.description || '',
            rule.status
        ]);

        return [headers, ...rows].map(row =>
            row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')
        ).join('\n');
    }

    // Utility: Parse CSV rules
    parseCSV(csvContent: string): Partial<FirewallRule>[] {
        const lines = csvContent.split('\n').filter(line => line.trim());
        if (lines.length < 2) return [];

        const headers = lines[0].split(',').map(h => h.trim());
        const rules: Partial<FirewallRule>[] = [];

        for (let i = 1; i < lines.length; i++) {
            const values = this.parseCSVLine(lines[i]);
            if (values.length >= headers.length) {
                const rule: Partial<FirewallRule> = {};
                values.forEach((value, index) => {
                    const header = headers[index];
                    if (header === 'priority') {
                        (rule as any)['priority'] = parseInt(value, 10);
                    } else if (header === 'rule_collection_name') {
                        rule.rule_collection_name = value;
                    } else if (header === 'action') {
                        rule.action = value;
                    } else if (header === 'protocol') {
                        rule.protocol = value;
                    } else if (header === 'description') {
                        rule.description = value;
                    } else if (header === 'status') {
                        rule.status = value;
                    }
                });
                rules.push(rule);
            }
        }

        return rules;
    }

    private parseCSVLine(line: string): string[] {
        const result: string[] = [];
        let current = '';
        let inQuotes = false;

        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                result.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }

        if (current) {
            result.push(current.trim());
        }

        return result;
    }
}
