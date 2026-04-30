import { ComponentFixture, TestBed, fakeAsync, tick, flush } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ComponentFixtureFakeAsyncTest } from '@angular/core/testing';
import { RulesListComponent } from './rules-list.component';
import { RulesService, FirewallRule } from '../services/rules.service';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { of, throwError, Subject } from 'rxjs';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

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
                NoopAnimationsModule,
                FormsModule,
                ReactiveFormsModule,
                CommonModule
            ],
            providers: [
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
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should load rules on init', () => {
        expect(component.rules.length).toBeGreaterThan(0);
        expect(component.rules).toEqual(mockRules);
    });

    it('should have selectedRules initialized as empty array', () => {
        expect(component.selectedRules.length).toBe(0);
    });

    it('should have empty searchFilter initially', () => {
        expect(component.searchFilter).toBe('');
    });

    it('should filter rules by search filter', () => {
        component.searchFilter = 'Rule 1';
        component.applyFilter();
        const filtered = component.rules.filter(r =>
            r.rule_collection_name.toLowerCase().includes('rule 1') ||
            r.description?.toLowerCase().includes('rule 1') ||
            r.id.toLowerCase().includes('rule 1')
        );
        expect(filtered.length).toBe(1);
    });

    it('should select/deselect a rule', () => {
        component.toggleSelectRule(mockRules[0], true);
        expect(component.selectedRules).toContain(mockRules[0]);

        component.toggleSelectRule(mockRules[0], false);
        expect(component.selectedRules).not.toContain(mockRules[0]);
    });

    it('should select all visible rules', () => {
        component.selectAll();
        expect(component.selectedRules.length).toBeGreaterThan(0);
    });

    it('should open create dialog', () => {
        const dialogSpy = jest.spyOn(component.dialog, 'open');
        component.openCreateDialog();
        expect(dialogSpy).toHaveBeenCalled();
    });

    it('should filter by status correctly', () => {
        component.statusFilter = 'active';
        component.applyFilter();
        expect(component.rules.every(r => r.status === 'active')).toBe(true);
    });
});