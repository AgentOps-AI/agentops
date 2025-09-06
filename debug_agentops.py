#!/usr/bin/env python3
"""
AgentOps Debugging Script

This script helps diagnose issues with AgentOps session logging.
Run this script to check connectivity, authentication, and configuration.
"""

import os
import sys
import asyncio
import requests
from typing import Optional

def test_network_connectivity():
    """Test basic network connectivity to AgentOps endpoints."""
    print("🔍 Testing network connectivity...")
    
    endpoints = [
        ("API Health", "https://api.agentops.ai/health"),
        ("OTLP Health", "https://otlp.agentops.ai/health"),
        ("Dashboard", "https://app.agentops.ai"),
    ]
    
    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=10)
            status = "✅" if response.status_code == 200 else f"⚠️ ({response.status_code})"
            print(f"  {status} {name}: {url}")
        except requests.exceptions.RequestException as e:
            print(f"  ❌ {name}: {url} - {e}")

def test_api_key_format(api_key: str):
    """Test if the API key format is valid."""
    print(f"\n🔑 Testing API key format...")
    
    if not api_key:
        print("  ❌ No API key provided")
        return False
    
    # Check if it looks like a UUID
    import uuid
    try:
        uuid.UUID(api_key)
        print(f"  ✅ API key format appears valid: {api_key[:8]}...")
        return True
    except ValueError:
        print(f"  ⚠️ API key format may be invalid: {api_key[:8]}...")
        return False

def test_agentops_initialization(api_key: str):
    """Test AgentOps initialization and authentication."""
    print(f"\n🚀 Testing AgentOps initialization...")
    
    try:
        import agentops
        
        # Initialize with debug logging
        agentops.init(api_key=api_key, log_level="DEBUG")
        
        # Check authentication status
        auth_status = agentops.check_auth_status()
        
        print(f"  📊 Authentication Status:")
        for key, value in auth_status.items():
            status = "✅" if value else "❌"
            print(f"    {status} {key}: {value}")
        
        # Check if authenticated
        if agentops.is_authenticated():
            print("  ✅ AgentOps is properly authenticated")
            return True
        else:
            print("  ❌ AgentOps authentication failed")
            return False
            
    except Exception as e:
        print(f"  ❌ AgentOps initialization failed: {e}")
        return False

def test_session_creation(api_key: str):
    """Test creating a session and logging it."""
    print(f"\n📝 Testing session creation...")
    
    try:
        import agentops
        
        # Initialize
        agentops.init(api_key=api_key, log_level="DEBUG")
        
        # Start a test session
        with agentops.start_trace("debug_test_session") as trace:
            print("  ✅ Session created successfully")
            print(f"  📋 Trace ID: {trace.span.context.trace_id}")
            
            # Add some test data
            trace.span.set_attribute("test.attribute", "debug_value")
            
        print("  ✅ Session ended successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Session creation failed: {e}")
        return False

def check_environment():
    """Check environment variables and configuration."""
    print(f"\n🌍 Checking environment...")
    
    env_vars = [
        "AGENTOPS_API_KEY",
        "AGENTOPS_LOG_LEVEL", 
        "AGENTOPS_API_ENDPOINT",
        "AGENTOPS_APP_URL",
        "AGENTOPS_EXPORTER_ENDPOINT",
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "API_KEY" in var:
                display_value = f"{value[:8]}..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ⚠️ {var}: Not set")

def main():
    """Main debugging function."""
    print("🔧 AgentOps Debugging Tool")
    print("=" * 50)
    
    # Get API key
    api_key = os.getenv("AGENTOPS_API_KEY")
    if not api_key:
        print("❌ AGENTOPS_API_KEY environment variable not set")
        print("Please set your API key: export AGENTOPS_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Run tests
    check_environment()
    test_network_connectivity()
    test_api_key_format(api_key)
    
    if test_agentops_initialization(api_key):
        test_session_creation(api_key)
    
    print(f"\n📋 Summary:")
    print("If you see ❌ errors above, those indicate potential issues.")
    print("Common solutions:")
    print("1. Check your API key is correct")
    print("2. Ensure network connectivity to AgentOps endpoints")
    print("3. Check firewall/proxy settings")
    print("4. Verify you're using the latest version of agentops")
    print("5. Contact support if issues persist")

if __name__ == "__main__":
    main()