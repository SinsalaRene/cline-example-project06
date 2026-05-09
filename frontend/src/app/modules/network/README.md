# Network Module

## Architecture Overview

The Network module provides network topology visualization capabilities for the Firewall Manager application. It enables users to visualize, explore, and manage Azure network resources through two complementary views: a hierarchical tree view and an interactive SVG graph view.

## Module Structure

```
network/
├── network.module.ts              ← Angular module declaration
├── network.routing.ts             ← Route configuration
├── README.md                      ← This file
├── models/
│   └── network.model.ts           ← TypeScript interfaces, enums, constants
├── services/
│   └── network.service.ts         ← API communication layer
└── components/
    ├── topology-container/         ← Parent component with view toggle
    ├── network-tree/               ← MatTree hierarchy view
    ├── network-graph/              ← SVG interactive graph view
    └── vnet-detail/                ← VNet detail view with CRUD
```

## Components

### TopologyContainerComponent

The root component for the network module. It provides:

- **View Toggle**: Switch between Tree View and Graph View
- **Search/Filter Bar**: Filter nodes by name, type, or location
- **Loading State**: Shows a spinner during initial topology fetch
- **Error Handling**: Displays an error bar with retry button on failure

### NetworkTreeComponent

A hierarchical MatTree view that displays the network topology in a tree structure:

```
VNet (parent)
├── Subnet (child)
│   └── NSG (child)
│       └── NSG Rule (leaf)
├── Subnet (child)
└── NSG (child of VNet)
```

Key features:

- Expand/collapse all buttons
- Node count per parent
- Clickable leaf nodes for editing
- Context menu for common actions

### NetworkGraphComponent

An SVG-based interactive graph renderer that visualizes network entities as styled shapes connected by edges:

#### Rendering Algorithm

1. **Node Layout**: Nodes are positioned using a force-directed layout algorithm
2. **Shape Mapping**: Each entity type maps to a specific SVG shape:
   - Virtual Network → Large blue rectangle
   - Subnet → Medium green rectangle
   - NSG → Orange diamond
   - NSG Rule → Small yellow square
   - External Device → Red hexagon
3. **Edge Drawing**: Lines connect parent-child nodes with arrow markers
4. **Interaction**: Users can drag nodes, zoom in/out, and click nodes to see details

#### Graph Transform Math

- **Zoom**: Uses SVG `transform="scale(s)"` where `s` is the zoom factor (0.5x to 3x)
- **Pan**: Uses SVG `transform="translate(dx, dy)"` for panning
- **Drag Delta**: `dx = newX - oldX`, `dy = newY - oldY` applied to node position

### VNet Detail Component

Displays detailed information about a specific Virtual Network:

- VNet properties in a MatCard
- Subnet listing in a MatTable
- Attached NSGs listing
- Create Subnet and Create NSG action buttons
- Back navigation to the topology view

## Data Flow

```
API Backend (FastAPI)
    ↓
NetworkService (Observable-based)
    ↓
Component (subscribe to Observable)
    ↓
Template (Angular data binding)
```

## Models

### Core Interfaces

| Interface | Description |
|-----------|-------------|
| `VirtualNetwork` | Azure Virtual Network with address space, subnets, and NSGs |
| `Subnet` | Subnet within a VNet with address prefix and NSG association |
| `NetworkSecurityGroup` | NSG with rules, subnets, and connections |
| `NSGRule` | Individual firewall rule with priority, direction, protocol |
| `ExternalNetworkDevice` | Physical/virtual network device (router, firewall, switch) |
| `NetworkConnection` | Link between two network entities |
| `TopologyNode` | Graph node for rendering |
| `TopologyEdge` | Graph edge connecting two nodes |

### Enums

| Enum | Values |
|------|--------|
| `Direction` | `inbound`, `outbound` |
| `Protocol` | `TCP`, `UDP`, `ICMP`, `AH`, `*` |
| `Access` | `allow`, `deny` |
| `DeviceType` | `router`, `switch`, `firewall`, `other` |
| `ConnectionType` | `direct`, `vpn`, `express_router`, `peering`, `vpn_gateway`, `custom` |
| `SyncStatus` | `pending`, `applied`, `failed` |
| `NodeType` | `virtual_network`, `subnet`, `nsg`, `nsg_rule`, `external_device`, `connection` |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/network/topology` | Full topology graph |
| GET | `/api/v1/network/virtual-networks` | List all VNets |
| GET | `/api/v1/network/virtual-networks/:id` | Get single VNet |
| POST | `/api/v1/network/virtual-networks` | Create VNet |
| PUT | `/api/v1/network/virtual-networks/:id` | Update VNet |
| DELETE | `/api/v1/network/virtual-networks/:id` | Delete VNet |
| GET | `/api/v1/network/subnets?vnetId=:id` | List subnets |
| POST | `/api/v1/network/subnets` | Create subnet |
| DELETE | `/api/v1/network/subnets/:id` | Delete subnet |
| GET | `/api/v1/network/nsgs` | List all NSGs |
| POST | `/api/v1/network/nsgs` | Create NSG |
| DELETE | `/api/v1/network/nsgs/:id` | Delete NSG |
| GET | `/api/v1/network/nsgs/:id/rules` | List NSG rules |
| POST | `/api/v1/network/nsgs/:id/rules` | Create NSG rule |
| PUT | `/api/v1/network/nsgs/:id/rules/reorder` | Reorder NSG rules |
| GET | `/api/v1/network/external-devices` | List external devices |
| POST | `/api/v1/network/external-devices` | Create external device |
| GET | `/api/v1/network/connections` | List connections |
| POST | `/api/v1/network/connections` | Create connection |
| DELETE | `/api/v1/network/connections/:id` | Delete connection |

## Routing

```typescript
{
    path: 'network',
    canActivate: [AuthGuard],
    loadChildren: () => import('./network.module').then(m => m.NetworkModule)
}
```

The network module is lazy-loaded for performance optimization. It is accessed via the sidebar navigation under the "Resources" section.

## Dependencies

The module depends on the following Angular Material modules:

- `MatTreeModule` — Tree hierarchy view
- `MatTableModule` — Data tables for subnet/NSG listings
- `MatCardModule` — Card containers
- `MatButtonModule` — Action buttons
- `MatIconModule` — Icons in tree and UI
- `MatDividerModule` — Visual separators
- `MatChipsModule` — Status indicators
- `MatProgressSpinnerModule` — Loading indicators
- `MatDialogModule` — Dialogs for create/edit forms
- `MatFormFieldModule` — Form field containers
- `MatInputModule` — Input fields
- `ReactiveFormsModule` — Form handling

## Testing

Unit tests are located in `services/network.service.spec.ts` and cover all service methods including CRUD operations, topology fetching, and API error handling.