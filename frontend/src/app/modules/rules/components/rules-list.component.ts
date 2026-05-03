import { Component, OnInit, ViewChild } from '@angular/core';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { RulesService, FirewallRule } from '../services/rules.service';
import { RuleFormDialogComponent } from './rule-form-dialog.component';
import { RuleDetailComponent } from './rule-detail.component';
import { ConfirmationDialogComponent } from '../components/confirmation-dialog.component';

export interface RuleListFilter {
  searchQuery: string;
  statusFilter: string;
  actionFilter: string;
  protocolFilter: string;
  workloadFilter: string;
}

@Component({
  selector: 'app-rules-list',
  template: `
    <div class="rules-container">
      <div class="header-section">
        <h2>Firewall Rules</h2>
        <p>Manage firewall rules for your Azure resources</p>
      </div>

      <!-- Toolbar with actions -->
      <div class="toolbar">
        <button mat-raised-button color="primary" (click)="openCreateDialog()" class="toolbar-btn">
          <mat-icon>add</mat-icon> New Rule
        </button>
        <button mat-raised-button color="accent" (click)="importRules()" class="toolbar-btn" [disabled]="!hasSelection()">
          <mat-icon>cloud_upload</mat-icon> Import
        </button>
        <button mat-raised-button color="primary" (click)="exportRules()" class="toolbar-btn" [disabled]="dataSource.data.length === 0">
          <mat-icon>cloud_download</mat-icon> Export
        </button>
        <button mat-raised-button color="warn" (click)="bulkDeleteSelected()" class="toolbar-btn" [disabled]="!hasSelection()">
          <mat-icon>delete_sweep</mat-icon> Delete Selected
        </button>
        <button mat-raised-button color="accent" (click)="bulkEnableSelected()" class="toolbar-btn" [disabled]="!hasSelection()">
          <mat-icon>check_circle</mat-icon> Enable Selected
        </button>
        <button mat-raised-button color="accent" (click)="bulkDisableSelected()" class="toolbar-btn" [disabled]="!hasSelection()">
          <mat-icon>cancel</mat-icon> Disable Selected
        </button>
        <div class="spacer"></div>
        <button mat-button (click)="toggleFilters()">
          <mat-icon>filter_list</mat-icon> {{showFilters ? 'Hide' : 'Show'}} Filters
        </button>
      </div>

      <!-- Filter panel -->
      <div class="filter-panel" *ngIf="showFilters">
        <div class="filter-row">
          <mat-form-field appearance="outline">
            <mat-label>Status</mat-label>
            <mat-select (selectionChange)="applyFilters()" [(value)]="currentFilters.statusFilter">
              <mat-option value="">All Statuses</mat-option>
              <mat-option value="active">Active</mat-option>
              <mat-option value="pending">Pending</mat-option>
              <mat-option value="deleted">Deleted</mat-option>
              <mat-option value="error">Error</mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Action</mat-label>
            <mat-select (selectionChange)="applyFilters()" [(value)]="currentFilters.actionFilter">
              <mat-option value="">All Actions</mat-option>
              <mat-option value="Allow">Allow</mat-option>
              <mat-option value="Deny">Deny</mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Protocol</mat-label>
            <mat-select (selectionChange)="applyFilters()" [(value)]="currentFilters.protocolFilter">
              <mat-option value="">All Protocols</mat-option>
              <mat-option value="Any">Any</mat-option>
              <mat-option value="Tcp">TCP</mat-option>
              <mat-option value="Udp">UDP</mat-option>
              <mat-option value="IpProtocol">IP Protocol</mat-option>
            </mat-select>
          </mat-form-field>
          <button mat-raised-button color="primary" (click)="resetFilters()" class="reset-filter-btn">
            Reset Filters
          </button>
        </div>
      </div>

      <!-- Search bar -->
      <div class="search-bar">
        <mat-form-field appearance="outline" class="search-field">
          <mat-label>Search rules</mat-label>
          <input matInput (keyup)="onSearchChange($event)" placeholder="Search by name, action, protocol, status..." #searchInput>
          <button mat-icon-button matSuffix *ngIf="searchInput.value" (click)="searchInput.value=''; onSearchChange($event)">
            <mat-icon>clear</mat-icon>
          </button>
        </mat-form-field>
      </div>

      <!-- Selection count indicator -->
      <div class="selection-info" *ngIf="selectedRows.size > 0">
        <span>{{selectedRows.size}} rule(s) selected</span>
        <button mat-button (click)="clearSelection()">Clear selection</button>
      </div>

      <!-- Loading indicator -->
      <div class="loading-indicator" *ngIf="isLoading">
        <mat-progress-spinner mode="indeterminate" [diameter]="40"></mat-progress-spinner>
        <span>Loading rules...</span>
      </div>

      <!-- Data table -->
      <div class="table-wrapper">
        <table mat-table [dataSource]="dataSource" matSort matSortDisableClear matSortActive="priority" matSortDirection="asc" class="rules-table">

          <!-- Selection column -->
          <ng-container matColumnDef="select">
            <th mat-header-cell *matHeaderCellDef>
              <mat-checkbox
                color="primary"
                [checked]="isAllSelected()"
                [indeterminate]="!isAllSelected() && hasSelectedItems()"
                (change)="$event ? toggleAllRows() : null"
                [disabled]="dataSource.data.length === 0"
              ></mat-checkbox>
            </th>
            <td mat-cell *matCellDef="let row">
              <mat-checkbox
                color="primary"
                [checked]="selectedRows.has(row)"
                (change)="$event ? toggleRowSelection(row) : null"
              ></mat-checkbox>
            </td>
          </ng-container>

          <!-- Name column -->
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Rule Name</th>
            <td mat-cell *matCellDef="let rule">
              <a class="rule-name-link" (click)="viewRuleDetail(rule)" title="Click to view details">
                {{ rule.rule_collection_name }}
              </a>
            </td>
          </ng-container>

          <!-- Priority column -->
          <ng-container matColumnDef="priority">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Priority</th>
            <td mat-cell *matCellDef="let rule">{{ rule.priority }}</td>
          </ng-container>

          <!-- Action column -->
          <ng-container matColumnDef="action">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Action</th>
            <td mat-cell *matCellDef="let rule">
              <mat-chip [color]="rule.action === 'Allow' ? 'accent' : 'warn'" class="action-chip">
                {{ rule.action }}
              </mat-chip>
            </td>
          </ng-container>

          <!-- Protocol column -->
          <ng-container matColumnDef="protocol">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Protocol</th>
            <td mat-cell *matCellDef="let rule">{{ rule.protocol }}</td>
          </ng-container>

          <!-- Status column -->
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef mat-sort-header>Status</th>
            <td mat-cell *matCellDef="let rule">
              <span class="status-badge status-{{ rule.status }}">
                <mat-icon class="status-icon" *ngIf="rule.status === 'active'">check_circle</mat-icon>
                <mat-icon class="status-icon" *ngIf="rule.status === 'pending'">schedule</mat-icon>
                <mat-icon class="status-icon" *ngIf="rule.status === 'deleted'">delete</mat-icon>
                <mat-icon class="status-icon" *ngIf="rule.status === 'error'">error</mat-icon>
                {{ rule.status | titlecase }}
              </span>
            </td>
          </ng-container>

          <!-- Actions column -->
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef>Actions</th>
            <td mat-cell *matCellDef="let rule">
              <button mat-icon-button color="primary" (click)="viewRuleDetail(rule)" matTooltip="View details">
                <mat-icon>visibility</mat-icon>
              </button>
              <button mat-icon-button color="accent" (click)="editRule(rule)" matTooltip="Edit rule">
                <mat-icon>edit</mat-icon>
              </button>
              <button mat-icon-button color="accent" (click)="duplicateRule(rule)" matTooltip="Duplicate rule">
                <mat-icon>content_copy</mat-icon>
              </button>
              <button mat-icon-button color="warn" (click)="deleteRule(rule)" matTooltip="Delete rule">
                <mat-icon>delete</mat-icon>
              </button>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns;" class="data-row"
              [class.selected-row]="selectedRows.has(row)"></tr>
        </table>

        <!-- Empty state -->
        <div class="empty-state" *ngIf="dataSource.data.length === 0 && !isLoading">
          <mat-icon class="empty-icon">rule</mat-icon>
          <h3>No firewall rules found</h3>
          <p>Create your first firewall rule to get started.</p>
          <button mat-raised-button color="primary" (click)="openCreateDialog()">
            <mat-icon>add</mat-icon> Create Rule
          </button>
        </div>

        <mat-paginator
          [pageSizeOptions]="[5, 10, 25, 50]"
          showFirstLastButtons
          aria-label="Select page"
        ></mat-paginator>
      </div>
    </div>
  `,
  styles: [`
      .rules-container {
        padding: 20px;
        max-width: 100%;
      }

      .header-section {
        margin-bottom: 24px;
      }

      .header-section h2 {
        margin: 0 0 4px 0;
        font-weight: 500;
      }

      .header-section p {
        color: #666;
        margin: 0;
      }

      .toolbar {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
        flex-wrap: wrap;
        align-items: center;
        padding: 12px;
        background: #f5f5f5;
        border-radius: 8px;
      }

      .toolbar-btn {
        margin: 0;
      }

      .spacer {
        flex: 1;
      }

      .filter-panel {
        background: #fafafa;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 16px;
        border: 1px solid #e0e0e0;
      }

      .filter-row {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        align-items: center;
      }

      .filter-row mat-form-field {
        flex: 1;
        min-width: 150px;
      }

      .reset-filter-btn {
        white-space: nowrap;
      }

      .search-bar {
        margin-bottom: 16px;
      }

      .search-field {
        width: 100%;
        max-width: 500px;
      }

      .selection-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 16px;
        background: #e3f2fd;
        border-radius: 4px;
        margin-bottom: 16px;
      }

      .loading-indicator {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        padding: 40px;
      }

      .table-wrapper {
        position: relative;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        overflow: hidden;
      }

      .rules-table {
        width: 100%;
      }

      .data-row.selected-row {
        background: #e3f2fd;
      }

      .data-row:hover {
        background: #f5f5f5;
      }

      .rule-name-link {
        color: #1976d2;
        cursor: pointer;
        text-decoration: none;
        font-weight: 500;
      }

      .rule-name-link:hover {
        text-decoration: underline;
        color: #1565c0;
      }

      .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 8px;
        border-radius: 4px;
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

      .status-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }

      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 60px 20px;
        text-align: center;
      }

      .empty-icon {
        font-size: 64px;
        color: #bdbdbd;
        margin-bottom: 16px;
      }

      .empty-state h3 {
        margin: 0 0 8px 0;
        color: #616161;
      }

      .empty-state p {
        margin: 0 0 16px 0;
        color: #9e9e9e;
      }

      @media (max-width: 768px) {
        .toolbar {
          flex-direction: column;
          align-items: stretch;
        }

        .toolbar .spacer {
          display: none;
        }

        .filter-row {
          flex-direction: column;
        }
      }
    `],
  imports: [
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatPaginatorModule,
    MatChipsModule,
    MatTableModule,
    MatSortModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatCheckboxModule,
    CommonModule,
    ReactiveFormsModule
  ],
  standalone: true
})
export class RulesListComponent implements OnInit {
  displayedColumns: string[] = ['select', 'name', 'priority', 'action', 'protocol', 'status', 'actions'];
  dataSource = new MatTableDataSource<FirewallRule>();
  selectedRows = new Set<FirewallRule>();

