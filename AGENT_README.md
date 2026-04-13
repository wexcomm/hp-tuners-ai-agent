# HP Tuners AI Agent - Agent Integration

This project is now integrated with the Agent Bridge communication system.

## Quick Start

### 1. Start the Agent

```bash
# Interactive mode (see what's happening)
python3 hp_tuners_ai_agent_agent.py run

# Or use the helper script
./start_agent.sh

# Daemon mode (background)
python3 hp_tuners_ai_agent_agent.py run --daemon
```

### 2. Check Status

```bash
python3 hp_tuners_ai_agent_agent.py status
```

### 3. Discover Other Agents

```bash
python3 hp_tuners_ai_agent_agent.py discover
```

### 4. Test Communication

```bash
# Run this in two different projects to see them communicate
python3 hp_tuners_ai_agent_agent.py test
```

## Communication Features

### From Other Agents

Other agents can:

1. **Send you commands:**
```python
agent.send_message(
    "HP Tuners AI Agent_agent",
    "command",
    {"command": "hello", "params": {}}
)
```

2. **Call RPC methods:**
```python
result = agent.call_agent(
    "HP Tuners AI Agent_agent",
    "ping",
    {"message": "hello"},
    timeout=5.0
)
```

3. **Check your status:**
```python
result = agent.call_agent(
    "HP Tuners AI Agent_agent",
    "get_status",
    {},
    timeout=5.0
)
```

### Your Agent's Capabilities

This agent is registered with:
- Agent ID: `HP Tuners AI Agent_agent`
- Capabilities: `tuning`, `diagnostics`, `api`, `automotive`, `j2534`
- Project: HP Tuners AI Agent

### Shared State

Access shared state between agents:
```python
# Write
agent.shared_state.set("my_key", {"data": "value"}, namespace="HP Tuners AI Agent")

# Read
data = agent.shared_state.get("my_key", namespace="HP Tuners AI Agent")
```

## Custom Commands

Edit `hp_tuners_ai_agent_agent.py` and modify the `execute_command` method:

```python
def execute_command(self, command: str, params: dict = None):
    if command == "my_custom_command":
        # Your logic here
        return {"result": "success"}
    
    # Don't forget to call super for default commands
    return super().execute_command(command, params)
```

## Agent Network

When you run multiple project agents, they:
1. Auto-discover each other
2. Can send messages
3. Can call RPC methods
4. Share state
5. Coordinate tasks

Run `python3 hp_tuners_ai_agent_agent.py test` to see it in action!
