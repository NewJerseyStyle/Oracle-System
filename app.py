"""
Gradio Web Interface for Stakeholder Analysis & Game Theory Predictions

Run with: python app.py
Access at: http://localhost:7860
"""

import gradio as gr
import json
from typing import Dict, Any, List, Tuple, Optional

import config
from stakeholder_analyzer import StakeholderAnalyzer


EXAMPLE_QUERIES = [
    "Iran war stakeholders and decision makers",
    "Gaza conflict key players and their positions",
    "Taiwan Strait tensions stakeholders",
    "Ukraine war negotiation parties",
    "South China Sea dispute actors"
]

MODEL_OPTIONS = [
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-haiku",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-chat"
]


def format_stakeholders_table(players: List[Dict]) -> str:
    """Format players as a markdown table."""
    if not players:
        return "No stakeholders identified."
    
    header = "| Stakeholder | Position | Salience | Clout | Resolve |\n"
    header += "|-------------|----------|----------|-------|----------|\n"
    
    rows = []
    for p in players:
        position_emoji = "🔴" if p["position"] > 66 else "🟡" if p["position"] > 33 else "🟢"
        resolve_emoji = "💪" if p["resolve"] > 66 else "🔄" if p["resolve"] > 33 else "↔️"
        
        rows.append(
            f"| {p['id']} | {position_emoji} {p['position']:.0f} | "
            f"{p['salience']:.0f} | {p['clout']:.1f} | {resolve_emoji} {p['resolve']:.0f} |"
        )
    
    return header + "\n".join(rows)


def format_war_risk(war_risk: Dict) -> str:
    """Format war risk assessment as markdown."""
    if not war_risk:
        return "Risk assessment unavailable."
    
    level = war_risk.get("risk_level", "UNKNOWN")
    emoji = {"LOW": "🟢", "MODERATE": "🟡", "ELEVATED": "🟠", "HIGH": "🔴"}.get(level, "⚪")
    
    return f"""
### {emoji} Risk Level: {level}

| Metric | Value |
|--------|-------|
| **Probability Range** | {war_risk.get('probability_range', 'N/A')} |
| **Equilibrium Position** | {war_risk.get('equilibrium_position', 'N/A')}/100 |
| **Confidence** | {war_risk.get('confidence', 'N/A'):.2f} |

**Assessment:** {war_risk.get('description', 'No description available.')}
"""


def format_lobbyability(lobbyability: List[Dict], players: List[Dict]) -> str:
    """Format lobby-ability ranking as markdown."""
    if not lobbyability:
        return "Lobby-ability analysis unavailable."
    
    header = "| Rank | Player | Lobby Score | Position | Flexibility | Influence |\n"
    header += "|------|--------|-------------|----------|-------------|----------|\n"
    
    rows = []
    for i, p in enumerate(lobbyability[:5], 1):
        resolve = p.get("current_resolve", 50)
        clout = p.get("current_clout", 1)
        
        flex = "🟢 High" if resolve < 40 else "🟡 Medium" if resolve < 70 else "🔴 Low"
        inf = "⬆️ High" if clout > 2 else "➡️ Medium" if clout > 1 else "⬇️ Low"
        
        rows.append(
            f"| {i} | **{p['player_id']}** | {p.get('lobby_score', 0):.2f} | "
            f"{p.get('current_position', 50):.0f} | {flex} | {inf} |"
        )
    
    output = header + "\n".join(rows)
    
    if lobbyability:
        top = lobbyability[0]
        output += f"\n\n### 🎯 Top Target: {top['player_id']}\n"
        output += f"**Potential Impact:** {top.get('improvement_potential', 0):.1f} points\n\n"
        
        if top.get("recommended_actions"):
            output += "**Recommended Actions:**\n"
            for action in top["recommended_actions"][:3]:
                output += f"- {action}\n"
    
    return output


def run_analysis(
    event_query: str,
    rapidapi_key: str,
    openrouter_key: str,
    model: str,
    use_research: bool,
    progress=gr.Progress()
) -> Tuple[str, str, str, str, str]:
    """
    Run the full analysis pipeline.
    
    Returns:
        Tuple of (status, stakeholders_md, war_risk_md, lobbyability_md, raw_json)
    """
    if not event_query.strip():
        return "Please enter an event query.", "", "", "", ""
    
    if not rapidapi_key.strip():
        return "Please enter your RapidAPI key.", "", "", "", ""
    
    if not openrouter_key.strip():
        return "Please enter your OpenRouter API key.", "", "", "", ""
    
    try:
        progress(0.1, desc="Initializing analyzer...")
        
        analyzer = StakeholderAnalyzer(
            rapidapi_key=rapidapi_key,
            openrouter_key=openrouter_key,
            openrouter_model=model
        )
        
        progress(0.2, desc="Researching stakeholders..." if use_research else "Processing...")
        
        results = analyzer.analyze_event(
            event_query=event_query,
            use_research=use_research
        )
        
        progress(0.7, desc="Formatting results...")
        
        if results.get("errors"):
            status = "⚠️ Analysis completed with warnings:\n" + "\n".join(f"- {e}" for e in results["errors"])
        else:
            status = "✅ Analysis completed successfully!"
        
        stakeholders_md = format_stakeholders_table(results.get("players", []))
        war_risk_md = format_war_risk(results.get("war_risk", {}))
        lobbyability_md = format_lobbyability(
            results.get("lobbyability", []),
            results.get("players", [])
        )
        
        raw_json = json.dumps(results, indent=2, default=str)
        
        progress(1.0, desc="Done!")
        
        return status, stakeholders_md, war_risk_md, lobbyability_md, raw_json
        
    except Exception as e:
        return f"❌ Error: {str(e)}", "", "", "", ""


