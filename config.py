'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                config.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-06-2026
    ******************************************************************************************
    <copyright file="config.py" company="Terry D. Eppler">

         Fiddy: AI-Powered Alcohol Label Verification App

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
        Centralizes Fiddy configuration for local development, prototype acceptance testing,
        and Azure-ready deployment.

        This module defines project paths, Streamlit display settings, upload limits, local OCR
        settings, optional Azure Vision settings, deterministic verification thresholds,
        reporting settings, performance-service-level targets, batch-acceptance limits,
        accessibility defaults, security and data-retention switches, and small environment
        parsing helpers used by the application and supporting service modules.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# ==========================================================================================
# Environment
# ==========================================================================================

load_dotenv( )

# ==========================================================================================
# App-level Utility Functions
# ==========================================================================================

def throw_if( name: str, value: object ) -> None:
	"""Raise ``ValueError`` when a required value is empty.

	Purpose:
		Provide a small, consistent guard for required arguments and configuration values. The
		function treats falsy values as invalid and raises a ``ValueError`` containing the
		caller-supplied argument or setting name.

	Parameters:
		name (str): Name of the argument or configuration value being validated.
		value (object): Value to validate.

	Returns:
		None.

	Raises:
		ValueError: Raised when ``value`` is falsy.
	"""
	if not value:
		raise ValueError( f'Argument "{name}" cannot be empty!' )

def get_bool( name: str, default: bool = False ) -> bool:
	"""Read a Boolean environment variable using Fiddy's true-value convention.

	Purpose:
		Convert environment-variable text into a deterministic Boolean value. Missing variables
		return the caller-provided default. Values of ``1``, ``true``, ``yes``, ``y``, and
		``on`` are treated as ``True``; all other defined values are treated as ``False``.

	Parameters:
		name (str): Environment variable name.
		default (bool): Default value used when the environment variable is not defined.

	Returns:
		bool: Parsed Boolean value. If parsing fails, the original ``default`` value is returned.
	"""
	try:
		throw_if( 'name', name )
		value = os.getenv( name )
		return default if value is None else value.strip( ).lower( ) in (
				'1',
				'true',
				'yes',
				'y',
				'on'
		)
	except Exception:
		return default

def get_int( name: str, default: int ) -> int:
	"""Read an integer environment variable with a deterministic fallback.

	Purpose:
		Parse an optional environment variable as an integer while preserving a safe default when
		the variable is missing, empty, or invalid.

	Parameters:
		name (str): Environment variable name.
		default (int): Default integer value used when parsing is not possible.

	Returns:
		int: Parsed integer value or the supplied default value.
	"""
	try:
		throw_if( 'name', name )
		value = os.getenv( name )
		return default if value in (None, '') else int( str( value ).strip( ) )
	except Exception:
		return default

def get_float( name: str, default: float ) -> float:
	"""Read a floating-point environment variable with a deterministic fallback.

	Purpose:
		Parse an optional environment variable as a float while preserving a safe default when the
		variable is missing, empty, or invalid.

	Parameters:
		name (str): Environment variable name.
		default (float): Default floating-point value used when parsing is not possible.

	Returns:
		float: Parsed floating-point value or the supplied default value.
	"""
	try:
		throw_if( 'name', name )
		value = os.getenv( name )
		return default if value in (None, '') else float( str( value ).strip( ) )
	except Exception:
		return default

def get_path( name: str, default: Path ) -> Path:
	"""Read a path environment variable and return a resolved ``Path``.

	Purpose:
		Resolve optional filesystem configuration from the environment. Missing variables return
		the resolved default path. Invalid values return the resolved default path rather than
		interrupting module import.

	Parameters:
		name (str): Environment variable name.
		default (Path): Default path used when the environment variable is not defined.

	Returns:
		Path: Resolved path value or resolved default path.
	"""
	try:
		throw_if( 'name', name )
		throw_if( 'default', default )
		value = os.getenv( name )
		return Path( value ).resolve( ) if value else default.resolve( )
	except Exception:
		return default.resolve( )

