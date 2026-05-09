/**
 * VNet Detail Component
 *
 * Displays detailed information about a specific Azure Virtual Network (VNet).
 * Shows VNet properties, attached subnets, NSGs, and provides action buttons
 * for creating new subnets or NSGs.
 *
 * @module vnet-detail-component
 * @author Network Module Team
 * @since 1.0.0
 */

import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule as NgFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';
import { take } from 'rxjs/operators';
import { NetworkService } from '../../services/network.service';
import { VirtualNetwork, Subnet, NetworkSecurityGroup, TopologyNode } from '../../models/network.model';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatDialogModule, MatDialog, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';

/** Dialog data for creating a new subnet. */
export interface CreateSubnetDialogData {
    vnet: VirtualNetwork;
}

/** Dialog result for creating a new subnet. */
export interface CreateSubnetDialogResult {
    subnetName: string;
    addressPrefix: string;
}

/** Dialog data for creating a new NSG. */
export interface CreateNsgDialogData {
    vnet: VirtualNetwork;
}

/** Dialog result for creating a new NSG. */
export interface CreateNsgDialogResult {
    nsgName: string;
    resourceGroup: string;
}

/**
 * VNet Detail Component.
 *
 * Displays detailed information about a specific Azure Virtual Network (VNet).
 * Shows VNet properties, attached subnets, NSGs, and provides action buttons
 * for creating new subnets or NSGs.
 *
 * @selector app-vnet-detail
 * @standalone
 */
@Component({
    selector: 'app-vnet-detail',
    templateUrl: './vnet-detail.component.html',
    styleUrls: ['./vnet-detail.component.css'],
    changeDetection: ChangeDetectionStrategy.OnPush,
    encapsulation: ViewEncapsulation.None,
    imports: [
        CommonModule,
        FormsModule,
        MatCardModule,
        MatButtonModule,
        MatIconModule,
        MatTableModule,
        MatChipsModule,
        MatDividerModule,
        MatDialogModule,
        MatTooltipModule,
        MatSnackBarModule,
    ],
    standalone: true,
})
export class VnetDetailComponent implements OnInit, OnDestroy {
    private destroy$ = new Subject<void>();

    /** The loaded Virtual Network. */
    public vnet: VirtualNetwork | null = null;

    /** Loading state. */
    public isLoading = true;

    /** Error message. */
    public error: string | null = null;

    /** Subnets attached to this VNet. */
    public subnets: Subnet[] = [];

    /** NSGs attached to this VNet. */
    public nsgs: NetworkSecurityGroup[] = [];

    /** Table columns for subnets. */
    public subnetColumns = ['name', 'addressPrefix', 'nsgCount', 'actions'];

    /** Table columns for NSGs. */
    public nsgColumns = ['name', 'location', 'ruleCount', 'actions'];

    /**
     * Creates a new VnetDetailComponent.
     *
     * @param route - The activated route for parameter access.
     * @param router - The Angular router for navigation.
     * @param networkService - The network service for API calls.
     * @param dialog - The Angular Material dialog service.
     * @param snackBar - The Angular Material snackbar service.
     */
    constructor(
        private route: ActivatedRoute,
        private router: Router,
        private networkService: NetworkService,
        public dialog: MatDialog,
        public snackBar: MatSnackBar
    ) { }

    /**
     * Lifecycle hook called after project initialization.
     * Loads VNet details from the API.
     */
    ngOnInit(): void {
        const id = this.route.snapshot.paramMap.get('id');
        if (id) {
            this.loadVnet(id);
        } else {
            this.error = 'No VNet ID provided in URL';
            this.isLoading = false;
        }
    }

    /**
     * Lifecycle hook called before component destruction.
     * Cleans up subscriptions.
     */
    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    /**
     * Load VNet details from the API.
     *
     * @param id - The VNet ID.
     */
    loadVnet(id: string): void {
        this.isLoading = true;
        this.error = null;

        this.networkService.getVnet(id).pipe(take(1)).subscribe({
            next: (vnet) => {
                this.vnet = vnet;
                this.loadSubnets(vnet);
                this.loadNsgs(vnet);
                this.isLoading = false;
            },
            error: (err: Error) => {
                this.error = `Failed to load VNet: ${err.message}`;
                this.isLoading = false;
            }
        });
    }

    /**
     * Load subnets for the VNet.
     *
     * @param vnet - The VNet to load subnets for.
     */
    loadSubnets(vnet: VirtualNetwork): void {
        if (!vnet || !vnet.id) return;

        this.networkService.getSubnets(vnet.id).pipe(take(1)).subscribe({
            next: (subnets) => {
                this.subnets = subnets;
            },
            error: (err: Error) => {
                this.error = `Failed to load subnets: ${err.message}`;
            }
        });
    }

    /**
     * Load NSGs for the VNet.
     *
     * @param vnet - The VNet to load NSGs for.
     */
    loadNsgs(vnet: VirtualNetwork): void {
        if (!vnet || !vnet.id) return;

        this.networkService.getNsgs().pipe(take(1)).subscribe({
            next: (nsgs) => {
                // NSGs reference subnets, filter by checking if any subnet belongs to this VNet
                this.nsgs = nsgs.filter(
                    (nsg) => nsg.subnets?.some((s) => s.vnetId === vnet.id || s.id === vnet.id)
                ) || [];
            },
            error: (err: Error) => {
                this.error = `Failed to load NSGs: ${err.message}`;
            }
        });
    }

    /**
     * Navigate back to the network topology view.
     */
    navigateBack(): void {
        this.router.navigate(['/network']);
    }

