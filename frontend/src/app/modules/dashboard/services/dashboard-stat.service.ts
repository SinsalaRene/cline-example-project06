import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, timer } from 'rxjs';
import { first, map, switchMap } from 'rxjs/operators';

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

@Injectable({
    providedIn: 'any',
})
export class StatService {
    private readonly MOCK_STATS: DashboardStat[] = [
        {
            id: 'firewall-rules',
            title: 'Firewall Rules',
            value: 1247,
            unit: 'active',
            trend: 'up',
            trendValue: 12,
            percentage: 87,
            color: '#2196F3',
            icon: 'shield',
            description: 'Total active firewall rules',
        },
        {
            id: 'blocked-ips',
            title: 'Blocked IPs',
            value: 3842,
            unit: 'total',
            trend: 'up',
            trendValue: 156,
            percentage: 92,
            color: '#F44336',
            icon: 'block',
            description: 'Total blocked IP addresses',
        },
        {
            id: 'active-connections',
            title: 'Active Connections',
            value: 847,
            unit: 'current',
            trend: 'stable',
            trendValue: 2,
            percentage: 45,
            color: '#4CAF50',
            icon: 'wifi',
            description: 'Currently active connections',
        },
        {
            id: 'bandwidth',
            title: 'Bandwidth Usage',
            value: 2.4,
            unit: 'GB/s',
            trend: 'up',
            trendValue: 0.3,
            percentage: 68,
            color: '#FF9800',
            icon: 'speed',
            description: 'Current bandwidth usage',
        },
        {
            id: 'packet-loss',
            title: 'Packet Loss',
            value: 0.02,
            unit: '%',
            trend: 'down',
            trendValue: 0.01,
            percentage: 2,
            color: '#9C27B0',
            icon: 'signal-cellularic',
            description: 'Current packet loss rate',
        },
        {
            id: 'avg-latency',
            title: 'Avg Latency',
            value: 12,
            unit: 'ms',
            trend: 'stable',
            trendValue: 0,
            percentage: 30,
            color: '#00BCD4',
            icon: 'lighthouse',
            description: 'Average network latency',
        },
    ];

    private readonly CHART_DATA: DashboardChartData[] = [
        { label: 'Rules Created', value: 45, date: '2024-01' },
        { label: 'Rules Created', value: 62, date: '2024-02' },
        { label: 'Rules Created', value: 38, date: '2024-03' },
        { label: 'Rules Created', value: 71, date: '2024-04' },
        { label: 'Rules Created', value: 55, date: '2024-05' },
        { label: 'Rules Created', value: 84, date: '2024-06' },
        { label: 'Rules Created', value: 49, date: '2024-07' },
        { label: 'Rules Created', value: 67, date: '2024-08' },
        { label: 'Rules Created', value: 93, date: '2024-09' },
        { label: 'Rules Created', value: 78, date: '2024-10' },
        { label: 'Rules Created', value: 56, date: '2024-11' },
        { label: 'Rules Created', value: 82, date: '2024-12' },
    ];

    private readonly DISTRIBUTION_DATA: DashboardChartData[] = [
        { label: 'TCP Inbound', value: 42, date: '' },
        { label: 'TCP Outbound', value: 28, date: '' },
        { label: 'UDP Inbound', value: 15, date: '' },
        { label: 'UDP Outbound', value: 10, date: '' },
        { label: 'ICMP', value: 5, date: '' },
    ];

    private readonly ACTIVITIES: DashboardActivity[] = [
        {
            id: '1',
            type: 'success',
            message: 'Firewall rule "Allow HTTPS" updated successfully',
            timestamp: new Date(Date.now() - 5 * 60 * 1000),
            source: 'admin',
        },
        {
            id: '2',
            type: 'warning',
            message: 'High traffic detected on port 443',
            timestamp: new Date(Date.now() - 15 * 60 * 1000),
            source: 'monitor',
        },
        {
            id: '3',
            type: 'info',
            message: 'Batch import of IP ranges completed (24 entries)',
            timestamp: new Date(Date.now() - 45 * 60 * 1000),
            source: 'system',
        },
        {
            id: '4',
            type: 'error',
            message: 'Connection timeout to upstream proxy 10.0.0.5:8080',
            timestamp: new Date(Date.now() - 120 * 60 * 1000),
            source: 'proxy',
        },
        {
            id: '5',
            type: 'success',
            message: 'SSL certificate renewal completed',
            timestamp: new Date(Date.now() - 240 * 60 * 1000),
            source: 'system',
        },
    ];

    private readonly QUICK_ACTIONS: QuickAction[] = [
        {
            id: 'add-rule',
            label: 'Add Rule',
            description: 'Create a new firewall rule',
            icon: 'add',
            route: '/rules',
        },
        {
            id: 'block-ip',
            label: 'Block IP',
            description: 'Block an IP address immediately',
            icon: 'block',
            route: '/rules',
        },
        {
            id: 'export-log',
            label: 'Export Logs',
            description: 'Download firewall logs',
            icon: 'download',
            route: '/audit',
        },
        {
            id: 'refresh-data',
            label: 'Refresh Data',
            description: 'Update dashboard metrics',
            icon: 'refresh',
            route: '/dashboard',
        },
        {
            id: 'add-tag',
            label: 'Add Tag',
            description: 'Create a new tag for categorization',
            icon: 'add_tag',
            route: '/settings',
        },
        {
            id: 'bulk-import',
            label: 'Bulk Import',
            description: 'Import multiple rules or IPs',
            icon: 'upload_file',
            route: '/rules',
        },
        {
            id: 'run-report',
            label: 'Run Report',
            description: 'Generate a compliance report',
            icon: 'assessment',
            route: '/audit',
        },
        {
            id: 'schedule-maint',
            label: 'Schedule Maintenance',
            description: 'Plan maintenance window',
            icon: 'event',
            route: '/settings',
        },
    ];

    private statsSubject: BehaviorSubject<DashboardStat[]> = new BehaviorSubject<DashboardStat[]>([]);

    constructor() {
        this.statsSubject.next(this.MOCK_STATS);
    }

    getStats(): Observable<DashboardStat[]> {
        return of(this.MOCK_STATS);
    }

    getStatById(id: string): Observable<DashboardStat | undefined> {
        return of(this.MOCK_STATS.find((s) => s.id === id));
    }

    getChartData(): Observable<DashboardChartData[]> {
        return of(this.CHART_DATA);
    }

    getDistributionData(): Observable<DashboardChartData[]> {
        return of(this.DISTRIBUTION_DATA);
    }

    getActivityFeed(): Observable<DashboardActivity[]> {
        return of(this.ACTIVITIES);
    }

    getQuickActions(): Observable<QuickAction[]> {
        return of(this.QUICK_ACTIONS);
    }

    simulateStatsUpdate(): Observable<DashboardStat[]> {
        return timer(2000).pipe(
            switchMap(() => {
                const updatedStats = this.MOCK_STATS.map((stat) => {
                    const variation = (Math.random() - 0.5) * 0.1;
                    const newValue = Math.max(0, stat.value * (1 + variation));
                    return {
                        ...stat,
                        value: parseFloat(newValue.toFixed(2)),
                    };
                });
                this.statsSubject.next(updatedStats);
                return of(updatedStats);
            })
        );
    }
}