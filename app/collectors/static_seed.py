from app.collectors.base import Candidate

SEED = [
    Candidate("chatgpt.com", "domain", "OpenAI", "genai_web", "manual_seed", 100),
    Candidate("api.openai.com", "domain", "OpenAI", "ai_api", "manual_seed", 100),
    Candidate("claude.ai", "domain", "Anthropic", "genai_web", "manual_seed", 100),
    Candidate("api.anthropic.com", "domain", "Anthropic", "ai_api", "manual_seed", 100),
    Candidate("gemini.google.com", "domain", "Google", "genai_web", "manual_seed", 100),
    Candidate("generativelanguage.googleapis.com", "domain", "Google", "ai_api", "manual_seed", 100),
    Candidate("ollama.com", "domain", "Ollama", "llm_runtime", "manual_seed", 100),
    Candidate("huggingface.co", "domain", "Hugging Face", "model_registry", "manual_seed", 100),
    Candidate("hf.co", "domain", "Hugging Face", "model_registry", "manual_seed", 100),
    Candidate("xethub.hf.co", "domain", "Hugging Face", "model_cdn", "manual_seed", 100),
]
