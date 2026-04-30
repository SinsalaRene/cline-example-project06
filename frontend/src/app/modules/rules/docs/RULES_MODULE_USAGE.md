# Rules Module Usage Guide

## Overview

The Rules Module provides a comprehensive interface for managing firewall rules in the Azure Firewall Manager. This guide covers all features including listing, searching, filtering, bulk operations, import/export, and detail views.

## Module Structure

```
frontend/src/app/modules/rules/
├── components/
│   ├── rules-list.component.ts      # Main list view with search/filter
│   ├── rule-form-dialog.component.ts # Create/Edit rule form
│   ├── rule-detail.component.ts      # Rule detail view (dialog)
│   └── confirmation-dialog.component.ts # Confirmation dialog
├── services/
│   └── rules.service.ts              # All API calls and utilities
├── rules.module.ts                   # Module definition
└── docs/
    └── RULES_MODULE_USAGE.md         # This documentation
```

## Features

### 1. Rules List View

The main list component displays firewall rules in a table with:

- **Search**: Filter rules by name, description, or ID
- **Status Filter**: Filter by rule status (active, pending, deleted)
- **Priority Filter**: Sort by priority
- **Bulk Selection**: Select multiple rules for bulk operations

#### Usage

```typescript
// The component is used within the rules module
// No direct instantiation needed when module is imported

// Example in parent component:
import { RulesModule } from './modules/rules/rules.module';

@NgModule({
  imports: [RulesModule]
})
export class AppModule { }
```

### 2. Search and Filter

The search/filter functionality includes:

- **Search Field**: Real-time search across rule name, description, and ID
- **Status Filter**: Dropdown to filter by status (active, pending, deleted)
- **Priority Sort**: Click column header to sort by priority

#### Implementation

```typescript
// Search filter
this.searchFilter = 'example.com';

// Status filter
this.statusFilter = 'active';

// Apply filters
this.applyFilters();
```

### 3. Bulk Operations

Select multiple rules and perform bulk operations:

- **Bulk Delete**: Remove multiple rules at once
- **Bulk Enable**: Activate multiple rules
- **Bulk Disable**: Deactivate multiple rules

#### Usage

```typescript
// Select rules (via UI checkboxes)
component.selectedRules = [rule1, rule2, rule3];

// Bulk delete
component.bulkDeleteSelected();

// Bulk enable
component.bulkEnableSelected();

// Bulk disable
component.bulkDisableSelected();
```

### 4. Rule Detail View

Click any rule row to see detailed information:

- **Overview Tab**: Basic rule information
- **Configuration Tab**: Address configuration details
- **Audit History Tab**: Creation and update timestamps
- **JSON Tab**: Raw JSON representation

#### Usage

```typescript
// Opens when clicking a rule row
component.onRuleClick(rule: FirewallRule);
```

### 5. Create/Edit Rule Form

The form dialog supports:

- **Create New Rules**: Fill out form and submit
- **Edit Existing Rules**: Pre-populated form with current values
- **Validation**: Required field validation
- **Duplicate Detection**: Warning for duplicate rule names

#### Usage

```typescript
// Open create dialog
this.dialog.open(RuleFormDialogComponent, {
  data: { rule: null, isEdit: false }
});

// Open edit dialog
this.dialog.open(RuleFormDialogComponent, {
  data: { rule: existingRule, isEdit: true }
});
```

### 6. Import/Export

The service provides methods for importing and exporting rules:

#### Export

```typescript
// Export to JSON
const blob = this.rulesService.exportRules(rules, 'json');
downloadBlob(blob, 'rules.json');

// Export to CSV
const blob = this.rulesService.exportRules(rules, 'csv');
downloadBlob(blob, 'rules.csv');
```

#### Import

```typescript
// Import from JSON
const jsonContent = await readFile('rules.json');
const rules: Partial<FirewallRule>[] = JSON.parse(jsonContent);
const result: ImportResult = await this.rulesService.importRules(rules);
console.log(`Imported: ${result.imported}, Skipped: ${result.skipped}`);

// Import from CSV
const csvContent = await readFile('rules.csv');
const rules: Partial<FirewallRule>[] = this.rulesService.parseCSV(csvContent);
const result: ImportResult = await this.rulesService.importRules(rules);
```

### 7. Service Methods

The `RulesService` provides the following methods:

#### CRUD Operations

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `getRules()` | Get paginated rules | `page`, `pageSize`, `status`, `workloadId` | `Observable<PaginatedResponse<FirewallRule>>` |
| `getRule()` | Get single rule | `id: string` | `Observable<FirewallRule>` |
| `createRule()` | Create new rule | `rule: Partial<FirewallRule>` | `Observable<FirewallRule>` |
| `updateRule()` | Update existing rule | `id: string`, `rule: Partial<FirewallRule>` | `Observable<FirewallRule>` |
| `deleteRule()` | Delete a rule | `id: string` | `Observable<void>` |

