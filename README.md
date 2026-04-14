# Agent Automation Factory

**Stop manual task assignment and start intelligent agent workflows.** This system transforms how teams work by:

## Prerequisites

- **Python 3.12+** - Required runtime
- **Git** - Version control
- **GitHub CLI (`gh`)** - For GitHub operations
- **pip** - Package manager

## Dependencies

Install project dependencies:

```bash
pip install -e .
```

Required packages (see `pyproject.toml`):
- `claude-agent-sdk>=0.1.29`
- `flask>=3.0.0`
- `python-dotenv>=1.0.0`
- `textual>=0.62.0`
- `tzdata>=2024.1`

## How to Run the Dashboard

The agent dashboard provides a visual interface for monitoring agent automation.

```bash
# Run the TUI dashboard
python -m agent_dashboard

# Or run as a web server
python -m agent_dashboard --serve
```

The dashboard displays:
- Active workers and their current issues
- Queue status (ready, active, done labels)
- Worker logs and metrics

**Start a local worker:**
```bash
.agent-automation/hooks/local-worker-start.sh <issue-number>
```

For more worker commands, see `AGENTS.md`.

## Setup Steps

1. **Install dependencies:**
   ```bash
   pip install -e .
   ```

2. **Configure GitHub authentication:**
   ```bash
   gh auth login
   ```

3. **Verify installation:**
   ```bash
   ./scripts/validate.sh
   ```

4. **Start workers** (optional, for local automation):
   ```bash
   .agent-automation/hooks/local-worker-launch-tmux.sh --run-agent <issue-number>
   ```

---

**Stop manual task assignment and start intelligent agent workflows.** This system transforms how teams work by:

- **Automatically assigning the right AI agent** to each GitHub issue based on required skills (role) and domain (lane)
- **Optimizing costs** by matching task complexity to appropriate AI model tiers (low/standard/high)
- **Eliminating context switching** - agents work continuously on assigned tickets without human intervention
- **Scaling development capacity** - run multiple specialized agents in parallel 24/7
- **Ensuring consistency** - every agent follows the same workflow standards and validation procedures

## How It Works

1. **You define the work**: Create GitHub issues using our standardized template, selecting a **role** (what skills are needed) and **lane** (what domain/backend/frontend/etc.)
2. **System assigns the agent**: Based on your role selection, the system picks the appropriate AI model (e.g., junior tasks get faster/cheaper models, architecture tasks get powerful models)
3. **Agents pick up work**: Automated workers continuously scan for "ready" issues, claim them, and execute using their assigned AI
4. **You monitor progress**: Issues move through standard GitHub workflow (ready → active → needs decision → done) with full audit trail
5. **Results integrate naturally**: Agents create branches, commit code, open PRs, and update issues just like human developers

## Cost & Efficiency Benefits

- **Right-sizing AI usage**: Simple tasks (documentation, tweaks) use low-cost models; complex tasks (architecture, debugging) use powerful models
- **No idle time**: Agents work 24/7 on queued work - no waiting for human availability
- **Predictable costs**: Role-based pricing lets you budget AI usage by task type
- **Reduced overhead**: Eliminates manual task assignment, context switching, and status meeting time

## Sample Workflow: From Requirements to Sprint

**Scenario**: Product manager finishes designing a new feature and needs development to begin.

### Step 1: Create Tickets (Human)
Product manager creates 3 GitHub issues using our template:
1. **Issue #101**: 
   - Role: `implementer` 
   - Lane: `agent:backend`
   - Outcome: "Implement user authentication API with JWT tokens"
2. **Issue #102**:
   - Role: `implementer`
   - Lane: `agent:frontend` 
   - Outcome: "Create login/logout UI components with form validation"
3. **Issue #103**:
   - Role: `architect` (custom role you defined)
   - Lane: `agent:infra`
   - Outcome: "Design scalable microservice architecture for auth service"

### Step 2: Agent Assignment (Automatic)
- Issue #101 → `implementer` role → `standard` cost → `nemotron-3-super-free` model (backend)
- Issue #102 → `implementer` role → `standard` cost → `nemotron-3-super-free` model (frontend)  
- Issue #103 → `architect` role → `high` cost → `nemotron-3-super-free` model (architecture)

### Step 3: Agents Execute (Automatic)
Your local agent workers (running in terminal or as services) continuously:
1. Scan for issues with `ready` label
2. Claim Issue #103 first (highest priority/complexity)
3. Create feature branch: `agent/issue-103-infra`
4. Use assigned AI to design microservice architecture
5. Commit proposed architecture docs and diagrams
6. Open PR: "Design scalable microservice architecture for auth service"
7. Move issue to `active` label while PR is open

### Step 4: Human Review & Continuation
- You review the architect's PR, provide feedback, approve
- Once merged, Issue #103 automatically moves to `needs decision` or ready for next phase
- Meanwhile, Issues #101 and #102 have been picked up by implementer agents
- Backend agent is coding the JWT API, frontend agent is building login UI

### Step 5: Monitoring Progress (Human)
Check status anytime with:
```bash
# See what agents are working on
gh issue list -l "active" 

# Check completed work  
gh issue list -l "done"

# View agent logs
cat .agent-automation/logs/worker-*.log

# See queued work
gh issue list -l "ready"
```

### Step 6: Continuous Flow
As tickets complete:
- Implementer agents automatically move to next ready `implementer` tasks
- Architect agent picks up next high-complexity infrastructure task
- QA agents verify completed work when lanes are done
- No manual reassignment needed - the system self-balances based on issue labels

## 🔁 Key Advantages Over Manual Assignment

| Manual Assignment | Agent Automation System |
|-------------------|-------------------------|
| Human spends time matching tasks to skills | System auto-matches based on role labels |
| Expensive models used on simple tasks | Right-sized model allocation per task complexity |
| Work waits for human availability | 24/7 agent processing queue |
| Context switching reduces productivity | Agents maintain deep focus on assigned work |
| Inconsistent approaches across team | Standardized agent workflows and validation |
| Hard to scale during peak periods | Add more agent workers instantly |

This turns your GitHub repository into a self-orchestrating work factory where AI agents handle routine development work, freeing humans for creative design, strategic decisions, and complex problem-solving that requires human judgment.
