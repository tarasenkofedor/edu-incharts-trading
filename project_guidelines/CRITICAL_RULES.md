---
description: Critically important rules that MUST be followed to prevent catastrophic errors or project destabilization.
globs: "**/*"
alwaysApply: true
---


- **For the frontend of the project use project's current code. If needed, create `frontend` folder in the root directory and move all files, related to frontend, to this folder.**

- **Always commit most important files and folders (backend, frotnend, database-related files and etc.) to Github!!!**

- **(skip this rule for now) After the completion of each task, make a necessary commit to the main branch of the user's repository.**

- **After the completion of each task, make necessary logs, update tasks and ask a permission to continue with other tasks.**


- **Filesystem Safety:**
    - **Never perform `rm` (remove/delete file or directory) commands on:**
        - The project root directory.
        - Any top-level directory (e.g., `src/`, `docs/`, `scripts/`, `test/`, `.git/`).
        - Any directory known to contain essential configuration or source code without explicit, case-by-case user confirmation for that specific path.
    - **If a deletion operation seems necessary for critical paths, you MUST:**
        1.  Clearly state the command you intend to run and the full path.
        2.  Explain *why* this deletion is necessary.
        3.  Ask for explicit user confirmation to proceed with that specific command and path.
        4.  Do NOT perform the command yourself even if you believe it's safe. User confirmation is mandatory for deletions in sensitive areas.
    - Prefer moving files to a temporary `_trash` directory instead of direct deletion if unsure, and inform the user.

- **Version Control Integrity:**
    - **Commit Before Significant Changes:** Before undertaking any significant update, refactoring, or feature implementation that involves multiple files or complex logic changes:
        1.  Ensure all current, stable work is committed to the Git repository.
        2.  State your intention to commit, providing a draft commit message.
        3.  Proceed with the commit using the appropriate tool (e.g., `run_terminal_cmd` with `git add . && git commit -m "message"`).
    - This ensures a stable checkpoint to revert to if the subsequent changes introduce issues.

- **Configuration File Handling:**
    - Exercise extreme caution when editing critical configuration files (e.g., `package.json`, `.taskmasterconfig`, `.env`, Nginx configurations, database configurations).
    - Always validate changes to these files carefully before applying.
    - If unsure about a configuration change, propose the change and ask for user review before applying.

- **Credentials Management (`.env`)**
    - **All sensitive credentials, API keys, secrets, and environment-specific URLs for the project MUST be stored in a `.env` file located in the root directory of the project.**
    - This file should be listed in `.gitignore` to prevent accidental commits of sensitive information.
    - The application (e.g., FastAPI backend via Pydantic settings) should be configured to load these variables from the `.env` file.
    - Do NOT hardcode secrets or API keys directly into source code files.
    - An example file (e.g., `.env.example`) SHOULD be provided in the repository, containing all necessary environment variable keys with placeholder or non-sensitive default values, to guide developers in setting up their local environment.

- **Tool Usage Verification:**
    - Before executing any tool that performs a potentially destructive or widespread action (e.g., mass find/replace, database schema migrations):
        1.  Double-check the parameters and scope of the command.
        2.  If the tool provides a "dry-run" or preview mode, use it first.
        3.  State the intended action and seek user confirmation if the impact is significant or unclear.

- **Task Master AI Safety:**
    - When using `task-master-ai` tools that modify tasks (`update`, `remove_task`, `expand_task --force`, `clear_subtasks`):
        - Clearly state the IDs of tasks/subtasks being affected and the nature of the change *before* execution.
        - If a large number of tasks will be affected, ask for confirmation.

- **Mandatory Test Coverage for New Features:**
    - **For every new feature implemented, a corresponding set of tests MUST be written.**
    - These tests must validate the core functionality of the feature and cover primary use cases and expected edge conditions.
    - Test types can include unit tests, integration tests, or API endpoint tests as appropriate for the feature.
    - All new tests must pass before the feature is considered complete or merged.
    - Test code should be maintained alongside the application code, typically in a dedicated `tests/` directory structure mirroring the app structure.
    - If a testing framework is not yet established, the implementation of the first feature requiring tests must also include setting up a basic testing framework (e.g., PyTest for backend, Jest/Vitest for frontend).

- **MVP Compromise Logging:**
    - **When architectural decisions or implementations are made as a compromise for MVP speed (e.g., using a simpler but less ideal long-term solution), these MUST be explicitly noted.**
    - A brief explanation of the compromise, the ideal long-term solution, and the reasoning for the MVP choice should be logged as an "Architectural Note" or "MVP Compromise" entry in `docs/project_guidelines/DIARY.md` under the relevant date and action.
    - This ensures that these decisions are documented for future refactoring and scaling efforts.

- **Logging and Continuation Permission:**
    - **After completing any task or a significant sub-task, ensure all necessary project logs (e.g., in `DIARY.md`, `CHANGELOG.md`, `TASKS.md` as appropriate) are meticulously updated to reflect the work done.**
    - **Before proceeding to the next task or a new phase of work, always explicitly ask the user (Fyodor) for permission to continue.**

- **Continuous Task Execution:**
    - **Once a coding task or a sequence of related changes (e.g., fixing a bug and then applying associated styling) is initiated, the AI assistant MUST continue working until the specified elements of that task are fully completed and verified, or until a natural break-point in the sub-task is reached.**
    - **The assistant should not prematurely end its turn or stop its coding session if the immediate, active coding task is still demonstrably unfinished. It should strive to complete the immediate, defined piece of work before yielding.**
