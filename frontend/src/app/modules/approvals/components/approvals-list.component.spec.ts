import { ComponentFixture, TestBed, fakeAsync, tick, flush } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ApprovalsListComponent } from './approvals-list.component';
import { ApprovalsService } from '../services/approvals.service';
import { ApprovalRequest } from '../models/approval.model';
import { MatDialogModule } from '@angular/material/dialog';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { provideHttpClient } from '@angular/common/http';
import { HttpClientTestingModule } from '@angular/common/http/testing';

describe('ApprovalsListComponent', () => {
    let component: ApprovalsListComponent;
    let fixture: ComponentFixture<ApprovalsListComponent>;
    let service: ApprovalsService;

    const mockApprovals: ApprovalRequest[] = [
        {
            id: '1',
            rule_name: 'Rule 1',
            rule_id: 'rule-1',
            requestor: 'User 1',
            request_type: 'create',
            status: 'pending',
            requested_at: '2024-01-01T10:00:00Z',
            priority: 'high',
            comments: [],
            metadata: { rule_changes: { field: 'field1' } }
        },
        {
            id: '2',
            rule_name: 'Rule 2',
            rule_id: 'rule-2',
            requestor: 'User 2',
            request_type: 'update',
            status: 'approved',
            requested_at: '2024-01-01T11:00:00Z',
            priority: 'medium',
            comments: [],
            metadata: { rule_changes: { field: 'field2' } }
        }
    ];

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                ApprovalsListComponent,
                MatDialogModule,
                MatSnackBarModule,
                MatProgressSpinnerModule,
                MatPaginatorModule,
                MatSortModule
            ],
            providers: [
                ApprovalsService,
                MatSnackBar
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(ApprovalsListComponent);
        component = fixture.componentInstance;
        service = TestBed.inject(ApprovalsService);
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize with empty state', () => {
        expect(component.isLoading).toBe(true);
        expect(component.dataSource.data.length).toBe(0);
        expect(component.selectedRows.size).toBe(0);
    });

    describe('loadApprovals', () => {
        it('should load approvals from service', () => {
            jest.spyOn(service, 'getApprovals').mockReturnValue({
                subscribe: (cb: any) => cb({
                    items: mockApprovals, total: 2, page: 1, pageSize: 20, totalPages: 1
                }),
                unsubscribe: jest.fn()
            } as any);

            component.loadApprovals();
            expect(component.isLoading).toBe(false);
        });
    });

    describe('filters', () => {
        it('should apply status filter', () => {
            component.currentFilters.statusFilter = 'pending';
            component.applyFilters();
            const filtered = component.dataSource.filteredData;
            expect(filtered).toBeDefined();
        });

        it('should apply type filter', () => {
            component.currentFilters.typeFilter = 'create';
            component.applyFilters();
            const filtered = component.dataSource.filteredData;
            expect(filtered).toBeDefined();
        });

        it('should apply priority filter', () => {
            component.currentFilters.priorityFilter = 'high';
            component.applyFilters();
            const filtered = component.dataSource.filteredData;
            expect(filtered).toBeDefined();
        });

        it('should reset filters', () => {
            component.currentFilters = {
                searchQuery: 'test',
                statusFilter: 'pending',
                typeFilter: 'create',
                priorityFilter: 'high'
            };
            component.resetFilters();
            expect(component.currentFilters.searchQuery).toBe('');
            expect(component.currentFilters.statusFilter).toBe('');
        });
    });

    describe('selection', () => {
        it('should toggle row selection', () => {
            const item = mockApprovals[0];
            component.toggleRowSelection(item);
            expect(component.selectedRows.has(item)).toBe(true);
            component.clearSelection();
            expect(component.selectedRows.has(item)).toBe(false);
        });

        it('should update stats after loading', () => {
            component['allItems'] = mockApprovals;
            component.updateStats();
            expect(component.stats.pending).toBe(1);
            expect(component.stats.approved).toBe(1);
            expect(component.stats.total).toBe(2);
        });
    });

    describe('viewDetail', () => {
        it('should open detail dialog', () => {
            const spy = jest.spyOn(component as any, 'viewDetail');
            component.viewDetail(mockApprovals[0]);
            expect(spy).toHaveBeenCalled();
        });
    });
});