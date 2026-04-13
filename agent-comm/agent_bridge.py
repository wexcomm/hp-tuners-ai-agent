#!/usr/bin/env python3
"""
Agent Bridge - Inter-Agent Communication System
Allows multiple AI agents to communicate via messages, RPC, and shared state
"""

import json
import os
import time
import uuid
import threading
import socket
import select
from pathlib import Path
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import queue

# Configuration
COMM_BASE_DIR = Path("/tmp/agent_comm") if os.name != 'nt' else Path(os.environ.get('TEMP', 'C:/temp')) / "agent_comm"
DEFAULT_PORT_RANGE = (9000, 9100)  # Port range for agent discovery

@dataclass
class AgentMessage:
    """Standard message format for inter-agent communication"""
    id: str
    sender: str
    recipient: str  # "broadcast" or specific agent_id
    message_type: str  # "ping", "rpc_request", "rpc_response", "event", "command", "status"
    payload: Dict[str, Any]
    timestamp: str
    ttl: int = 300  # Time to live in seconds
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def create(cls, sender: str, recipient: str, msg_type: str, payload: Dict, 
               ttl: int = 300) -> 'AgentMessage':
        return cls(
            id=str(uuid.uuid4()),
            sender=sender,
            recipient=recipient,
            message_type=msg_type,
            payload=payload,
            timestamp=datetime.now().isoformat(),
            ttl=ttl
        )

class AgentRegistry:
    """Register and discover agents in the system"""
    
    def __init__(self, base_dir: Path = COMM_BASE_DIR):
        self.base_dir = base_dir / "registry"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
    
    def register(self, agent_id: str, agent_info: Dict) -> bool:
        """Register an agent with the system"""
        with self._lock:
            agent_file = self.base_dir / f"{agent_id}.json"
            agent_info.update({
                "agent_id": agent_id,
                "registered_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "status": "active"
            })
            agent_file.write_text(json.dumps(agent_info, indent=2))
            return True
    
    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent"""
        agent_file = self.base_dir / f"{agent_id}.json"
        if agent_file.exists():
            agent_file.unlink()
            return True
        return False
    
    def heartbeat(self, agent_id: str) -> bool:
        """Update last seen timestamp"""
        agent_file = self.base_dir / f"{agent_id}.json"
        if agent_file.exists():
            data = json.loads(agent_file.read_text())
            data["last_seen"] = datetime.now().isoformat()
            data["status"] = "active"
            agent_file.write_text(json.dumps(data, indent=2))
            return True
        return False
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get info about a specific agent"""
        agent_file = self.base_dir / f"{agent_id}.json"
        if agent_file.exists():
            return json.loads(agent_file.read_text())
        return None
    
    def list_agents(self, active_only: bool = True) -> List[Dict]:
        """List all registered agents"""
        agents = []
        for agent_file in self.base_dir.glob("*.json"):
            try:
                data = json.loads(agent_file.read_text())
                if active_only:
                    # Check if agent has been seen in last 60 seconds
                    last_seen = datetime.fromisoformat(data.get("last_seen", "2000-01-01"))
                    if (datetime.now() - last_seen).total_seconds() < 60:
                        agents.append(data)
                else:
                    agents.append(data)
            except Exception:
                pass
        return agents
    
    def find_by_capability(self, capability: str) -> List[Dict]:
        """Find agents with specific capabilities"""
        matching = []
        for agent in self.list_agents():
            capabilities = agent.get("capabilities", [])
            if capability in capabilities:
                matching.append(agent)
        return matching