# ==========================================================================================
# Project Paths
# ==========================================================================================

ROOT_DIR: Path = Path( __file__ ).resolve( ).parent
SRC_DIR: Path = ROOT_DIR / 'src'
ASSETS_DIR: Path = ROOT_DIR / 'assets'
SAMPLES_DIR: Path = ROOT_DIR / 'samples'
TESTS_DIR: Path = ROOT_DIR / 'tests'
DOCS_DIR: Path = ROOT_DIR / 'docs'
LOG_DIR: Path = get_path( 'LOG_DIR', ROOT_DIR / 'logging' )
LOG_PATH: str = os.getenv( 'LOG_PATH', str( LOG_DIR / 'Exceptions.db' ) )
LOG_FILE: str = os.getenv( 'LOG_FILE', 'Exceptions' )
FAVICON: str = os.getenv( 'FAVICON', r'assets/images/favicon.ico' )
LOGO: str = os.getenv( 'LOGO', r'assets/images/fiddy.png' )
TITLE: str = os.getenv( 'TITLE', r'assets/images/title.png' )
BLUE_DIVIDER: str = "<div style='height:2px;align:left;background:#0078FC;margin:0px 30px 30px 0px;'></div>"

# ==========================================================================================
# Application Settings
# ==========================================================================================

APP_NAME: str = os.getenv( 'APP_NAME', 'Label Verification' )
APP_TITLE: str = os.getenv( 'APP_TITLE', 'Fiddy' )

APP_DESCRIPTION: str = os.getenv(
	'APP_DESCRIPTION',
	'A local-first prototype for alcohol label verification using OCR, deterministic rules, '
	'fuzzy matching, and human-review flags.' )

APP_ICON: str = os.getenv( 'APP_ICON', '🥃' )
APP_LAYOUT: str = os.getenv( 'APP_LAYOUT', 'wide' )

# ==========================================================================================
# Deployment and Infrastructure Settings
# ==========================================================================================

DEPLOYMENT_TARGET: str = os.getenv( 'DEPLOYMENT_TARGET', 'local' )
REQUIRE_LOCAL_OCR: bool = get_bool( 'REQUIRE_LOCAL_OCR', True )
ALLOW_EXTERNAL_ML_ENDPOINTS: bool = get_bool( 'ALLOW_EXTERNAL_ML_ENDPOINTS', False )
ENABLE_UPLOAD_PERSISTENCE: bool = get_bool( 'ENABLE_UPLOAD_PERSISTENCE', False )
ENABLE_AZURE_DEPLOYMENT_MODE: bool = get_bool( 'ENABLE_AZURE_DEPLOYMENT_MODE', False )

# ==========================================================================================
# Upload Settings
# ==========================================================================================

MAX_UPLOAD_MB: int = get_int( 'MAX_UPLOAD_MB', 25 )
MAX_BATCH_FILES: int = get_int( 'MAX_BATCH_FILES', 50 )
MAX_PARALLEL_WORKERS: int = get_int( 'MAX_PARALLEL_WORKERS', 4 )
MAX_PDF_PAGES: int = get_int( 'MAX_PDF_PAGES', 1 )
MAX_IMAGE_DIMENSION: int = get_int( 'MAX_IMAGE_DIMENSION', 2400 )

SUPPORTED_IMAGE_EXTENSIONS: tuple[ str, ... ] = (
		'.png',
		'.jpg',
		'.jpeg',
		'.webp',
		'.bmp',
		'.tif',
		'.tiff'
)

SUPPORTED_PDF_EXTENSIONS: tuple[ str, ... ] = (
		'.pdf',
)

SUPPORTED_ARCHIVE_EXTENSIONS: tuple[ str, ... ] = (
		'.zip',
)

SUPPORTED_UPLOAD_EXTENSIONS: tuple[ str, ... ] = (
		*SUPPORTED_IMAGE_EXTENSIONS,
		*SUPPORTED_PDF_EXTENSIONS
)

