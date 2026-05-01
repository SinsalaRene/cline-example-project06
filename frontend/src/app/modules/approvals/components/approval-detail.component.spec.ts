import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ApprovalDetailComponent } from './approval-detail.component';
import { ApprovalsService } from '../services/approvals.service';
import { ApprovalRequest } from '../models/approval.model';

describe('ApprovalDetailComponent', () => {
    let component: ApprovalDetailComponent;
    let fixture: ComponentFixture<ApprovalDetailComponent>;
    let service: ApprovalsService;

    const mockApproval: ApprovalRequest = {
        id: '1',
        rule_name: 'Test Rule',
        rule_id: 'rule-123',
        requestor: 'John Doe',
        request_type: 'create',
        status: 'pending',
        requested_at: '2024-01-01T10:00:00Z',
        priority: 'high',
        comments: [],
        metadata: { rule_changes: { field: 'test_field' } }
    };

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                ReactiveFormsModule,
                MatDialogModule,
                MatSnackBarModule,
                NoopAnimationsModule
            ],
            providers: [
                { provide: ApprovalDetailComponent, useValue: {} },
                { provide: MatDialogRef, useValue: {} },
                ApprovalsService,
                MatSnackBar
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(ApprovalDetailComponent);
        component = fixture.componentInstance;
        service = TestBed.inject(ApprovalsService);
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize with approval data', () => {
        component.ngOnInit();
        expect(component.isLoading).toBe(false);
    });

    it('should format value as JSON string', () => {
        const obj = { key: 'value' };
        const result = component.formatValue(obj);
        expect(result).toBe(JSON.stringify(obj, null, 2));
    });

    it('should return string value as-is', () => {
        const result = component.formatValue('test string');
        expect(result).toBe('test string');
    });

    it('should get initials from name', () => {
        const result = component.getInitials('John Doe');
        expect(result).toBe('J');
    });

    it('should return false for isExpired when approval is not set', () => {
        component.approval = null;
        const result = component.isExpired();
        expect(result).toBe(false);
    });
});