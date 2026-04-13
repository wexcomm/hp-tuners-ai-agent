#!/usr/bin/env python3
"""
Example Agent - Shows how to use the agent communication system
Run this in different VS Code terminals to see agents talk to each other
"""

import sys
import time
import json
from agent_bridge import Agent

def run_compute_agent():
    """Example: Compute agent that can be asked to do calculations"""
    
    agent = Agent(
        agent_id="compute_agent",
        capabilities=["math", "compute", "search"],
        metadata={
            "description": "Agent that performs calculations and searches",
            "version": "1.0"
        }
    )
    
    # Register RPC methods that other agents can call
    @agent.register_rpc_method
    def calculate(expression: str) -> dict:
        """Evaluate a mathematical expression"""
        try:
            # Safe eval - only allow basic math
            allowed = {"__builtins__": {}}
            allowed.update({
                "abs": abs, "round": round, "max": max, "min": min,
                "sum": sum, "pow": pow
            })
            result = eval(expression, allowed)
            return {"result": result, "success": True}
        except Exception as e:
            return {"error": str(e), "success": False}
    
    @agent.register_rpc_method
    def search(query: str, max_results: int = 5) -> dict:
        """Simulate a search (placeholder for actual implementation)"""
        return {
            "query": query,
            "results": [f"Result {i} for '{query}'" for i in range(1, max_results + 1)],
            "success": True
        }
    
    # Handle incoming messages
    @agent.on_message("task_request")
    def handle_task(msg):
        print(f"\n📥 Received task from {msg.sender}: {msg.payload}")
        
        # Process task
        task_type = msg.payload.get("task_type")
        params = msg.payload.get("params", {})
        
        if task_type == "calculate":
            result = calculate(**params)
        elif task_type == "search":
            result = search(**params)
        else:
            result = {"error": f"Unknown task type: {task_type}"}
        
        # Send response
        agent.send_message(
            recipient=msg.sender,
            msg_type="task_response",
            payload={
                "task_id": msg.payload.get("task_id"),
                "result": result
            }
        )
        print(f"📤 Sent response to {msg.sender}")
    
    # Start agent
    print("🚀 Starting Compute Agent...")
    agent.start()
    
    print("\nAgent is running. Press Ctrl+C to stop.")
    print("This agent can:")
    print("  - Receive task requests via messages")
    print("  - Handle RPC calls for 'calculate' and 'search'")
    print("  - Store results in shared state")
    
    try:
        while True:
            # Show any pending messages
            messages = agent.message_bus.get_pending_messages()
            if messages:
                print(f"\n📨 {len(messages)} pending messages")
            
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping agent...")
        agent.stop()
        print("✅ Agent stopped")

def run_coordinator_agent():
    """Example: Coordinator agent that orchestrates other agents"""
    
    agent = Agent(
        agent_id="coordinator",
        capabilities=["orchestration", "management"],
        metadata={
            "description": "Coordinates tasks across multiple agents",
            "version": "1.0"
        }
    )
    
    # Start agent
    print("🚀 Starting Coordinator Agent...")
    agent.start()
    
    print("\n📋 Discovering available agents...")
    time.sleep(1)
    
    agents = agent.discover_agents()
    print(f"Found {len(agents)} active agent(s):")
    for a in agents:
        print(f"  - {a['agent_id']}: {', '.join(a.get('capabilities', []))}")
    
    # Example: Send a calculation task
    if any(a['agent_id'] == 'compute_agent' for a in agents):
        print("\n🧮 Testing compute capability...")
        try:
            result = agent.call_agent(
                "compute_agent",
                "calculate",
                {"expression": "2**10 + 100"},
                timeout=10.0
            )
            print(f"  Result: {result}")
        except Exception as e:
            print(f"  Error: {e}")
        
        print("\n🔍 Testing search capability...")
        try:
            result = agent.call_agent(
                "compute_agent",
                "search",
                {"query": "AI agents", "max_results": 3},
                timeout=10.0
            )
            print(f"  Results: {result}")
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n📊 Coordinator is running. Press Ctrl+C to stop.")
    print("\nAvailable commands:")
    print("  - Will discover and coordinate with other agents")
    print("  - Can call RPC methods on other agents")
    print("  - Can broadcast messages to all agents")
    
    # Test broadcast
    print("\n📢 Broadcasting test message...")
    agent.broadcast("ping", {"test": True, "message": "Hello from coordinator"})
    
    try:
        while True:
            messages = agent.message_bus.get_pending_messages()
            for msg in messages:
                print(f"\n📨 Message from {msg.sender}: {msg.message_type}")
                print(f"   Payload: {msg.payload}")
                
                if msg.message_type == "ping" and msg.payload.get("expect_response"):
                    agent.send_message(
                        msg.sender,
                        "pong",
                        {"in_response_to": msg.id}
                    )
            
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping coordinator...")
        agent.stop()
        print("✅ Coordinator stopped")

def run_monitor_agent():
    """Example: Monitor agent that watches system state"""
    
    agent = Agent(
        agent_id="monitor",
        capabilities=["monitoring", "logging"],
        metadata={
            "description": "Monitors system state and agent health",
            "version": "1.0"
        }
    )
    
    @agent.on_message("*")  # Subscribe to all message types
    def log_all_messages(msg):
        """Log all messages for monitoring"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {msg.sender} -> {msg.recipient}: {msg.message_type}")
        
        # Store in shared state for later analysis
        logs = agent.shared_state.get("message_logs", namespace="monitoring") or []
        logs.append({
            "timestamp": msg.timestamp,
            "sender": msg.sender,
            "recipient": msg.recipient,
            "type": msg.message_type
        })
        # Keep only last 100 logs
        logs = logs[-100:]
        agent.shared_state.set("message_logs", logs, namespace="monitoring")
    
    @agent.on_message("status")
    def handle_status(msg):
        """Respond to status requests"""
        if msg.payload.get("request") == "system_status":
            # Collect status from all agents
            all_agents = agent.discover_agents()
            agent.send_message(
                msg.sender,
                "status_response",
                {
                    "system_status": "healthy",
                    "active_agents": len(all_agents),
                    "agents": [{"id": a["agent_id"], "caps": a.get("capabilities", [])} for a in all_agents]
                }
            )
    
    print("🚀 Starting Monitor Agent...")
    agent.start()
    
    print("\n📊 Monitor is watching all agent communication")
    print("Press Ctrl+C to stop")
    
    # Periodically report stats
    try:
        while True:
            time.sleep(10)
            logs = agent.shared_state.get("message_logs", namespace="monitoring") or []
            print(f"\n📈 Stats: {len(logs)} messages logged in last period")
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping monitor...")
        agent.stop()
        print("✅ Monitor stopped")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python example_agent.py <role>")
        print("")
        print("Roles:")
        print("  compute      - Run the compute agent (calculations, searches)")
        print("  coordinator  - Run the coordinator agent (orchestration)")
        print("  monitor      - Run the monitor agent (logging, health checks)")
        print("")
        print("Run in different terminals:")
        print("  Terminal 1: python example_agent.py compute")
        print("  Terminal 2: python example_agent.py coordinator")
        print("  Terminal 3: python example_agent.py monitor")
        sys.exit(1)
    
    role = sys.argv[1]
    
    if role == "compute":
        run_compute_agent()
    elif role == "coordinator":
        run_coordinator_agent()
    elif role == "monitor":
        run_monitor_agent()
    else:
        print(f"Unknown role: {role}")
        sys.exit(1)
