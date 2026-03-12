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
        
        self.openrouter_key = openrouter_key or config.OPENROUTER_API_KEY
        self.llm_client = None
        
        if self.openrouter_key:
            self.llm_client = OpenAI(
                api_key=self.openrouter_key,
                base_url=config.OPENROUTER_BASE_URL
            )
        self.model = openrouter_model or config.OPENROUTER_MODEL
    
    def has_llm(self) -> bool:
        """Check if OpenRouter LLM is available."""
        return self.llm_client is not None

    def enhance_query(self, user_query: str) -> Dict[str, str]:
        """
        Transform a simple user query into a comprehensive research query
        that collects information about all stakeholders and their influencers.
        
        Key principle: Break down organizations and governments into INDIVIDUAL
        decision-makers, not treat them as monolithic actors. This captures
        internal dynamics and early warning signals of policy shifts.
        
        Args:
            user_query: The user's original (potentially vague) query
            
        Returns:
            Dict with 'enhanced_query', 'focus_areas', and 'explanation'
        """
        fallback_result = {
            "original_query": user_query,
            "enhanced_query": f"""
Who are the SPECIFIC INDIVIDUAL decision-makers involved in: {user_query}

IMPORTANT: Do NOT list organizations as actors. Break down each institution into its key people:

GOVERNMENTS: Identify the head of state, foreign minister, defense minister, military chiefs, key legislators, and internal faction leaders. Note any public disagreements or divergent positions.

ORGANIZATIONS (UN, EU, NATO, etc.): Identify the Secretary General, key commissioners, and influential member state representatives. Track their individual positions.

NON-STATE ACTORS: Identify specific leaders, commanders, major donors, and ideological influencers.

For EACH individual, research:
1. Their official position and actual decision-making power
2. Their personal stance (may differ from official position)
3. Who influences them (advisors, family, donors, allies)
4. Recent statements or actions signaling position changes
5. Relationships with other individuals (alliances, rivalries)

Look for EARLY WARNING SIGNALS: individual statements that diverge from official positions, internal disagreements, personnel changes that signal policy shifts.
            """.strip(),
            "focus_areas": [
                "Individual decision-makers within governments (not governments as wholes)",
                "Internal factions and power struggles",
                "Personal positions vs official institutional positions",
                "Early warning signals from individuals",
                "Key people within international organizations",
                "Advisors and influence networks",
                "Cross-institutional alliances between individuals",
                "Recent personnel changes and what they signal"
            ],
            "stakeholder_categories": [
                "Heads of State/Government",
                "Foreign Ministers & Diplomats",
                "Military/Defense Chiefs",
                "Organization Leaders (UN, EU, NATO)",
                "Key Legislators",
                "Internal Faction Leaders",
                "Personal Advisors",
                "Business/Donor Networks"
            ],
            "explanation": "Broken down institutions into individual decision-makers to capture internal dynamics and early warning signals of policy shifts."
        }
        
        if not self.has_llm():
            return fallback_result
        
        prompt = f"""
You are helping a user research geopolitical stakeholders. Their query is: "{user_query}"

Transform this into a comprehensive research query. CRITICAL: Do NOT treat organizations or governments as single actors. Instead, identify the SPECIFIC INDIVIDUALS within them who make decisions.

Create a JSON response with:

1. "enhanced_query": A detailed research query (3-4 sentences) that asks about:

   **Governments** - Break down into individuals:
   - Head of state/government (President, PM, Supreme Leader)
   - Foreign affairs officials (Foreign Minister, Secretary of State)
   - Military/Defense leaders (Defense Minister, military chiefs)
   - Security/Intelligence chiefs
   - Key legislators and committee chairs
   - Internal factions and their leaders
   
   **International Organizations** (UN, EU, NATO, etc.) - Break down into:
   - Secretary General / President
   - Key commissioners, directors, or representatives
   - Member state representatives who influence decisions
   - Internal bureaus and their heads
   
   **Non-State Actors** (corporations, NGOs, militias, religious groups) - Break down into:
   - CEO, board members, major shareholders
   - Key commanders, regional leaders
   - Religious authorities, ideological leaders
   - Major donors and financiers
   
   **Influence Networks** for each individual:
   - Personal advisors, chiefs of staff
   - Family members with influence
   - Business partners, donors
   - Ideological allies, media allies
   - Early signs of position changes or internal disagreements

2. "focus_areas": An array of 6-10 specific aspects to research:
   - "Individual decision-makers within each government"
   - "Internal factions and power struggles"
   - "Personal positions vs official institutional positions"
   - "Early warning signals of policy shifts from individuals"
   - "Cross-cutting alliances between individuals across institutions"
   - "Advisors and influence networks for each key person"
   - "Public and private statements showing divergent views"
   - "Recent personnel changes signaling policy direction"

3. "explanation": Brief explanation (1-2 sentences)

4. "stakeholder_categories": Categories focused on individuals:
   e.g., ["Heads of State", "Foreign Ministers", "Military Chiefs", "Organization Leaders", 
   "Key Legislators", "Personal Advisors", "Business Elites", "Internal Opposition"]

Return ONLY valid JSON, no markdown formatting.
"""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a geopolitical research assistant. Return only valid JSON, no markdown."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1200
            )

            content = response.choices[0].message.content.strip()
            json_match = re.search(r'\{[\s\S]*\}', content)
            
            if json_match:
                result = json.loads(json_match.group())
                result["original_query"] = user_query
                return result
            
        except Exception as e:
            pass

        return {
            "original_query": user_query,
            "enhanced_query": f"""
Who are the SPECIFIC INDIVIDUAL decision-makers involved in: {user_query}

IMPORTANT: Do NOT list organizations as actors. Break down each institution into its key people:

GOVERNMENTS: Identify the head of state, foreign minister, defense minister, military chiefs, key legislators, and internal faction leaders. Note any public disagreements or divergent positions.

ORGANIZATIONS (UN, EU, NATO, etc.): Identify the Secretary General, key commissioners, and influential member state representatives. Track their individual positions.

NON-STATE ACTORS: Identify specific leaders, commanders, major donors, and ideological influencers.

For EACH individual, research:
1. Their official position and actual decision-making power
2. Their personal stance (may differ from official position)
3. Who influences them (advisors, family, donors, allies)
4. Recent statements or actions signaling position changes
5. Relationships with other individuals (alliances, rivalries)

Look for EARLY WARNING SIGNALS: individual statements that diverge from official positions, internal disagreements, personnel changes that signal policy shifts.
            """.strip(),
            "focus_areas": [
                "Individual decision-makers within governments (not governments as wholes)",
                "Internal factions and power struggles",
                "Personal positions vs official institutional positions",
                "Early warning signals from individuals",
                "Key people within international organizations",
                "Advisors and influence networks",
                "Cross-institutional alliances between individuals",
                "Recent personnel changes and what they signal"
            ],
            "stakeholder_categories": [
                "Heads of State/Government",
                "Foreign Ministers & Diplomats",
                "Military/Defense Chiefs",
                "Organization Leaders (UN, EU, NATO)",
                "Key Legislators",
                "Internal Faction Leaders",
                "Personal Advisors",
                "Business/Donor Networks"
            ],
            "explanation": "Broken down institutions into individual decision-makers to capture internal dynamics and early warning signals of policy shifts."
        }

    def extract_players_with_llm(self, research_text: str, event_context: str) -> List[Dict[str, Any]]:
        """
        Use LLM to extract and quantify stakeholder data from research results.
        
        Falls back to local-deep-research's Ollama if OpenRouter is not available.
        
        Args:
            research_text: The raw research output
            event_context: The original event query for context
            
        Returns:
            List of player dicts with position, salience, clout, resolve
        """
        if not self.has_llm():
            return self.local_research.extract_stakeholders_with_llm(research_text, event_context)
        
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
        existing_players: List[Dict] = None,
        enhance_query: bool = True
    ) -> Dict[str, Any]:
        """
        Main analysis pipeline: research -> extract -> analyze -> lobby-ability.
        
        Args:
            event_query: The event/conflict to analyze
            use_research: Whether to use local research (False = use existing_players)
            existing_players: Pre-defined players (skips research if provided)
            enhance_query: Whether to enhance simple queries into comprehensive ones
            
        Returns:
            Complete analysis results
        """
        results = {
            "event": event_query,
            "enhanced_query": None,
            "players": [],
            "equilibrium": None,
            "war_risk": None,
            "lobbyability": [],
            "research_summary": None,
            "errors": []
        }

        research_query = event_query
        
        if enhance_query and use_research and not existing_players:
            enhancement = self.enhance_query(event_query)
            results["enhanced_query"] = enhancement
            research_query = enhancement.get("enhanced_query", event_query)

        if use_research and not existing_players:
            research = self.local_research.search_stakeholders(research_query)
            
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
