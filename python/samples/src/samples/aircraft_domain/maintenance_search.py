"""
Demo: Aircraft Maintenance Search with Graph-Enriched Context.

Shows fulltext search on maintenance events using neo4j-graphrag FulltextRetriever
with graph traversal to enrich results with aircraft, system, and component context.

This demo uses the Aircraft database (AIRCRAFT_NEO4J_* env vars).
"""

from __future__ import annotations

import asyncio
import os

from samples.shared import print_header

# Graph-enriched retrieval query for maintenance events
# Traverses: MaintenanceEvent <- Component <- System <- Aircraft
# Note: Uses null-safe sorting per Cypher best practices
MAINTENANCE_RETRIEVAL_QUERY = """
MATCH (node)<-[:HAS_EVENT]-(comp:Component)<-[:HAS_COMPONENT]-(sys:System)<-[:HAS_SYSTEM]-(aircraft:Aircraft)
WHERE score IS NOT NULL
RETURN
    node.fault AS fault,
    node.corrective_action AS corrective_action,
    node.severity AS severity,
    score,
    aircraft.tail_number AS aircraft,
    aircraft.model AS model,
    sys.name AS system,
    sys.type AS system_type,
    comp.name AS component
ORDER BY score DESC
"""


async def demo_aircraft_maintenance_search() -> None:
    """Demo: Aircraft Maintenance Search with graph-enriched context."""
    from azure.identity.aio import AzureCliCredential

    from agent_framework_neo4j import Neo4jContextProvider
    from samples.shared import AgentConfig, create_agent_client, get_logger

    logger = get_logger()

    print_header("Demo: Aircraft Maintenance Search")
    print("This demo searches maintenance events using fulltext search")
    print("and enriches results with aircraft, system, and component context.\n")

    # Load configs
    agent_config = AgentConfig()

    # Aircraft database credentials (different from main Neo4j)
    aircraft_uri = os.getenv("AIRCRAFT_NEO4J_URI")
    aircraft_username = os.getenv("AIRCRAFT_NEO4J_USERNAME")
    aircraft_password = os.getenv("AIRCRAFT_NEO4J_PASSWORD")

    if not agent_config.project_endpoint:
        print("Error: AZURE_AI_PROJECT_ENDPOINT not configured.")
        return

    if not all([aircraft_uri, aircraft_username, aircraft_password]):
        print("Error: Aircraft database not configured.")
        print("Required: AIRCRAFT_NEO4J_URI, AIRCRAFT_NEO4J_USERNAME, AIRCRAFT_NEO4J_PASSWORD")
        return

    print(f"Agent: {agent_config.name}")
    print(f"Model: {agent_config.model}")
    print(f"Aircraft DB: {aircraft_uri}")
    print("Index: maintenance_search (fulltext)")
    print("Mode: graph_enriched\n")

    print("Graph Traversal Pattern:")
    print("-" * 50)
    print("  MaintenanceEvent <- Component <- System <- Aircraft")
    print("  Returns: fault, corrective_action, severity, aircraft, system, component")
    print("-" * 50 + "\n")

    credential = AzureCliCredential()

    try:
        # Create context provider with fulltext search (no embedder needed)
        # Uses FulltextRetriever internally
        provider = Neo4jContextProvider(
            uri=aircraft_uri,
            username=aircraft_username,
            password=aircraft_password,
            index_name="maintenance_search",
            index_type="fulltext",
            retrieval_query=MAINTENANCE_RETRIEVAL_QUERY,
            top_k=5,
            context_prompt=(
                "## Aircraft Maintenance Records\n"
                "Use the following maintenance event data to answer questions about "
                "aircraft faults, repairs, and maintenance history. Each record includes "
                "the fault description, corrective action taken, severity, and the affected "
                "aircraft, system, and component:"
            ),
        )

        # Create agent client
        client = create_agent_client(agent_config, credential)

        # Use both provider and agent as async context managers
        async with provider:
            print("Connected to Aircraft database!\n")

            async with client.create_agent(
                name=agent_config.name,
                instructions=(
                    "You are an aircraft maintenance assistant. When asked about maintenance "
                    "issues, analyze the provided maintenance records and explain:\n"
                    "- What faults were found\n"
                    "- What corrective actions were taken\n"
                    "- Which aircraft, systems, and components were affected\n"
                    "- The severity level of issues\n\n"
                    "Be specific and cite the actual data from the records."
                ),
                context_provider=provider,
            ) as agent:
                print("Agent created with maintenance search context!\n")
                print("-" * 50)

                # Demo queries for maintenance search
                # Note: Queries should use terms that exist in fault/corrective_action fields
                queries = [
                    "What maintenance issues involve vibration?",
                    "Tell me about electrical faults and how they were fixed",
                    "What sensor drift issues have been recorded?",
                ]

                for i, query in enumerate(queries, 1):
                    print(f"\n[Query {i}] User: {query}\n")

                    response = await agent.run(query)
                    print(f"[Query {i}] Agent: {response.text}\n")
                    print("-" * 50)

                print(
                    "\nDemo complete! Fulltext search found maintenance records and "
                    "graph traversal enriched them with aircraft context."
                )

    except ConnectionError as e:
        print(f"\nConnection Error: {e}")
        print("Please check your Aircraft Neo4j configuration.")
    except Exception as e:
        logger.error(f"Error during demo: {e}")
        print(f"\nError: {e}")
        raise
    finally:
        await credential.close()
        await asyncio.sleep(0.1)
