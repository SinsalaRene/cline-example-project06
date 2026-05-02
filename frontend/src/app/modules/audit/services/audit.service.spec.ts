import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { AuditService } from './audit.service';
import { AuditEntry, AuditLevel } from '../models/audit.model';

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

    describe('getAuditLog', () => {
        it('should return audit log entries', () => {
            const mockAuditLog: AuditEntry[] = [
                {
                    id: '1',
                    level: AuditLevel.INFO,
                    message: 'Test audit entry',
                    timestamp: new Date(),
                    user: 'admin',
                    action: 'TEST'
                }
            ];

            service.getAuditLog({ level: 'info' }).subscribe(entries => {
                expect(entries.length).toBe(1);
            });

            const req = httpTestingController.expectOne('/api/audit?level=info');
            expect(req.request.method).toBe('GET');
            req.flush(mockAuditLog);
        });

        it('should support filtering by date range', () => {
            const mockAuditLog: AuditEntry[] = [];

            service.getAuditLog({
                startDate: new Date('2024-01-01'),
                endDate: new Date('2024-12-31')
            }).subscribe(entries => {
                expect(entries.length).toBe(0);
            });

            const req = httpTestingController.expectOne('/api/audit?start_date=2024-01-01&end_date=2024-12-31');
            expect(req.request.method).toBe('GET');
            req.flush(mockAuditLog);
        });

        it('should support pagination', () => {
            const mockAuditLog: AuditEntry[] = [];

            service.getAuditLog({
                page: 1,
                pageSize: 20
            }).subscribe(entries => {
                expect(entries.length).toBe(0);
            });

            const req = httpTestingController.expectOne('/api/audit?page=1&page_size=20');
            expect(req.request.method).toBe('GET');
            req.flush(mockAuditLog);
        });
    });

    describe('getAuditEntryById', () => {
        it('should return single audit entry', () => {
            const mockEntry: AuditEntry = {
                id: '1',
                level: AuditLevel.INFO,
                message: 'Test entry',
                timestamp: new Date(),
                user: 'admin',
                action: 'TEST'
            };

            service.getAuditEntryById('1').subscribe(entry => {
                expect(entry.id).toBe('1');
            });

            const req = httpTestingController.expectOne('/api/audit/1');
            expect(req.request.method).toBe('GET');
            req.flush(mockEntry);
        });
    });

    describe('exportAuditLog', () => {
        it('should export audit log as CSV', () => {
            const mockExport = { format: 'csv', content: 'id,level,message\n1,INFO,test' };

            service.exportAuditLog('csv').subscribe(result => {
                expect(result.format).toBe('csv');
            });

            const req = httpTestingController.expectOne('/api/audit/export?format=csv');
            expect(req.request.method).toBe('GET');
            req.flush(mockExport);
        });
    });

    describe('getAuditStats', () => {
        it('should return audit statistics', () => {
            const mockStats = {
                totalEntries: 100,
                infoCount: 50,
                warningCount: 30,
                errorCount: 20,
                criticalCount: 0
            };

            service.getAuditStats().subscribe(stats => {
                expect(stats.totalEntries).toBe(100);
            });

            const req = httpTestingController.expectOne('/api/audit/stats');
            expect(req.request.method).toBe('GET');
            req.flush(mockStats);
        });
    });

    describe('getAuditTimeline', () => {
        it('should return audit timeline', () => {
            const mockTimeline = [
                { date: '2024-01-01', count: 10 },
                { date: '2024-01-02', count: 15 }
            ];

            service.getAuditTimeline().subscribe(timeline => {
                expect(timeline.length).toBe(2);
            });

            const req = httpTestingController.expectOne('/api/audit/timeline');
            expect(req.request.method).toBe('GET');
            req.flush(mockTimeline);
        });
    });
});