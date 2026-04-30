import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { RuleDetailComponent } from './rule-detail.component';
import { RulesService, FirewallRule } from '../services/rules.service';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('RuleDetailComponent', () => {
    let component: RuleDetailComponent;
    let fixture: ComponentFixture<RuleDetailComponent>;

    const mockRule: FirewallRule = {
        id: 'rule-1',
        rule_collection_name: 'Test Rule',
        priority: 100,
        action: 'Allow',
        protocol: 'Tcp',
        source_addresses: ['10.0.0.0/24'],
        destination_fqdns: ['example.com'],
        source_ip_groups: [],
        destination_ports: [443],
        description: 'Test rule description',
        status: 'active',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
    };

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                RuleDetailComponent,
                MatDialogModule,
                MatSnackBarModule,
                NoopAnimationsModule
            ],
            providers: [
                {
                    provide: MatDialogRef,
                    useValue: { close: () => { } }
                },
                {
                    provide: MAT_DIALOG_DATA,
                    useValue: { rule: mockRule }
                },
                {
                    provide: RulesService,
                    useValue: {}
                },
                {
                    provide: MatSnackBar,
                    useValue: { open: () => ({ onClose: () => { } } as any) }
                }
            ]
        }).compileComponents();
    });

    beforeEach(() => {
        fixture = TestBed.createComponent(RuleDetailComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should close dialog when onClose is called', () => {
        const spy = jest.spyOn(component.dialogRef, 'close');
        component.onClose();
        expect(spy).toHaveBeenCalled();
    });

    it('should return rule data when onEdit is called', () => {
        const result = component.onEdit();
        // Dialog closes with the rule data
        expect(component.dialogRef.close).toHaveBeenCalledWith({ edit: mockRule });
    });
});