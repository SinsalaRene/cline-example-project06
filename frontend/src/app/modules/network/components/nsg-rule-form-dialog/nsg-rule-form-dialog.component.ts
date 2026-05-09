/**
 * NSG Rule Form Dialog Component
 *
 * A Material dialog that provides a form for creating or editing NSG rules.
 * Validates required fields, priority range (100-4096), priority uniqueness
 * across existing rules, and protocol/port format.
 *
 * # Form Fields
 *
 * - **Name**: Required, unique rule name
 * - **Priority**: Required, integer 100-4096, must be unique within the NSG
 * - **Direction**: Required, dropdown (inbound/outbound)
 * - **Protocol**: Required, dropdown (TCP/UDP/ICMP/AH/*)
 * - **Source IP**: Required, IP address or wildcard (*)
 * - **Destination IP**: Required, IP address or wildcard (*)
 * - **Source Port**: Required, port range (0-65535 or *)
 * - **Destination Port**: Required, port range (0-65535 or *)
 * - **Access**: Required, dropdown (allow/deny)
 * - **Enabled**: Checkbox, default true
 *
 * # Priority Validation
 *
 * The priority field uses async validation to check uniqueness against
 * existing rules for the same NSG. The `PriorityUniqueValidator` service
 * queries the existing rule priorities and returns an error if a duplicate
 * is found. This prevents priority collisions that would cause backend errors.
 *
 * @module nsg-rule-form-dialog-component
 * @author Network Module Team
 * @since 1.0.0
 */

import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule, Validators, FormGroup, FormBuilder, AbstractControl, ValidationErrors, AsyncValidator } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { Observable, of } from 'rxjs';
import { debounceTime, switchMap, tap, finalize } from 'rxjs/operators';
import { NetworkService } from '../../services/network.service';
import { Direction, Protocol, Access, NSGRule } from '../../models/network.model';

/** Dialog data interface for NSG rule form. */
export interface NsgRuleFormData {
    /** The NSG ID this rule belongs to. */
    nsgId: string;
    /** Existing rules for priority uniqueness check. */
    existingRules: NSGRule[];
    /** Optional existing rule data for edit mode. */
    rule?: NSGRule | null;
}

/** Priority async validator service for uniqueness checking. */
export class PriorityUniqueValidator {
    /**
     * Validates that the priority is unique among existing rules.
     *
     * Checks if any existing rule (excluding the current rule being edited)
     * has the same priority value. Returns error object if duplicate found,
     * null if unique.
     *
     * @param control - The form control containing the priority value.
     * @param existingRules - Array of existing NSG rules for the same NSG.
     * @param editingRule - Optional existing rule being edited (to exclude from check).
     * @returns ValidationErrors object if not unique, null if valid.
     */
    static validate(control: AbstractControl, existingRules: NSGRule[], editingRule?: NSGRule | null): ValidationErrors | null {
        const priority = control.value;
        if (!priority) return null;

        return existingRules.some(rule => rule.priority === priority && rule.id !== editingRule?.id)
            ? { priorityNotUnique: true }
            : null;
    }
}

/**
 * NSG Rule Form Dialog Component.
 *
 * Displays a form for creating or editing NSG rules within a dialog.
 * Supports add mode (empty form) and edit mode (pre-filled form).
 * Validates priority range, uniqueness, required fields, and protocol/port ranges.
 *
 * @selector app-nsg-rule-form-dialog
 * @standalone
 */
