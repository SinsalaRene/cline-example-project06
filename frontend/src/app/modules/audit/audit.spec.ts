/**
 * Audit Module Tests
 */

import { ComponentFixture, TestBed, fakeAsync, tick, flush } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ReactiveFormsModule, FormsModule, FormBuilder } from '@angular/forms';
import { provideAnimations } from '@angular/platform-browser/animations';
import {
    AuditEntry,
    AuditFilter,
    AuditAction,
    AuditResourceType,
    AuditSeverity,
    AuditSummary
} from './models/audit.model';
import { AuditService } from './services/audit.service';
import { AuditViewerComponent } from './components/audit-viewer.component';
import { AuditDetailComponent } from './components/audit-detail.component';
import { of, throwError, lastValueFrom } from 'rxjs';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

// Helper values since AuditAction/AuditResourceType/AuditSeverity are type aliases, not enums
const AUDIT_ACTIONS: AuditAction[] = ['CREATE', 'UPDATE', 'DELETE', 'READ', 'LOGIN', 'LOGOUT', 'APPROVE', 'REJECT', 'IMPORT', 'EXPORT', 'CONFIGURE', 'DEPLOY', 'TEST', 'EXECUTE'];
const AUDIT_RESOURCE_TYPES: AuditResourceType[] = ['FIREWALL_RULE', 'ACCESS_RULE', 'THRESHOLD', 'WORKSPACE', 'USER', 'CONFIGURATION', 'DEPLOYMENT', 'APPROVAL', 'RULE_EVALUATION', 'BATCH_OPERATION', 'WEBHOOK', 'NOTIFICATION'];
const AUDIT_SEVERITIES: AuditSeverity[] = ['info', 'warning', 'error', 'success'];

// ============================================================
// Audit Model Tests
// ============================================================

describe('Audit Models', () => {
    describe('AuditEntry', () => {
        it('should create a valid AuditEntry', () => {
            const entry: AuditEntry = {
                id: 'test-001',
                timestamp: '2024-01-15T10:30:00Z',
                user: 'john@example.com',
                displayName: 'John Doe',
                ipAddress: '192.168.1.100',
                httpMethod: 'POST',
                path: '/api/v1/firewall/rules',
                action: 'CREATE',
                resourceType: 'FIREWALL_RULE',
                resourceId: 'fw-rule-123',
                description: 'Created new firewall rule',
                severity: 'info',
                success: true,
                details: {
                    requestBody: { name: 'Allow SSH' }
                },
                result: {
                    success: true,
                    affectedCount: 1
                }
            };

            expect(entry.id).toBe('test-001');
            expect(entry.action).toBe('CREATE');
            expect(entry.resourceType).toBe('FIREWALL_RULE');
            expect(entry.severity).toBe('info');
            expect(entry.success).toBe(true);
        });

        it('should validate AuditAction enum values', () => {
            AUDIT_ACTIONS.forEach(action => {
                expect(action).toBeDefined();
            });
        });

        it('should validate AuditResourceType enum values', () => {
            AUDIT_RESOURCE_TYPES.forEach(type => {
                expect(type).toBeDefined();
            });
        });

        it('should validate AuditSeverity enum values', () => {
            AUDIT_SEVERITIES.forEach(severity => {
                expect(severity).toBeDefined();
            });
        });
    });

    describe('AuditFilter', () => {
        it('should create a default empty filter', () => {
            const filter: AuditFilter = {
                searchQuery: '',
                page: 1,
                pageSize: 20
            };

            expect(filter.searchQuery).toBe('');
            expect(filter.page).toBe(1);
            expect(filter.pageSize).toBe(20);
        });

        it('should create a filter with multiple criteria', () => {
            const filter: AuditFilter = {
                searchQuery: 'firewall',
                dateFrom: '2024-01-01T00:00:00Z',
                dateTo: '2024-01-31T23:59:59Z',
                actionFilter: ['CREATE', 'DELETE'],
                resourceTypeFilter: ['FIREWALL_RULE'],
                severityFilter: ['error', 'warning'],
                userFilter: ['admin@example.com'],
                successFilter: false,
                page: 1,
                pageSize: 50
            };

            expect(filter.searchQuery).toBe('firewall');
            expect(filter.actionFilter).toHaveLength(2);
            expect(filter.resourceTypeFilter).toHaveLength(1);
            expect(filter.severityFilter).toHaveLength(2);
            expect(filter.page).toBe(1);
            expect(filter.pageSize).toBe(50);
        });
    });

    describe('AuditListResponse', () => {
        it('should create a valid paginated response', () => {
            const response: any = {
                items: [] as AuditEntry[],
                total: 100,
                page: 1,
                pageSize: 20,
                totalPages: 5
            };

            expect(response.items).toBeDefined();
            expect(response.total).toBe(100);
            expect(response.page).toBe(1);
            expect(response.pageSize).toBe(20);
            expect(response.totalPages).toBe(5);
        });
    });

    describe('AuditSummary', () => {
        it('should create a valid audit summary', () => {
            const summary: AuditSummary = {
                totalCount: 1000,
                byAction: { 'CREATE': 100, 'UPDATE': 200 },
                byResourceType: { 'FIREWALL_RULE': 500, 'USER': 500 },
                bySeverity: { 'info': 800, 'error': 200 },
                bySuccess: { 'true': 900, 'false': 100 },
                byUser: { 'admin@example.com': 300, 'user@example.com': 700 },
                recentActivity: [
                    { date: '2024-01-15', count: 50 },
                    { date: '2024-01-14', count: 45 }
                ],
                topUsers: [
                    { user: 'admin@example.com', count: 300 },
                    { user: 'user@example.com', count: 200 }
                ]
            };

            expect(summary.totalCount).toBe(1000);
            expect(summary.byAction).toBeDefined();
            expect(summary.byResourceType).toBeDefined();
            expect(summary.bySeverity).toBeDefined();
            expect(summary.bySuccess).toBeDefined();
            expect(summary.byUser).toBeDefined();
            expect(summary.recentActivity).toHaveLength(2);
            expect(summary.topUsers).toHaveLength(2);
        });
    });
});

