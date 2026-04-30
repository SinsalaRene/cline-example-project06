import { Component, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule, MatTabGroup, MatTab } from '@angular/material/tabs';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { FormsModule } from '@angular/forms';
import { RulesService, FirewallRule } from '../services/rules.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { CommonModule } from '@angular/common';

interface RuleDetailTab {
  name: string;
  icon: string;
}

@Component({
  selector: 'app-rule-detail',
  standalone: true,
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    MatCardModule,
    MatExpansionModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    FormsModule,
    CommonModule
  ],
  template: `
    <div class="rule-detail-container">
      <h2 mat-dialog-title>
        <mat-icon color="primary">rule</mat-icon>
        {{ data.rule?.rule_collection_name || 'Rule Details' }}
      </h2>

      <mat-tab-group mat-dialog-content class="detail-tabs">
        <mat-tab label="Overview">
          <div class="tab-content">
            <div class="detail-section">
              <div class="detail-header">
                <h3>Rule Information</h3>
                <div class="status-badges">
                  <span class="status-badge status-{{ data.rule?.status }}">
                    {{ data.rule?.status | titlecase }}
                  </span>
                  <span class="action-badge action-{{ data.rule?.action | lowercase }}">
                    {{ data.rule?.action }}
                  </span>
                </div>
              </div>

              <div class="detail-grid">
                <div class="detail-item">
                  <label>Rule Name</label>
                  <p>{{ data.rule?.rule_collection_name }}</p>
                </div>
                <div class="detail-item">
                  <label>Priority</label>
                  <p>{{ data.rule?.priority }}</p>
                </div>
                <div class="detail-item">
                  <label>Protocol</label>
                  <p>{{ data.rule?.protocol }}</p>
                </div>
                <div class="detail-item">
                  <label>Rule ID</label>
                  <p class="mono">{{ data.rule?.id }}</p>
                </div>
              </div>

              <div class="detail-item full-width">
                <label>Description</label>
                <p>{{ data.rule?.description || 'No description provided.' }}</p>
              </div>
            </div>

            <div class="detail-section">
              <h3>Timestamps</h3>
              <div class="detail-grid">
                <div class="detail-item">
                  <label>Created</label>
                  <p>{{ data.rule?.created_at | date:'medium' }}</p>
                </div>
                <div class="detail-item">
                  <label>Last Updated</label>
                  <p>{{ data.rule?.updated_at | date:'medium' }}</p>
                </div>
              </div>
            </div>
          </div>
        </mat-tab>

        <mat-tab label="Configuration">
          <div class="tab-content">
            <div class="detail-section">
              <h3>Address Configuration</h3>

              <mat-expansion-panel class="detail-panel">
                <mat-expansion-panel-header>
                  <mat-panel-title>
                    <mat-icon>public</mat-icon>
                    Source Addresses
                  </mat-panel-title>
                </mat-expansion-panel-header>
                <ng-content *ngIf="data.rule?.source_addresses && data.rule.source_addresses.length > 0; else noAddresses">
                  <ul class="address-list">
                    <li *ngFor="let addr of data.rule.source_addresses">{{ addr }}</li>
                  </ul>
                </ng-content>
                <ng-template #noAddresses>
                  <p class="empty-text">No source addresses configured.</p>
                </ng-template>
              </mat-expansion-panel>

              <mat-expansion-panel class="detail-panel">
                <mat-expansion-panel-header>
                  <mat-panel-title>
                    <mat-icon>public</mat-icon>
                    Source IP Groups
                  </mat-panel-title>
                </mat-expansion-panel-header>
                <ng-content *ngIf="data.rule?.source_ip_groups && data.rule.source_ip_groups.length > 0; else noIpGroups">
                  <ul class="address-list">
                    <li *ngFor="let group of data.rule.source_ip_groups">{{ group }}</li>
                  </ul>
                </ng-content>
                <ng-template #noIpGroups>
                  <p class="empty-text">No source IP groups configured.</p>
                </ng-template>
              </mat-expansion-panel>

              <mat-expansion-panel class="detail-panel">
                <mat-expansion-panel-header>
                  <mat-panel-title>
                    <mat-icon>language</mat-icon>
                    Destination FQDNs
                  </mat-panel-title>
                </mat-expansion-panel-header>
                <ng-content *ngIf="data.rule?.destination_fqdns && data.rule.destination_fqdns.length > 0; else noFqdns">
                  <ul class="address-list">
                    <li *ngFor="let fqdn of data.rule.destination_fqdns">{{ fqdn }}</li>
                  </ul>
                </ng-content>
                <ng-template #noFqdns>
                  <p class="empty-text">No destination FQDNs configured.</p>
                </ng-template>
              </mat-expansion-panel>

              <mat-expansion-panel class="detail-panel">
                <mat-expansion-panel-header>
                  <mat-panel-title>
                    <mat-icon>settings_remote</mat-icon>
                    Destination Ports
                  </mat-panel-title>
                </mat-expansion-panel-header>
                <ng-content *ngIf="data.rule?.destination_ports && data.rule.destination_ports.length > 0; else noPorts">
                  <ul class="port-list">
                    <li *ngFor="let port of data.rule.destination_ports">{{ port }}</li>
                  </ul>
                </ng-content>
                <ng-template #noPorts>
                  <p class="empty-text">No destination ports configured.</p>
                </ng-template>
              </mat-expansion-panel>
            </div>

            <div class="detail-section">
              <h3>Azure Configuration</h3>
              <div class="detail-grid">
                <div class="detail-item">
                  <label>Workload ID</label>
                  <p class="mono">{{ data.rule?.workload_id || 'N/A' }}</p>
                </div>
                <div class="detail-item">
                  <label>Azure Resource ID</label>
                  <p class="mono text-truncate">{{ data.rule?.azure_resource_id || 'N/A' }}</p>
                </div>
              </div>
            </div>
          </div>
        </mat-tab>

        <mat-tab label="Audit History">
          <div class="tab-content">
            <div class="audit-timeline">
              <div class="audit-entry">
                <mat-icon class="audit-icon">check_circle</mat-icon>
                <div class="audit-content">
                  <span class="audit-action">Rule created</span>
                  <span class="audit-date">{{ data.rule?.created_at | date:'medium' }}</span>
                </div>
              </div>
              <div class="audit-entry" *ngIf="data.rule?.updated_at && data.rule.updated_at !== data.rule.created_at">
                <mat-icon class="audit-icon">edit</mat-icon>
                <div class="audit-content">
                  <span class="audit-action">Rule updated</span>
                  <span class="audit-date">{{ data.rule?.updated_at | date:'medium' }}</span>
                </div>
              </div>
              <div class="audit-entry" *ngIf="data.rule?.status === 'deleted'">
                <mat-icon class="audit-icon">delete</mat-icon>
                <div class="audit-content">
                  <span class="audit-action">Rule deleted</span>
                  <span class="audit-date">{{ data.rule?.updated_at | date:'medium' }}</span>
                </div>
              </div>
            </div>

            <div class="audit-note">
              <p>Full audit history is available in the Audit module.</p>
            </div>
          </div>
        </mat-tab>

        <mat-tab label="JSON">
          <div class="tab-content">
            <pre class="json-preview">{{ data.rule | json }}</pre>
          </div>
        </mat-tab>
      </mat-tab-group>

      <div mat-dialog-actions class="detail-actions">
        <button mat-button (click)="onClose()">Close</button>
        <button mat-raised-button color="primary" (click)="onEdit()">
          <mat-icon>edit</mat-icon> Edit
        </button>
      </div>
    </div>
  `,
  styles: [`
    .rule-detail-container {
      min-width: 600px;
      max-width: 90vw;
    }

    @media (max-width: 600px) {
      .rule-detail-container {
        min-width: 300px;
      }
    }

    .detail-tabs {
      height: 500px;
      overflow-y: auto;
    }

    .tab-content {
      padding: 24px;
    }

    .detail-section {
      margin-bottom: 32px;
    }

    .detail-section:last-child {
      margin-bottom: 0;
    }

    .detail-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .detail-header h3 {
      margin: 0;
      font-size: 1.1rem;
      font-weight: 500;
    }

    .status-badges {
      display: flex;
      gap: 8px;
    }

    .status-badge, .action-badge {
      padding: 4px 12px;
      border-radius: 16px;
      font-size: 0.875rem;
      font-weight: 500;
    }

    .status-active {
      background: #e8f5e9;
      color: #2e7d32;
    }

    .status-pending {
      background: #fff3e0;
      color: #ef6c00;
    }

    .status-deleted {
      background: #f5f5f5;
      color: #616161;
    }

    .status-error {
      background: #ffebee;
      color: #c62828;
    }

    .action-allow {
      background: #e8f5e9;
      color: #2e7d32;
    }

    .action-deny {
      background: #ffebee;
      color: #c62828;
    }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }

    .detail-item {
      padding: 12px;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .detail-item.full-width {
      grid-column: 1 / -1;
    }

    .detail-item label {
      display: block;
      font-size: 0.75rem;
      font-weight: 500;
      text-transform: uppercase;
      color: #666;
      margin-bottom: 4px;
    }

    .detail-item p {
      margin: 0;
      font-weight: 500;
    }

    .mono {
      font-family: monospace;
      font-size: 0.85rem;
    }

    .text-truncate {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 300px;
    }

    .detail-panel {
      margin-bottom: 8px;
    }

    .address-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .address-list li {
      padding: 8px 12px;
      background: #f5f5f5;
      border-radius: 4px;
      margin-bottom: 4px;
      font-family: monospace;
      font-size: 0.875rem;
    }

    .port-list {
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .port-list li {
      padding: 4px 12px;
      background: #e3f2fd;
      border-radius: 16px;
      font-family: monospace;
      font-size: 0.875rem;
    }

    .empty-text {
      color: #999;
      font-style: italic;
    }

    .audit-timeline {
      position: relative;
      padding-left: 24px;
    }

    .audit-timeline::before {
      content: '';
      position: absolute;
      left: 8px;
      top: 0;
      bottom: 0;
      width: 2px;
      background: #e0e0e0;
    }

    .audit-entry {
      position: relative;
      padding: 16px 0;
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .audit-icon {
      color: #1976d2;
    }

    .audit-content {
      display: flex;
      flex-direction: column;
    }

    .audit-action {
      font-weight: 500;
    }

    .audit-date {
      font-size: 0.8rem;
      color: #666;
    }

    .audit-note {
      padding: 16px;
      background: #fff3e0;
      border-radius: 8px;
      margin-top: 24px;
    }

    .json-preview {
      background: #263238;
      color: #aed581;
      padding: 16px;
      border-radius: 8px;
      overflow: auto;
      max-height: 400px;
      font-size: 0.85rem;
      line-height: 1.5;
    }

    .detail-actions {
      justify-content: flex-end;
      padding: 16px;
      border-top: 1px solid #e0e0e0;
    }
  `]
})
export class RuleDetailComponent {
  activeTab = 'overview';

  constructor(
    public dialogRef: MatDialogRef<RuleDetailComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { rule: FirewallRule },
    private rulesService: RulesService,
    private snackBar: MatSnackBar
  ) { }

  onClose(): void {
    this.dialogRef.close();
  }

  onEdit(): void {
    this.dialogRef.close({ edit: this.data.rule });
  }
}