import { Component, OnInit, ViewChild } from '@angular/core';
import { MatTableDataSource } from '@angular/material/table';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { MatDialog } from '@angular/material/dialog';
import { RulesService, FirewallRule } from '../services/rules.service';

@Component({
    selector: 'app-rules-list',
    template: `
    <div class="rules-container">
      <h2>Firewall Rules</h2>
      <div class="toolbar">
        <button mat-raised-button color="primary" (click)="openCreateDialog()">
          New Rule
        </button>
        <mat-form-field>
          <input matInput (keyup)="applyFilter($event)" placeholder="Search...">
        </mat-form-field>
      </div>
      <table mat-table [dataSource]="dataSource" matSort>
        <ng-container matColumnDef="name">
          <th mat-header-cell *matHeaderCellDef>Rule Name</th>
          <td mat-cell *matCellDef="let rule">{{ rule.rule_collection_name }}</td>
        </ng-container>
        <ng-container matColumnDef="priority">
          <th mat-header-cell *matHeaderCellDef>Priority</th>
          <td mat-cell *matCellDef="let rule">{{ rule.priority }}</td>
        </ng-container>
        <ng-container matColumnDef="action">
          <th mat-header-cell *matHeaderCellDef>Action</th>
          <td mat-cell *matCellDef="let rule">{{ rule.action }}</td>
        </ng-container>
        <ng-container matColumnDef="protocol">
          <th mat-header-cell *matHeaderCellDef>Protocol</th>
          <td mat-cell *matCellDef="let rule">{{ rule.protocol }}</td>
        </ng-container>
        <ng-container matColumnDef="status">
          <th mat-header-cell *matHeaderCellDef>Status</th>
          <td mat-cell *matCellDef="let rule">
            <span [class]="rule.status">{{ rule.status }}</span>
          </td>
        </ng-container>
        <ng-container matColumnDef="actions">
          <th mat-header-cell *matHeaderCellDef>Actions</th>
          <td mat-cell *matCellDef="let rule">
            <button mat-icon-button color="primary" (click)="editRule(rule)">
              <mat-icon>edit</mat-icon>
            </button>
            <button mat-icon-button color="warn" (click)="deleteRule(rule)">
              <mat-icon>delete</mat-icon>
            </button>
          </td>
        </ng-container>
        <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
        <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
      </table>
      <mat-paginator [pageSizeOptions]="[5, 10, 25, 100]" showFirstLastButtons></mat-paginator>
    </div>
  `,
    styles: [`
    .rules-container { padding: 20px; }
    .toolbar { display: flex; gap: 10px; margin-bottom: 20px; }
    .active { color: green; }
    .pending { color: orange; }
    .deleted { color: gray; }
    .error { color: red; }
  `]
})
export class RulesListComponent implements OnInit {
    displayedColumns: string[] = ['name', 'priority', 'action', 'protocol', 'status', 'actions'];
    dataSource: MatTableDataSource<FirewallRule> = new MatTableDataSource<FirewallRule>();

    @ViewChild(MatPaginator) paginator!: MatPaginator;
    @ViewChild(MatSort) sort!: MatSort;

    constructor(private rulesService: RulesService, private dialog: MatDialog) { }

    ngOnInit(): void {
        this.loadRules();
    }

    loadRules(): void {
        this.rulesService.getRules().subscribe({
            next: (response) => {
                this.dataSource = new MatTableDataSource<FirewallRule>(response.items || []);
                this.dataSource.paginator = this.paginator;
                this.dataSource.sort = this.sort;
            },
            error: (err) => console.error('Error loading rules:', err)
        });
    }

    applyFilter(event: Event): void {
        const filterValue = (event.target as HTMLInputElement).value;
        this.dataSource.filter = filterValue.trim().toLowerCase();
        if (this.dataSource.paginator) {
            this.dataSource.paginator.firstPage();
        }
    }

    openCreateDialog(): void {
        // Open create dialog
    }

    editRule(rule: FirewallRule): void {
        // Open edit dialog
    }

    deleteRule(rule: FirewallRule): void {
        if (confirm(`Delete rule '${rule.rule_collection_name}'?`)) {
            this.rulesService.deleteRule(rule.id).subscribe({
                next: () => this.loadRules(),
                error: (err) => console.error('Error deleting rule:', err)
            });
        }
    }
}