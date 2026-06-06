'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                config.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
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
        Provides application configuration constants and environment-variable helpers for
        Fiddy.

        This module centralizes project paths, logging locations, branding assets, Streamlit
        settings, upload limits, OCR configuration, optional Azure Vision settings, verification
        thresholds, report settings, and small validation helpers used throughout the
        application.
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
# Project Paths
# ==========================================================================================

ROOT_DIR: Path = Path( __file__ ).resolve( ).parent
SRC_DIR: Path = ROOT_DIR / 'src'
ASSETS_DIR: Path = ROOT_DIR / 'assets'
SAMPLES_DIR: Path = ROOT_DIR / 'samples'
TESTS_DIR: Path = ROOT_DIR / 'tests'
LOG_PATH = r'logging/Exceptions.db'
LOG_FILE = 'Exceptions'
FAVICON = r'assets/images/favicon.ico'
LOGO = r'assets/images/fiddy.png'
TITLE = r'assets/images/title.png'
BLUE_DIVIDER = "<div style='height:2px;align:left;background:#0078FC;margin:0px 30px 30px 0px;'></div>"

# ==========================================================================================
# Application Settings
# ==========================================================================================

APP_NAME: str = os.getenv( 'APP_NAME', '2-Fiddy' )
APP_TITLE: str = os.getenv( 'APP_TITLE', 'Label Verification' )

APP_DESCRIPTION: str = os.getenv(
	'APP_DESCRIPTION',
	'A local-first prototype for alcohol label verification using OCR, deterministic rules, '
	'fuzzy matching, and human-review flags.' )

APP_ICON: str = os.getenv( 'APP_ICON', '🥃' )
APP_LAYOUT: str = os.getenv( 'APP_LAYOUT', 'wide' )

# ==========================================================================================
# Upload Settings
# ==========================================================================================

MAX_UPLOAD_MB: int = int( os.getenv( 'MAX_UPLOAD_MB', '25' ) )
MAX_BATCH_FILES: int = int( os.getenv( 'MAX_BATCH_FILES', '25' ) )

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

SUPPORTED_UPLOAD_EXTENSIONS: tuple[ str, ... ] = (
		*SUPPORTED_IMAGE_EXTENSIONS,
		*SUPPORTED_PDF_EXTENSIONS
)

# ==========================================================================================
# OCR Settings
# ==========================================================================================

OCR_ENGINE: str = os.getenv( 'OCR_ENGINE', 'tesseract' )
TESSERACT_CMD: Optional[ str ] = os.getenv( 'TESSERACT_CMD' )
OCR_LANGUAGE: str = os.getenv( 'OCR_LANGUAGE', 'eng' )
OCR_TIMEOUT_SECONDS: int = int( os.getenv( 'OCR_TIMEOUT_SECONDS', '5' ) )

# ==========================================================================================
# Optional Azure Vision Settings
# ==========================================================================================

ENABLE_AZURE_VISION: bool = os.getenv( 'ENABLE_AZURE_VISION', 'false' ).lower( ) == 'true'
AZURE_VISION_ENDPOINT: Optional[ str ] = os.getenv( 'AZURE_VISION_ENDPOINT' )
AZURE_VISION_KEY: Optional[ str ] = os.getenv( 'AZURE_VISION_KEY' )

# ==========================================================================================
# Verification Settings
# ==========================================================================================

BRAND_MATCH_THRESHOLD: float = float( os.getenv( 'BRAND_MATCH_THRESHOLD', '90.0' ) )
CLASS_TYPE_MATCH_THRESHOLD: float = float( os.getenv( 'CLASS_TYPE_MATCH_THRESHOLD', '85.0' ) )
LOW_CONFIDENCE_THRESHOLD: float = float( os.getenv( 'LOW_CONFIDENCE_THRESHOLD', '70.0' ) )

DEFAULT_STATUS_PASS: str = 'Pass'
DEFAULT_STATUS_WARNING: str = 'Warning'
DEFAULT_STATUS_FAIL: str = 'Fail'
DEFAULT_STATUS_REVIEW: str = 'Needs Review'

# ==========================================================================================
# Reporting Settings
# ==========================================================================================

REPORT_FILENAME_PREFIX: str = os.getenv( 'REPORT_FILENAME_PREFIX', 'fiddy_report' )
REPORT_DATE_FORMAT: str = os.getenv( 'REPORT_DATE_FORMAT', '%Y-%m-%d %H:%M:%S' )

# ==========================================================================================
# Streamlit Settings
# ==========================================================================================

STREAMLIT_SERVER_PORT: int = int(
	os.getenv( 'PORT', os.getenv( 'STREAMLIT_SERVER_PORT', '8501' ) ) )
STREAMLIT_SERVER_ADDRESS: str = os.getenv( 'STREAMLIT_SERVER_ADDRESS', '0.0.0.0' )

# ==========================================================================================
# App-level Utility Functions
# ==========================================================================================

def throw_if( name: str, value: object ) -> None:
	"""Raise ``ValueError`` when a required value is empty.

	This helper provides a small, consistent guard for required arguments and configuration
	values. It treats falsy values as invalid and raises a ``ValueError`` that includes the
	caller-supplied argument or setting name.

	The function intentionally has no internal exception handler. It is designed to raise when
	validation fails so calling code can handle the error in the appropriate guarded execution
	path.

	Args:
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

	This function reads an environment variable by name and converts it to ``True`` only when
	the trimmed lowercase value is one of ``1``, ``true``, ``yes``, ``y``, or ``on``. Missing
	environment variables return the supplied default value. Values outside the accepted
	true-value set return ``False``.

	Args:
		name (str): Environment variable name.
		default (bool): Default value used when the environment variable is not defined.

	Returns:
		bool: Parsed Boolean value. If parsing fails, the exception is logged when Booger is
		available and the original ``default`` fallback is returned.
	"""
	try:
		throw_if( 'name', name )
		
		value = os.getenv( name )
		if value is None:
			return default
		
		return value.strip( ).lower( ) in ('1', 'true', 'yes', 'y', 'on')
	except Exception as e:
		try:
			from booger import Error, Logger
			
			error = Error( e )
			error.cause = 'Configuration'
			error.module = __name__
			error.method = 'get_bool( name: str, default: bool ) -> bool'
			Logger( ).write( error )
		except Exception:
			pass
		
		return default

def get_path( name: str, default: Path ) -> Path:
	"""Read a path environment variable and return a resolved ``Path``.

	This function reads an environment variable by name and resolves it into a ``Path`` when the
	value is present. If the environment variable is missing, the supplied default path is
	resolved and returned. The helper is used for configurable filesystem locations while
	preserving deterministic fallback behavior.

	Args:
		name (str): Environment variable name.
		default (Path): Default path used when the environment variable is not defined.

	Returns:
		Path: Resolved path value. If path parsing fails, the exception is logged when Booger is
		available and the resolved default path is returned.
	"""
	try:
		throw_if( 'name', name )
		throw_if( 'default', default )
		
		value = os.getenv( name )
		return Path( value ).resolve( ) if value else default.resolve( )
	except Exception as e:
		try:
			from booger import Error, Logger
			
			error = Error( e )
			error.cause = 'Configuration'
			error.module = __name__
			error.method = 'get_path( name: str, default: Path ) -> Path'
			Logger( ).write( error )
		except Exception:
			pass
		
		return default.resolve( )