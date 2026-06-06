# Development Guide

This guide describes the recommended development workflow for Fiddy.

Fiddy is a local-first Streamlit prototype for alcohol label verification. Development should
preserve the application’s core posture:

- Local OCR execution.
- Deterministic rule evaluation.
- Explainable reviewer-facing results.
- Temporary upload handling.
- Sanitized exception logging.
- No external machine-learning endpoint dependency.
- Azure-compatible container deployment.

## Development Environment

Recommended local tools:

- Python 3.12 or newer.
- Git.
- PyCharm, Visual Studio Code, or similar IDE.
- Tesseract OCR.
- Poppler for PDF processing.
- Docker Desktop for container validation.
- MkDocs for documentation.

## Repository Layout

```text
Fiddy/
├── app.py
├── config.py
├── booger.py
├── requirements.txt
├── requirements-docs.txt
├── Dockerfile
├── startup.sh
├── .dockerignore
├── mkdocs.yml
├── docs/
├── samples/
│   ├── labels/
│   └── manifests/
├── src/
└── tests/
```

## Local Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install runtime dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install documentation dependencies:

```powershell
python -m pip install -r requirements-docs.txt
```

## Running the Application

Start the Streamlit app from the project root:

```powershell
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## Demonstration Assets

Place local demonstration files in:

```text
samples/
├── labels/
└── manifests/
```

Use `samples/labels` for label artwork and `samples/manifests` for CSV manifests.

Do not place sensitive or production files in the repository.

## Documentation Workflow

MkDocs documentation is built from the `docs/` directory.

Run a local documentation preview:

```powershell
mkdocs serve
```

Build the static documentation site:

```powershell
mkdocs build
```

The generated site is written to:

```text
site/
```

## API Documentation

Fiddy uses MkDocs with mkdocstrings to generate API documentation from Python docstrings.

The source API reference is configured in:

```text
docs/API.md
```

Docstrings should use mkdocstrings-compatible Google style.

### Correct no-argument method docstring

```python
def reset( self ) -> None:
	"""Clear active timers and collected timing results.

	Reset the monitor so the same instance can be reused for a new benchmark,
	smoke test, or batch run.

	Returns:
		None.
	"""
```

### Correct method docstring with arguments

```python
def start( self, file_name: str ) -> None:
	"""Start timing one label file.

	Store the start time for the supplied file name.

	Args:
		file_name (str): Label file name being processed.

	Returns:
		None.
	"""
```

### Do not use

```python
Args:
	None.
```

or:

```python
Parameters:
	None.
```

Those patterns create mkdocstrings/Griffe parsing warnings.

## Validation

Before committing code changes, run:

```powershell
python -m compileall app.py config.py booger.py src
```

Then rebuild documentation:

```powershell
mkdocs build
```

For container-related changes, build the local image:

```powershell
docker build -t fiddy:local .
```

Run the container locally:

```powershell
docker run --rm -p 8501:8501 fiddy:local
```

Open:

```text
http://localhost:8501
```

## Development Rules

When modifying source files:

1. Preserve public class and function names unless the calling code is updated at the same time.
2. Keep runtime logic local-first.
3. Do not add external OCR or external machine-learning endpoint dependencies.
4. Do not log raw OCR text, manifest rows, uploaded file contents, or full file paths.
5. Use temporary storage for uploaded files.
6. Keep Simple Mode reviewer-friendly.
7. Keep Advanced Mode available for diagnostics and acceptance review.
8. Preserve CSV, JSON, Markdown, summary, detail, comparison, and performance exports.
9. Use mkdocstrings-compatible Google-style docstrings.
10. Run `compileall` and `mkdocs build` after changes.

## Logging


```python
try:
	# guarded operation
	pass
except Exception as e:
	error = Error( e )
	error.cause = self.__class__.__name__
	error.module = __name__
	error.method = 'method_name( self ) -> ReturnType'
	Logger( ).write( error )
	return None
```

Do not include raw OCR output, manifest rows, uploaded file contents, or full local file paths in
exception messages.

## Acceptance-Oriented Development

Changes should preserve or improve evidence for these prototype acceptance areas:

| Area | Evidence |
|---|---|
| Label extraction | OCR text and extracted field records. |
| Comparison | Field-level status, severity, confidence, explanation, and reviewer action. |
| Batch processing | Processed files, skipped files, missing files, and report counts. |
| Performance | Per-label timing, SLA status, p50, p90, p95, breach rate, and acceptance status. |
| Accessibility | Simple Mode, high contrast, large text, keyboard checklist. |
| Security | Local OCR, no external ML endpoint, sanitized logging, temporary upload handling. |
| Azure readiness | Dockerfile, startup script, runtime environment variables, local OCR dependencies. |

## Branching and Commit Guidance

Use focused commits:

```text
feature/<short-description>
fix/<short-description>
docs/<short-description>
```

Suggested commit examples:

```text
docs/add-mkdocs-api-reference
fix/sanitize-exception-logging
feature/add-acceptance-checker
feature/add-accessibility-checklist
```

## Pre-Commit Checklist

Before committing:

- `python -m compileall app.py config.py booger.py src` passes.
- `mkdocs build` passes without project docstring warnings.
- `streamlit run app.py` starts locally.
- Upload controls work.
- Manifest upload works.
- Label upload works.
- Verification completes.
- Downloads are available.
- No raw OCR text or manifest rows are written to logs.
- Documentation links render correctly.