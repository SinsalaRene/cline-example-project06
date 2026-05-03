import { TestBed } from '@angular/core/testing';
import { StatService } from './dashboard-stat.service';

describe('StatService', () => {
    let service: StatService;

    beforeEach(() => {
        TestBed.configureTestingModule({});
        service = TestBed.inject(StatService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('should return mock stats', () => {
        let stats: unknown[] | undefined;
        service.getStats().subscribe((s) => { stats = s; });
        expect(stats?.length).toBeGreaterThan(0);
    });

    it('should return activity feed', () => {
        let activity: unknown[] | undefined;
        service.getActivityFeed().subscribe((a) => { activity = a; });
        expect(activity?.length).toBeGreaterThan(0);
    });

    it('should return workload stats', () => {
        let chart: unknown[] | undefined;
        service.getChartData().subscribe((c) => { chart = c; });
        expect(chart?.length).toBeGreaterThan(0);
    });

    it('should return cached stats', () => {
        let distribution: unknown[] | undefined;
        service.getDistributionData().subscribe((d) => { distribution = d; });
        expect(distribution?.length).toBeGreaterThan(0);
    });
});