# PROMPT 7: External Devices + Impact Analysis

## Context

You are working on an Azure Firewall Management application built with Angular (frontend) and FastAPI/Python (backend). NSG inline editing is complete (Prompt 6). Now implement external network device management and impact visualization.

**Relevant frontend files:**
- `frontend/src/app/modules/network/services/network.service.ts`
- `frontend/src/app/modules/network/models/network.model.ts`
- `frontend/src/app/modules/network/components/`

**Known state:**
- Backend has endpoints for external devices and impact analysis

## Task

### 1. External Devices Module (`network/components/external-devices/`)
- `external-devices-list.component.ts`: MatTable with columns: Name, IP Address, Device Type, Vendor, Model, Contact Email. Actions: Edit, Delete, View Connections. Add button opens dialog.
- `external-device-form.component.ts`: Dialog with reactive form — name (required), ipAddress (required, pattern: IP), deviceType (dropdown: router/switch/firewall/other), vendor (text), model (text), contactName (text), contactEmail (email pattern), notes (textarea), tags (comma-separated).
- `external-device-detail.component.ts`: Card showing all properties, list of connections to/from this device. "Edit" and "Delete" buttons.

### 2. Impact Analysis Service (`network/services/impact-analyzer.service.ts`)
- `analyzeNsgImpact(nsgId, ruleChanges): Observable<ImpactResult>`
- `compareRules(oldRules: NSGRule[], newRules: NSGRule[]): RuleComparison`
- `getAffectedSubnets(nsgId, ruleChanges)`: returns subnets affected by rule changes
- `getReachableDevices(nsgId, ruleChanges)`: returns external devices reachable after changes

### 3. Impact Analysis Component (`network/components/impact-analysis/`)
- `impact-analysis-dialog.component.ts`: Material dialog
  - Takes NSG ID and new rules as input
  - Shows side-by-side comparison: "Before" vs "After" rules tables
  - Below: "Affected Subnets" section — list with subnet names, addresses, which rules affect them
  - Below: "Newly Reachable External Devices" section — list with device details
  - Below: "Blocked Access" section — devices that lost access (rules removed)
  - Color coding: green (no change), yellow (added), red (removed)
  - "Confirm" and "Cancel" buttons
  - Warning banner if changes remove existing access

### 4. Integration
- In NsgRuleEditor, when "Add Rule" or "Update Rule" is submitted, open ImpactAnalysisDialog before saving
- Show impact analysis summary inline below the table (collapsible)
- "Review Impact" button next to unsaved changes indicator

### 5. NetworkConnections Management
- `network/components/connection-manager.component.ts`: Table of connections with CRUD operations
- Wire into topology container as a section/tab

### 6. Update NetworkService
- Add: `analyzeImpact(nsgId, rules)`, `getImpactSummary(nsgId)`

## Quality Checks

1. [ ] External devices list with CRUD works
2. [ ] External device form validates IP address pattern
3. [ ] Impact analysis dialog shows before/after comparison
3. [ ] Affected subnets correctly identified
4. [ ] Reachable external devices correctly identified
5. [ ] Color coding matches spec (green/yellow/red)
6. [ ] Integration with NSG rule editor opens impact dialog on submit
7. [ ] Connection manager component works
8. [ ] No TypeScript compilation errors

## Skills

Before starting, load and activate these skills:

```
use_skill(skill_name="tdd")
```

Follow the TDD skill's red-green-refactor loop. Write tests for: impact analysis algorithm (before/after rule comparison, affected subnet identification, reachable device calculation), external device CRUD service methods, and form validation before implementing components.

## Documentation Requirements

- Add JSDoc to impact analyzer service
- Document impact analysis algorithm in component
- Create `frontend/src/app/modules/network/components/impact-analysis/README.md`
