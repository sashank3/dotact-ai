import logging
from dotenv import load_dotenv
from src.data.gsi.gsi import gsi_orchestrator, get_processed_gsi_data
from src.llm.llm import LLMOrchestrator
from src.llm.prompt.response_formatter import process_llm_response


def main():
    load_dotenv()

    logging.info("[MAIN] Starting GSI pipeline...")
    gsi_orchestrator()

    llm_orch = LLMOrchestrator()

    while True:
        user_input = input("\nEnter your query (or 'exit' to quit): ")
        if user_input.lower() == "exit":
            break

        game_state_text = get_processed_gsi_data()

        response_generator = llm_orch.get_llm_response(user_input, game_state_text, stream=True)

        process_llm_response(response_generator)

    logging.info("[MAIN] Exiting application.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    main()
