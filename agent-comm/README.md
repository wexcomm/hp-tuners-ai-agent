# 🤖 Agent Bridge - Inter-Agent Communication System

A lightweight system for multiple AI agents to communicate, share state, and call functions on each other - perfect for coordinating agents across VS Code terminals or different machines.

## 🚀 Quick Start

### Run Multiple Agents in VS Code Terminals

**Terminal 1 - Compute Agent:**
```bash
cd /root/hermes-ollama/agent-comm
python3 example_agent.py compute
```

**Terminal 2 - Coordinator Agent:**
```bash
cd /root/hermes-ollama/agent-comm
python3 example_agent.py coordinator
```

**Terminal 3 - Monitor Agent:**
```bash
cd /root/hermes-ollama/agent-comm
python3 example_agent.py monitor
```

Watch them discover each other and communicate! 🎉

---

## 📡 How It Works

### File-Based Communication

Agents communicate through a shared file system:

```
/tmp/agent_comm/
├── registry/          # Agent registration & discovery
│   ├── agent_alpha.json
│   ├── agent_beta.json
│   └── ...
├── messages/          # Message inboxes
│   ├── agent_alpha/
│   │   ├── msg_123.json
│   │   └── ...
│   └── agent_beta/
│       └── ...
└── shared_state/      # Shared key-value store
    └── global/
        └── key.json
```

**Why files?**
- ✅ No network configuration needed
- ✅ Works across different users/permissions
- ✅ Persistent messages (survive crashes)
- ✅ Easy to debug (just `cat` the files)
- ✅ Works in containerized environments

---

## 🛠️ Core Components

### 1. Agent Registry

Discover and register agents:

```python
from agent_bridge import Agent

# Create and start an agent
agent = Agent(
    agent_id="my_agent",
    capabilities=["compute", "storage"]
)
agent.start()

# Discover other agents
others = agent.discover_agents()
for a in others:
    print(f"Found: {a['agent_id']} with {a['capabilities']}")

# Find by capability
compute_agents = agent.discover_agents(capability="compute")
```

### 2. Message Bus

Send and receive messages:

```python
# Send to specific agent
agent.send_message(
    recipient="other_agent",
    msg_type="task_request",
    payload={"task": "process_data", "data": [1, 2, 3]}
)

# Broadcast to all agents
agent.broadcast(
    msg_type="announcement",
    payload={"message": "System going down for maintenance"}
)

# Handle incoming messages
@agent.on_message("task_request")
def handle_task(msg):
    print(f"Task from {msg.sender}: {msg.payload}")
    # Process task...
    agent.send_message(
        msg.sender,
        "task_complete",
        {"result": "success"}
    )
```

### 3. RPC System

Call functions on other agents:

```python
# Register RPC methods (in target agent)
@agent.register_rpc_method
def analyze(data: str) -> dict:
    return {"sentiment": "positive", "confidence": 0.95}

# Call from another agent
result = agent.call_agent(
    agent_id="analysis_agent",
    method="analyze",
    params={"data": "I love this product!"},
    timeout=10.0
)
print(result)  # {"sentiment": "positive", "confidence": 0.95}
```

### 4. Shared State

Share data between agents:

```python
# Agent A writes
agent.shared_state.set("config", {"debug": True, "version": "1.0"})

# Agent B reads
config = agent.shared_state.get("config")
print(config)  # {"debug": True, "version": "1.0"}

# Namespaced storage
agent.shared_state.set("api_keys", {...}, namespace="secrets")
keys = agent.shared_state.get("api_keys", namespace="secrets")

# List all keys
all_keys = agent.shared_state.list_keys()
```

---

## 💡 Use Cases

### Use Case 1: Distributed Task Processing

```python
# coordinator.py
agent = Agent("coordinator", ["orchestration"])
agent.start()

# Distribute tasks to workers
workers = agent.discover_agents(capability="compute")
for i, task in enumerate(tasks):
    worker = workers[i % len(workers)]
    agent.send_message(
        worker["agent_id"],
        "process_task",
        {"task_id": i, "data": task}
    )

# Collect results
@agent.on_message("task_complete")
def collect_result(msg):
    results[msg.payload["task_id"]] = msg.payload["result"]
```

### Use Case 2: Multi-Agent Research System

