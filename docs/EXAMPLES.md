# 💻 Examples

## 📌 Purpose

This page provides programmatic examples for using Fiddy’s core Python modules directly.

The Streamlit application is the primary reviewer interface, but these examples demonstrate that
Fiddy is also organized as a set of separable, testable services. They are useful for developers,
technical reviewers, maintainers, and evaluators who want to understand how the workflow can be
invoked outside the UI.

These examples support:

* Single-label verification.
* Manifest parsing.
* Manifest-to-application conversion.
* Batch processing.
* Review table generation.
* CSV export.
* OCR inspection.
* Government-warning validation.
* Local exception logging.



## 🧭 Example Assumptions

The examples assume they are run from the project root.

Expected project structure:

```text
Fiddy/
├── app.py
├── config.py
├── booger.py
├── samples/
│   ├── labels/
│   └── manifests/
└── src/
```

The examples also assume the virtual environment is active and dependencies are installed:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run examples from the project root so Python can resolve the `src` package correctly.



## ✅ Verify One Label File

This example verifies one label file against manually supplied expected application data.

```python
from pathlib import Path

from src.label_verifier import AlcoholLabelVerifier
from src.models import LabelApplication

application = LabelApplication(
	brand_name='OLD TOM DISTILLERY',
	class_type='Kentucky Straight Bourbon Whiskey',
	beverage_type='Distilled Spirits',
	alcohol_content=45.0,
	proof=90.0,
	net_contents='750 mL',
	producer_bottler='Old Tom Distillery LLC',
	imported=False,
	importer='',
	country_of_origin='',
	cola_id='COLA-001',
	notes='Programmatic single-label review.'
)

label_path = Path( 'samples/labels/old_tom_label.png' )

verifier = AlcoholLabelVerifier( )
report = verifier.verify_file(
	application=application,
	file_path=label_path
)

print( report.file_name )
print( report.overall_status )

for result in report.results:
	print(
		result.field_name,
		result.status,
		result.severity,
		result.confidence,
		result.message
	)
```



## 📄 Parse a Manifest

This example loads a manifest CSV and prints key application fields from each row.

```python
from pathlib import Path

from src.batch_manifest import BatchManifest

manifest_path = Path( 'samples/manifests/alcohol_labels.csv' )

manifest = BatchManifest( )
records = manifest.load_records( manifest_path )

for record in records:
	print(
		record.file_name,
		record.brand_name,
		record.alcohol_content
	)
```



## 🔁 Convert a Manifest Row to Application Data

This example converts the first manifest row into a `LabelApplication` object.

```python
from pathlib import Path

from src.batch_manifest import BatchManifest

manifest_path = Path( 'samples/manifests/alcohol_labels.csv' )

manifest = BatchManifest( )
records = manifest.load_records( manifest_path )

application = records[ 0 ].to_label_application( )

print( application.brand_name )
print( application.class_type )
print( application.alcohol_content )
```



## 📦 Process a Batch

This example loads manifest records, scans a folder for supported label files, and processes the
batch.

```python
from pathlib import Path

from src.batch_manifest import BatchManifest
from src.batch_processor import BatchProcessor

manifest_path = Path( 'samples/manifests/alcohol_labels.csv' )
artwork_folder = Path( 'samples/labels' )

manifest = BatchManifest( )
records = manifest.load_records( manifest_path )

file_paths = [
	path
	for path in artwork_folder.iterdir( )
	if path.suffix.lower( ) in (
		'.png',
		'.jpg',
		'.jpeg',
		'.webp',
		'.bmp',
		'.tif',
		'.tiff',
		'.pdf'
	)
]

processor = BatchProcessor( )
batch_result = processor.process_manifest_records(
	records=records,
	file_paths=file_paths
)

print( 'Processed:', len( batch_result.processed_files ) )
print( 'Skipped:', len( batch_result.skipped_files ) )
print( 'Errors:', len( batch_result.errors ) )

for report in batch_result.batch_report.reports:
	print(
		report.file_name,
		report.overall_status
	)
```



## 📊 Generate Review Tables

This example converts a batch report into pandas DataFrames for summary and detail review.

```python
from src.report_writer import ReportWriter

writer = ReportWriter( )

df_summary = writer.batch_to_summary_dataframe(
	batch_result.batch_report
)

df_details = writer.batch_to_detail_dataframe(
	batch_result.batch_report
)

print( df_summary.head( ) )
print( df_details.head( ) )
```



## 📥 Export Results to CSV

This example writes summary and detail CSV files to an output folder.

```python
from pathlib import Path

from src.report_writer import ReportWriter

output_folder = Path( 'outputs' )
output_folder.mkdir(
	parents=True,
	exist_ok=True
)

writer = ReportWriter( )

df_summary = writer.batch_to_summary_dataframe(
	batch_result.batch_report
)

df_details = writer.batch_to_detail_dataframe(
	batch_result.batch_report
)

df_summary.to_csv(
	output_folder / 'fiddy_summary.csv',
	index=False
)

df_details.to_csv(
	output_folder / 'fiddy_details.csv',
	index=False
)
```



## 🔍 Inspect OCR Output

This example runs OCR on one label file and prints raw OCR text and image-quality notes.

```python
from pathlib import Path

from src.ocr_engine import OcrEngine

label_path = Path( 'samples/labels/old_tom_label.png' )

ocr = OcrEngine( )
extracted = ocr.extract_text( label_path )

print( 'File:', extracted.file_name )
print( 'OCR Engine:', extracted.ocr_engine )
print( 'OCR Seconds:', extracted.ocr_seconds )

print( 'Raw OCR Text:' )
print( extracted.raw_text )

print( 'Image Quality Notes:' )
for note in extracted.image_quality_notes:
	print( '-', note )
```