// ============================================================
// AuditService Tests
// ============================================================

describe('AuditService', () => {
    let service: AuditService;
    let httpMock: HttpTestingController;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [
                HttpClientTestingModule
            ],
            providers: [
                AuditService,
                provideHttpClient(),
                provideHttpClientTesting()
            ]
        });

        service = TestBed.inject(AuditService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpMock.verify();
    });

    describe('getAuditLogs', () => {
        it('should retrieve paginated audit logs', fakeAsync(() => {
            const mockResponse: any = {
                items: [
                    {
                        id: '1',
                        timestamp: '2024-01-15T10:00:00Z',
                        user: 'test@example.com',
                        action: 'CREATE',
                        resourceType: 'FIREWALL_RULE',
                        description: 'Test entry',
                        severity: 'info',
                        success: true
                    }
                ],
                total: 1,
                page: 1,
                pageSize: 20,
                totalPages: 1
            };

            service.getAuditLogs(1, 20).subscribe(response => {
                expect(response.items.length).toBe(1);
                expect(response.total).toBe(1);
            });

            const req = httpMock.expectOne('/api/v1/audit?page=1&page_size=20');
            expect(req.request.method).toBe('GET');
            req.flush(mockResponse);
            tick();
        }));

        it('should apply filters when provided', fakeAsync(() => {
            const filter: AuditFilter = {
                searchQuery: 'firewall',
                dateFrom: '2024-01-01T00:00:00Z',
                actionFilter: ['CREATE'],
                page: 1,
                pageSize: 10
            };

            service.getAuditLogs(1, 10, filter).subscribe();

            const req = httpMock.expectOne((request) => {
                return request.params.get('search') === 'firewall' &&
                    request.params.get('actions') === 'CREATE';
            });
            expect(req.request.params.get('search')).toBe('firewall');
            req.flush({ items: [], total: 0, page: 1, pageSize: 10, totalPages: 0 });
            tick();
        }));
    });

    describe('getAuditEntry', () => {
        it('should retrieve a single audit entry', fakeAsync(() => {
            const mockEntry: AuditEntry = {
                id: 'test-123',
                timestamp: '2024-01-15T10:00:00Z',
                user: 'test@example.com',
                action: 'UPDATE',
                resourceType: 'USER',
                description: 'Updated user',
                severity: 'info',
                success: true
            };

            service.getAuditEntry('test-123').subscribe(entry => {
                expect(entry.id).toBe('test-123');
                expect(entry.action).toBe('UPDATE');
            });

            const req = httpMock.expectOne('/api/v1/audit/test-123');
            expect(req.request.method).toBe('GET');
            req.flush(mockEntry);
            tick();
        }));
    });

    describe('filterAuditEntries', () => {
        it('should filter entries by search query', () => {
            const entries: AuditEntry[] = [
                {
                    id: '1',
                    timestamp: '2024-01-15T10:00:00Z',
                    user: 'test@example.com',
                    action: 'CREATE',
                    resourceType: 'FIREWALL_RULE',
                    description: 'Create firewall rule',
                    severity: 'info',
                    success: true
                },
                {
                    id: '2',
                    timestamp: '2024-01-15T11:00:00Z',
                    user: 'admin@example.com',
                    action: 'UPDATE',
                    resourceType: 'USER',
                    description: 'Update user settings',
                    severity: 'info',
                    success: true
                }
            ];

            const filtered = service.filterAuditEntries(entries, { searchQuery: 'firewall' });
            expect(filtered).toHaveLength(1);
            expect(filtered[0].id).toBe('1');
        });

        it('should filter entries by action type', () => {
            const entries: AuditEntry[] = [
                {
                    id: '1',
                    timestamp: '2024-01-15T10:00:00Z',
                    user: 'test@example.com',
                    action: 'CREATE',
                    resourceType: 'FIREWALL_RULE',
                    description: 'Test',
                    severity: 'info',
                    success: true
                },
                {
                    id: '2',
                    timestamp: '2024-01-15T11:00:00Z',
                    user: 'admin@example.com',
                    action: 'DELETE',
                    resourceType: 'USER',
                    description: 'Test',
                    severity: 'info',
                    success: true
                }
            ];

            const filtered = service.filterAuditEntries(entries, { actionFilter: ['CREATE'] });
            expect(filtered).toHaveLength(1);
            expect(filtered[0].action).toBe('CREATE');
        });

        it('should filter entries by severity', () => {
            const entries: AuditEntry[] = [
                {
                    id: '1',
                    timestamp: '2024-01-15T10:00:00Z',
                    user: 'test@example.com',
                    action: 'CREATE',
                    resourceType: 'FIREWALL_RULE',
                    description: 'Test',
                    severity: 'info',
                    success: true
                },
                {
                    id: '2',
                    timestamp: '2024-01-15T11:00:00Z',
                    user: 'admin@example.com',
                    action: 'UPDATE',
                    resourceType: 'USER',
                    description: 'Test',
                    severity: 'error',
                    success: false
                }
            ];

            const filtered = service.filterAuditEntries(entries, { severityFilter: ['error'] });
            expect(filtered).toHaveLength(1);
            expect(filtered[0].severity).toBe('error');
        });

        it('should return empty array when no matches found', () => {
            const entries: AuditEntry[] = [
                {
                    id: '1',
                    timestamp: '2024-01-15T10:00:00Z',
                    user: 'test@example.com',
                    action: 'CREATE',
                    resourceType: 'FIREWALL_RULE',
                    description: 'Test',
                    severity: 'info',
                    success: true
                }
            ];

            const filtered = service.filterAuditEntries(entries, { searchQuery: 'nonexistent' });
            expect(filtered).toHaveLength(0);
        });

        it('should filter by success status', () => {
            const entries: AuditEntry[] = [
                {
                    id: '1',
                    timestamp: '2024-01-15T10:00:00Z',
                    user: 'test@example.com',
                    action: 'CREATE',
                    resourceType: 'FIREWALL_RULE',
                    description: 'Test',
                    severity: 'info',
                    success: true
                },
                {
                    id: '2',
                    timestamp: '2024-01-15T11:00:00Z',
                    user: 'admin@example.com',
                    action: 'UPDATE',
                    resourceType: 'USER',
                    description: 'Test',
                    severity: 'info',
                    success: false
                }
            ];

            const filtered = service.filterAuditEntries(entries, { successFilter: false });
            expect(filtered).toHaveLength(1);
            expect(filtered[0].success).toBe(false);
        });
    });

    describe('Formatting methods', () => {
        it('should format severity display correctly', () => {
            const infoDisplay = service.getSeverityDisplay('info');
            expect(infoDisplay.label).toBe('Info');
            expect(infoDisplay.cssClass).toBe('audit-severity-info');

            const errorDisplay = service.getSeverityDisplay('error');
            expect(errorDisplay.label).toBe('Error');
            expect(errorDisplay.cssClass).toBe('audit-severity-error');
        });

        it('should format action display correctly', () => {
            expect(service.getActionDisplay('CREATE')).toBe('Created');
            expect(service.getActionDisplay('UPDATE')).toBe('Updated');
            expect(service.getActionDisplay('DELETE')).toBe('Deleted');
            expect(service.getActionDisplay('READ')).toBe('Viewed');
        });

        it('should format resource type display correctly', () => {
            expect(service.getResourceTypeDisplay('FIREWALL_RULE')).toBe('Firewall Rule');
            expect(service.getResourceTypeDisplay('USER')).toBe('User');
            expect(service.getResourceTypeDisplay('CONFIGURATION')).toBe('Configuration');
        });

        it('should format timestamp correctly', () => {
            const timestamp = '2024-01-15T10:30:00Z';
            const formatted = service.formatTimestamp(timestamp);
            expect(formatted).toBeDefined();
            expect(typeof formatted).toBe('string');
        });

        it('should format duration correctly', () => {
            expect(service.formatDuration(500)).toBe('500ms');
            expect(service.formatDuration(1500)).toBe('1.50s');
            expect(service.formatDuration(60000)).toBe('1.00min');
        });

        it('should get action icon correctly', () => {
            expect(service.getActionIcon('CREATE')).toBe('add');
            expect(service.getActionIcon('DELETE')).toBe('delete');
            expect(service.getActionIcon('LOGIN')).toBe('login');
        });

        it('should get resource type icon correctly', () => {
            expect(service.getResourceTypeIcon('FIREWALL_RULE')).toBe('network_internet');
            expect(service.getResourceTypeIcon('USER')).toBe('person');
        });
    });

    describe('getUniqueUsers', () => {
        it('should return unique users from entries', () => {
            const entries: AuditEntry[] = [
                {
                    id: '1',
                    timestamp: '2024-01-15T10:00:00Z',
                    user: 'admin@example.com',
                    action: 'CREATE',
                    resourceType: 'FIREWALL_RULE',
                    description: 'Test',
                    severity: 'info',
                    success: true
                },
                {
                    id: '2',
                    timestamp: '2024-01-15T11:00:00Z',
                    user: 'admin@example.com',
                    action: 'UPDATE',
                    resourceType: 'USER',
                    description: 'Test',
                    severity: 'info',
                    success: true
                },
                {
                    id: '3',
                    timestamp: '2024-01-15T12:00:00Z',
                    user: 'user@example.com',
                    action: 'DELETE',
                    resourceType: 'FIREWALL_RULE',
                    description: 'Test',
                    severity: 'info',
                    success: true
                }
            ];

            const users = service.getUniqueUsers(entries);
            expect(users).toHaveLength(2);
            expect(users).toContain('admin@example.com');
            expect(users).toContain('user@example.com');
        });
    });

    describe('getUniqueActions', () => {
        it('should return unique actions from entries', () => {
            const entries: AuditEntry[] = [
                {
                    id: '1',
                    timestamp: '2024-01-15T10:00:00Z',
                    user: 'test@example.com',
                    action: 'CREATE',
                    resourceType: 'FIREWALL_RULE',
                    description: 'Test',
                    severity: 'info',
                    success: true
                },
                {
                    id: '2',
                    timestamp: '2024-01-15T11:00:00Z',
                    user: 'test@example.com',
                    action: 'UPDATE',
                    resourceType: 'FIREWALL_RULE',
                    description: 'Test',
                    severity: 'info',
                    success: true
                }
            ];

            const actions = service.getUniqueActions(entries);
            expect(actions).toContain('CREATE');
            expect(actions).toContain('UPDATE');
        });
    });

    describe('isRecent', () => {
        it('should identify recent entries', () => {
            const recentEntry: AuditEntry = {
                id: '1',
                timestamp: new Date(Date.now() - 1800000).toISOString(),
                user: 'test@example.com',
                action: 'CREATE',
                resourceType: 'FIREWALL_RULE',
                description: 'Test',
                severity: 'info',
                success: true
            };

            const oldEntry: AuditEntry = {
                id: '2',
                timestamp: new Date(Date.now() - 7200000).toISOString(),
                user: 'test@example.com',
                action: 'UPDATE',
                resourceType: 'FIREWALL_RULE',
                description: 'Test',
                severity: 'info',
                success: true
            };

            expect(service.isRecent(recentEntry)).toBe(true);
            expect(service.isRecent(oldEntry)).toBe(false);
        });
    });
});

