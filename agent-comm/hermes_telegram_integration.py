#!/usr/bin/env python3
"""
Hermes Telegram Bot Integration for HP Tuners AI Agent

Allows the Hermes AI bot to communicate with the HP Tuners agent
via the agent communication system. Run tuning operations, check status,
and get diagnostics through Telegram commands.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json
import time

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "hpt_converter"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_bridge import Agent, SharedState


class HermesHPIntegration:
    """
    Integration layer between Hermes Telegram Bot and HP Tuners Agent
    
    Usage in your Hermes bot:
        from agent_comm.hermes_telegram_integration import HermesHPIntegration
        
        hp_integration = HermesHPIntegration()
        
        # Add to your bot's command handlers
        @bot.command("/hpt_status")
        async def hpt_status(event):
            return await hp_integration.handle_status(event)
    """
    
    def __init__(self, agent_id: str = "hermes_hp_bridge"):
        """
        Initialize the integration
        
        Args:
            agent_id: Unique ID for this bridge agent
        """
        self.agent_id = agent_id
        self.hp_agent_id = "hp_tuners_ai_agent_agent"
        self.agent: Optional[Agent] = None
        self._connected = False
        
    def connect(self) -> bool:
        """
        Connect to the agent communication system
        
        Returns:
            True if connected successfully
        """
        try:
            self.agent = Agent(
                agent_id=self.agent_id,
                capabilities=["hermes_bridge", "telegram", "tuning"],
                metadata={
                    "bridge": "hermes_telegram",
                    "target": "hp_tuners",
                    "version": "1.0"
                }
            )
            self.agent.start()
            self._connected = True
            
            # Check if HP agent is online
            agents = self.agent.discover_agents()
            hp_agents = [a for a in agents if "hp_tuners" in a.get("agent_id", "")]
            
            if hp_agents:
                self.hp_agent_id = hp_agents[0]["agent_id"]
                return True
            else:
                # HP agent not running, but we can still queue messages
                return True
                
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from agent system"""
        if self.agent:
            self.agent.stop()
            self._connected = False
    
    def _ensure_connected(self) -> bool:
        """Ensure connection is active"""
        if not self._connected:
            return self.connect()
        return True
    
    def _call_hp_agent(self, method: str, params: Dict = None, timeout: float = 10.0) -> Dict:
        """
        Call a method on the HP Tuners agent
        
        Args:
            method: RPC method name
            params: Method parameters
            timeout: Call timeout
            
        Returns:
            Result dict
        """
        if not self._ensure_connected():
            return {"error": "Not connected to agent system"}
        
        params = params or {}
        
        try:
            # Try RPC call first
            result = self.agent.call_agent(
                self.hp_agent_id,
                method,
                params,
                timeout=timeout
            )
            return result if isinstance(result, dict) else {"result": result}
            
        except Exception as e:
            # Fallback to message-based
            msg_id = self.agent.send_message(
                recipient=self.hp_agent_id,
                msg_type="command",
                payload={"command": method, "params": params},
                ttl=int(timeout)
            )
            
            # Wait for response (simplified - in production use async)
            time.sleep(1)
            messages = self.agent.message_bus.get_pending_messages()
            
            for msg in messages:
                if msg.message_type == "command_response":
                    if msg.payload.get("command") == method:
                        return msg.payload.get("result", {"error": "No result"})
            
            return {"error": f"RPC failed: {str(e)}. Message queued."}
    
    # ============== Command Handlers ==============
    
    async def handle_status(self, event) -> str:
        """
        Handle /hpt_status command
        
        Returns agent and vehicle status
        """
        if not self._ensure_connected():
            return "❌ Not connected to HP Tuners agent"
        
        try:
            # Get HP agent status
            result = self._call_hp_agent("get_status", {}, timeout=5.0)
            
            if "error" in result:
                return f"⚠️ Status check failed: {result['error']}"
            
            # Format response
            lines = [
                "🚗 **HP Tuners Agent Status**",
                "",
                f"**Vehicle:** {result.get('vehicle', 'Unknown')}",
                f"**Platform:** {result.get('platform', 'Unknown')}",
                f"**Device:** {result.get('device', 'Not detected')}",
                f"**Status:** {'🟢 Online' if result.get('running') else '🔴 Offline'}",
                f"**Capabilities:** {', '.join(result.get('capabilities', [])[:5])}",
            ]
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f"❌ Error getting status: {str(e)}"
    
    async def handle_tune(self, event, rev_limit: int = 7000, fuel: str = "premium") -> str:
        """
        Handle /hpt_tune command
        
        Generate a Stage 1 tune
        
        Args:
            event: Telegram event
            rev_limit: Target rev limit (default 7000)
            fuel: Fuel grade (premium/91/93)
        """
        if not self._ensure_connected():
            return "❌ Not connected to HP Tuners agent"
        
        try:
            # Call tune_vehicle RPC
            result = self._call_hp_agent(
                "tune_vehicle",
                {"rev_limit": rev_limit, "fuel_grade": fuel},
                timeout=15.0
            )
            
            if "error" in result:
                return f"⚠️ Tuning failed: {result['error']}"
            
            if not result.get("success"):
                return f"⚠️ Tuning unsuccessful"
            
            # Format tune results
            mods = result.get("modifications", {})
            
            lines = [
                "🎛️ **Stage 1 Tune Generated**",
                "",
                f"**File:** `{result.get('tune_file')}`",
                f"**Rev Limit:** {mods.get('rev_limit', 'N/A')} RPM",
                f"**Speed Limiter:** {mods.get('speed_limit', 'N/A')}",
                f"**Fuel:** {mods.get('fuel_adjustments', 'N/A')}",
                f"**Spark:** {mods.get('spark_advance', 'N/A')}",
                "",
                f"**Validation:** {'✅ Passed' if result.get('validation', {}).get('safe_to_flash') else '❌ Failed'}",
                f"**Ready to Flash:** {'✅ Yes' if result.get('ready_to_flash') else '❌ No'}",
                "",
                "**Notes:**",
            ]
            
            for note in result.get("notes", []):
                lines.append(f"• {note}")
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f"❌ Error generating tune: {str(e)}"
    
    async def handle_diagnostics(self, event) -> str:
        """
        Handle /hpt_diagnostics command
        
        Run diagnostic scan
        """
        if not self._ensure_connected():
            return "❌ Not connected to HP Tuners agent"
        
        try:
            result = self._call_hp_agent("scan_vehicle", {}, timeout=10.0)
            
            if "error" in result:
                return f"⚠️ Diagnostics failed: {result['error']}"
            
            # Format diagnostics
            dtc_codes = result.get("dtc_codes", [])
            live_data = result.get("live_data", {})
            
            lines = [
                "🔍 **Vehicle Diagnostics**",
                "",
                f"**Status:** {result.get('status', 'Unknown')}",
                f"**ECU:** {result.get('ecu_id', 'Unknown')}",
                "",
            ]
            
            # DTC Codes
            if dtc_codes:
                lines.append("**DTC Codes:**")
                for code in dtc_codes:
                    lines.append(f"• ⚠️ {code}")
            else:
                lines.append("**DTC Codes:** ✅ No codes found")
            
            lines.append("")
            
            # Live Data
            if live_data:
                lines.append("**Live Data:**")
                lines.append(f"• RPM: {live_data.get('rpm', 'N/A')}")
                lines.append(f"• Coolant: {live_data.get('coolant_temp_f', 'N/A')}°F")
                lines.append(f"• MAF: {live_data.get('maf_gps', 'N/A')} g/s")
                lines.append(f"• TPS: {live_data.get('tps_percent', 'N/A')}%")
                lines.append(f"• O2 Voltage: {live_data.get('o2_voltage', 'N/A')}V")
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f"❌ Error running diagnostics: {str(e)}"
    
    async def handle_flash(self, event, tune_file: str = None) -> str:
        """
        Handle /hpt_flash command
        
        Flash a tune to the ECU
        
        ⚠️ This is a dangerous operation! Should require confirmation.
        """
        if not self._ensure_connected():
            return "❌ Not connected to HP Tuners agent"
        
        if not tune_file:
            return "❌ Please specify a tune file: `/hpt_flash <filename>`"
        
        try:
            # First validate the file
            validate_result = self._call_hp_agent(
                "validate_file",
                {"file_path": tune_file},
                timeout=5.0
            )
            
            if not validate_result.get("safe_to_flash"):
                return f"❌ **Cannot flash - validation failed!**\n\nErrors: {validate_result.get('errors', 'Unknown')}"
            
            # Flash the tune
            flash_result = self._call_hp_agent(
                "flash_tune",
                {"tune_file": tune_file, "verify": True},
                timeout=60.0  # Flashing takes time
            )
            
            if "error" in flash_result:
                return f"❌ Flash failed: {flash_result['error']}"
            
            if flash_result.get("success"):
                lines = [
                    "✅ **Flash Complete!**",
                    "",
                    f"**File:** `{tune_file}`",
                    f"**ECU:** {flash_result.get('ecu_id', 'Unknown')}",
                    f"**Verified:** {'✅ Yes' if flash_result.get('verified') else '❌ No'}",
                    f"**Time:** {flash_result.get('flash_time_seconds', 'N/A')}s",
                    "",
                    "⚠️ **Post-Flash Notes:**",
                    "• Turn ignition off for 10 seconds",
                    "• Restart engine and check for codes",
                    "• Monitor knock sensors on first drive",
                ]
                return '\n'.join(lines)
            else:
                return "❌ Flash operation reported failure"
                
        except Exception as e:
            return f"❌ Error flashing: {str(e)}"
    
    async def handle_log(self, event, lines: int = 50) -> str:
        """
        Handle /hpt_log command
        
        Retrieve recent operation logs
        """
        # This would read from shared state or log files
        return "📋 **Recent Operations**\n\n(Feature coming soon - logs stored in shared state)"
    
    async def handle_vin(self, event) -> str:
        """
        Handle /hpt_vin command
        
        Read vehicle VIN
        """
        if not self._ensure_connected():
            return "❌ Not connected to HP Tuners agent"
        
        try:
            result = self._call_hp_agent("execute", {"command": "read_vin"}, timeout=5.0)
            
            if "error" in result:
                return f"⚠️ VIN read failed: {result['error']}"
            
            lines = [
                "🆔 **Vehicle Information**",
                "",
                f"**VIN:** `{result.get('vin', 'Unknown')}`",
                f"**Year:** {result.get('year', 'Unknown')}",
                f"**Make:** {result.get('make', 'Unknown')}",
                f"**Model:** {result.get('model', 'Unknown')}",
                f"**Engine:** {result.get('engine', 'Unknown')}",
                f"**Platform:** {result.get('platform', 'Unknown')}",
            ]
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f"❌ Error reading VIN: {str(e)}"
    
    async def handle_device(self, event) -> str:
        """
        Handle /hpt_device command
        
        Check J2534 device status
        """
        if not self._ensure_connected():
            return "❌ Not connected to HP Tuners agent"
        
        try:
            result = self._call_hp_agent("execute", {"command": "device_detect"}, timeout=5.0)
            
            if "error" in result:
                return f"⚠️ Device detection failed: {result['error']}"
            
            detected = result.get("detected", False)
            
            lines = [
                "🔌 **J2534 Device Status**",
                "",
                f"**Detected:** {'✅ Yes' if detected else '❌ No'}",
            ]
            
            if detected:
                lines.extend([
                    f"**Device:** {result.get('device', 'Unknown')}",
                    f"**DLL:** `{result.get('dll_path', 'Unknown')}`",
                    f"**CAN Baud:** {result.get('can_baud', 'Unknown')}",
                    "",
                    "**Protocols:**",
                ])
                for protocol in result.get("protocols", []):
                    lines.append(f"• {protocol}")
            else:
                lines.extend([
                    "",
                    "**Troubleshooting:**",
                    "• Check USB connection",
                    "• Ensure TOPDON software installed",
                    "• Try reinstalling drivers",
                ])
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f"❌ Error detecting device: {str(e)}"


