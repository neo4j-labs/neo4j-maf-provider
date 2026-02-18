"""
Demo: Aircraft Flight Delay Analysis with Graph-Enriched Context.

Shows fulltext search on flight delays using neo4j-graphrag FulltextRetriever
with graph traversal to enrich results with flight, aircraft, and airport context.

This demo uses the Aircraft database (AIRCRAFT_NEO4J_* env vars).
"""

from __future__ import annotations

import asyncio
import os

from samples.shared import print_header

# Graph-enriched retrieval query for flight delays
# Traverses: Delay <- Flight -> Aircraft, Origin Airport, Destination Airport
# Simplified output to minimize context size
# Note: Uses null-safe sorting per Cypher best practices
DELAY_RETRIEVAL_QUERY = """
MATCH (node)<-[:HAS_DELAY]-(flight:Flight)-[:OPERATES_FLIGHT]-(aircraft:Aircraft)
MATCH (flight)-[:DEPARTS_FROM]->(origin:Airport)
MATCH (flight)-[:ARRIVES_AT]->(dest:Airport)
WHERE score IS NOT NULL AND node.minutes IS NOT NULL
RETURN
    node.cause AS cause,
    node.minutes AS minutes,
    flight.flight_number AS flight,
    aircraft.tail_number AS aircraft,
    origin.iata + ' -> ' + dest.iata AS route
ORDER BY node.minutes DESC
"""


async def demo_aircraft_flight_delays() -> None:
    """Demo: Aircraft Flight Delay Analysis with graph-enriched context."""
    from azure.identity.aio import AzureCliCredential

    from agent_framework_neo4j import Neo4jContextProvider
    from samples.shared import AgentConfig, create_agent, create_agent_client, get_logger

    logger = get_logger()

    print_header("Demo: Flight Delay Analysis")
    print("This demo searches flight delays using fulltext search")
    print("and enriches results with flight, aircraft, and route context.\n")

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
    print("Index: delay_search (fulltext)")
    print("Mode: graph_enriched\n")

    print("Graph Traversal Pattern:")
    print("-" * 50)
    print("  Delay <- Flight -> Aircraft, Origin, Destination")
    print("  Returns: cause, minutes, flight, aircraft, route")
    print("-" * 50 + "\n")

    credential = AzureCliCredential()

    try:
        # Create context provider with fulltext search (no embedder needed)
        # Uses FulltextRetriever internally
        # Use minimal top_k and message_history to avoid context overflow
        provider = Neo4jContextProvider(
            uri=aircraft_uri,
            username=aircraft_username,
            password=aircraft_password,
            index_name="delay_search",
            index_type="fulltext",
            retrieval_query=DELAY_RETRIEVAL_QUERY,
            top_k=2,
            message_history_count=1,
            context_prompt=(
                "## Flight Delay Records\n"
                "Delay data (cause, minutes, flight, aircraft, route):"
            ),
        )

        # Create agent client and agent
        client = create_agent_client(agent_config, credential)
        agent = create_agent(
            client,
            agent_config,
            instructions=(
                "You are a flight operations analyst. Analyze delay records and "
                "explain causes, durations, and affected flights/routes. Be concise."
            ),
            context_providers=[provider],
        )

        async with provider:
            print("Connected to Aircraft database!\n")

            async with agent:
                print("Agent created with delay analysis context!\n")
                print("-" * 50)

                session = agent.create_session()

                # Demo queries for delay analysis (limited to 2 to manage context)
                queries = [
                    "What flights were delayed due to weather?",
                    "Tell me about security-related delays",
                ]

                for i, query in enumerate(queries, 1):
                    print(f"\n[Query {i}] User: {query}\n")

                    response = await agent.run(query, session=session)
                    print(f"[Query {i}] Agent: {response.text}\n")
                    print("-" * 50)

                print(
                    "\nDemo complete! Fulltext search found delay records and "
                    "graph traversal enriched them with flight/route context."
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
