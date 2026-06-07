<p align="center">
  <img src="../assets/images/fiddy_fade_loop_gentle.gif" alt="Fiddy animated header" width="100%">
</p>

# 🥃 Fiddy Documentation

## 📌 Overview

**Fiddy** is an AI-assisted alcohol label verification prototype designed to compare alcohol label
artwork against expected application data.

The application uses local OCR, deterministic validation rules, fuzzy matching for acceptable
textual variation, strict government-warning validation, image-quality diagnostics, batch
processing, performance monitoring, accessibility controls, and reviewer-facing exports.

Fiddy is designed as a **reviewer-assist** workflow. It does not make final compliance decisions,
does not write results back to COLA, and does not require external machine-learning endpoints for
prototype operation.



## 🎯 Documentation Purpose

This documentation supports three audiences:

| Audience                            | What They Need                                                                            |
|-------------------------------------|-------------------------------------------------------------------------------------------|
| Reviewer or evaluator               | How to install, run, operate, and interpret Fiddy.                                        |
| Technical reviewer or CIO-developer | How Fiddy is structured, why design choices were made, and how the code can be inspected. |
| Maintainer or future implementer    | How to validate, extend, package, and deploy the prototype responsibly.                   |



## 🧭 Documentation Guides

| Guide                                    | Purpose                                                                                                                                |
|------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| [Installation](INSTALLATION.md)          | Set up Python, dependencies, Tesseract OCR, Poppler, and the local runtime environment.                                                |
| [User Guide](USER_GUIDE.md)              | Operate Fiddy through the Streamlit interface, including manifest review, manual CAV review, results, downloads, and troubleshooting.  |
| [Examples](EXAMPLES.md)                  | Use Fiddy’s Python modules directly for verification, manifest parsing, OCR inspection, reports, and evidence generation.              |
| [Architecture](ARCHITECTURE.md)          | Review architecture, runtime boundary, major components, data flow, and design patterns.                                               |
| [API Reference](API.md)                  | Inspect source-code API documentation generated from Python docstrings using MkDocs and mkdocstrings.                                  |
| [Acceptance](ACCEPTANCE.md)              | Understand acceptance scope, evidence sources, requirement validation, performance checks, and demonstration readiness.                |
| [Accessibility](ACCESSIBILITY.md)        | Review accessibility posture, Simple Mode expectations, keyboard guidance, and manual validation checklist.                            |
| [Azure Deployment](AZURE_DEPLOYMENT.md)  | Build and deploy Fiddy as an Azure-compatible local-OCR container.                                                                     |
| [Development](DEVELOPMENT.md)            | Follow development workflow, logging rules, validation commands, documentation conventions, and release discipline.                    |
| [PopplerSetup](PATH-POPPLER.md)    | Add Poppler to the Windows PATH so PDF label artwork can be processed for OCR.                                                         |



## 🚀 What Fiddy Demonstrates

Fiddy demonstrates a practical AI engineering approach for a federal review workflow.

| Demonstration Area           | Description                                                                         |
|------------------------------|-------------------------------------------------------------------------------------|
| Local AI-assisted extraction | Uses local OCR to extract evidence from label artwork.                              |
| Deterministic validation     | Uses explicit rules and thresholds rather than opaque final decisions.              |
| Human-in-the-loop review     | Routes uncertainty, low confidence, and visual-format issues to the reviewer.       |
| Batch workflow               | Processes multiple labels through manifest-driven verification.                     |
| Explainable outputs          | Provides status, severity, confidence, explanation, and reviewer action.            |
| Evidence generation          | Produces reports, performance metrics, acceptance outputs, and deployment evidence. |
| Federal deployment posture   | Avoids external ML endpoint dependency and supports Azure-compatible packaging.     |



## 🧠 AI Engineering Posture

Fiddy is **AI-assisted**, not **AI-autonomous**.

The prototype uses OCR to read label artwork, then applies deterministic logic to compare extracted
evidence against expected application data. This keeps the workflow explainable and allows reviewers
to understand why a result passed, failed, generated a warning, or requires human review.

This approach is intentional because alcohol label review includes judgment-sensitive cases, such
as:

* Minor brand-name punctuation or casing differences.
* Low-confidence OCR caused by image quality.
* Government-warning wording differences.
* Visual-format requirements that OCR cannot prove.



## 🧩 Core Components

