# Contributing

Thanks for your interest in DataInsight AI!

1. Fork the repo and create a branch: `git checkout -b feature/my-change`
2. Install dependencies: `pip install -r requirements.txt pytest ruff`
3. Make your change and run the checks:
   ```bash
   ruff check --select E9,F63,F7,F82 .
   pytest -q
   ```
4. Open a pull request describing what changed and how you tested it.

Please never commit API keys or the local `data/` folder — they're git-ignored for a reason.
