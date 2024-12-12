import sys
import importlib.util


def verify_packages():
    required_packages = [("camel", "camel-ai[all]"), ("agentops", "agentops"), ("jupyter", "jupyter")]

    all_passed = True
    for module_name, package_name in required_packages:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            print(f"❌ {package_name} is not installed properly")
            all_passed = False
        else:
            print(f"✅ {package_name} is installed properly")
    return all_passed


def verify_imports():
    try:
        from camel.agents import ChatAgent
        from camel.messages import BaseMessage
        from camel.models import ModelFactory
        from camel.types import ModelPlatformType, ModelType
        from camel.toolkits import SearchToolkit
        print("✅ All required Camel modules can be imported")
        return True
    except ImportError as e:
        print(f"❌ Error importing Camel modules: {e}")
        return False


def main():
    packages_ok = verify_packages()
    imports_ok = verify_imports()

    if not (packages_ok and imports_ok):
        sys.exit(1)
    print("\n✅ Basic setup verification completed successfully")


if __name__ == "__main__":
    main()
