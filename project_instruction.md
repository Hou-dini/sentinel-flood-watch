# Software Engineering Philosophy & Best Practices Guide

This document defines core software engineering principles, coding practices, and deployment guidelines for building resilient AI agent systems.

## 1. SOLID Design Principles in Agent Development
- **Single Responsibility Principle (SRP):**
  - Divide agents, tools, and database controllers into distinct modules. An agent should only reason, a tool should only execute a specific function, and the database controller should only persist data.
  - *Example:* Avoid writing database logic directly in GEE image processing tools.
- **Open/Closed Principle (OCP):**
  - Build agents to be extensible via modular sub-agents and toolsets. Adding new capabilities should involve adding a new tool to the `tools` array rather than rewriting the agent's core loop.
- **Liskov Substitution Principle (LSP):**
  - Custom agents inheriting from `BaseAgent` must adhere to the async run contracts (`_run_async_impl`) without breaking sequential or parallel workflows.
- **Interface Segregation Principle (ISP):**
  - Expose narrow tool interfaces. Do not pass the entire application context to a simple calculation tool unless it requires state read/write access via `ToolContext`.
- **Dependency Inversion Principle (DIP):**
  - Depend on abstractions (like the `ArtifactService` base class or database helper interfaces) rather than concrete implementations (like `GcsArtifactService` or direct MongoDB clients). This enables seamless local fallback to `InMemoryArtifactService` or JSON DB files.

## 2. Version Control & Git Guidelines
- **Commit Granularity:** Make small, self-contained commits. A commit should address a single feature or bug fix.
- **Descriptive Messages:** Use conventional commit formatting:
  - `feat: add GEE NDVI index calculation`
  - `fix: resolve Windows stdout encoding error`
  - `docs: update design spec with Accra coordinates`
- **Branching Strategy:** Keep the `main` branch stable. Work on feature branches (`feat/satellite-pipeline`) and merge via Pull Requests after passing evaluation runs.

## 3. Continuous Integration & Continuous Delivery (CI/CD)
- **Local Testing First:** Use pytest for unit tests and local `adk eval` runs for LLM evaluation before pushing changes.
- **Automated DevOps (GitHub Actions):** 
  - Automate linters (`ruff check .`) and type checks (`ty`) to enforce code formatting and catch static analysis bugs before merging.
  - **Environment-Safe Tests:** Configure runners to execute only unit tests (`tests/unit/`) under mock conditions. Avoid running cloud-dependent integration tests on public runners where service account keys cannot be safely stored.
  - **Dependency Caching:** Use cached execution runners (such as caching the `uv` package manager and `.venv` builds) to reduce pipeline runtime.
- **Immutable Infrastructure:** Define deployment environments using Terraform to guarantee consistency between staging and production instances on Vertex AI Agent Engine.

## 4. Observability and Fail-Safe Engineering
- **Graceful Degradation:** When external cloud services (like Google Earth Engine or MongoDB Atlas) are unavailable, the application must fall back to local mocks or JSON files instead of crashing.
- **End-to-End Tracing:** Always instrument LLM operations and tools with OpenTelemetry to track execution latency, input/output structures, and tool failures.

## 5. Deployment Containerization (Docker)
- **Multi-Stage Builds:** Use multi-stage Dockerfiles. Build dependencies inside a python-builder stage using `uv` and copy only the compiled virtual environment (`.venv`) and source code to the final runtime stage. This results in minimal production image sizes and reduces vulnerable dependencies.
- **Environment Secret Isolation:** Never burn API keys, passwords, or service account files (`gee-key.json`) directly into the image layers. Retrieve secrets at runtime using environment variables (`.env` files) or securely mount credential directories via volumes.
- **Service Orchestration (Docker Compose):** Coordinate multi-container applications (e.g. connecting the FastAPI backend service to a persistent MongoDB database service) using Docker Compose. Make sure to define local volume mounts (`/data/db`) for persistent database storage across container restarts.
- **Build Context Exclusions:** Maintain a robust `.dockerignore` file in the project root to exclude local virtual environments (`.venv`), temporary testing/caching directories (`.pytest_cache`, `__pycache__`), credentials, and git logs to prevent leaking secrets and bloating build contexts.

