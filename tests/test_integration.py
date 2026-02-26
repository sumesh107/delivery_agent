"""Integration test for orchestrator with database persistence."""

import asyncio
import sys

# This simple test verifies that:
# 1. Database initializes without errors
# 2. Orchestrator can start with DB backend
# 3. Sessions can be imported from DB layer


async def test_integration():
    """Test that the orchestrator integrates with database."""
    print("\n🧪 Starting integration test...\n")
    
    # Test 1: Database initialization
    print("✓ Test 1: Checking database module imports...")
    try:
        from db.database import init_db, close_db
        from db.models import SessionRecord, MessageRecord
        from db.repositories import SessionRepository
        print("  ✓ All database modules imported successfully")
    except Exception as e:
        print(f"  ✗ Failed to import database modules: {e}")
        return False
    
    # Test 2: Configuration
    print("\n✓ Test 2: Checking configuration...")
    try:
        from core.config import is_db_enabled, get_session_ttl_days, get_database_url
        db_enabled = is_db_enabled()
        ttl_days = get_session_ttl_days()
        db_url = get_database_url()
        print(f"  ✓ DB Enabled: {db_enabled}")
        print(f"  ✓ Session TTL: {ttl_days} days")
        print(f"  ✓ Database URL: {db_url}")
    except Exception as e:
        print(f"  ✗ Failed to load configuration: {e}")
        return False
    
    # Test 3: Database initialization
    print("\n✓ Test 3: Initializing database...")
    try:
        from db.database import init_db, close_db
        await init_db()
        print("  ✓ Database initialization successful")
    except Exception as e:
        print(f"  ✗ Database initialization failed: {e}")
        return False
    
    # Test 4: Create a test session
    print("\n✓ Test 4: Testing session repository...")
    try:
        from db.database import async_session_maker
        from db.repositories import SessionRepository
        from langchain_core.messages import HumanMessage, AIMessage
        
        async with async_session_maker() as session:
            repo = SessionRepository(session)
            
            # Create session
            test_session = await repo.create_session("test-integration-1", ttl_days=7)
            print(f"  ✓ Session created: {test_session.id}")
            
            # Save messages
            messages = [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi there!"),
            ]
            await repo.save_session("test-integration-1", messages)
            print(f"  ✓ Messages saved ({len(messages)} messages)")
            
            # Load messages
            loaded = await repo.get_session("test-integration-1")
            print(f"  ✓ Messages loaded ({len(loaded)} messages)")
            
            await session.commit()
    except Exception as e:
        print(f"  ✗ Session repository test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Cleanup
    print("\n✓ Test 5: Closing database...")
    try:
        await close_db()
        print("  ✓ Database closed successfully")
    except Exception as e:
        print(f"  ✗ Database cleanup failed: {e}")
        return False
    
    print("\n✅ All integration tests passed!\n")
    return True


if __name__ == "__main__":
    result = asyncio.run(test_integration())
    sys.exit(0 if result else 1)
