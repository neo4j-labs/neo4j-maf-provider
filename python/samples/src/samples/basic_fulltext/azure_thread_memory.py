"""
Demo: Azure thread-based conversation memory.

This sample demonstrates how the Microsoft Agent Framework maintains
conversation context using Azure-managed threads (not Neo4j).
"""

from __future__ import annotations

from samples.shared import print_header


async def demo_azure_thread_memory() -> None:
    """Demo: Azure thread-based conversation memory."""
    from azure.identity.aio import AzureCliCredential

    from samples.shared import AgentConfig, create_agent_client, create_agent_context, get_logger

    logger = get_logger()

    print_header("Demo: Azure Thread Memory")
    print("This demo shows how Azure threads maintain conversation context.\n")
    print("Note: This uses Azure's built-in thread memory, not Neo4j.\n")

    config = AgentConfig()

    if not config.project_endpoint:
        print("Error: AZURE_AI_PROJECT_ENDPOINT not configured.")
        print("Please ensure your .env file is set up correctly.")
        return

    print(f"Agent: {config.name}")
    print(f"Model: {config.model}")
    print(f"Endpoint: {config.project_endpoint[:50]}...\n")

    credential = AzureCliCredential()

    try:
        client = create_agent_client(config, credential)

        async with create_agent_context(client, config) as agent:
            print("Agent created successfully!\n")

            # Create a thread to maintain conversation memory
            thread = agent.get_new_thread()
            print("Conversation thread created.\n")
            print("-" * 50)

            # First message
            print("\n[Turn 1] User: Hello! My name is Wayne and I love horses.")
            response = await agent.run(
                "Hello! My name is Wayne and I love horses.", thread=thread
            )
            print(f"[Turn 1] Agent: {response.text}\n")

            # Second message - test memory
            print("-" * 50)
            print("\n[Turn 2] User: What is my name and what do I enjoy?")
            response = await agent.run(
                "What is my name and what do I enjoy?", thread=thread
            )
            print(f"[Turn 2] Agent: {response.text}\n")

            # Third message - continue conversation
            print("-" * 50)
            print("\n[Turn 3] User: Can you suggest recommendations for my passion?")
            response = await agent.run(
                "Can you suggest recommendations for my passion?", thread=thread
            )
            print(f"[Turn 3] Agent: {response.text}\n")

            print("-" * 50)
            print(
                "\nDemo complete! The agent successfully remembered context across turns."
            )

    except Exception as e:
        logger.error(f"Error during demo: {e}")
        print(f"\nError: {e}")
        raise
    finally:
        await credential.close()
