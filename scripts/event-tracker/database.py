#!/usr/bin/env python3
"""
PostgreSQL Database Handler for FinancialReportNews
Connects to database and manages market events storage
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# Simulated database handler for when Docker/PostgreSQL becomes available
class PostgreSQLHandler:
    def __init__(self, host: str = "postgres", port: int = 5432, 
                 database: str = "n8n", user: str = "n8n", password: str = "n8n_principal"):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        self.connected = False
        
    def connect(self) -> bool:
        try:
            # This will work when psycopg2 is available
            import psycopg2
            
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.connected = True
            print(f"[DATABASE] Connected to PostgreSQL at {self.host}:{self.port}")
            return True
            
        except ImportError:
            print("[WARNING] psycopg2 not installed. Running in simulation mode.")
            self.connected = False
            return False
        except Exception as e:
            print(f"[ERROR] Failed to connect: {e}")
            self.connected = False
            return False
    
    def insert_event(self, event: Dict[str, Any]) -> bool:
        if not self.connected:
            print("[SIMULATION] Would insert event:", event)
            return True
        
        try:
            cursor = self.connection.cursor()
            
            query = """
            INSERT INTO market_events 
            (title, event_type, ticker, source, announcement_date, url, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """
            
            values = (
                event.get('title'),
                event.get('event_type'),
                event.get('ticker'),
                event.get('source'),
                event.get('announcement_date'),
                event.get('url'),
                datetime.now()
            )
            
            cursor.execute(query, values)
            self.connection.commit()
            cursor.close()
            
            print(f"[DATABASE] Inserted: {event.get('title')[:40]}...")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to insert event: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def insert_batch(self, events: List[Dict[str, Any]]) -> int:
        inserted = 0
        for event in events:
            if self.insert_event(event):
                inserted += 1
        
        print(f"[DATABASE] Batch insert: {inserted}/{len(events)} events")
        return inserted
    
    def log_pipeline_run(self, run_data: Dict[str, Any]) -> bool:
        if not self.connected:
            print("[SIMULATION] Would log pipeline run:", run_data)
            return True
        
        try:
            cursor = self.connection.cursor()
            
            query = """
            INSERT INTO pipeline_runs 
            (total_collected, total_normalized, total_validated, 
             total_deduplicated, errors_count, warnings_count, 
             execution_time_ms, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                run_data.get('collected', 0),
                run_data.get('normalized', 0),
                run_data.get('validated', 0),
                run_data.get('deduplicated', 0),
                run_data.get('errors', 0),
                run_data.get('warnings', 0),
                run_data.get('execution_time_ms', 0),
                run_data.get('status', 'SUCCESS')
            )
            
            cursor.execute(query, values)
            self.connection.commit()
            cursor.close()
            
            print("[DATABASE] Pipeline run logged")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to log pipeline run: {e}")
            return False
    
    def get_event_count(self) -> int:
        if not self.connected:
            print("[SIMULATION] Would return event count")
            return 0
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM market_events")
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            print(f"[ERROR] Failed to count events: {e}")
            return 0
    
    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.connected:
            print(f"[SIMULATION] Would return {limit} recent events")
            return []
        
        try:
            cursor = self.connection.cursor()
            query = "SELECT * FROM market_events ORDER BY created_at DESC LIMIT %s"
            cursor.execute(query, (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            events = []
            for row in cursor.fetchall():
                events.append(dict(zip(columns, row)))
            
            cursor.close()
            return events
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch events: {e}")
            return []
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connected = False
            print("[DATABASE] Disconnected")


# Test function
def test_connection():
    print("[DATABASE HANDLER TEST]")
    print("-" * 60)
    
    # Get credentials from environment
    host = os.getenv("DB_HOST", "postgres")
    port = int(os.getenv("DB_PORT", 5432))
    database = os.getenv("DB_NAME", "n8n")
    user = os.getenv("DB_USER", "n8n")
    password = os.getenv("DB_PASSWORD", "n8n_principal")
    
    db = PostgreSQLHandler(host, port, database, user, password)
    
    # Try to connect
    if db.connect():
        print("[SUCCESS] Database connection established")
        
        # Test inserting sample event
        sample_event = {
            'title': 'Test Event',
            'event_type': 'IPO',
            'ticker': 'TEST',
            'source': 'IDX',
            'announcement_date': '2026-04-07',
            'url': 'https://example.com'
        }
        
        db.insert_event(sample_event)
        
        # Get count
        count = db.get_event_count()
        print(f"[INFO] Total events in database: {count}")
        
        # Get recent events
        recent = db.get_recent_events(5)
        print(f"[INFO] Recent events: {len(recent)}")
        
        db.disconnect()
    else:
        print("[INFO] Running in simulation mode (no psycopg2)")
        print("[INFO] Database operations will be simulated")


if __name__ == "__main__":
    test_connection()
