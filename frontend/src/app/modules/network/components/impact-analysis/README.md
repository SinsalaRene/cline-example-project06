# Impact Analysis Module

## Overview

The Impact Analysis module provides comprehensive visualization of the effects of NSG (Network Security Group) rule changes before they are applied. It enables network administrators to understand the security impact of proposed changes through detailed before/after comparisons.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Impact Analysis Flow                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. User modifies NSG rules in rule editor                  │
│  2. User clicks "Review Impact" or "Submit"                 │
│  3. ImpactAnalysisDialog opens with current + proposed rules│
│  4. ImpactAnalyzerService computes:                         │
│     - Rule comparisons (added, modified, removed)           │
│     - Affected subnets (which subnets are impacted)         │
│     - Reachable devices (which external devices gain/lose  │
│       access)                                               │
│  5. Dialog displays results with color coding             │
│  6. User confirms or cancels changes                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components

### ImpactAnalysisDialogComponent

A standalone Material dialog that displays comprehensive impact analysis results.

**Features:**
- Loading spinner during analysis
- Warning banner if changes remove existing access
- Summary statistics (new, modified, removed counts)
- Side-by-side rule comparison tables (Before vs After)
- Affected subnets list with rule references
- Devices gaining access list with enabling rules
- Devices losing access list with removed rules
- Color-coded status indicators (green/yellow/red)

**Usage:**
```typescript
const dialogRef = this.dialog.open(ImpactAnalysisDialogComponent, {
  width: '1200px',
  data: {
    nsgId: 'nsg-123',
    newRules: proposedRules,
    title: 'NSG Rule Changes'
  }
});

dialogRef.afterClosed().subscribe(result => {
  if (result.confirmed) {
    // Apply the changes
    this.applyRuleChanges(result.impact);
  }
});
```

## Impact Analysis Algorithm

### Rule Comparison

The algorithm compares old and new rule sets using name-based matching:

1. Build a map of rules by name from both sets
2. Iterate through all unique rule names
3. For each name:
   - If in new but not old: **ADDED**
   - If in old but not new: **REMOVED**
   - If in both: compare all fields
     - If any field differs: **MODIFIED** (with list of changed fields)
     - If all fields match: **UNCHANGED**

### Affected Subnet Identification

For each subnet associated with the NSG:

1. Get all rules currently active on the subnet's NSG
2. Compare rules before vs after changes
3. A subnet is affected if:
   - Any rule in the NSG is ADDED, MODIFIED, or REMOVED
   - The rule change affects traffic flows through the subnet
4. Identify which specific rules cause the change for each subnet

### Reachable Device Calculation

For each external device connected to subnets in the NSG:

1. Get all connections linking the device to subnets
2. For each connection, get the rules affecting that subnet
3. Analyze traffic flows:
   - **Gains access**: If a new ALLOW rule matches the device's IP and port
   - **Loses access**: If a REMOVE/MODIFY removes an existing ALLOW rule
   - **Unchanged**: If existing rules still permit/deny the same traffic

### Color Coding

| Color | Meaning | Context |
|-------|---------|---------|
| 🟢 Green | No change | Rule remains the same |
| 🟡 Yellow | Added/Modified | New or changed rules |
| 🔴 Red | Removed | Rules being deleted |

## ImpactAnalyzerService

The service layer that performs all impact analysis computations.

**Key Methods:**

```typescript
// Main entry point
analyzeNsgImpact(
  nsgId: string,
  currentRules: NSGRule[],
  proposedRules: NSGRule[],
  subnets?: Subnet[],
  externalDevices?: ExternalNetworkDevice[],
  connections?: NetworkConnection[],
  nsgMap?: Map<string, NetworkSecurityGroup>
): ImpactResult

// Rule comparison
compareRules(oldRules: NSGRule[], newRules: NSGRule[]): RuleComparison[]

// Subnet analysis
getAffectedSubnets(
  subnets: Subnet[],
  nsgMap: Map<string, NetworkSecurityGroup>,
  comparisons: RuleComparison[]
): AffectedSubnetInfo[]

// Device reachability
getReachableDevices(
  devices: ExternalNetworkDevice[],
  connections: NetworkConnection[],
  subnets: Subnet[],
  comparisons: RuleComparison[]
): DeviceImpact[]
```

## Data Models

### ImpactResult

