'''
    ******************************************************************************************
      Assembly:                Veritas
      Filename:                constants.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="constants.py" company="Terry D. Eppler">

         Veritas: AI-Powered Alcohol Label Verification App

     Permission is hereby granted, free of charge, to any person obtaining a copy
     of this software and associated documentation files (the “Software”),
     to deal in the Software without restriction,
     including without limitation the rights to use,
     copy, modify, merge, publish, distribute, sublicense,
     and/or sell copies of the Software,
     and to permit persons to whom the Software is furnished to do so,
     subject to the following conditions:

     The above copyright notice and this permission notice shall be included in all
     copies or substantial portions of the Software.

     THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
     INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
     FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT.
     IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
     DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
     ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
     DEALINGS IN THE SOFTWARE.

     You can contact me at:  terryeppler@gmail.com

    </copyright>
    <summary>
        constants.py
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

# ==========================================================================================
# Application Identity
# ==========================================================================================

APP_NAME: str = 'Veritas'
APP_DISPLAY_NAME: str = 'Veritas: AI-Powered Alcohol Label Verification App'
APP_SUBTITLE: str = 'AI-assisted alcohol label verification for compliance review.'

# ==========================================================================================
# Beverage Types
# ==========================================================================================

BEVERAGE_TYPE_BEER: str = 'Beer / Malt Beverage'
BEVERAGE_TYPE_WINE: str = 'Wine'
BEVERAGE_TYPE_DISTILLED_SPIRITS: str = 'Distilled Spirits'
BEVERAGE_TYPE_UNKNOWN: str = 'Unknown'

BEVERAGE_TYPES: list[ str ] = [
		BEVERAGE_TYPE_DISTILLED_SPIRITS,
		BEVERAGE_TYPE_WINE,
		BEVERAGE_TYPE_BEER,
		BEVERAGE_TYPE_UNKNOWN
]

# ==========================================================================================
# Verification Status Values
# ==========================================================================================

STATUS_PASS: str = 'Pass'
STATUS_WARNING: str = 'Warning'
STATUS_FAIL: str = 'Fail'
STATUS_REVIEW: str = 'Needs Review'
STATUS_NOT_APPLICABLE: str = 'Not Applicable'

STATUS_VALUES: list[ str ] = [
		STATUS_PASS,
		STATUS_WARNING,
		STATUS_FAIL,
		STATUS_REVIEW,
		STATUS_NOT_APPLICABLE
]

# ==========================================================================================
# Severity Values
# ==========================================================================================

SEVERITY_INFO: str = 'Info'
SEVERITY_LOW: str = 'Low'
SEVERITY_MEDIUM: str = 'Medium'
SEVERITY_HIGH: str = 'High'
SEVERITY_CRITICAL: str = 'Critical'

SEVERITY_VALUES: list[ str ] = [
		SEVERITY_INFO,
		SEVERITY_LOW,
		SEVERITY_MEDIUM,
		SEVERITY_HIGH,
		SEVERITY_CRITICAL
]

# ==========================================================================================
# Required Label Fields
# ==========================================================================================

FIELD_BRAND_NAME: str = 'Brand Name'
FIELD_CLASS_TYPE: str = 'Class / Type'
FIELD_ALCOHOL_CONTENT: str = 'Alcohol Content'
FIELD_PROOF: str = 'Proof'
FIELD_NET_CONTENTS: str = 'Net Contents'
FIELD_PRODUCER_BOTTLER: str = 'Producer / Bottler'
FIELD_IMPORTER: str = 'Importer'
FIELD_COUNTRY_OF_ORIGIN: str = 'Country of Origin'
FIELD_GOVERNMENT_WARNING: str = 'Government Warning'
FIELD_LABEL_TEXT: str = 'Extracted Label Text'
FIELD_OVERALL_STATUS: str = 'Overall Status'

REQUIRED_COMMON_FIELDS: list[ str ] = [
		FIELD_BRAND_NAME,
		FIELD_CLASS_TYPE,
		FIELD_ALCOHOL_CONTENT,
		FIELD_NET_CONTENTS,
		FIELD_PRODUCER_BOTTLER,
		FIELD_GOVERNMENT_WARNING
]

IMPORT_REQUIRED_FIELDS: list[ str ] = [
		FIELD_COUNTRY_OF_ORIGIN,
		FIELD_IMPORTER
]

# ==========================================================================================
# Rule Identifiers
# ==========================================================================================

RULE_BRAND_NAME_MATCH: str = 'brand_name_match'
RULE_CLASS_TYPE_MATCH: str = 'class_type_match'
RULE_ALCOHOL_CONTENT_PRESENT: str = 'alcohol_content_present'
RULE_ALCOHOL_CONTENT_MATCH: str = 'alcohol_content_match'
RULE_PROOF_PRESENT: str = 'proof_present'
RULE_PROOF_CONSISTENCY: str = 'proof_consistency'
RULE_NET_CONTENTS_PRESENT: str = 'net_contents_present'
RULE_NET_CONTENTS_MATCH: str = 'net_contents_match'
RULE_PRODUCER_BOTTLER_PRESENT: str = 'producer_bottler_present'
RULE_IMPORTER_PRESENT: str = 'importer_present'
RULE_COUNTRY_OF_ORIGIN_PRESENT: str = 'country_of_origin_present'
RULE_GOVERNMENT_WARNING_PRESENT: str = 'government_warning_present'
RULE_GOVERNMENT_WARNING_EXACT: str = 'government_warning_exact'
RULE_GOVERNMENT_WARNING_PREFIX_CAPS: str = 'government_warning_prefix_caps'
RULE_GOVERNMENT_WARNING_VISUAL_FORMAT: str = 'government_warning_visual_format'

# ==========================================================================================
# Standard Government Warning
# ==========================================================================================

GOVERNMENT_WARNING_PREFIX: str = 'GOVERNMENT WARNING:'

GOVERNMENT_WARNING_TEXT: str = (
		'GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink '
		'alcoholic beverages during pregnancy because of the risk of birth defects. '
		'(2) Consumption of alcoholic beverages impairs your ability to drive a car or operate '
		'machinery, and may cause health problems.'
)

GOVERNMENT_WARNING_TEXT_NORMALIZED: str = (
		'government warning 1 according to the surgeon general women should not drink alcoholic '
		'beverages during pregnancy because of the risk of birth defects 2 consumption of '
		'alcoholic beverages impairs your ability to drive a car or operate machinery and may '
		'cause health problems'
)

# ==========================================================================================
# Regular Expression Patterns
# ==========================================================================================

ABV_PATTERN: str = (
		r'(?P<abv>\d{1,3}(?:\.\d+)?)\s*%?\s*'
		r'(?:alc\.?\s*/?\s*vol\.?|abv|alcohol\s+by\s+volume)'
)

PROOF_PATTERN: str = r'(?P<proof>\d{1,3}(?:\.\d+)?)\s*proof'

NET_CONTENTS_PATTERN: str = (
		r'(?P<amount>\d+(?:\.\d+)?)\s*'
		r'(?P<unit>ml|m\.l\.|milliliter|milliliters|l|liter|liters|fl\s*oz|fluid\s*ounces|oz)'
)

PRODUCER_BOTTLER_PATTERN: str = (
		r'(bottled\s+by|distilled\s+by|produced\s+by|vinted\s+by|brewed\s+by|'
		r'cellared\s+by|packed\s+by)'
)

IMPORTER_PATTERN: str = r'(imported\s+by|imported\s+for|sole\s+importer|importer)'

COUNTRY_OF_ORIGIN_PATTERN: str = (
		r'(product\s+of|made\s+in|produced\s+in|country\s+of\s+origin|origin)\s+'
		r'(?P<country>[a-zA-Z][a-zA-Z\s]+)'
)

# ==========================================================================================
# Matching Defaults
# ==========================================================================================

DEFAULT_BRAND_MATCH_THRESHOLD: float = 90.0
DEFAULT_CLASS_TYPE_MATCH_THRESHOLD: float = 85.0
DEFAULT_WARNING_MATCH_THRESHOLD: float = 98.0
DEFAULT_LOW_CONFIDENCE_THRESHOLD: float = 70.0
DEFAULT_PROOF_TOLERANCE: float = 0.75
DEFAULT_ABV_TOLERANCE: float = 0.25

# ==========================================================================================
# Report Columns
# ==========================================================================================

RESULT_COLUMN_FILE_NAME: str = 'File Name'
RESULT_COLUMN_FIELD_NAME: str = 'Field Name'
RESULT_COLUMN_RULE_ID: str = 'Rule ID'
RESULT_COLUMN_STATUS: str = 'Status'
RESULT_COLUMN_SEVERITY: str = 'Severity'
RESULT_COLUMN_EXPECTED: str = 'Expected'
RESULT_COLUMN_OBSERVED: str = 'Observed'
RESULT_COLUMN_CONFIDENCE: str = 'Confidence'
RESULT_COLUMN_EVIDENCE: str = 'Evidence'
RESULT_COLUMN_MESSAGE: str = 'Message'

RESULT_COLUMNS: list[ str ] = [
		RESULT_COLUMN_FILE_NAME,
		RESULT_COLUMN_FIELD_NAME,
		RESULT_COLUMN_RULE_ID,
		RESULT_COLUMN_STATUS,
		RESULT_COLUMN_SEVERITY,
		RESULT_COLUMN_EXPECTED,
		RESULT_COLUMN_OBSERVED,
		RESULT_COLUMN_CONFIDENCE,
		RESULT_COLUMN_EVIDENCE,
		RESULT_COLUMN_MESSAGE
]

# ==========================================================================================
# Supported Upload Types
# ==========================================================================================

SUPPORTED_IMAGE_TYPES: list[ str ] = [
		'png',
		'jpg',
		'jpeg',
		'webp',
		'bmp',
		'tif',
		'tiff'
]

SUPPORTED_DOCUMENT_TYPES: list[ str ] = [
		'pdf'
]

SUPPORTED_UPLOAD_TYPES: list[ str ] = [
		*SUPPORTED_IMAGE_TYPES,
		*SUPPORTED_DOCUMENT_TYPES
]