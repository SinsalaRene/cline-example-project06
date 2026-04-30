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
}