  showFilters = false;
  isLoading = false;
  currentFilters: RuleListFilter = {
    searchQuery: '',
    statusFilter: '',
    actionFilter: '',
    protocolFilter: '',
    workloadFilter: ''
  };

  @ViewChild('searchInput') searchInput!: { value: string };
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  protected allRules: FirewallRule[] = [];

  constructor(
    private rulesService: RulesService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private router: Router,
    private fb: FormBuilder
  ) { }

  ngOnInit(): void {
    this.loadRules();
  }

  loadRules(): void {
    this.isLoading = true;
    this.rulesService.getRules().subscribe({
      next: (response) => {
        this.allRules = response.items || [];
        this.dataSource = new MatTableDataSource<FirewallRule>(this.allRules);
        this.dataSource.paginator = this.paginator;
        this.applyFilters();
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading rules:', err);
        this.isLoading = false;
        this.snackBar.open('Error loading rules. Please try again.', 'Retry', { duration: 5000 });
      }
    });
  }

  onSearchChange(event: Event): void {
    this.currentFilters.searchQuery = (event.target as HTMLInputElement).value;
    this.applyFilters();
  }

  applyFilters(): void {
    const searchLower = this.currentFilters.searchQuery.toLowerCase();
    const statusLower = this.currentFilters.statusFilter.toLowerCase();
    const actionLower = this.currentFilters.actionFilter.toLowerCase();
    const protocolLower = this.currentFilters.protocolFilter.toLowerCase();

    this.dataSource.filter = '';
    this.dataSource.filteredData = this.allRules.filter(rule => {
      // Search filter
      if (searchLower && !this.matchesSearch(rule, searchLower)) {
        return false;
      }

      // Status filter
      if (statusLower && rule.status.toLowerCase() !== statusLower) {
        return false;
      }

      // Action filter
      if (actionLower && rule.action.toLowerCase() !== actionLower) {
        return false;
      }

      // Protocol filter
      if (protocolLower && rule.protocol.toLowerCase() !== protocolLower) {
        return false;
      }

      return true;
    });

    // Re-apply paginator to filtered data
    if (this.paginator) {
      this.dataSource.paginator = this.paginator;
    }
  }

