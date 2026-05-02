import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { DashboardStatService } from './dashboard-stat.service';

describe('DashboardStatService', () => {
    let service: DashboardStatService;
    let httpTestingController: HttpTestingController;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [DashboardStatService]
        });

        service = TestBed.inject(DashboardStatService);
        httpTestingController = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpTestingController.verify();
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('getDashboardStats', () => {
        it('should return dashboard statistics', () => {
            const mockStats = {
                totalRules: 150,
                activeRules: 120,
                pendingApprovals: 5,
                recentActivity: []
            };

            service.getDashboardStats().subscribe(stats => {
                expect(stats.totalRules).toBe(150);
                expect(stats.activeRules).toBe(120);
                expect(stats.pendingApprovals).toBe(5);
            });

            const req = httpTestingController.expectOne('/api/dashboard/stats');
            expect(req.request.method).toBe('GET');
            req.flush(mockStats);
        });
    });

    describe('getActivityFeed', () => {
        it('should return activity feed', () => {
            const mockActivity = [
                { id: '1', message: 'Test activity', timestamp: new Date().toISOString() }
            ];

            service.getActivityFeed().subscribe(activity => {
                expect(activity.length).toBe(1);
            });

            const req = httpTestingController.expectOne('/api/dashboard/activity');
            expect(req.request.method).toBe('GET');
            req.flush(mockActivity);
        });
    });

    describe('getWorkloadStats', () => {
        it('should return workload statistics', () => {
            const mockStats = {
                totalWorkloads: 25,
                activeWorkloads: 20,
                pausedWorkloads: 5
            };

            service.getWorkloadStats().subscribe(stats => {
                expect(stats.totalWorkloads).toBe(25);
                expect(stats.activeWorkloads).toBe(20);
            });

            const req = httpTestingController.expectOne('/api/dashboard/workloads');
            expect(req.request.method).toBe('GET');
            req.flush(mockStats);
        });
    });

    describe('getCachedStats', () => {
        it('should return cached stats when available', () => {
            const mockStats = {
                totalRules: 150,
                activeRules: 120,
                pendingApprovals: 5,
                recentActivity: []
            };

            service.getCachedStats().subscribe(stats => {
                expect(stats.totalRules).toBe(150);
            });

            const req = httpTestingController.expectOne('/api/dashboard/stats');
            expect(req.request.method).toBe('GET');
            req.flush(mockStats);
        });
    });
});