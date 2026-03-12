import requests
from typing import List, Dict, Any, Optional
import config


class GameTheoryClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.RAPIDAPI_KEY
        self.base_url = config.GAME_THEORY_API_URL
        self.headers = {
            "Content-Type": "application/json",
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": config.GAME_THEORY_HOST
        }

    def run_analysis(self, players: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run Nash Equilibrium analysis on players.
        
        Args:
            players: List of player dicts with id, position, salience, clout, resolve
            
        Returns:
            Analysis results with predictions and confidence intervals
        """
        url = f"{self.base_url}/run_analysis"
        payload = {"players": players}
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def sensitivity_analysis(self, players: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Test prediction stability against parameter changes.
        
        Args:
            players: List of player dicts
            
        Returns:
            Sensitivity metrics for each player
        """
        url = f"{self.base_url}/sensitivity_analysis"
        payload = {"players": players}
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def optimize_strategy(
        self, 
        players: List[Dict[str, Any]], 
        target_player_id: str, 
        target_outcome: float
    ) -> Dict[str, Any]:
        """
        Find optimal strategy for a target player to achieve desired outcome.
        
        Args:
            players: List of player dicts
            target_player_id: ID of player to optimize for
            target_outcome: Desired equilibrium position (0-100)
            
        Returns:
            Recommended actions and expected improvement
        """
        url = f"{self.base_url}/optimize_strategy"
        payload = {
            "players": players,
            "target_player_id": target_player_id,
            "target_outcome": target_outcome
        }
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def run_strategic_simulation(
        self,
        players: List[Dict[str, Any]],
        actions: Optional[List[str]] = None,
        interventions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Test specific strategies and interventions.
        
        Args:
            players: List of player dicts
            actions: Strategy types (AGGRESSIVE, CONCILIATORY, PATIENT, URGENT, DECEPTIVE, TRANSPARENT)
            interventions: Intervention types (NEW_PLAYER, REMOVE_PLAYER, COALITION_FORMATION, etc.)
            
        Returns:
            Simulation results showing outcome changes
        """
        url = f"{self.base_url}/run_strategic_simulation"
        payload = {
            "players": players,
            "actions": actions or [],
            "interventions": interventions or []
        }
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def find_lobbyable_players(
        self, 
        players: List[Dict[str, Any]], 
        desired_outcome: float = 30.0
    ) -> List[Dict[str, Any]]:
        """
        Identify players whose change would most impact the outcome.
        
        Args:
            players: List of player dicts
            desired_outcome: Target equilibrium (lower = less conflict)
            
        Returns:
            List of players ranked by lobby-ability
        """
        results = []
        
        for player in players:
            try:
                optimization = self.optimize_strategy(
                    players, 
                    player["id"], 
                    desired_outcome
                )
                
                improvement = optimization.get("improvement", 0)
                
                results.append({
                    "player_id": player["id"],
                    "current_position": player["position"],
                    "current_resolve": player["resolve"],
                    "current_clout": player["clout"],
                    "improvement_potential": improvement,
                    "recommended_actions": optimization.get("recommended_actions", []),
                    "lobby_score": improvement * player["clout"] / (player["resolve"] + 1)
                })
            except Exception as e:
                results.append({
                    "player_id": player["id"],
                    "error": str(e),
                    "lobby_score": 0
                })
        
        results.sort(key=lambda x: x.get("lobby_score", 0), reverse=True)
        return results
