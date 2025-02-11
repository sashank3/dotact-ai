import logging
from dotenv import load_dotenv
from src.llm.config.paths import ENV_FILE
from src.data.gsi.gsi import gsi_orchestrator, get_processed_gsi_data
from src.llm.llm import LLMOrchestrator


def main():
    # Load .env if present
    load_dotenv(dotenv_path=ENV_FILE)

    logging.info("[MAIN] Starting GSI pipeline...")
    gsi_orchestrator()  # Launches server in a background thread

    llm_orch = LLMOrchestrator()

    while True:
        user_input = input("\nEnter your query (or 'exit' to quit): ")
        if user_input.lower() == "exit":
            break

        # Get processed GSI data for context
        game_state_text = get_processed_gsi_data()

        # Ask LLM
        response = llm_orch.get_llm_response(user_input, game_state_text)

        print("LLM Response:", response)

    logging.info("[MAIN] Exiting application.")


if __name__ == "__main__":
    # Basic logging format
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    main()
