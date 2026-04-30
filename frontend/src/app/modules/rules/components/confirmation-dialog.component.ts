import { Component, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';

export interface ConfirmationDialogData {
  title: string;
  message: string;
  confirmLabel: string;
  type?: 'primary' | 'warn' | 'accent';
}

@Component({
  selector: 'app-confirmation-dialog',
  standalone: true,
  imports: [MatDialogModule, MatButtonModule, MatIconModule, CommonModule],
  template: `
    <div class="confirmation-dialog">
      <h2 mat-dialog-title>{{ data.title }}</h2>
      <mat-dialog-content>
        <mat-icon class="confirmation-icon" *ngIf="data.type === 'warn'">warning</mat-icon>
        <mat-icon class="confirmation-icon" *ngIf="data.type === 'primary'">info</mat-icon>
        <p>{{ data.message }}</p>
      </mat-dialog-content>
      <mat-dialog-actions class="confirm-actions">
        <button mat-button (click)="onCancel()">Cancel</button>
        <button 
          mat-raised-button 
          [color]="data.type || 'primary'" 
          (click)="onConfirm()"
        >
          {{ data.confirmLabel }}
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [`
    .confirmation-dialog {
      min-width: 400px;
    }
    
    @media (max-width: 600px) {
      .confirmation-dialog {
        min-width: 300px;
      }
    }
    
    mat-dialog-content {
      min-width: 400px;
    }
    
    .confirmation-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
      margin-bottom: 16px;
    }
    
    .confirmation-icon.warn {
      color: #f44336;
    }
    
    .confirm-actions {
      justify-content: flex-end;
      padding: 0 24px 16px;
    }
  `]
})
export class ConfirmationDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<ConfirmationDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConfirmationDialogData
  ) { }

  onConfirm(): void {
    this.dialogRef.close(true);
  }

  onCancel(): void {
    this.dialogRef.close(false);
  }
}