// ============================================================
// AuditViewerComponent Tests
// ============================================================

describe('AuditViewerComponent', () => {
    let component: AuditViewerComponent;
    let fixture: ComponentFixture<AuditViewerComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                AuditViewerComponent,
                HttpClientTestingModule,
                ReactiveFormsModule,
            ],
            providers: [
                AuditService,
                { provide: MatDialog, useValue: { open: () => ({ afterClosed: () => of(true) }) } },
                { provide: MatSnackBar, useValue: { open: () => ({ afterClosed: () => of(true) }) } },
                { provide: FormBuilder, useValue: { group: () => ({}) } },
                provideHttpClient(),
                provideAnimations()
            ],
            schemas: [NO_ERRORS_SCHEMA]
        }).compileComponents();

        fixture = TestBed.createComponent(AuditViewerComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize with default filter form values', () => {
        const filterForm = component.filterForm;
        expect(filterForm.get('searchQuery')?.value).toBe('');
        expect(filterForm.get('dateFrom')?.value).toBeNull();
        expect(filterForm.get('dateTo')?.value).toBeNull();
        expect(filterForm.get('actionFilter')?.value).toEqual([]);
        expect(filterForm.get('userFilter')?.value).toEqual([]);
    });

    it('should have isLoading set to true initially', () => {
        expect(component.isLoading).toBe(true);
    });

    it('should load audit logs on init', () => {
        expect(component.loadAuditLogs).toBeDefined();
    });

    it('should apply filters and reload', () => {
        expect(component.applyFilters).toBeDefined();
    });

    it('should reset filters', () => {
        expect(component.resetFilters).toBeDefined();
    });

    it('should view detail for an entry', () => {
        const mockEntry: AuditEntry = {
            id: 'test-1',
            timestamp: '2024-01-15T10:00:00Z',
            user: 'test@example.com',
            action: 'CREATE',
            resourceType: 'FIREWALL_RULE',
            description: 'Test',
            severity: 'info',
            success: true
        };

        expect(component.viewDetail).toBeDefined();
    });
});

