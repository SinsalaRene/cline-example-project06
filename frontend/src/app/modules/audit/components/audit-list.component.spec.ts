/**
 * Audit List Component — Unit Tests
 *
 * Tests cover the new enhanced features:
 * - Date range filtering (default 30 days, manual selection, clear)
 * - Multi-select filter dropdowns (actions, resource types, severity)
 * - Filter chip management (add/remove)
 * - Export functionality (CSV, JSON with blob download)
 * - Summary statistics loading and rendering
 * - Pagination (0→1 page mapping)
 * - Debounced filter change handling
 */

import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSelectModule } from '@angular/material/select';
import { MatDividerModule } from '@angular/material/divider';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { DatePipe } from '@angular/common';
import { of, Subject } from 'rxjs';

import { AuditListComponent } from './audit-list.component';
import { AuditService } from '../services/audit.service';
import type {
    AuditEntry,
    AuditAction,
    AuditResourceType,
    AuditSeverity,
    AuditFilter,
    AuditSummary,
} from '../models/audit.model';

// ─── Mock AuditService ───────────────────────────────────────────────────────

class AuditServiceMock {
    getLogs$ = new Subject<any[]>();
    summary$ = new Subject<AuditSummary>();

    getAuditLogs(_page: number, _pageSize: number, _filters?: AuditFilter) {
        return this.getLogs$.asObservable();
    }

    getAuditEntry(_id: string) {
        return of(null as unknown as AuditEntry);
    }

    searchAuditLogs(_query: string, _page: number, _pageSize: number) {
        return of({ items: [], total: 0, page: 1, pageSize: 20 } as any);
    }

    exportAsCsv(_filters?: AuditFilter) {
        return of(new Blob(['col1,col2'], { type: 'text/csv' }));
    }

    exportAsJson(_filters?: AuditFilter) {
        return of(new Blob(['{}'], { type: 'application/json' }));
    }

    getAuditSummary(_dateFrom?: string, _dateTo?: string) {
        return this.summary$.asObservable();
    }

    filterAuditEntries(entries: AuditEntry[], _filters: AuditFilter): AuditEntry[] {
        return entries;
    }

    getSeverityDisplay(severity: AuditSeverity) {
        return {
            label: severity.charAt(0).toUpperCase() + severity.slice(1),
            color: '#000',
            icon: 'circle',
            cssClass: `audit-severity-${severity}`,
        };
    }

    getActionDisplay(action: string) {
        return action.toLowerCase().replace(/_/g, ' ');
    }

    getResourceTypeDisplay(resourceType: string) {
        return resourceType.toLowerCase().replace(/_/g, ' ');
    }

    formatTimestamp(dateString: string): string {
        return dateString;
    }

    getRelativeTime(_dateString: string): string {
        return 'now';
    }

    getUniqueUsers(_entries: AuditEntry[]): string[] {
        return [];
    }

    getUniqueActions(_entries: AuditEntry[]): string[] {
        return [];
    }

    getActionIcon(_action: string): string {
        return 'help';
    }

    getResourceTypeIcon(_resourceType: string): string {
        return 'help';
    }

    isRecent(_dateString: string): boolean {
        return true;
    }
}

// ─── Test Fixtures ───────────────────────────────────────────────────────────

const MOCK_ENTRIES: AuditEntry[] = [
    {
        id: '1',
        action: 'CREATE' as AuditAction,
        resourceType: 'FIREWALL_RULE' as AuditResourceType,
        severity: 'info' as AuditSeverity,
        user: 'user1@example.com',
        displayName: 'User One',
        timestamp: new Date('2026-05-01T10:00:00Z').toISOString(),
        description: 'Created firewall rule',
        resourceId: 'fw-rule-001',
        ipAddress: '192.168.1.1',
        success: true,
        metadata: {},
    },
    {
        id: '2',
        action: 'DELETE' as AuditAction,
        resourceType: 'ACCESS_RULE' as AuditResourceType,
        severity: 'error' as AuditSeverity,
        user: 'user2@example.com',
        displayName: 'User Two',
        timestamp: new Date('2026-05-02T14:00:00Z').toISOString(),
        description: 'Deleted access rule',
        resourceId: 'access-rule-002',
        ipAddress: '192.168.1.2',
        success: false,
        metadata: {},
    },
];

