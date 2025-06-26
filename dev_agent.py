import requests
import subprocess
import os
import re
import difflib
import sys
import platform
import datetime
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, simpledialog
import webbrowser
from urllib.parse import urljoin, urlparse
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import HtmlFormatter
except ImportError:
    highlight = None
    get_lexer_by_name = None
    HtmlFormatter = None

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "gemma:2b"
LOG_FILE = "devagent_session.log"

# Detect shell and OS
IS_WINDOWS = platform.system() == "Windows"
SHELL = os.environ.get("SHELL") or os.environ.get("COMSPEC") or "powershell.exe" if IS_WINDOWS else "bash"

# Persistent Ollama session (pre-warm)
def warm_ollama():
    try:
        requests.post(OLLAMA_API, json={"model": MODEL, "prompt": "Hello", "stream": False}, timeout=10)
    except Exception as e:
        print(f"[WARN] Ollama warmup failed: {e}")

def log_action(action, content=None):
    with open(LOG_FILE, 'a', encoding='utf-8') as log:
        log.write(f"[{datetime.datetime.now()}] {action}\n")
        if content:
            log.write(f"{content}\n\n")

def call_ollama(prompt):
    try:
        res = requests.post(OLLAMA_API, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }, timeout=120)
        response = res.json()["response"]
        log_action("AI Response", response)
        return response
    except Exception as e:
        print(f"[ERROR] Ollama call failed: {e}")
        return ""

def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"<error reading file {path}>: {e}"

def write_file(path, new_content):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            old_content = f.readlines()
    except:
        old_content = []
    new_lines = new_content.splitlines(keepends=True)
    diff = difflib.unified_diff(old_content, new_lines, fromfile='before', tofile='after')
    diff_text = ''.join(diff)
    print(f"\n📄 File diff for {path}:")
    print(diff_text or '[New file]')
    log_action(f"File diff for {path}", diff_text or '[New file]')
    confirm = input("Apply this change? (yes/no): ").strip().lower()
    if confirm == 'yes':
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ Changes written to {path}")
        log_action(f"File written: {path}")
    else:
        print("❌ Skipped writing changes.")
        log_action(f"Skipped writing: {path}")

def run_shell_command(cmd):
    # Format command for shell
    if IS_WINDOWS and SHELL.lower().endswith("powershell.exe"):
        shell_cmd = cmd
    else:
        shell_cmd = cmd
    print(f"\n💻 Command to run: {shell_cmd}")
    log_action("Shell command preview", shell_cmd)
    confirm = input("Run this command? (yes/no): ")

    if confirm == 'yes':
        try:
            output = subprocess.check_output(shell_cmd, shell=True, text=True)
            print("✅ Output:\n", output)
            log_action("Shell command output", output)
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {e}")
            log_action("Shell command failed", str(e))
    else:
        print("❌ Skipped command.")
        log_action("Skipped shell command", shell_cmd)

def parse_ai_response(response):
    # Extract file code blocks (support # File: and File:)
    file_blocks = re.findall(r'(?:(?<=File: )|(?:# File: ))(.+\.[\w/\\]+)\n```[a-zA-Z]*\n(.*?)```', response, re.DOTALL)
    # Extract shell commands (bash, powershell, sh, or no lang)
    shell_blocks = re.findall(r'```(?:bash|powershell|sh)?\n(.*?)```', response, re.DOTALL)
    return file_blocks, shell_blocks

class DevAgentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DevAgent (AI Developer)")
        self.project_path = tk.StringVar()
        self.create_widgets()
        warm_ollama()
        self.log("[INFO] Ollama pre-warmed.")

    def create_widgets(self):
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True)

        # Project path selection
        tk.Label(frame, text="Project Path:").grid(row=0, column=0, sticky='w')
        tk.Entry(frame, textvariable=self.project_path, width=50).grid(row=0, column=1, sticky='ew')
        tk.Button(frame, text="Browse", command=self.browse_project).grid(row=0, column=2)

        # Task input
        tk.Label(frame, text="Task:").grid(row=1, column=0, sticky='w')
        self.task_entry = tk.Entry(frame, width=60)
        self.task_entry.grid(row=1, column=1, columnspan=2, sticky='ew')
        self.task_entry.bind('<Return>', lambda e: self.run_task())
        tk.Button(frame, text="Run Task", command=self.run_task).grid(row=1, column=3)

        # AI suggestion display
        tk.Label(frame, text="AI Suggestion:").grid(row=2, column=0, sticky='nw')
        self.suggestion_box = scrolledtext.ScrolledText(frame, height=15, width=80, wrap=tk.WORD)
        self.suggestion_box.grid(row=2, column=1, columnspan=3, sticky='nsew')

        # Session log
        tk.Label(frame, text="Session Log:").grid(row=3, column=0, sticky='nw')
        self.log_box = scrolledtext.ScrolledText(frame, height=8, width=80, wrap=tk.WORD, state='disabled')
        self.log_box.grid(row=3, column=1, columnspan=3, sticky='nsew')

        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_rowconfigure(3, weight=1)

    def browse_project(self):
        path = filedialog.askdirectory()
        if path:
            self.project_path.set(path)
            self.log(f"[INFO] Project set: {path}")

    def log(self, msg):
        self.log_box.config(state='normal')
        self.log_box.insert(tk.END, msg + '\n')
        self.log_box.see(tk.END)
        self.log_box.config(state='disabled')
        log_action("GUI", msg)

    def list_project_files(self, root_dir, max_files=200):
        file_list = []
        for dirpath, _, filenames in os.walk(root_dir):
            for fname in filenames:
                rel_path = os.path.relpath(os.path.join(dirpath, fname), root_dir)
                file_list.append(rel_path.replace('\\', '/'))
                if len(file_list) >= max_files:
                    return file_list
        return file_list

    def run_task(self):
        project = self.project_path.get().strip()
        if not os.path.isdir(project):
            messagebox.showerror("Invalid Path", "Please select a valid project directory.")
            return
        task = self.task_entry.get().strip()
        if not task:
            messagebox.showwarning("No Task", "Please enter a task.")
            return
        os.chdir(project)
        self.log(f"[TASK] {task}")
        # --- FETCH ONLY: If fetch is requested, do not generate code, just fetch and preview ---
        if "fetch info from the internet" in task.lower() or "fetch online" in task.lower() or "fetch" in task.lower():
            url = simpledialog.askstring("Enter URL", "Enter the URL to fetch:")
            if url:
                # Auto-add https:// if missing
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "https://" + url
                import requests
                try:
                    r = requests.get(url)
                    fetched = r.text[:5000]  # Preview only
                    self.show_fetch_preview(url, fetched)
                    self.log(f"[Fetched from {url}]\n{fetched}")
                    # Find next available fetched_infoN.txt
                    n = 1
                    while True:
                        fname = f"fetched_info{n}.txt"
                        fpath = os.path.join(os.getcwd(), fname)
                        if not os.path.exists(fpath):
                            break
                        n += 1
                    # Use Windows-style backslashes if on Windows
                    if IS_WINDOWS:
                        fpath = fpath.replace('/', '\\')
                    if messagebox.askyesno("Save Fetched Content?", f"Save fetched content from {url} to {fname}?"):
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(r.text)
                        self.log(f"[Fetched info saved] {fpath}")
                except Exception as e:
                    messagebox.showerror("Fetch Failed", str(e))
                    self.log(f"[Fetch failed] {url}\n{e}")
            else:
                self.log("[Skipped online fetch]")
            return  # Do not proceed to code generation

        # --- Q&A/SUMMARY: If task is a question about the project/codebase, do a summary, not code changes ---
        if any(q in task.lower() for q in ["what kind of code", "what does this project do", "summarize", "overview", "describe"]):
            self.summarize_project(project, task)
            return

        # --- NEW: List project files and ask AI which are relevant ---
        file_list = self.list_project_files(project)
        file_list_str = '\n'.join(file_list)
        file_discovery_prompt = (
            f"You are an expert software agent. The user wants to perform this task in the project: {task}\n"
            f"Here is a list of all files in the project (relative to the project root):\n{file_list_str}\n"
            f"List only the most relevant file paths (from the list above) that should be read before making changes. "
            f"Return only a plain list of file paths, one per line, no explanation."
        )
        self.suggestion_box.delete(1.0, tk.END)
        self.suggestion_box.insert(tk.END, "[AI is analyzing which files are relevant... please wait]\n")
        self.root.update()
        relevant_files_response = call_ollama(file_discovery_prompt)
        relevant_files = [line.strip() for line in relevant_files_response.splitlines() if line.strip() and not line.strip().startswith('#') and line.strip() in file_list]
        # --- AGENTIC: Fallback if AI gives no files or gives a non-informative answer ---
        if not relevant_files:
            py_files = [f for f in file_list if f.endswith('.py')]
            if py_files and messagebox.askyesno("No files selected", "AI did not select any files. Analyze all Python files in the project root?"):
                relevant_files = py_files
            else:
                selected = filedialog.askopenfilenames(title="Select files to analyze", initialdir=project, filetypes=[("Python files", "*.py"), ("All files", "*.*")])
                relevant_files = [os.path.relpath(f, project).replace('\\', '/') for f in selected]
        self.log(f"[AI Relevant Files] {relevant_files}")
        # Read those files
        file_contexts = []
        for rel_path in relevant_files:
            full_path = os.path.join(project, rel_path.replace("/", os.sep))
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                content = f"<error reading file {rel_path}>: {e}"
            file_contexts.append((rel_path, content))
        # --- Now ask for code changes with context ---
        context_prompt = (
            f"You are an autonomous software developer agent.\n"
            f"The user wants to perform this task: {task}\n"
            f"Here are the current contents of the most relevant files for this task:\n"
        )
        for fname, fcontent in file_contexts:
            context_prompt += f"\n# File: {fname}\n" + fcontent + "\n"
        context_prompt += ("\nPlease generate the updated code blocks for only the necessary changes, "
                          "using triple backticks and filename above each block, and any shell commands needed. "
                          "No explanation, just the actions.")
        self.suggestion_box.insert(tk.END, "\n[AI is generating context-aware code changes...]\n")
        self.root.update()
        response = call_ollama(context_prompt)
        self.suggestion_box.delete(1.0, tk.END)
        self.suggestion_box.insert(tk.END, response)
        self.log("[AI Context-Aware Suggestion] Displayed.")
        file_blocks, shell_blocks = parse_ai_response(response)
        # Preview all file diffs
        file_diffs = []
        for filename, content in file_blocks:
            full_path = os.path.join(project, filename.strip().replace("/", os.sep))
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    old_content = f.readlines()
            except:
                old_content = []
            new_lines = content.splitlines(keepends=True)
            diff = difflib.unified_diff(old_content, new_lines, fromfile='before', tofile='after')
            diff_text = ''.join(diff)
            if not diff_text:
                diff_text = '[New file]'
            file_diffs.append((full_path, diff_text, content))
        # Preview all shell commands (filter out markdown/list lines)
        all_cmds = []
        for shell_block in shell_blocks:
            for cmd in shell_block.strip().split("\n"):
                cmd = cmd.strip()
                if not cmd or cmd.startswith('#') or cmd.startswith('*') or cmd.startswith('**') or cmd[0].isdigit() and cmd[1:2] in ['.', ')']:
                    continue
                all_cmds.append(cmd)
        # --- NEW: Show all changes in a modal dialog with syntax highlighting and options ---
        if file_diffs or all_cmds:
            self.show_batch_preview(file_diffs, all_cmds)
        else:
            self.render_code_blocks_in_suggestion(response)

    def show_fetch_preview(self, url, content):
        preview = tk.Toplevel(self.root)
        preview.title(f"Fetched Content from {url}")
        text = scrolledtext.ScrolledText(preview, width=100, height=30, font=("Consolas", 10))
        text.insert(tk.END, content)
        text.config(state='disabled')
        text.pack(fill=tk.BOTH, expand=True)
        tk.Button(preview, text="Close", command=preview.destroy).pack()

    def show_batch_preview(self, file_diffs, all_cmds):
        preview = tk.Toplevel(self.root)
        preview.title("Review All Changes")
        text = scrolledtext.ScrolledText(preview, width=100, height=40, font=("Consolas", 10))
        # Show file diffs with code block formatting
        if file_diffs:
            text.insert(tk.END, "File changes:\n")
            for path, diff_text, _ in file_diffs:
                text.insert(tk.END, f"\n--- {os.path.basename(path)} ---\n")
                text.insert(tk.END, f"```diff\n{diff_text}\n```")
        if all_cmds:
            text.insert(tk.END, "\nShell commands:\n")
            for cmd in all_cmds:
                text.insert(tk.END, f"\n```bash\n{cmd}\n```")
        text.config(state='disabled')
        text.pack(fill=tk.BOTH, expand=True)
        btn_frame = tk.Frame(preview)
        btn_frame.pack(fill=tk.X)
        def apply_all():
            preview.destroy()
            for path, _, content in file_diffs:
                self.retry_file_write(path, content)
            for cmd in all_cmds:
                self.retry_shell_command(cmd)
        def cancel_all():
            preview.destroy()
            self.log("[User cancelled all changes]")
        def edit_task():
            preview.destroy()
            self.task_entry.focus_set()
        tk.Button(btn_frame, text="Apply All", command=apply_all).pack(side=tk.LEFT, padx=10, pady=5)
        tk.Button(btn_frame, text="Undo/Cancel", command=cancel_all).pack(side=tk.LEFT, padx=10, pady=5)
        tk.Button(btn_frame, text="Edit Task", command=edit_task).pack(side=tk.LEFT, padx=10, pady=5)

    def retry_file_write(self, path, new_content):
        while True:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    old_content = f.readlines()
            except:
                old_content = []
            new_lines = new_content.splitlines(keepends=True)
            diff = difflib.unified_diff(old_content, new_lines, fromfile='before', tofile='after')
            diff_text = ''.join(diff)
            if not diff_text:
                diff_text = '[New file]'
            preview = f"File: {path}\n\n{diff_text}"
            if messagebox.askyesno("Apply File Change?", f"Preview diff for {os.path.basename(path)}:\n\n{diff_text}\n\nApply this change?"):
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    self.log(f"[File written] {path}")
                    break
                except Exception as e:
                    retry = messagebox.askretrycancel("File Write Failed", f"Error: {e}\nRetry?")
                    self.log(f"[File write failed] {path}\n{e}")
                    if not retry:
                        break
            else:
                self.log(f"[Skipped file] {path}")
                break

    def retry_shell_command(self, cmd):
        file_ops_handled = self.handle_file_operation(cmd)
        if file_ops_handled:
            return
        shell_type = 'powershell' if IS_WINDOWS and SHELL.lower().endswith('powershell.exe') else 'bash'
        while True:
            if messagebox.askyesno("Run Shell Command?", f"({shell_type}) Command:\n{cmd}\n\nRun this command?"):
                try:
                    # Run each command in a new, isolated process
                    process = subprocess.Popen(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
                    stdout, stderr = process.communicate()
                    if process.returncode == 0:
                        messagebox.showinfo("Command Output", stdout)
                        self.log(f"[Shell output] {cmd}\n{stdout}")
                        break
                    else:
                        retry = messagebox.askretrycancel("Command Failed", f"{stderr}\nRetry with different shell?")
                        self.log(f"[Shell failed] {cmd}\n{stderr}")
                        if retry:
                            if shell_type == 'powershell':
                                shell_type = 'bash'
                            else:
                                shell_type = 'powershell'
                            continue
                        else:
                            break
                except Exception as e:
                    messagebox.showerror("Command Exception", str(e))
                    self.log(f"[Shell exception] {cmd}\n{e}")
                    break
            else:
                self.log(f"[Skipped shell] {cmd}")
                break

    def fetch_and_cache_docs(self, base_url, max_pages=30):
        import requests
        from collections import deque
        seen = set()
        queue = deque([base_url])
        docs_dir = os.path.join(os.getcwd(), 'docs_cache')
        os.makedirs(docs_dir, exist_ok=True)
        count = 0
        while queue and count < max_pages:
            url = queue.popleft()
            if url in seen:
                continue
            seen.add(url)
            try:
                r = requests.get(url, timeout=10)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, 'html.parser')
                # Save main text content
                text = soup.get_text(separator='\n', strip=True)
                parsed = urlparse(url)
                fname = parsed.path.strip('/').replace('/', '_') or 'index'
                fname = fname.split('?')[0]
                fname = fname[:100]  # limit filename length
                fpath = os.path.join(docs_dir, f"{fname}.txt")
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(f"URL: {url}\n\n{text}")
                count += 1
                self.log(f"[Doc cached] {url}")
                # Find more doc links
                for a in soup.find_all('a', href=True):
                    link = urljoin(url, a['href'])
                    if link.startswith(base_url) and link not in seen and '#' not in link:
                        queue.append(link)
            except Exception as e:
                self.log(f"[Doc fetch failed] {url}\n{e}")
        messagebox.showinfo("Docs Fetch Complete", f"Fetched and cached {count} documentation pages in docs_cache/.")

    def render_code_blocks_in_suggestion(self, response):
        self.suggestion_box.config(state='normal')
        self.suggestion_box.delete(1.0, tk.END)
        import re
        code_block_pattern = re.compile(r'```(\w+)?\n(.*?)```', re.DOTALL)
        last_end = 0
        for match in code_block_pattern.finditer(response):
            lang = match.group(1) or 'text'
            code = match.group(2)
            # Insert text before code block
            self.suggestion_box.insert(tk.END, response[last_end:match.start()])
            # Syntax highlight if possible
            code_text = code
            if highlight and get_lexer_by_name and HtmlFormatter:
                try:
                    lexer = get_lexer_by_name(lang, stripall=True)
                    formatter = HtmlFormatter(noclasses=True, style='monokai')
                    from io import StringIO
                    import html
                    html_code = highlight(code, lexer, formatter)
                    # Remove HTML tags for Tkinter, fallback to plain
                    code_text = re.sub('<.*?>', '', html_code)
                except Exception:
                    code_text = code
            # Insert code block with bg
            start_idx = self.suggestion_box.index(tk.END)
            self.suggestion_box.insert(tk.END, code_text)
            end_idx = self.suggestion_box.index(tk.END)
            self.suggestion_box.tag_add('codeblock', start_idx, end_idx)
            # Add copy button
            btn = tk.Button(self.suggestion_box, text="Copy", command=lambda c=code: self.copy_to_clipboard(c))
            self.suggestion_box.window_create(tk.END, window=btn)
            self.suggestion_box.insert(tk.END, '\n')
            last_end = match.end()
        # Insert any remaining text
        self.suggestion_box.insert(tk.END, response[last_end:])
        self.suggestion_box.tag_config('codeblock', font=('Consolas', 10), background='#f5f5f5')
        self.suggestion_box.config(state='disabled')

    def copy_to_clipboard(self, code):
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        messagebox.showinfo("Copied", "Code copied to clipboard!")

    def summarize_project(self, project, task):
        # List project files (prefer .py, up to 5 files)
        file_list = self.list_project_files(project, max_files=30)
        py_files = [f for f in file_list if f.endswith('.py')]
        main_files = py_files[:5] if py_files else file_list[:5]
        file_contexts = []
        for rel_path in main_files:
            full_path = os.path.join(project, rel_path.replace("/", os.sep))
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    # Read only first 40 lines for brevity
                    lines = f.readlines()[:40]
                    content = ''.join(lines)
            except Exception as e:
                content = f"<error reading file {rel_path}>: {e}"
            file_contexts.append((rel_path, content))
        file_list_str = '\n'.join(main_files)
        context = ''
        for fname, fcontent in file_contexts:
            context += f"\n# File: {fname}\n" + fcontent + "\n"
        prompt = (
            f"You are an expert software agent. The user asked: {task}\n"
            f"Here are the first 40 lines of the main files in the project (relative to the project root):\n{context}\n"
            f"Give a concise, high-level summary of what this project is, what it does, and its main components. "
            f"If possible, mention the main entry point and any key libraries or frameworks used."
        )
        self.suggestion_box.delete(1.0, tk.END)
        self.suggestion_box.insert(tk.END, "[AI is analyzing the project... please wait]\n")
        self.root.update()
        summary = call_ollama(prompt)
        # Fallback: if AI still refuses, prompt user to select files
        if 'unable to access' in summary.lower() or 'cannot provide' in summary.lower():
            messagebox.showwarning("AI could not summarize", "AI could not summarize. Please select files to include in the summary.")
            selected = filedialog.askopenfilenames(title="Select files for summary", initialdir=project, filetypes=[("Python files", "*.py"), ("All files", "*.*")])
            file_contexts = []
            for fpath in selected:
                rel_path = os.path.relpath(fpath, project).replace('\\', '/')
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[:40]
                        content = ''.join(lines)
                except Exception as e:
                    content = f"<error reading file {rel_path}>: {e}"
                file_contexts.append((rel_path, content))
            context = ''
            for fname, fcontent in file_contexts:
                context += f"\n# File: {fname}\n" + fcontent + "\n"
            prompt = (
                f"You are an expert software agent. The user asked: {task}\n"
                f"Here are the first 40 lines of the selected files in the project (relative to the project root):\n{context}\n"
                f"Give a concise, high-level summary of what this project is, what it does, and its main components. "
                f"If possible, mention the main entry point and any key libraries or frameworks used."
            )
            summary = call_ollama(prompt)
        self.suggestion_box.delete(1.0, tk.END)
        self.suggestion_box.insert(tk.END, summary)
        self.log("[AI Project Summary Displayed]")

def main():
    root = tk.Tk()
    app = DevAgentGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
