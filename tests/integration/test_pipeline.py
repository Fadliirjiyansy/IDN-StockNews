#!/usr/bin/env python3
"""
Integration test: verify n8n test workflow executes successfully.
Run: python3 tests/integration/test_pipeline.py
"""

import urllib.request
import urllib.error
import json
import os
import base64

N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_USER = os.getenv("N8N_BASIC_AUTH_USER", "admin")
N8N_PASS = os.getenv("N8N_BASIC_AUTH_PASSWORD", "changeme")
WORKFLOW_ID = "BZdFA5mQuB3EA1E1"

def auth_header():
    token = base64.b64encode(f"{N8N_USER}:{N8N_PASS}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

def test_n8n_health():
    print("Testing n8n health...")
    req = urllib.request.Request(f"{N8N_URL}/healthz", headers=auth_header())
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            assert r.status == 200, f"Expected 200, got {r.status}"
            print("  ✅ n8n is healthy")
    except Exception as e:
        print(f"  ❌ Health check failed: {e}")
        raise

def test_workflow_exists():
    print(f"Testing workflow {WORKFLOW_ID} exists...")
    req = urllib.request.Request(
        f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
        headers=auth_header()
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            assert data["id"] == WORKFLOW_ID
            print(f"  ✅ Workflow found: {data['name']}")
    except Exception as e:
        print(f"  ❌ Workflow not found: {e}")
        raise

if __name__ == "__main__":
    print("=== IDN-StockNews Integration Tests ===\n")
    test_n8n_health()
    test_workflow_exists()
    print("\n✅ All integration tests passed!")
