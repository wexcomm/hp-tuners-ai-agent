#!/usr/bin/env python3
"""
Agent Integration Helper - Add agent communication to any project
Run this in your project directory to create an agent wrapper
"""

import os
import sys
import json
from pathlib import Path

def create_agent_wrapper(project_name: str, capabilities: list, project_path: str = "."):
    """Create an agent wrapper for a project"""
    
    # Create agent_config.json
    config = {
        "agent_id": f"{project_name}_agent",
        "project_name": project_name,
        "capabilities": capabilities,
        "project_path": os.path.abspath(project_path),
        "auto_start": True,
        "log_level": "info"
    }
    
    config_file = Path(project_path) / "agent_config.json"
    config_file.write_text(json.dumps(config, indent=2))
    print(f"✅ Created: {config_file}")
    
    # Create project_agent.py wrapper
    wrapper_code = f'''#!/usr/bin/env python3
"""
{project_name} Agent - Integrated with Agent Bridge
Auto-generated wrapper for inter-agent communication
"""

import sys
import os
from pathlib import Path

# Add agent-comm to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agent-comm"))

from agent_bridge import Agent, SharedState
import json
import time

class {project_name.replace("-", "_").replace(" ", "_").title()}Agent:
    """
    Agent wrapper for {project_name} project
    Provides inter-agent communication capabilities
    """
    
    def __init__(self):
        # Load config
        config_path = Path(__file__).parent / "agent_config.json"
        with open(config_path) as f:
            self.config = json.load(f)
        
        # Create agent
        self.agent = Agent(
            agent_id=self.config["agent_id"],
            capabilities=self.config["capabilities"],
            metadata={{
                "project": self.config["project_name"],
                "path": self.config["project_path"],
                "type": "project_agent"
            }}
        )
        
        # Register default handlers
        self._register_handlers()
        
        self.running = False
    
    def _register_handlers(self):
        """Register message handlers"""
        
        @self.agent.on_message("status_request")
        def handle_status(msg):
            """Respond to status requests from other agents"""
            self.agent.send_message(
                recipient=msg.sender,
                msg_type="status_response",
                payload={{
                    "agent_id": self.config["agent_id"],
                    "project": self.config["project_name"],
                    "status": "running" if self.running else "idle",
                    "capabilities": self.config["capabilities"]
                }}
            )
        
        @self.agent.on_message("command")
        def handle_command(msg):
            """Handle commands from coordinator agents"""
            command = msg.payload.get("command")
            params = msg.payload.get("params", {{}})
            
            # Custom command handling
            result = self.execute_command(command, params)
            
            self.agent.send_message(
                recipient=msg.sender,
                msg_type="command_response",
                payload={{
                    "command": command,
                    "result": result,
                    "success": result is not None
                }}
            )
        
        # Register RPC methods
        self.agent.register_rpc_method("ping", self.ping)
        self.agent.register_rpc_method("get_status", self.get_status)
        self.agent.register_rpc_method("execute", self.execute_command)
    
    def ping(self, message: str = "pong") -> str:
        """Simple ping test"""
        return f"{{self.config['agent_id']}}: {{message}}"
    
    def get_status(self) -> dict:
        """Get current status"""
        return {{
            "agent_id": self.config["agent_id"],
            "running": self.running,
            "capabilities": self.config["capabilities"],
            "project": self.config["project_name"]
        }}
    
    def execute_command(self, command: str, params: dict = None) -> any:
        """
        Execute a project-specific command
        Override this method to add custom functionality
        """
        params = params or {{}}
        
        # Default commands - customize for your project
        if command == "hello":
            return f"Hello from {{self.config['project_name']}}!"
        
        elif command == "info":
            return {{
                "project": self.config["project_name"],
                "agent_id": self.config["agent_id"],
                "path": self.config["project_path"],
                "capabilities": self.config["capabilities"]
            }}
        
        elif command == "discover":
            # Discover other agents
            agents = self.agent.discover_agents()
            return [{{"id": a["agent_id"], "caps": a.get("capabilities", [])}} for a in agents]
        
        else:
            return {{"error": f"Unknown command: {{command}}", "available": ["hello", "info", "discover"]}}
    
    def start(self):
        """Start the agent"""
        self.agent.start()
        self.running = True
        print(f"🚀 {{self.config['agent_id']}} started")
        print(f"   Project: {{self.config['project_name']}}")
        print(f"   Capabilities: {{', '.join(self.config['capabilities'])}}")
        print(f"   Path: {{self.config['project_path']}}")
        
        # Share project info
        self.agent.shared_state.set(
            f"{{self.config['agent_id']}}_info",
            self.get_status(),
            namespace="projects"
        )
    
    def stop(self):
        """Stop the agent"""
        self.running = False
        self.agent.stop()
        print(f"🛑 {{self.config['agent_id']}} stopped")
    
    def run_interactive(self):
        """Run in interactive mode"""
        self.start()
        
        print("\\n📡 Agent is running. Press Ctrl+C to stop.")
        print("\\nThis agent can:")
        print("  - Receive commands from other agents")
        print("  - Respond to status requests")
        print("  - Share state with other agents")
        print("  - Execute RPC calls")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\\n\\n🛑 Stopping...")
            self.stop()

# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="{project_name} Agent")
    parser.add_argument("command", nargs="?", default="run",
                       choices=["run", "status", "discover", "test"],
                       help="Command to execute")
    parser.add_argument("--daemon", action="store_true",
                       help="Run as daemon (no interactive output)")
    
    args = parser.parse_args()
    
    agent = {project_name.replace("-", "_").replace(" ", "_").title()}Agent()
    
    if args.command == "run":
        if args.daemon:
            agent.start()
            # Keep running
            import signal
            signal.signal(signal.SIGINT, lambda s, f: agent.stop())
            signal.pause()
        else:
            agent.run_interactive()
    
    elif args.command == "status":
        agent.start()
        print(json.dumps(agent.get_status(), indent=2))
        agent.stop()
    
    elif args.command == "discover":
        agent.start()
        agents = agent.agent.discover_agents()
        print(f"\\n🔍 Found {{len(agents)}} agent(s):")
        for a in agents:
            print(f"  - {{a['agent_id']}}: {{', '.join(a.get('capabilities', []))}}")
        agent.stop()
    
    elif args.command == "test":
        # Test communication
        agent.start()
        
        # Broadcast presence
        agent.agent.broadcast(
            "announcement",
            {{"message": f"{{agent.config['agent_id']}} is online!"}}
        )
        
        # Check for other agents
        time.sleep(2)
        other_agents = agent.agent.discover_agents()
        
        if len(other_agents) > 1:  # More than just ourselves
            print(f"\\n📡 Found {{len(other_agents) - 1}} other agent(s)")
            
            # Try to ping first other agent
            for other in other_agents:
                if other["agent_id"] != agent.config["agent_id"]:
                    try:
                        result = agent.agent.call_agent(
                            other["agent_id"],
                            "ping",
                            {{"message": "hello from {project_name}"}},
                            timeout=5.0
                        )
                        print(f"\\n✅ Ping {{other['agent_id']}}: {{result}}")
                    except Exception as e:
                        print(f"\\n❌ Ping {{other['agent_id']}} failed: {{e}}")
                    break
        else:
            print("\\n⚠️ No other agents found. Run this in another project to test communication.")
        
        agent.stop()
'''
    
    wrapper_file = Path(project_path) / f"{project_name.lower().replace(' ', '_').replace('-', '_')}_agent.py"
    wrapper_file.write_text(wrapper_code)
    print(f"✅ Created: {wrapper_file}")
    
    # Make executable
    wrapper_file.chmod(0o755)
    
    # Create requirements addition
    req_file = Path(project_path) / "requirements-agent.txt"
    req_content = """# Agent Bridge Dependencies
# Add these to your main requirements.txt or install separately:

# File-based messaging (no external deps needed)
# Uses only Python stdlib: json, pathlib, threading, time, etc.

# Optional: For network bridging between machines
# redis>=5.0.0  # If using Redis backend instead of files

# Install agent-bridge from sibling directory
# Or copy agent_bridge.py to your project
"""
    req_file.write_text(req_content)
    print(f"✅ Created: {req_file}")
    
    # Create quick start script
    quickstart = f'''#!/bin/bash
# Quick start script for {project_name} Agent

echo "🚀 Starting {project_name} Agent..."

# Check if agent_bridge is available
if [ -f "../agent-comm/agent_bridge.py" ]; then
    echo "✅ Found agent-comm in parent directory"
elif [ -f "./agent_bridge.py" ]; then
    echo "✅ Found agent_bridge.py in current directory"
else
    echo "⚠️  agent_bridge.py not found!"
    echo "   Copy it from: /path/to/hermes-ollama/agent-comm/"
    exit 1
fi

# Run the agent
python3 {wrapper_file.name} run "$@"
'''
    
    quickstart_file = Path(project_path) / "start_agent.sh"
    quickstart_file.write_text(quickstart)
    quickstart_file.chmod(0o755)
    print(f"✅ Created: {quickstart_file}")
    
    # Create README
    readme = f"""# {project_name} - Agent Integration

This project is now integrated with the Agent Bridge communication system.

## Quick Start

### 1. Start the Agent

```bash
# Interactive mode (see what's happening)
python3 {wrapper_file.name} run

# Or use the helper script
./start_agent.sh

# Daemon mode (background)
python3 {wrapper_file.name} run --daemon
```

### 2. Check Status

```bash
python3 {wrapper_file.name} status
```

### 3. Discover Other Agents

```bash
python3 {wrapper_file.name} discover
```

### 4. Test Communication

```bash
# Run this in two different projects to see them communicate
python3 {wrapper_file.name} test
```

## Communication Features

### From Other Agents

Other agents can:

1. **Send you commands:**
```python
agent.send_message(
    "{config['agent_id']}",
    "command",
    {{"command": "hello", "params": {{}}}}
)
```

2. **Call RPC methods:**
```python
result = agent.call_agent(
    "{config['agent_id']}",
    "ping",
    {{"message": "hello"}},
    timeout=5.0
)
```

3. **Check your status:**
```python
result = agent.call_agent(
    "{config['agent_id']}",
    "get_status",
    {{}},
    timeout=5.0
)
```

### Your Agent's Capabilities

This agent is registered with:
- Agent ID: `{config['agent_id']}`
- Capabilities: {', '.join(f"`{c}`" for c in capabilities)}
- Project: {project_name}

### Shared State

Access shared state between agents:
```python
# Write
agent.shared_state.set("my_key", {{"data": "value"}}, namespace="{project_name}")

# Read
data = agent.shared_state.get("my_key", namespace="{project_name}")
```

## Custom Commands

Edit `{wrapper_file.name}` and modify the `execute_command` method:

```python
def execute_command(self, command: str, params: dict = None):
    if command == "my_custom_command":
        # Your logic here
        return {{"result": "success"}}
    
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

Run `python3 {wrapper_file.name} test` to see it in action!
"""
    
    readme_file = Path(project_path) / "AGENT_README.md"
    readme_file.write_text(readme)
    print(f"✅ Created: {readme_file}")
    
    print(f"\n🎉 {project_name} is now agent-enabled!")
    print(f"\nNext steps:")
    print(f"  1. cd {project_path}")
    print(f"  2. python3 {wrapper_file.name} run")
    print(f"  3. In another terminal: python3 {wrapper_file.name} test")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Integrate agent communication with any project"
    )
    parser.add_argument("project_name", help="Name of your project")
    parser.add_argument("capabilities", nargs="+", 
                       default=["compute"],
                       help="Agent capabilities (e.g., tuning diagnostics api)")
    parser.add_argument("--path", default=".",
                       help="Path to project directory")
    
    args = parser.parse_args()
    
    create_agent_wrapper(
        args.project_name,
        args.capabilities,
        args.path
    )