class FileBasedMessageBus:
    """File-based message bus for agent communication"""
    
    def __init__(self, agent_id: str, base_dir: Path = COMM_BASE_DIR):
        self.agent_id = agent_id
        self.base_dir = base_dir / "messages"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.inbox_dir = self.base_dir / agent_id
        self.inbox_dir.mkdir(exist_ok=True)
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._listener_thread = None
        self._lock = threading.Lock()
    
    def send(self, recipient: str, msg_type: str, payload: Dict, 
             ttl: int = 300) -> str:
        """Send a message to another agent or broadcast"""
        msg = AgentMessage.create(
            sender=self.agent_id,
            recipient=recipient,
            msg_type=msg_type,
            payload=payload,
            ttl=ttl
        )
        
        if recipient == "broadcast":
            # Send to all agents
            registry = AgentRegistry(self.base_dir.parent)
            for agent in registry.list_agents():
                if agent["agent_id"] != self.agent_id:
                    self._deliver_to_agent(agent["agent_id"], msg)
        else:
            # Send to specific agent
            self._deliver_to_agent(recipient, msg)
        
        return msg.id
    
    def _deliver_to_agent(self, agent_id: str, msg: AgentMessage):
        """Deliver message to specific agent's inbox"""
        inbox = self.base_dir / agent_id
        inbox.mkdir(exist_ok=True)
        msg_file = inbox / f"{msg.id}.json"
        msg_file.write_text(json.dumps(msg.to_dict(), indent=2))
    
    def subscribe(self, msg_type: str, handler: Callable):
        """Subscribe to a specific message type"""
        with self._lock:
            if msg_type not in self._handlers:
                self._handlers[msg_type] = []
            self._handlers[msg_type].append(handler)
    
    def start_listener(self, poll_interval: float = 1.0):
        """Start listening for messages"""
        self._running = True
        self._listener_thread = threading.Thread(
            target=self._listen_loop,
            args=(poll_interval,),
            daemon=True
        )
        self._listener_thread.start()
    
    def stop_listener(self):
        """Stop the listener"""
        self._running = False
        if self._listener_thread:
            self._listener_thread.join(timeout=5)
    
    def _listen_loop(self, poll_interval: float):
        """Main listening loop"""
        processed = set()
        
        while self._running:
            try:
                # Check for new messages
                for msg_file in self.inbox_dir.glob("*.json"):
                    if msg_file.name in processed:
                        continue
                    
                    try:
                        data = json.loads(msg_file.read_text())
                        msg = AgentMessage(**data)
                        
                        # Check TTL
                        msg_time = datetime.fromisoformat(msg.timestamp)
                        if (datetime.now() - msg_time).total_seconds() > msg.ttl:
                            msg_file.unlink()  # Expired, delete
                            continue
                        
                        # Process message
                        self._handle_message(msg)
                        processed.add(msg_file.name)
                        
                        # Optionally delete processed message
                        msg_file.unlink()
                        
                    except Exception as e:
                        print(f"Error processing message {msg_file}: {e}")
                
                time.sleep(poll_interval)
                
            except Exception as e:
                print(f"Error in listen loop: {e}")
                time.sleep(poll_interval)
    
    def _handle_message(self, msg: AgentMessage):
        """Handle received message"""
        with self._lock:
            handlers = self._handlers.get(msg.message_type, [])
            # Also check for wildcard handlers
            handlers.extend(self._handlers.get("*", []))
        
        for handler in handlers:
            try:
                handler(msg)
            except Exception as e:
                print(f"Error in message handler: {e}")
    
    def get_pending_messages(self) -> List[AgentMessage]:
        """Get all pending messages (manual check if not using listener)"""
        messages = []
        for msg_file in self.inbox_dir.glob("*.json"):
            try:
                data = json.loads(msg_file.read_text())
                messages.append(AgentMessage(**data))
            except Exception:
                pass
        return messages

class AgentRPC:
    """RPC system for agent-to-agent function calls"""
    
    def __init__(self, agent_id: str, message_bus: FileBasedMessageBus):
        self.agent_id = agent_id
        self.bus = message_bus
        self._pending_calls: Dict[str, queue.Queue] = {}
        self._methods: Dict[str, Callable] = {}
        
        # Subscribe to RPC responses
        self.bus.subscribe("rpc_response", self._handle_response)
        self.bus.subscribe("rpc_request", self._handle_request)
    
    def register_method(self, name: str, func: Callable):
        """Register a method that can be called by other agents"""
        self._methods[name] = func
    
    def call(self, target_agent: str, method: str, params: Dict, 
             timeout: float = 30.0) -> Any:
        """Call a method on another agent"""
        call_id = str(uuid.uuid4())
        
        # Create response queue
        response_queue = queue.Queue()
        self._pending_calls[call_id] = response_queue
        
        # Send RPC request
        self.bus.send(
            recipient=target_agent,
            msg_type="rpc_request",
            payload={
                "call_id": call_id,
                "method": method,
                "params": params,
                "return_to": self.agent_id
            },
            ttl=int(timeout) + 10
        )
        
        # Wait for response
        try:
            response = response_queue.get(timeout=timeout)
            del self._pending_calls[call_id]
            
            if response.get("error"):
                raise Exception(response["error"])
            return response.get("result")
            
        except queue.Empty:
            del self._pending_calls[call_id]
            raise TimeoutError(f"RPC call to {target_agent}.{method} timed out")
    
    def _handle_request(self, msg: AgentMessage):
        """Handle incoming RPC request"""
        payload = msg.payload
        call_id = payload.get("call_id")
        method = payload.get("method")
        params = payload.get("params", {})
        return_to = payload.get("return_to")
        
        result = None
        error = None
        
        try:
            if method in self._methods:
                result = self._methods[method](**params)
            else:
                error = f"Method '{method}' not found"
        except Exception as e:
            error = str(e)
        
        # Send response
        self.bus.send(
            recipient=return_to,
            msg_type="rpc_response",
            payload={
                "call_id": call_id,
                "result": result,
                "error": error
            },
            ttl=60
        )
    
    def _handle_response(self, msg: AgentMessage):
        """Handle RPC response"""
        payload = msg.payload
        call_id = payload.get("call_id")
        
        if call_id in self._pending_calls:
            self._pending_calls[call_id].put(payload)