SUPPORTED_BATCH_UPLOAD_EXTENSIONS: tuple[ str, ... ] = (
		*SUPPORTED_UPLOAD_EXTENSIONS,
		*SUPPORTED_ARCHIVE_EXTENSIONS
)

# ==========================================================================================
# OCR Settings
# ==========================================================================================

OCR_ENGINE: str = os.getenv( 'OCR_ENGINE', 'tesseract' )
TESSERACT_CMD: Optional[ str ] = os.getenv( 'TESSERACT_CMD' )
OCR_LANGUAGE: str = os.getenv( 'OCR_LANGUAGE', 'eng' )
OCR_TIMEOUT_SECONDS: int = get_int( 'OCR_TIMEOUT_SECONDS', 5 )
OCR_CONFIG: str = os.getenv( 'OCR_CONFIG', '--oem 3 --psm 6' )
OCR_MINIMUM_WIDTH: int = get_int( 'OCR_MINIMUM_WIDTH', 800 )
OCR_MINIMUM_HEIGHT: int = get_int( 'OCR_MINIMUM_HEIGHT', 800 )

# ==========================================================================================
# Optional Azure Vision Settings
# ==========================================================================================

ENABLE_AZURE_VISION: bool = get_bool( 'ENABLE_AZURE_VISION', False )
AZURE_VISION_ENDPOINT: Optional[ str ] = os.getenv( 'AZURE_VISION_ENDPOINT' )
AZURE_VISION_KEY: Optional[ str ] = os.getenv( 'AZURE_VISION_KEY' )

# ==========================================================================================
# Verification Settings
# ==========================================================================================

BRAND_MATCH_THRESHOLD: float = get_float( 'BRAND_MATCH_THRESHOLD', 90.0 )
CLASS_TYPE_MATCH_THRESHOLD: float = get_float( 'CLASS_TYPE_MATCH_THRESHOLD', 85.0 )
LOW_CONFIDENCE_THRESHOLD: float = get_float( 'LOW_CONFIDENCE_THRESHOLD', 70.0 )
ABV_TOLERANCE: float = get_float( 'ABV_TOLERANCE', 0.3 )
PROOF_TOLERANCE: float = get_float( 'PROOF_TOLERANCE', 0.6 )
NET_CONTENTS_MATCH_THRESHOLD: float = get_float( 'NET_CONTENTS_MATCH_THRESHOLD', 90.0 )
PRODUCER_BOTTLER_MATCH_THRESHOLD: float = get_float( 'PRODUCER_BOTTLER_MATCH_THRESHOLD', 85.0 )
COUNTRY_OF_ORIGIN_MATCH_THRESHOLD: float = get_float( 'COUNTRY_OF_ORIGIN_MATCH_THRESHOLD', 90.0 )

DEFAULT_STATUS_PASS: str = 'Pass'
DEFAULT_STATUS_WARNING: str = 'Warning'
DEFAULT_STATUS_FAIL: str = 'Fail'
DEFAULT_STATUS_REVIEW: str = 'Needs Review'

# ==========================================================================================
# Acceptance and SLA Settings
# ==========================================================================================

LABEL_PROCESSING_SLA_SECONDS: float = get_float( 'LABEL_PROCESSING_SLA_SECONDS', 5.0 )
BATCH_ACCEPTANCE_MIN_FILES: int = get_int( 'BATCH_ACCEPTANCE_MIN_FILES', 20 )
BATCH_ACCEPTANCE_MAX_FILES: int = get_int( 'BATCH_ACCEPTANCE_MAX_FILES', 50 )
BATCH_ACCEPTANCE_MAX_AVERAGE_SECONDS: float = get_float( 'BATCH_ACCEPTANCE_MAX_AVERAGE_SECONDS',
	5.0 )
