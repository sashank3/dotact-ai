# Dotact-ai: LLM-Based Dota 2 Coaching System

### Table of Contents
1. [Project Description](#project-description)
2. [Purpose and Features](#purpose-and-features)
3. [Data Sources](#data-sources)
4. [Repository Cloning and Setup](#repository-cloning-and-setup)
5. [Dependencies](#dependencies)
6. [Running the Application](#running-the-application)
7. [Further Configuration](#further-configuration)
8. [Contact](#contact)

---

## Project Description
This project provides a **real-time, LLM-driven coaching system for Dota 2**. It leverages Valve’s Game State Integration (GSI) to fetch in-game data, processes that data, and then uses a Large Language Model to generate situational advice, item recommendations, and strategic insights during live matches. 

The application showcases how advanced language models can interpret complex game states to give meaningful in-game guidance.

---

## Purpose and Features
- **Real-Time Coaching**: Continuously listens to live game data (health, hero stats, items, etc.) and provides up-to-date suggestions.
- **Hero & Item Insights**: References static data for all Dota 2 heroes and items to tailor recommended builds and strategies.
- **Historical Trends**: Integrates historical match data (via external APIs like Stratz) to inform suggestions based on current meta.
- **LLM Communication**: Uses prompt engineering to provide short, high-impact tips in a structured format.

---

## Data Sources
The system uses three primary data types:

1. **Live Data**  
   - Provided via Valve’s GSI (Game State Integration).  
   - GSI sends JSON updates with in-game stats (hero health, items, map info, etc.).

2. **Static Data**  
   - Pulled from the Liquipedia [Dota 2 wiki](https://liquipedia.net/dota2/Portal:Heroes).  
   - Includes hero and item details (e.g., attributes, abilities, item costs, cooldowns).

3. **Historical Data**  
   - Gathered from [Stratz](https://stratz.com/) API using GraphQL.  
   - Contains aggregated match stats and hero win rates to inform strategic decisions.

> **Note**: The data sets are not directly included in this repository. You’ll need to configure your own GSI or supply your own API keys (e.g. for Stratz or other services) to fully leverage the historical data component.

---

## Repository Cloning and Setup
1. **Clone this repository**:
   ```bash
   git clone https://github.com/sashank3/dotact-ai.git
   cd dotact-ai
   ```
2. Ensure you have **Python 3.9+** (or your preferred version) available.

---

## Dependencies
We recommend using [uv](https://pypi.org/project/uv/) to manage and sync the project’s dependencies. All necessary Python packages are declared in a `pyproject.toml` file, and the typical workflow is:

1. **Install uv (if not installed)**:
   ```bash
   pip install uv
   ```
2. **Sync dependencies**:
   ```bash
   uv sync
   ```
   This will install packages based on the `pyproject.toml` and ensure the environment is up to date.

---

## Running the Application
1. **Configure Environment Variables**  
   - Create a `.env` file (or otherwise set environment variables) for your LLM API key and other secrets.  
   - Example:
     ```bash
     NEBIUS_API_KEY="<your-api-key-here>"
     ```
   - Confirm or edit any paths in `gsi_config.yaml` and `llm_config.yaml` as needed.

2. **Start the main script**:
   ```bash
   python main.py
   ```
   - This will:
     1. Set up the GSI config and launch a local server to receive game data.  
     2. Start a Chainlit-based UI where you can interact with the LLM in real time.

3. **Launch Dota 2** (with GSI enabled)  
   - Ensure the `gamestate_integration_custom.cfg` was successfully written to the correct Dota 2 config directory (as specified in `gsi_config.yaml`).
   - Once in-game, the system will begin receiving data from the local GSI server.

4. **Use the Chainlit UI**  
   - Open your browser to the URL displayed in the console (typically `http://localhost:8000`) and ask the bot for item or strategy suggestions.

---

## Further Configuration
- **Logging and Debugging**  
  Logs are stored in the `logs` directory (configurable in `gsi_config.yaml`). You can adjust logging levels in `logger.py` or the YAML configurations.

- **LLM Prompt Tuning**  
  `prompt_builder.py` controls how queries are sent to the LLM. You can modify the system prompt or response format to suit your coaching style.

- **Advanced Integrations**  
  This project’s architecture allows easy extension with other data sources or additional LLM functionalities (e.g., RAG workflows, advanced chain-of-thought reasoning, etc.).

---

## Contact
For questions, suggestions, or feedback, feel free to reach out or open an issue in the repository.

**Enjoy your real-time LLM-based Dota 2 coaching experience!**