```python
# research_orchestrator.py
class ResearchSystem:
    def __init__(self):
        self.search_agent = Agent("searcher", ["web_search"])
        self.analysis_agent = Agent("analyzer", ["nlp", "summarize"])
        self.writer_agent = Agent("writer", ["content_gen"])
        
        # Register capabilities
        @self.search_agent.register_rpc_method
        def search(query: str) -> list:
            # Search the web
            return search_duckduckgo(query)
        
        @self.analysis_agent.register_rpc_method
        def analyze(urls: list) -> dict:
            # Analyze content
            return process_urls(urls)
        
        @self.writer_agent.register_rpc_method
        def write(data: dict) -> str:
            # Generate report
            return generate_report(data)
    
    def research(self, topic: str) -> str:
        # Step 1: Search
        urls = self.search_agent.call_agent(
            "searcher", "search", {"query": topic}
        )
        
        # Step 2: Analyze
        analysis = self.analysis_agent.call_agent(
            "analyzer", "analyze", {"urls": urls}
        )
        
        # Step 3: Write
        report = self.writer_agent.call_agent(
            "writer", "write", {"data": analysis}
        )
        
        return report
```

### Use Case 3: Load Balancing

```python
# Load balancer distributes requests to least busy agent
class LoadBalancer:
    def __init__(self):
        self.agent = Agent("load_balancer", ["routing"])
        self.agent.start()
        
        # Track agent load
        self.load = {}
    
    @self.agent.on_message("status_update")
    def update_load(msg):
        agent_id = msg.sender
        self.load[agent_id] = msg.payload["queue_depth"]
    
    def route_request(self, request):
        # Find agent with lowest load
        workers = self.agent.discover_agents(capability="worker")
        if not workers:
            raise Exception("No workers available")
        
        # Sort by load
        sorted_workers = sorted(
            workers,
            key=lambda w: self.load.get(w["agent_id"], 0)
        )
        
        target = sorted_workers[0]["agent_id"]
        return self.agent.call_agent(
            target, "process", {"request": request}
        )
```

### Use Case 4: Agent-to-Agent Learning

```python
# Knowledge sharing between agents
class LearningAgent:
    def __init__(self):
        self.agent = Agent("learner", ["ml"])
        
        @self.agent.on_message("training_data")
        def receive_training_data(msg):
            # Add to local training set
            self.training_data.append(msg.payload["data"])
            
        @self.agent.on_message("model_update")
        def update_model(msg):
            # Merge model weights
            self.merge_weights(msg.payload["weights"])
            
        # Periodically share learnings
        def share_learnings():
            while True:
                time.sleep(3600)  # Every hour
                other_learners = self.agent.discover_agents(capability="ml")
                for peer in other_learners:
                    if peer["agent_id"] != self.agent.agent_id:
                        self.agent.send_message(
                            peer["agent_id"],
                            "model_update",
                            {"weights": self.get_weights()}
                        )
```

---

## 🔧 CLI Usage

### Register an Agent
```bash
python3 agent_bridge.py register my_agent compute search storage
```

### List Active Agents
```bash
python3 agent_bridge.py list
```

### Send a Message
```bash
python3 agent_bridge.py send my_agent other_agent greeting '{"text": "Hello!"}'
```

### Test Communication
```bash
python3 agent_bridge.py test
```

---

## 🧪 Testing Communication

### Check if Agents Can Communicate

```bash
# Terminal 1: Start an agent
python3 -c "
from agent_bridge import Agent
import time

agent = Agent('test_agent', ['test'])
agent.start()

@agent.on_message('ping')
def handle_ping(msg):
    print(f'Received ping from {msg.sender}')
    agent.send_message(msg.sender, 'pong', {'received': True})

time.sleep(30)  # Run for 30 seconds
"
```

```bash
# Terminal 2: Send message
python3 -c "
from agent_bridge import Agent
import time

agent = Agent('sender', ['test'])
agent.start()

# Send ping
time.sleep(1)
agent.send_message('test_agent', 'ping', {'expect_response': True})

# Check for response
time.sleep(2)
for msg in agent.message_bus.get_pending_messages():
    print(f'Got {msg.message_type} from {msg.sender}: {msg.payload}')
"
```

---

## 🌐 Cross-Machine Communication

For agents on different machines, mount the shared directory via NFS or use a simple network bridge:

### Option 1: NFS Share
```bash
# On server (machine A)
mkdir -p /shared/agent_comm
exportfs -o rw,sync,no_root_squash *:/shared/agent_comm

# On client (machine B)
mount server:/shared/agent_comm /tmp/agent_comm
```

### Option 2: SSHFS
```bash
# Mount remote agent_comm directory
sshfs user@remote:/tmp/agent_comm /tmp/agent_comm
```

