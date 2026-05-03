import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { AuditService } from './audit.service';
import { AuditEntry, AuditFilter, AuditListResponse, AuditSummary } from '../models/audit.model';

describe('AuditService', () => {
    let service: AuditService;
    let httpTestingController: HttpTestingController;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [AuditService]
        });

        service = TestBed.inject(AuditService);
        httpTestingController = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpTestingController.verify();
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('getAuditLogs', () => {
        it('should return paginated audit entries', () => {
            const mockResponse: AuditListResponse = {
                items: [
                    {
                        id: '1',
                        action: 'CREATE',
                        resourceId: 'res-1',
                        resourceType: 'FIREWALL_RULE',
                        severity: 'info',
                        user: 'admin',
                        displayName: 'Admin User',
                        timestamp: '2024-01-01T10:00:00Z',
                        success: true,
                        description: 'Test audit entry'
                    }
                ],
                total: 1,
                page: 1,
                pageSize: 20,
                totalPages: 1
            };

            service.getAuditLogs(1, 20).subscribe((response: AuditListResponse) => {
                expect(response.items.length).toBe(1);
            });

            const req = httpTestingController.expectOne('/api/v1/audit?page=1&page_size=20');
            expect(req.request.method).toBe('GET');
            req.flush(mockResponse);
        });

        it('should support filtering by search query', () => {
            const mockResponse: AuditListResponse = {
                items: [],
                total: 0,
                page: 1,
                pageSize: 20,
                totalPages: 0
            };

            service.getAuditLogs(1, 20, { searchQuery: 'test' }).subscribe(() => { });

            const req = httpTestingController.expectOne('/api/v1/audit?page=1&page_size=20&search=test');
            expect(req.request.method).toBe('GET');
            req.flush(mockResponse);
        });
    });

    describe('getAuditEntry', () => {
        it('should return single audit entry', () => {
            const mockEntry: AuditEntry = {
                id: '1',
                action: 'CREATE',
                resourceId: 'res-1',
                resourceType: 'FIREWALL_RULE',
                severity: 'info',
                user: 'admin',
                displayName: 'Admin User',
                timestamp: '2024-01-01T10:00:00Z',
                success: true,
                description: 'Test entry'
            };

            service.getAuditEntry('1').subscribe((entry: AuditEntry) => {
                expect(entry.id).toBe('1');
            });

            const req = httpTestingController.expectOne('/api/v1/audit/1');
            expect(req.request.method).toBe('GET');
            req.flush(mockEntry);
        });
    });

    describe('searchAuditLogs', () => {
        it('should search audit logs', () => {
            const mockEntries: AuditEntry[] = [];

            service.searchAuditLogs('test query').subscribe((entries: AuditEntry[]) => {
                expect(entries.length).toBe(0);
            });

            const req = httpTestingController.expectOne('/api/v1/audit/search?query=test%20query&limit=50');
            expect(req.request.method).toBe('GET');
            req.flush(mockEntries);
        });
    });

    describe('getAuditSummary', () => {
        it('should return audit summary', () => {
            const mockSummary: AuditSummary = {
                totalCount: 100,
                byAction: { CREATE: 40, UPDATE: 30, DELETE: 30 },
                byResourceType: { FIREWALL_RULE: 50, ACCESS_RULE: 50 },
                bySeverity: { info: 50, warning: 30, error: 20 },
                bySuccess: { true: 90, false: 10 },
                byUser: { admin: 60, user: 40 },
                recentActivity: [],
                topUsers: []
            };

            service.getAuditSummary().subscribe((summary: AuditSummary) => {
                expect(summary.totalCount).toBe(100);
            });

            const req = httpTestingController.expectOne('/api/v1/audit/summary');
            expect(req.request.method).toBe('GET');
            req.flush(mockSummary);
        });
    });

    describe('exportAuditLogs', () => {
        it('should export audit logs as CSV', () => {
            const mockBlob = new Blob(['id,action,resourceType'], { type: 'text/csv' });

            service.exportAuditLogs({ format: 'csv', filters: {} as AuditFilter }).subscribe((result: Blob) => {
                expect(result.type).toBe('text/csv');
            });

            const req = httpTestingController.expectOne('/api/v1/audit/export/csv');
            expect(req.request.method).toBe('GET');
            req.flush(mockBlob);
        });
    });

    describe('formatTimestamp', () => {
        it('should format timestamp', () => {
            const result = service.formatTimestamp('2024-01-01T10:00:00Z');
            expect(result).toBeDefined();
        });
    });

    describe('getSeverityDisplay', () => {
        it('should return severity display info', () => {
            const result = service.getSeverityDisplay('info');
            expect(result.label).toBe('Info');
        });
    });

    describe('getActionDisplay', () => {
        it('should return action display text', () => {
            const result = service.getActionDisplay('CREATE');
            expect(result).toBe('Created');
        });
    });

    describe('getRelativeTime', () => {
        it('should return relative time string', () => {
            const pastDate = new Date(Date.now() - 60000).toISOString();
            const result = service.getRelativeTime(pastDate);
            expect(result).toContain('m ago');
        });
    });

    describe('filterAuditEntries', () => {
        it('should filter entries by action', () => {
            const entries: AuditEntry[] = [
                {
                    id: '1',
                    action: 'CREATE',
                    resourceId: 'res-1',
                    resourceType: 'FIREWALL_RULE',
                    severity: 'info',
                    user: 'admin',
                    displayName: 'Admin',
                    timestamp: '2024-01-01T10:00:00Z',
                    success: true,
                    description: 'test'
                }
            ];
            const filtered = service.filterAuditEntries(entries, { actionFilter: ['CREATE'] });
            expect(filtered.length).toBe(1);
        });
    });
});