BATCH_ACCEPTANCE_MAX_P95_SECONDS: float = get_float( 'BATCH_ACCEPTANCE_MAX_P95_SECONDS', 5.0 )
BATCH_ACCEPTANCE_MAX_BREACH_RATE: float = get_float( 'BATCH_ACCEPTANCE_MAX_BREACH_RATE', 0.0 )
ENABLE_ACCEPTANCE_SUMMARY: bool = get_bool( 'ENABLE_ACCEPTANCE_SUMMARY', True )
ENABLE_PERFORMANCE_WARNINGS: bool = get_bool( 'ENABLE_PERFORMANCE_WARNINGS', True )

# ==========================================================================================
# Accessibility Settings
# ==========================================================================================

DEFAULT_SIMPLE_MODE: bool = get_bool( 'DEFAULT_SIMPLE_MODE', True )
DEFAULT_HIGH_CONTRAST_MODE: bool = get_bool( 'DEFAULT_HIGH_CONTRAST_MODE', False )
DEFAULT_LARGE_TEXT_MODE: bool = get_bool( 'DEFAULT_LARGE_TEXT_MODE', False )
REQUIRE_KEYBOARD_ACCESSIBILITY_CHECK: bool = get_bool( 'REQUIRE_KEYBOARD_ACCESSIBILITY_CHECK',
	True )
SHOW_KEYBOARD_ACCESSIBILITY_NOTES: bool = get_bool( 'SHOW_KEYBOARD_ACCESSIBILITY_NOTES', True )
MINIMUM_TOUCH_TARGET_PX: int = get_int( 'MINIMUM_TOUCH_TARGET_PX', 44 )

# ==========================================================================================
# Security, Privacy, and Retention Settings
# ==========================================================================================

ENABLE_EXCEPTION_LOGGING: bool = get_bool( 'ENABLE_EXCEPTION_LOGGING', True )
ENABLE_RAW_TEXT_LOGGING: bool = get_bool( 'ENABLE_RAW_TEXT_LOGGING', False )
ENABLE_RAW_OCR_EXPORT: bool = get_bool( 'ENABLE_RAW_OCR_EXPORT', False )
ENABLE_MANIFEST_ROW_LOGGING: bool = get_bool( 'ENABLE_MANIFEST_ROW_LOGGING', False )
ENABLE_FILE_PATH_LOGGING: bool = get_bool( 'ENABLE_FILE_PATH_LOGGING', False )
LOG_RETENTION_DAYS: int = get_int( 'LOG_RETENTION_DAYS', 7 )
MAX_LOG_MESSAGE_CHARS: int = get_int( 'MAX_LOG_MESSAGE_CHARS', 1000 )
MAX_LOG_TRACE_CHARS: int = get_int( 'MAX_LOG_TRACE_CHARS', 4000 )

# ==========================================================================================
# Reporting Settings
# ==========================================================================================

REPORT_FILENAME_PREFIX: str = os.getenv( 'REPORT_FILENAME_PREFIX', 'fiddy_report' )
REPORT_DATE_FORMAT: str = os.getenv( 'REPORT_DATE_FORMAT', '%Y-%m-%d %H:%M:%S' )
ENABLE_MARKDOWN_REPORT: bool = get_bool( 'ENABLE_MARKDOWN_REPORT', True )
ENABLE_JSON_REPORT: bool = get_bool( 'ENABLE_JSON_REPORT', True )
ENABLE_CSV_REPORTS: bool = get_bool( 'ENABLE_CSV_REPORTS', True )

# ==========================================================================================
# Streamlit Settings
# ==========================================================================================

STREAMLIT_SERVER_PORT: int = get_int(
	'PORT',
	get_int( 'STREAMLIT_SERVER_PORT', 8501 ) )

STREAMLIT_SERVER_ADDRESS: str = os.getenv( 'STREAMLIT_SERVER_ADDRESS', '0.0.0.0' )
STREAMLIT_BROWSER_GATHER_USAGE_STATS: bool = get_bool( 'STREAMLIT_BROWSER_GATHER_USAGE_STATS',
	False )