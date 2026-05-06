# PROMPT 5: Network Topology Views

## Context

You are working on an Azure Firewall Management application built with Angular (frontend) and FastAPI/Python (backend). Backend network services are complete (Prompt 4). Now implement the frontend network topology visualization module.

**Relevant frontend files:**
- `frontend/src/app/modules/workloads/` — existing workloads module (may reference network concepts)
- `frontend/src/app/shared/shared.module.ts` — shared components
- `frontend/angular.json` — for dependency management

**Known state:**
- Backend has new network API endpoints: /network/topology, /network/virtual-networks, /network/nsgs, /network/subnets, /network/connections, /network/external-devices
- Frontend has MatTreeModule, MatTableModule available from existing modules
- Need to create a new Network module for topology visualization

## Task

Create the network topology frontend module with tree view and graph view:

### 1. Network Module & Routing (`frontend/src/app/modules/network/`)
Create new module:
- `network.module.ts` — declares components, provides NetworkService
- `network.routing.ts` — routes: `network` → TopologyContainerComponent, `network/vnets/:id` → VnetDetailComponent
- `network/services/network.service.ts` — API service layer
- `network/models/network.model.ts` — TypeScript interfaces
- `network/components/topology-container.component.ts` — parent component with view toggle
- `network/components/network-tree.component.ts` — tree hierarchy view
- `network/components/network-graph.component.ts` — SVG-based graph view
- `network/components/vnet-detail.component.ts` — detail view for a VNet

### 2. Network Models (`models/network.model.ts`)
Define TypeScript interfaces:
- `VirtualNetwork`: id, name, addressSpace, location, resourceGroup, tags, subnets[], nsgs[]
- `Subnet`: id, name, addressPrefix, vnets, nsgs[]
- `NSG`: id, name, location, rules[], subnets[], connections[]
- `NSGRule`: id, name, priority, direction, protocol, sourceIp, destIp, sourcePort, destPort, access, enabled
- `ExternalDevice`: id, name, ipAddress, deviceType, vendor, model, contactEmail
- `NetworkConnection`: id, sourceId, sourceType, destId, destType, connectionType, description
- `TopologyNode`: id, type, data, connections[] — for graph rendering

### 3. NetworkService (`services/network.service.ts`)
Methods:
- `getTopology()` → Observable<TopologyGraph>
- `getVnets()`, `getVnet(id)`, `createVnet(data)`, `updateVnet(id, data)`, `deleteVnet(id)`
- `getSubnets(vnetId?)`, `getSubnet(id)`, `createSubnet(data)`, `deleteSubnet(id)`
- `getNsgs()`, `getNsg(id)`, `createNsg(data)`, `updateNsg(id, data)`, `deleteNsg(id)`
- `getNsgRules(nsgId)`, `createNsgRule(nsgId, data)`, `updateNsgRule(ruleId, data)`, `deleteNsgRule(ruleId)`
- `reorderNsgRules(nsgId, ruleOrder)`
- `getExternalDevices()`, `createExternalDevice(data)`, `updateExternalDevice(id, data)`, `deleteExternalDevice(id)`
- `getConnections(filters?)`, `createConnection(data)`, `deleteConnection(id)`

### 4. TopologyContainerComponent
- MatCard with header: "Network Topology"
- Toggle buttons: [Tree View] [Graph View]
- Search/filter bar at top (filter by name, type, location)
- Lazy-loads the selected view component
- Shows loading spinner during initial fetch
- Shows error bar with retry button on failure

### 5. NetworkTreeComponent (MatTree)
- Hierarchical tree: VNet → Subnets (children) → NSGs (children of subnets) → Rules (children of NSGs)
- Each leaf node is clickable to edit
- Expand/collapse all buttons
- Search highlights matching nodes
- Shows node count per parent
- Context menu (right-click) for common actions

### 6. NetworkGraphComponent (SVG)
- Custom SVG-based network graph (no external libraries — use Angular component with native SVG)
- Nodes rendered as styled rectangles/circles based on type:
  - VNet: large blue rectangle
  - Subnet: medium green rectangle
  - NSG: orange diamond
  - Rule: small yellow square
  - External Device: red hexagon
- Edges drawn as SVG lines with arrow markers
- Drag-and-drop for nodes (mouse events)
- Click node to select → shows detail panel on right side
- Zoom in/out buttons (scale transform)
- Legend at bottom
- Responsive: resizes on window resize

### 7. VNet Detail Component
- Shows VNet properties in MatCard
- Lists subnets in a table
- Lists NSGs attached to the VNet
- "Create Subnet" and "Create NSG" buttons
- Navigation back to topology

### 8. Network Module Registration
- Register the network module in `app-routing.module.ts` as lazy-loaded route: `network`
- Update `layout.component.ts` sidebar/navigation to include "Network" link

## Quality Checks

1. [ ] Network module loads as lazy-loaded route
2. [ ] NetworkService calls all backend endpoints correctly
3. [ ] Tree view shows VNet → Subnet → NSG → Rule hierarchy
4. [ ] Graph view renders nodes and edges with correct styling
5. [ ] Graph nodes are draggable
6. [ ] Graph supports zoom in/out
7. [ ] Clicking a graph node shows detail panel
8. [ ] Search/filter works on both views
9. [ ] VNet detail shows subnets and NSGs
10. [ ] Navigation integrated into sidebar
11. [ ] No TypeScript compilation errors
12. [ ] All new components documented with JSDoc

## Skills

Before starting, load and activate these skills in order:

```
use_skill(skill_name="improve-codebase-architecture")
```

Use this skill to validate the new network module architecture against existing Angular patterns. Ensure component hierarchy, service layer design, and routing follow conventions from existing modules (rules, approvals, audit).

```
use_skill(skill_name="tdd")
```

After the architecture skill, activate TDD. Write unit tests for NetworkService methods, tree view rendering logic, and SVG graph coordinate calculations before implementing components. Test graph drag-and-drop math and zoom transform math.

## Documentation Requirements

- Add module-level JSDoc to network.module.ts
- Add inline comments explaining graph rendering algorithm in network-graph.component.ts
- Create `frontend/src/app/modules/network/README.md` with architecture overview
