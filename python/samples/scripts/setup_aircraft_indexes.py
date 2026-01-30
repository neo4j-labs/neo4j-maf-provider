"""
Setup indexes for the Aircraft Neo4j database.

Creates fulltext indexes required for the aircraft demo samples.

Run with: uv run python scripts/setup_aircraft_indexes.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ClientError

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from util import get_env_file_path


# Index definitions
INDEXES = [
    {
        "name": "maintenance_search",
        "type": "FULLTEXT",
        "label": "MaintenanceEvent",
        "properties": ["fault", "corrective_action"],
        "description": "Search maintenance faults and corrective actions",
    },
    {
        "name": "component_search",
        "type": "FULLTEXT",
        "label": "Component",
        "properties": ["name", "type"],
        "description": "Search component names and types",
    },
    {
        "name": "airport_search",
        "type": "FULLTEXT",
        "label": "Airport",
        "properties": ["name", "city"],
        "description": "Search airport names and cities",
    },
    {
        "name": "delay_search",
        "type": "FULLTEXT",
        "label": "Delay",
        "properties": ["cause"],
        "description": "Search delay causes",
    },
]


async def create_fulltext_index(
    session,
    name: str,
    label: str,
    properties: list[str],
) -> bool:
    """Create a fulltext index if it doesn't exist."""
    props_cypher = ", ".join(f"n.{p}" for p in properties)
    query = f"""
    CREATE FULLTEXT INDEX {name} IF NOT EXISTS
    FOR (n:{label})
    ON EACH [{props_cypher}]
    """
    try:
        await session.run(query)
        return True
    except ClientError as e:
        if "already exists" in str(e).lower():
            return True  # Index already exists
        print(f"  Error creating index {name}: {e}")
        return False


async def verify_index(session, name: str) -> dict | None:
    """Verify an index exists and return its info."""
    query = """
    SHOW INDEXES
    YIELD name, type, labelsOrTypes, properties, state
    WHERE name = $name
    RETURN name, type, labelsOrTypes, properties, state
    """
    result = await session.run(query, {"name": name})
    record = await result.single()
    if record:
        return {
            "name": record["name"],
            "type": record["type"],
            "labels": record["labelsOrTypes"],
            "properties": record["properties"],
            "state": record["state"],
        }
    return None


async def test_fulltext_search(session, index_name: str, query: str) -> list:
    """Test a fulltext search query."""
    cypher = f"""
    CALL db.index.fulltext.queryNodes($index_name, $query)
    YIELD node, score
    RETURN node, score
    LIMIT 3
    """
    result = await session.run(cypher, {"index_name": index_name, "query": query})
    return [record async for record in result]


async def setup_indexes() -> None:
    """Set up all indexes for the aircraft database."""
    # Load environment
    env_path = get_env_file_path()
    if env_path:
        load_dotenv(env_path)
        print(f"Loaded environment from: {env_path}\n")

    # Get aircraft database credentials
    uri = os.getenv("AIRCRAFT_NEO4J_URI")
    username = os.getenv("AIRCRAFT_NEO4J_USERNAME")
    password = os.getenv("AIRCRAFT_NEO4J_PASSWORD")

    if not all([uri, username, password]):
        print("ERROR: Aircraft database not configured.")
        print("Required: AIRCRAFT_NEO4J_URI, AIRCRAFT_NEO4J_USERNAME, AIRCRAFT_NEO4J_PASSWORD")
        return

    print(f"Connecting to Aircraft Neo4j at: {uri}")
    print("=" * 70)

    driver = AsyncGraphDatabase.driver(uri, auth=(username, password))

    try:
        await driver.verify_connectivity()
        print("Connected successfully!\n")

        async with driver.session() as session:
            # Create indexes
            print("## Creating Indexes")
            print("-" * 70)

            for idx in INDEXES:
                print(f"\n  Creating: {idx['name']}")
                print(f"    Label: {idx['label']}")
                print(f"    Properties: {idx['properties']}")
                print(f"    Purpose: {idx['description']}")

                success = await create_fulltext_index(
                    session,
                    idx["name"],
                    idx["label"],
                    idx["properties"],
                )

                if success:
                    print("    Status: Created/Exists")
                else:
                    print("    Status: FAILED")

            # Wait for indexes to be online
            print("\n\n## Verifying Indexes")
            print("-" * 70)
            print("Waiting for indexes to come online...")
            await asyncio.sleep(2)  # Give time for index creation

            all_online = True
            for idx in INDEXES:
                info = await verify_index(session, idx["name"])
                if info:
                    status = info["state"]
                    print(f"\n  {idx['name']}: {status}")
                    if status != "ONLINE":
                        all_online = False
                        print("    Waiting for index to come online...")
                else:
                    print(f"\n  {idx['name']}: NOT FOUND")
                    all_online = False

            # Test searches
            print("\n\n## Testing Fulltext Searches")
            print("-" * 70)

            test_queries = [
                ("maintenance_search", "vibration"),
                ("component_search", "turbine"),
                ("airport_search", "Los Angeles"),
                ("delay_search", "weather"),
            ]

            for index_name, query in test_queries:
                print(f"\n  Testing {index_name} with query: '{query}'")
                try:
                    results = await test_fulltext_search(session, index_name, query)
                    if results:
                        print(f"    Found {len(results)} results")
                        for r in results[:2]:
                            node = dict(r["node"])
                            score = r["score"]
                            # Show first few properties
                            display = {k: v for k, v in list(node.items())[:3]}
                            print(f"      Score: {score:.3f} - {display}")
                    else:
                        print("    No results found")
                except Exception as e:
                    print(f"    Error: {e}")

        print("\n" + "=" * 70)
        if all_online:
            print("All indexes created and online!")
        else:
            print("Some indexes may still be building. Run again to verify.")
        print("=" * 70)

    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        await driver.close()


def main() -> None:
    """Entry point."""
    asyncio.run(setup_indexes())


if __name__ == "__main__":
    main()
