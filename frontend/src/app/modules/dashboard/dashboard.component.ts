import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { Subject, forkJoin, Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { HttpParams } from '@angular/common/http';
import { ApiService, ApiResponse } from '../../core/services/api.service';

export interface DashboardStat {
    id: string;
    title: string;
    value: number;
    unit: string;
    trend: 'up' | 'down' | 'stable';
    trendValue: number;
    percentage: number;
    color: string;
    icon: string;
    description: string;
}

export interface DashboardChartData {
    label: string;
    value: number;
    date: string;
}

export interface DashboardActivity {
    id: string;
    type: 'info' | 'warning' | 'error' | 'success';
    message: string;
    timestamp: Date;
    source: string;
}

export interface QuickAction {
    id: string;
    label: string;
    description: string;
    icon: string;
    route: string;
    permission?: string;
}

@Component({
    selector: 'app-dashboard',
    templateUrl: './dashboard.component.html',
    styleUrls: ['./dashboard.component.css'],
})
export class DashboardComponent implements OnInit, OnDestroy {
    private destroy$ = new Subject<void>();

    stats: DashboardStat[] = [];
    chartData: DashboardChartData[] = [];
    distributionData: DashboardChartData[] = [];
    activities: DashboardActivity[] = [];
    quickActions: QuickAction[] = [];
    isLoading = true;

    constructor(
        private api: ApiService,
        private router: Router
    ) { }

    ngOnInit(): void {
        this.loadQuickActions(); // static
        this.loadDashboardData();
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    private loadDashboardData(): void {
        this.isLoading = true;

        forkJoin({
            stats: this.loadStats(),
            chartData: this.loadChartData(),
            distributionData: this.loadDistributionData(),
            activities: this.loadActivities(),
        }).subscribe({
            next: ({ stats, chartData, distributionData, activities }) => {
                this.stats = stats;
                this.chartData = chartData;
                this.distributionData = distributionData;
                this.activities = activities;
                this.isLoading = false;
            },
            error: (err) => {
                console.error('Dashboard load error', err);
                this.isLoading = false;
            }
        });
    }

    private loadStats(): Observable<DashboardStat[]> {
        const params = new HttpParams().set('pageSize', '1');

        return forkJoin({
            rules: this.api.get('/rules', params),
            approvals: this.api.get('/approvals', params.set('status', 'pending')),
        }).pipe(
            map(({ rules, approvals }: { rules: ApiResponse<any>, approvals: ApiResponse<any> }) => [
                {
                    id: 'firewall-rules',
                    title: 'Firewall Rules',
                    value: rules.total || 0,
                    unit: 'rules',
                    trend: 'stable' as const,
                    trendValue: 0,
                    percentage: 0,
                    color: '#2196F3',
                    icon: 'shield',
                    description: 'Total active firewall rules',
                },
                {
                    id: 'pending-approvals',
                    title: 'Pending Approvals',
                    value: approvals.total || 0,
                    unit: 'requests',
                    trend: 'up' as const,
                    trendValue: 0,
                    percentage: 0,
                    color: '#FF9800',
                    icon: 'approval',
                    description: 'Pending approval requests',
                },
            ])
        );
    }

    private loadChartData(): Observable<DashboardChartData[]> {
        // Static for now, or fetch time series if backend supports
        return of([
            { label: 'Jan', value: 45, date: '2024-01' },
            { label: 'Feb', value: 62, date: '2024-02' },
            // ... 
        ]);
    }

    private loadDistributionData(): Observable<DashboardChartData[]> {
        // Static protocol distribution
        return of([
            { label: 'TCP', value: 42, date: '' },
            { label: 'UDP', value: 28, date: '' },
            { label: 'ICMP', value: 15, date: '' },
            { label: 'Other', value: 15, date: '' },
        ]);
    }

    private loadActivities(): Observable<DashboardActivity[]> {
        const params = new HttpParams()
            .set('limit', '5')
            .set('sort', '-timestamp');

        return this.api.get('/audit', params).pipe(
            map((response: ApiResponse<any>) => {
                return (response.items || []).map((item: any) => ({
                    id: item.id,
                    type: this.mapAuditLevel(item.level || 'info') as any,
                    message: item.message || 'Audit event',
                    timestamp: new Date(item.timestamp),
                    source: item.user_id || item.actor || 'system',
                }));
            })
        );
    }

    private loadQuickActions(): void {
        this.quickActions = [
            {
                id: 'add-rule',
                label: 'Add Rule',
                description: 'Create a new firewall rule',
                icon: 'add',
                route: '/rules',
            },
            {
                id: 'view-approvals',
                label: 'View Approvals',
                description: 'Review pending approvals',
                icon: 'approval',
                route: '/approvals',
            },
            {
                id: 'audit-log',
                label: 'Audit Log',
                description: 'View recent audit events',
                icon: 'history',
                route: '/audit',
            },
        ];
    }

    private mapAuditLevel(level: string): 'info' | 'warning' | 'error' | 'success' {
        switch (level.toLowerCase()) {
            case 'success':
            case 'info':
                return 'info';
            case 'warning':
                return 'warning';
            case 'error':
            case 'critical':
                return 'error';
            default:
                return 'info';
        }
    }

    navigateToAction(action: QuickAction): void {
        this.router.navigate([action.route]);
    }

    refreshData(): void {
        this.isLoading = true;
        this.loadDashboardData();
    }

    getTrendIcon(trend: string): string {
        switch (trend) {
            case 'up':
                return 'arrow_upward';
            case 'down':
                return 'arrow_downward';
            default:
                return 'remove';
        }
    }

    getTrendColor(trend: string): string {
        switch (trend) {
            case 'up':
                return '#4CAF50';
            case 'down':
                return '#F44336';
            default:
                return '#9E9E9E';
        }
    }

    getActivityIcon(type: string): string {
        switch (type) {
            case 'success':
                return 'check_circle';
            case 'warning':
                return 'warning';
            case 'error':
                return 'error';
            case 'info':
                return 'info';
            default:
                return 'info';
        }
    }

    formatTimestamp(date: Date): string {
        const now = new Date();
        const diff = now.getTime() - new Date(date).getTime();
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);

        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        return new Date(date).toLocaleDateString();
    }
}