@Component({
    selector: 'app-nsg-rule-form-dialog',
    standalone: true,
    imports: [
        CommonModule,
        ReactiveFormsModule,
        FormsModule,
        MatDialogModule,
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        MatCheckboxModule,
        MatButtonModule,
        MatDividerModule,
    ],
    template: `
    <div class="dialog-content">
      <h2 mat-dialog-title>{{ data.rule ? 'Edit NSG Rule' : 'Add NSG Rule' }}</h2>
      <mat-divider />
      <form [formGroup]="form" class="rule-form" (ngSubmit)="onSubmit()">
        <div class="form-grid">
          <mat-form-field appearance="outline">
            <mat-label>Rule Name</mat-label>
            <input matInput formControlName="name" placeholder="MyRule" />
            <mat-error *ngIf="form.get('name')?.hasError('required')">Name is required</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Priority</mat-label>
            <input matInput type="number" min="100" max="4096" formControlName="priority" placeholder="100" />
            <mat-error *ngIf="form.get('priority')?.hasError('required')">Priority is required</mat-error>
            <mat-error *ngIf="form.get('priority')?.hasError('min')">Minimum priority is 100</mat-error>
            <mat-error *ngIf="form.get('priority')?.hasError('max')">Maximum priority is 4096</mat-error>
            <mat-error *ngIf="form.get('priority')?.hasError('priorityNotUnique')">Priority must be unique</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Direction</mat-label>
            <mat-select formControlName="direction">
              <mat-option [value]="Direction.INBOUND">Inbound</mat-option>
              <mat-option [value]="Direction.OUTBOUND">Outbound</mat-option>
            </mat-select>
            <mat-error *ngIf="form.get('direction')?.hasError('required')">Direction is required</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Protocol</mat-label>
            <mat-select formControlName="protocol">
              <mat-option [value]="Protocol.TCP">TCP</mat-option>
              <mat-option [value]="Protocol.UDP">UDP</mat-option>
              <mat-option [value]="Protocol.ICMP">ICMP</mat-option>
              <mat-option [value]="Protocol.AH">AH</mat-option>
              <mat-option [value]="Protocol.ANY">*</mat-option>
            </mat-select>
            <mat-error *ngIf="form.get('protocol')?.hasError('required')">Protocol is required</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Source IP</mat-label>
            <input matInput formControlName="sourceAddressPrefix" placeholder="10.0.0.0/16 or *" />
            <mat-error *ngIf="form.get('sourceAddressPrefix')?.hasError('required')">Source IP is required</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Destination IP</mat-label>
            <input matInput formControlName="destinationAddressPrefix" placeholder="10.1.0.0/16 or *" />
            <mat-error *ngIf="form.get('destinationAddressPrefix')?.hasError('required')">Destination IP is required</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Source Port</mat-label>
            <input matInput formControlName="sourcePortRange" placeholder="80 or 8000-9000 or *" />
            <mat-error *ngIf="form.get('sourcePortRange')?.hasError('required')">Source port is required</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Destination Port</mat-label>
            <input matInput formControlName="destinationPortRange" placeholder="443 or 8000-9000 or *" />
            <mat-error *ngIf="form.get('destinationPortRange')?.hasError('required')">Destination port is required</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Access</mat-label>
            <mat-select formControlName="access">
              <mat-option [value]="Access.ALLOW">Allow</mat-option>
              <mat-option [value]="Access.DENY">Deny</mat-option>
            </mat-select>
            <mat-error *ngIf="form.get('access')?.hasError('required')">Access is required</mat-error>
          </mat-form-field>

          <div class="checkbox-cell">
            <mat-checkbox formControlName="isEnabled">Enabled</mat-checkbox>
          </div>
        </div>

        <div class="form-actions">
          <button type="submit" mat-raised-button color="primary" [disabled]="form.invalid || submitting">
            {{ data.rule ? 'Update' : 'Create' }}
          </button>
          <button type="button" mat-button mat-dialog-close>Cancel</button>
        </div>
      </form>
    </div>
  `,
    styles: [`
    .dialog-content {
      padding: 0;
    }

    h2[mat-dialog-title] {
      padding: 0 24px;
      margin: 0;
      font-size: 20px;
      font-weight: 500;
      line-height: 56px;
    }

    mat-divider {
      margin: 0;
    }

    .rule-form {
      padding: 16px 24px 24px;
    }

    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    .checkbox-cell {
      display: flex;
      align-items: center;
      padding-top: 24px;
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 24px;
    }

    mat-form-field {
      width: 100%;
    }
  `],
})
export class NsgRuleFormDialogComponent {
    /** The reactive form for rule data. */
    form: FormGroup;

    /** Whether the form is currently submitting. */
    submitting = false;

    /** Enum references for template binding. */
    readonly Direction = Direction;
    readonly Protocol = Protocol;
    readonly Access = Access;

