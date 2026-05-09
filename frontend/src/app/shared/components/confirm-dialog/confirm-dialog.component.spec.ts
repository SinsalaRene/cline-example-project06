import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { MatDialogModule, MatDialog, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { ConfirmDialogComponent, ConfirmDialogData, openConfirmDialog } from './confirm-dialog.component';
import { Observable, of } from 'rxjs';

describe('ConfirmDialogComponent', () => {
    let component: ConfirmDialogComponent;
    let fixture: ComponentFixture<ConfirmDialogComponent>;

    const mockData: ConfirmDialogData = {
        title: 'Delete Rule',
        message: 'Are you sure you want to delete this rule?',
        confirmText: 'Delete',
        cancelText: 'Cancel'
    };

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [
                ConfirmDialogComponent,
                MatDialogModule,
                MatButtonModule
            ],
            providers: [
                { provide: MAT_DIALOG_DATA, useValue: mockData }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(ConfirmDialogComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should have injected dialog data', () => {
        expect(component.data.title).toBe('Delete Rule');
        expect(component.data.message).toBe('Are you sure you want to delete this rule?');
        expect(component.data.confirmText).toBe('Delete');
        expect(component.data.cancelText).toBe('Cancel');
    });
});

describe('openConfirmDialog', () => {
    let dialog: MatDialog;

    const mockDialogData: ConfirmDialogData = {
        title: 'Confirm Delete',
        message: 'Are you sure?',
        confirmText: 'Delete',
        cancelText: 'Cancel'
    };

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [MatDialogModule, MatButtonModule, ConfirmDialogComponent],
            providers: [
                {
                    provide: MatDialogRef,
                    useValue: {
                        afterClosed: () => new Observable<boolean>(observer => {
                            setTimeout(() => observer.next(true), 10);
                            setTimeout(() => observer.complete(), 20);
                        })
                    }
                }
            ]
        }).compileComponents();

        dialog = TestBed.inject(MatDialog);
    });

    it('should open dialog with default confirm/cancel text', () => {
        const ref = openConfirmDialog(dialog, {
            title: 'Delete',
            message: 'Are you sure?'
        });
        expect(ref).toBeTruthy();
    });

    it('should open dialog with custom confirm/cancel text', () => {
        const ref = openConfirmDialog(dialog, {
            title: 'Delete',
            message: 'Are you sure?',
            confirmText: 'Remove',
            cancelText: 'Go Back'
        });
        expect(ref).toBeTruthy();
    });

    it('should emit true when user confirms', fakeAsync(() => {
        const ref = openConfirmDialog(dialog, {
            title: 'Delete',
            message: 'Are you sure?'
        });
        let result: boolean | undefined;
        ref.afterClosed().subscribe(r => result = r);

        // Simulate confirm
        ref.close(true);
        tick();

        expect(result).toBe(true);
    }));

    it('should emit false when user cancels', fakeAsync(() => {
        const ref = openConfirmDialog(dialog, {
            title: 'Delete',
            message: 'Are you sure?'
        });
        let result: boolean | undefined;
        ref.afterClosed().subscribe(r => result = r);

        // Simulate cancel
        ref.close(false);
        tick();

        expect(result).toBe(false);
    }));
});