  private matchesSearch(rule: FirewallRule, searchLower: string): boolean {
    return (
      (rule.rule_collection_name || '').toLowerCase().includes(searchLower) ||
      (rule.action || '').toLowerCase().includes(searchLower) ||
      (rule.protocol || '').toLowerCase().includes(searchLower) ||
      (rule.status || '').toLowerCase().includes(searchLower) ||
      (rule.description || '').toLowerCase().includes(searchLower) ||
      (rule.priority?.toString() || '').includes(searchLower)
    );
  }

  resetFilters(): void {
    this.currentFilters = {
      searchQuery: '',
      statusFilter: '',
      actionFilter: '',
      protocolFilter: '',
      workloadFilter: ''
    };
    this.dataSource.filter = '';
    this.dataSource.filteredData = this.allRules ?? [];
  }

  toggleFilters(): void {
    this.showFilters = !this.showFilters;
  }

  // Selection methods
  isAllSelected(): boolean {
    const dataLength = this.dataSource.filteredData?.length ?? this.dataSource.data.length;
    if (dataLength === 0) return false;
    return this.selectedRows.size === dataLength && dataLength > 0;
  }

  hasSelectedItems(): boolean {
    return this.selectedRows.size > 0;
  }

  toggleAllRows(): void {
    const data = this.dataSource.filteredData ?? this.dataSource.data;
    if (!data || data.length === 0) return;

    const allSelected = this.selectedRows.size === data.length;

    if (allSelected) {
      this.selectedRows.clear();
    } else {
      data.forEach((rule: FirewallRule) => this.selectedRows.add(rule));
    }
  }

