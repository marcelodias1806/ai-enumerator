# Sources intentionally constrained to official/vendor-controlled roots.
# Automatic discoveries are REVIEW-only.

VENDORS = [
    {
        "vendor": "OpenAI",
        "root_domains": ["openai.com", "chatgpt.com"],
        "docs": [
            "https://help.openai.com/",
            "https://platform.openai.com/docs/",
        ],
        "category": "genai_web",
    },
    {
        "vendor": "Anthropic",
        "root_domains": ["anthropic.com", "claude.ai"],
        "docs": [
            "https://docs.anthropic.com/",
        ],
        "category": "genai_web",
    },
    {
        "vendor": "Google Gemini",
        "root_domains": ["google.com", "googleapis.com"],
        "docs": [
            "https://ai.google.dev/",
        ],
        "category": "genai_web",
    },
    {
        "vendor": "Ollama",
        "root_domains": ["ollama.com"],
        "docs": [
            "https://ollama.com/",
        ],
        "category": "llm_runtime",
    },
    {
        "vendor": "Hugging Face",
        "root_domains": ["huggingface.co", "hf.co"],
        "docs": [
            "https://huggingface.co/docs/",
        ],
        "category": "model_registry",
    },
    {
        "vendor": "Mistral AI",
        "root_domains": ["mistral.ai"],
        "docs": [
            "https://docs.mistral.ai/",
        ],
        "category": "genai_web",
    },
]
