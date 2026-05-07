import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatMenuModule } from '@angular/material/menu';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatTableModule } from '@angular/material/table';
import { FormsModule } from '@angular/forms';
import { WorkloadsService } from '../services/workloads.service';
import { Workload } from '../models/workload.model';
import { ConfirmationDialogComponent } from './confirmation-dialog.component';

/**
 * Interface summarizing a firewall rule for display in the detail view.
 *
 * @interface RuleSummary
 * @description A lightweight representation of a firewall rule showing only key fields
 * relevant for the workload detail page rule association sections.
 */
interface RuleSummary {
    id: string;
    name: string;
    priority: number;
    action: string;
    protocol: string;
    associatedType: 'include' | 'exclude';
}

/**
 * WorkloadDetailComponent - Displays detailed information about a single workload.
 *
 * @component
 * @description Shows workload metadata in a card layout with tabs for associated
 * firewall rules and available rules. Supports:
 * - Viewing full workload properties
 * - Associating/disassociating firewall rules
 * - Deleting the workload with confirmation
 * - Navigating to the edit form
 *
 * @example
 * ```html
 * <!-- Accessed via: /workloads/:id -->
 * ```
 */
@Component({
    selector: 'app-workload-detail',
    standalone: false,
    templateUrl: './workload-detail.component.html',
    styleUrls: ['./workload-detail.component.css']
})
export class WorkloadDetailComponent implements OnInit {
    /** The loaded workload entity. */
    workload: Workload | null = null;
    /** Indicates whether workload data is being loaded. */
    isLoading = true;
    /** The workload ID extracted from the route parameter. */
    workloadId: string = '';
    /** Rules directly associated with this workload. */
    associatedRules: RuleSummary[] = [];
    /** Available rules that can be associated with this workload. */
    availableRules: RuleSummary[] = [];

    /**
     * Creates an instance of WorkloadDetailComponent.
     */
    constructor(
        private route: ActivatedRoute,
        private workloadsService: WorkloadsService,
        private dialog: MatDialog,
        private snackBar: MatSnackBar,
        private router: Router
    ) { }

    /**
     * Initializes the component by loading workload data from the route.
     */
    ngOnInit(): void {
        const id = this.route.snapshot.paramMap.get('id');
        if (id) {
            this.workloadId = id;
            this.loadWorkload(id);
        }
    }

    /**
     * Loads the workload entity and its associated rules.
     *
     * @param id - The workload identifier.
     */
    loadWorkload(id: string): void {
        this.isLoading = true;
        this.workloadsService.getWorkload(id).subscribe({
            next: (workload: Workload) => {
                this.workload = workload;
                this.loadAssociatedRules(id);
                this.isLoading = false;
            },
            error: (error) => {
                this.isLoading = false;
                this.snackBar.open('Error loading workload: ' + error.message, 'Close', { duration: 3000 });
            }
        });
    }

    /**
     * Loads firewall rules associated with this workload.
     *
     * @param id - The workload identifier.
     */
    loadAssociatedRules(id: string): void {
        this.workloadsService.getWorkloadRules(id).subscribe({
            next: (rules: any[]) => {
                this.associatedRules = rules.map((r: any) => ({
                    id: r.id,
                    name: r.name || r.rule_collection_name,
                    priority: r.priority,
                    action: r.action,
                    protocol: r.protocol,
                    associatedType: 'include'
                }));
            },
            error: (error) => {
                this.snackBar.open('Error loading rules: ' + error.message, 'Close', { duration: 3000 });
            }
        });
    }

    /**
     * Associates a firewall rule with this workload.
     *
     * @param ruleId - The firewall rule identifier.
     * @param associationType - Whether the rule includes or excludes this workload.
     */
    associateRule(ruleId: string, associationType: 'include' | 'exclude'): void {
        if (!this.workloadId) return;

        this.workloadsService.associateRule(this.workloadId, ruleId, associationType).subscribe({
            next: () => {
                this.snackBar.open('Rule associated successfully', 'Close', { duration: 3000 });
                this.loadAssociatedRules(this.workloadId);
            },
            error: (error) => {
                this.snackBar.open('Error associating rule: ' + error.message, 'Close', { duration: 3000 });
            }
        });
    }

    /**
     * Disassociates a firewall rule from this workload.
     *
     * @param ruleId - The firewall rule identifier to disassociate.
     */
    disassociateRule(ruleId: string): void {
        if (!this.workloadId) return;

        this.workloadsService.disassociateRule(this.workloadId, ruleId).subscribe({
            next: () => {
                this.snackBar.open('Rule disassociated successfully', 'Close', { duration: 3000 });
                this.loadAssociatedRules(this.workloadId);
            },
            error: (error) => {
                this.snackBar.open('Error disassociating rule: ' + error.message, 'Close', { duration: 3000 });
            }
        });
    }

    /**
     * Deletes the current workload after confirmation.
     */
    deleteWorkload(): void {
        if (!this.workload || !this.workloadId) return;

        const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
            data: {
                title: 'Delete Workload',
                message: `Are you sure you want to delete "${this.workload.name}"? This action cannot be undone.`,
                confirmLabel: 'Delete',
                cancelLabel: 'Cancel'
            }
        });

        dialogRef.afterClosed().subscribe(result => {
            if (result) {
                this.workloadsService.deleteWorkload(this.workloadId!).subscribe({
                    next: () => {
                        this.snackBar.open('Workload deleted successfully', 'Close', { duration: 3000 });
                        this.router.navigate(['/workloads']);
                    },
                    error: (error) => {
                        this.snackBar.open('Error deleting workload: ' + error.message, 'Close', { duration: 3000 });
                    }
                });
            }
        });
    }

    /**
     * Navigates to the edit form for the current workload.
     */
    editWorkload(): void {
        if (this.workloadId) {
            this.router.navigate(['/workloads', this.workloadId, 'edit']);
        }
    }

    /**
     * Formats a date string for display.
     *
     * @param date - ISO date string.
     * @returns Locally formatted date string.
     */
    formatDateTime(date: string): string {
        return new Date(date).toLocaleString();
    }

    /**
     * Converts the tags object to an array for template display.
     *
     * @returns Array of { key, value } objects.
     */
    getTagsArray(): Array<{ key: string; value: string }> {
        if (!this.workload?.tags) return [];
        return Object.entries(this.workload.tags).map(([key, value]) => ({ key, value }));
    }
}
