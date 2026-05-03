import { Component, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { RulesService } from '../services/rules.service';

@Component({
  selector: 'app-rule-form-dialog',
  standalone: true,
  imports: [MatDialogModule, ReactiveFormsModule, MatInputModule, MatFormFieldModule, MatSelectModule, MatButtonModule],
  template: `
    <h2 mat-dialog-title>{{data.isEdit ? 'Edit' : 'Create'}} Firewall Rule</h2>
    <form [formGroup]="ruleForm" (ngSubmit)="onSubmit()">
      <mat-dialog-content>
        <mat-form-field appearance="fill" class="full-width">
          <mat-label>Rule Collection Name</mat-label>
          <input matInput formControlName="ruleCollectionName" required>
        </mat-form-field>

        <mat-form-field appearance="fill" class="full-width">
          <mat-label>Priority</mat-label>
          <input matInput type="number" formControlName="priority" required>
        </mat-form-field>

        <mat-form-field appearance="fill" class="full-width">
          <mat-label>Action</mat-label>
          <mat-select formControlName="action">
            <mat-option value="Allow">Allow</mat-option>
            <mat-option value="Deny">Deny</mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="fill" class="full-width">
          <mat-label>Protocol</mat-label>
          <mat-select formControlName="protocol">
            <mat-option value="Any">Any</mat-option>
            <mat-option value="Tcp">TCP</mat-option>
            <mat-option value="Udp">UDP</mat-option>
            <mat-option value="IpProtocol">IP Protocol</mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="fill" class="full-width">
          <mat-label>Description</mat-label>
          <textarea matInput formControlName="description" rows="3"></textarea>
        </mat-form-field>
      </mat-dialog-content>

      <mat-dialog-actions>
        <button mat-button type="button" (click)="onCancel()">Cancel</button>
        <button mat-raised-button color="primary" type="submit" [disabled]="ruleForm.invalid">
          {{data.isEdit ? 'Update' : 'Create'}}
        </button>
      </mat-dialog-actions>
    </form>
  `,
  styles: [`
    .full-width { width: 100%; margin-bottom: 16px; }
    mat-dialog-content { min-width: 400px; }
  `]
})
export class RuleFormDialogComponent {
  ruleForm: FormGroup;

  constructor(
    public dialogRef: MatDialogRef<RuleFormDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any,
    private fb: FormBuilder,
    private rulesService: RulesService
  ) {
    this.ruleForm = this.fb.group({
      ruleCollectionName: [data?.rule?.rule_collection_name || '', Validators.required],
      priority: [data?.rule?.priority || 100, [Validators.required, Validators.min(1)]],
      action: [data?.rule?.action || 'Deny', Validators.required],
      protocol: [data?.rule?.protocol || 'Any', Validators.required],
      description: [data?.rule?.description || '']
    });
  }

  onSubmit(): void {
    if (this.ruleForm.valid) {
      const ruleData = {
        ...this.ruleForm.value,
        source_addresses: this.ruleForm.value.source_addresses || [],
        destination_fqdns: this.ruleForm.value.destination_fqdns || [],
        source_ip_groups: this.ruleForm.value.source_ip_groups || [],
        destination_ports: this.ruleForm.value.destination_ports || []
      };

      if (this.data.isEdit && this.data.rule?.id) {
        this.rulesService.updateRule(this.data.rule.id, ruleData).subscribe({
          next: () => this.dialogRef.close(true),
          error: (err: any) => console.error('Error updating rule:', err)
        });
      } else {
        this.rulesService.createRule(ruleData).subscribe({
          next: () => this.dialogRef.close(true),
          error: (err: any) => console.error('Error creating rule:', err)
        });
      }
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}