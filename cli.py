#!/usr/bin/env python3
"""
CLI for Stakeholder Analysis & Game Theory Predictions

Usage:
    python cli.py --event "Iran war stakeholders"
    python cli.py -e "Gaza war decision makers" --api-key YOUR_KEY
"""

import argparse
import json
import sys
import os
from typing import Dict, Any

import config
from stakeholder_analyzer import StakeholderAnalyzer


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)


def print_table(headers: list, rows: list, widths: list = None):
    """Print a formatted table."""
    if not widths:
        widths = [max(len(str(row[i])) for row in [headers] + rows) + 2 for i in range(len(headers))]
    
    header_row = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    separator = "-+-".join("-" * w for w in widths)
    
    print(header_row)
    print(separator)
    
    for row in rows:
        print(" | ".join(str(v).ljust(w) for v, w in zip(row, widths)))


def display_results(results: Dict[str, Any], verbose: bool = False):
    """Display analysis results in formatted output."""
    
    if results.get("errors"):
        print_section("ERRORS")
        for error in results["errors"]:
            print(f"  ! {error}")
    
    if results.get("players"):
        print_section("STAKEHOLDERS")
        headers = ["Name", "Position", "Salience", "Clout", "Resolve"]
        rows = [
            [
                p["id"][:20],
                f"{p['position']:.0f}",
                f"{p['salience']:.0f}",
                f"{p['clout']:.1f}",
                f"{p['resolve']:.0f}"
            ]
            for p in results["players"]
        ]
        print_table(headers, rows, [22, 10, 10, 10, 10])
        
        if verbose:
            print("\nRationales:")
            for p in results["players"]:
                if p.get("rationale"):
                    print(f"  {p['id']}: {p['rationale']}")
    
    if results.get("war_risk"):
        wr = results["war_risk"]
        print_section("WAR RISK ASSESSMENT")
        print(f"  Risk Level:     {wr['risk_level']}")
        print(f"  Probability:    {wr['probability_range']}")
        print(f"  Equilibrium:    {wr['equilibrium_position']}/100")
        print(f"  Confidence:     {wr['confidence']:.2f}")
        print(f"\n  {wr['description']}")
    
    if results.get("lobbyability"):
        print_section("LOBBY-ABILITY RANKING")
        print("  Players ranked by potential to influence outcome toward peace:\n")
        
        headers = ["Rank", "Player", "Lobby Score", "Position", "Flexibility"]
        rows = []
        for i, p in enumerate(results["lobbyability"][:5], 1):
            resolve = p.get("current_resolve", 50)
            flexibility = "High" if resolve < 40 else "Medium" if resolve < 70 else "Low"
            rows.append([
                str(i),
                p["player_id"][:18],
                f"{p.get('lobby_score', 0):.2f}",
                f"{p.get('current_position', 50):.0f}",
                flexibility
            ])
        print_table(headers, rows, [6, 20, 12, 10, 12])
        
        if results["lobbyability"]:
            top = results["lobbyability"][0]
            print(f"\n  >>> TOP TARGET: {top['player_id']}")
            if top.get("recommended_actions"):
                print("  Recommended actions:")
                for action in top["recommended_actions"][:3]:
                    print(f"    - {action}")
    
    if results.get("equilibrium") and verbose:
        print_section("DETAILED EQUILIBRIUM DATA")
        eq = results["equilibrium"]
        if "simple_predictions" in eq:
            sp = eq["simple_predictions"]
            print(f"  Equilibrium Position: {sp.get('equilibrium_position', 'N/A')}")
            print(f"  Predicted Outcome:    {sp.get('predicted_outcome', 'N/A')}")
        if "monte_carlo_analysis" in eq:
            mc = eq["monte_carlo_analysis"]
            print(f"\n  Monte Carlo Analysis:")
            print(f"    Confidence:  {mc.get('confidence', 'N/A')}")
            print(f"    Mean:        {mc.get('mean', 'N/A')}")
            print(f"    Std Dev:     {mc.get('std_dev', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze stakeholders and predict conflict outcomes using game theory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py --event "Iran war stakeholders"
  python cli.py -e "Gaza conflict" --verbose
  python cli.py -e "Taiwan Strait tensions" --api-key KEY --openrouter-key KEY
        """
    )
    
    parser.add_argument(
        "-e", "--event",
        required=True,
        help="Event/conflict to analyze (e.g., 'Iran war stakeholders')"
    )
    
    parser.add_argument(
        "--api-key",
        default=None,
        help="RapidAPI key (or set RAPIDAPI_KEY env var)"
    )
    
    parser.add_argument(
        "--openrouter-key",
        default=None,
        help="OpenRouter API key (or set OPENROUTER_API_KEY env var)"
    )
    
    parser.add_argument(
        "--model",
        default=None,
        help="LLM model to use (default: from config or claude-3.5-sonnet)"
    )
    
    parser.add_argument(
        "--ldr-url",
        default=None,
        help="Local Deep Research URL (default: http://localhost:5000)"
    )
    
    parser.add_argument(
        "--no-research",
        action="store_true",
        help="Skip local research (requires --players-json)"
    )
    
    parser.add_argument(
        "--players-json",
        default=None,
        help="JSON file with pre-defined players (skips research)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    
    parser.add_argument(
        "--output-json",
        default=None,
        help="Save results to JSON file"
    )
    
    args = parser.parse_args()
    
    api_key = args.api_key or config.RAPIDAPI_KEY
    openrouter_key = args.openrouter_key or config.OPENROUTER_API_KEY
    model = args.model or config.OPENROUTER_MODEL
    ldr_url = args.ldr_url or config.LOCAL_RESEARCH_URL
    
    if not api_key:
        print("ERROR: RAPIDAPI_KEY not set. Use --api-key or set environment variable.")
        sys.exit(1)
    
    if not openrouter_key:
        print("ERROR: OPENROUTER_API_KEY not set. Use --openrouter-key or set environment variable.")
        sys.exit(1)
    
    existing_players = None
    if args.players_json:
        try:
            with open(args.players_json, 'r') as f:
                existing_players = json.load(f)
        except Exception as e:
            print(f"ERROR: Failed to load players JSON: {e}")
            sys.exit(1)
    
    print(f"\nAnalyzing: {args.event}")
    print("=" * 60)
    
    analyzer = StakeholderAnalyzer(
        rapidapi_key=api_key,
        openrouter_key=openrouter_key,
        openrouter_model=model,
        ldr_url=ldr_url
    )
    
    results = analyzer.analyze_event(
        event_query=args.event,
        use_research=not args.no_research,
        existing_players=existing_players
    )
    
    display_results(results, verbose=args.verbose)
    
    if args.output_json:
        with open(args.output_json, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {args.output_json}")
    
    if results.get("errors"):
        sys.exit(1)


if __name__ == "__main__":
    main()
