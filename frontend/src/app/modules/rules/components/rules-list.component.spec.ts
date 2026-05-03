import { ComponentFixture, TestBed, fakeAsync, tick, flush } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { RulesListComponent } from './rules-list.component';
import { RulesService, FirewallRule } from '../services/rules.service';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { of, throwError } from 'rxjs';

describe('RulesListComponent', () => {
    let component: RulesListComponent;
    let fixture: ComponentFixture<RulesListComponent>;
    let rulesService: RulesService;

    const mockRules: FirewallRule[] = [
        {
            id: 'rule-1',
            rule_collection_name: 'Test Rule 1',
            priority: 100,
            action: 'Allow',
            protocol: 'Tcp',
            source_addresses: ['10.0.0.0/24'],
            destination_fqdns: ['example.com'],
            description: 'Test rule description',
            status: 'active',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z'
        },
        {
            id: 'rule-2',
            rule_collection_name: 'Test Rule 2',
            priority: 200,
            action: 'Deny',
            protocol: 'Udp',
            description: 'Another test rule',
            status: 'pending',
            created_at: '2024-01-02T00:00:00Z',
            updated_at: '2024-01-02T00:00:00Z'
        }
    ];

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                RulesListComponent,
                MatDialogModule,
                MatSnackBarModule,
                HttpClientTestingModule
            ],
            providers: [
                provideNoopAnimations(),
                {
                    provide: RulesService,
                    useValue: {
                        getRules: () => of({
                            items: mockRules,
                            total: 2,
                            page: 1,
                            pageSize: 50,
                            totalPages: 1
                        }),
                        createRule: () => of(mockRules[0]),
                        updateRule: () => of(mockRules[0]),
                        deleteRule: () => of(undefined),
                        bulkDelete: () => of({ success: 2, failed: 0, errors: [] }),
                        bulkEnable: () => of({ success: 1, failed: 0, errors: [] }),
                        bulkDisable: () => of({ success: 1, failed: 0, errors: [] })
                    }
                },
                { provide: MatDialog, useValue: { open: () => ({ afterClosed: () => of(true) }) } },
                { provide: MatSnackBar, useValue: { open: () => ({ onClose: () => { } } as any) } }
            ]
        }).compileComponents();
    });

    beforeEach(() => {
        fixture = TestBed.createComponent(RulesListComponent);
        component = fixture.componentInstance;
        rulesService = TestBed.inject(RulesService);
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load rules on init', () => {
        expect(component.dataSource.data.length).toBeGreaterThan(0);
    });

    it('should have selectedRows initialized as empty map', () => {
        expect(component.selectedRows.size).toBe(0);
    });

    it('should filter rules by search filter', () => {
        component.currentFilters.searchQuery = 'Rule 1';
        component.applyFilters();
        const filtered = component.dataSource.filteredData;
        expect(filtered?.length).toBe(1);
        expect(filtered?.[0].rule_collection_name).toBe('Test Rule 1');
    });

    it('should select/deselect a rule', () => {
        component.toggleRowSelection(mockRules[0]);
        expect(component.selectedRows.has(mockRules[0])).toBe(true);

        component.toggleRowSelection(mockRules[0]);
        expect(component.selectedRows.has(mockRules[0])).toBe(false);
    });

    it('should select all visible rules', () => {
        component.dataSource.data = mockRules;
        component.toggleAllRows();
        expect(component.selectedRows.size).toBeGreaterThan(0);
    });

    it('should open create dialog', () => {
        const dialogInstance = TestBed.inject(MatDialog);
        const dialogSpy = jest.spyOn(dialogInstance, 'open');
        component.openCreateDialog();
        expect(dialogSpy).toHaveBeenCalled();
    });

    it('should filter by status correctly', () => {
        component.currentFilters.statusFilter = 'active';
        component.applyFilters();
        const filtered = component.dataSource.filteredData;
        if (filtered && filtered.length > 0) {
            expect(filtered.every((r: FirewallRule) => r.status === 'active')).toBe(true);
        }
    });

    it('should reset filters to default values', () => {
        component.currentFilters.statusFilter = 'active';
        component.resetFilters();
        expect(component.currentFilters.statusFilter).toBe('');
    });

    it('should toggle filter panel visibility', fakeAsync(() => {
        component.showFilters = false;
        component.toggleFilters();
        expect(component.showFilters).toBe(true);
        tick();
    }));

    it('should report hasSelection returns false initially', () => {
        expect(component.hasSelection()).toBe(false);
    });

    it('should clear selection', () => {
        component.toggleRowSelection(mockRules[0]);
        component.clearSelection();
        expect(component.selectedRows.size).toBe(0);
    });

    it('should report isAllSelected returns false when no data', () => {
        component.dataSource.data = [];
        expect(component.isAllSelected()).toBe(false);
    });
});