from app.db import SessionLocal
from app.models import AssetKind, Category, SourceType
from app.services.ingest import ingest_candidate

CATALOG = [
    ("chatgpt.com","OpenAI","genai_web"),
    ("api.openai.com","OpenAI","ai_api"),
    ("platform.openai.com","OpenAI","ai_api"),
    ("claude.ai","Anthropic","genai_web"),
    ("api.anthropic.com","Anthropic","ai_api"),
    ("console.anthropic.com","Anthropic","ai_api"),
    ("gemini.google.com","Google Gemini","genai_web"),
    ("generativelanguage.googleapis.com","Google Gemini","ai_api"),
    ("aistudio.google.com","Google Gemini","ai_api"),
    ("copilot.microsoft.com","Microsoft Copilot","genai_web"),
    ("api.githubcopilot.com","GitHub Copilot","ai_coding"),
    ("githubcopilot.com","GitHub Copilot","ai_coding"),
    ("perplexity.ai","Perplexity","genai_web"),
    ("api.perplexity.ai","Perplexity","ai_api"),
    ("mistral.ai","Mistral AI","genai_web"),
    ("api.mistral.ai","Mistral AI","ai_api"),
    ("console.mistral.ai","Mistral AI","ai_api"),
    ("chat.deepseek.com","DeepSeek","genai_web"),
    ("api.deepseek.com","DeepSeek","ai_api"),
    ("groq.com","Groq","genai_web"),
    ("api.groq.com","Groq","ai_api"),
    ("console.groq.com","Groq","ai_api"),
    ("cohere.com","Cohere","genai_web"),
    ("api.cohere.com","Cohere","ai_api"),
    ("huggingface.co","Hugging Face","model_registry"),
    ("hf.co","Hugging Face","model_registry"),
    ("xethub.hf.co","Hugging Face","model_cdn"),
    ("cas-server.xethub.hf.co","Hugging Face","model_cdn"),
    ("transfer.xethub.hf.co","Hugging Face","model_cdn"),
    ("ollama.com","Ollama","llm_runtime"),
    ("registry.ollama.ai","Ollama","model_registry"),
    ("modelscope.cn","ModelScope","model_registry"),
    ("lmstudio.ai","LM Studio","llm_runtime"),
    ("cursor.com","Cursor","ai_coding"),
    ("api2.cursor.sh","Cursor","ai_coding"),
    ("windsurf.com","Windsurf","ai_coding"),
    ("codeium.com","Windsurf","ai_coding"),
    ("replit.com","Replit","ai_coding"),
]

with SessionLocal() as db:
    for domain,vendor,category in CATALOG:
        ingest_candidate(
            db,
            kind=AssetKind.domain,
            value=domain,
            vendor=vendor,
            category=Category(category),
            source_type=SourceType.manual,
            source_ref="v0.6-curated-seed",
            source_confidence=100,
            evidence="Curated GenAI exposure target for v0.6. Validate vendor endpoints before production enforcement.",
        )
print(f"Seed loaded: {len(CATALOG)} curated GenAI targets.")
