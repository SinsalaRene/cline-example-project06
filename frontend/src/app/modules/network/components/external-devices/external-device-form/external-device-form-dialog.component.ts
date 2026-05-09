/**
 * External Device Form Dialog Component
 *
 * A Material dialog for adding/editing external network devices.
 * Uses reactive forms with validation for IP address pattern, email format,
 * and required fields.
 *
 * Form Fields:
 * - Name (required)
 * - IP Address (required, IP pattern)
 * - Device Type (dropdown: router/switch/firewall/other)
 * - Vendor (text)
 * - Model (text)
 * - Contact Name (text)
 * - Contact Email (email pattern)
 * - Notes (textarea)
 * - Tags (comma-separated)
 *
 * @module external-device-form-dialog
 * @author Network Module Team
 * @since 1.0.0
 */

import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDividerModule } from '@angular/material/divider';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { ExternalNetworkDevice, DeviceType } from '../../../models/network.model';

/**
 * Form data interface for the external device dialog.
 */
export interface ExternalDeviceFormData {
  device: ExternalNetworkDevice | null;
}

/**
 * IP address regex pattern (IPv4).
 */
const IP_PATTERN = '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$';

/**
 * Email regex pattern.
 */
const EMAIL_PATTERN = '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$';

/**
 * External Device Form Dialog Component.
 *
 * @selector app-external-device-form-dialog
 * @standalone
 */
@Component({
  selector: 'app-external-device-form-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule,
    MatButtonModule,
    MatCheckboxModule,
    MatDividerModule,
    MatDialogModule,
    MatIconModule,
  ],
  template: `
    <h2 mat-dialog-title>
      {{ formData.device ? 'Edit Device' : 'Add Device' }}
    </h2>

    <form [formGroup]="deviceForm" (ngSubmit)="onSubmit()">
      <div class="dialog-content">
        <!-- Device Name -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Device Name *</mat-label>
          <input matInput formControlName="name" placeholder="e.g., Core Router US-East">
          <mat-error *ngIf="deviceForm.get('name')?.hasError('required')">
            Device name is required
          </mat-error>
        </mat-form-field>

        <!-- IP Address -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>IP Address *</mat-label>
          <input matInput formControlName="ipAddress" placeholder="e.g., 192.168.1.1">
          <mat-icon matSuffix>public</mat-icon>
          <mat-error *ngIf="deviceForm.get('ipAddress')?.hasError('required')">
            IP address is required
          </mat-error>
          <mat-error *ngIf="deviceForm.get('ipAddress')?.hasError('pattern')">
            Invalid IP address format
          </mat-error>
        </mat-form-field>

        <!-- Device Type -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Device Type</mat-label>
          <mat-select formControlName="deviceType">
            <mat-option *ngFor="let type of deviceTypes" [value]="type.value">
              {{ type.label }}
            </mat-option>
          </mat-select>
        </mat-form-field>

        <!-- Vendor -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Vendor</mat-label>
          <input matInput formControlName="vendor" placeholder="e.g., Cisco, Juniper">
        </mat-form-field>

        <!-- Model -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Model</mat-label>
          <input matInput formControlName="model" placeholder="e.g., ISR4451, MX240">
        </mat-form-field>

        <!-- Contact Name -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Contact Name</mat-label>
          <input matInput formControlName="contactName" placeholder="e.g., John Smith">
        </mat-form-field>

        <!-- Contact Email -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Contact Email</mat-label>
          <input matInput formControlName="contactEmail" placeholder="e.g., john@example.com">
          <mat-icon matSuffix>email</mat-icon>
          <mat-error *ngIf="deviceForm.get('contactEmail')?.hasError('pattern')">
            Invalid email format
          </mat-error>
        </mat-form-field>

        <!-- Contact Phone -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Contact Phone</mat-label>
          <input matInput formControlName="contactPhone" placeholder="e.g., +1-555-123-4567">
        </mat-form-field>

        <!-- Notes -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Notes</mat-label>
          <textarea matInput formControlName="notes" rows="3" placeholder="Additional notes..."></textarea>
        </mat-form-field>

        <!-- Tags -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Tags</mat-label>
          <input matInput formControlName="tags" placeholder="e.g., production, core, us-east">
          <mat-hint>Comma-separated tags</mat-hint>
        </mat-form-field>

        <!-- Active Status -->
        <mat-checkbox formControlName="isActive" class="full-width">
          Active
        </mat-checkbox>
      </div>

      <div class="dialog-actions">
        <button mat-button (click)="onCancel()">Cancel</button>
        <button mat-raised-button color="primary" type="submit" [disabled]="deviceForm.invalid">
          {{ formData.device ? 'Update' : 'Create' }}
        </button>
      </div>
    </form>
  `,
  styles: [`
    .full-width {
      width: 100%;
      margin-bottom: 16px;
    }

    .dialog-content {
      padding: 16px 24px;
      max-height: 60vh;
      overflow-y: auto;
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      padding: 8px 24px 24px;
    }

    mat-divider {
      margin: 8px 0;
    }
  `],
})
export class ExternalDeviceFormDialogComponent {
  /** Form data passed from parent. */
  formData: ExternalDeviceFormData;