class SharedState:
    """Shared state/knowledge store between agents"""
    
    def __init__(self, base_dir: Path = COMM_BASE_DIR):
        self.base_dir = base_dir / "shared_state"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
    
    def set(self, key: str, value: Any, namespace: str = "global"):
        """Set a value in shared state"""
        with self._lock:
            ns_dir = self.base_dir / namespace
            ns_dir.mkdir(exist_ok=True)
            
            key_file = ns_dir / f"{key}.json"
            data = {
                "key": key,
                "value": value,
                "updated_at": datetime.now().isoformat(),
                "version": 1
            }
            
            # Increment version if exists
            if key_file.exists():
                try:
                    old_data = json.loads(key_file.read_text())
                    data["version"] = old_data.get("version", 0) + 1
                except:
                    pass
            
            key_file.write_text(json.dumps(data, indent=2))
    
    def get(self, key: str, namespace: str = "global") -> Optional[Any]:
        """Get a value from shared state"""
        key_file = self.base_dir / namespace / f"{key}.json"
        if key_file.exists():
            try:
                data = json.loads(key_file.read_text())
                return data.get("value")
            except:
                pass
        return None
    
    def delete(self, key: str, namespace: str = "global") -> bool:
        """Delete a key from shared state"""
        key_file = self.base_dir / namespace / f"{key}.json"
        if key_file.exists():
            key_file.unlink()
            return True
        return False
    
    def list_keys(self, namespace: str = "global") -> List[str]:
        """List all keys in a namespace"""
        ns_dir = self.base_dir / namespace
        if not ns_dir.exists():
            return []
        return [f.stem for f in ns_dir.glob("*.json")]
    
    def subscribe(self, key: str, callback: Callable, namespace: str = "global") -> threading.Thread:
        """Subscribe to changes on a key (simple polling-based)"""
        def watcher():
            last_version = None
            key_file = self.base_dir / namespace / f"{key}.json"
            
            while True:
                try:
                    if key_file.exists():
                        data = json.loads(key_file.read_text())
                        current_version = data.get("version")
                        
                        if current_version != last_version:
                            last_version = current_version
                            callback(data.get("value"))
                    
                    time.sleep(1)
                except Exception:
                    time.sleep(1)
        
        thread = threading.Thread(target=watcher, daemon=True)
        thread.start()
        return thread

class Agent:
    """Main agent class that coordinates communication"""
    
    def __init__(self, agent_id: str, capabilities: List[str] = None, 
                 metadata: Dict = None):
        self.agent_id = agent_id
        self.capabilities = capabilities or []
        self.metadata = metadata or {}
        
        # Initialize components
        self.registry = AgentRegistry()
        self.message_bus = FileBasedMessageBus(agent_id)
        self.rpc = AgentRPC(agent_id, self.message_bus)
        self.shared_state = SharedState()
        
        self._running = False
        self._heartbeat_thread = None
        
        # Default message handlers
        self.message_bus.subscribe("ping", self._handle_ping)
        self.message_bus.subscribe("command", self._handle_command)
        self.message_bus.subscribe("status", self._handle_status_request)
    
    def start(self, heartbeat_interval: float = 30.0):
        """Start the agent and begin communication"""
        # Register with system
        self.registry.register(self.agent_id, {
            "capabilities": self.capabilities,
            "metadata": self.metadata,
            "started_at": datetime.now().isoformat()
        })
        
        # Start message listener
        self.message_bus.start_listener()
        
        # Start heartbeat
        self._running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(heartbeat_interval,),
            daemon=True
        )
        self._heartbeat_thread.start()
        
        print(f"✅ Agent '{self.agent_id}' started and registered")
    
    def stop(self):
        """Stop the agent"""
        self._running = False
        self.message_bus.stop_listener()
        
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        
        self.registry.unregister(self.agent_id)
        print(f"✅ Agent '{self.agent_id}' stopped")
    
    def _heartbeat_loop(self, interval: float):
        """Send periodic heartbeats"""
        while self._running:
            self.registry.heartbeat(self.agent_id)
            time.sleep(interval)
    
    def send_message(self, recipient: str, msg_type: str, payload: Dict, **kwargs):
        """Send a message to another agent"""
        return self.message_bus.send(recipient, msg_type, payload, **kwargs)
    
    def broadcast(self, msg_type: str, payload: Dict, **kwargs):
        """Broadcast a message to all agents"""
        return self.message_bus.send("broadcast", msg_type, payload, **kwargs)
    
    def call_agent(self, agent_id: str, method: str, params: Dict, timeout: float = 30.0):
        """Call a method on another agent via RPC"""
        return self.rpc.call(agent_id, method, params, timeout)
    
    def register_rpc_method(self, name: str, func: Callable):
        """Register an RPC method"""
        self.rpc.register_method(name, func)
    
    def on_message(self, msg_type: str):
        """Decorator to register message handlers"""
        def decorator(func: Callable):
            self.message_bus.subscribe(msg_type, func)
            return func
        return decorator
    
    def discover_agents(self, capability: str = None) -> List[Dict]:
        """Discover other agents in the system"""
        if capability:
            return self.registry.find_by_capability(capability)
        return self.registry.list_agents()
    
    def _handle_ping(self, msg: AgentMessage):
        """Default ping handler - respond with pong"""
        if msg.payload.get("expect_response", False):
            self.send_message(
                recipient=msg.sender,
                msg_type="pong",
                payload={
                    "in_response_to": msg.id,
                    "agent_id": self.agent_id,
                    "timestamp": datetime.now().isoformat()
                }
            )
    
    def _handle_command(self, msg: AgentMessage):
        """Default command handler"""
        command = msg.payload.get("command")
        print(f"Received command from {msg.sender}: {command}")
    
    def _handle_status_request(self, msg: AgentMessage):
        """Handle status requests"""
        if msg.payload.get("request") == "status":
            self.send_message(
                recipient=msg.sender,
                msg_type="status_response",
                payload={
                    "agent_id": self.agent_id,
                    "status": "active",
                    "capabilities": self.capabilities,
                    "uptime": "running"  # Could track actual uptime
                }
            )

