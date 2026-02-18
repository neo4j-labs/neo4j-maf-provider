"""
Demo: Maintenance Manual Search with Graph-Enriched Context.

Shows fulltext search on maintenance manual Document nodes using
neo4j-graphrag FulltextRetriever with graph traversal to enrich results
with aircraft context and chunk content.

This demo uses the Aircraft database (AIRCRAFT_NEO4J_* env vars).
"""

from __future__ import annotations

import asyncio
import os

from samples.shared import print_header

# Graph-enriched retrieval query for maintenance documents
# Traverses: Document -> Aircraft (via APPLIES_TO)
#            Document <- Chunk  (via FROM_DOCUMENT, sampled content)
DOCUMENT_RETRIEVAL_QUERY = """
MATCH (node)-[:APPLIES_TO]->(aircraft:Aircraft)
OPTIONAL MATCH (node)<-[:FROM_DOCUMENT]-(chunk:Chunk)
WITH node, score, aircraft,
     count(chunk) AS chunk_count,
     collect(chunk.text)[0] AS sample_text
WHERE score IS NOT NULL
RETURN
    node.title AS title,
    node.aircraftType AS aircraft_type,
    score,
    aircraft.tail_number AS tail_number,
    aircraft.model AS model,
    aircraft.manufacturer AS manufacturer,
    chunk_count AS chunks,
    left(sample_text, 500) AS sample_content
ORDER BY score DESC
"""


async def demo_maintenance_docs() -> None:
    """Demo: Maintenance Manual Search with graph-enriched context."""
    from azure.identity.aio import AzureCliCredential

    from agent_framework_neo4j import Neo4jContextProvider
    from samples.shared import AgentConfig, create_agent, create_agent_client, get_logger

    logger = get_logger()

    print_header("Demo: Maintenance Manual Search")
    print("This demo searches maintenance manual documents using fulltext search")
    print("and enriches results with aircraft context and document content.\n")

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
    print("Index: document_search (fulltext)")
    print("Mode: graph_enriched\n")

    print("Graph Traversal Pattern:")
    print("-" * 50)
    print("  Document -[:APPLIES_TO]-> Aircraft")
    print("  Document <-[:FROM_DOCUMENT]- Chunk (sampled)")
    print("  Returns: title, aircraft_type, tail_number, manufacturer, chunks, sample_content")
    print("-" * 50 + "\n")

    credential = AzureCliCredential()

    try:
        # Create context provider with fulltext search (no embedder needed)
        provider = Neo4jContextProvider(
            uri=aircraft_uri,
            username=aircraft_username,
            password=aircraft_password,
            index_name="document_search",
            index_type="fulltext",
            retrieval_query=DOCUMENT_RETRIEVAL_QUERY,
            top_k=3,
            context_prompt=(
                "## Maintenance Manual Documents\n"
                "Use the following maintenance manual data to answer questions about "
                "aircraft maintenance documentation. Each record includes the document "
                "title, aircraft type, associated aircraft, and a sample of the content:"
            ),
        )

        # Create agent client and agent
        client = create_agent_client(agent_config, credential)
        agent = create_agent(
            client,
            agent_config,
            instructions=(
                "You are an aircraft documentation specialist. When asked about maintenance "
                "manuals, analyze the provided document records and explain:\n"
                "- Which manuals are available and what aircraft they cover\n"
                "- What content the manuals contain based on the sample text\n"
                "- How the documentation relates to specific aircraft\n\n"
                "Be specific and cite the actual data from the records."
            ),
            context_providers=[provider],
        )

        # Use both provider and agent as async context managers
        async with provider:
            print("Connected to Aircraft database!\n")

            async with agent:
                print("Agent created with maintenance document search context!\n")
                print("-" * 50)

                session = agent.create_session()

                queries = [
                    "What maintenance manuals are available for Airbus aircraft?",
                    "Tell me about the B737 maintenance documentation",
                ]

                for i, query in enumerate(queries, 1):
                    print(f"\n[Query {i}] User: {query}\n")

                    response = await agent.run(query, session=session)
                    print(f"[Query {i}] Agent: {response.text}\n")
                    print("-" * 50)

                print(
                    "\nDemo complete! Fulltext search found maintenance manuals and "
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
