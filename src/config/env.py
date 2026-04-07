import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Groq Configuration
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    # Llama 3.3 70B is great for complex tasks like doc generation
    GROQ_MODEL = "llama-3.3-70b-versatile" 

    # GitHub MCP (Keep this the same)
    GITHUB_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    MCP_COMMAND = "npx"
    MCP_ARGS = ["-y", "@modelcontextprotocol/server-github"]

config = Config()