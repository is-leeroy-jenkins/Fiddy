# 👤 User Guide

## 🎯 Purpose

**Fiddy** is an AI-assisted alcohol label verification prototype. It helps reviewers compare alcohol
label artwork against expected application data using local OCR, deterministic validation rules,
fuzzy matching, image-quality diagnostics, batch processing, performance monitoring, and
reviewer-facing exports.

Fiddy is designed to assist review. It does **not** make final compliance decisions and does **not**
write results back to COLA or any official workflow system.

## 👥 Who This Guide Is For

This guide is written for reviewers, evaluators, and demonstration users who need to run Fiddy
through the Streamlit interface.

For installation instructions, see:

```text
docs/INSTALLATION.md
```

For programmatic Python examples, see:

```text
docs/EXAMPLES.md
```

For architecture and design details, see:

```text
docs/ARCHITECTURE.md
```

## 🧭 Reviewer Workflow Overview

Fiddy supports a short reviewer workflow:

```text
Upload application data and label artwork
        ↓
Run verification
        ↓
Review results and download outputs
```

The application supports two primary operating paths:

1. **Manifest Batch Workflow** — Upload a CSV manifest and one or more label files.
2. **Manual CAV Workflow** — Enter expected application values manually and upload label artwork.

## 🖥️ Reviewer Modes

Fiddy supports two display modes.

| Mode              | Purpose                                                                                                                                                     |
| -- | -- |
| **Simple Mode**   | Keeps the screen focused on the routine reviewer workflow.                                                                                                  |
| **Advanced Mode** | Shows diagnostics, manifest previews, file-matching information, OCR details, image-quality results, performance timing, and additional technical evidence. |

Use **Simple Mode** for routine demonstration and review.

Use **Advanced Mode** when validating requirements, troubleshooting OCR behavior, reviewing batch
matching, or preparing acceptance evidence.

## ♿ Accessibility Controls

Fiddy includes reviewer-facing accessibility controls.

| Control               | Purpose                                                  |
|  | -- |
| **High Contrast**     | Improves readability by increasing visual contrast.      |
| **Large Text**        | Enlarges text and controls for easier reading.           |
| **Keyboard Guidance** | Provides workflow guidance for keyboard-based operation. |

Accessibility behavior should be manually validated in the browser used for demonstration.

## 📂 Input Files

Fiddy uses two types of input:

1. **Application data**
2. **Label artwork**

### 📋 Application Data

Application data may be supplied by:

* Uploading a manifest CSV file.
* Entering values manually in the CAV-style form.

### 🖼️ Label Artwork

Label artwork may be supplied as:

* PNG image.
* JPG or JPEG image.
* WEBP image.
* BMP image.
* TIF or TIFF image.
* PDF file, when Poppler is installed.
* ZIP archive containing supported label files.

## 📦 Manifest Batch Workflow

Use this workflow when you want to process multiple labels.

### Step 1 — Open Fiddy

Start Fiddy locally:

```powershell
streamlit run app.py
```

Then open the local Streamlit URL in your browser:

```text
http://localhost:8501
```



### Step 2 — Select Simple Mode or Advanced Mode

For a clean demonstration, use **Simple Mode**.

Use **Advanced Mode** if you want to inspect manifest rows, uploaded-file matching, OCR diagnostics,
image-quality warnings, rule details, or performance timing.



### Step 3 — Upload the Manifest CSV

Use the manifest upload control to select the CSV file containing expected application data.

The recommended manifest header is:

```csv
file_name,brand_name,class_type,beverage_type,alcohol_content,proof,net_contents,producer_bottler,imported,importer,country_of_origin,cola_id,notes,government_warning
```

Each manifest row should identify one expected label file through the `file_name` column.

Example:

```csv
file_name,brand_name,class_type,beverage_type,alcohol_content,proof,net_contents,producer_bottler,imported,importer,country_of_origin,cola_id,notes,government_warning
old_tom_label.png,OLD TOM DISTILLERY,Kentucky Straight Bourbon Whiskey,Distilled Spirits,45,90,750 mL,Old Tom Distillery LLC,false,,,COLA-001,Demo record,"GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems."
```



