import { Component, Input } from '@angular/core';
import { DashboardActivity } from '../../services/dashboard-stat.service';

@Component({
    selector: 'app-activity-feed',
    templateUrl: './activity-feed.component.html',
    styleUrls: ['./activity-feed.component.css'],
})
export class ActivityFeedComponent {
    @Input() activities: DashboardActivity[] = [];
    @Input() getActivityIcon: ((type: string) => string) | null = null;
    @Input() formatTimestamp: ((date: Date) => string) | null = null;

    getActivityTypeColor(type: string): string {
        switch (type) {
            case 'success':
                return '#4CAF50';
            case 'warning':
                return '#FF9800';
            case 'error':
                return '#F44336';
            case 'info':
                return '#2196F3';
            default:
                return '#757575';
        }
    }

    getRelativeTime(timestamp: Date): string {
        const now = new Date();
        const diff = now.getTime() - new Date(timestamp).getTime();
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);

        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        return new Date(timestamp).toLocaleDateString();
    }
}