#!/usr/bin/env python3

import agentops
import os
import time

os.environ['AGENTOPS_API_KEY'] = 'local-dev-api-key-placeholder'
os.environ['AGENTOPS_API_ENDPOINT'] = 'http://localhost:8000'
os.environ['AGENTOPS_APP_URL'] = 'http://localhost:3000'
os.environ['AGENTOPS_EXPORTER_ENDPOINT'] = 'http://localhost:4318/v1/traces'

def test_agentops_trace():
    """Test AgentOps trace generation without external dependencies"""
    try:
        print("🚀 Starting AgentOps trace test...")
        
        agentops.init(auto_start_session=True, trace_name="Simple Trace Test", tags=["local-test", "demo"])
        print("✓ AgentOps initialized successfully")
        
        tracer = agentops.start_trace(
            trace_name="Simple Trace Test", 
            tags=["simple-test", "agentops-demo"]
        )
        print("✓ Trace started successfully")
        
        print("📝 Simulating work...")
        time.sleep(1)
        
        print("📊 Adding custom events...")
        time.sleep(0.5)
        
        agentops.end_trace(tracer, end_state="Success")
        print("✓ Trace ended successfully")
        
        print("\n🎉 AgentOps trace test completed successfully!")
        print("🖇 Check the AgentOps output above for the session replay URL")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during trace test: {e}")
        return False

if __name__ == "__main__":
    success = test_agentops_trace()
    if success:
        print("\n✅ Simple trace test passed!")
    else:
        print("\n❌ Simple trace test failed!")