### Step 4 — Upload Label Artwork

Upload the label files that correspond to the manifest rows.

You may upload:

* Individual image files.
* Individual PDF files.
* A ZIP archive containing supported label files.

For batch testing, the label filenames should match the `file_name` values in the manifest.



### Step 5 — Confirm Readiness

After the manifest and labels are uploaded, Fiddy should indicate whether the batch is ready for
verification.

If Fiddy reports that the batch is not ready, check:

* The manifest was uploaded.
* At least one label file was uploaded.
* Manifest `file_name` values match uploaded label filenames.
* Required manifest columns are present.
* Uploaded file types are supported.



### Step 6 — Run Verification

Click:

```text
Run Verification
```

Fiddy will process the uploaded label files using local OCR, image-quality diagnostics, field
extraction, deterministic rule checks, and performance monitoring.

During processing, Fiddy may show progress indicators or status messages.



### Step 7 — Review the Batch Dashboard

After processing, review the dashboard summary.

Common dashboard values include:

* Files reviewed.
* Passed labels.
* Failed labels.
* Warning labels.
* Needs-review labels.
* SLA breaches.
* Processing timing.

The dashboard is intended to provide a quick first look at the batch result.



### Step 8 — Review the Side-by-Side Comparison

The side-by-side comparison is the primary review surface.

Expected columns include:

| Column              | Meaning                                               |
| - | -- |
| **File Name**       | Label file being reviewed.                            |
| **Field**           | Label field or rule being checked.                    |
| **Application**     | Expected application value.                           |
| **Extracted**       | OCR-derived or rule-observed value.                   |
| **Status**          | Pass, Warning, Fail, Needs Review, or Not Applicable. |
| **Severity**        | Importance of the finding.                            |
| **Confidence**      | Strength of the rule or match result.                 |
| **Explanation**     | Plain-language explanation of the result.             |
| **Reviewer Action** | Recommended reviewer action.                          |



### Step 9 — Download Outputs

Fiddy may provide several downloadable outputs.

| Output              | Purpose                                    |
| - |  |
| **Summary CSV**     | One row per reviewed label.                |
| **Detail CSV**      | One row per rule result.                   |
| **Comparison CSV**  | Application-versus-label comparison table. |
| **Performance CSV** | Per-label timing data.                     |
| **JSON Report**     | Structured machine-readable report.        |
| **Markdown Report** | Human-readable review report.              |

Download outputs only when needed. Fiddy is designed so report generation is reviewer-initiated.

## 📝 Manual CAV Workflow

Use this workflow when you want to test or review a single label without a manifest.

### Step 1 — Upload Label Artwork

Upload one supported label image or PDF.



### Step 2 — Enter Expected Application Values

Enter expected values in the manual CAV-style form.

Typical fields include:

* Brand name.
* Class/type.
* Beverage type.
* Alcohol content.
* Proof.
* Net contents.
* Producer or bottler.
* Imported indicator.
* Importer, when applicable.
* Country of origin, when applicable.
* Government warning.
* COLA or application reference.
* Notes.



### Step 3 — Run Verification

Click:

```text
Run Verification
```

Fiddy will OCR the uploaded artwork, run field checks, and create a verification result.



### Step 4 — Review Results

Review:

* Overall status.
* Field-level results.
* Severity.
* Confidence.
* Explanation.
* Reviewer action.
* OCR and image-quality notes, if available.



### Step 5 — Download Outputs

Download any available CSV, JSON, or Markdown outputs if needed for review, demonstration, or
evidence.

## 🧪 Synthetic Data

Fiddy is planned to include a sidebar control for generating synthetic demonstration data.

The purpose of synthetic data is to allow reviewers and evaluators to test the prototype without
using real application data or real alcohol label submissions.

Generated files are expected to be written under:

```text
samples/
├── labels/
└── manifests/
```

Synthetic data should be treated as fictional demonstration content only.



## Generating Synthetic Demo Data

