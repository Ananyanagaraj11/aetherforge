from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AetherForge"
    app_env: str = "demo"
    database_url: str = "sqlite:///./data/aetherforge.db"
    redis_url: str = ""
    jira_base_url: str = ""
    jira_email: str = ""
    jira_token: str = ""
    jira_project_key: str = "AF"
    jenkins_url: str = ""
    jenkins_user: str = ""
    jenkins_token: str = ""
    openai_api_key: str = ""


settings = Settings()
