# Upload the full project to GitHub (Windows 11)

The ChatGPT GitHub connector can update text files in a repository but cannot take a local binary ZIP as an attachment. To transfer the exact Python source and original character JPEGs without corrupting them, use the included `push_to_github.bat` from this extracted project folder.

1. Install Git for Windows if needed: https://git-scm.com/download/win
2. Ensure you can sign in to GitHub and have write access to `zobaerio/jarvisai`.
3. Double-click `push_to_github.bat`.
4. Complete the Git Credential Manager sign-in if prompted.
5. After the push succeeds, the script opens a comparison page for the new branch. Review the files and create a Pull Request into `main`.

The script clones the existing repository, creates a new branch, copies source and assets (excluding `.venv`, cache files, and `.env`), commits them, and pushes that branch. It does not force-push or merge into `main` automatically.

## Safety
- Never place API keys, passwords, or `.env` secrets in the project before upload.
- Review the Git diff before merging.
- A successful push means the branch exists remotely; the app is not considered production-tested until Windows 11 installation, voice, microphone, and automation are tested on the target machine.