## 🧪 Generate Synthetic Demo Data

This example generates the standard fictional Fiddy demo pack from Python.

The generator writes one manifest CSV and eight label images under:

```text
samples/
├── labels/
└── manifests/
```

```python
from src.synthetic_data_generator import SyntheticDataGenerator

generator = SyntheticDataGenerator( )
result = generator.generate_standard_demo_pack(
	overwrite=True
)

print( result.success )
print( result.message )
print( result.manifest_path )
print( result.label_directory )
print( result.record_count )
```

The generated manifest path is:

```text
samples/manifests/fiddy_v2_demo_manifest.csv
```

The generated label files are written to:

```text
samples/labels/
```

The standard demo pack includes these files:

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

Use the generated manifest and label files through the normal Fiddy upload controls.

## 🧹 Clear Synthetic Demo Data

This example removes the generated Fiddy demo pack.

Only generated files with the configured `fiddy_v2` prefix are removed.

```python
from src.synthetic_data_generator import SyntheticDataGenerator

generator = SyntheticDataGenerator( )
result = generator.clear_demo_pack( )

print( result.success )
print( result.message )
print( result.deleted_files )
```

This cleanup operation does not delete unrelated files in `samples/labels` or `samples/manifests`.


## ⚠️ Validate Government Warning Text

This example validates government-warning text directly.

```python
from src.warning_validator import GovernmentWarningValidator

label_text = '''
OLD TOM DISTILLERY
Kentucky Straight Bourbon Whiskey
ALC. 45% BY VOL

GOVERNMENT WARNING:
(1) According to the Surgeon General, women should not drink alcoholic beverages
during pregnancy because of the risk of birth defects.
(2) Consumption of alcoholic beverages impairs your ability to drive a car or operate
machinery, and may cause health problems.
'''

validator = GovernmentWarningValidator( )
validation = validator.validate( label_text )
results = validator.create_results( validation )

for result in results:
	print(
		result.rule_id,
		result.status,
		result.severity,
		result.message
	)
```



## 🧪 Run Acceptance Evidence Components

This example shows the intended pattern for running acceptance evidence generation from code.

The exact inputs should point to local demonstration assets.

```python
from pathlib import Path

from src.acceptance_test_harness import AcceptanceTestHarness

project_root = Path( '.' )
manifest_path = Path( 'samples/manifests/alcohol_labels.csv' )
label_directory = Path( 'samples/labels' )
output_root = Path( 'acceptance_evidence' )

harness = AcceptanceTestHarness(
	project_root=project_root,
	output_root=output_root,
	max_workers=4,
	sla_seconds=5.0
)

result = harness.run(
	test_name='fiddy_demo_acceptance',
	manifest_path=manifest_path,
	label_directory=label_directory
)

print( result.status )
print( result.message )
print( result.package.to_json( ) )
```



## ♿ Generate Accessibility Checklist Evidence

This example creates the accessibility checklist model and exports records.

```python
from src.accessibility_checklist import AccessibilityChecklist

checklist = AccessibilityChecklist( )
result = checklist.evaluate( )

df_accessibility = result.to_dataframe( )

print( result.status )
print( result.message )
print( df_accessibility.head( ) )
```

Accessibility should still be manually validated in the target browser because Streamlit renders
final interactive controls at runtime.



## ☁️ Generate Deployment Evidence

This example evaluates local deployment posture and supporting project artifacts.

```python
from pathlib import Path

from src.deployment_evidence import DeploymentEvidenceChecker

checker = DeploymentEvidenceChecker(
	project_root=Path( '.' )
)

evidence = checker.evaluate( )
df_deployment = evidence.to_dataframe( )

print( evidence.overall_status( ) )
print( df_deployment.head( ) )
```



## 🧾 Log an Exception Locally

This example logs a sanitized local exception using Fiddy’s structured logging pattern.

```python
from booger import Error, Logger

try:
	raise ValueError( 'Example failure while processing label artwork.' )
except Exception as e:
	error = Error( e )
	error.cause = 'Demo'
	error.module = 'docs.EXAMPLES'
	error.method = 'example_exception_logging( ) -> None'

	row_id = Logger( ).write( error )
	print( 'Logged row:', row_id )
```



## 🛠️ Troubleshooting Examples

### ModuleNotFoundError: No module named `src`

Run the example from the project root.

The project root should contain:

```text
app.py
config.py
src/
```

Then run your script from that folder.



### Tesseract Not Found

Confirm Tesseract is installed.

On Windows, configure the path if needed:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Restart the terminal or IDE after changing environment variables.



### PDF Conversion Fails

PDF support requires Poppler.

Confirm Poppler is available:

```powershell
pdfinfo -v
```

If the command is not found, install Poppler and add its `bin` folder to the Windows PATH.

See:

```text
docs/PATH-POPPLER.md
```



## ⚖️ Example Limitations

These examples are intended for development, testing, and demonstration. They do not replace the
Streamlit reviewer workflow.

Important limitations:

* OCR quality depends on source artwork.
* Programmatic examples do not perform browser accessibility validation.
* Government-warning visual properties still require human confirmation.
* Acceptance evidence depends on representative runtime inputs.
* Examples should use synthetic or fictional data unless formal handling rules are in place.
* Generated outputs should not include real sensitive application data unless appropriate controls
  are established.



## 🧠 Final Note

The examples show that Fiddy’s implementation is not tightly coupled to the UI. The core OCR,
manifest, verification, reporting, performance, accessibility, deployment, and acceptance components
can be invoked directly for testing, automation, or future integration work.