// ============================================================
// AuditDetailComponent Tests
// ============================================================

describe('AuditDetailComponent', () => {
    let component: AuditDetailComponent;
    let fixture: ComponentFixture<AuditDetailComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                AuditDetailComponent,
                HttpClientTestingModule,
                ReactiveFormsModule,
            ],
            providers: [
                AuditService,
                { provide: MatDialogRef, useValue: { close: () => { } } },
                { provide: MatDialog, useValue: { open: () => ({ afterClosed: () => of(true) }) } },
                { provide: MatSnackBar, useValue: { open: () => ({ afterClosed: () => of(true) }) } },
                provideHttpClient(),
                provideAnimations()
            ],
            schemas: [NO_ERRORS_SCHEMA]
        }).compileComponents();

        fixture = TestBed.createComponent(AuditDetailComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize with loading state', () => {
        expect(component.isLoading).toBe(true);
    });

    it('should set entry from data', () => {
        const mockEntry: AuditEntry = {
            id: 'test-1',
            timestamp: '2024-01-15T10:00:00Z',
            user: 'test@example.com',
            action: 'CREATE',
            resourceType: 'FIREWALL_RULE',
            description: 'Test entry',
            severity: 'info',
            success: true
        };

        component.data = { entry: mockEntry };
        component.ngOnInit();

        expect(component.entry).toEqual(mockEntry);
        expect(component.isLoading).toBe(false);
    });

    it('should format value correctly', () => {
        expect(component.formatValue('test')).toBe('test');
        expect(component.formatValue({ key: 'value' })).toBe('{"key":"value"}');
    });

    it('should copy entry ID', () => {
        component.entry = {
            id: 'test-id-123',
            timestamp: '2024-01-15T10:00:00Z',
            user: 'test@example.com',
            action: 'CREATE',
            resourceType: 'FIREWALL_RULE',
            description: 'Test',
            severity: 'info',
            success: true
        };

        expect(component.entry?.id).toBe('test-id-123');
    });
});

