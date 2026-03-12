# Stakeholder Analysis & Game Theory Predictor

A CLI + Gradio web demo that analyzes geopolitical events to identify stakeholders, predict outcomes using Nash Equilibrium game theory, and find the most "lobby-able" players to influence toward peaceful outcomes.

## Features

- **Stakeholder Research**: Uses Local Deep Research to gather information from news sources
- **LLM-Powered Extraction**: Converts unstructured research into quantified player data
- **Game Theory Predictions**: Uses Nash Equilibrium API to predict conflict outcomes
- **Lobby-ability Analysis**: Identifies which stakeholders are most influenceable
- **Dual Interface**: Both CLI and Gradio web UI

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Local Deep Research

```bash
curl -O https://raw.githubusercontent.com/LearningCircuit/local-deep-research/main/docker-compose.yml
MODEL=qwen3.5:4b docker compose up -d
```

Wait ~30 seconds, then verify at http://localhost:5000

### 3. Set API Keys

```bash
# Required: RapidAPI key for Game Theory API
export RAPIDAPI_KEY="your-rapidapi-key"

# Required: OpenRouter key for LLM-powered extraction
export OPENROUTER_API_KEY="your-openrouter-key"

# Optional: Model selection (defaults to claude-3.5-sonnet)
export OPENROUTER_MODEL="anthropic/claude-3.5-sonnet"
```

### 4. Run

**CLI:**
```bash
python cli.py --event "Iran war stakeholders"
```

**Web UI:**
```bash
python app.py
# Open http://localhost:7860
```

## API Keys

### RapidAPI (Game Theory)
1. Visit https://rapidapi.com/worksourcewishes/api/game-theory-nash-equilibrium-predictor
2. Subscribe to the API (free tier available)
3. Copy your API key from the dashboard

### OpenRouter (LLM)
1. Visit https://openrouter.ai/keys
2. Create an account and generate an API key
3. Supports models from: Anthropic, OpenAI, Google, Meta, DeepSeek, etc.

## Usage Examples

### CLI Examples

```bash
# Basic analysis
python cli.py --event "Iran war stakeholders"

# Verbose output
python cli.py -e "Gaza conflict" --verbose

# With inline API keys
python cli.py -e "Taiwan Strait tensions" \
    --api-key YOUR_RAPIDAPI_KEY \
    --openrouter-key YOUR_OPENROUTER_KEY

# Save results to JSON
python cli.py -e "Ukraine war" --output-json results.json

# Use pre-defined players (skip research)
python cli.py -e "Custom scenario" --no-research --players-json players.json
```

### Web UI

1. Open http://localhost:7860
2. Enter your API keys
3. Type a query like "Iran war stakeholders"
4. Click "Analyze"
5. View results in tabs: Stakeholders, War Risk, Lobby-ability

### Example Queries

- "Iran war stakeholders and decision makers"
- "Gaza conflict key players and their positions"
- "Taiwan Strait tensions stakeholders"
- "Ukraine war negotiation parties"
- "South China Sea dispute actors"

## Project Structure

```
├── config.py              # API settings and configuration
├── game_theory_api.py     # Client for Nash Equilibrium API
├── local_research.py      # Integration with Local Deep Research
├── stakeholder_analyzer.py # Core analysis logic
├── cli.py                 # Command-line interface
├── app.py                 # Gradio web application
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## How It Works

### Pipeline

```
User Query → Local Deep Research → LLM Extraction → Game Theory API → Results
     ↓              ↓                    ↓                 ↓            ↓
  "Iran war"   Search news      Extract players    Run equilibrium  Display
               & articles       with position,     predictions      risk &
                                salience, clout                     lobby-ability
```

### Player Data Structure

Each stakeholder is quantified as:

| Field | Range | Description |
|-------|-------|-------------|
| `position` | 0-100 | Stance (0=pro-peace, 100=pro-conflict) |
| `salience` | 0-100 | Issue importance to stakeholder |
| `clout` | 0.1-10.0 | Relative influence/power |
| `resolve` | 0-100 | Firmness of position |

### War Risk Levels

| Level | Position | Probability | Description |
|-------|----------|-------------|-------------|
| LOW | 0-30 | 10-25% | Diplomatic solution likely |
| MODERATE | 30-50 | 25-45% | Tensions, negotiations ongoing |
| ELEVATED | 50-70 | 45-65% | Confrontation likely |
| HIGH | 70-100 | 65-85% | Conflict probable |

### Lobby-ability Score

Calculated as:
```
lobby_score = improvement_potential × clout / (resolve + 1)
```

Higher scores indicate players who:
- Have greater influence (high clout)
- Are more flexible (low resolve)
- Can significantly shift the equilibrium

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RAPIDAPI_KEY` | Yes | - | RapidAPI key for Game Theory API |
| `OPENROUTER_API_KEY` | Yes | - | OpenRouter API key for LLM |
| `OPENROUTER_MODEL` | No | claude-3.5-sonnet | LLM model to use |
| `LOCAL_RESEARCH_URL` | No | http://localhost:5000 | Local Deep Research URL |

### Supported LLM Models

- `anthropic/claude-3.5-sonnet` (recommended)
- `anthropic/claude-3-haiku` (faster, cheaper)
- `openai/gpt-4o`
- `openai/gpt-4o-mini`
- `google/gemini-2.0-flash-001`
- `meta-llama/llama-3.3-70b-instruct`
- `deepseek/deepseek-chat`

## Troubleshooting

### "Local research service is not running"
```bash
# Check if Docker container is running
docker ps | grep local-deep-research

# Start it
docker compose up -d

# Check logs
docker compose logs -f
```

### "RAPIDAPI_KEY not set"
```bash
export RAPIDAPI_KEY="your-key"
# Or pass inline: --api-key YOUR_KEY
```

### "Failed to authenticate with local research service"
Default credentials are `admin/admin`. If you changed them:
```bash
# In Python
client = LocalResearchClient(username="your_user", password="your_pass")
```

### LLM extraction returns empty
- Check your OpenRouter API key and credits
- Try a different model
- Check the research actually returned content

## API Endpoints Used

### Game Theory API (RapidAPI)

| Endpoint | Purpose |
|----------|---------|
| `POST /run_analysis` | Main equilibrium prediction |
| `POST /sensitivity_analysis` | Test prediction stability |
| `POST /optimize_strategy` | Find optimal strategy for a player |
| `POST /run_strategic_simulation` | Test interventions |

### Local Deep Research

| Endpoint | Purpose |
|----------|---------|
| `POST /api/start_research` | Start research task |
| `GET /api/research/{id}/status` | Check status |
| `GET /api/report/{id}` | Get results |

## License

MIT License

## Credits

- [Local Deep Research](https://github.com/LearningCircuit/local-deep-research) - Research engine
- [OpenRouter](https://openrouter.ai) - LLM gateway
- [Game Theory Nash Equilibrium Predictor](https://rapidapi.com/worksourcewishes/api/game-theory-nash-equilibrium-predictor) - Predictions API
