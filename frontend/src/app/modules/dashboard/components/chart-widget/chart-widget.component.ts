import { Component, Input, OnInit } from '@angular/core';
import { DashboardChartData } from '../../services/dashboard-stat.service';

@Component({
    selector: 'app-chart-widget',
    templateUrl: './chart-widget.component.html',
    styleUrls: ['./chart-widget.component.css'],
})
export class ChartWidgetComponent implements OnInit {
    @Input() chartData!: DashboardChartData[];
    @Input() chartTitle: string = 'Chart';
    @Input() chartType: string = 'line';
    @Input() chartColor: string = '#2196F3';

    ngOnInit(): void {
        // Chart rendering is handled by child components
    }

    getChartColors(): string[] {
        const baseColor = this.chartColor || '#2196F3';
        const colors = [];
        for (let i = 0; i < (this.chartData?.length || 0); i++) {
            colors.push(baseColor);
        }
        return colors;
    }

    getChartLabels(): string[] {
        return this.chartData?.map((item) => item.label || '') || [];
    }

    getChartValues(): number[] {
        return this.chartData?.map((item) => item.value || 0) || [];
    }

    getBarHeight(value: number, data: DashboardChartData[]): number {
        if (!data || data.length === 0) return 0;
        const max = Math.max(...data.map((d) => d.value || 0));
        if (max === 0) return 0;
        return (value / max) * 100;
    }

    getLinePoints(data: DashboardChartData[]): string {
        if (!data || data.length === 0) return '';
        const width = 500;
        const height = 200;
        const padding = 20;
        const usableWidth = width - padding * 2;
        const usableHeight = height - padding * 2;
        const max = Math.max(...data.map((d) => d.value || 0));

        return data
            .map(
                (item, index) => {
                    const x = padding + (index / Math.max(data.length - 1, 1)) * usableWidth;
                    const y = height - padding - ((item.value || 0) / Math.max(max, 1)) * usableHeight;
                    return `${x},${y}`;
                }
            )
            .join(' ');
    }

    getLineFillPoints(data: DashboardChartData[]): string {
        if (!data || data.length === 0) return '';
        const linePoints = this.getLinePoints(data);
        const width = 500;
        const padding = 20;
        const lastPoint = linePoints.split(' ').pop() || `${width - padding},200`;
        return `${padding},200 ${linePoints} ${lastPoint.split(',')[0]},200`;
    }

    getPointX(index: number, total: number): number {
        const width = 500;
        const padding = 20;
        const usableWidth = width - padding * 2;
        return padding + (index / Math.max(total - 1, 1)) * usableWidth;
    }

    getPointY(value: number, data: DashboardChartData[]): number {
        const height = 200;
        const padding = 20;
        const usableHeight = height - padding * 2;
        const max = Math.max(...data.map((d) => d.value || 0));
        return height - padding - (value / Math.max(max, 1)) * usableHeight;
    }

    getDoughnutColor(index: number, total: number): string {
        const colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0'];
        return colors[index % colors.length];
    }

    getTotalValue(data: DashboardChartData[]): number {
        if (!data) return 0;
        return data.reduce((sum, item) => sum + (item.value || 0), 0);
    }

    getDoughnutDash(value: number, data: DashboardChartData[]): string {
        if (!data || data.length === 0) return '0';
        const total = this.getTotalValue(data);
        if (total === 0) return '0';
        const percentage = (value / total) * 2 * Math.PI * 80;
        return `${percentage} 999`;
    }

    getDoughnutOffset(index: number, data: DashboardChartData[]): number {
        if (!data || data.length === 0) return 0;
        const total = this.getTotalValue(data);
        if (total === 0) return 0;
        let offset = 0;
        for (let i = 0; i < index; i++) {
            const item = data[i];
            const percentage = ((item?.value || 0) / total) * 2 * Math.PI * 80;
            offset += percentage;
        }
        return -offset;
    }
}
