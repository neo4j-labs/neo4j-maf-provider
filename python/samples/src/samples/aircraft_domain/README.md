# Aircraft Domain Samples

Domain-specific samples using an aircraft maintenance knowledge graph. Demonstrates fulltext search with graph-enriched context for real-world maintenance scenarios.

## Samples

### maintenance_search.py - Aircraft Maintenance Search

Search maintenance events and enrich with aircraft, system, and component context.

```bash
uv run start-samples 5
```

**Graph Pattern:**
```
MaintenanceEvent <- Component <- System <- Aircraft
```

**Returns:** fault, corrective_action, severity, aircraft, system, component

### flight_delays.py - Flight Delay Analysis

Analyze flight delays with route and aircraft information.

```bash
uv run start-samples 6
```

**Graph Pattern:**
```
Delay <- Flight -> Aircraft, Origin Airport, Destination Airport
```

**Returns:** cause, minutes, flight, aircraft, route

### component_health.py - Component Health Analysis

Component health analysis with maintenance event counts and system hierarchy.

```bash
uv run start-samples 7
```

**Graph Pattern:**
```
Component <- System <- Aircraft
Component -> MaintenanceEvent (count)
```

**Returns:** component, type, aircraft, system, maintenance_events, severity

## Required Environment Variables

```
AZURE_AI_PROJECT_ENDPOINT=https://your-project.cognitiveservices.azure.com
AZURE_AI_MODEL_NAME=gpt-4o
AIRCRAFT_NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
AIRCRAFT_NEO4J_USERNAME=neo4j
AIRCRAFT_NEO4J_PASSWORD=your-password
```

## Database Schema

The aircraft database contains:

- **Aircraft** - Aircraft records with tail numbers and models
- **System** - Aircraft systems (hydraulic, electrical, etc.)
- **Component** - Components within systems
- **MaintenanceEvent** - Maintenance records with faults and actions
- **Flight** - Flight records
- **Delay** - Delay records with causes
- **Airport** - Airport information

## Fulltext Indexes

- `maintenance_search` - Searches MaintenanceEvent fault/action fields
- `delay_search` - Searches Delay cause field
- `component_search` - Searches Component name/type fields