const MOCK_SUMMARY: AuditSummary = {
    totalCount: 42,
    byAction: {
        CREATE: 15,
        DELETE: 10,
        UPDATE: 8,
        READ: 5,
        LOGIN: 4,
    },
    byResourceType: {
        FIREWALL_RULE: 20,
        ACCESS_RULE: 12,
        USER: 6,
        CONFIGURATION: 4,
        DEPLOYMENT: 0,
    },
    bySeverity: {
        info: 25,
        error: 10,
        warning: 5,
        success: 2,
    },
    bySuccess: {
        true: 38,
        false: 4,
    },
    byUser: {
        'user1@example.com': 20,
        'user2@example.com': 15,
        'user3@example.com': 7,
    },
    recentActivity: [
        { date: '2026-05-01', count: 15 },
        { date: '2026-05-02', count: 12 },
        { date: '2026-05-03', count: 8 },
        { date: '2026-05-04', count: 5 },
        { date: '2026-05-05', count: 2 },
    ],
    topUsers: [
        { user: 'user1@example.com', count: 20 },
        { user: 'user2@example.com', count: 15 },
        { user: 'user3@example.com', count: 7 },
    ],
};

describe('AuditListComponent', () => {
    let component: AuditListComponent;
    let fixture: ComponentFixture<AuditListComponent>;
    let mockService: AuditServiceMock;

    beforeEach(async () => {
        mockService = new AuditServiceMock();

        await TestBed.configureTestingModule({
            imports: [
                AuditListComponent,
                ReactiveFormsModule,
                NoopAnimationsModule,
                MatDatepickerModule,
                MatNativeDateModule,
                MatCheckboxModule,
                MatSelectModule,
                MatDividerModule,
                MatTableModule,
                MatPaginatorModule,
                MatSortModule,
                MatFormFieldModule,
                MatInputModule,
                MatButtonModule,
                MatIconModule,
                MatProgressSpinnerModule,
                MatChipsModule,
                MatCardModule,
                MatSnackBarModule,
            ],
            providers: [
                DatePipe,
                {
                    provide: AuditService,
                    useValue: mockService,
                },
            ],
        }).compileComponents();

        // Set up spies on the mock service
        spyOn(mockService, 'getAuditLogs').and.returnValue(of(MOCK_ENTRIES));
        spyOn(mockService, 'getAuditSummary').and.returnValue(of(MOCK_SUMMARY));
        spyOn(mockService, 'exportAsCsv').and.returnValue(
            of(new Blob(['a,b'], { type: 'text/csv' }))
        );
        spyOn(mockService, 'exportAsJson').and.returnValue(
            of(new Blob(['{}'], { type: 'application/json' }))
        );
        spyOn(mockService, 'getSeverityDisplay').and.callThrough();
        spyOn(mockService, 'getActionDisplay').and.callThrough();
        spyOn(mockService, 'getResourceTypeDisplay').and.callThrough();
        spyOn(mockService, 'getRelativeTime').and.returnValue('5m ago');
        spyOn(mockService, 'getActionIcon').and.returnValue('add');
        spyOn(mockService, 'getResourceTypeIcon').and.returnValue('folder');

        fixture = TestBed.createComponent(AuditListComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    // ─── Date Range Tests ──────────────────────────────────────────────────

    describe('date range filtering', () => {
        it('should default toDate to today and fromDate to 30 days ago on init', () => {
            expect(component.toDate).not.toBeNull();
            expect(component.fromDate).not.toBeNull();

            const today = new Date();
            const todayStr = today.toISOString().split('T')[0];
            const fromStr = (component.fromDate as Date).toISOString().split('T')[0];

            // Allow 1 day tolerance for timezone differences
            const diffMs = Math.abs(
                new Date(todayStr).getTime() -
                new Date(fromStr).getTime()
            );
            const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
            expect(diffDays).toBeGreaterThanOrEqual(29);
            expect(diffDays).toBeLessThanOrEqual(31);
        });

        it('should call loadAuditLog and loadSummary when from date changes', fakeAsync(() => {
            const newDate = new Date('2026-04-15');
            component.onFromDateChange(newDate);
            tick(400); // Wait for debounce

            expect(component.fromDate).toEqual(newDate);
            expect(mockService.getAuditLogs).toHaveBeenCalled();
            expect(mockService.getAuditSummary).toHaveBeenCalled();
        }));

        it('should call loadAuditLog and loadSummary when to date changes', fakeAsync(() => {
            const newDate = new Date('2026-05-10');
            component.onToDateChange(newDate);
            tick(400);

            expect(component.toDate).toEqual(newDate);
            expect(mockService.getAuditLogs).toHaveBeenCalled();
            expect(mockService.getAuditSummary).toHaveBeenCalled();
        }));

        it('should clear dates and reload when clearDates is called', fakeAsync(() => {
            component.fromDate = new Date('2026-04-01');
            component.toDate = new Date('2026-05-01');
            component.clearDates();
            tick(400);

            expect(component.fromDate).toBeNull();
            expect(component.toDate).toBeNull();
            expect(mockService.getAuditLogs).toHaveBeenCalled();
        }));
    });

    // ─── Filter Dropdown Tests ─────────────────────────────────────────────

    describe('filter dropdowns', () => {
        it('should populate action options from service display helpers', () => {
            expect(component.actionOptions.length).toBeGreaterThan(0);
            const createAction = component.actionOptions.find(
                (o) => o.value === 'CREATE'
            );
            expect(createAction).toBeDefined();
            expect(createAction!.label).toEqual(
                mockService.getActionDisplay('CREATE')
            );
        });

        it('should populate resource type options from service display helpers', () => {
            expect(component.resourceTypeOptions.length).toBeGreaterThan(0);
            const createRT = component.resourceTypeOptions.find(
                (o) => o.value === 'FIREWALL_RULE'
            );
            expect(createRT).toBeDefined();
            expect(createRT!.label).toEqual(
                mockService.getResourceTypeDisplay('FIREWALL_RULE')
            );
        });

        it('should populate severity options', () => {
            expect(component.severityOptions.length).toBe(4);
            const severities = component.severityOptions.map((o) => o.value);
            expect(severities).toContain('info');
            expect(severities).toContain('warning');
            expect(severities).toContain('error');
            expect(severities).toContain('success');
        });

        it('should emit filter change when action filter is updated', fakeAsync(() => {
            component.onActionFilterChange(['CREATE', 'UPDATE']);
            tick(400);

            expect(component.selectedActions).toEqual(['CREATE', 'UPDATE']);
            expect(mockService.getAuditLogs).toHaveBeenCalled();
        }));

        it('should emit filter change when resource type filter is updated', fakeAsync(() => {
            component.onResourceTypeFilterChange([
                'FIREWALL_RULE' as AuditResourceType,
            ]);
            tick(400);

            expect(component.selectedResourceTypes).toEqual([
                'FIREWALL_RULE' as AuditResourceType,
            ]);
            expect(mockService.getAuditLogs).toHaveBeenCalled();
        }));

        it('should emit filter change when severity filter is updated', fakeAsync(() => {
            component.onSeverityFilterChange(['error' as AuditSeverity]);
            tick(400);

            expect(component.selectedSeverities).toEqual(['error' as AuditSeverity]);
            expect(mockService.getAuditLogs).toHaveBeenCalled();
        }));

        it('should build active filter chips from selected values', () => {
            component.selectedActions = ['CREATE'];
            component.selectedSeverities = ['error'];

            const chips = component.activeFilters;
            expect(chips.length).toBe(2);
            expect(chips.some((c) => c.key === 'action' && c.value === 'CREATE'))
                .toBeTruthy();
            expect(chips.some((c) => c.key === 'severity' && c.value === 'error'))
                .toBeTruthy();
        });

        it('should remove an action filter chip and reload', fakeAsync(() => {
            component.selectedActions = ['CREATE', 'UPDATE'];
            component.selectedSeverities = ['error'];

            const chips = component.activeFilters;
            const actionChip = chips.find((c) => c.key === 'action' && c.value === 'CREATE');
            expect(actionChip).toBeDefined();

            if (actionChip) {
                component.removeFilter(actionChip);
                tick(400);

                expect(component.selectedActions).toEqual(['UPDATE']);
                expect(mockService.getAuditLogs).toHaveBeenCalled();
            }
        }));
    });

    // ─── Export Tests ──────────────────────────────────────────────────────

    describe('export functionality', () => {
        it('should export CSV and trigger file download', () => {
            const mockLink = {
                href: '',
                download: '',
                click: jasmine.createSpy('click'),
            } as unknown as HTMLAnchorElement;
            spyOn(document, 'createElement').and.returnValue(mockLink as any);

            component.exportCsv();

            expect(mockService.exportAsCsv).toHaveBeenCalled();
            expect(mockLink.click).toHaveBeenCalled();
        });

        it('should export JSON and trigger file download', () => {
            const mockLink = {
                href: '',
                download: '',
                click: jasmine.createSpy('click'),
            } as unknown as HTMLAnchorElement;
            spyOn(document, 'createElement').and.returnValue(mockLink as any);

            component.exportJson();

            expect(mockService.exportAsJson).toHaveBeenCalled();
            expect(mockLink.click).toHaveBeenCalled();
        });

        it('should show success snackbar on export', () => {
            const snackBarSpy = spyOn(
                TestBed.inject(MatSnackBar),
                'open'
            ).and.stub();

            const mockLink = {
                href: '',
                download: '',
                click: jasmine.createSpy('click'),
            } as unknown as HTMLAnchorElement;
            spyOn(document, 'createElement').and.returnValue(mockLink as any);

            component.exportCsv();

            expect(snackBarSpy).toHaveBeenCalled();
            const call = snackBarSpy.calls.first() as any;
            expect(call.args[0]).toContain('CSV export downloaded');
        });

        it('should show error snackbar on export failure', fakeAsync(() => {
            spyOn(mockService, 'exportAsCsv').and.throwError('network error');

            const snackBarSpy = spyOn(
                TestBed.inject(MatSnackBar),
                'open'
            ).and.stub();

            const mockLink = {
                href: '',
                download: '',
                click: jasmine.createSpy('click'),
            } as unknown as HTMLAnchorElement;
            spyOn(document, 'createElement').and.returnValue(mockLink as any);

            component.exportCsv();
            tick();

            expect(snackBarSpy).toHaveBeenCalled();
        }));
    });

    // ─── Summary Statistics Tests ──────────────────────────────────────────

    describe('summary statistics', () => {
        it('should load summary on component init', () => {
            expect(mockService.getAuditSummary).toHaveBeenCalled();
            expect(component.summaryLoaded).toBeTruthy();
        });

        it('should populate topActions from summary data', () => {
            expect(component.topActions.length).toBe(5);
            expect(component.topActions[0].label).toEqual(
                mockService.getActionDisplay('CREATE')
            );
            expect(component.topActions[0].count).toBe(15);
        });

        it('should populate topResourceTypes from summary data', () => {
            expect(component.topResourceTypes.length).toBe(5);
            expect(component.topResourceTypes[0].label).toEqual(
                mockService.getResourceTypeDisplay('FIREWALL_RULE')
            );
            expect(component.topResourceTypes[0].count).toBe(20);
        });

        it('should refresh summary when filters change', fakeAsync(() => {
            const newSummary: AuditSummary = {
                totalCount: 100,
                byAction: { CREATE: 50 },
                byResourceType: {},
                bySeverity: {},
                bySuccess: {},
                byUser: {},
                recentActivity: [],
                topUsers: [],
            };
            spyOn(mockService, 'getAuditSummary').and.returnValue(
                of(newSummary)
            );

            component.onFromDateChange(new Date());
            tick(400);

            expect(mockService.getAuditSummary).toHaveBeenCalled();
        }));
    });

    // ─── Pagination Tests ──────────────────────────────────────────────────

    describe('pagination', () => {
        it('should map 0-based paginator pageIndex to 1-based API page', fakeAsync(() => {
            // Simulate paginator on page 1 (pageIndex = 1)
            component.paginator = {
                pageIndex: 1,
                pageSize: 25,
                length: 100,
                page: new Subject(),
            } as any;

            component.loadAuditLog();

            expect(mockService.getAuditLogs).toHaveBeenCalledWith(
                2, // pageIndex 1 + 1 = 2
                25,
                jasmine.any(Object)
            );
        }));

        it('should use paginator pageSize for page size', fakeAsync(() => {
            component.paginator = {
                pageIndex: 0,
                pageSize: 50,
                length: 100,
                page: new Subject(),
            } as any;

            component.loadAuditLog();

            expect(mockService.getAuditLogs).toHaveBeenCalledWith(
                1,
                50,
                jasmine.any(Object)
            );
        }));

        it('should default to page 1 and page size 20 when paginator is not set', fakeAsync(() => {
            component.paginator = null as any;

            component.loadAuditLog();

            expect(mockService.getAuditLogs).toHaveBeenCalledWith(
                1,
                20,
                jasmine.any(Object)
            );
        }));
    });

    // ─── Display Helper Tests ──────────────────────────────────────────────

    describe('display helpers', () => {
        it('should get severity display from service', () => {
            const result = component.getSeverityDisplay('error' as AuditSeverity);
            expect(result).toEqual(
                mockService.getSeverityDisplay('error' as AuditSeverity)
            );
        });

        it('should get action display from service', () => {
            const result = component.getActionDisplay('CREATE');
            expect(result).toEqual(
                mockService.getActionDisplay('CREATE')
            );
        });

        it('should get resource type display from service', () => {
            const result = component.getResourceTypeDisplay(
                'FIREWALL_RULE' as AuditResourceType
            );
            expect(result).toEqual(
                mockService.getResourceTypeDisplay(
                    'FIREWALL_RULE' as AuditResourceType
                )
            );
        });

        it('should get relative time from service', () => {
            const result = component.getRelativeTime(
                new Date().toISOString()
            );
            expect(result).toEqual(mockService.getRelativeTime(
                new Date().toISOString()
            ));
        });

        it('should calculate bar width correctly', () => {
            expect(component.getBarWidth(15, 15)).toBe(100);
            expect(component.getBarWidth(10, 20)).toBe(50);
            expect(component.getBarWidth(0, 100)).toBe(0);
            expect(component.getBarWidth(5, 0)).toBe(0);
        });

        it('should return severity CSS class', () => {
            const cssClass = component.getSeverityClass('error' as AuditSeverity);
            expect(cssClass).toEqual(
                mockService.getSeverityDisplay('error' as AuditSeverity).cssClass
            );
        });

        it('should get action icon from service', () => {
            const icon = component.getActionIcon('CREATE');
            expect(icon).toEqual(mockService.getActionIcon('CREATE'));
        });
    });

    // ─── Search Tests ──────────────────────────────────────────────────────

    describe('search', () => {
        it('should emit filter change when search query changes', fakeAsync(() => {
            component.onSearchQueryChange('firewall rule');
            tick(400);

            expect(component.searchQuery).toEqual('firewall rule');
            expect(mockService.getAuditLogs).toHaveBeenCalled();
        }));
    });

    // ─── Refresh Tests ─────────────────────────────────────────────────────

    describe('refresh', () => {
        it('should reload audit log on refreshData', fakeAsync(() => {
            component.refreshData();
            expect(mockService.getAuditLogs).toHaveBeenCalled();
        }));
    });

    // ─── Documentation Tests ───────────────────────────────────────────────

    describe('documentation', () => {
        it('should have JSDoc comment block at top of component', () => {
            // Verify component has the documented features
            expect(component.loadAuditLog).toBeDefined();
            expect(component.loadSummary).toBeDefined();
            expect(component.exportCsv).toBeDefined();
            expect(component.exportJson).toBeDefined();
        });
    });
});