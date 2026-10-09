from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://ai_enum:change-me@db:5432/ai_enum"
    redis_url: str = "redis://redis:6379/0"
    http_timeout: int = 15

    jwt_secret: str = "change-this-to-a-long-random-secret-at-least-32-bytes"
    jwt_ttl_minutes: int = 480
    auth_cookie_secure: bool = False
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "change-me-now"

    feed_token: str = "change-this-feed-token"

    exposure_http_timeout: int = 6
    exposure_tcp_timeout: int = 3
    exposure_max_targets: int = 500
    exposure_verify_tls: bool = True
    exposure_allow_http_get: bool = False
    exposure_auto_scan: bool = True
    exposure_auto_scan_interval_seconds: int = 86400
    exposure_scan_concurrency: int = 20
    exposure_redirect_limit: int = 5

    assessment_company_name: str = "Organization"
    assessment_report_title: str = "AI Egress Exposure Assessment"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
