#!/usr/bin/env python3
"""
LFX Tuning Copilot — Session Tracker
SQLite-based tracking of tuning sessions, changes, and results.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tuning_sessions.db")


def init_db():
    """Initialize the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            description TEXT,
            vehicle TEXT DEFAULT '2013 Chevy Impala LS LFX',
            baseline_log TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            made_at TEXT DEFAULT CURRENT_TIMESTAMP,
            table_name TEXT,
            vcm_path TEXT,
            parameter TEXT,
            old_value TEXT,
            new_value TEXT,
            reason TEXT,
            risk_level TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            logged_at TEXT DEFAULT CURRENT_TIMESTAMP,
            log_path TEXT,
            findings_json TEXT,
            suggestions_json TEXT,
            notes TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    ''')
    
    conn.commit()
    conn.close()


class SessionTracker:
    def __init__(self):
        init_db()
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
    
    def close(self):
        self.conn.close()
    
    def create_session(self, description: str = "", baseline_log: str = "") -> int:
        """Create a new tuning session. Returns session ID."""
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO sessions (description, baseline_log) VALUES (?, ?)",
            (description or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}", baseline_log)
        )
        self.conn.commit()
        return c.lastrowid
    
    def log_change(self, session_id: int, table_name: str, vcm_path: str,
                   parameter: str, old_value: str, new_value: str,
                   reason: str = "", risk_level: str = "low"):
        """Log a tuning change."""
        c = self.conn.cursor()
        c.execute(
            """INSERT INTO changes 
               (session_id, table_name, vcm_path, parameter, old_value, new_value, reason, risk_level)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, table_name, vcm_path, parameter, old_value, new_value, reason, risk_level)
        )
        self.conn.commit()
    
    def log_analysis(self, session_id: int, log_path: str,
                     findings: List[Dict], suggestions: List[Dict],
                     notes: str = ""):
        """Log analysis results."""
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO logs (session_id, log_path, findings_json, suggestions_json, notes) VALUES (?, ?, ?, ?, ?)",
            (session_id, log_path, json.dumps(findings), json.dumps(suggestions), notes)
        )
        self.conn.commit()
    
    def get_session_history(self, session_id: int) -> Dict:
        """Get full history of a tuning session."""
        c = self.conn.cursor()
        
        c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session = dict(c.fetchone() or {})
        
        c.execute("SELECT * FROM changes WHERE session_id = ? ORDER BY made_at", (session_id,))
        changes = [dict(row) for row in c.fetchall()]
        
        c.execute("SELECT * FROM logs WHERE session_id = ? ORDER BY logged_at", (session_id,))
        logs = [dict(row) for row in c.fetchall()]
        
        return {
            'session': session,
            'changes': changes,
            'logs': logs,
            'change_count': len(changes),
            'log_count': len(logs)
        }
    
    def list_sessions(self) -> List[Dict]:
        """List all tuning sessions."""
        c = self.conn.cursor()
        c.execute("SELECT * FROM sessions ORDER BY created_at DESC")
        return [dict(row) for row in c.fetchall()]
    
    def get_latest_session(self) -> Optional[int]:
        """Get the most recent session ID."""
        c = self.conn.cursor()
        c.execute("SELECT id FROM sessions ORDER BY created_at DESC LIMIT 1")
        row = c.fetchone()
        return row[0] if row else None


if __name__ == '__main__':
    # Quick test
    tracker = SessionTracker()
    sid = tracker.create_session("Test session", "baseline.csv")
    print(f"Created session: {sid}")
    tracker.log_change(sid, "Main Spark", "Engine → Spark → Main", "Spark Advance", "28", "26", "Knock at 4000 RPM", "low")
    history = tracker.get_session_history(sid)
    print(f"History: {history}")
    tracker.close()
