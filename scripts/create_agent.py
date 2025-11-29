import asyncio
import asyncpg
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()


async def create_agent():
    """Create a new human agent"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return False
    
    print("Create New Agent\n")
    
    # Get agent information
    name = input("Agent name: ").strip()
    phone = input("Agent phone number (e.g., +1234567890): ").strip()
    
    print("\nSelect departments (comma-separated):")
    print("  - general")
    print("  - billing")
    print("  - technical")
    print("  - sales")
    departments = input("Departments: ").strip().split(',')
    departments = [d.strip() for d in departments]
    
    max_calls = input("Max concurrent calls (default: 2): ").strip()
    max_calls = int(max_calls) if max_calls else 2
    
    try:
        conn = await asyncpg.connect(database_url)
        
        await conn.execute(
            """
            INSERT INTO agents (name, phone_number, status, skills, max_concurrent_calls)
            VALUES ($1, $2, 'offline', $3, $4)
            """,
            name,
            phone,
            {"departments": departments},
            max_calls
        )
        
        print(f"\nCreated agent: {name}")
        print(f"   Phone: {phone}")
        print(f"   Departments: {', '.join(departments)}")
        print(f"   Max calls: {max_calls}")
        print("\nAgent starts in 'offline' status. Use dashboard to set them online.")
        
        await conn.close()
        return True
        
    except asyncpg.UniqueViolationError:
        print(f"\nERROR: Agent with phone number {phone} already exists")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(create_agent())
    sys.exit(0 if success else 1)