# 🔧 HP Tuners AI Agent - Agent Bridge Integration

## Overview

This guide integrates the Agent Bridge communication system with your HP Tuners AI Agent project.

## Setup Steps

### Step 1: Copy Files to Your Laptop

Since your HP Tuners project is at `C:\git\hp-tuners-ai-agent` on your laptop, you need to copy the agent communication files there.

**Option A: Clone the repo on your laptop**
```bash
# On your laptop (Windows Terminal/Git Bash)
cd C:\git
git clone https://github.com/wexcomm/hermes-ollama-agent.git temp-hermes
cp -r temp-hermes/agent-comm hp-tuners-ai-agent/
rm -rf temp-hermes
```

**Option B: Download just the files**
```bash
# Download from GitHub
curl -L https://raw.githubusercontent.com/wexcomm/hermes-ollama-agent/main/agent-comm/agent_bridge.py > agent_bridge.py
curl -L https://raw.githubusercontent.com/wexcomm/hermes-ollama-agent/main/agent-comm/example_agent.py > example_agent.py
```

**Option C: Use the integration script from server**
The integration script is ready on the server. Just run the setup commands below in your project.

### Step 2: Run Integration Script

In your HP Tuners project directory:

```bash
# Windows (Git Bash or WSL)
cd C:/git/hp-tuners-ai-agent
python3 integrate_with_project.py "HP Tuners AI Agent" tuning diagnostics api automotive --path .
```

This creates:
- `hp_tuners_ai_agent.py` - Your agent wrapper
- `agent_config.json` - Configuration
- `start_agent.sh` - Quick start script
- `AGENT_README.md` - Documentation

### Step 3: Start the Agent

**Terminal 1 (VS Code integrated terminal in hp-tuners-ai-agent folder):**
```bash
python3 hp_tuners_ai_agent.py run
```

You'll see:
```
🚀 hp_tuners_ai_agent_agent started
   Project: HP Tuners AI Agent
   Capabilities: tuning, diagnostics, api, automotive
   Path: C:/git/hp-tuners-ai-agent
```

## How It Works

### Your Agent Can:

1. **Communicate with other agents** - Send/receive messages
2. **Receive commands** - Other agents can tell it what to do
3. **Share data** - Store and retrieve shared state
4. **Be discovered** - Other agents can find it by capability

### From Other Agents

**Send a command to HP Tuners agent:**
```python
# From another agent (like a coordinator)
agent.send_message(
    "hp_tuners_ai_agent_agent",
    "command",
    {
        "command": "analyze_tuning_data",
        "params": {"file": "tune_v1.bin"}
    }
)
```

**Call HP Tuners methods directly:**
```python
# RPC call
result = agent.call_agent(
    "hp_tuners_ai_agent_agent",
    "execute",
    {
        "command": "diagnose",
        "params": {"ecu_id": "ABC123"}
    },
    timeout=30.0
)
```

**Discover HP Tuners agent by capability:**
```python
# Find all agents with "tuning" capability
tuning_agents = agent.discover_agents(capability="tuning")
```

## Customizing for HP Tuners

### Add HP Tuners-Specific Commands

Edit `hp_tuners_ai_agent.py` and modify the `execute_command` method:

```python
def execute_command(self, command: str, params: dict = None):
    params = params or {}
    
    # HP Tuners specific commands
    if command == "read_tune":
        file_path = params.get("file")
        # Your logic to read tune file
        return {"tune_data": {...}, "success": True}
    
    elif command == "modify_tune":
        tune_id = params.get("tune_id")
        changes = params.get("changes", {})
        # Your logic to modify tune
        return {"modified": True, "new_checksum": "..."}
    
    elif command == "flash_ecu":
        tune_file = params.get("tune_file")
        ecu_id = params.get("ecu_id")
        # Your flashing logic
        return {"flashed": True, "verified": True}
    
    elif command == "scan_diagnostics":
        ecu_id = params.get("ecu_id")
        # Run diagnostic scan
        return {"codes": [...], "live_data": {...}}
    
    elif command == "analyze_log":
        log_file = params.get("log_file")
        # Analyze datalog
        return {"analysis": {...}, "recommendations": [...]}
    
    # Call parent for default commands
    return super().execute_command(command, params)
```

### Add Project-Specific RPC Methods

```python
def _register_handlers(self):
    # ... existing handlers ...
    
    # Register HP Tuners specific RPC methods
    self.agent.register_rpc_method("read_tune", self.read_tune)
    self.agent.register_rpc_method("flash_ecu", self.flash_ecu)
    self.agent.register_rpc_method("scan_diagnostics", self.scan_diagnostics)


def read_tune(self, file_path: str) -> dict:
    """Read and parse a tune file"""
    # Your implementation
    return {"tune": {...}, "metadata": {...}}

def flash_ecu(self, tune_file: str, ecu_id: str) -> dict:
    """Flash ECU with tune"""
    # Your implementation
    return {"success": True, "flash_time": 45.2}

def scan_diagnostics(self, ecu_id: str) -> dict:
    """Scan for diagnostic trouble codes"""
    # Your implementation
    return {"dtc_codes": [...], "status": "complete"}
```

## Multi-Agent Workflow

### Example: Tuning Coordinator System

