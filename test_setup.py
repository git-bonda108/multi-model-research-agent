"""
Quick setup test script for Multi-Model Research Agent
Tests if all required packages and configurations are available
"""

import sys
import os

def test_imports():
    """Test if required packages can be imported"""
    print("🔍 Testing package imports...")
    
    packages = {
        "streamlit": "Streamlit",
        "openai": "OpenAI SDK",
        "anthropic": "Anthropic SDK",
        "tavily": "Tavily",
        "youtube_search": "YouTube Search",
        "dotenv": "python-dotenv",
        "requests": "Requests"
    }
    
    failed = []
    for package, name in packages.items():
        try:
            __import__(package)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} - NOT INSTALLED")
            failed.append(name)
    
    # Test OpenAI Agents SDK
    print("\n🤖 Testing OpenAI Agents SDK...")
    agents_available = False
    try:
        from agents import Agent, Runner
        print("  ✅ OpenAI Agents SDK (from agents)")
        agents_available = True
    except ImportError:
        try:
            from openai.agents import Agent, Runner
            print("  ✅ OpenAI Agents SDK (from openai.agents)")
            agents_available = True
        except ImportError:
            print("  ⚠️  OpenAI Agents SDK - NOT INSTALLED (optional)")
            print("     Install with: pip install openai-agents")
    
    return failed, agents_available

def test_env_vars():
    """Test if environment variables are set"""
    print("\n🔐 Testing environment variables...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required = ["OPENAI_API_KEY"]
    optional = ["ANTHROPIC_API_KEY", "TAVILY_API_KEY", "SERPER_API_KEY"]
    
    missing_required = []
    missing_optional = []
    
    for key in required:
        value = os.getenv(key)
        if value:
            print(f"  ✅ {key} (set)")
        else:
            print(f"  ❌ {key} - NOT SET (REQUIRED)")
            missing_required.append(key)
    
    for key in optional:
        value = os.getenv(key)
        if value:
            print(f"  ✅ {key} (set)")
        else:
            print(f"  ⚠️  {key} - NOT SET (optional)")
            missing_optional.append(key)
    
    return missing_required, missing_optional

def main():
    print("=" * 60)
    print("Multi-Model Research Agent - Setup Test")
    print("=" * 60)
    print()
    
    # Test imports
    failed_imports, agents_available = test_imports()
    
    # Test environment variables
    missing_required, missing_optional = test_env_vars()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    if failed_imports:
        print(f"\n❌ Missing packages: {', '.join(failed_imports)}")
        print("   Install with: pip install -r requirements.txt")
    else:
        print("\n✅ All core packages available")
    
    if not agents_available:
        print("\n⚠️  OpenAI Agents SDK not installed")
        print("   Agentic features will be disabled")
        print("   Install with: pip install openai-agents")
    else:
        print("\n✅ OpenAI Agents SDK available")
        print("   Agentic features will be enabled")
    
    if missing_required:
        print(f"\n❌ Missing required API keys: {', '.join(missing_required)}")
        print("   Create a .env file with these keys")
    else:
        print("\n✅ Required API keys are set")
    
    if missing_optional:
        print(f"\n⚠️  Missing optional API keys: {', '.join(missing_optional)}")
        print("   Some features may be limited")
    
    print("\n" + "=" * 60)
    
    # Final status
    if failed_imports or missing_required:
        print("❌ Setup incomplete - please fix the issues above")
        sys.exit(1)
    elif not agents_available:
        print("⚠️  Setup complete - will run in standard mode")
        sys.exit(0)
    else:
        print("✅ Setup complete - ready to run!")
        sys.exit(0)

if __name__ == "__main__":
    main()