    /**
     * Creates a new NsgRuleFormDialogComponent.
     *
     * @param fb - FormBuilder for creating the reactive form.
     * @param dialogRef - Reference to the Material dialog.
     * @param data - Dialog data containing NSG ID, existing rules, and optional rule data.
     */
    constructor(
        private fb: FormBuilder,
        public dialogRef: MatDialogRef<NsgRuleFormDialogComponent>,
        public data: NsgRuleFormData
    ) {
        this.form = this.fb.group({});
        this.initializeForm();
        this.setupPriorityValidation();

        // If editing, patch form with existing rule data
        if (data.rule) {
            this.form.patchValue({
                name: data.rule.name,
                priority: data.rule.priority,
                direction: data.rule.direction,
                protocol: data.rule.protocol,
                sourceAddressPrefix: data.rule.sourceAddressPrefix || '*',
                destinationAddressPrefix: data.rule.destinationAddressPrefix || '*',
                sourcePortRange: data.rule.sourcePortRange || '*',
                destinationPortRange: data.rule.destinationPortRange || '*',
                access: data.rule.access,
                isEnabled: data.rule.isEnabled ?? true,
            });
        }
    }

    /**
     * Initializes the reactive form with all fields and validators.
     *
     * Sets up required validators for name, priority, direction, protocol,
     * source/destination IPs, source/destination ports, and access.
     * Priority has custom min/max validators (100-4096).
     */
    private initializeForm(): void {
        this.form = this.fb.group({
            name: ['', [Validators.required]],
            priority: [null, [Validators.required, Validators.min(100), Validators.max(4096)]],
            direction: [Direction.INBOUND, [Validators.required]],
            protocol: [Protocol.ANY, [Validators.required]],
            sourceAddressPrefix: ['', [Validators.required]],
            destinationAddressPrefix: ['', [Validators.required]],
            sourcePortRange: ['', [Validators.required]],
            destinationPortRange: ['', [Validators.required]],
            access: [Access.ALLOW, [Validators.required]],
            isEnabled: [true],
        });
    }

    /**
     * Sets up async priority uniqueness validation.
     *
     * Uses debounceTime(400ms) to avoid excessive validation on every keystroke.
     * On each priority change, compares against existing rules and flags
     * duplicates (excluding the current rule when editing).
     */
    private setupPriorityValidation(): void {
        const priorityControl = this.form.get('priority');
        if (!priorityControl) return;

        // Remove sync validation first, then add async validation
        priorityControl.setValidators([]);
        priorityControl.setAsyncValidators([]);

        // Debounced live validation
        priorityControl.valueChanges
            .pipe(
                debounceTime(400),
                tap((priority: number) => {
                    const error = PriorityUniqueValidator.validate(
                        priorityControl,
                        this.data.existingRules || [],
                        this.data.rule || undefined
                    );
                    if (error) {
                        priorityControl.setErrors({ ...priorityControl.errors, ...error });
                    } else {
                        // Clear priorityNotUnique error if unique
                        const currentErrors = { ...priorityControl.errors };
                        delete currentErrors['priorityNotUnique'];
                        priorityControl.setErrors(Object.keys(currentErrors).length ? currentErrors : null);
                    }
                })
            )
            .subscribe();
    }

    /**
     * Handles form submission.
     *
     * Validates the form, marks all controls as touched to trigger validation
     * messages, then emits the form value through MatDialogRef.
     */
    onSubmit(): void {
        if (this.form.invalid) {
            this.form.markAllAsTouched();
            return;
        }

        this.submitting = true;
        const value = this.form.value;

        this.dialogRef.close({
            name: value.name.trim(),
            priority: value.priority,
            direction: value.direction,
            protocol: value.protocol,
            sourceAddressPrefix: value.sourceAddressPrefix.trim(),
            destinationAddressPrefix: value.destinationAddressPrefix.trim(),
            sourcePortRange: value.sourcePortRange.trim(),
            destinationPortRange: value.destinationPortRange.trim(),
            access: value.access,
            isEnabled: value.isEnabled,
        });
    }
}