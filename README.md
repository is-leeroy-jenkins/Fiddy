###### Fiddy

<img src="assets/images/fiddy_fade_loop_gentle.gif" width="1200" height="300">

[![Azure](https://img.shields.io/badge/Azure-Live%20Prototype-0078D4?logo=microsoftazure&logoColor=white)](https://fiddy.lemondune-a14fc806.eastus.azurecontainerapps.io)

[Overview](#-overview) •
[Installation](#-installation) •
[Capabilities](#-capabilities) •
[Documentation](#documentation) •
[Workflow](#-workflow) •
[Architecture](#%EF%B8%8F-architecture) •
[Components](#%EF%B8%8F-component-uml) •
[Usage](#-usage-examples) •
[Outputs](#-outputs) •
[Configuration](#%EF%B8%8F-configuration) •
[Run](#%EF%B8%8F-run-the-app)

## 📌 Overview

**Fiddy** is a local-first, AI-assisted prototype that helps alcohol-label reviewers compare
submitted label artwork against expected application data. The application uses local OCR,
deterministic validation rules, fuzzy matching, image-quality diagnostics, batch processing,
performance monitoring, accessibility controls, and reviewer-facing exports to reduce repetitive
manual comparison work while preserving human judgment.

Fiddy demonstrates how an AI-focused technical solution can be constrained, explainable, auditable,
and deployable in a federal environment where data handling, local execution, firewall restrictions,
accessibility, performance, and reviewer trust matter as much as model capability.

## 🎥 Demo

![](https://github.com/is-leeroy-jenkins/Fiddy/blob/main/assets/images/fiddy-main-demo.gif)



## 🎯 Issue

Alcohol label review involves a large amount of field-by-field comparison:

* Does the brand name on the label match the application?
* Does the class or type designation match?
* Is the alcohol by volume correct?
* Are net contents present?
* Is the producer, bottler, importer, or responsible party present?
* Is country of origin present when applicable?
* Is the mandatory government warning present and correct?

Much of this work is repetitive but still requires judgment. Minor text differences may be
acceptable in ordinary fields, while the government warning must be handled more strictly. Label
artwork may also be imperfect: skewed, low contrast, blurry, glare-affected, or supplied as a PDF.

Fiddy addresses this problem by creating a reviewer-assist workflow that:

1. Extracts label evidence using local OCR.
2. Diagnoses image-quality risk.
3. Compares label evidence against expected application data.
4. Flags mismatches, warnings, and uncertain items.
5. Explains results in reviewer-facing language.
6. Produces downloadable evidence.
7. Keeps the final decision with the human reviewer.



## 🎦 Features

Fiddy provides a clear and practical approach to improving the 
alcohol‑label review process while emphasizing explainability, security, and alignment with analyst
workflows. The prototype is intentionally transparent. If OCR is weak, if an image is difficult 
to read, or if a visual condition requires judgment, Fiddy marks the item for review and explains why.

- **Automated Evidence Extraction** — Local OCR and image diagnostics pull structured text and
  visual cues directly from label artwork to support reliable field‑level comparison.

- **Transparent, Deterministic Matching** — Each field produces a status, severity, confidence
  score, and concise explanation, reflecting an emphasis on clarity and auditability.

- **Batch Processing via Manifest** — A manifest‑driven workflow enables consistent, repeatable
  processing of multiple applications and label sets.

- **Local‑Only Execution** — All OCR, diagnostics, and matching run locally, avoiding external
  inference services and supporting secure, offline operation.

- **Workflow Aligned With Analyst Practice** — The pipeline mirrors real review steps: *Upload →
  Extract → Diagnose → Compare → Flag exceptions → Review → Export.*

- **Modular Architecture** — OCR, diagnostics, matching, and reporting are separated into clear
  components, making the system maintainable, testable, and easy to extend.

- **Human‑in‑the‑Loop Handling** — Low‑confidence or ambiguous fields are routed for manual
  review, reducing false positives and supporting compliance‑oriented decision‑making.

## ✨ Capabilities

| Capability              | What Fiddy Does                                                                         |
|-------------------------|-----------------------------------------------------------------------------------------|
| Label artwork intake    | Accepts image files, PDFs, and ZIP archives containing label artwork.                   |
| Application data intake | Accepts manifest CSV uploads or manual CAV-style entry.                                 |
| Local OCR               | Extracts label text using local Tesseract OCR.                                          |
| Image preparation       | Loads, orients, converts, and prepares label images for OCR.                            |
| Image diagnostics       | Evaluates practical OCR risk factors such as blur, glare, darkness, contrast, and skew. |
| Field comparison        | Compares expected application values against extracted or observed label evidence.      |
| Fuzzy matching          | Tolerates minor text variation where ordinary reviewer judgment would tolerate it.      |
| Strict warning review   | Handles government-warning text separately from ordinary fuzzy fields.                  |
| Batch verification      | Processes matched manifest rows and uploaded files as independent label reviews.        |
| Reviewer guidance       | Provides status, severity, confidence, explanation, and recommended action.             |
| Downloadable reports    | Exports summary, detail, comparison, performance, JSON, and Markdown outputs.           |
| Local diagnostics       | Supports optional SQLite exception logging for troubleshooting.                         |
| Azure fit               | Runs as a standalone local-first workload suitable for Azure-hosted deployment.         |

## 🧠 AI-Assisted Posture

Fiddy is **AI-assisted**, **_not_** **AI-autonomous**.

The AI-enabled portion of the system is OCR-based extraction from label artwork. Once label text is
extracted, Fiddy relies on deterministic validation logic, structured data models, explicit
thresholds, and reviewer-facing explanations.

This architecture reflects several practical federal AI principles:

* **Human accountability remains intact.** Fiddy routes uncertain, low-confidence, or visually
  dependent results to human review.
* **Results are explainable.** Field-level checks include status, severity, confidence, explanation,
  evidence, and reviewer action.
* **AI output is bounded.** OCR output is treated as evidence, not as a final determination.
* **External dependency risk is reduced.** The prototype does not require external machine-learning
  endpoints.
* **Compliance risk is surfaced.** The system distinguishes between text checks that can be
  automated and visual checks that require reviewer confirmation.



## ✨ Core Capabilities

| Capability                                           | Description                                                                   |
|------------------------------------------------------|-------------------------------------------------------------------------------|
| Label artwork intake                                 | Accepts image files, PDFs, and ZIP archives containing label artwork.         |
| Application data intake                              | Accepts manifest CSV uploads or manual CAV-style entry.                       |
| Local OCR                                            | Extracts label text using local Tesseract OCR.                                |
| PDF support                                          | Uses Poppler through `pdf2image` for PDF label artwork conversion.            |
| Image preparation                                    | Loads, orients, resizes, preprocesses, and prepares images for OCR.           |
| Image diagnostics                                    | Evaluates blur, glare, darkness, low contrast, skew, size, and readability.   |
| Field extraction                                     | Extracts likely brand, class/type, ABV, net contents, producer/bottler,country, and warning text.                           |
| Field comparison                                     | Compares expected application values against extracted or observed label evidence.                                            |
| Fuzzy matching                                       | Handles acceptable minor text variations for ordinary fields.                 |
| Government warning validation                        | Checks warning presence, prefix capitalization, exact text, near-match conditions, and visual-review boundaries. |
| Batch verification                                   | Processes matched manifest rows and uploaded label files.                     |
| Performance monitoring                               | Records per-label timing, SLA status, and batch-level performance  metrics.                                             |
| Reviewer guidance                                    | Provides status, severity, confidence, explanation, and recommended action.   |
| Report downloads                                     | Exports summary, detail, comparison, performance, JSON, and Markdown outputs. |
| Accessibility controls                               | Provides Simple Mode, Advanced Mode, high contrast, large text, and keyboard guidance.                                   |
| Evidence generation                                  | Supports acceptance, deployment, accessibility, and performance evidence  outputs.                                             |


## 🏗️ Architecture Overview

Fiddy is organized as a local-first verification pipeline that separates the reviewer interface,
upload handling, manifest parsing, OCR, image-quality analysis, deterministic rules, reporting,
acceptance evidence, and deployment boundary.

<p align="center">
  <img src="assets/images/fiddy-architecture-diagram.png" alt="Fiddy architecture diagram" width="100%">
</p>

## Runtime Boundary

Fiddy runs inside a local or Azure-compatible runtime boundary. The prototype keeps OCR, rule
execution, temporary upload handling, and reviewer-initiated reporting inside the application
boundary.

| Boundary Control                   | Implementation                                                                                        |
|------------------------------------|-------------------------------------------------------------------------------------------------------|
| Local OCR execution                | Label text extraction runs through local OCR tooling rather than an external OCR endpoint.            |
| Deterministic rule execution       | Field comparison, fuzzy matching, warning validation, and review routing run inside the application.  |
| No external ML endpoint dependency | The prototype does not require an external machine-learning endpoint for core operation.              |
| No direct COLA writeback           | Fiddy accepts manifest or manual CAV-style input and does not write results back to COLA.             |
| Temporary upload handling          | Uploaded files are handled during the active review workflow rather than stored as long-term records. |
| Reviewer-initiated reports         | Reports are generated through explicit reviewer download actions.                                     |

### Component Map

<p align="center">
  <img src="assets/images/fiddy-component-map.png" alt="Fiddy component map" width="100%">
</p>

## 🧩 Patterns 

Fiddy is designed around simple, durable, and auditable patterns. The goal is 
to provide a flexible framework of basic components using patterns that can be easily reconfigured 
into a working AI-assisted solution to a common problem across multiple domains and usecases while being
simple for users, maintainable for developers, and defensible in a federal environment.

| Pattern               | Implementation                                                                                                 | Purpose                                                                                                                                                                      |
|-----------------------|----------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Pipelines**         | Upload → normalize → preprocess → OCR → extract → compare → report                                             | Organizes the review process as a clear sequence of independently testable steps. This mirrors the reviewer workflow and makes failures easier to isolate.                   |
| **Facades**           | `AlcoholLabelVerifier`                                                                                         | Provides a single high-level verification interface while hiding the internal coordination of OCR, field extraction, rule execution, and report construction.                |
| **Strategy**          | `AlcoholLabelRules`, `GovernmentWarningValidator`                                                              | Keeps field-specific validation logic separated so brand matching, ABV checks, net-contents checks, importer checks, and government-warning checks can evolve independently. |
| **Adapter**           | `BatchManifestRecord.to_label_application()`                                                                   | Converts CSV manifest rows into the `LabelApplication` model expected by the verification engine. This keeps spreadsheet intake separate from rule execution.                |
| **DTO**               | `LabelApplication`, `ExtractedLabel`, `LabelCheckResult`, `LabelVerificationReport`, `BatchVerificationReport` | Uses explicit structured models to move data between layers safely and predictably. This supports validation, serialization, exports, and testability.                       |
| **Policy**            | `DataRetentionPolicy`                                                                                          | Centralizes redaction, export, and no-persistence decisions so sensitive-data handling is consistent across reports, acceptance evidence, and generated outputs.             |
| **Service**           | `OcrEngine`, `ImageProcessor`, `VisualQualityAnalyzer`, `ReportWriter`, `PerformanceMonitor`                   | Encapsulates focused business or infrastructure operations in dedicated classes instead of concentrating logic in the Streamlit UI.                                          |
| **Observer**          | OCR & batch progress event callbacks                                                                           | Allows processing services to report progress without depending directly on Streamlit. This keeps UI concerns separate from processing logic.                                |
| **Evidence**          | `AcceptanceChecker`, `AcceptanceTestHarness`, `DeploymentEvidenceChecker`, `AccessibilityChecklist`            | Converts runtime behavior into reviewable evidence for stakeholder acceptance, performance validation, deployment readiness, and accessibility review.                       |
| **Anticorruption**    | Upload validation, ZIP handling, fallback reports, sanitized logging                                           | Protects the reviewer workflow from malformed inputs, OCR failures, unsupported files, and unexpected exceptions.                                                            |
| **Human-in-the-Loop** | `Needs Review`, visual warning checks, reviewer-action fields                                                  | Preserves human judgment where automation cannot responsibly make a final determination, especially for low-confidence OCR and visual-format requirements.                   |




## 🧭 Core Workflow

Fiddy supports two primary reviewer workflows.

###  Batch Workflow

```text
Upload manifest CSV
        ↓
Upload label artwork files or ZIP archive
        ↓
Confirm file matching and readiness
        ↓
Run local OCR and deterministic validation
        ↓
Review dashboard and side-by-side comparison
        ↓
Download summary, detail, comparison, performance, JSON, or Markdown outputs
```

### Manual Workflow

```text
Upload label artwork
        ↓
Enter expected CAV-style application values
        ↓
Run local OCR and deterministic validation
        ↓
Review field-level results
        ↓
Download outputs
```

## 🖥️ Simple & Advanced Modes

Fiddy supports both reviewer-friendly operation and technical inspection.

| Mode       | Purpose                                                                                                                                                |
|------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| Simple     | Keeps the workflow focused on upload, run, review, and download.                                                                                       |
| Advanced   | Exposes manifest preview, file matching, OCR diagnostics, image-quality diagnostics, rule detail, worker controls, SLA tuning, and performance timing. |

Simple Mode is intended for routine reviewer use. Advanced Mode is intended for testing,
troubleshooting, demonstration, acceptance review, and technical evaluation.


## 📋 Requirement Traceability

| Requirement Area                                | Fiddy Implementation                                                                                           |
|-------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| Label data extraction                           | `src/ocr_engine.py`, `src/image_processor.py`, `src/label_field_extractor.py`, `src/models.py`                 |
| OCR on imperfect images                         | `src/image_processor.py`, `src/visual_quality.py`, OCR notes,                        image-quality diagnostics |
| Application versus label comparison             | `src/label_rules.py`, `src/label_verifier.py`, side-by-side                          comparison table          |
| Fuzzy matching                                  | `rapidfuzz`, `TextNormalizer`, brand/class/type matching rules                                                 |
| Government warning exact review                 | `src/warning_validator.py`, strict normalized warning                                comparison                |
| Batch upload                                    | `src/batch_manifest.py`, `src/batch_processor.py`, ZIP extraction support in         `app.py`                  |
| Per-label results                               | `BatchVerificationReport`, summary/detail/comparison tables                                                    |
| Five-second performance target                  | `src/performance_monitor.py`, SLA configuration, performance                         exports                   |
| Reviewer outputs                                | Streamlit dashboard, comparison table, CSV/JSON/Markdown downloads                                             |
| Usability                                       | Simple Mode, clear labels, large action controls, minimal routine workflow                                     |
| Reliability                                     | OCR fallback reports, image-quality warnings, missing/skipped file handling                                    |
| Security                                        | Local OCR, no external ML endpoint requirement, sanitized logging, redacted exports                            |
| Prototype scalability                           | Parallel batch processing and 20–50 file acceptance posture                                                    |
| Accessibility                                   | High contrast, large text, keyboard guidance, accessibility checklist                                          |
| Azure readiness                                 | Dockerfile, startup script, local OCR dependencies, Azure deployment                 documentation             |
| No COLA integration                             | Manifest/manual CAV input only; no COLA writeback                                                              |
| No long-term storage                            | Temporary upload handling and data-retention policy controls                                                   |


## ⚠️ Warning Handling

Fiddy treats the government warning as a specialized compliance check. These checks 
are low-hanging fruit easily translated into control points used in SOX404/FMFIA Internal Control frameworks

The validator distinguishes between:

* Warning text missing.
* Warning prefix present.
* Required all-caps prefix present.
* Exact standard warning text present.
* Near match requiring review.
* Visual-format confirmation required.

Fiddy deliberately does **not** claim that OCR text alone can prove visual properties such as
boldness, font size, prominence, contrast, or whether the warning is hidden. Those conditions are
surfaced as reviewer-confirmation items.


## ⏱️ Performance & Acceptance Evidence

Fiddy records per-label timing and batch-level timing metrics.

Performance evidence may include:

* Processing seconds.
* SLA seconds (5).
* Within-SLA status (<=5).
* SLA breach seconds (>=5).
* Average seconds.
* Median seconds.
* P95 seconds.
* SLA breach count.
* SLA breach rate.
* Throughput.
* Performance acceptance status.

The default prototype target is:

```text
LABEL_PROCESSING_SLA_SECONDS = 5.0
```

Fiddy also includes acceptance-oriented components designed to turn runtime behavior into reviewable
evidence.

| Component                        | Purpose                                                       |
|----------------------------------|---------------------------------------------------------------|
| `src/acceptance_checker.py`      | Evaluates stakeholder requirement status from runtime         evidence.                        |
| `src/acceptance_test_harness.py` | Runs non-UI acceptance checks and generates redacted evidence  packages.                        |
| `src/accessibility_checklist.py` | Produces accessibility checklist evidence.                    |
| `src/deployment_evidence.py`     | Evaluates Azure, local-OCR, endpoint, COLA, and data-handling  posture.                         |
| `src/performance_monitor.py`     | Generates SLA and timing evidence.                            |
| `src/report_writer.py`           | Produces redacted summary, detail, JSON, Markdown, and CSV     outputs.                         |



## 🧪 Synthetic Data Generation

Fiddy includes controls for generating synthetic demonstration data under:

```text
samples/
├── labels/
└── manifests/
```

The synthetic-data feature is intended to support repeatable, non-sensitive prototype
demonstrations. Generated files should represent fictional alcohol-label scenarios such as:

* Clean passing labels.
* Fuzzy brand variations.
* ABV mismatches.
* Missing or altered government warnings.
* Low-contrast labels.
* Skewed labels.
* Glare-like images.
* Missing net contents.
* Imported-product cases.

Synthetic data is for demonstration and testing. It should not be treated as production data,
official TTB records, or real COLA application data.
Copy everything between the lines below.


## 🧪 Synthetic Data in Azure

When Fiddy runs locally, the Synthetic Data Generator writes fictional demonstration files under the
local project folders:

```text
samples/manifests/
samples/labels/
```

When Fiddy runs in Azure Container Apps, those same files are generated inside the remote container
filesystem:

```text
/app/samples/manifests/
/app/samples/labels/
```

Because browser upload controls can only browse files on the reviewer’s local computer,
Azure-generated synthetic files will not appear in the local file picker automatically.

For Azure-hosted demonstrations, use this workflow:

```text
Create Synthetic Data
        ↓
Download Synthetic Manifest CSV
        ↓
Download Synthetic Label ZIP
        ↓
Upload the downloaded CSV and ZIP through the normal upload controls
        ↓
Run verification
```

This behavior is expected. The synthetic generator creates fictional demonstration assets only; it
does not bypass upload validation, does not automatically inject files into the review pipeline, and
does not write files to the reviewer’s local computer.

In Azure, first download the generated manifest CSV and label ZIP, then upload those downloaded
files using the normal application upload controls.



## 🧪 Demo Assets

Fiddy includes a local **Synthetic Generator** in the sidebar for creating fictional demonstration
data.

The generator writes one manifest CSV and eight label images under:

```text
samples/
├── labels/
└── manifests/
```

The generated manifest is written to:

```text
samples/manifests/fiddy_v2_demo_manifest.csv
```

The generated labels are written to:

```text
samples/labels/
```

The standard demo pack includes:

```text
fiddy_v2_001_clean_pass.png
fiddy_v2_002_fuzzy_brand.png
fiddy_v2_003_abv_mismatch.png
fiddy_v2_004_missing_warning.png
fiddy_v2_005_low_contrast.png
fiddy_v2_006_skewed_label.png
fiddy_v2_007_imported_product.png
fiddy_v2_008_missing_net_contents.png
```

Use the generated manifest and label files through the normal upload controls. The generator does
not bypass the application workflow and does not automatically load files into Streamlit upload
widgets.

Generated data is fictional and is intended only for local demonstration, testing, and release
validation.

## 🔐 Security & Data Handling

Fiddy follows a conservative prototype security posture.

The application:

* Runs OCR locally.
* Avoids external machine-learning endpoints by default.
* Does not require COLA credentials.
* Does not write results back to COLA.
* Handles uploaded files through temporary runtime storage.
* Uses sanitized exception logging.
* Redacts sensitive fields in evidence exports by default.
* Avoids intentional long-term storage of uploaded label artwork or raw OCR content.

Recommended prototype settings include:

```env
REQUIRE_LOCAL_OCR=true
ALLOW_EXTERNAL_ML_ENDPOINTS=false
ENABLE_UPLOAD_PERSISTENCE=false
ENABLE_RAW_TEXT_LOGGING=false
ENABLE_FILE_PATH_LOGGING=false
ENABLE_RAW_OCR_EXPORT=false
ENABLE_EXTRACTED_DATA_EXPORT=false
ENABLE_REDACTED_EVIDENCE_EXPORT=true
```

## ☁️ Azure Deployment

Fiddy is deployed as an Azure-hosted container application.

- **Azure Service:** Azure Container Apps
- **Resource Group:** Fiddy
- **Container Registry:** 2fiddy.azurecr.io
- **Image:** fiddy:latest
- **Runtime:** Streamlit container
- **OCR:** Local Tesseract OCR inside the container
- **PDF Support:** Poppler inside the container
- **External ML Endpoints:** Disabled
- **COLA Integration:** Disabled
- **Upload Persistence:** Disabled
- **Deployed URL:** https://<your-azure-container-app-url>


## 📁 Repository Structure

```text
Fiddy/
├── app.py
├── booger.py
├── config.py
├── Dockerfile
├── mkdocs.yml
├── requirements.txt
├── requirements-docs.txt
├── startup.sh
├── assets/
│   └── images/
├── docs/
│   ├── ACCEPTANCE.md
│   ├── ACCESSIBILITY.md
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── AZURE_DEPLOYMENT.md
│   ├── DEVELOPMENT.md
│   ├── INSTALLATION.md
│   ├── PATH-POPPLER.md
│   └── USER_GUIDE.md
├── samples/
│   ├── labels/
│   └── manifests/
├── src/
│   ├── acceptance_checker.py
│   ├── acceptance_test_harness.py
│   ├── accessibility_checklist.py
│   ├── batch_manifest.py
│   ├── batch_processor.py
│   ├── constants.py
│   ├── data_retention.py
│   ├── deployment_evidence.py
│   ├── image_processor.py
│   ├── label_field_extractor.py
│   ├── label_rules.py
│   ├── label_verifier.py
│   ├── models.py
│   ├── normalizer.py
│   ├── ocr_engine.py
│   ├── performance_monitor.py
│   ├── report_writer.py
│   ├── visual_quality.py
│   └── warning_validator.py
└── tests/
```

## 📚 Documentation

Full documentation is available in the `docs/` directory and can be built with MkDocs.

| Guide                                        | Purpose                                                                                            |
|----------------------------------------------|----------------------------------------------------------------------------------------------------|
| [Installation](docs/INSTALLATION.md)         | Local Python, OCR, dependency, and runtime setup.                                                  |
| [User Guide](docs/USER_GUIDE.md)             | Reviewer workflow for running Fiddy through the Streamlit interface.                               |
| [Examples](docs/EXAMPLES.md)                 | Programmatic examples for verification, manifests, OCR, reports, acceptance evidence, and logging. |
| [Architecture](docs/ARCHITECTURE.md)         | Architecture, components, design patterns, and data flow.                                          |
| [API Reference](docs/API.md)                 | MkDocs/mkdocstrings API reference generated from docstrings.                                       |
| [Acceptance](docs/ACCEPTANCE.md)             | Acceptance posture, evidence, and validation workflow.                                             |
| [Accessibility](docs/ACCESSIBILITY.md)       | Accessibility features and manual validation checklist.                                            |
| [Azure Deployment](docs/AZURE_DEPLOYMENT.md) | Container and Azure deployment guidance.                                                           |
| [Development](docs/DEVELOPMENT.md)           | Development workflow, validation, logging, and contribution discipline.                            |
| [Poppler Setup](docs/PATH-POPPLER.md)        | Windows Poppler PATH configuration for PDF support.                                                |

## 📚 Build the Documentation

Fiddy uses **MkDocs** with the **Material for MkDocs** theme to build the project documentation from
the Markdown files in the `docs/` directory.

The documentation build supports the project’s reviewer-facing and developer-facing guides,
including installation, user workflow, architecture, API reference, acceptance evidence,
accessibility, Azure deployment, and development notes.

### 📦 Install Documentation Dependencies

Create and activate a virtual environment if one is not already active:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the documentation dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements-docs.txt
```

### 🏗️ Build the Static Site

Run the MkDocs build command from the repository root:

```powershell
mkdocs build
```

A successful build creates the static documentation site under:

```text
site/
```

### 🔍 Preview the Documentation Locally

To preview the documentation in a browser:

```powershell
mkdocs serve
```

Then open:

```text
http://127.0.0.1:8000
```

MkDocs will reload the local preview when documentation files are updated.

### ✅ Recommended Documentation Validation

Before committing documentation changes, run:

```powershell
mkdocs build
```

If code or docstring changes were made, also run:

```powershell
python -m compileall app.py config.py booger.py src
```

This confirms that the documentation builds cleanly and that the Python source files compile before
the repository is pushed or packaged.


## 📥 Installation

For detailed setup instructions, see the Installation Guide:

```text
docs/INSTALLATION.md
```

### Prerequisites

* Python 3.11 or newer.
* Tesseract OCR.
* Poppler for PDF support.
* Git.
* Python virtual environment support.

### Quick Start

```powershell
git clone <repository-url> fiddy
cd fiddy
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Open:

```text
http://localhost:8501
```



## ⚙️ Configuration

Configuration is centralized in `config.py` and may be supplemented by a local `.env` file.

Common settings include:

| Setting                        | Purpose                                    |
|--------------------------------|--------------------------------------------|
| `APP_NAME`                     | Application name.                          |
| `APP_TITLE`                    | Browser and Streamlit title.               |
| `MAX_UPLOAD_MB`                | Upload size guardrail.                     |
| `MAX_BATCH_FILES`              | Maximum batch upload size.                 |
| `MAX_PARALLEL_WORKERS`         | Worker count for batch processing.         |
| `OCR_ENGINE`                   | OCR engine identifier.                     |
| `TESSERACT_CMD`                | Optional path to the Tesseract executable. |
| `OCR_LANGUAGE`                 | OCR language.                              |
| `OCR_TIMEOUT_SECONDS`          | OCR timeout threshold.                     |
| `BRAND_MATCH_THRESHOLD`        | Fuzzy brand-match threshold.               |
| `CLASS_TYPE_MATCH_THRESHOLD`   | Fuzzy class/type threshold.                |
| `LOW_CONFIDENCE_THRESHOLD`     | Low-confidence review threshold.           |
| `LABEL_PROCESSING_SLA_SECONDS` | Per-label processing target.               |
| `REPORT_FILENAME_PREFIX`       | Download filename prefix.                  |
| `LOG_PATH`                     | SQLite exception log database path.        |
| `LOG_FILE`                     | SQLite exception log table name.           |

Example `.env`:

```env
APP_NAME=Fiddy
APP_TITLE=Fiddy
APP_ICON=🥃
OCR_ENGINE=tesseract
OCR_LANGUAGE=eng
OCR_TIMEOUT_SECONDS=5
MAX_UPLOAD_MB=25
MAX_BATCH_FILES=50
MAX_PARALLEL_WORKERS=4
BRAND_MATCH_THRESHOLD=90.0
CLASS_TYPE_MATCH_THRESHOLD=85.0
LOW_CONFIDENCE_THRESHOLD=70.0
LABEL_PROCESSING_SLA_SECONDS=5.0
REPORT_FILENAME_PREFIX=fiddy_report
LOG_PATH=logging/Exceptions.db
LOG_FILE=Exceptions
```

On Windows, if Tesseract is not already on `PATH`:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```



## 📄 Manifest Format

A manifest row represents expected application data for one uploaded label file.

Recommended CSV header:

```csv
file_name,brand_name,class_type,beverage_type,alcohol_content,proof,net_contents,producer_bottler,imported,importer,country_of_origin,cola_id,notes,government_warning
```

Example:

```csv
file_name,brand_name,class_type,beverage_type,alcohol_content,proof,net_contents,producer_bottler,imported,importer,country_of_origin,cola_id,notes,government_warning
old_tom_label.png,OLD TOM DISTILLERY,Kentucky Straight Bourbon Whiskey,Distilled Spirits,45,90,750 mL,Old Tom Distillery LLC,false,,,COLA-001,Demo record,"GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems."
```

### Manifest Columns

| Column               | Description                                                           |
|----------------------|-----------------------------------------------------------------------|
| `file_name`          | Expected uploaded label filename.                                     |
| `brand_name`         | Expected brand name.                                                  |
| `class_type`         | Expected class or type designation.                                   |
| `beverage_type`      | Product category used for review context.                             |
| `alcohol_content`    | Expected ABV value.                                                   |
| `proof`              | Expected proof value when applicable.                                 |
| `net_contents`       | Expected container volume.                                            |
| `producer_bottler`   | Expected producer, bottler, brewer, vintner, importer, or responsible 
 party.               |
| `imported`           | Indicates whether imported-product review applies.                    |
| `importer`           | Expected importer when applicable.                                    |
| `country_of_origin`  | Expected country of origin when applicable.                           |
| `cola_id`            | Optional application or COLA reference.                               |
| `notes`              | Optional reviewer notes.                                              |
| `government_warning` | Expected government-warning text.                                     |



## 📊 Outputs

Fiddy presents results in progressively detailed layers.

### Batch Dashboard

The dashboard provides a quick summary of the current review run:

* Files reviewed.
* Failures.
* Warnings.
* Needs-review items.
* SLA breaches.

### Summary Table

The summary table provides one row per processed label.

### Side-by-Side Comparison

The side-by-side comparison is the primary reviewer surface.

| Column          | Purpose                                               |
|-----------------|-------------------------------------------------------|
| File Name       | Identifies the reviewed label file.                   |
| Field           | Shows the label field being checked.                  |
| Application     | Displays the expected application value.              |
| Extracted       | Displays OCR-derived or rule-observed label evidence. |
| Status          | Shows the review outcome.                             |
| Severity        | Indicates the significance of the finding.            |
| Confidence      | Shows the rule confidence score.                      |
| Explanation     | Explains the finding in reviewer-facing language.     |
| Reviewer Action | Recommends the next reviewer step.                    |

### Downloadable Files

| Output          | Purpose                                              |
|-----------------|------------------------------------------------------|
| Summary CSV     | One row per reviewed label.                          |
| Detail CSV      | One row per rule result.                             |
| Comparison CSV  | Field-by-field application-versus-label comparison.  |
| Performance CSV | Per-label timing data.                               |
| JSON Report     | Structured machine-readable report.                  |
| Markdown Report | Human-readable review report.                        |



## ✅ Run Validation

Before demonstration or commit, run:

```powershell
python -m compileall app.py config.py booger.py src
mkdocs build
```

Then run the application locally:

```powershell
streamlit run app.py
```

For container validation:

```powershell
docker build -t fiddy:local .
docker run --rm -p 8501:8501 fiddy:local
```

Open:

```text
http://localhost:8501
```







## ⚖️ Trade-Offs and Limitations

Fiddy is a working prototype, not a production compliance system.

The implementation intentionally prioritizes a clean, runnable core application over ambitious
features that would be incomplete or inappropriate for the prototype scope.

Known trade-offs and limitations include:

* OCR quality depends on submitted label quality.
* OCR text alone cannot prove visual properties such as boldness, font size, visual prominence, or
  hidden placement.
* Government-warning visual-format checks require human confirmation.
* The prototype does not integrate directly with COLA.
* The prototype does not write results back to any official workflow system.
* The prototype does not require external ML endpoints.
* Synthetic demonstration data is fictional and is not a substitute for formal production testing.
* Formal acceptance evidence requires representative runtime data.
* Azure deployment readiness is documented, but production deployment would require agency-specific
  security review.
* Large-scale production processing would require queueing, monitoring, authentication,
  authorization, audit logging, and records-retention controls.

These trade-offs are deliberate and keep the prototype focused on the core review problem:
extracting label evidence, comparing it to application data, flagging exceptions, and helping
reviewers decide what needs attention.

## 🛣️ Roadmap

Fiddy is a working prototype focused on local OCR, deterministic comparison, reviewer guidance,
batch processing, and Azure-hosted deployment. Future work should preserve the same principles used
in the current implementation: local-first execution where practical, explainable validation, human
accountability, conservative data handling, and clear separation between automated evidence and
final compliance judgment.

Future iterations should improve reliability, deployment simplicity, PDF extraction, local release
packaging, accessibility validation, performance evidence, and production-readiness.

### ✅ Current Prototype Baseline

The current version demonstrates the core review workflow:

```text
Upload application data
        ↓
Upload label artwork
        ↓
Run local OCR
        ↓
Extract label evidence
        ↓
Compare application values to label evidence
        ↓
Flag mismatches, warnings, and review items
        ↓
Export reviewer-facing results
```

The prototype currently supports:

* Local Tesseract OCR.
* Image and PDF label intake.
* ZIP-based batch artwork upload.
* Manifest CSV application-data intake.
* Manual CAV-style data entry.
* Field extraction for common alcohol-label elements.
* Fuzzy matching for ordinary field variation.
* Strict government-warning text validation.
* Human-review routing for uncertain or visual-format-dependent checks.
* Image-quality diagnostics for blur, glare, contrast, darkness, skew, and readability.
* Batch-level results.
* Per-label timing and service-level evidence.
* Redacted CSV, JSON, and Markdown outputs.
* Azure Container Apps deployment.
* No external machine-learning endpoint dependency.
* No direct COLA integration.
* No intentional long-term storage of uploaded label artwork or extracted OCR data.

### 🔜 Near-Term Enhancements

The next phase should improve demonstration reliability, reviewer usability, and acceptance evidence
without changing the basic architecture.

| Area                   | Planned Enhancement                                                                                     | Purpose                                                                                     |
| ---------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Azure demonstration    | Improve Azure-hosted synthetic-data workflow with download/upload guidance and clearer UI messaging.    | Prevent confusion between local files and files generated inside the Azure container.       |
| Runtime evidence       | Add a visible Azure smoke-test panel or acceptance summary in the UI.                                   | Make deployment, OCR, no-external-ML, no-COLA, and no-persistence posture easier to verify. |
| Performance validation | Add a repeatable 20–50 label benchmark run using the synthetic demo pack.                               | Produce stronger evidence for the five-second-per-label performance target.                 |
| Error visibility       | Improve reviewer-safe messages when OCR, upload validation, ZIP extraction, or report generation fails. | Make failures actionable without exposing sensitive file paths or raw OCR content.          |
| Documentation          | Expand Azure deployment, synthetic-data, acceptance, and troubleshooting sections.                      | Help users reproduce the deployment and test workflow.                                      |
| Accessibility          | Complete browser-level keyboard testing and document results.                                           | Move accessibility from source-supported to manually verified.                              |

### 🔁 Ongoing Improvement Needs

Fiddy should be treated as a working prototype that will require continuous refinement as more
realistic labels, reviewer feedback, deployment constraints, and performance evidence become
available. The current implementation demonstrates the core workflow, but production readiness would
require repeated evaluation, tuning, and hardening.

Ongoing improvement areas include:

* OCR accuracy testing against more realistic label artwork.
* Field-extraction tuning for varied label layouts and typography.
* Better handling of distorted, skewed, low-contrast, blurry, or glare-affected images.
* Reviewer feedback loops for false positives, false negatives, and unclear explanations.
* Performance tuning for larger batches and Azure-hosted execution.
* Accessibility validation across browsers, screen sizes, and keyboard-only workflows.
* Security hardening for authentication, authorization, logging, upload handling, and data
  retention.
* Documentation updates as deployment, limitations, and acceptance evidence mature.
* Regression testing for rule changes, OCR changes, and report-format changes.
* Continued separation between automated evidence and final human compliance judgment.

The project should preserve the current design discipline: automation should assist reviewers, not
obscure uncertainty or replace required judgment.

### 🔄 PDF Extraction and Poppler Replacement

The current prototype uses Poppler through `pdf2image` to convert PDF label artwork into image pages
before OCR. This approach works in some local and containerized scenarios, but recent deployment and
setup work exposed practical friction around PDF extraction, dependency installation, PATH
configuration, runtime portability, and container behavior.

Those difficulties make PDF processing an important roadmap item. A future version of Fiddy should
explore replacing Poppler, or at least providing a reliable fallback, so PDF extraction is less
fragile across Windows, local development, Docker, and Azure-hosted environments.

Potential replacement or fallback options include:

| Option                           | Purpose                                                                          | Consideration                                                                    |
| -------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| PyMuPDF / `fitz`                 | Render PDF pages directly from Python.                                           | May reduce reliance on Poppler command-line tools and simplify deployment.       |
| `pypdfium2`                      | Render PDF pages through PDFium bindings.                                        | May provide a more portable rendering path than Poppler in some environments.    |
| Image-only upload requirement    | Require reviewers or submitters to upload PNG/JPG label artwork instead of PDFs. | Simplifies runtime dependencies but reduces upload flexibility.                  |
| Pre-converted PDF workflow       | Convert PDFs to images before upload.                                            | Keeps Fiddy simpler but shifts conversion responsibility outside the app.        |
| Dual-path PDF handling           | Use Poppler when available and fallback to PyMuPDF or PDFium when Poppler fails. | Improves resilience but requires additional testing and clear error handling.    |
| Azure-approved document handling | Evaluate Azure-native document processing only if policy permits.                | Must not violate the no-external-ML-endpoint posture required for the prototype. |

Recommended future direction:

```text
Short term:
Keep Poppler in the Docker container because it currently supports the deployed prototype and preserves PDF intake.

Medium term:
Prototype PyMuPDF or pypdfium2 as a Poppler replacement or fallback, using the same label PDFs that recently caused setup and extraction friction.

Long term:
Select the PDF rendering approach that best balances OCR accuracy, security, maintainability, deployment simplicity, Windows compatibility, Azure compatibility, and federal environment constraints.
```

A replacement should not weaken the core design constraint: PDF label artwork must be converted into
OCR-ready images without relying on blocked external machine-learning endpoints, unauthorized
services, or fragile manual setup steps.

### 📦 Locally Downloadable Releases

Future iterations of Fiddy should include locally downloadable release packages in addition to the
Azure-hosted prototype. The Azure deployment is valuable for demonstrating cloud readiness, but
recent testing showed that cloud-hosted execution introduces practical nuances that can confuse
reviewers during demonstration.

Examples include:

* Synthetic files generated inside the Azure container are written to `/app/samples/...`, not to the
  reviewer’s local machine.
* Browser upload controls cannot browse files from the remote container filesystem.
* Generated demo files must be downloaded from the Azure app before they can be uploaded through the
  normal review workflow.
* Container filesystem behavior differs from local project-folder behavior.
* Azure runtime configuration, ingress settings, registry setup, and revision behavior add
  deployment-specific complexity.
* Troubleshooting Azure-hosted behavior often requires portal logs, container logs, or deployment
  settings rather than local file inspection.

To reduce those frictions, future releases should provide a downloadable local package that can be
run directly by evaluators, reviewers, or technical staff.

Recommended local release options include:

| Release Type                    | Purpose                                                              | Consideration                                                                               |
| ------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Source ZIP                      | Provides the full repository as a versioned release artifact.        | Simple and transparent, but still requires Python, Tesseract, and Poppler or a replacement. |
| Preconfigured local package     | Includes source code, setup scripts, sample data, and documentation. | Easier for reviewers, but requires platform-specific packaging.                             |
| Docker image release            | Allows users with Docker to run the app consistently.                | Avoids Python setup, but still depends on local Docker availability.                        |
| Windows-oriented release bundle | Supports the most likely reviewer workstation environment.           | Should minimize PATH setup, OCR dependency friction, and PDF-rendering issues.              |
| Image-only demo package         | Includes pre-generated PNG/JPG labels and manifest CSV.              | Avoids PDF extraction and synthetic-generation location confusion during demos.             |

Recommended future direction:

```text
Short term:
Publish a tagged GitHub release containing the source ZIP, synthetic manifest CSV, synthetic label ZIP, and clear local run instructions.

Medium term:
Create a local evaluator package with pre-generated demo files so reviewers do not need to run the synthetic generator before testing.

Long term:
Provide a more polished local release that minimizes dependency setup, reduces reliance on fragile PATH configuration, and includes a Poppler replacement or fallback if adopted.
```

The goal is not to replace Azure deployment. The goal is to provide both paths:

```text
Azure-hosted prototype
        +
Locally downloadable evaluation release
```

This gives users a working Azure URL while also offering a simpler local demonstration path that
avoids cloud-container filesystem nuances, Azure portal configuration issues, and remote runtime
troubleshooting.

### 🧪 Acceptance and Evaluation Improvements

Future versions should make acceptance evidence easier to generate, review, and archive.

Planned improvements include:

* One-click acceptance evidence generation from the UI.
* Downloadable acceptance package with redacted evidence only.
* Batch performance report showing average, median, p95, breach count, and breach rate.
* Deployment evidence showing Azure runtime, local OCR configuration, and disabled external ML
  endpoints.
* Accessibility checklist export.
* Synthetic-data test run summary.
* Clear pass, warning, fail, and needs-review counts for stakeholder review.

### 🖼️ OCR and Image Handling Improvements

The prototype already handles basic image diagnostics and preprocessing. A production-grade version
could improve OCR reliability through stronger image-processing controls.

Future OCR and image improvements may include:

* Automatic deskewing before OCR.
* Better PDF page handling and page selection.
* Optional image crop suggestions.
* Improved glare detection.
* Improved low-contrast enhancement.
* Layout-aware text grouping.
* Better extraction of producer, bottler, importer, and address blocks.
* Confidence scoring tied more directly to OCR quality and field-specific extraction quality.
* OCR regression tests using controlled synthetic and real-world-style labels.

### ⚖️ Compliance Rule Enhancements

The current prototype uses deterministic rules and reviewer-facing explanations. Future versions
could broaden the compliance rule set while preserving explainability.

Potential rule enhancements include:

* Beverage-type-specific label rules for distilled spirits, wine, malt beverages, and beer.
* Required-field rule sets by product category.
* More precise alcohol-content formatting checks.
* Net-contents unit normalization and tolerance handling.
* Producer, bottler, importer, and responsible-party address validation.
* Country-of-origin checks for imported products.
* Expanded government-warning formatting checklist.
* Rule versioning for auditability.
* Configurable thresholds for fuzzy matching and confidence routing.
* Reviewer override notes and disposition categories.

### 👤 Human-in-the-Loop Workflow

Fiddy should remain reviewer-assistive rather than reviewer-replacing. Future workflow improvements
should make human judgment easier to capture and explain.

Planned human-review enhancements include:

* Reviewer override controls.
* Reviewer notes at the field and label level.
* Review disposition categories such as approved, rejected, needs resubmission, and manual review
  required.
* Exportable reviewer decision summaries.
* Clear separation between automated evidence and reviewer determination.
* Optional second-review workflow for high-severity findings.

### 📦 Batch Processing Enhancements

The prototype supports small-to-medium batch review. Larger or production-style batch operations
should be handled through more durable patterns.

Potential batch improvements include:

* Queue-based batch processing.
* Background job status tracking.
* Retry handling for failed labels.
* Batch pause/resume.
* Large-batch chunking.
* Parallel processing controls by runtime size.
* Batch-level exception summaries.
* Reviewer assignment by batch or importer.
* Exportable batch audit packages.

### 🔐 Security and Data Governance Enhancements

The prototype uses conservative local-first and no-persistence defaults. A production deployment
would require formal security and governance controls.

Future security work may include:

* Microsoft Entra ID authentication.
* Role-based access control.
* Private Azure networking.
* Managed identity for Azure resource access.
* Secure secret management through Azure Key Vault.
* Malware scanning for uploaded files.
* Formal records-retention policy integration.
* Configurable data-retention periods.
* Structured audit logging.
* Security review and authorization package support.
* Separation between prototype logs and compliance records.

### ☁️ Azure Production Hardening

The current Azure deployment is suitable for prototype demonstration. A production deployment would
require additional Azure architecture decisions.

Potential Azure hardening includes:

* Private Azure Container Apps environment.
* Azure Container Registry private networking.
* Managed identity instead of registry username/password.
* Azure Key Vault integration.
* Log Analytics dashboards.
* Application Insights telemetry.
* Health probes and alerting.
* Autoscaling rules based on HTTP traffic or queue depth.
* Deployment slots or revision-based release workflow.
* Infrastructure-as-code deployment through Bicep, Terraform, or Azure Developer CLI.
* GitHub Actions deployment with environment approvals.
* Container image vulnerability scanning.

### 🔗 COLA and Enterprise Integration

The current prototype intentionally does not integrate directly with COLA. Any future COLA
integration should be handled as a separate governed effort.

Potential long-term integration options include:

* Read-only COLA application-data import.
* Authorized API integration if available.
* Controlled writeback only after formal approval.
* Reviewer decision synchronization.
* Case-management integration.
* Records-management integration.
* Audit trail integration.
* Procurement-ready architecture documentation.

### 🤖 Machine Learning Enhancements

Fiddy does not require external machine-learning endpoints for the prototype. Future
machine-learning work should be carefully bounded, tested, and explainable.

Possible future enhancements include:

* Fine-tuned OCR models for stylized label fonts.
* Layout detection for complex labels.
* Field-level extraction models.
* Confidence calibration.
* Human-feedback loops for extraction improvement.
* Model performance monitoring.
* Bias and error analysis across label styles.
* Offline or Azure-approved model hosting only.
* Clear fallback to deterministic rules and human review.

### 📚 Documentation Roadmap

Documentation should continue to support both reviewers and technical evaluators.

Planned documentation improvements include:

* Expanded Azure deployment guide.
* Azure troubleshooting guide.
* Synthetic-data workflow guide.
* Acceptance evidence guide.
* Accessibility validation guide.
* Reviewer quick-start guide.
* Developer setup guide.
* API reference generated from docstrings.
* Architecture decision records.
* Known limitations and trade-offs.
* Release notes for each tagged version.

### 🧭 Long-Term Vision

The long-term vision for Fiddy is a secure, explainable, reviewer-centered compliance-assistance
platform that reduces repetitive manual comparison work while preserving human accountability.

A mature version would support:

* Reliable application-to-label comparison.
* Scalable batch processing.
* Strong evidence trails.
* Accessibility-compliant reviewer workflows.
* Approved Azure-hosted infrastructure.
* Formal data governance.
* Controlled enterprise integration.
* Continuous performance and quality monitoring.
* Clear distinction between automated evidence and official compliance decisions.

Fiddy should remain focused on helping reviewers move faster, identify exceptions earlier, and
document findings more consistently without obscuring the judgment required in alcohol-label
compliance review.

## 👶 Dependencies

Fiddy uses a compact Python dependency stack focused on a Web UI, local OCR, image processing,
fuzzy matching, structured models, and test automation.

| Package                  | Version      | Purpose                                                                                                                     |
|--------------------------|--------------|-----------------------------------------------------------------------------------------------------------------------------|
| `streamlit`              | `1.56.0 < 2` | Provides the web application framework, upload controls, sidebar controls, review workflow, tables, metrics, and downloads. |
| `pandas`                 | `2.2.3`      | Handles manifest CSV loading, validation tables, summary tables, detail tables, comparison tables, and CSV exports.         |
| `numpy`                  | `2.2.6`      | Supports numeric operations used by image analysis, preprocessing, and data handling.                                       |
| `pillow`                 | `11.2.1`     | Loads and manipulates image files before OCR, including mode conversion and orientation handling.                           |
| `opencv-python-headless` | `4.11.0.86`  | Supports image preprocessing and visual-quality analysis without requiring GUI libraries.                                   |
| `pytesseract`            | `0.3.13`     | Provides the Python wrapper around the local Tesseract OCR engine.                                                          |
| `rapidfuzz`              | `3.13.0`     | Performs fast fuzzy text matching for reviewer-tolerant comparisons such as brand and class/type.                           |
| `pydantic`               | `2.11.5`     | Defines structured application, extraction, rule-result, report, and batch-processing models.                               |
| `python-dotenv`          | `1.1.0`      | Loads environment-based configuration from `.env` files.                                                                    |
| `pdf2image`              | `1.17.0`     | Converts PDF label artwork into images for OCR processing.                                                                  |

### System Dependencies

Some Python packages require external system tools.

| Dependency                                                        | Required For   | Notes                                                                        |
|-------------------------------------------------------------------|----------------|------------------------------------------------------------------------------|
| [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)    | OCR extraction | Required by `pytesseract`. Must be installed on the host or container image. |
| [Poppler](https://github.com/oschwartz10612/poppler-windows)      | PDF processing | Required by `pdf2image` when processing PDF label artwork.                   |



## 👮 License

Fiddy is distributed for free and available for general use under the MIT license located [here](https://github.com/is-leeroy-jenkins/Fiddy/blob/main/LICENSE.txt).



