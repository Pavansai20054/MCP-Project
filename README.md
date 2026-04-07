# 📚 README Upgrade Studio

Transform your GitHub repository documentation using AI-powered analysis and the Model Context Protocol.

> **Audit → Learn → Upgrade** — Generate production-grade READMEs by analyzing your actual codebase with Groq's advanced LLM.

![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square)
![MCP](https://img.shields.io/badge/MCP-GitHub-black?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red?style=flat-square)

---

## 🎯 What It Does

**README Upgrade Studio** autonomously audits your GitHub repository and generates a significantly upgraded README by:

- 🔍 **Deep Code Analysis** — Inspects source files, configs, and package declarations
- 🧠 **AI-Powered Recommendations** — Uses Groq's Llama 3.3 70B to understand your project's true capabilities
- 📐 **Architecture Documentation** — Automatically documents folder structure, design patterns, and best practices
- 🛡️ **Security Insights** — Identifies and flags potential security issues or risky patterns
- ⚡ **Two Interfaces** — Choose between CLI for automation or Streamlit UI for interactive exploration

---

## ⚙️ Prerequisites

Before you start, ensure you have:

- **Python 3.8+** installed
- **Git** (for cloning this repo)
- **Node.js 16+** (required for GitHub MCP server)
- Two API keys:
  - **Groq API Key** → [Get one free](https://console.groq.com)
  - **GitHub Personal Access Token** → [Create here](https://github.com/settings/tokens) (requires `repo` scope)

---

## 🚀 Quick Start (5 minutes)

### 1️⃣ Clone & Navigate

```bash
git clone https://github.com/Pavansai20054/MCP-Project.git
cd my-mcp-server
```

### 2️⃣ Create Environment File

Create a `.env` file in the project root:

```bash
cat > .env << EOF
GROQ_API_KEY=your_groq_api_key_here
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token_here
EOF
```

> 💡 **Tip:** Keep these tokens safe. Never commit `.env` to version control.

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Choose Your Interface

#### **Option A: CLI (Programmatic)**

Ideal for automation, CI/CD pipelines, or batch processing.

```bash
python -m src.main --repo owner/repository --max-iterations 10 --output upgraded_readme.md
```

**Arguments:**

- `--repo` — Repository in `owner/repo` format (e.g., `torvalds/linux`)
- `--max-iterations` — Agentic loop depth; higher = more thorough (default: 10)
- `--output` — Optional file path to save the generated README

**Example:**

```bash
python -m src.main --repo vercel/next.js --max-iterations 12
```

#### **Option B: Streamlit UI (Interactive)**

Perfect for exploring, iterating, and visual feedback.

```bash
streamlit run generator.py
```

Then open your browser to `http://localhost:8501`

**Features:**

- 🎨 Browse your public GitHub repositories
- ⚙️ Adjust iteration depth via sidebar slider
- 📊 Real-time generation progress
- 🔄 Built-in rate limiting for shared deployments
- 📋 Copy-paste results directly

---

## 📁 Project Architecture

```
my-mcp-server/
├── src/
│   ├── main.py                 # CLI entrypoint with argparse
│   ├── app_service.py          # Core business logic (README generation, GitHub API)
│   ├── orchestrator.py         # Agentic loop orchestration
│   ├── config/
│   │   └── env.py              # Configuration & environment loading
│   ├── prompts/
│   │   └── readme_upgrade.py   # System & user prompt builders
│   ├── tools/
│   │   ├── mcp_bridge.py       # MCP <→ Groq adapter
│   │   ├── groq_client.py      # Groq API wrapper
│   │   └── rate_limiter.py     # Request throttling for UI
│   └── ui/
│       └── app.py              # Streamlit application
├── generator.py                # Streamlit entry (run this for UI)
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🔄 How It Works

```
GitHub Repository
       │
       ├→ [MCP Server] reads files & structure
       │
       ├→ [Groq LLM] receives findings
       │
       ├→ [Agentic Loop] iterates (think-act-observe)
       │   • Identifies gaps in documentation
       │   • Extracts architecture & config details
       │   • Flags security concerns
       │
       └→ [Output] Professional README v2.0
```

**Key Flow:**

1. User specifies target repository
2. MCP establishes connection to GitHub
3. Groq analyzes repository structure & code
4. Agentic loop refines findings (configurable iterations)
5. Final README is generated with formatting & sections

---

## 🔧 Configuration

Edit `src/config/env.py` to customize:

```python
GROQ_MODEL = "llama-3.3-70b-versatile"  # Other models: "mixtral-8x7b-32768", "llama2-70b-4096"
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
MCP_COMMAND = "npx"  # Must have Node.js installed
MCP_ARGS = ["-y", "@modelcontextprotocol/server-github"]
```

---

## 📊 Example Usage

### CLI Example

```bash
# Analyze a popular open-source project
python -m src.main --repo facebook/react --max-iterations 15 --output react_readme_v2.md

# Dry-run with fewer iterations (faster)
python -m src.main --repo your-org/your-project --max-iterations 5
```

### UI Example

1. Run `streamlit run generator.py`
2. Use the sidebar dropdown to browse your repos
3. Adjust iteration slider (8-12 recommended)
4. Click "Generate"
5. View & copy the upgraded README

---

## ⚠️ Troubleshooting

| Issue                                    | Solution                                                            |
| ---------------------------------------- | ------------------------------------------------------------------- |
| `Missing required environment variables` | Ensure `.env` has `GROQ_API_KEY` and `GITHUB_PERSONAL_ACCESS_TOKEN` |
| `GitHub username not found`              | Use exact username; check authentication token has correct scopes   |
| `No content generated`                   | Increase `--max-iterations` or check Groq API quota                 |
| `Streamlit not found`                    | Run `pip install -r requirements.txt` again                         |
| `Node.js error in MCP`                   | Verify Node.js 16+ is installed: `node --version`                   |

---

## 🛡️ Security Notes

- **Never commit `.env` to Git** — Use `.gitignore`
- **GitHub Token Scopes** — Request minimum required permissions
- **API Key Protection** — Store keys in environment variables, never hardcode
- **Rate Limiting** — The UI enforces 2 generations per hour per user for public deployments

---

## 🧪 Testing Your Setup

Run this quick validation:

```bash
# Check Python & dependencies
python -c "import mcp, httpx, streamlit, groq; print('✓ All imports OK')"

# Validate environment
python -c "from src.config.env import config; print(f'Model: {config.GROQ_MODEL}'); print(f'Keys loaded: {bool(config.GROQ_API_KEY and config.GITHUB_TOKEN)}')"

# List available CLI args
python -m src.main --help
```

---

## 📦 Dependencies

| Package         | Purpose                             |
| --------------- | ----------------------------------- |
| `mcp`           | Model Context Protocol client       |
| `httpx`         | Async HTTP client                   |
| `pydantic`      | Data validation                     |
| `python-dotenv` | Environment variable management     |
| `streamlit`     | Web UI framework                    |
| `groq`          | Groq API client (installed via mcp) |

---

## 🎓 How to Use Output

The generated README includes:

✅ Project overview with clear value proposition  
✅ Complete installation & setup instructions  
✅ Usage examples for all major features  
✅ Architecture & folder structure explanation  
✅ Contributing guidelines (if detected)  
✅ Security best practices & warnings  
✅ Troubleshooting section  
✅ Links to related documentation

---

## 🤝 Contributing

Found a bug or have an idea? Contributions welcome!

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit changes (`git commit -am 'Add feature'`)
4. Push to branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see LICENSE file for details.

---

**Made with ❤️ by Rangdal Pavansai**

_Transform your documentation. Empower your users. Upgrade your README._
