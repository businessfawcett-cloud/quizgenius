# McGraw Hill Quiz Automation Agent

Automates McGraw Hill Connect quizzes by reading questions from the DOM, querying GLM-4.5 for answers, and selecting the correct option.

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
copy .env.example .env
```

Edit `.env` and add your GLM-4.5 API key:

```
GLM_API_KEY=your_actual_api_key
```

### 3. Launch Chrome with remote debugging

**Close ALL Chrome windows first**, then run:

```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-debug"
```

> This opens Chrome with debugging enabled. Log into McGraw Hill and navigate to your quiz.

### 4. Run the agent

```bash
python main.py
```

## Project Structure

| File | Purpose |
|------|---------|
| `main.py` | Entry point — orchestrates the automation loop |
| `browser_controller.py` | Connects to Chrome via CDP, handles clicks and text extraction |
| `question_parser.py` | Extracts question text, type, options, and progress from the DOM |
| `llm_client.py` | Sends questions to GLM-4.5 API and returns the predicted answer |
| `decision_engine.py` | Fuzzy-matches the LLM answer to a DOM option and clicks it |
| `config.py` | Loads `.env` variables and sets up logging |

## How It Works

```
Page loaded → Parse question & options → Ask GLM-4.5 → Click answer → Submit → Next
```

The agent loops until the quiz reports all concepts complete or parsing fails (end of quiz).

## Troubleshooting

- **"Could not connect to Chrome"** — Make sure Chrome was launched with `--remote-debugging-port=9222` and no other Chrome instance is running.
- **Parsing fails** — The CSS selectors may need tuning for your specific quiz layout. Check `question_parser.py` SELECTORS.
- **LLM returns wrong format** — The prompt asks for the exact option text only. If the model adds explanation, the fuzzy matcher in `decision_engine.py` handles it.
