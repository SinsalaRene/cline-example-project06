import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { SharedModule } from '../../shared/shared.module';
import { DashboardComponent } from './dashboard.component';
import { MetricCardComponent } from './components/metric-card/metric-card.component';
import { ChartWidgetComponent } from './components/chart-widget/chart-widget.component';
import { QuickActionPanelComponent } from './components/quick-action-panel/quick-action-panel.component';
import { ActivityFeedComponent } from './components/activity-feed/activity-feed.component';
import { StatService } from './services/dashboard-stat.service';

@NgModule({
    declarations: [
        DashboardComponent,
        MetricCardComponent,
        ChartWidgetComponent,
        QuickActionPanelComponent,
        ActivityFeedComponent,
    ],
    imports: [
        CommonModule,
        SharedModule,
        ReactiveFormsModule,
    ],
    providers: [
        StatService,
    ],
    exports: [
        DashboardComponent,
        MetricCardComponent,
        ChartWidgetComponent,
        QuickActionPanelComponent,
        ActivityFeedComponent,
    ]
})
export class DashboardModule { }