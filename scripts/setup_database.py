import asyncio
import asyncpg
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()


async def setup_database():
    """Setup database schema and initial data"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set in environment")
        return False
    
    print("Setting up database...")
    
    try:
        conn = await asyncpg.connect(database_url)
        print("Connected to database")
        
        # Read schema file
        schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
        if not schema_path.exists():
            print(f"ERROR: Schema file not found at {schema_path}")
            await conn.close()
            return False
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Execute schema
        print("Creating tables...")
        await conn.execute(schema_sql)
        print("Tables created successfully")
        
        await conn.close()
        print("Database setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(setup_database())
    sys.exit(0 if success else 1)