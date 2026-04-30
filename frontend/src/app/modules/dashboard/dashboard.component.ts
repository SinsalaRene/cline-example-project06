import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { StatService, DashboardStat, DashboardChartData, DashboardActivity, QuickAction } from './services/dashboard-stat.service';

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
        private statService: StatService,
        private router: Router
    ) { }

    ngOnInit(): void {
        this.loadDashboardData();
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
    }

    private loadDashboardData(): void {
        this.isLoading = true;

        Promise.all([
            this.loadStats(),
            this.loadChartData(),
            this.loadDistributionData(),
            this.loadActivities(),
            this.loadQuickActions(),
        ]).finally(() => {
            this.isLoading = false;
        });
    }

    private async loadStats(): Promise<void> {
        return new Promise((resolve) => {
            this.statService.getStats().subscribe((stats) => {
                this.stats = stats;
                resolve();
            });
        });
    }

    private async loadChartData(): Promise<void> {
        return new Promise((resolve) => {
            this.statService.getChartData().subscribe((data) => {
                this.chartData = data;
                resolve();
            });
        });
    }

    private async loadDistributionData(): Promise<void> {
        return new Promise((resolve) => {
            this.statService.getDistributionData().subscribe((data) => {
                this.distributionData = data;
                resolve();
            });
        });
    }

    private async loadActivities(): Promise<void> {
        return new Promise((resolve) => {
            this.statService.getActivityFeed().subscribe((activities) => {
                this.activities = activities;
                resolve();
            });
        });
    }

    private async loadQuickActions(): Promise<void> {
        return new Promise((resolve) => {
            this.statService.getQuickActions().subscribe((actions) => {
                this.quickActions = actions;
                resolve();
            });
        });
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