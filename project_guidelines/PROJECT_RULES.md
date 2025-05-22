---
description: Core development guidelines for the InChart trading platform project.
globs: "**/*"
alwaysApply: true
---

- **Follow the PRD and Tech Stack**
    - All development must align with the [`PRD.md`](mdc:docs/project_guidelines/PRD.md) and [`TECH_STACK.md`](mdc:docs/project_guidelines/TECH_STACK.md).
    - Prioritize MVP features as outlined in the PRD.

- **API First Design (Backend)**
    - Define API endpoints and data contracts (using Pydantic models in FastAPI) before implementing frontend consumers.
    - Ensure APIs are stateless and use JWT for authentication.

- **Data Integrity and Validation**
    - Backend (FastAPI) is the source of truth for data validation.
    - Validate all incoming data, especially timestamps (must be sorted ascending) for price/signal data.
    - Use Pydantic for request/response validation.

- **Code Clarity and Simplicity**
    - Write clear, concise, and well-documented code.
    - Favor simple solutions, especially for the MVP.
    - Adhere to Python (PEP 8) and Vue.js style guides.

- **Frontend Component Structure**
    - Break down UI into reusable Vue components.
    - Maintain separation of concerns (e.g., API calls in services/Vuex actions, not directly in components).

- **Error Handling**
    - Implement basic but clear error handling on both frontend and backend.
    - Provide user-friendly error messages for common issues (e.g., invalid file upload).

- **Configuration Management**
    - Use environment variables for sensitive information (API keys, DB credentials).
    - Store application-level configurations in dedicated files or modules.
    - Refer to [`CREDENTIALS_LOCATIONS.md`](mdc:docs/project_guidelines/CREDENTIALS_LOCATIONS.md) for details on where specific credentials (like database access, JWT secrets) are stored and managed.

- **Task Management (Task Master AI)**
    - Follow the workflow outlined in [`dev_workflow.mdc`](mdc:.cursor/rules/dev_workflow.mdc).
    - Regularly update task statuses and log progress as per iterative subtask implementation.

- **Styling**
    - Adhere to a minimalistic, clean, "Apple-like" design aesthetic.
    - Use utility-first CSS (e.g., Tailwind CSS if adopted) consistently.

- **Security (MVP Basics)**
    - Ensure all password storage uses strong hashing (e.g., bcrypt via `passlib`).
    - Use HTTPS in production (Nginx/Caddy will handle).
    - Basic input sanitization/validation to prevent common injections.

- **`trading-vue-js` Specifics**
    - Adhere to the data structures expected by `trading-vue-js` for chart data and overlays.
    - Remember all timestamped data for the chart must be sorted in ascending order.

- **Changelog Maintenance**
    - All significant changes to project functionality, architecture, or dependencies must be documented in [`CHANGELOG.md`](mdc:docs/project_guidelines/CHANGELOG.md) following the Keep a Changelog format.
    - Each entry should include version, date, and categorized changes (Added, Changed, Fixed, etc.).
    - Update the changelog before or immediately after merging any feature, fix, or refactor.

- **Error Logging**
    - Any encountered errors, bugs, or unexpected behaviors during development must be logged in [`ERROR_LOG.md`](mdc:docs/internal_dev_log/ERROR_LOG.md).
    - Each error entry should include the date, error description, context/tool, resolution attempts, solution, and key takeaways.
    - Review the error log regularly to identify recurring issues and improve processes.

- **AI Action Logging**
    - Every action performed by the AI assistant must be logged in [`DIARY.md`](mdc:docs/project_guidelines/DIARY.md) with a timestamp, action description, and result.
    - The AI must consult the latest entries in `DIARY.md` before starting new actions to maintain context and avoid redundancy.

- **Version Control and Changelog Management**
    - **Committing Changes:** Adhere to the "Commit Before Significant Changes" rule in [`CRITICAL_RULES.md`](mdc:docs/project_guidelines/CRITICAL_RULES.md).
    - **Commit After Task Completion:** After each task or subtask is marked as 'done', all related code changes, documentation updates (TASKS.md, DIARY.md, CHANGELOG.md), and version counter increments must be committed to the version control system (GitHub) with a descriptive commit message referencing the completed task(s).
    - **GitHub Username:** When using tools to interact with GitHub (e.g., committing, creating PRs), always ensure the username `tarasenkofedor` is used if the tool requires specifying an owner or committer.
    - **Versioning Files:**
        - The project's Semantic Version is tracked in the `VERSION` file in the project root (e.g., `0.1.0`).
        - An internal development stage counter is tracked in `VERSION_COUNTER.txt` in the project root (e.g., `1`, `2`). This is used for `[vX]` tags.
    - **Changelog Updates (`CHANGELOG.md`):**
        - After each significant development stage or completion of a logical block of work, create a new entry in [`CHANGELOG.md`](mdc:docs/project_guidelines/CHANGELOG.md) as per `llmrules.mdc` (using `[vX] - YYYY-MM-DD` format, where `vX` is from `VERSION_COUNTER.txt`).
        - For formal releases (e.g., MVP, major feature milestones):
            1.  Update the `[Unreleased]` section in `CHANGELOG.md` to the new Semantic Version (e.g., `## [0.1.0] - YYYY-MM-DD`).
            2.  Update the `VERSION` file to this new Semantic Version.
            3.  Add a new `## [Unreleased]` section at the top of `CHANGELOG.md` for future changes.

- **Automated Testing (Future Integration)**
    - Once a test suite is established (e.g., using PyTest for backend, Jest/Vitest for frontend):
        - All new features and bug fixes must be accompanied by relevant tests.
        - Tests must be run and pass before committing code that affects functionality.
        - Test execution summaries (pass/fail, coverage if available) should be logged in [`DIARY.md`](mdc:docs/project_guidelines/DIARY.md) or a dedicated test log file.

- **Continuous Integration (CI) (Future Integration)**
    - A CI pipeline (e.g., GitHub Actions) will be implemented to automate:
        - Linting and code style checks.
        - Running automated tests.
        - Potentially, automated builds and deployments.
        - Optionally, validating `CHANGELOG.md` format or `VERSION` consistency.
    - All commits pushed to the main development branch must pass CI checks.

- **Regular Log Review (Guideline)**
    - Periodically review [`ERROR_LOG.md`](mdc:docs/internal_dev_log/ERROR_LOG.md) and [`DIARY.md`](mdc:docs/project_guidelines/DIARY.md) to:
        - Identify recurring issues or patterns.
        - Evaluate the effectiveness of the development workflow.
        - Extract lessons learned to improve future work.

- **AI Task Management Adherence**
    - The AI assistant must strictly follow the rules and procedures defined in [`TASK_RULES.md`](mdc:docs/project_guidelines/TASK_RULES.md) for all task management activities, including status updates, task breakdown, and progress reporting.
    - After completing any task or a significant portion thereof, and before selecting the next task, the AI must re-consult [`TASK_RULES.md`](mdc:docs/project_guidelines/TASK_RULES.md) to ensure compliance. 

- **Backend Python Execution**
    - All Python scripts, FastAPI application launches (via Uvicorn), Alembic commands, and Pytest runs related to the backend **MUST** be executed using the Python interpreter from the designated virtual environment located at `backend/.venv/bin/python`.
    - For example, to run a script `main.py` in the backend, the command should be `backend/.venv/bin/python backend/app/main.py` (adjust path to `main.py` as needed).
    - To run pytest: `backend/.venv/bin/python -m pytest backend/tests` (or similar, depending on test location and pytest command structure).
    - To run alembic: `backend/.venv/bin/alembic [command]`. 
