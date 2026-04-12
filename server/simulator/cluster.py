import copy
from typing import Dict, List, Optional
from server.models import ComponentState

class ClusterGraph:
    def __init__(self, components: List[ComponentState]):
        self.components: Dict[str, ComponentState] = {}
        self.original_connections: Dict[str, List[str]] = {}
        
        for comp in components:
            self.add_component(comp)

    def add_component(self, comp: ComponentState):
        # We store copies to protect the original graph states passed in
        comp_copy = comp.model_copy(deep=True)
        self.components[comp_copy.component_id] = comp_copy
        self.original_connections[comp_copy.component_id] = list(comp_copy.connections)

    def get_component(self, component_id: str) -> Optional[ComponentState]:
        return self.components.get(component_id)

    def isolate_component(self, component_id: str):
        """Removes all incoming and outgoing connections logically."""
        comp = self.get_component(component_id)
        if comp:
            comp.connections = []
            comp.safety_status = "offline"  # Mark offline/contained computationally
            
            # Remove incoming connections from other components
            for other in self.components.values():
                if component_id in other.connections:
                    other.connections.remove(component_id)

    def restore_component(self, component_id: str):
        """Restores connections to original state."""
        comp = self.get_component(component_id)
        if comp:
            comp.connections = list(self.original_connections.get(component_id, []))
            
            # Restore incoming connections
            for other_id, orig_conns in self.original_connections.items():
                if component_id in orig_conns:
                    other = self.components.get(other_id)
                    if other and component_id not in other.connections:
                        other.connections.append(component_id)
            
            # If it was offline due to isolation, we restore it to contained or nominal conditionally.
            # Usually restoring implies we patched it or we're just rolling back isolation.
            if comp.safety_status == "offline" or comp.safety_status == "contained":
                comp.safety_status = "nominal"
                comp.health_score = 1.0

    def get_state(self) -> List[ComponentState]:
        return [c.model_copy(deep=True) for c in self.components.values()]