  /** The reactive form group. */
  deviceForm: FormGroup;

  /** Available device types for the dropdown. */
  deviceTypes = [
    { value: DeviceType.ROUTER, label: 'Router' },
    { value: DeviceType.SWITCH, label: 'Switch' },
    { value: DeviceType.FIREWALL, label: 'Firewall' },
    { value: DeviceType.OTHER, label: 'Other' },
  ];

  /**
   * Creates a new ExternalDeviceFormDialogComponent.
   *
   * @param formBuilder - Angular form builder.
   * @param data - Dialog data containing optional existing device.
   * @param dialogRef - Reference to the Material dialog.
   */
  constructor(
    private formBuilder: FormBuilder,
    @Inject(MAT_DIALOG_DATA) data: ExternalDeviceFormData,
    private dialogRef: MatDialogRef<ExternalDeviceFormDialogComponent>
  ) {
    this.formData = data;
    this.deviceForm = this.initForm();
    this.loadFormData();
  }

  /**
   * Initializes the reactive form with validators.
   *
   * @returns The configured form group.
   */
  private initForm(): FormGroup {
    return this.formBuilder.group({
      name: [null, [Validators.required]],
      ipAddress: [null, [Validators.pattern(IP_PATTERN)]],
      deviceType: [DeviceType.OTHER],
      vendor: [null],
      model: [null],
      contactName: [null],
      contactEmail: [null, [Validators.pattern(EMAIL_PATTERN)]],
      contactPhone: [null],
      notes: [null],
      tags: [null],
      isActive: [true],
    });
  }

  /**
   * Loads existing device data into the form when editing.
   */
  private loadFormData(): void {
    if (this.formData.device) {
      const device = this.formData.device;
      this.deviceForm.patchValue({
        name: device.name,
        ipAddress: device.ipAddress,
        deviceType: device.deviceType || DeviceType.OTHER,
        vendor: device.vendor || '',
        model: device.model || '',
        contactName: device.contactName || '',
        contactEmail: device.contactEmail || '',
        contactPhone: device.contactPhone || '',
        notes: device.notes || '',
        tags: device.tags || '',
        isActive: device.isActive ?? true,
      });
    }
  }

  /**
   * Handles form submission.
   * Validates and emits the device data to the parent.
   */
  onSubmit(): void {
    if (this.deviceForm.invalid) {
      this.deviceForm.markAllAsTouched();
      return;
    }

    const formValue = this.deviceForm.value;
    const tags = formValue.tags
      ? formValue.tags
        .split(',')
        .map((t: string) => t.trim())
        .filter(Boolean)
        .join(', ')
      : '';

    const device: ExternalNetworkDevice = {
      id: this.formData.device?.id || `ext-dev-${Date.now()}`,
      name: formValue.name,
      ipAddress: formValue.ipAddress,
      deviceType: formValue.deviceType || DeviceType.OTHER,
      vendor: formValue.vendor || '',
      model: formValue.model || '',
      contactName: formValue.contactName || '',
      contactEmail: formValue.contactEmail || '',
      contactPhone: formValue.contactPhone || '',
      notes: formValue.notes || '',
      tags,
      isActive: formValue.isActive,
    };

    this.dialogRef.close(device);
  }

  /**
   * Cancels the dialog and closes without saving.
   */
  onCancel(): void {
    this.dialogRef.close();
  }
}