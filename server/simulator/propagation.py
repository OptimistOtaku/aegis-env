from server.simulator.cluster import ClusterGraph
from typing import Set

class PropagationEngine:
    """Handles the blast radius expansion per tick."""
    
    def __init__(self, incident_type: str, initial_compromised: list[str]):
        self.incident_type = incident_type
        # Maintain a set of currently compromised component IDs
        self.blast_radius: Set[str] = set(initial_compromised)
        self.user_impact_score = 0.0

    def get_user_impact(self) -> float:
        return min(1.0, self.user_impact_score)

    def get_blast_radius(self) -> list[str]:
        return list(self.blast_radius)

    def tick(self, cluster: ClusterGraph) -> int:
        """
        Advances the simulation by 1 tick.
        Propagates the incident down edges if incident is not contained.
        Returns the delta in blast radius size.
        """
        new_infected = set()
        
        # Propagation phase
        for comp_id in list(self.blast_radius):
            comp = cluster.get_component(comp_id)
            # If origin is isolated/contained/offline/nominal, it doesn't spread further
            if not comp or comp.safety_status in ("contained", "offline", "nominal"):
                continue
            
            # Spread to downstream connections
            for downstream_id in comp.connections:
                downstream = cluster.get_component(downstream_id)
                if downstream and downstream.safety_status not in ("contained", "offline", "compromised"):
                    # Incident spreads deterministically
                    downstream.safety_status = "compromised"
                    downstream.health_score = max(0.0, downstream.health_score - 0.2)
                    new_infected.add(downstream_id)
        
        prev_radius = len(self.blast_radius)
        self.blast_radius.update(new_infected)
        
        # Cleanup blast radius to only include genuinely compromised nodes
        active_blast_radius = set()
        for comp_id in self.blast_radius:
            comp = cluster.get_component(comp_id)
            if comp and comp.safety_status == "compromised":
                active_blast_radius.add(comp_id)
        
        delta = len(active_blast_radius) - prev_radius
        self.blast_radius = active_blast_radius
        
        # Impact phase
        if len(self.blast_radius) > 0:
            self.user_impact_score += 0.05
            
        for comp_id in self.blast_radius:
            comp = cluster.get_component(comp_id)
            if comp and comp.component_type == "downstream_app":
                self.user_impact_score += 0.1
                
        self.user_impact_score = min(1.0, self.user_impact_score)
        
        return delta

    def mark_fixed(self, component_id: str, cluster: ClusterGraph):
        comp = cluster.get_component(component_id)
        if comp:
            comp.safety_status = "nominal"
            comp.health_score = 1.0
            if component_id in self.blast_radius:
                self.blast_radius.remove(component_id)
