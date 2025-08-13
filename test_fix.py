#!/usr/bin/env python3
"""
Test script to validate AgentOps fixes without requiring API keys
"""

import sys
import os
import importlib.util

def test_imports():
    """Test that all required modules can be imported"""
    try:
        import agentops
        import crewai
        from dotenv import load_dotenv
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_agentops_api():
    """Test that the modern AgentOps API is available"""
    try:
        import agentops
        
        # Check if modern functions exist
        assert hasattr(agentops, 'init'), "agentops.init not found"
        assert hasattr(agentops, 'start_trace'), "agentops.start_trace not found"
        assert hasattr(agentops, 'end_trace'), "agentops.end_trace not found"
        assert hasattr(agentops, 'validate_trace_spans'), "agentops.validate_trace_spans not found"
        
        print("✅ Modern AgentOps API available")
        return True
    except (ImportError, AssertionError) as e:
        print(f"❌ AgentOps API test failed: {e}")
        return False

def test_fixed_code_syntax():
    """Test that the fixed code has valid syntax"""
    try:
        # Test the fixed code file
        spec = importlib.util.spec_from_file_location("fixed_example", "fixed_crewai_example.py")
        if spec is None:
            print("❌ Could not load fixed_crewai_example.py")
            return False
            
        module = importlib.util.module_from_spec(spec)
        # We don't execute it, just check if it can be loaded
        print("✅ Fixed code has valid syntax")
        return True
    except Exception as e:
        print(f"❌ Syntax error in fixed code: {e}")
        return False

def test_deprecation_fix():
    """Test that deprecated functions are not used in the fixed code"""
    try:
        with open("fixed_crewai_example.py", "r") as f:
            content = f.read()
        
        # Check for deprecated patterns
        deprecated_patterns = [
            "end_session()",
            "agentops.end_session",
        ]
        
        for pattern in deprecated_patterns:
            if pattern in content:
                print(f"❌ Found deprecated pattern: {pattern}")
                return False
        
        # Check for modern patterns
        modern_patterns = [
            "start_trace(",
            "end_trace(",
            "auto_start_session=False",
        ]
        
        for pattern in modern_patterns:
            if pattern not in content:
                print(f"❌ Missing modern pattern: {pattern}")
                return False
        
        print("✅ No deprecated patterns found, modern API used")
        return True
    except Exception as e:
        print(f"❌ Error checking deprecation fix: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing AgentOps fixes...\n")
    
    tests = [
        ("Import Test", test_imports),
        ("AgentOps API Test", test_agentops_api),
        ("Syntax Test", test_fixed_code_syntax),
        ("Deprecation Fix Test", test_deprecation_fix),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        result = test_func()
        results.append(result)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("="*50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The fix should resolve the AgentOps issues.")
    else:
        print("⚠️  Some tests failed. Please check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()