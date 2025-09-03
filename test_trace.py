#!/usr/bin/env python3

import agentops
import os

os.environ['AGENTOPS_API_KEY'] = '6b7a1469-bdcb-4d47-85ba-c4824bc8486e'
os.environ['AGENTOPS_API_ENDPOINT'] = 'http://localhost:8000'
os.environ['AGENTOPS_APP_URL'] = 'http://localhost:3000'
os.environ['AGENTOPS_EXPORTER_ENDPOINT'] = 'http://localhost:4318/v1/traces'

def test_trace_generation():
    """Test basic trace generation with local AgentOps setup"""
    try:
        print("Initializing AgentOps...")
        agentops.init()
        print("✓ AgentOps initialized successfully")
        
        print("Starting trace...")
        trace_context = agentops.start_trace('Test Trace - Local Setup')
        print(f"✓ Trace started: {trace_context}")
        
        print("Ending trace...")
        agentops.end_trace(trace_context, 'Success')
        print("✓ Trace ended successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during trace generation: {e}")
        return False

if __name__ == "__main__":
    success = test_trace_generation()
    if success:
        print("\n🎉 Trace generation test completed successfully!")
    else:
        print("\n❌ Trace generation test failed!")