```typescript
interface ImpactResult {
  nsgId: string;
  ruleComparisons: RuleComparison[];
  affectedSubnets: AffectedSubnetInfo[];
  reachableDevices: DeviceImpact[];
  hasRemovedAccess: boolean;
  addedCount: number;
  removedCount: number;
  modifiedCount: number;
  unchangedCount: number;
}
```

### RuleComparison

```typescript
interface RuleComparison {
  oldRule?: NSGRule;
  newRule?: NSGRule;
  changeType: 'ADDED' | 'REMOVED' | 'MODIFIED' | 'UNCHANGED';
  changedFields?: string[];
}
```

### DeviceImpact

```typescript
interface DeviceImpact {
  device: ExternalNetworkDevice;
  gainsAccess: boolean;
  responsibleRules: RuleComparison[];
  subnet: Subnet;
  connection: NetworkConnection;
}
```

## Integration Example

### With NSG Rule Editor

```typescript
// In NsgRuleEditorComponent

onSubmitRuleChanges(newRules: NSGRule[]): void {
  // Open impact analysis dialog
  const dialogRef = this.dialog.open(ImpactAnalysisDialogComponent, {
    width: '1200px',
    data: {
      nsgId: this.nsgId,
      newRules: newRules,
      title: `Review Impact: ${newRules.length} Rules`
    }
  });

  dialogRef.afterClosed().subscribe(result => {
    if (result?.confirmed) {
      // Apply the changes only if confirmed
      this.applyChanges(result.impact);
    }
  });
}
```

### Inline Impact Summary

```typescript
// In NsgRuleEditorComponent template
<mat-expansion-panel *ngIf="hasUnsavedChanges">
  <mat-expansion-panel-header>
    <mat-panel-title>Review Impact</mat-panel-title>
    <mat-panel-description>
      {{ impactSummary?.addedCount }} new,
      {{ impactSummary?.removedCount }} removed
    </mat-panel-description>
  </mat-expansion-panel-header>

  <div class="impact-summary">
    <div class="stat" *ngIf="impactSummary?.addedCount">
      <mat-icon color="accent">add_circle</mat-icon>
      {{ impactSummary.addedCount }} new rules
    </div>
    <div class="stat" *ngIf="impactSummary?.removedCount">
      <mat-icon color="warn">remove_circle</mat-icon>
      {{ impactSummary.removedCount }} removed rules
    </div>
    <div class="stat" *ngIf="impactSummary?.hasRemovedAccess">
      <mat-icon color="warn">warning</mat-icon>
      Warning: Access removal detected
    </div>
  </div>
</mat-expansion-panel>
```

## File Structure

```
network/components/impact-analysis/
├── impact-analysis-dialog.component.ts   # Main dialog component
├── impact-analysis.module.ts             # Module definition
└── README.md                             # This file
```

## Testing

```typescript
// Unit test example
describe('ImpactAnalyzerService', () => {
  let service: ImpactAnalyzerService;

  beforeEach(() => {
    service = new ImpactAnalyzerService();
  });

  it('should detect added rules', () => {
    const oldRules: NSGRule[] = [];
    const newRules: NSGRule[] = [{
      id: 'rule-1',
      name: 'AllowHTTP',
      priority: 100,
      direction: Direction.INBOUND,
      sourceAddressPrefix: '*',
      destinationAddressPrefix: '10.0.0.0/24',
      protocol: Protocol.TCP,
      port: 80,
      access: Access.ALLOW
    }];

    const result = service.compareRules(oldRules, newRules);
    expect(result[0].changeType).toBe(RuleChangeType.ADDED);
  });
});
```

## Security Considerations

1. **Change Confirmation**: Always require explicit confirmation before applying rule changes
2. **Warning Display**: Show prominent warnings when access is being removed or restricted
3. **Audit Trail**: Log all impact analysis sessions for compliance
4. **Review Period**: Consider implementing a mandatory review period for production changes
5. **Role-Based Access**: Restrict impact analysis viewing to authorized roles

## Future Enhancements

- [ ] Export impact analysis report as PDF
- [ ] Schedule recurring impact analysis
- [ ] Compare multiple rule sets simultaneously
- [ ] Simulate traffic flows based on rules
- [ ] Integration with Azure Monitor for real-time impact data
- [ ] Impact history tracking and trending
- [ ] Automated rollback suggestions for high-risk changes