#### Bulk Operations

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `bulkDelete()` | Delete multiple rules | `ids: string[]` | `Observable<BulkOperationResult>` |
| `bulkEnable()` | Enable multiple rules | `ids: string[]` | `Observable<BulkOperationResult>` |
| `bulkDisable()` | Disable multiple rules | `ids: string[]` | `Observable<BulkOperationResult>` |
| `duplicateRule()` | Duplicate a rule | `id: string`, `newName?: string` | `Observable<FirewallRule>` |

#### Import/Export Operations

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `importRules()` | Import rules | `rules: Partial<FirewallRule>[]` | `Promise<ImportResult>` |
| `exportRules()` | Export rules | `rules: FirewallRule[]`, `format: 'json' \| 'csv'` | `Observable<Blob>` |
| `parseCSV()` | Parse CSV content | `csvContent: string` | `Partial<FirewallRule>[]` |

#### Utility Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `validateRule()` | Validate rule data | `rule: Partial<FirewallRule>` | `{ valid: boolean; errors: string[] }` |
| `findDuplicates()` | Find duplicate rules | `rules: FirewallRule[]`, `newRule: Partial<FirewallRule>` | `FirewallRule[]` |
| `getAllRules()` | Get all rules (unpaginated) | None | `Observable<FirewallRule[]>` |

## Types

### FirewallRule

```typescript
interface FirewallRule {
    id: string;                           // Unique rule identifier
    rule_collection_name: string;         // Rule collection name
    priority: number;                     // Rule priority (1-1000)
    action: string;                       // 'Allow' or 'Deny'
    protocol: string;                     // 'Any', 'Tcp', 'Udp', 'IpProtocol'
    source_addresses?: string[];           // Source IP addresses
    destination_fqdns?: string[];          // Destination FQDNs
    source_ip_groups?: string[];           // Source IP groups
    destination_ports?: number[];          // Destination ports
    description?: string;                  // Rule description
    workload_id?: string;                  // Azure workload ID
    azure_resource_id?: string;            // Azure resource ID
    status: string;                        // 'active', 'pending', 'deleted'
    created_at: string;                    // ISO 8601 timestamp
    updated_at: string;                    // ISO 8601 timestamp
}
```

### PaginatedResponse

```typescript
interface PaginatedResponse<T> {
    items: T[];           // Array of items
    total: number;        // Total count
    page: number;         // Current page
    pageSize: number;     // Page size
    totalPages: number;   // Total pages
}
```

### BulkOperationResult

```typescript
interface BulkOperationResult {
    success: number;                    // Number of successful operations
    failed: number;                     // Number of failed operations
    errors: Array<{ id: string; error: string }>; // Error details
}
```

### ImportResult

```typescript
interface ImportResult {
    imported: number;    // Number of imported rules
    skipped: number;     // Number of skipped rules
    errors: string[];    // Error messages
}
```

## Testing

Unit tests are provided for all components:

- `rules-list.component.spec.ts` - Tests list functionality
- `rule-form-dialog.component.spec.ts` - Tests form submission
- `rule-detail.component.spec.ts` - Tests detail view
- `confirmation-dialog.component.spec.ts` - Tests confirmation dialog

Run tests with:

```bash
ng test
```

## Integration Example

### Module Import

```typescript
import { RulesModule } from './modules/rules/rules.module';

@NgModule({
  imports: [
    RulesModule,
    // ... other modules
  ]
})
export class AppModule { }
```

### Component Usage

```typescript
import { Component } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { RulesService, FirewallRule } from './modules/rules/services/rules.service';

@Component({
  selector: 'app-rules-container',
  template: `
    <app-rules-list></app-rules-list>
  `
})
export class RulesContainerComponent {
  constructor(
    private rulesService: RulesService,
    private dialog: MatDialog
  ) {}

  async importRules(fileContent: string) {
    try {
      const rules = JSON.parse(fileContent);
      const result = await this.rulesService.importRules(rules);
      console.log(`Imported ${result.imported} rules`);
    } catch (error) {
      console.error('Import failed:', error);
    }
  }
}
```

## Best Practices

1. **Always use bulk operations** when managing multiple rules to reduce API calls
2. **Export before bulk changes** to create a backup of your configuration
3. **Validate rules before importing** using `validateRule()` method
4. **Check for duplicates** using `findDuplicates()` before creating new rules
5. **Use pagination** for large rule sets to improve performance
6. **Filter by status** when looking for specific rule states
7. **Use detail view** to see complete rule configuration including addresses and ports

## Troubleshooting

### Common Issues

1. **Rules not loading**: Check that the backend API is running at `/api/v1/rules`
2. **Bulk operations failing**: Verify that all selected rules exist in the backend
3. **Import parsing errors**: Ensure CSV format matches expected columns
4. **Detail view not showing**: Check that rule data is properly formatted

### Debug Tips

1. Check browser console for TypeScript errors
2. Verify API responses in Network tab
3. Use Angular DevTools to inspect component state
4. Check service methods for proper error handling