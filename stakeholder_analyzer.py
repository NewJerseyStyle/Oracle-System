import json
import re
from typing import Dict, Any, List, Optional, Tuple
from openai import OpenAI
import config
from local_research import LocalResearchClient
from game_theory_api import GameTheoryClient


class StakeholderAnalyzer:
    def __init__(
        self,
        rapidapi_key: str = None,
        openrouter_key: str = None,
        openrouter_model: str = None,
        ldr_url: str = None
    ):
        self.game_theory = GameTheoryClient(api_key=rapidapi_key)
        self.local_research = LocalResearchClient(base_url=ldr_url)
        
        self.llm_client = OpenAI(
            api_key=openrouter_key or config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL
        )
        self.model = openrouter_model or config.OPENROUTER_MODEL

    def extract_players_with_llm(self, research_text: str, event_context: str) -> List[Dict[str, Any]]:
        """
        Use LLM to extract and quantify stakeholder data from research results.
        
        Args:
            research_text: The raw research output
            event_context: The original event query for context
            
        Returns:
            List of player dicts with position, salience, clout, resolve
        """
        prompt = f"""
Analyze the following research text about stakeholders in: "{event_context}"

Extract each stakeholder and rate them on these scales:

1. **position** (0-100): Their stance on the issue
   - 0 = Strongly against conflict escalation / pro-peace / pro-negotiation
   - 50 = Neutral / ambivalent / seeking balance
   - 100 = Strongly supports escalation / military action / hardline position

2. **salience** (0-100): How important this issue is to them
   - 0 = Low priority, many other concerns
   - 100 = Critical priority, central to their interests

3. **clout** (0.1-10.0): Their relative influence/power
   - 0.1 = Minimal influence
   - 1.0 = Average influence
   - 10.0 = Dominant power

4. **resolve** (0-100): How firm/unwavering is their position
   - 0 = Very flexible, easily swayed
   - 100 = Absolutely firm, will not compromise

Return ONLY a JSON array with this exact format:
[
  {{
    "id": "Stakeholder Name",
    "position": 85,
    "salience": 90,
    "clout": 2.5,
    "resolve": 75,
    "rationale": "Brief explanation of ratings"
  }}
]

Research text:
{research_text[:8000]}
"""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a geopolitical analyst. Extract stakeholder data as JSON only, no markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            content = response.choices[0].message.content.strip()
            
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                players = json.loads(json_match.group())
                return self._validate_players(players)
            
            return []
        except Exception as e:
            print(f"LLM extraction error: {e}")
            return []

    def _validate_players(self, players: List[Dict]) -> List[Dict[str, Any]]:
        """Validate and sanitize player data."""
        validated = []
        for p in players:
            try:
                validated.append({
                    "id": str(p.get("id", "Unknown"))[:50],
                    "position": max(0, min(100, float(p.get("position", 50)))),
                    "salience": max(0, min(100, float(p.get("salience", 50)))),
                    "clout": max(0.1, min(10.0, float(p.get("clout", 1.0)))),
                    "resolve": max(0, min(100, float(p.get("resolve", 50)))),
                    "rationale": str(p.get("rationale", ""))[:200]
                })
            except (ValueError, TypeError):
                continue
        return validated

    def calculate_war_risk(self, equilibrium_position: float, confidence: float = 1.0) -> Dict[str, Any]:
        """
        Convert equilibrium position to war risk assessment.
        
        Args:
            equilibrium_position: The predicted outcome (0-100)
            confidence: Confidence level from Monte Carlo analysis
            
        Returns:
            Risk assessment dict
        """
        if equilibrium_position < 30:
            risk_level = "LOW"
            description = "Diplomatic solution likely. Stakeholders favor negotiation."
            probability = "10-25%"
        elif equilibrium_position < 50:
            risk_level = "MODERATE"
            description = "Tensions present but negotiations ongoing. Mixed signals."
            probability = "25-45%"
        elif equilibrium_position < 70:
            risk_level = "ELEVATED"
            description = "Significant risk of confrontation. Limited diplomatic progress."
            probability = "45-65%"
        else:
            risk_level = "HIGH"
            description = "Conflict probable. Hardliners dominate decision-making."
            probability = "65-85%"

        return {
            "risk_level": risk_level,
            "equilibrium_position": round(equilibrium_position, 1),
            "confidence": round(confidence, 2),
            "description": description,
            "probability_range": probability
        }

    def analyze_event(
        self,
        event_query: str,
        use_research: bool = True,
        existing_players: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Main analysis pipeline: research -> extract -> analyze -> lobby-ability.
        
        Args:
            event_query: The event/conflict to analyze
            use_research: Whether to use local research (False = use existing_players)
            existing_players: Pre-defined players (skips research if provided)
            
        Returns:
            Complete analysis results
        """
        results = {
            "event": event_query,
            "players": [],
            "equilibrium": None,
            "war_risk": None,
            "lobbyability": [],
            "research_summary": None,
            "errors": []
        }

        if use_research and not existing_players:
            research = self.local_research.search_stakeholders(event_query)
            
            if "error" in research:
                results["errors"].append(f"Research error: {research['error']}")
                if not existing_players:
                    return results
            
            results["research_summary"] = research.get("summary", "")
            
            research_text = research.get("summary", "") + "\n" + "\n".join(
                source.get("content", "") for source in research.get("sources", [])
            )
            
            players = self.extract_players_with_llm(research_text, event_query)
            
            if not players:
                results["errors"].append("LLM failed to extract players from research")
                return results
            
            results["players"] = players
        else:
            results["players"] = existing_players or []

        if not results["players"]:
            results["errors"].append("No players available for analysis")
            return results

        try:
            analysis = self.game_theory.run_analysis(results["players"])
            results["equilibrium"] = analysis
            
            eq_position = analysis.get("simple_predictions", {}).get("equilibrium_position", 50)
            confidence = analysis.get("monte_carlo_analysis", {}).get("confidence", 1.0)
            results["war_risk"] = self.calculate_war_risk(eq_position, confidence)
            
        except Exception as e:
            results["errors"].append(f"Game theory analysis error: {str(e)}")
            return results

        try:
            target_outcome = 30.0
            lobbyability = self.game_theory.find_lobbyable_players(
                results["players"],
                desired_outcome=target_outcome
            )
            results["lobbyability"] = lobbyability
        except Exception as e:
            results["errors"].append(f"Lobbyability analysis error: {str(e)}")

        return results

    def get_recommendations(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate actionable recommendations based on analysis.
        
        Args:
            analysis_results: Results from analyze_event()
            
        Returns:
            List of recommendation dicts
        """
        recommendations = []
        
        if not analysis_results.get("lobbyability"):
            return recommendations

        top_lobbyable = analysis_results["lobbyability"][:3]
        
        for i, player in enumerate(top_lobbyable, 1):
            if player.get("lobby_score", 0) > 0:
                recommendations.append({
                    "priority": i,
                    "target": player["player_id"],
                    "lobby_score": round(player.get("lobby_score", 0), 2),
                    "current_stance": player.get("current_position", 50),
                    "flexibility": "High" if player.get("current_resolve", 50) < 40 else 
                                   "Medium" if player.get("current_resolve", 50) < 70 else "Low",
                    "influence": "High" if player.get("current_clout", 1) > 2 else
                                 "Medium" if player.get("current_clout", 1) > 1 else "Low",
                    "actions": player.get("recommended_actions", ["Engage in diplomatic dialogue"]),
                    "rationale": f"Targeting this player could shift equilibrium by ~{round(player.get('improvement_potential', 0), 1)} points"
                })

        return recommendations


def analyze_event(
    event_query: str,
    rapidapi_key: str = None,
    openrouter_key: str = None,
    use_research: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for one-shot analysis.
    
    Args:
        event_query: Event to analyze
        rapidapi_key: RapidAPI key for game theory
        openrouter_key: OpenRouter key for LLM
        use_research: Whether to use local research
        
    Returns:
        Analysis results
    """
    analyzer = StakeholderAnalyzer(
        rapidapi_key=rapidapi_key,
        openrouter_key=openrouter_key
    )
    return analyzer.analyze_event(event_query, use_research=use_research)
