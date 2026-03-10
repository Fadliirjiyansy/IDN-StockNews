# Test Workflow Guide

## Workflow: Market Briefing - Test Workflow

**n8n ID:** `BZdFA5mQuB3EA1E1`  
**File:** `n8n/workflows/test-workflow.json`

## Purpose

Validates that your local n8n instance is correctly set up and the pipeline skeleton is working before connecting real data sources.

## Flow

```
Manual Trigger
     │
     ▼
Set Test Data  →  sets project="market-briefing", status="testing", timestamp=now
     │
     ▼
Check Status   →  IF status == "testing"
    / \
   ✅   ❌
```

## How to Run

1. Open n8n at `http://localhost:5678`
2. Find **Market Briefing - Test Workflow**
3. Click **Execute Workflow**
4. Check the output of the last node — should show `✅ Test passed!`

## Expected Output

```json
{
  "result": "✅ Test passed! Workflow is running correctly."
}
```
