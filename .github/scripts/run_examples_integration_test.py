#!/usr/bin/env python3
"""
Integration test script that runs AgentOps examples and verifies they logged data correctly
using the AgentOps public API.
"""

import os
import sys
import subprocess
import json
import re
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class ExampleResult:
    """Result of running an example script."""
    file_path: str
    success: bool
    trace_id: Optional[str] = None
    error_message: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    api_verified: bool = False
    api_error: Optional[str] = None


class AgentOpsAPIClient:
    """Client for AgentOps public API verification."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.agentops.ai"):
        self.api_key = api_key
        self.base_url = base_url
        self.bearer_token = None
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Exchange API key for bearer token."""
        try:
            response = requests.post(
                f"{self.base_url}/public/v1/auth/access_token",
                json={"api_key": self.api_key},
                timeout=30
            )
            response.raise_for_status()
            self.bearer_token = response.json()["bearer"]
        except Exception as e:
            raise Exception(f"Failed to authenticate with AgentOps API: {e}")
    
    def get_trace_details(self, trace_id: str) -> Dict:
        """Get trace details from the API."""
        if not self.bearer_token:
            raise Exception("Not authenticated")
        
        try:
            response = requests.get(
                f"{self.base_url}/public/v1/traces/{trace_id}",
                headers={"Authorization": f"Bearer {self.bearer_token}"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get trace details: {e}")
    
    def get_trace_metrics(self, trace_id: str) -> Dict:
        """Get trace metrics from the API."""
        if not self.bearer_token:
            raise Exception("Not authenticated")
        
        try:
            response = requests.get(
                f"{self.base_url}/public/v1/traces/{trace_id}/metrics",
                headers={"Authorization": f"Bearer {self.bearer_token}"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get trace metrics: {e}")
    
    def verify_trace(self, trace_id: str) -> Tuple[bool, Optional[str]]:
        """Verify that a trace has valid data."""
        try:
            details = self.get_trace_details(trace_id)
            metrics = self.get_trace_metrics(trace_id)
            
            if not details.get("spans"):
                return False, "No spans found in trace"
            
            span_count = metrics.get("span_count", 0)
            success_count = metrics.get("success_count", 0)
            
            if span_count == 0:
                return False, "Span count is 0"
            
            if success_count == 0:
                return False, "No successful spans found"
            
            return True, None
            
        except Exception as e:
            return False, str(e)


class ExampleRunner:
    """Runs AgentOps examples and verifies their output."""
    
    def __init__(self, api_client: AgentOpsAPIClient):
        self.api_client = api_client
        self.repo_root = Path(__file__).parent.parent.parent
        self.examples_dir = self.repo_root / "examples"
        
        self.skip_patterns = [
            "generate_documentation.py",
            "__pycache__",
            ".ipynb_checkpoints",
        ]
        
        self.skip_interactive = [
            "async_human_input",
        ]
    
    def find_examples(self) -> List[Path]:
        """Find all example files to test."""
        examples = []
        
        for pattern in ["**/*.py", "**/*.ipynb"]:
            for file_path in self.examples_dir.glob(pattern):
                if any(skip in str(file_path) for skip in self.skip_patterns):
                    continue
                if any(skip in str(file_path) for skip in self.skip_interactive):
                    continue
                examples.append(file_path)
        
        return sorted(examples)
    
    def extract_trace_id(self, output: str) -> Optional[str]:
        """Extract trace ID from example output."""
        patterns = [
            r"https://app\.agentops\.ai/traces/([a-f0-9-]+)",
            r"trace_id[:\s]+([a-f0-9-]+)",
            r"Trace ID[:\s]+([a-f0-9-]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def run_python_example(self, file_path: Path) -> ExampleResult:
        """Run a Python example file."""
        try:
            result = subprocess.run(
                ["uv", "run", "python", str(file_path)],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            combined_output = stdout + stderr
            
            trace_id = self.extract_trace_id(combined_output)
            
            success = result.returncode == 0
            error_message = None if success else f"Exit code {result.returncode}: {stderr}"
            
            return ExampleResult(
                file_path=str(file_path.relative_to(self.repo_root)),
                success=success,
                trace_id=trace_id,
                error_message=error_message,
                stdout=stdout,
                stderr=stderr
            )
            
        except subprocess.TimeoutExpired:
            return ExampleResult(
                file_path=str(file_path.relative_to(self.repo_root)),
                success=False,
                error_message="Timeout after 120 seconds"
            )
        except Exception as e:
            return ExampleResult(
                file_path=str(file_path.relative_to(self.repo_root)),
                success=False,
                error_message=str(e)
            )
    
    def run_notebook_example(self, file_path: Path) -> ExampleResult:
        """Run a Jupyter notebook example."""
        try:
            result = subprocess.run(
                ["uv", "run", "jupyter", "nbconvert", "--to", "notebook", "--execute", 
                 "--stdout", str(file_path)],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            combined_output = stdout + stderr
            
            trace_id = self.extract_trace_id(combined_output)
            
            success = result.returncode == 0
            error_message = None if success else f"Exit code {result.returncode}: {stderr}"
            
            return ExampleResult(
                file_path=str(file_path.relative_to(self.repo_root)),
                success=success,
                trace_id=trace_id,
                error_message=error_message,
                stdout=stdout,
                stderr=stderr
            )
            
        except subprocess.TimeoutExpired:
            return ExampleResult(
                file_path=str(file_path.relative_to(self.repo_root)),
                success=False,
                error_message="Timeout after 120 seconds"
            )
        except Exception as e:
            return ExampleResult(
                file_path=str(file_path.relative_to(self.repo_root)),
                success=False,
                error_message=str(e)
            )
    
    def run_example(self, file_path: Path) -> ExampleResult:
        """Run a single example and return the result."""
        print(f"Running {file_path.relative_to(self.repo_root)}...")
        
        if file_path.suffix == ".py":
            result = self.run_python_example(file_path)
        elif file_path.suffix == ".ipynb":
            result = self.run_notebook_example(file_path)
        else:
            return ExampleResult(
                file_path=str(file_path.relative_to(self.repo_root)),
                success=False,
                error_message="Unsupported file type"
            )
        
        if result.success and result.trace_id:
            time.sleep(2)
            api_verified, api_error = self.api_client.verify_trace(result.trace_id)
            result.api_verified = api_verified
            result.api_error = api_error
        
        return result
    
    def run_all_examples(self, max_workers: int = 4) -> List[ExampleResult]:
        """Run all examples with parallel execution."""
        examples = self.find_examples()
        results = []
        
        print(f"Found {len(examples)} examples to test")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_example = {
                executor.submit(self.run_example, example): example 
                for example in examples
            }
            
            for future in as_completed(future_to_example):
                result = future.result()
                results.append(result)
        
        return results


def main():
    """Main function to run the integration test."""
    api_key = os.getenv("AGENTOPS_API_KEY")
    if not api_key:
        print("ERROR: AGENTOPS_API_KEY environment variable is required")
        sys.exit(1)
    
    try:
        api_client = AgentOpsAPIClient(api_key)
        runner = ExampleRunner(api_client)
        results = runner.run_all_examples()
        
        total_examples = len(results)
        successful_runs = sum(1 for r in results if r.success)
        api_verified = sum(1 for r in results if r.api_verified)
        
        print("\n" + "="*80)
        print("INTEGRATION TEST RESULTS")
        print("="*80)
        print(f"Total examples: {total_examples}")
        print(f"Successful runs: {successful_runs}")
        print(f"API verified: {api_verified}")
        print(f"Success rate: {successful_runs/total_examples*100:.1f}%")
        print(f"API verification rate: {api_verified/total_examples*100:.1f}%")
        
        print("\nFAILED EXAMPLES:")
        failed_examples = [r for r in results if not r.success]
        if failed_examples:
            for result in failed_examples:
                print(f"  ❌ {result.file_path}: {result.error_message}")
        else:
            print("  None")
        
        print("\nAPI VERIFICATION FAILURES:")
        api_failures = [r for r in results if r.success and not r.api_verified]
        if api_failures:
            for result in api_failures:
                print(f"  ⚠️  {result.file_path}: {result.api_error}")
        else:
            print("  None")
        
        print("\nSUCCESSFUL EXAMPLES:")
        successful_examples = [r for r in results if r.success and r.api_verified]
        for result in successful_examples:
            print(f"  ✅ {result.file_path}")
        
        if failed_examples or api_failures:
            print(f"\n❌ Integration test FAILED: {len(failed_examples)} execution failures, {len(api_failures)} API verification failures")
            sys.exit(1)
        else:
            print(f"\n✅ Integration test PASSED: All {total_examples} examples executed successfully and verified via API")
            sys.exit(0)
    
    except Exception as e:
        print(f"ERROR: Integration test failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