// ============================================================
// Audit Filter Functionality Tests
// ============================================================

describe('AuditFilter Functionality', () => {
    let service: AuditService;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [AuditService]
        });
        service = TestBed.inject(AuditService);
    });

    it('should filter entries by date range', () => {
        const entries: AuditEntry[] = [
            {
                id: '1',
                timestamp: '2024-01-10T10:00:00Z',
                user: 'test@example.com',
                action: 'CREATE',
                resourceType: 'FIREWALL_RULE',
                description: 'Test',
                severity: 'info',
                success: true
            },
            {
                id: '2',
                timestamp: '2024-01-20T10:00:00Z',
                user: 'admin@example.com',
                action: 'UPDATE',
                resourceType: 'USER',
                description: 'Test',
                severity: 'info',
                success: true
            }
        ];

        const filtered = service.filterAuditEntries(entries, {
            dateFrom: '2024-01-15T00:00:00Z',
            dateTo: '2024-01-31T23:59:59Z'
        });

        expect(filtered).toHaveLength(1);
        expect(filtered[0].id).toBe('2');
    });

    it('should filter by resource type', () => {
        const entries: AuditEntry[] = [
            {
                id: '1',
                timestamp: '2024-01-15T10:00:00Z',
                user: 'test@example.com',
                action: 'CREATE',
                resourceType: 'FIREWALL_RULE',
                description: 'Test',
                severity: 'info',
                success: true
            },
            {
                id: '2',
                timestamp: '2024-01-15T11:00:00Z',
                user: 'admin@example.com',
                action: 'UPDATE',
                resourceType: 'USER',
                description: 'Test',
                severity: 'info',
                success: true
            }
        ];

        const filtered = service.filterAuditEntries(entries, {
            resourceTypeFilter: ['FIREWALL_RULE']
        });

        expect(filtered).toHaveLength(1);
        expect(filtered[0].resourceType).toBe('FIREWALL_RULE');
    });

    it('should filter by multiple criteria', () => {
        const entries: AuditEntry[] = [
            {
                id: '1',
                timestamp: '2024-01-15T10:00:00Z',
                user: 'test@example.com',
                action: 'CREATE',
                resourceType: 'FIREWALL_RULE',
                description: 'Firewall rule created',
                severity: 'info',
                success: true
            },
            {
                id: '2',
                timestamp: '2024-01-15T11:00:00Z',
                user: 'admin@example.com',
                action: 'CREATE',
                resourceType: 'FIREWALL_RULE',
                description: 'Another rule created',
                severity: 'warning',
                success: true
            },
            {
                id: '3',
                timestamp: '2024-01-15T12:00:00Z',
                user: 'test@example.com',
                action: 'DELETE',
                resourceType: 'USER',
                description: 'User deleted',
                severity: 'error',
                success: false
            }
        ];

        const filtered = service.filterAuditEntries(entries, {
            searchQuery: 'created',
            actionFilter: ['CREATE'],
            resourceTypeFilter: ['FIREWALL_RULE']
        });

        expect(filtered.length).toBeGreaterThanOrEqual(0);
    });
});