When the synthetic data feature is available, use the sidebar expander labeled something similar to:

```text
Generate Synthetic Demo Data
```

Expected controls may include:

* Number of labels.
* Scenario mix.
* Random seed.
* Generate button.
* Optional clear generated samples button.

Possible scenario types may include:

* Clean passing labels.
* Fuzzy brand variations.
* ABV mismatches.
* Missing government warning.
* Altered government warning.
* Low-contrast label.
* Skewed label.
* Glare-like image.
* Missing net contents.
* Imported-product case.

After generation, upload the generated manifest from:

```text
samples/manifests/
```

Then upload generated labels from:

```text
samples/labels/
```

## 🚦 Understanding Result Status

Fiddy uses reviewer-facing status values.

| Status             | Meaning                                                               |
|  |  |
| **Pass**           | The rule or field appears to meet the expected condition.             |
| **Warning**        | The field may be acceptable but should be reviewed.                   |
| **Fail**           | The field appears to conflict with the expected value or requirement. |
| **Needs Review**   | Fiddy cannot responsibly determine the result automatically.          |
| **Not Applicable** | The rule does not apply to the current label or application data.     |

## 📊 Understanding Severity

Severity describes the significance of the finding.

| Severity     | Meaning                                         |
|  | -- |
| **Info**     | Informational result.                           |
| **Low**      | Minor issue or low-risk review item.            |
| **Medium**   | Review item that may require attention.         |
| **High**     | Significant issue or likely compliance concern. |
| **Critical** | Highest severity condition, when used.          |

## 🎚️ Understanding Confidence

Confidence is a rule-specific score that helps the reviewer understand how strongly Fiddy matched or
evaluated the evidence.

A high confidence value generally means the rule had strong evidence.

A low confidence value means the result should be reviewed more carefully.

Confidence should not be treated as a final compliance decision.

## 🧑‍⚖️ Understanding Reviewer Action

Reviewer action text explains what the reviewer should do next.

Examples include:

* Accept field as matching.
* Review minor text variation.
* Confirm visually.
* Request clearer artwork.
* Correct application data.
* Reject or route for further review.
* Review government warning manually.

Reviewer action text is intentionally visible and should not depend only on mouse hover.



## ⚠️ Government Warning Review


The government warning is handled separately from ordinary fuzzy matching.

Fiddy may check:

* Whether warning text appears to be present.
* Whether the `GOVERNMENT WARNING:` prefix appears.
* Whether the prefix appears in all caps.
* Whether the standard warning text appears exactly after normalization.
* Whether a near match should be treated as a failure or review condition.
* Whether visual formatting requires manual confirmation.

Fiddy does not claim that OCR text alone can prove:

* Boldness.
* Font size.
* Label placement.
* Contrast.
* Visual prominence.
* Whether the warning is hidden.

Those visual conditions should be reviewed by a human.

## 🖼️ Image-Quality Notes

Fiddy may report image-quality warnings that explain OCR risk.

Common image-quality issues include:

| Issue                | Meaning                                                       |
| -- | - |
| **Blur**             | Text may be too blurry for reliable OCR.                      |
| **Glare**            | Bright reflections may hide text.                             |
| **Low contrast**     | Text and background may be too similar.                       |
| **Darkness**         | Image may be too dark.                                        |
| **Skew**             | Label may be tilted or photographed at an angle.              |
| **Small image size** | Image may not contain enough pixels for reliable OCR.         |
| **Low readability**  | Composite readability score suggests manual review is needed. |

Image-quality warnings do not necessarily mean the label fails. They mean OCR evidence may be less
reliable.

## 🔍 Advanced Diagnostics

Advanced Mode may expose additional information such as:

* Manifest preview.
* Uploaded-file preview.
* File matching diagnostics.
* OCR text.
* Image-quality diagnostics.
* Rule detail.
* Performance timing.
* Acceptance evidence.
* Accessibility checklist.
* Deployment evidence.

These details are useful for demonstration, testing, troubleshooting, and acceptance review.

## 📥 Downloaded Report Types

### Summary CSV

