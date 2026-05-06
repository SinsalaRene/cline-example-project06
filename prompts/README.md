# Implementation Prompts — Azure Firewall Management Application

This directory contains 8 focused, self-contained implementation prompts for completing the Azure Firewall Management application.

## Execution Order

Run prompts **in order** — each prompt depends on the previous one completing successfully.

| Step | Prompt | Scope | Est. Complexity |
|------|--------|-------|-----------------|
| 1 | [AUDIT_ENHANCEMENT](./PROMPT_01_AUDIT_ENHANCEMENT.md) | Audit list: date filtering, exports, summary stats | Medium |
| 2 | [AUDIT_DETAIL_VIEWER](./PROMPT_02_AUDIT_DETAIL_VIEWER.md) | Audit detail + resource viewer components | Medium |
| 3 | [WORKLOADS_MODULE](./PROMPT_03_WORKLOADS_MODULE.md) | Complete workloads CRUD module | Medium |
| 4 | [NETWORK_BACKEND](./PROMPT_04_NETWORK_BACKEND_SERVICES.md) | Backend: models, schemas, services, API | High |
| 5 | [NETWORK_TOPOLOGY](./PROMPT_05_NETWORK_TOPOLOGY_VIEWS.md) | Frontend: tree view + graph view | High |
| 6 | [NSG_MANAGEMENT](./PROMPT_06_NSG_MANAGEMENT.md) | NSG inline rule editing | Medium-High |
| 7 | [EXTERNAL_DEVICES](./PROMPT_07_EXTERNAL_DEVICES_IMPACT_ANALYSIS.md) | External devices + impact analysis | High |
| 8 | [SHARED_INFRA](./PROMPT_08_SHARED_INFRASTRUCTURE.md) | Shared components, interceptors, polish | Low-Medium |

## How to Use Each Prompt

1. Copy the prompt content from the `.md` file
2. Feed it to the agent as a standalone instruction
3. Each prompt includes:
   - Context (what exists, what needs to change)
   - Relevant file paths
   - Detailed task breakdown
   - Quality check checklist (verify after implementation)
   - Documentation requirements

## Architecture Overview

```
frontend/
├── core/              ← Prompt 8: interceptors, guards, services
├── shared/            ← Prompt 8: reusable components
├── modules/
│   ├── audit/         ← Prompt 1-2: enhanced list + detail + viewer
│   ├── approvals/     ← existing
│   ├── dashboard/     ← existing
│   ├── rules/         ← existing
│   ├── workloads/     ← Prompt 3: complete CRUD module
│   └── network/       ← Prompts 4-7: new module (topology, NSG, impact)
└── app-routing.module ← updated in prompts 3, 5, 6

backend/
├── models/            ← Prompt 4: new network.py models
├── schemas/           ← Prompt 4: new network.py schemas
├── services/          ← Prompt 4: new network_service.py
├── api/               ← Prompt 4: new network.py router
└── alembic/           ← Prompt 4: migration for network tables
```

## Prompt Dependencies

```
Prompt 1 → Prompt 2 (audit list → detail)
Prompt 3 (independent — workloads module)
Prompt 4 → Prompt 5 (backend → frontend topology)
Prompt 5 → Prompt 6 (topology views → NSG editing)
Prompt 6 → Prompt 7 (NSG → impact analysis)
Prompt 8 (independent — runs after all others)
```

**Parallel paths:** Prompt 1+2 can run independently of Prompt 3+4+5+6+7.
Prompt 8 runs last and depends on everything being stable.

## Skill Recommendations

When executing these prompts, consider using these skills:

- **`tdd`** — Use for Prompts 4, 5, 6, 7 (complex new features). Write tests first for:
  - Network backend services (models, schemas, service layer)
  - Network frontend components (tree view, graph view, NSG editor)
  - Impact analysis logic
  - External device CRUD

- **`improve-codebase-architecture`** — Use before Prompt 4 (new module creation). Run `npx -y @angular/cli mcp get_best_practices` for Angular conventions, then run `improve-codebase-architecture` to validate the network module architecture against existing code patterns.

- **`diagnose`** — Use if any prompt fails quality checks. Run the diagnose loop: reproduce → minimize → hypothesize → instrument → fix → regression-test.

## Quality Verification

After each prompt completes:
1. Run all quality checks listed in the prompt
2. Verify TypeScript compiles without errors: `cd frontend && npx tsc --noEmit`
3. Run backend tests: `cd backend && pytest tests/ -v`
4. Run frontend tests: `cd frontend && ng test --watch=false`
5. Verify API endpoints with: `curl http://localhost:8000/docs`
