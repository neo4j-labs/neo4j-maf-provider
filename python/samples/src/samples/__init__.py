"""
Neo4j MAF Provider Sample Applications.

This package contains demo applications showcasing the agent-framework-neo4j library.
"""

from .aircraft_domain import (
    demo_aircraft_flight_delays,
    demo_aircraft_maintenance_search,
    demo_component_health,
)
from .basic_fulltext import demo_azure_thread_memory, demo_context_provider_basic
from .graph_enriched import demo_context_provider_graph_enriched
from .memory_basic import demo_memory_basic
from .vector_search import demo_context_provider_vector, demo_semantic_search

__all__ = [
    "demo_context_provider_basic",
    "demo_azure_thread_memory",
    "demo_context_provider_vector",
    "demo_semantic_search",
    "demo_context_provider_graph_enriched",
    "demo_aircraft_maintenance_search",
    "demo_aircraft_flight_delays",
    "demo_component_health",
    "demo_memory_basic",
]
