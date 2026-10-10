# Official/vendor-controlled roots used by enrichment collectors.
# Automatic discoveries are evidence for REVIEW; they never become block decisions automatically.

VENDORS = [
    {
        "vendor": "OpenAI",
        "root_domains": ["openai.com", "chatgpt.com"],
        "docs": ["https://help.openai.com/", "https://platform.openai.com/docs/"],
        "category": "genai_web",
    },
    {
        "vendor": "Anthropic",
        "root_domains": ["anthropic.com", "claude.ai"],
        "docs": ["https://docs.anthropic.com/"],
        "category": "genai_web",
    },
    {
        "vendor": "Google Gemini",
        "root_domains": ["google.com", "googleapis.com"],
        "docs": ["https://ai.google.dev/"],
        "category": "genai_web",
    },
    {
        "vendor": "Microsoft Copilot",
        "root_domains": ["copilot.microsoft.com"],
        "docs": ["https://copilot.microsoft.com/"],
        "category": "genai_web",
    },
    {
        "vendor": "GitHub Copilot",
        "root_domains": ["githubcopilot.com"],
        "docs": ["https://github.com/features/copilot"],
        "category": "ai_coding",
    },
    {
        "vendor": "Perplexity",
        "root_domains": ["perplexity.ai"],
        "docs": ["https://docs.perplexity.ai/"],
        "category": "genai_web",
    },
    {
        "vendor": "Mistral AI",
        "root_domains": ["mistral.ai"],
        "docs": ["https://docs.mistral.ai/"],
        "category": "genai_web",
    },
    {
        "vendor": "DeepSeek",
        "root_domains": ["deepseek.com"],
        "docs": ["https://api-docs.deepseek.com/"],
        "category": "genai_web",
    },
    {
        "vendor": "Groq",
        "root_domains": ["groq.com"],
        "docs": ["https://console.groq.com/docs/"],
        "category": "genai_web",
    },
    {
        "vendor": "Cohere",
        "root_domains": ["cohere.com"],
        "docs": ["https://docs.cohere.com/"],
        "category": "genai_web",
    },
    {
        "vendor": "Hugging Face",
        "root_domains": ["huggingface.co", "hf.co"],
        "docs": ["https://huggingface.co/docs/"],
        "category": "model_registry",
    },
    {
        "vendor": "Ollama",
        "root_domains": ["ollama.com"],
        "docs": ["https://ollama.com/"],
        "category": "llm_runtime",
    },
    {
        "vendor": "LM Studio",
        "root_domains": ["lmstudio.ai"],
        "docs": ["https://lmstudio.ai/"],
        "category": "llm_runtime",
    },
    {
        "vendor": "ModelScope",
        "root_domains": ["modelscope.cn"],
        "docs": ["https://modelscope.cn/"],
        "category": "model_registry",
    },
    {
        "vendor": "Cursor",
        "root_domains": ["cursor.com", "cursor.sh"],
        "docs": ["https://cursor.com/"],
        "category": "ai_coding",
    },
    {
        "vendor": "Windsurf",
        "root_domains": ["windsurf.com", "codeium.com"],
        "docs": ["https://windsurf.com/"],
        "category": "ai_coding",
    },
    {
        "vendor": "Replit",
        "root_domains": ["replit.com"],
        "docs": ["https://replit.com/"],
        "category": "ai_coding",
    },
]
