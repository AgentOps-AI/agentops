#!/usr/bin/env python
"""
Run the OpenAI Agents SDK tools in sequence.

This script runs the export_response.py script to generate response data,
then runs the generate_test_fixture.py script to generate test fixtures from the data.

Usage:
    python -m tests.unit.instrumentation.openai_agents_tools.run
"""

import os
import importlib
import asyncio
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def run_module(module_name):
    """Run a module by importing it."""
    print(f"\n{'='*80}")
    print(f"Running {module_name}")
    print(f"{'='*80}\n")
    
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, 'main'):
            module.main()
        elif module_name.endswith('export_response'):
            # Special handling for export_response which uses asyncio
            if hasattr(module, 'export_response_data') and hasattr(module, 'export_tool_calls_response'):
                asyncio.run(module.export_response_data())
                asyncio.run(module.export_tool_calls_response())
    except Exception as e:
        print(f"Error running {module_name}: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to run all tools in sequence."""
    # Ensure we're in the right directory
    package_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Working directory: {os.getcwd()}")
    print(f"Package directory: {package_dir}")
    
    # Run the tools in sequence
    run_module('tests.unit.instrumentation.openai_agents_tools.export_response')
    run_module('tests.unit.instrumentation.openai_agents_tools.generate_test_fixture')
    
    print("\nAll tools completed.")
    print("The following files should have been created:")
    print("- openai_response_export.json")
    print("- openai_response_tool_calls_export.json")
    print("- test_fixtures.py")
    
    print("\nThese files contain real response data and test fixtures that can be used in your tests.")
    print("To use the fixtures, copy the relevant parts into your test file:")
    print("tests/unit/instrumentation/test_openai_agents.py")

if __name__ == "__main__":
    main()