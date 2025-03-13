from setuptools import setup, find_namespace_packages

setup(
    name="opentelemetry-instrumentation-agents",
    version="0.1.0",
    description="OpenTelemetry instrumentation for OpenAI Agents SDK",
    author="AgentOps",
    author_email="info@agentops.ai",
    url="https://github.com/agentops-ai/agentops",
    packages=find_namespace_packages(include=["opentelemetry.*"]),
    install_requires=[
        "agentops>=0.1.0",
        "opentelemetry-api>=1.0.0",
        "opentelemetry-sdk>=1.0.0",
        "opentelemetry-instrumentation>=0.30b0",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
)
