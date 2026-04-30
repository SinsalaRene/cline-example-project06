# Dashboard Module

## Overview

The Dashboard module provides a comprehensive overview of system metrics, analytics, and quick actions through a responsive and interactive interface. It serves as the central hub for monitoring and managing the application.

## Architecture

### Module Structure

```
dashboard/
├── dashboard.component.ts          # Main dashboard component
├── dashboard.component.html        # Dashboard template
├── dashboard.component.css         # Dashboard styles
├── dashboard.component.spec.ts     # Unit tests
├── dashboard.module.ts             # Module definition
├── services/
│   └── dashboard-stat.service.ts   # Data service
└── components/
    ├── metric-card/                # Metric card display component
    ├── chart-widget/               # Chart visualization component
    ├── quick-action-panel/         # Quick action buttons component
    └── activity-feed/              # Activity feed component
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    DashboardComponent                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    Dashboard Header                   │    │
│  │  • Title & Description                               │    │
│  │  • Refresh Button                                    │    │
│  │  • Quick Action Button                               │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Key Metrics (Metric Cards)              │    │
│  │  • Real-time data visualization                     │    │
│  │  • Trend indicators (up/down/stable)                │    │
│  │  • Percentage-based progress bars                    │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Analytics (Chart Widgets)                │    │
│  │  • Line charts for trends                            │    │
│  │  • Doughnut charts for distribution                  │    │
│  │  • Bar charts for comparison                         │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Quick Actions & Activity Feed                  │    │
│  │  • Actionable buttons with navigation                 │    │
│  │  • Real-time activity log                              │    │
│  │  • Color-coded activity types                         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Components

### DashboardComponent

The main component that orchestrates all dashboard functionality.

**Features:**
- Loads and displays dashboard data
- Manages loading state
- Provides navigation to actions
- Formats timestamps for display
- Maps activity types to icons

**Key Methods:**
- `loadDashboardData()`: Loads all dashboard data from the service
- `navigateToAction(action: QuickAction)`: Navigates to the specified route
- `refreshData()`: Refreshes all dashboard data
- `getTrendIcon(trend: string)`: Returns the appropriate icon for trend direction
- `getTrendColor(trend: string)`: Returns the appropriate color for trend direction
- `getActivityIcon(type: string)`: Returns the appropriate icon for activity type
- `formatTimestamp(date: Date)`: Formats a date for display

### MetricCardComponent

Displays individual metric information with visual indicators.

**Inputs:**
- `stat`: DashboardStat object containing metric data
- `trendIconFn`: Function to get trend icon
- `trendColorFn`: Function to get trend color

**Features:**
- Displays metric value with appropriate formatting
- Shows trend direction with icons
- Visual progress indicator based on percentage
- Color-coded based on metric type

### ChartWidgetComponent

Renders charts for data visualization.

**Inputs:**
- `chartData`: Array of DashboardChartData objects
- `chartTitle`: Title for the chart
- `chartType`: Type of chart (line, bar, doughnut)
- `chartColor`: Primary color for the chart

**Features:**
- Line chart for trend visualization
- Bar chart for comparison data
- Doughnut chart for distribution data
- Responsive sizing

### QuickActionPanelComponent

Displays actionable items for common operations.

**Inputs:**
- `actions`: Array of QuickAction objects
**Outputs:**
- `actionClicked`: Emits when an action is clicked

**Features:**
- Grid layout for action cards
- Icon-based visualization
- Confirmation dialog support
- Route navigation

### ActivityFeedComponent

Displays recent system activities.

**Inputs:**
- `activities`: Array of DashboardActivity objects
- `getActivityIcon`: Function to get activity icon by type
- `formatTimestamp`: Function to format timestamps

**Features:**
- Color-coded activity indicators
- Relative time display
- Empty state handling

## Service Layer

### StatService

Provides all data for the dashboard.

**Methods:**
- `getStats()`: Returns dashboard statistics
- `getChartData()`: Returns chart data
- `getDistributionData()`: Returns distribution data
- `getActivityFeed()`: Returns activity feed
- `getQuickActions()`: Returns quick actions
- `simulateStatsUpdate()`: Simulates real-time updates

## Data Models

### DashboardStat

```typescript
interface DashboardStat {
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
```

### DashboardChartData

```typescript
interface DashboardChartData {
    label: string;
    value: number;
    date: string;
}
```

### DashboardActivity

```typescript
interface DashboardActivity {
    id: string;
    type: 'info' | 'warning' | 'error' | 'success';
    message: string;
    timestamp: Date;
    source: string;
}
```

### QuickAction

```typescript
interface QuickAction {
    id: string;
    label: string;
    description: string;
    icon: string;
    route: string;
    permission?: string;
}
```

## Responsive Design

The dashboard adapts to different screen sizes:

- **Desktop**: Full grid layout with multiple columns
- **Tablet**: Single column for charts and activities
- **Mobile**: Stacked layout with full-width elements

## Testing

Unit tests are provided in `dashboard.component.spec.ts` covering:

- Component creation and initialization
- Data loading from services
- Trend icon and color mapping
- Activity icon mapping
- Timestamp formatting
- Navigation functionality
- Refresh functionality

## Styling

The dashboard uses Material Design principles with:
- Consistent spacing and padding
- Shadow effects for depth
- Hover states for interactivity
- Color-coded status indicators
- Responsive grid layouts

## Accessibility

- Semantic HTML structure
- ARIA labels where appropriate
- Keyboard navigation support
- Color contrast compliance
- Screen reader friendly