| Component                         | Responsibility                                                                                                            |
|-----------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| `app.py`                          | Streamlit interface, workflow routing, uploads, reviewer controls, results display, and downloads.                        |
| `config.py`                       | Centralized settings for paths, OCR, upload limits, reports, performance targets, accessibility, and deployment posture.  |
| `booger.py`                       | Sanitized local exception logging.                                                                                        |
| `src/batch_manifest.py`           | Manifest parsing, validation, filename matching, and application-record conversion.                                       |
| `src/batch_processor.py`          | Batch orchestration, per-label isolation, skipped-file handling, timing capture, and batch evidence.                      |
| `src/image_processor.py`          | Image loading, orientation correction, resizing, preprocessing, downscaling, and conservative deskew.                     |
| `src/visual_quality.py`           | Blur, contrast, glare, darkness, skew, size, and readability diagnostics.                                                 |
| `src/ocr_engine.py`               | Local OCR extraction from supported image and PDF files.                                                                  |
| `src/label_field_extractor.py`    | Structured field extraction from OCR text.                                                                                |
| `src/normalizer.py`               | Text, numeric, ABV, proof, net-contents, OCR artifact, and warning normalization.                                         |
| `src/label_rules.py`              | Field-level deterministic comparison rules and fuzzy matching.                                                            |
| `src/warning_validator.py`        | Government-warning presence, exact text, prefix, near-match, and visual-review validation.                                |
| `src/label_verifier.py`           | Single-label OCR, extraction, rule execution, and verification report orchestration.                                      |
| `src/performance_monitor.py`      | Per-label timing, SLA tracking, batch timing summaries, and performance acceptance evidence.                              |
| `src/report_writer.py`            | Redacted summary, detail, comparison, CSV, JSON, and Markdown report generation.                                          |
| `src/data_retention.py`           | Redaction and no-persistence policy enforcement.                                                                          |
| `src/accessibility_checklist.py`  | Manual accessibility validation checklist and evidence records.                                                           |
| `src/deployment_evidence.py`      | Deployment, local-OCR, endpoint, COLA, and data-handling evidence checks.                                                 |
| `src/acceptance_checker.py`       | Stakeholder requirement-status evaluation.                                                                                |
| `src/acceptance_test_harness.py`  | Non-UI acceptance test harness and redacted evidence package generation.                                                  |



## 🧭 Reviewer Workflow

The primary reviewer workflow is:

```text
Upload application data and label artwork
        ↓
Run verification
        ↓
Review results and download outputs
```

Fiddy supports:

* **Simple Mode** for routine reviewer use.
* **Advanced Mode** for diagnostics, acceptance evidence, and technical review.



## 📂 Demonstration Assets

Demonstration files should be organized as:

```text
samples/
├── labels/
└── manifests/
```

Use:

* `samples/labels/` for label artwork.
* `samples/manifests/` for manifest CSV files.

Synthetic demonstration data is planned to support repeatable, non-sensitive local testing.
Synthetic data should be fictional and should not be treated as production data, official TTB
records, or real COLA application data.



## 📊 Outputs

Fiddy can display and export:

| Output                  | Purpose                                                        |
| -- | -- |
| Batch dashboard         | Quick status summary for the current review run.               |
| Summary table           | One row per processed label.                                   |
| Detail table            | One row per rule result.                                       |
| Side-by-side comparison | Application value beside extracted or observed label evidence. |
| Performance table       | Per-label processing time and SLA evidence.                    |
| Summary CSV             | Downloadable batch summary.                                    |
| Detail CSV              | Downloadable rule-level results.                               |
| Comparison CSV          | Downloadable field-level comparison.                           |
| Performance CSV         | Downloadable timing evidence.                                  |
| JSON report             | Structured machine-readable report.                            |
| Markdown report         | Human-readable review report.                                  |



## ✅ Validation Workflow

Before demonstration, run:

```powershell
python -m compileall app.py config.py booger.py src
mkdocs build
```

Then start the application:

```powershell
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

For container validation:

```powershell
docker build -t fiddy:local .
docker run --rm -p 8501:8501 fiddy:local
```



## 🔐 Security and Data Handling

Fiddy follows a conservative prototype posture:

* Local OCR execution.
* No external ML endpoint dependency by default.
* No direct COLA integration.
* No COLA writeback.
* Temporary upload handling.
* Sanitized exception logging.
* Redacted evidence exports by default.
* No intentional long-term storage of uploaded label artwork or raw OCR text.

Production use would require agency-approved identity, access control, audit logging, monitoring,
vulnerability scanning, records-retention handling, and deployment security review.



## ⚖️ Trade-Offs and Limitations

Fiddy intentionally prioritizes a clean, working core prototype over broad but incomplete production
features.

Known limitations include:

* OCR quality depends on source label artwork.
* OCR cannot prove every visual formatting requirement.
* Government-warning visual format requires human confirmation.
* The prototype does not integrate directly with COLA.
* The prototype does not write results back to official systems.
* Formal performance acceptance requires representative runtime evidence.
* Production-scale deployment would require additional security, monitoring, workflow, and
  records-management controls.


