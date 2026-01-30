"""Aircraft domain samples."""

from .component_health import demo_component_health
from .flight_delays import demo_aircraft_flight_delays
from .maintenance_search import demo_aircraft_maintenance_search

__all__ = [
    "demo_aircraft_maintenance_search",
    "demo_aircraft_flight_delays",
    "demo_component_health",
]