### Option 3: Network Bridge (Simple TCP)

Add a network bridge to `agent_bridge.py`:

```python
class NetworkBridge:
    """Bridge file-based messages over network"""
    
    def __init__(self, host: str, port: int = 9999):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def forward_messages(self, local_bus: FileBasedMessageBus):
        """Forward local messages to remote, and vice versa"""
        # Implementation to bridge file-based to network
        ...
```

---

## 📊 Monitoring & Debugging

### View Registry
```bash
ls -la /tmp/agent_comm/registry/
cat /tmp/agent_comm/registry/agent_alpha.json
```

### Watch Messages
```bash
# Real-time message watching
watch -n 1 'ls /tmp/agent_comm/messages/agent_alpha/'

# Read a message
cat /tmp/agent_comm/messages/agent_alpha/msg_*.json
```

### Check Shared State
```bash
ls -la /tmp/agent_comm/shared_state/global/
cat /tmp/agent_comm/shared_state/global/config.json
```

### Debug Log
```python
import logging
logging.basicConfig(level=logging.DEBUG)

from agent_bridge import Agent
agent = Agent("debug_agent", ["test"])
agent.start()
```

---

## 🚨 Troubleshooting

### Agents Can't See Each Other
```bash
# Check if registry directory exists
ls -la /tmp/agent_comm/registry/

# Check agent registration
cat /tmp/agent_comm/registry/*.json

# Manual heartbeat
python3 -c "
from agent_bridge import AgentRegistry
reg = AgentRegistry()
reg.heartbeat('your_agent_id')
"
```

### Messages Not Delivered
```bash
# Check message inbox exists
ls -la /tmp/agent_comm/messages/TARGET_AGENT/

# Check permissions
chmod 777 /tmp/agent_comm -R

# Verify message format
cat /tmp/agent_comm/messages/.../*.json | python3 -m json.tool
```

### RPC Timeout
- Check if target agent is running: `list` command
- Verify method is registered
- Increase timeout in `call_agent()`
- Check logs for errors

---

## 🎓 Advanced Patterns

### Agent Composition
```python
class CompositeAgent:
    """Agent composed of multiple specialized agents"""
    
    def __init__(self):
        self.nlp = Agent("nlp_subagent", ["nlp"])
        self.vision = Agent("vision_subagent", ["vision"])
        self.reasoning = Agent("reasoning_subagent", ["reasoning"])
        
        self.nlp.start()
        self.vision.start()
        self.reasoning.start()
    
    def process(self, data):
        # Parallel processing
        with ThreadPoolExecutor() as pool:
            nlp_future = pool.submit(self.nlp.call_agent, ...)
            vision_future = pool.submit(self.vision.call_agent, ...)
            
            nlp_result = nlp_future.result()
            vision_result = vision_future.result()
        
        # Reasoning combines results
        return self.reasoning.call_agent(...)
```

### Agent Swarms
```python
class AgentSwarm:
    """Dynamic swarm of agents for parallel processing"""
    
    def __init__(self, task_type: str, count: int = 5):
        self.agents = []
        for i in range(count):
            agent = Agent(f"swarm_{task_type}_{i}", [task_type])
            agent.start()
            self.agents.append(agent)
    
    def map_reduce(self, tasks: list) -> list:
        # Map: Send to all agents
        results = []
        for i, task in enumerate(tasks):
            agent = self.agents[i % len(self.agents)]
            result = agent.call_agent(agent.agent_id, "process", task)
            results.append(result)
        
        # Reduce: Aggregate
        return self.reduce(results)
```

---

## 🔒 Security Considerations

- **File permissions**: Ensure `/tmp/agent_comm` has appropriate permissions
- **Network exposure**: Don't expose agent ports directly to internet
- **Message validation**: Always validate message payloads
- **RPC authorization**: Consider adding auth tokens for sensitive methods
- **Sandboxing**: Run agents in separate containers for isolation

---

## 📚 API Reference

See `agent_bridge.py` docstrings for full API details.

Key classes:
- `Agent` - Main agent class
- `AgentRegistry` - Registration and discovery
- `FileBasedMessageBus` - Message passing
- `AgentRPC` - Remote procedure calls
- `SharedState` - Distributed key-value store

---

## 🚀 Next Steps

1. **Run the examples** in different terminals
2. **Create your own agents** with custom capabilities
3. **Build a multi-agent system** for your use case
4. **Add network bridging** for cross-machine agents
5. **Integrate with your existing code** using the Agent class

Happy agenting! 🤖🤖🤖