Use the summary CSV to review one row per processed label.

### Detail CSV

Use the detail CSV to inspect every rule result across labels.

### Comparison CSV

Use the comparison CSV to review application values beside extracted or observed label values.

### Performance CSV

Use the performance CSV to inspect per-label processing time and SLA behavior.

### JSON Report

Use JSON when another tool or script needs structured output.

### Markdown Report

Use Markdown when a human-readable review summary is needed.

## 🎬 Basic Demonstration Script

Use this simple script when demonstrating Fiddy.

1. Open Fiddy.
2. Select Simple Mode.
3. Upload the manifest.
4. Upload the label files or ZIP archive.
5. Confirm the app is ready.
6. Click **Run Verification**.
7. Review the dashboard.
8. Open the side-by-side comparison.
9. Point out status, severity, confidence, explanation, and reviewer action.
10. Download the summary and comparison CSVs.
11. Switch to Advanced Mode if technical diagnostics are needed.
12. Explain that final compliance decisions remain with the reviewer.

## 🛠️ Troubleshooting

### The App Is Not Ready

Check that:

* A manifest was uploaded, or manual application fields were entered.
* At least one label file was uploaded.
* Uploaded file types are supported.
* Manifest filenames match uploaded label filenames.



### Manifest Rows Do Not Match Uploaded Files

Check the `file_name` column in the manifest.

The value should match the uploaded label filename, including extension.

Example:

```text
old_tom_label.png
```

If the manifest says `old_tom_label.png` but the uploaded file is named `old_tom_label_v2.png`,
Fiddy may treat it as missing or unmatched.



### OCR Output Is Weak

Try using a clearer label image.

Helpful improvements include:

* Higher resolution.
* Straight-on image angle.
* Better lighting.
* Less glare.
* Better contrast.
* Cropped image focused on the label.
* PNG or JPG instead of a poor-quality PDF scan.



### PDF Uploads Fail

PDF support requires Poppler.

Confirm Poppler is installed and available on the system path.

For Windows setup, see:

```text
docs/PATH-POPPLER.md
```



### Tesseract Is Not Found

Tesseract OCR must be installed locally.

If Tesseract is installed but not on the system path, configure:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Then restart the terminal or IDE and run Fiddy again.



### Downloads Are Missing

Downloads usually appear after verification has completed.

If downloads are not visible:

* Confirm verification completed.
* Confirm at least one report was generated.
* Check whether Simple Mode hides advanced outputs.
* Switch to Advanced Mode if needed.

## ✅ Pre-Demonstration Checklist

Before demonstrating Fiddy:

* The app starts locally.
* Manifest upload works.
* Label upload works.
* ZIP upload works if needed.
* PDF upload works if Poppler is installed.
* Run Verification completes.
* Dashboard renders.
* Side-by-side comparison renders.
* Status values are visible.
* Severity values are visible.
* Confidence values are visible.
* Explanation text is visible.
* Reviewer action text is visible.
* Downloads are available.
* Simple Mode works.
* Advanced Mode works.
* High Contrast works.
* Large Text works.
* Keyboard navigation has been manually checked.
* No real sensitive data is used for demonstration.
* Synthetic or fictional data is used when possible.

## ⚖️ Trade-Offs and Limitations

Fiddy is a working prototype, not a production compliance system.

Known limitations include:

* OCR quality depends on submitted image quality.
* OCR cannot prove all visual formatting requirements.
* Government-warning visual formatting requires human confirmation.
* The prototype does not connect directly to COLA.
* The prototype does not write results back to an official workflow.
* The prototype avoids external ML endpoints by design.
* Synthetic demonstration data is fictional and limited.
* Production deployment would require additional security, identity, audit, monitoring, scanning,
  and records-management controls.

These limitations are intentional for the prototype. The goal is a working, explainable, local-first
core application rather than an overly broad system with incomplete production features.



## Final Reminder

Fiddy helps reviewers focus attention on likely mismatches, low-confidence results, poor image
quality, and government-warning issues.

The reviewer remains responsible for the final determination.
