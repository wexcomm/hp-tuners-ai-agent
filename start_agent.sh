#!/bin/bash
# Quick start script for HP Tuners AI Agent Agent

echo "🚀 Starting HP Tuners AI Agent Agent..."

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
python3 hp_tuners_ai_agent_agent.py run "$@"
