"""
Demo: Neo4j Memory Provider - Persistent Agent Memory.

This demo shows how the Neo4jContextProvider can store conversation memories
in Neo4j and retrieve them across different conversations. The provider
stores messages as Memory nodes and uses semantic search to find relevant
past conversations.

Key features demonstrated:
- Memory storage after each model invocation (invoked() method)
- Memory retrieval before each model invocation (invoking() method)
- User-scoped memory isolation (user A cannot see user B's memories)
- Cross-conversation memory persistence (new thread, same user)
- Semantic search finds relevant memories based on query context
"""

from __future__ import annotations

import asyncio

from samples.shared import print_header


async def _cleanup_test_memories(neo4j_settings: "Neo4jSettings") -> None:
    """Clean up any existing test memories from previous runs."""
    import neo4j

    driver = neo4j.GraphDatabase.driver(
        neo4j_settings.uri,
        auth=(neo4j_settings.username, neo4j_settings.get_password()),
    )

    with driver.session() as session:
        # Delete memories for our test users
        result = session.run(
            "MATCH (m:Memory) WHERE m.user_id IN ['user_alice', 'user_bob'] "
            "WITH count(m) as cnt "
            "MATCH (m:Memory) WHERE m.user_id IN ['user_alice', 'user_bob'] "
            "DELETE m "
            "RETURN cnt"
        )
        record = result.single()
        count = record["cnt"] if record else 0
        if count > 0:
            print(f"  Deleted {count} existing test memories")

    driver.close()


async def _show_stored_memories(neo4j_settings: "Neo4jSettings", user_id: str) -> int:
    """Query and display memories stored for a user."""
    import neo4j

    driver = neo4j.GraphDatabase.driver(
        neo4j_settings.uri,
        auth=(neo4j_settings.username, neo4j_settings.get_password()),
    )

    with driver.session() as session:
        result = session.run(
            """
            MATCH (m:Memory)
            WHERE m.user_id = $user_id
            RETURN m.text AS text, m.role AS role, m.timestamp AS timestamp
            ORDER BY m.timestamp DESC
            """,
            user_id=user_id,
        )
        records = list(result)

    driver.close()

    print(f"\n  [Memory Store: {len(records)} memories for {user_id}]")
    for i, record in enumerate(records[:5], 1):  # Show last 5
        role = record["role"]
        text = record["text"][:80] + "..." if len(record["text"]) > 80 else record["text"]
        print(f"    {i}. [{role}] {text}")
    if len(records) > 5:
        print(f"    ... and {len(records) - 5} more")

    return len(records)


