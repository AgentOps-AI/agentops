 #!/usr/bin/env python
"""
Advanced example of using the AgentOps SDK.

This example demonstrates more advanced features of the SDK including:
- Error handling
- Nested spans
- Complex workflows with multiple agents and tools
- Custom attributes and tags
"""

import os
import sys
import time
import random
import json
from typing import List, Dict, Any, Optional, Union, Tuple
 
from agentops.config import Config
from agentops.sdk.core import TracingCore
from agentops.sdk.decorators.session import session
from agentops.sdk.decorators.agent import agent
from agentops.sdk.decorators.tool import tool


class DataSource:
    """Simulated data source for the example."""
    
    @staticmethod
    def get_data(query: str) -> List[Dict[str, Any]]:
        """Get data based on a query."""
        # Simulate a data source
        time.sleep(0.3)
        
        # Randomly fail sometimes to demonstrate error handling
        if random.random() < 0.2:
            raise ConnectionError("Failed to connect to data source")
        
        return [
            {"id": i, "title": f"Item {i} for {query}", "value": random.random()}
            for i in range(1, 6)
        ]


class APIClient:
    """Simulated API client for the example."""
    
    @staticmethod
    def fetch(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from an API endpoint."""
        # Simulate an API call
        time.sleep(0.4)
        
        # Randomly fail sometimes to demonstrate error handling
        if random.random() < 0.2:
            raise TimeoutError("API request timed out")
        
        return {
            "endpoint": endpoint,
            "params": params,
            "results": [
                {"name": f"API result {i}", "score": random.random()}
                for i in range(1, 4)
            ]
        }


def initialize_tracing():
    """Initialize the tracing core."""
    config = Config(
        api_key="test_key",  # Replace with your API key
        host="https://api.agentops.ai",  # Replace with your host
        project_id="example-project",  # Replace with your project ID
    )
    core = TracingCore.get_instance()
    core.initialize(config)
    return core


@session(
    name="advanced_workflow",
    tags=["example", "advanced"],
    attributes={"priority": "high"}
)
class AdvancedWorkflowSession:
    """An advanced workflow session that demonstrates complex scenarios."""
    
    def __init__(self, query: str, max_retries: int = 3):
        """Initialize the advanced workflow session."""
        self.query = query
        self.max_retries = max_retries
        self.orchestrator = OrchestratorAgent()
        self.data_agent = DataAgent()
        self.analysis_agent = AnalysisAgent()
    
    def run(self) -> Dict[str, Any]:
        """Run the advanced workflow."""
        print(f"Starting advanced workflow for query: {self.query}")
        
        try:
            # Step 1: Orchestrator plans the workflow
            plan = self.orchestrator.plan_workflow(self.query)
            
            # Step 2: Data agent fetches and processes data
            data_results = self.execute_with_retry(
                self.data_agent.fetch_data,
                self.query,
                plan.get("data_sources", [])
            )
            
            # Step 3: Analysis agent analyzes the data
            analysis_results = self.execute_with_retry(
                self.analysis_agent.analyze_data,
                data_results,
                plan.get("analysis_methods", [])
            )
            
            # Step 4: Orchestrator generates the final report
            final_report = self.orchestrator.generate_report(
                self.query, plan, data_results, analysis_results
            )
            
            print(f"Advanced workflow completed successfully")
            return final_report
            
        except Exception as e:
            print(f"Advanced workflow failed: {str(e)}")
            # Record the error in the session span
            try:
                self._session_span.set_attribute("error", str(e))
                self._session_span.set_attribute("error_type", type(e).__name__)
            except AttributeError:
                pass
            raise
    
    def execute_with_retry(self, func, *args, **kwargs) -> Any:
        """Execute a function with retry logic."""
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                print(f"Attempt {attempt} failed: {str(e)}")
                if attempt < self.max_retries:
                    # Exponential backoff
                    wait_time = 0.5 * (2 ** (attempt - 1))
                    print(f"Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
        
        # If we get here, all retries failed
        raise last_error


@agent(
    name="orchestrator",
    agent_type="orchestrator",
    attributes={"role": "coordinator"}
)
class OrchestratorAgent:
    """An agent that orchestrates the workflow."""
    
    def plan_workflow(self, query: str) -> Dict[str, Any]:
        """Plan the workflow based on the query."""
        try:
            self._agent_span.record_thought(f"Planning workflow for query: {query}")
        except AttributeError:
            pass
        
        # Use the planning tool
        return self.create_plan(query)
    
    @tool(name="create_plan", tool_type="planning")
    def create_plan(self, query: str) -> Dict[str, Any]:
        """Create a workflow plan."""
        # Simulate planning
        time.sleep(0.5)
        
        return {
            "query": query,
            "steps": ["data_collection", "analysis", "reporting"],
            "data_sources": ["database", "api"],
            "analysis_methods": ["statistical", "semantic"],
            "timestamp": time.time()
        }
    
    def generate_report(
        self,
        query: str,
        plan: Dict[str, Any],
        data_results: Dict[str, Any],
        analysis_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a final report."""
        try:
            self._agent_span.record_thought(f"Generating final report for query: {query}")
        except AttributeError:
            pass
        
        # Use the reporting tool
        return self.create_report(query, plan, data_results, analysis_results)
    
    @tool(name="create_report", tool_type="reporting")
    def create_report(
        self,
        query: str,
        plan: Dict[str, Any],
        data_results: Dict[str, Any],
        analysis_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a final report."""
        # Simulate report generation
        time.sleep(0.6)
        
        return {
            "query": query,
            "plan_summary": {
                "steps": plan["steps"],
                "data_sources": plan["data_sources"],
                "analysis_methods": plan["analysis_methods"]
            },
            "data_summary": {
                "sources": list(data_results.keys()),
                "total_items": sum(len(items) for items in data_results.values())
            },
            "analysis_summary": {
                "methods": list(analysis_results.keys()),
                "insights": analysis_results.get("insights", [])
            },
            "timestamp": time.time()
        }


@agent(
    name="data_agent",
    agent_type="data",
    attributes={"role": "data_collector"}
)
class DataAgent:
    """An agent that fetches and processes data."""
    
    def __init__(self):
        """Initialize the data agent."""
        self.data_source = DataSource()
        self.api_client = APIClient()
    
    def fetch_data(self, query: str, sources: List[str]) -> Dict[str, Any]:
        """Fetch data from multiple sources."""
        try:
            self._agent_span.record_thought(f"Fetching data for query: {query} from sources: {sources}")
        except AttributeError:
            pass
        
        results = {}
        
        # Fetch from database if requested
        if "database" in sources:
            try:
                results["database"] = self.query_database(query)
            except Exception as e:
                try:
                    self._agent_span.record_error(f"Database query failed: {str(e)}")
                except AttributeError:
                    pass
                # Continue with other sources even if one fails
        
        # Fetch from API if requested
        if "api" in sources:
            try:
                results["api"] = self.call_api(query)
            except Exception as e:
                try:
                    self._agent_span.record_error(f"API call failed: {str(e)}")
                except AttributeError:
                    pass
        
        return results
    
    @tool(name="query_database", tool_type="data_access")
    def query_database(self, query: str) -> List[Dict[str, Any]]:
        """Query a database for data."""
        # Use the data source to get data
        return self.data_source.get_data(query)
    
    @tool(name="call_api", tool_type="data_access")
    def call_api(self, query: str) -> Dict[str, Any]:
        """Call an API to get data."""
        # Use the API client to fetch data
        return self.api_client.fetch("search", {"q": query, "limit": 10})


@agent(
    name="analysis_agent",
    agent_type="analysis",
    attributes={"role": "data_analyzer"}
)
class AnalysisAgent:
    """An agent that analyzes data."""
    
    def analyze_data(
        self,
        data_results: Dict[str, Any],
        methods: List[str]
    ) -> Dict[str, Any]:
        """Analyze data using multiple methods."""
        try:
            self._agent_span.record_thought(
                f"Analyzing data with methods: {methods}"
            )
        except AttributeError:
            pass
        
        results = {}
        
        # Perform statistical analysis if requested
        if "statistical" in methods:
            results["statistical"] = self.statistical_analysis(data_results)
        
        # Perform semantic analysis if requested
        if "semantic" in methods:
            results["semantic"] = self.semantic_analysis(data_results)
        
        # Generate insights from the analyses
        results["insights"] = self.generate_insights(results)
        
        return results
    
    @tool(name="statistical_analysis", tool_type="analysis")
    def statistical_analysis(self, data_results: Dict[str, Any]) -> Dict[str, Any]:
        """Perform statistical analysis on the data."""
        # Simulate statistical analysis
        time.sleep(0.4)
        
        stats = {}
        
        # Process database results if available
        if "database" in data_results:
            db_data = data_results["database"]
            if isinstance(db_data, list):
                values = [item.get("value", 0) for item in db_data if "value" in item]
                if values:
                    stats["database"] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values)
                    }
        
        # Process API results if available
        if "api" in data_results:
            api_data = data_results["api"]
            if "results" in api_data and isinstance(api_data["results"], list):
                scores = [item.get("score", 0) for item in api_data["results"] if "score" in item]
                if scores:
                    stats["api"] = {
                        "count": len(scores),
                        "min": min(scores),
                        "max": max(scores),
                        "avg": sum(scores) / len(scores)
                    }
        
        return stats
    
    @tool(name="semantic_analysis", tool_type="analysis")
    def semantic_analysis(self, data_results: Dict[str, Any]) -> Dict[str, Any]:
        """Perform semantic analysis on the data."""
        # Simulate semantic analysis
        time.sleep(0.5)
        
        semantic = {"topics": [], "entities": []}
        
        # Extract titles/names from all sources
        titles = []
        
        # From database
        if "database" in data_results:
            db_data = data_results["database"]
            if isinstance(db_data, list):
                titles.extend([item.get("title", "") for item in db_data if "title" in item])
        
        # From API
        if "api" in data_results:
            api_data = data_results["api"]
            if "results" in api_data and isinstance(api_data["results"], list):
                titles.extend([item.get("name", "") for item in api_data["results"] if "name" in item])
        
        # Simulate topic extraction
        if titles:
            semantic["topics"] = ["topic1", "topic2", "topic3"]
            semantic["entities"] = ["entity1", "entity2"]
        
        return semantic
    
    @tool(name="generate_insights", tool_type="analysis")
    def generate_insights(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate insights from the analysis results."""
        # Simulate insight generation
        time.sleep(0.3)
        
        insights = []
        
        # Generate insights from statistical analysis
        if "statistical" in analysis_results:
            stats = analysis_results["statistical"]
            if "database" in stats:
                db_stats = stats["database"]
                insights.append(f"Database data has {db_stats['count']} items with average value of {db_stats['avg']:.2f}")
            
            if "api" in stats:
                api_stats = stats["api"]
                insights.append(f"API data has {api_stats['count']} items with average score of {api_stats['avg']:.2f}")
        
        # Generate insights from semantic analysis
        if "semantic" in analysis_results:
            semantic = analysis_results["semantic"]
            if semantic.get("topics"):
                insights.append(f"Main topics identified: {', '.join(semantic['topics'])}")
            if semantic.get("entities"):
                insights.append(f"Key entities identified: {', '.join(semantic['entities'])}")
        
        return insights


def main():
    """Run the example."""
    # Initialize tracing
    initialize_tracing()
    
    # Create and run the advanced workflow
    try:
        session = AdvancedWorkflowSession("AgentOps SDK advanced example")
        result = session.run()
        
        # Print the result
        print("\nFinal report:")
        print(f"Query: {result['query']}")
        print("Plan summary:")
        for key, value in result['plan_summary'].items():
            print(f"  {key}: {value}")
        print("Data summary:")
        for key, value in result['data_summary'].items():
            print(f"  {key}: {value}")
        print("Analysis summary:")
        for key, value in result['analysis_summary'].items():
            if key == "insights":
                print("  Insights:")
                for i, insight in enumerate(value, 1):
                    print(f"    {i}. {insight}")
            else:
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error running advanced example: {str(e)}")


if __name__ == "__main__":
    main()
