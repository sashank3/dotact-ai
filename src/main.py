import logging
from src.data.gsi.gsi import gsi_orchestrator, get_processed_gsi_data


def main():
    # 1) Start GSI pipeline (in background thread)
    logging.info("[MAIN] Starting GSI pipeline...")
    gsi_orchestrator()

    # 2) Enter a loop to continuously accept user queries
    while True:
        user_input = input("\nEnter your query (type 'exit' to quit): ")
        if user_input.lower() == "exit":
            logging.info("[MAIN] Exiting application at user request.")
            break

        # 3) Get the latest processed GSI data
        processed_gsi_data = get_processed_gsi_data()
        print(processed_gsi_data)

        # 4) Combine with user query
        combined_prompt = f"GAME CONTEXT:\n{processed_gsi_data}\n\nUSER QUERY:\n{user_input}"

        # 5) Send to LLM (stubbed)
        # response = call_llm_api(combined_prompt)
        response = "[LLM MOCK RESPONSE]: Build items for survivability."

        # 6) Print result
        print("LLM Response:", response)

    logging.info("[MAIN] Application shutting down...")


if __name__ == "__main__":
    main()