def create_demo():
    """Create the Gradio demo interface."""
    
    with gr.Blocks(
        title="Stakeholder Analysis & Game Theory Predictor",
        theme=gr.themes.Soft(),
        css="""
        .status-box { padding: 10px; border-radius: 8px; }
        .tab-nav button { font-weight: bold; }
        """
    ) as demo:
        
        gr.Markdown("""
        # 🎯 Stakeholder Analysis & Game Theory Predictor
        
        Analyze geopolitical events to identify stakeholders, predict outcomes using Nash Equilibrium,
        and find the most "lobby-able" players to influence toward peace.
        
        **Powered by:** Local Deep Research + OpenRouter LLMs + Game Theory Nash Equilibrium API
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                event_input = gr.Textbox(
                    label="Event / Conflict Query",
                    placeholder="e.g., Iran war stakeholders, Gaza conflict decision makers",
                    lines=2,
                    info="Describe the geopolitical event to analyze"
                )
                
                example_buttons = gr.Examples(
                    examples=EXAMPLE_QUERIES,
                    inputs=event_input,
                    label="Example Queries"
                )
            
            with gr.Column(scale=1):
                rapidapi_key = gr.Textbox(
                    label="RapidAPI Key",
                    type="password",
                    placeholder="Enter your RapidAPI key",
                    info="Get from: rapidapi.com"
                )
                
                openrouter_key = gr.Textbox(
                    label="OpenRouter API Key",
                    type="password",
                    placeholder="Enter your OpenRouter key",
                    info="Get from: openrouter.ai"
                )
                
                model_dropdown = gr.Dropdown(
                    choices=MODEL_OPTIONS,
                    value="anthropic/claude-3.5-sonnet",
                    label="LLM Model",
                    info="Select model for stakeholder extraction"
                )
        
        with gr.Row():
            use_research = gr.Checkbox(
                value=True,
                label="Use Local Deep Research",
                info="Uncheck if LDR is not running (requires manual player input)"
            )
            
            analyze_btn = gr.Button(
                "🔍 Analyze",
                variant="primary",
                size="lg"
            )
        
        status_output = gr.Textbox(
            label="Status",
            lines=2,
            interactive=False
        )
        
        with gr.Tabs():
            with gr.TabItem("👥 Stakeholders"):
                stakeholders_output = gr.Markdown(
                    label="Identified Stakeholders",
                    value="Results will appear here after analysis."
                )
            
            with gr.TabItem("⚠️ War Risk"):
                war_risk_output = gr.Markdown(
                    label="War Risk Assessment",
                    value="Risk assessment will appear here."
                )
            
            with gr.TabItem("🎯 Lobby-ability"):
                lobbyability_output = gr.Markdown(
                    label="Lobby-ability Ranking",
                    value="Rankings will appear here."
                )
            
            with gr.TabItem("📋 Raw JSON"):
                raw_output = gr.Code(
                    label="Raw Analysis Data",
                    language="json",
                    value="{}"
                )
        
        gr.Markdown("""
        ---
        ### 📋 Setup Instructions
        
        1. **Start Local Deep Research:** 
           ```bash
           curl -O https://raw.githubusercontent.com/LearningCircuit/local-deep-research/main/docker-compose.yml
           MODEL=qwen3.5:4b docker compose up -d
           ```
        
        2. **Get API Keys:**
           - RapidAPI: https://rapidapi.com/worksourcewishes/api/game-theory-nash-equilibrium-predictor
           - OpenRouter: https://openrouter.ai/keys
        
        3. **Run this app:**
           ```bash
           pip install -r requirements.txt
           python app.py
           ```
        """)
        
        analyze_btn.click(
            fn=run_analysis,
            inputs=[event_input, rapidapi_key, openrouter_key, model_dropdown, use_research],
            outputs=[status_output, stakeholders_output, war_risk_output, lobbyability_output, raw_output]
        )
    
    return demo


if __name__ == "__main__":
    demo = create_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
