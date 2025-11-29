import asyncio
import os
import sys
from pathlib import Path
from livekit import api
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()


async def test_agent():
    """Test agent connectivity"""
    
    print("Testing Agent Configuration\n")
    
    # Check environment variables
    checks = {
        "LIVEKIT_URL": os.getenv("LIVEKIT_URL"),
        "LIVEKIT_API_KEY": os.getenv("LIVEKIT_API_KEY"),
        "LIVEKIT_API_SECRET": os.getenv("LIVEKIT_API_SECRET"),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        "DATABASE_URL": os.getenv("DATABASE_URL"),
    }
    
    print("Environment Variables:")
    for key, value in checks.items():
        status = "OK" if value else "MISSING"
        print(f"  {key}: {status}")
    
    if not all(checks.values()):
        print("\nERROR: Missing required environment variables")
        return False
    
    print("\nTesting LiveKit Connection...")
    
    try:
        lkapi = api.LiveKitAPI(
            url=checks["LIVEKIT_URL"],
            api_key=checks["LIVEKIT_API_KEY"],
            api_secret=checks["LIVEKIT_API_SECRET"]
        )
        
        response = await lkapi.room.list_rooms(api.ListRoomsRequest())
        room_count = len(response.rooms)
        print(f"  OK - Connected ({room_count} active rooms)")
        
        await lkapi.aclose()
        
    except Exception as e:
        print(f"  FAILED - {e}")
        return False
    
    print("\nTesting Database Connection...")
    
    try:
        import asyncpg
        conn = await asyncpg.connect(checks["DATABASE_URL"])
        result = await conn.fetchval("SELECT COUNT(*) FROM agents")
        print(f"  OK - Connected ({result} agents configured)")
        await conn.close()
        
    except Exception as e:
        print(f"  FAILED - {e}")
        return False
    
    print("\nTesting Gemini API...")
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=checks["GOOGLE_API_KEY"])
        
        # List available models to verify
        models = genai.list_models()
        available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        if not available_models:
            print(f"  FAILED - No models available for content generation")
            return False
        
        # Use the first available model
        model_name = available_models[0].replace('models/', '')
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'test successful'")
        print(f"  OK - Gemini API working (using {model_name})")
        
    except Exception as e:
        print(f"  FAILED - {e}")
        return False
    
    print("\nAll tests passed!")
    print("Ready to run: python app/agents/gemini_agent.py dev")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_agent())
    sys.exit(0 if success else 1)