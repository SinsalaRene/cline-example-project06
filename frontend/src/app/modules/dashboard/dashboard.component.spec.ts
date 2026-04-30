import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterTestingModule } from '@angular/router/testing';
import { DashboardComponent } from './dashboard.component';
import { StatService, DashboardStat, DashboardChartData, DashboardActivity, QuickAction } from './services/dashboard-stat.service';
import { of } from 'rxjs';
import { Router } from '@angular/router';

describe('DashboardComponent', () => {
    let component: DashboardComponent;
    let fixture: ComponentFixture<DashboardComponent>;
    let statService: StatService;
    let router: Router;

    const mockStats: DashboardStat[] = [
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
    ];

    const mockChartData: DashboardChartData[] = [
        { label: 'Rules Created', value: 45, date: '2024-01' },
        { label: 'Rules Created', value: 62, date: '2024-02' },
        { label: 'Rules Created', value: 38, date: '2024-03' },
    ];

    const mockDistributionData: DashboardChartData[] = [
        { label: 'TCP Inbound', value: 42, date: '' },
        { label: 'TCP Outbound', value: 28, date: '' },
        { label: 'UDP Inbound', value: 15, date: '' },
    ];

    const mockActivities: DashboardActivity[] = [
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
    ];

    const mockQuickActions: QuickAction[] = [
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
    ];

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            declarations: [DashboardComponent],
            imports: [ReactiveFormsModule, RouterTestingModule],
            providers: [
                {
                    provide: StatService,
                    useValue: {
                        getStats: () => of(mockStats),
                        getChartData: () => of(mockChartData),
                        getDistributionData: () => of(mockDistributionData),
                        getActivityFeed: () => of(mockActivities),
                        getQuickActions: () => of(mockQuickActions),
                    },
                },
            ],
            schemas: [NO_ERRORS_SCHEMA],
        }).compileComponents();
    });

    beforeEach(() => {
        fixture = TestBed.createComponent(DashboardComponent);
        component = fixture.componentInstance;
        statService = TestBed.inject(StatService);
        router = TestBed.inject(Router);
        fixture.detectChanges();
    });

    it('should create the dashboard component', () => {
        expect(component).toBeTruthy();
    });

    it('should initialize with empty arrays when service returns empty', () => {
        TestBed.overrideComponent(DashboardComponent, {
            set: {
                providers: [
                    {
                        provide: StatService,
                        useValue: {
                            getStats: () => of([]),
                            getChartData: () => of([]),
                            getDistributionData: () => of([]),
                            getActivityFeed: () => of([]),
                            getQuickActions: () => of([]),
                        },
                    },
                ],
            },
        });

        const newFixture = TestBed.createComponent(DashboardComponent);
        const newComponent = newFixture.componentInstance;
        newFixture.detectChanges();

        expect(newComponent.stats).toEqual([]);
        expect(newComponent.chartData).toEqual([]);
        expect(newComponent.distributionData).toEqual([]);
        expect(newComponent.activities).toEqual([]);
        expect(newComponent.quickActions).toEqual([]);
    });

    it('should load stats on init', () => {
        expect(component.stats).toEqual(mockStats);
    });

    it('should load chart data on init', () => {
        expect(component.chartData).toEqual(mockChartData);
    });

    it('should load distribution data on init', () => {
        expect(component.distributionData).toEqual(mockDistributionData);
    });

    it('should load activities on init', () => {
        expect(component.activities).toEqual(mockActivities);
    });

    it('should load quick actions on init', () => {
        expect(component.quickActions).toEqual(mockQuickActions);
    });

    it('should get trend icon for upward trend', () => {
        const icon = component.getTrendIcon('up');
        expect(icon).toBe('arrow_upward');
    });

    it('should get trend icon for downward trend', () => {
        const icon = component.getTrendIcon('down');
        expect(icon).toBe('arrow_downward');
    });

    it('should get trend icon for stable trend', () => {
        const icon = component.getTrendIcon('stable');
        expect(icon).toBe('remove');
    });

    it('should get trend icon for unknown trend', () => {
        const icon = component.getTrendIcon('unknown' as any);
        expect(icon).toBe('remove');
    });

    it('should get trend color for upward trend', () => {
        const color = component.getTrendColor('up');
        expect(color).toBe('#4CAF50');
    });

    it('should get trend color for downward trend', () => {
        const color = component.getTrendColor('down');
        expect(color).toBe('#F44336');
    });

    it('should get trend color for stable trend', () => {
        const color = component.getTrendColor('stable');
        expect(color).toBe('#9E9E9E');
    });

    it('should get trend color for unknown trend', () => {
        const color = component.getTrendColor('unknown' as any);
        expect(color).toBe('#9E9E9E');
    });

    it('should get activity icon for success type', () => {
        const icon = component.getActivityIcon('success');
        expect(icon).toBe('check_circle');
    });

    it('should get activity icon for warning type', () => {
        const icon = component.getActivityIcon('warning');
        expect(icon).toBe('warning');
    });

    it('should get activity icon for error type', () => {
        const icon = component.getActivityIcon('error');
        expect(icon).toBe('error');
    });

    it('should get activity icon for info type', () => {
        const icon = component.getActivityIcon('info');
        expect(icon).toBe('info');
    });

    it('should get activity icon for unknown type', () => {
        const icon = component.getActivityIcon('unknown' as any);
        expect(icon).toBe('info');
    });

    it('should format timestamp as just now when difference is less than 1 minute', () => {
        const now = new Date();
        const result = component.formatTimestamp(now);
        expect(result).toBe('Just now');
    });

    it('should format timestamp as minutes ago when difference is less than 1 hour', () => {
        const past = new Date(Date.now() - 5 * 60000);
        const result = component.formatTimestamp(past);
        expect(result).toBe('5m ago');
    });

    it('should format timestamp as hours ago when difference is less than 24 hours', () => {
        const past = new Date(Date.now() - 2 * 3600000);
        const result = component.formatTimestamp(past);
        expect(result).toBe('2h ago');
    });

    it('should format timestamp as date string when difference is more than 24 hours', () => {
        const past = new Date(Date.now() - 25 * 3600000);
        const result = component.formatTimestamp(past);
        expect(result).toBeTruthy();
        expect(typeof result).toBe('string');
    });

    it('should navigate to action route', () => {
        const navigateSpy = jasmine.createSpy('navigate');
        (router as any).navigate = navigateSpy;

        const action: QuickAction = {
            id: 'test',
            label: 'Test',
            description: 'Test action',
            icon: 'test',
            route: '/test/route',
        };

        component.navigateToAction(action);
        expect(navigateSpy).toHaveBeenCalledWith(['/test/route']);
    });

    it('should set isLoading to true when refreshData is called', () => {
        expect(component.isLoading).toBe(false);
        component.refreshData();
        expect(component.isLoading).toBe(true);
    });

    it('should have isLoading set to false after initialization', () => {
        expect(component.isLoading).toBe(false);
    });
});