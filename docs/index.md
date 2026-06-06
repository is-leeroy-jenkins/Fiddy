<p align="center">
  <img src="../assets/images/fiddy_fade_loop_gentle.gif" alt="Fiddy animated header" width="100%">
</p>

# Fiddy Documentation

**Fiddy** is an AI-assisted alcohol label verification prototype designed to compare alcohol label
artwork against expected application data.

The application uses local OCR, deterministic validation rules, fuzzy matching for acceptable
textual variations, strict government-warning validation, image-quality diagnostics, batch
processing, performance monitoring, and reviewer-facing exports.

## Documentation Guides

| Guide | Purpose |
|---|---|
| [Installation](INSTALLATION.md) | Set up Python, dependencies, Tesseract OCR, Poppler, and the local runtime environment. |
| [PATH Setup](PATH-POPPLER.md) | Add Poppler to the Windows PATH so PDF labels can be converted for OCR. |
| [Azure Deployment](AZURE_DEPLOYMENT.md) | Build and deploy Fiddy as an Azure-compatible local-OCR container. |

## Prototype Capabilities

Fiddy supports:

- Local OCR using Tesseract.
- PDF label processing using Poppler.
- Batch upload processing with manifest-driven application data.
- Side-by-side comparison of application fields and extracted label fields.
- Fuzzy matching for brand and class/type variation.
- Exact-match validation for the government warning.
- Image-quality notes for glare, skew, blur, low contrast, and exposure issues.
- CSV, JSON, and Markdown report exports.
- Simple Mode for reviewer-friendly operation.
- Advanced Mode for diagnostics and acceptance review.

## Demonstration Assets

Place demonstration files in the following directories:

```text
samples/
├── labels/
└── manifests/