
# Deep Research AI Agentic System

## Overview
This project implements a dual-agent AI system for deep online research. It uses:

- **Research Agent**: Crawls and collects data from the web using the Tavily API.
- **Answer Drafter Agent**: Generates concise answers via the Groq API based on collected context.
- **Knowledge Graph**: Builds and visualizes relationships between sources and keywords using networkx and Graphviz.
- **Streamlit UI**: Provides an interactive interface to input queries, adjust parameters, and view results.

## Features
- Customizable number of search results and context size.
- Automatic context trimming to respect API limits.
- Downloadable answer text.
- Interactive knowledge graph visualization.
- Expandable raw data view with links to sources.

## Prerequisites
- Python 3.8 or higher
- System installation of Graphviz (for rendering graphs)
- Valid API keys for:
  - **Tavily** (`TAVILY_API_KEY`)
  - **Groq** (`GROQ_API_KEY`)

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Graphviz on your system:
   - On Ubuntu/Debian:
     ```bash
     sudo apt-get update && sudo apt-get install graphviz
     ```
   - On macOS (with Homebrew):
     ```bash
     brew install graphviz
     ```

## Configuration
Create a `.env` file or set environment variables directly:

```bash
export TAVILY_API_KEY="tvly-dev-..."
export GROQ_API_KEY="sk-..."
```

## Usage
Run the Streamlit application:
```bash
streamlit run main.py
```
- Enter your research query.
- Adjust the **Max results** and **Context size** sliders.
- Click **Run Deep Research** to view the answer, graph, and raw data.

## Project Structure
```text
├── main.py                # Main Streamlit application
├── requirements.txt      # Python dependencies
├── README.md             # Project overview and setup instructions
└── ...                   # Additional modules or assets
```

## Notes
- The research agent caches results to speed up repeat queries.
- Context trimming logic ensures prompts stay within API limits.
- Modify `MAX_CONTEXT_LENGTH` default in `app.py` if needed.

## License
This project is released under the MIT License.

## Requirements
```text
streamlit>=1.22.0
requests>=2.28.0
networkx>=3.0
graphviz>=0.20
tavily>=0.1.0
```