# CLI for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python agent_bridge.py <command> [args]")
        print("")
        print("Commands:")
        print("  register <agent_id> [capabilities...]  - Register a new agent")
        print("  list                                     - List all active agents")
        print("  send <from> <to> <type> <json_payload>   - Send a message")
        print("  rpc <from> <to> <method> <json_params>   - Make RPC call")
        print("  share <key> <value>                      - Set shared state")
        print("  get <key>                                - Get shared state")
        print("  test                                     - Run test communication")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "register":
        agent_id = sys.argv[2]
        caps = sys.argv[3:] if len(sys.argv) > 3 else []
        agent = Agent(agent_id, capabilities=caps)
        agent.start()
        print(f"Agent {agent_id} registered. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            agent.stop()
    
    elif command == "list":
        registry = AgentRegistry()
        agents = registry.list_agents()
        print(f"Active agents ({len(agents)}):")
        for agent in agents:
            print(f"  - {agent['agent_id']}: {', '.join(agent.get('capabilities', []))}")
    
    elif command == "send":
        sender = sys.argv[2]
        recipient = sys.argv[3]
        msg_type = sys.argv[4]
        payload = json.loads(sys.argv[5])
        
        agent = Agent(sender)
        agent.start()
        msg_id = agent.send_message(recipient, msg_type, payload)
        print(f"Message sent: {msg_id}")
        time.sleep(2)  # Give time for delivery
        agent.stop()
    
    elif command == "test":
        print("Running agent communication test...")
        
        # Create two agents
        agent1 = Agent("agent_alpha", capabilities=["compute", "search"])
        agent2 = Agent("agent_beta", capabilities=["storage", "cache"])
        
        # Register handlers
        @agent2.on_message("greeting")
        def handle_greeting(msg):
            print(f"Agent Beta received greeting: {msg.payload}")
            agent2.send_message(
                msg.sender,
                "response",
                {"message": f"Hello {msg.sender}, I'm Beta!"}
            )
        
        # Start agents
        agent1.start()
        agent2.start()
        
        # Test message
        time.sleep(1)
        print("\n📨 Sending greeting from Agent Alpha to Agent Beta...")
        agent1.send_message("agent_beta", "greeting", {"text": "Hi Beta!"})
        
        time.sleep(2)
        print("\n📋 Checking Agent Beta's messages...")
        for msg in agent2.message_bus.get_pending_messages():
            print(f"  - {msg.message_type} from {msg.sender}: {msg.payload}")
        
        # Test shared state
        print("\n💾 Testing shared state...")
        agent1.shared_state.set("test_key", {"data": "Hello from Alpha"})
        value = agent2.shared_state.get("test_key")
        print(f"  Agent Beta read: {value}")
        
        # Test RPC
        print("\n🔗 Testing RPC...")
        agent2.register_rpc_method("echo", lambda message: f"Echo: {message}")
        
        time.sleep(1)
        try:
            result = agent1.call_agent("agent_beta", "echo", {"message": "Testing RPC"})
            print(f"  RPC result: {result}")
        except Exception as e:
            print(f"  RPC error: {e}")
        
        # Stop agents
        time.sleep(1)
        agent1.stop()
        agent2.stop()
        
        print("\n✅ Test completed!")