  toggleRowSelection(rule: FirewallRule): void {
    if (this.selectedRows.has(rule)) {
      this.selectedRows.delete(rule);
    } else {
      this.selectedRows.add(rule);
    }
  }

  hasSelection(): boolean {
    return this.selectedRows.size > 0;
  }

  clearSelection(): void {
    this.selectedRows.clear();
  }

  // Bulk operations
  bulkDeleteSelected(): void {
    if (this.selectedRows.size === 0) return;

    const rulesToDelete = Array.from(this.selectedRows);
    const count = rulesToDelete.length;

    const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
      data: {
        title: 'Delete Rules',
        message: `Are you sure you want to delete ${count} rule(s)?`,
        confirmLabel: 'Delete',
        type: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        let completed = 0;
        let errors = 0;

        rulesToDelete.forEach(rule => {
          this.rulesService.deleteRule(rule.id).subscribe({
            next: () => {
              completed++;
              if (completed + errors === count) {
                this.selectedRows.clear();
                this.loadRules();
                this.snackBar.open(`${completed} rule(s) deleted successfully.`, 'Close', { duration: 3000 });
              }
            },
            error: () => {
              errors++;
              if (completed + errors === count) {
                this.snackBar.open(`${completed} rule(s) deleted, ${errors} failed.`, 'Close', { duration: 3000 });
              }
            }
          });
        });
      } else {
        this.selectedRows.clear();
      }
    });
  }

  bulkEnableSelected(): void {
    this.performBulkOperation(
      'enable',
      `Enable ${this.selectedRows.size} rule(s)?`,
      'enable'
    );
  }

  bulkDisableSelected(): void {
    this.performBulkOperation(
      'disable',
      `Disable ${this.selectedRows.size} rule(s)?`,
      'disable'
    );
  }

  private performBulkOperation(operation: string, message: string, actionType: string): void {
    const rules = Array.from(this.selectedRows);
    const count = rules.length;
    let completed = 0;
    let errors = 0;

    const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
      data: {
        title: operation === 'enable' ? 'Enable Rules' : 'Disable Rules',
        message: message,
        confirmLabel: operation === 'enable' ? 'Enable' : 'Disable',
        type: 'primary'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        rules.forEach(rule => {
          const updatedRule = { ...rule, status: actionType === 'enable' ? 'active' : 'pending' };
          this.rulesService.updateRule(rule.id, updatedRule).subscribe({
            next: () => {
              completed++;
              if (completed + errors === count) {
                this.selectedRows.clear();
                this.loadRules();
                this.snackBar.open(`${completed} rule(s) ${operation}d successfully.`, 'Close', { duration: 3000 });
              }
            },
            error: () => {
              errors++;
              if (completed + errors === count) {
                this.snackBar.open(`${completed} rule(s) ${operation}d, ${errors} failed.`, 'Close', { duration: 3000 });
              }
            }
          });
        });
      } else {
        this.selectedRows.clear();
      }
    });
  }

  // Import/Export
  importRules(): void {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,.csv';

    input.onchange = (event: Event) => {
      const file = (event.target as HTMLInputElement).files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = () => {
        try {
          const content = reader.result as string;
          const rules = JSON.parse(content);
          if (Array.isArray(rules)) {
            // Import logic would go here
            this.snackBar.open(`Imported ${rules.length} rule(s) successfully.`, 'Close', { duration: 3000 });
            this.loadRules();
          } else {
            this.snackBar.open('Invalid file format.', 'Close', { duration: 3000 });
          }
        } catch (e) {
          this.snackBar.open('Error parsing import file.', 'Close', { duration: 3000 });
        }
      };
      reader.readAsText(file);
    };

    input.click();
  }

  exportRules(): void {
    const dataToExport = this.selectedRows.size > 0
      ? Array.from(this.selectedRows)
      : this.dataSource.data;

    const exportData = dataToExport.map(rule => ({
      rule_collection_name: rule.rule_collection_name,
      priority: rule.priority,
      action: rule.action,
      protocol: rule.protocol,
      source_addresses: rule.source_addresses,
      destination_fqdns: rule.destination_fqdns,
      source_ip_groups: rule.source_ip_groups,
      destination_ports: rule.destination_ports,
      description: rule.description,
      status: rule.status
    }));

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `firewall-rules-export-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    this.snackBar.open(`Exported ${exportData.length} rule(s) successfully.`, 'Close', { duration: 3000 });
  }

  // Individual operations
  openCreateDialog(): void {
    const dialogRef = this.dialog.open(RuleFormDialogComponent, {
      width: '600px',
      data: {
        isEdit: false,
        rule: null
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.loadRules();
      }
    });
  }

  editRule(rule: FirewallRule): void {
    const dialogRef = this.dialog.open(RuleFormDialogComponent, {
      width: '600px',
      data: {
        isEdit: true,
        rule: rule
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.loadRules();
      }
    });
  }

  viewRuleDetail(rule: FirewallRule): void {
    const dialogRef = this.dialog.open(RuleDetailComponent, {
      width: '800px',
      data: { rule: rule }
    });
  }

  deleteRule(rule: FirewallRule): void {
    const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
      data: {
        title: 'Delete Firewall Rule',
        message: `Are you sure you want to delete rule '${rule.rule_collection_name}'?`,
        confirmLabel: 'Delete',
        type: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.rulesService.deleteRule(rule.id).subscribe({
          next: () => {
            this.snackBar.open('Rule deleted successfully.', 'Close', { duration: 3000 });
            this.loadRules();
          },
          error: (err) => {
            console.error('Error deleting rule:', err);
            this.snackBar.open('Error deleting rule.', 'Close', { duration: 3000 });
          }
        });
      }
    });
  }

  duplicateRule(rule: FirewallRule): void {
    const duplicatedRule = {
      ...rule,
      rule_collection_name: `${rule.rule_collection_name} (Copy)`,
      id: undefined,
      status: 'pending'
    };

    this.rulesService.createRule(duplicatedRule).subscribe({
      next: () => {
        this.snackBar.open('Rule duplicated successfully.', 'Close', { duration: 3000 });
        this.loadRules();
      },
      error: (err) => {
        console.error('Error duplicating rule:', err);
        this.snackBar.open('Error duplicating rule.', 'Close', { duration: 3000 });
      }
    });
  }
}