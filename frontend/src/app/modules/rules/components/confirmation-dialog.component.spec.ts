import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { ConfirmationDialogComponent } from './confirmation-dialog.component';

describe('ConfirmationDialogComponent', () => {
    let component: ConfirmationDialogComponent;
    let fixture: ComponentFixture<ConfirmationDialogComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                ConfirmationDialogComponent,
                MatDialogModule,
                MatButtonModule
            ],
            providers: [
                {
                    provide: MatDialogRef,
                    useValue: { close: () => { } }
                },
                {
                    provide: MAT_DIALOG_DATA,
                    useValue: { title: 'Test Title', message: 'Test Message', type: 'warn' }
                }
            ]
        }).compileComponents();
    });

    beforeEach(() => {
        fixture = TestBed.createComponent(ConfirmationDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should have correct title', () => {
        expect(component.title).toBe('Test Title');
    });

    it('should have correct message', () => {
        expect(component.message).toBe('Test Message');
    });

    it('should close with true when confirm is called', () => {
        const spy = jest.spyOn((component as any).dialogRef, 'close');
        component.onConfirm();
        expect(spy).toHaveBeenCalledWith(true);
    });

    it('should close with false when cancel is called', () => {
        const spy = jest.spyOn((component as any).dialogRef, 'close');
        component.onCancel();
        expect(spy).toHaveBeenCalledWith(false);
    });
});