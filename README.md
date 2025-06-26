# DevAgent: Agentic AI Developer Assistant

DevAgent is a cross-platform, agentic AI developer assistant with a modern GUI. It leverages local LLMs (via Ollama) to provide safe, context-aware, and user-approved code changes, project summaries, and web content fetching for any codebase.

## Features

- **Tkinter GUI**: All interactions are graphical—no terminal I/O for user actions.
- **Project-Aware**: Select a project folder and enter tasks or questions.
- **Agentic File Selection**: Lists all project files and asks the AI to select relevant ones for each task. If the AI fails, prompts the user or defaults to Python files.
- **Context-Aware Code Changes**: Reads only relevant files, provides their content to the AI, and previews all diffs and shell commands for user approval before applying.
- **Project Summaries & Q&A**: Asks the AI for high-level summaries or answers about the codebase, including actual file content for reliable results.
- **Web Fetching & Caching**: Fetches and saves online content or documentation, with unique filenames and a docs cache.
- **Session Logging**: All actions and AI responses are logged for traceability.
- **Syntax Highlighting**: Code blocks in the UI are rendered with syntax highlighting and copy buttons (if Pygments is installed).
- **Safe File & Shell Operations**: All file and shell changes are previewed and require explicit user approval.
- **Cross-Platform & Shell-Aware**: Detects and uses the correct shell for your OS.

## Requirements

- Python 3.8+
- [Ollama](https://ollama.com/) running locally (for LLM API)
- Optional: `beautifulsoup4` and `pygments` for enhanced features

Install dependencies:
```sh
pip install requests
```

## Usage

1. Start Ollama locally (e.g., `ollama serve`).
2. Run the agent:
   ```sh
   python dev_agent.py
   ```
3. Use the GUI to select your project folder and enter tasks, such as:
   - "Add a function to parse JSON files."
   - "What kind of code is here and what is it doing?"
   - "Fetch info from the internet."
4. Review all code diffs and shell commands in the GUI before applying.

## How It Works

- The agent lists all files in your project and asks the AI which are relevant for your task.
- It reads those files, sends their content to the AI, and displays the AI's suggested changes.
- All file changes and shell commands are shown in a batch preview for your approval.
- For project summaries, the agent includes the first 40 lines of up to 5 main files to ensure the AI can provide a meaningful answer.
- Fetching web content or documentation is supported and cached for future use.

## Security & Safety

- No changes are made without your explicit approval.
- All actions are logged in `devagent_session.log`.
- Only true system/package commands are run in the terminal; file operations are handled directly in Python.

## Customization

- You can change the LLM model by editing the `MODEL` variable in `dev_agent.py`. Suugested to use mistral or any other more parameters model for better response and systen specs like use deepseek-r1:671b if you have 1000gb of ram
- The agent is easily extensible for new workflows or integrations.

---

*DevAgent: Your safe, agentic, and context-aware AI developer for any project.*
