Below is a concise UI requirements document you can share with the frontend developer.

## UI Requirements: Support Multiple Target Agent Types

### Goal
Update the UI so users can configure how the backend should test a target agent, not just define attack categories. The UI should support both:
- simulation-based execution
- real execution against different target agent types, including Azure AI Foundry-compatible targets

---

## Functional Requirements

### 1. Add target configuration section
On the attack configuration page, add a new section called “Target Agent Configuration”.

This section should allow the user to specify:
- target type
- target endpoint or project details
- authentication mode
- optional credentials or connection settings

### 2. Support target types
The UI should allow the user to choose at least the following target types:
- Generic HTTP endpoint
- Azure AI Foundry
- Simulation only

If possible, the UI should be designed so additional target types can be added later.

### 3. Show fields based on selected target type
The form should dynamically change based on the selected target type.

Examples:
- For Generic HTTP:
  - target URL
  - optional headers
  - optional auth method
- For Azure AI Foundry:
  - project endpoint
  - agent/project identifier
  - auth mode
- For Simulation:
  - no additional target connection fields needed

### 4. Send target configuration to backend
When the user submits the attack generation/execution request, the UI must send the target configuration along with:
- agent profile
- attack plan
- execution mode

The backend contract should receive this target config in the request body.

### 5. Preserve current behavior
Existing functionality must continue to work:
- generate prompts only
- generate and simulate responses
- generate and execute against a real endpoint

The new fields should be optional unless the selected execution mode requires them.

### 6. Validation
The UI should validate inputs before sending the request.

Examples:
- if target type is Generic HTTP, require a URL
- if target type is Azure AI Foundry, require the required Foundry fields
- if execution mode is real execution and no valid target config is provided, show an error

### 7. User experience
The UI should clearly explain:
- what each target type means
- when simulation is being used
- when the backend will call a real target agent

---

## API/Integration Requirements

### 1. Backend contract
The UI should send a request payload structure similar to:

```json
{
  "agent_profile": {...},
  "attack_plan": [...],
  "execute": true,
  "use_simulation": false,
  "target": {
    "type": "azure_foundry",
    "endpoint": "...",
    "auth": {
      "mode": "managed_identity"
    }
  }
}
```

The exact structure can be refined with backend team, but the UI should be built to send a structured target object.

### 2. Backward compatibility
The UI should remain compatible with the current backend request format where possible, or support a fallback if the backend still expects the older fields.

---

## UI Scope
The change should be limited to:
- attack configuration page
- request payload creation logic
- validation and error messaging

No backend logic changes are required in the UI.

---

## Acceptance Criteria
The UI should:
- allow users to configure a target agent type
- support at least generic HTTP and Azure AI Foundry
- send the target configuration to the backend
- show useful validation errors
- continue to work for existing simulation flows

---

## Notes for the UI Developer
Please keep the implementation modular so new target types can be added later without changing the whole flow.

If you want, I can also turn this into a more formal ticket-style format with “User Story”, “Acceptance Criteria”, and “Implementation Notes”.