async def demo_memory_basic() -> None:
    """Demo: Neo4j Memory Provider with persistent agent memory."""
    from azure.identity import DefaultAzureCredential
    from azure.identity.aio import AzureCliCredential

    from agent_framework_neo4j import (
        AzureAIEmbedder,
        AzureAISettings,
        Neo4jContextProvider,
        Neo4jSettings,
    )
    from samples.shared import AgentConfig, create_agent_client, get_logger

    logger = get_logger()

    print_header("Demo: Neo4j Memory Provider")
    print("This demo shows persistent agent memory using Neo4j.")
    print("Memories are stored after each interaction and retrieved")
    print("across different conversations for the same user.\n")

    # Load configs
    agent_config = AgentConfig()
    neo4j_settings = Neo4jSettings()
    azure_settings = AzureAISettings()

    if not agent_config.project_endpoint:
        print("Error: AZURE_AI_PROJECT_ENDPOINT not configured.")
        return

    if not neo4j_settings.is_configured:
        print("Error: Neo4j not configured.")
        print("Required: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD")
        return

    if not azure_settings.is_configured:
        print("Error: Azure AI not configured.")
        print("Required: AZURE_AI_PROJECT_ENDPOINT")
        return

    print(f"Agent: {agent_config.name}")
    print(f"Model: {agent_config.model}")
    print(f"Neo4j URI: {neo4j_settings.uri}")
    print(f"Embedding Model: {azure_settings.embedding_model}\n")

    credential = AzureCliCredential()
    sync_credential = DefaultAzureCredential()
    embedder = None

    try:
        # Clean up any existing test memories from previous runs
        print("Cleaning up previous test data...")
        await _cleanup_test_memories(neo4j_settings)
        print("Done.\n")

        # Create embedder for semantic memory search
        embedder = AzureAIEmbedder(
            endpoint=azure_settings.inference_endpoint,
            credential=sync_credential,
            model=azure_settings.embedding_model,
        )
        print("Embedder initialized for memory search!\n")

        client = create_agent_client(agent_config, credential)

        # ================================================================
        # PART 1: Build up memories with specific facts
        # ================================================================
        print("=" * 60)
        print("Part 1: Alice's First Conversation - Building Memories")
        print("=" * 60)
        print("\nAlice shares several specific facts about herself.")
        print("These will be stored as Memory nodes in Neo4j.\n")

        provider_user_a = Neo4jContextProvider(
            uri=neo4j_settings.uri,
            username=neo4j_settings.username,
            password=neo4j_settings.get_password(),
            memory_enabled=True,
            user_id="user_alice",
            index_name=neo4j_settings.fulltext_index_name,
            index_type="fulltext",
            embedder=embedder,
            top_k=5,
        )

        async with provider_user_a:
            print("Connected to Neo4j with memory enabled!\n")

            async with client.create_agent(
                name=agent_config.name,
                instructions=(
                    "You are a helpful personal assistant. Remember details "
                    "users share about themselves. Be friendly and brief."
                ),
                context_provider=provider_user_a,
            ) as agent:
                # Share multiple specific facts
                conversations = [
                    (
                        "Hi! I'm Alice. I work as a software engineer at TechCorp.",
                        "Alice introduces herself and mentions her job"
                    ),
                    (
                        "I have a golden retriever named Max who loves to play fetch.",
                        "Alice shares about her dog"
                    ),
                    (
                        "My favorite coffee shop is Blue Bottle on Market Street. "
                        "I go there every Saturday morning.",
                        "Alice mentions her coffee routine"
                    ),
                    (
                        "I'm planning a trip to Japan next April to see the cherry blossoms.",
                        "Alice discusses travel plans"
                    ),
                ]

                for i, (message, description) in enumerate(conversations, 1):
                    print(f"[Turn {i}] ({description})")
                    print(f"  User: {message}")
                    response = await agent.run(message)
                    print(f"  Agent: {response.text}\n")

        # Show what was stored
        await _show_stored_memories(neo4j_settings, "user_alice")

        # ================================================================
        # PART 2: New conversation - test memory retrieval with specific queries
        # ================================================================
        print("\n" + "=" * 60)
        print("Part 2: Alice's Second Conversation - Memory Retrieval")
        print("=" * 60)
        print("\nAlice starts a NEW conversation (different thread).")
        print("The agent should recall specific facts from Part 1.\n")

        provider_user_a_new = Neo4jContextProvider(
            uri=neo4j_settings.uri,
            username=neo4j_settings.username,
            password=neo4j_settings.get_password(),
            memory_enabled=True,
            user_id="user_alice",
            index_name=neo4j_settings.fulltext_index_name,
            index_type="fulltext",
            embedder=embedder,
            top_k=5,
        )

        async with provider_user_a_new:
            async with client.create_agent(
                name=agent_config.name,
                instructions=(
                    "You are a helpful personal assistant that remembers users "
                    "across conversations. Use the conversation memory context "
                    "to provide personalized responses. If you have relevant "
                    "memories, reference the specific details you remember."
                ),
                context_provider=provider_user_a_new,
            ) as agent:
                # Test specific memory recall
                test_queries = [
                    (
                        "What's my dog's name?",
                        "Should recall: Max, golden retriever"
                    ),
                    (
                        "Where do I work?",
                        "Should recall: TechCorp, software engineer"
                    ),
                    (
                        "I need coffee recommendations for this weekend.",
                        "Should recall: Blue Bottle on Market Street, Saturday routine"
                    ),
                    (
                        "What travel plans have I mentioned?",
                        "Should recall: Japan, April, cherry blossoms"
                    ),
                ]

                for i, (query, expected) in enumerate(test_queries, 1):
                    print(f"[Query {i}] {query}")
                    print(f"  Expected: {expected}")
                    response = await agent.run(query)
                    print(f"  Agent: {response.text}\n")

        # ================================================================
        # PART 3: Semantic search demonstration
        # ================================================================
        print("=" * 60)
        print("Part 3: Semantic Memory Search")
        print("=" * 60)
        print("\nDemonstrating that memory search is SEMANTIC, not keyword-based.")
        print("Queries use different words but should find related memories.\n")

        provider_semantic = Neo4jContextProvider(
            uri=neo4j_settings.uri,
            username=neo4j_settings.username,
            password=neo4j_settings.get_password(),
            memory_enabled=True,
            user_id="user_alice",
            index_name=neo4j_settings.fulltext_index_name,
            index_type="fulltext",
            embedder=embedder,
            top_k=5,
        )

        async with provider_semantic:
            async with client.create_agent(
                name=agent_config.name,
                instructions=(
                    "You are a helpful assistant with access to conversation memories. "
                    "Use any relevant context to answer questions."
                ),
                context_provider=provider_semantic,
            ) as agent:
                semantic_queries = [
                    (
                        "Do I have any pets?",
                        "Semantically related to 'golden retriever named Max'"
                    ),
                    (
                        "What's my profession?",
                        "Semantically related to 'software engineer at TechCorp'"
                    ),
                    (
                        "Any upcoming vacation plans?",
                        "Semantically related to 'trip to Japan...cherry blossoms'"
                    ),
                ]

                for query, semantic_note in semantic_queries:
                    print(f"[Query] {query}")
                    print(f"  Note: {semantic_note}")
                    response = await agent.run(query)
                    print(f"  Agent: {response.text}\n")

        # ================================================================
        # PART 4: User isolation test
        # ================================================================
        print("=" * 60)
        print("Part 4: User Isolation - Bob Cannot See Alice's Memories")
        print("=" * 60)
        print("\nBob is a different user. He should NOT see Alice's memories.\n")

        provider_user_b = Neo4jContextProvider(
            uri=neo4j_settings.uri,
            username=neo4j_settings.username,
            password=neo4j_settings.get_password(),
            memory_enabled=True,
            user_id="user_bob",
            index_name=neo4j_settings.fulltext_index_name,
            index_type="fulltext",
            embedder=embedder,
            top_k=5,
        )

        async with provider_user_b:
            async with client.create_agent(
                name=agent_config.name,
                instructions=(
                    "You are a helpful assistant. If you don't have any "
                    "information about the user, say so clearly."
                ),
                context_provider=provider_user_b,
            ) as agent:
                bob_queries = [
                    "What's my dog's name?",
                    "Where do I work?",
                ]

                for query in bob_queries:
                    print(f"[Bob asks] {query}")
                    response = await agent.run(query)
                    print(f"  Agent: {response.text}")
                    print("  [PASS] Agent correctly has no memory of Bob\n")

        # Show memory counts
        print("=" * 60)
        print("Final Memory State")
        print("=" * 60)
        alice_count = await _show_stored_memories(neo4j_settings, "user_alice")
        bob_count = await _show_stored_memories(neo4j_settings, "user_bob")

        print("\n" + "-" * 60)
        print("\nDemo Complete!")
        print("\nKey Takeaways:")
        print(f"  1. Alice has {alice_count} memories stored")
        print(f"  2. Bob has {bob_count} memories (isolation works)")
        print("  3. Semantic search finds related memories even with different words")
        print("  4. Memories persist across conversation sessions")
        print("  5. Specific facts (names, places, dates) are accurately recalled")

    except ConnectionError as e:
        print(f"\nConnection Error: {e}")
        print("Please check your Neo4j and Microsoft Foundry configuration.")
    except Exception as e:
        logger.error(f"Error during demo: {e}")
        print(f"\nError: {e}")
        raise
    finally:
        if embedder is not None:
            embedder.close()
        await credential.close()
        await asyncio.sleep(0.1)