# ============== Helper Functions ==============

def integrate_with_hermes_bot(hermes_bot_instance) -> HermesHPIntegration:
    """
    Create integration and register with Hermes bot
    
    Usage:
        from agent_comm.hermes_telegram_integration import integrate_with_hermes_bot
        
        integration = integrate_with_hermes_bot(hermes_bot)
        
        # Commands are automatically registered if bot supports it
        # Otherwise manually add:
        hermes_bot.add_command("/hpt_status", integration.handle_status)
    """
    integration = HermesHPIntegration()
    
    # Try to connect immediately
    if integration.connect():
        print("✅ HP Tuners integration connected")
    else:
        print("⚠️ HP Tuners agent not running - will queue messages")
    
    return integration


# ============== Example Usage ==============

if __name__ == "__main__":
    # Test the integration
    print("🧪 Testing HP Tuners Integration...")
    
    integration = HermesHPIntegration()
    
    if integration.connect():
        print("✅ Connected to agent system")
        
        # Test status
        import asyncio
        status = asyncio.run(integration.handle_status(None))
        print("\n" + status)
        
        # Test VIN
        vin = asyncio.run(integration.handle_vin(None))
        print("\n" + vin)
        
        # Test device
        device = asyncio.run(integration.handle_device(None))
        print("\n" + device)
        
        integration.disconnect()
        print("\n✅ Tests complete")
    else:
        print("❌ Could not connect - is HP agent running?")
        print("   Run: python3 hp_tuners_ai_agent_agent.py run")
