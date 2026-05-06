# PROMPT 6: NSG Management (Inline Rule Editing)

## Context

You are working on an Azure Firewall Management application built with Angular (frontend) and FastAPI/Python (backend). Network topology views are complete (Prompt 5). Now implement NSG management with inline rule editing.

**Relevant frontend files:**
- `frontend/src/app/modules/network/components/network-graph.component.ts`
- `frontend/src/app/modules/network/components/topology-container.component.ts`
- `frontend/src/app/modules/network/services/network.service.ts`
- `frontend/src/app/modules/network/models/network.model.ts`

## Task

Implement NSG inline rule editing:

### 1. NSG Rule Editor Component (`network/components/nsg-rule-editor.component.ts`)
A table-based inline editor for NSG rules within the NSG detail view:
- MatTable displaying all rules for an NSG with columns: Name, Priority, Direction, Protocol, Source IP, Dest IP, Source Port, Dest Port, Access, Enabled (checkbox)
- Each row has Edit, Delete buttons
- "Add Rule" button at top opens an inline form row or a dialog
- Add Rule dialog has form with: name (required), priority (100-4096, unique), direction (inbound/outbound dropdown), protocol (TCP/UDP/ICMP/* dropdown), source IP (required), dest IP (required), source port (required), dest port (required), access (allow/deny dropdown), enabled (checkbox, default true)
- Edit button opens the same dialog pre-filled with rule data
- Delete button opens ConfirmationDialogComponent (reuse from workloads)
- Priority field validates uniqueness across rules (async validation)
- On add/update, calls NetworkService methods and refreshes the table
- On delete, removes from table then calls service

### 2. NSG Rule Editor Drag Order
- Rules table uses MatSort + CdkDragDrop for manual priority reordering
- When rules are reordered, calls `reorderNsgRules(nsgId, ruleOrder)` to persist new order
- Shows visual drag handles (grip icon)

### 3. NSG Detail Panel (`network/components/nsg-detail-panel.component.ts`)
- Shows NSG properties in a card: name, location, resource group, tags, sync status
- Sync status badge: green (synced), yellow (pending), red (failed), gray (never synced)
- "Sync to Azure" button → calls `syncNsgToAzure(id)`, shows spinner, updates status badge
- Shows total rule count
- Embedded NsgRuleEditor component below properties
- "View NSG Audit" button → navigates to `/audit/resource/nsg/{nsgId}`
- "Back to Topology" button

### 4. Graph Integration
- When clicking an NSG node in NetworkGraphComponent, opens the NSG detail panel (can be a side drawer or modal)
- The panel should be embedded into the topology view

### 5. Update NetworkService
- Add methods: `syncNsgToAzure(nsgId)`, `reorderNsgRules(nsgId, ruleIds)`

## Quality Checks

1. [ ] NSG rule editor shows all rules with correct columns
2. [ ] Add rule dialog validates priority uniqueness and required fields
3. [ ] Edit rule dialog pre-fills existing values
4. [ ] Delete uses confirmation dialog
5. [ ] Drag reordering calls reorder service method
6. [ ] NSG detail panel shows sync status badge
7. [ ] Sync to Azure button shows spinner and updates status
8. [ ] Clicking NSG graph node opens detail panel
9. [ ] No TypeScript compilation errors

## Skills

Before starting, load and activate these skills:

```
use_skill(skill_name="tdd")
```

Follow the TDD skill's red-green-refactor loop. Write tests for: NSG rule form validation (priority uniqueness, required fields), drag-and-drop reorder logic, and NSG sync status badge updates before implementing components.

## Documentation Requirements

- Add JSDoc to each new component
- Comment the priority validation logic
