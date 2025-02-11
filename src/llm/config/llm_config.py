import os


class LLMConfig:
    """
    Configuration for the Nebius-based LLM (DeepSeek R1).
    """

    # IAM key or token for Nebius Studio Inference
    NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "None")

    # The base URL for Nebius Studio Inference (similar to examples)
    BASE_URL = "https://api.studio.nebius.ai/v1/"

    # Default model name
    MODEL_NAME = "deepseek-ai/DeepSeek-R1"

    # Optional default parameters for chat completion
    DEFAULT_PARAMS = {
        "max_tokens": 512,
        "temperature": 0.7,
        # Add or modify as desired
        # "top_p": 1,
        # "n": 1,
        # etc.
    }

# eyJhbGciOiJIUzI1NiIsImtpZCI6IlV6SXJWd1h0dnprLVRvdzlLZWstc0M1akptWXBvX1VaVkxUZlpnMDRlOFUiLCJ0eXAiOiJKV1QifQ.eyJzdWIiOiJnb29nbGUtb2F1dGgyfDEwNTU3NjA3ODA4MTY3NTY1Nzc2MSIsInNjb3BlIjoib3BlbmlkIG9mZmxpbmVfYWNjZXNzIiwiaXNzIjoiYXBpX2tleV9pc3N1ZXIiLCJhdWQiOlsiaHR0cHM6Ly9uZWJpdXMtaW5mZXJlbmNlLmV1LmF1dGgwLmNvbS9hcGkvdjIvIl0sImV4cCI6MTg5NjkxMjE1MSwidXVpZCI6IjUxYjczY2Q0LTZhYmYtNGY4OS04NTAzLWJkZWNmZTdmNjMzNiIsIm5hbWUiOiJkZWVwc2Vlay1yMSIsImV4cGlyZXNfYXQiOiIyMDMwLTAyLTEwVDAwOjAyOjMxKzAwMDAifQ.kQt_N-EfxoN4PlUUaOhcxa6ljdpNyGsVGokNopGgmW4