"""
Demo: Component Health Analysis with Graph-Enriched Context.

Shows fulltext search on components using neo4j-graphrag FulltextRetriever
with graph traversal to enrich results with aircraft, system, and maintenance context.

This demo uses the Aircraft database (AIRCRAFT_NEO4J_* env vars).
"""

from __future__ import annotations

import asyncio
import os

from samples.shared import print_header

# Graph-enriched retrieval query for component health
# Traverses: Component <- System <- Aircraft, Component -> MaintenanceEvent
# Simplified to minimize context size
# Note: Uses explicit grouping and null-safe sorting per Cypher best practices
COMPONENT_RETRIEVAL_QUERY = """
MATCH (node)<-[:HAS_COMPONENT]-(sys:System)<-[:HAS_SYSTEM]-(aircraft:Aircraft)
OPTIONAL MATCH (node)-[:HAS_EVENT]->(event:MaintenanceEvent)
WITH node, score, aircraft, sys,
     count(event) AS event_count,
     collect(event.severity)[0] AS last_severity
WHERE score IS NOT NULL
RETURN
    node.name AS component,
    node.type AS type,
    aircraft.tail_number AS aircraft,
    sys.name AS system,
    event_count AS maintenance_events,
    last_severity AS severity
ORDER BY score DESC
"""


async def demo_component_health() -> None:
    """Demo: Component Health Analysis with graph-enriched context."""
    from azure.identity.aio import AzureCliCredential

    from agent_framework_neo4j import Neo4jContextProvider
    from samples.shared import AgentConfig, create_agent, create_agent_client, get_logger

    logger = get_logger()

    print_header("Demo: Component Health Analysis")
    print("This demo searches components using fulltext search")
    print("and enriches results with aircraft, system, and maintenance context.\n")

    # Load configs
    agent_config = AgentConfig()

    # Aircraft database credentials
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
    print("Index: component_search (fulltext)")
    print("Mode: graph_enriched\n")

    print("Graph Traversal Pattern:")
    print("-" * 50)
    print("  Component <- System <- Aircraft")
    print("  Component -> MaintenanceEvent (count)")
    print("  Returns: component, type, aircraft, system, events, severity")
    print("-" * 50 + "\n")

    credential = AzureCliCredential()

    try:
        # Create context provider with fulltext search (no embedder needed)
        # Uses FulltextRetriever internally
        # Use minimal top_k to avoid context overflow
        provider = Neo4jContextProvider(
            uri=aircraft_uri,
            username=aircraft_username,
            password=aircraft_password,
            index_name="component_search",
            index_type="fulltext",
            retrieval_query=COMPONENT_RETRIEVAL_QUERY,
            top_k=3,
            message_history_count=1,
            context_prompt=(
                "## Component Health Records\n"
                "Component data (name, type, aircraft, system, maintenance events):"
            ),
        )

        # Create agent client and agent
        client = create_agent_client(agent_config, credential)
        agent = create_agent(
            client,
            agent_config,
            instructions=(
                "You are an aircraft component analyst. Analyze component data and "
                "explain maintenance history, system context, and health status. Be concise."
            ),
            context_providers=[provider],
        )

        async with provider:
            print("Connected to Aircraft database!\n")

            async with agent:
                print("Agent created with component health context!\n")
                print("-" * 50)

                session = agent.create_session()

                # Demo queries for component health analysis
                # Note: Queries should use terms in component name/type fields
                queries = [
                    "What turbine components have maintenance issues?",
                    "Tell me about fuel pump components and their maintenance",
                ]

                for i, query in enumerate(queries, 1):
                    print(f"\n[Query {i}] User: {query}\n")

                    response = await agent.run(query, session=session)
                    print(f"[Query {i}] Agent: {response.text}\n")
                    print("-" * 50)

                print(
                    "\nDemo complete! Fulltext search found components and "
                    "graph traversal enriched them with maintenance context."
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