    /**
     * Open dialog to create a new subnet.
     */
    createSubnet(): void {
        if (!this.vnet) return;

        const dialogRef = this.dialog.open(CreateSubnetDialogComponent, {
            data: { vnet: this.vnet },
            width: '400px',
        });

        dialogRef.afterClosed().subscribe((result: CreateSubnetDialogResult | undefined) => {
            if (result) {
                this.networkService.createSubnet({
                    name: result.subnetName,
                    addressPrefix: result.addressPrefix,
                    vnetId: this.vnet!.id,
                }).subscribe({
                    next: () => {
                        this.loadSubnets(this.vnet!);
                        this.snackBar.open('Subnet created successfully', 'Close', { duration: 3000 });
                    },
                    error: (err: Error) => {
                        this.error = `Failed to create subnet: ${err.message}`;
                    }
                });
            }
        });
    }

    /**
     * Open dialog to create a new NSG.
     */
    createNsg(): void {
        if (!this.vnet) return;

        const dialogRef = this.dialog.open(CreateNsgDialogComponent, {
            data: { vnet: this.vnet },
            width: '400px',
        });

        dialogRef.afterClosed().subscribe((result: CreateNsgDialogResult | undefined) => {
            if (result) {
                this.networkService.createNsg({
                    name: result.nsgName,
                    resourceGroup: result.resourceGroup || this.vnet!.resourceGroup,
                    location: this.vnet!.location || 'eastus',
                    vnetId: this.vnet!.id,
                }).subscribe({
                    next: () => {
                        this.loadNsgs(this.vnet!);
                        this.snackBar.open('NSG created successfully', 'Close', { duration: 3000 });
                    },
                    error: (err: Error) => {
                        this.error = `Failed to create NSG: ${err.message}`;
                    }
                });
            }
        });
    }

    /**
     * Delete a subnet.
     *
     * @param subnetId - The subnet ID to delete.
     */
    deleteSubnet(subnetId: string): void {
        this.networkService.deleteSubnet(subnetId).subscribe({
            next: () => {
                this.subnets = this.subnets.filter((s) => s.id !== subnetId);
                this.snackBar.open('Subnet deleted', 'Close', { duration: 3000 });
            },
            error: (err: Error) => {
                this.error = `Failed to delete subnet: ${err.message}`;
            }
        });
    }

    /**
     * Delete an NSG.
     *
     * @param nsgId - The NSG ID to delete.
     */
    deleteNsg(nsgId: string): void {
        this.networkService.deleteNsg(nsgId).subscribe({
            next: () => {
                this.nsgs = this.nsgs.filter((n) => n.id !== nsgId);
                this.snackBar.open('NSG deleted', 'Close', { duration: 3000 });
            },
            error: (err: Error) => {
                this.error = `Failed to delete NSG: ${err.message}`;
            }
        });
    }
}

/**
 * Create Subnet Dialog Component.
 */
@Component({
    selector: 'app-create-subnet-dialog',
    templateUrl: './create-subnet-dialog.component.html',
    imports: [
        CommonModule,
        ReactiveFormsModule,
        MatDialogModule,
        MatFormFieldModule,
        MatInputModule,
        MatButtonModule,
    ],
    standalone: true,
})
export class CreateSubnetDialogComponent {
    /** Form data for subnet name. */
    public subnetName = '';

    /** Form data for address prefix. */
    public addressPrefix = '';

    /** The VNet from dialog data. */
    public vnet: VirtualNetwork | undefined;

    /**
     * Creates a new CreateSubnetDialogComponent.
     *
     * @param dialogRef - Dialog reference for closing.
     * @param data - Dialog data containing the VNet.
     */
    constructor(
        public dialogRef: MatDialogRef<CreateSubnetDialogComponent>,
        public data: CreateSubnetDialogData
    ) {
        this.vnet = data.vnet;
    }

    /**
     * Handle submit event.
     */
    onSubmit(): void {
        if (this.subnetName && this.addressPrefix) {
            this.dialogRef.close({ subnetName: this.subnetName, addressPrefix: this.addressPrefix });
        }
    }

    /**
     * Handle cancel event.
     */
    onCancel(): void {
        this.dialogRef.close();
    }
}

/**
 * Create NSG Dialog Component.
 */
@Component({
    selector: 'app-create-nsg-dialog',
    templateUrl: './create-nsg-dialog.component.html',
    imports: [
        CommonModule,
        ReactiveFormsModule,
        MatDialogModule,
        MatFormFieldModule,
        MatInputModule,
        MatButtonModule,
    ],
    standalone: true,
})
export class CreateNsgDialogComponent {
    /** Form data for NSG name. */
    public nsgName = '';

    /** Form data for resource group. */
    public resourceGroup = '';

    /** The VNet from dialog data. */
    public vnet: VirtualNetwork | undefined;

    /**
     * Creates a new CreateNsgDialogComponent.
     *
     * @param dialogRef - Dialog reference for closing.
     * @param data - Dialog data containing the VNet.
     */
    constructor(
        public dialogRef: MatDialogRef<CreateNsgDialogComponent>,
        public data: CreateNsgDialogData
    ) {
        this.vnet = data.vnet;
        if (data.vnet) {
            this.resourceGroup = data.vnet.resourceGroup || '';
        }
    }

    /**
     * Handle submit event.
     */
    onSubmit(): void {
        if (this.nsgName) {
            this.dialogRef.close({ nsgName: this.nsgName, resourceGroup: this.resourceGroup });
        }
    }

    /**
     * Handle cancel event.
     */
    onCancel(): void {
        this.dialogRef.close();
    }
}