**Coordinator Agent** (Terminal 1):
```python
from agent_bridge import Agent

class TuningCoordinator:
    def __init__(self):
        self.agent = Agent("tuning_coordinator", ["orchestration"])
        self.agent.start()
    
    def tune_vehicle(self, vehicle_data: dict):
        # 1. Discover HP Tuners agent
        hp_agent = self.agent.discover_agents(
            capability="tuning"
        )[0]
        
        # 2. Read current tune
        current = self.agent.call_agent(
            hp_agent["agent_id"],
            "read_tune",
            {"file": vehicle_data["current_tune_file"]},
            timeout=10.0
        )
        
        # 3. Analyze with compute agent
        compute_agent = self.agent.discover_agents(
            capability="compute"
        )[0]
        
        analysis = self.agent.call_agent(
            compute_agent["agent_id"],
            "calculate",
            {"expression": "optimize_tune(current)"},
            timeout=30.0
        )
        
        # 4. Modify tune via HP agent
        modified = self.agent.call_agent(
            hp_agent["agent_id"],
            "modify_tune",
            {
                "tune_id": current["tune_id"],
                "changes": analysis["optimizations"]
            },
            timeout=30.0
        )
        
        # 5. Flash to ECU
        result = self.agent.call_agent(
            hp_agent["agent_id"],
            "flash_ecu",
            {
                "tune_file": modified["file"],
                "ecu_id": vehicle_data["ecu_id"]
            },
            timeout=120.0
        )
        
        return result
```

**HP Tuners Agent** (Terminal 2):
```bash
# Just run the agent - it will receive and execute commands
python3 hp_tuners_ai_agent.py run
```

**Compute Agent** (Terminal 3):
```bash
python3 example_agent.py compute
```

## Communication Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Coordinator   │────▶│  HP Tuners Agent │────▶│    Vehicle      │
│    (Terminal 1) │     │   (Terminal 2)   │     │      ECU        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │
         │              ┌──────────────────┐
         └─────────────▶│  Compute Agent   │
                        │  (Terminal 3)    │
                        └──────────────────┘
```

## Testing

### Test 1: Single Agent
```bash
python3 hp_tuners_ai_agent.py status
```

### Test 2: Agent Discovery
```bash
# Terminal 1
python3 hp_tuners_ai_agent.py run

# Terminal 2 (different folder with another agent)
python3 example_agent.py coordinator
```

### Test 3: Full Communication
```bash
# Start HP agent
python3 hp_tuners_ai_agent.py run

# In another terminal, test communication
python3 -c "
from agent_bridge import Agent
import time

agent = Agent('tester', ['test'])
agent.start()

# Call HP agent
time.sleep(2)
result = agent.call_agent(
    'hp_tuners_ai_agent_agent',
    'ping',
    {'message': 'hello'},
    timeout=5.0
)
print(f'Response: {result}')

agent.stop()
"
```

## Shared State Use Cases

### Share Tuning Database
```python
# HP agent stores tuning data
self.agent.shared_state.set(
    "tune_database",
    {"tunes": [...], "updated": "2024-04-11"},
    namespace="hp_tuners"
)

# Other agents can read it
db = agent.shared_state.get("tune_database", namespace="hp_tuners")
```

### Share Vehicle Profiles
```python
# Store vehicle configuration
self.agent.shared_state.set(
    f"vehicle_{vin}",
    {
        "make": "Chevrolet",
        "model": "Camaro",
        "engine": "LS3",
        "current_tune": "aggressive_street_v2"
    },
    namespace="vehicles"
)
```

### Share Diagnostic Results
```python
# After scanning
self.agent.shared_state.set(
    f"diagnostics_{ecu_id}",
    {
        "timestamp": "2024-04-11T10:30:00",
        "dtc_codes": ["P0171", "P0174"],
        "live_data": {...}
    },
    namespace="diagnostics"
)
```

## Troubleshooting

### Agent Not Discovered
```bash
# Check registry
ls -la /tmp/agent_comm/registry/
cat /tmp/agent_comm/registry/hp_tuners_ai_agent_agent.json

# Manual heartbeat
python3 -c "
from agent_bridge import AgentRegistry
r = AgentRegistry()
r.heartbeat('hp_tuners_ai_agent_agent')
"
```

### Messages Not Received
```bash
# Check inbox
ls -la /tmp/agent_comm/messages/hp_tuners_ai_agent_agent/

# Check file permissions
chmod 777 /tmp/agent_comm -R
```

### RPC Timeout
- Increase timeout in `call_agent()`
- Check if target agent is running
- Check agent capabilities match

## Security

Since agents communicate via files in `/tmp/agent_comm/`:

1. **File permissions** - Only your user should have access
2. **No network exposure** - File-based is local-only
3. **For cross-machine** - Use SSH tunnel or VPN to share `/tmp/agent_comm/`

## Next Steps

1. ✅ Copy agent-comm/ to your laptop project
2. ✅ Run integration script
3. ✅ Customize with HP Tuners commands
4. ✅ Test with coordinator agent
5. ✅ Build multi-agent tuning workflow

## Questions?

- Check `AGENT_README.md` in your project
- Read full docs in `agent-comm/README.md`
- Run `python3 hp_tuners_ai_agent.py --help`

Happy tuning! 🚗💨
