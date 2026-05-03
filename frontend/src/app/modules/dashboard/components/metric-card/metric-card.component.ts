import { Component, Input } from '@angular/core';
import { DashboardStat } from '../../services/dashboard-stat.service';

@Component({
    selector: 'app-metric-card',
    templateUrl: './metric-card.component.html',
    styleUrls: ['./metric-card.component.css'],
})
export class MetricCardComponent {
    @Input() stat!: DashboardStat;
    @Input() trendIcon: string = '';
    @Input() trendColor: string = '';
    @Input() trendIconFn: ((trend: string) => string) | null = null;
    @Input() trendColorFn: ((trend: string) => string) | null = null;

    getTrendIcon(): string {
        if (this.trendIconFn && this.stat?.trend) {
            return this.trendIconFn(this.stat.trend);
        }
        return this.trendIcon || 'trending_up';
    }

    getTrendColor(): string {
        if (this.trendColorFn && this.stat?.trend) {
            return this.trendColorFn(this.stat.trend);
        }
        return this.trendColor || '#2196F3';
    }
}
