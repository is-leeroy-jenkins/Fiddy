## 💻 Usage Examples

The Streamlit interface is the primary way to use Fiddy. The following examples show how the core
modules can also be used directly for testing, scripting, or future integration work.

### Verify One Label File

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

label_path = Path( 'samples/old_tom_label.png' )

verifier = AlcoholLabelVerifier( )
report = verifier.verify_file( application=application,
	file_path=label_path )

print( report.file_name )
print( report.overall_status )

for result in report.results:
	print( result.field_name, result.status,
		result.severity, result.confidence,
		result.message )
```

### Parse a Manifest

```python
from pathlib import Path

from src.batch_manifest import BatchManifest

manifest_path = Path( 'samples/alcohol_labels.csv' )

manifest = BatchManifest( )
records = manifest.load_records( manifest_path )

for record in records:
	print( record.file_name, record.brand_name, record.alcohol_content )
```

### Convert a Manifest Row to Application Data

```python
from pathlib import Path

from src.batch_manifest import BatchManifest

manifest_path = Path( 'samples/alcohol_labels.csv' )

manifest = BatchManifest( )
records = manifest.load_records( manifest_path )

application = records[ 0 ].to_label_application( )

print( application.brand_name )
print( application.class_type )
print( application.alcohol_content )
```

### Process a Batch

```python
from pathlib import Path

from src.batch_manifest import BatchManifest
from src.batch_processor import BatchProcessor

manifest_path = Path( 'samples/alcohol_labels.csv' )
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
	print( report.file_name, report.overall_status )
```

### Generate Review Tables

```python
from src.report_writer import ReportWriter

writer = ReportWriter( )

df_summary = writer.batch_to_summary_dataframe( batch_result.batch_report )
df_details = writer.batch_to_detail_dataframe( batch_result.batch_report )

print( df_summary.head( ) )
print( df_details.head( ) )
```

### Export Results to CSV

```python
from pathlib import Path

from src.report_writer import ReportWriter

output_folder = Path( 'outputs' )
output_folder.mkdir( parents=True, exist_ok=True )

writer = ReportWriter( )

df_summary = writer.batch_to_summary_dataframe( batch_result.batch_report )
df_details = writer.batch_to_detail_dataframe( batch_result.batch_report )

df_summary.to_csv( output_folder / 'fiddy_summary.csv', index=False )
df_details.to_csv( output_folder / 'fiddy_details.csv', index=False )
```

### Inspect OCR Output

```python
from pathlib import Path

from src.ocr_engine import OcrEngine

label_path = Path( 'samples/old_tom_label.png' )

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

### Validate Government Warning Text

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
	print( result.rule_id, result.status, result.severity, result.message )
```

### Log an Exception Locally

```python
from booger import Error, Logger

try:
	raise ValueError( 'Example failure while processing label artwork.' )
except Exception as e:
	exception = Error(
		error=e,
		cause='Demo',
		method='example_exception_logging',
		module='README'
	)

	row_id = Logger( ).log( exception )
	print( 'Logged row:', row_id )
```

## 📄 Manifest Format

A manifest row represents the expected application data for one uploaded label file.

Recommended CSV header:

```csv
file_name,brand_name,class_type,beverage_type,alcohol_content,proof,net_contents,producer_bottler,imported,importer,country_of_origin,cola_id,notes
```

Example:

```csv
file_name,brand_name,class_type,beverage_type,alcohol_content,proof,net_contents,producer_bottler,imported,importer,country_of_origin,cola_id,notes
old_tom_label.png,OLD TOM DISTILLERY,Kentucky Straight Bourbon Whiskey,Distilled Spirits,45,90,750 mL,Old Tom Distillery LLC,false,,,COLA-001,Demo record
```

### Schema

| Column                | Description                                                                   |
|-----------------------|-------------------------------------------------------------------------------|
| `file_name`           | Expected uploaded label filename.                                             |
| `brand_name`          | Expected brand name.                                                          |
| `class_type`          | Expected class or type designation.                                           |
| `beverage_type`       | Product category used for review context.                                     |
| `alcohol_content`     | Expected ABV value.                                                           |
| `proof`               | Expected proof, when applicable.                                              |
| `net_contents`        | Expected container volume.                                                    |
| `producer_bottler`    | Expected producer, bottler, brewer, vintner, importer, or responsible party.  |
| `imported`            | Indicates whether imported-product review applies.                            |
| `importer`            | Expected importer when applicable.                                            |
| `country_of_origin`   | Expected country of origin when applicable.                                   |
| `cola_id`             | Optional application or COLA reference.                                       |
| `notes`               | Optional reviewer notes.                                                      |