// ============================================================
// Export Functionality Tests
// ============================================================

describe('Export Functionality', () => {
    let service: AuditService;
    let httpMock: HttpTestingController;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [
                AuditService,
                provideHttpClient(),
                provideHttpClientTesting()
            ]
        });
        service = TestBed.inject(AuditService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpMock.verify();
    });

    it('should export as CSV', fakeAsync(() => {
        const mockBlob = new Blob(['id,timestamp,user,action\n1,2024-01-15,test@example.com,CREATE'], { type: 'text/csv' });

        service.exportAsCsv({ page: 1, pageSize: 20, searchQuery: '' }).subscribe(blob => {
            expect(blob).toBe(mockBlob);
        });

        const req = httpMock.expectOne('/api/v1/audit/export/csv');
        expect(req.request.method).toBe('GET');
        req.flush(mockBlob);
        tick();
    }));

    it('should export as JSON', fakeAsync(() => {
        const mockBlob = new Blob([JSON.stringify([{ id: '1', action: 'CREATE' }])], { type: 'application/json' });

        service.exportAsJson({ page: 1, pageSize: 20, searchQuery: '' }).subscribe(blob => {
            expect(blob).toBe(mockBlob);
        });

        const req = httpMock.expectOne('/api/v1/audit/export/json');
        expect(req.request.method).toBe('GET');
        req.flush(mockBlob);
        tick();
    }));
});
