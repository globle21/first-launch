"""
Quick script to test database connection
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file")
    exit(1)

print(f"🔍 Testing connection to: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'database'}")
print("⏳ Connecting...")

try:
    engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 10})
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print(f"✅ Connection successful!")
        print(f"📊 PostgreSQL version: {version[:50]}...")
        
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\n💡 Troubleshooting steps:")
    print("1. Check if Neon database is awake (visit dashboard)")
    print("2. Verify DATABASE_URL in .env is correct")
    print("3. Check your internet connection")
    print("4. Try using direct endpoint instead of pooler")
