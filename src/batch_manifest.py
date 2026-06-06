'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                batch_manifest.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="batch_manifest.py" company="Terry D. Eppler">

         Fiddy: AI-Powered Alcohol Label Verification App

     Permission is hereby granted, free of charge, to any person obtaining a copy
     of this software and associated documentation files (the â€œSoftwareâ€),
     to deal in the Software without restriction,
     including without limitation the rights to use,
     copy, modify, merge, publish, distribute, sublicense,
     and/or sell copies of the Software,
     and to permit persons to whom the Software is furnished to do so,
     subject to the following conditions:

     The above copyright notice and this permission notice shall be included in all
     copies or substantial portions of the Software.

     THE SOFTWARE IS PROVIDED â€œAS ISâ€, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
     INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
     FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT.
     IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
     DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
     ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
     DEALINGS IN THE SOFTWARE.

     You can contact me at:  terryeppler@gmail.com

    </copyright>
    <summary>
        Provides manifest loading, normalization, validation, and conversion services for
        Fiddy batch label verification workflows.

        This module defines the manifest data structures and processing logic used to convert
        reviewer-provided CSV application data into strongly typed verification inputs. It
        normalizes common column-name aliases, reads CSV files using multiple encoding
        fallbacks, validates required application-data columns, detects duplicate manifest file
        names, converts manifest rows into BatchManifestRecord objects, maps manifest records
        to LabelApplication models, and validates manifest rows against uploaded label files.

        The module is intentionally conservative because it sits at the boundary between user
        supplied spreadsheet data and the deterministic verification engine. Invalid, missing,
        duplicated, or unmatched manifest records are captured as errors or warnings rather
        than silently ignored. Existing fallback behavior is preserved so the reviewer-facing
        application can continue operating safely when a manifest cannot be read, normalized,
        converted, or matched.

        Booger logging is used in guarded execution paths to persist structured diagnostic
        metadata before returning the original fallback values. The logging metadata uses stable
        method-signature strings and intentionally avoids live manifest content, uploaded file
        paths, or row-level user data in the logged method names.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from io import BytesIO
import pandas as pd
from pydantic import BaseModel, Field
from booger import Error, Logger
from config import throw_if
from src.constants import BEVERAGE_TYPE_DISTILLED_SPIRITS
from src.models import LabelApplication

class BatchManifestRecord( BaseModel ):
	"""Represent one application-data row from a batch manifest file.

	The ``BatchManifestRecord`` model stores the expected application values for one uploaded
	label file. Each record is usually created from one row of a normalized manifest DataFrame.
	The field names are canonical internal names used throughout the batch verification
	workflow, regardless of the original column headers supplied by the reviewer.

	The record can be converted directly into a ``LabelApplication`` model, which is the input
	contract expected by the label verifier. This separation keeps manifest parsing concerns
	isolated from verification concerns while preserving a clear handoff between batch data
	loading and label-rule execution.

	Attributes:
		file_name (str): Expected uploaded label file name associated with the manifest row.
		brand_name (str): Expected brand name from the application data.
		class_type (str): Expected class or type designation from the application data.
		beverage_type (str): Expected beverage category, defaulting to distilled spirits.
		alcohol_content (Optional[float]): Expected alcohol by volume value when available.
		proof (Optional[float]): Expected proof value when available.
		net_contents (str): Expected net contents value.
		producer_bottler (str): Expected producer, bottler, or responsible party text.
		imported (bool): Indicates whether importer and country-of-origin fields are relevant.
		importer (str): Expected importer value when applicable.
		country_of_origin (str): Expected country-of-origin value when applicable.
		cola_id (str): Optional COLA identifier or application reference.
		notes (str): Optional reviewer notes carried forward from the manifest.
	"""
	file_name: str = Field( default='', description='Expected uploaded label file name.' )
	brand_name: str = Field( default='', description='Expected brand name.' )
	class_type: str = Field( default='', description='Expected class or type designation.' )
	beverage_type: str = Field( default=BEVERAGE_TYPE_DISTILLED_SPIRITS )
	alcohol_content: Optional[ float ] = Field( default=None, description='Expected ABV.' )
	proof: Optional[ float ] = Field( default=None, description='Expected proof.' )
	net_contents: str = Field( default='', description='Expected net contents.' )
	producer_bottler: str = Field( default='', description='Expected producer or bottler.' )
	imported: bool = Field( default=False,
		description='Indicates whether the product is imported.' )
	importer: str = Field( default='', description='Expected importer when applicable.' )
	country_of_origin: str = Field( default='', description='Expected country of origin.' )
	cola_id: str = Field( default='', description='Optional COLA or application reference.' )
	notes: str = Field( default='', description='Optional reviewer notes.' )
	
	def to_label_application( self ) -> LabelApplication:
		"""Convert the manifest row into a ``LabelApplication`` verifier input.

		This method maps the canonical manifest-record fields into the application model used
		by the verification engine. The conversion is intentionally direct: text fields,
		numeric fields, import indicators, optional COLA references, and notes are passed to
		``LabelApplication`` without additional normalization or rule interpretation.

		The government-warning field is not populated here because the original manifest
		contract for this file does not include that field. The target ``LabelApplication``
		model is expected to apply its own default for omitted values.

		Returns:
			LabelApplication: Expected application values for one label file. If conversion
			fails, the exception is logged and an empty ``LabelApplication`` fallback is
			returned to preserve the original reviewer-safe behavior.
		"""
		try:
			return LabelApplication(
				brand_name=self.brand_name,
				class_type=self.class_type,
				beverage_type=self.beverage_type,
				alcohol_content=self.alcohol_content,
				proof=self.proof,
				net_contents=self.net_contents,
				producer_bottler=self.producer_bottler,
				imported=self.imported,
				importer=self.importer,
				country_of_origin=self.country_of_origin,
				cola_id=self.cola_id,
				notes=self.notes
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_label_application( ) -> LabelApplication'
			Logger( ).write( error )
			return LabelApplication( )

class BatchManifestValidationResult( BaseModel ):
	"""Represent validation results for a manifest and uploaded label-file set.

	The ``BatchManifestValidationResult`` model captures the outcome of comparing parsed
	manifest rows to the label files uploaded for batch processing. It records row and file
	counts, matched file names, missing files, extra uploaded files, duplicate manifest file
	names, blocking validation errors, and non-blocking warnings.

	The ``is_valid`` flag is intended to represent whether blocking validation errors were
	found. Extra uploaded files are treated as warnings in the current workflow, while missing
	manifest files and duplicate manifest file names are treated as errors.

	Attributes:
		is_valid (bool): Indicates whether the manifest/file set passed blocking validation.
		total_manifest_rows (int): Number of parsed manifest records considered.
		total_uploaded_files (int): Number of uploaded label files considered.
		matched_files (List[str]): Manifest file names that matched uploaded files.
		missing_files (List[str]): Manifest file names without corresponding uploaded files.
		extra_files (List[str]): Uploaded file names without corresponding manifest rows.
		duplicate_manifest_files (List[str]): Duplicate file names found in the manifest.
		errors (List[str]): Blocking validation or processing errors.
		warnings (List[str]): Non-blocking validation or processing warnings.
	"""
	is_valid: bool = Field( default=False )
	total_manifest_rows: int = Field( default=0 )
	total_uploaded_files: int = Field( default=0 )
	matched_files: List[ str ] = Field( default_factory=list )
	missing_files: List[ str ] = Field( default_factory=list )
	extra_files: List[ str ] = Field( default_factory=list )
	duplicate_manifest_files: List[ str ] = Field( default_factory=list )
	errors: List[ str ] = Field( default_factory=list )
	warnings: List[ str ] = Field( default_factory=list )
	
	def to_record( self ) -> Dict[ str, Any ]:
		"""Convert validation results into a flat display-ready dictionary.

		This method reduces list-valued validation details into counts that are convenient for
		Streamlit metrics, summary tables, CSV exports, and report writers. Detailed lists are
		retained on the model itself; this record intentionally presents a compact overview.

		Returns:
			Dict[str, Any]: Flat validation summary containing validity, row counts, file counts,
			match counts, duplicate counts, error counts, and warning counts. If rendering fails,
			the exception is logged and the original conservative fallback summary is returned.
		"""
		try:
			return {
					'Manifest Valid': self.is_valid,
					'Manifest Rows': self.total_manifest_rows,
					'Uploaded Files': self.total_uploaded_files,
					'Matched Files': len( self.matched_files ),
					'Missing Files': len( self.missing_files ),
					'Extra Files': len( self.extra_files ),
					'Duplicate Manifest Files': len( self.duplicate_manifest_files ),
					'Errors': len( self.errors ),
					'Warnings': len( self.warnings )
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( ) -> Dict[str, Any]'
			Logger( ).write( error )
			return {
					'Manifest Valid': False,
					'Manifest Rows': 0,
					'Uploaded Files': 0,
					'Matched Files': 0,
					'Missing Files': 0,
					'Extra Files': 0,
					'Duplicate Manifest Files': 0,
					'Errors': 1,
					'Warnings': 0
			}

class BatchManifest( ):
	"""Load, normalize, validate, and convert batch application-data manifests.

	The ``BatchManifest`` class is the manifest-processing service for Fiddy batch workflows.
	It reads CSV files, normalizes user-facing column headers into canonical internal field
	names, validates that required columns are present, converts manifest rows into typed
	``BatchManifestRecord`` objects, identifies duplicate manifest file names, and validates
	manifest rows against the uploaded label files selected by the reviewer.

	The class keeps errors and warnings as instance state so callers can inspect manifest
	processing issues after loading or validation. Errors represent blocking issues such as an
	unreadable manifest, missing required columns, duplicate file names, or manifest rows that
	cannot be matched to uploaded labels. Warnings represent non-blocking issues, such as
	uploaded label files that do not have matching manifest rows.

	Column normalization supports common reviewer-friendly aliases such as ``file``,
	``file name``, ``label file``, ``brand``, ``class/type``, ``abv``, ``producer/bottler``,
	``country of origin``, and ``application reference``. This allows CSV files exported from
	different tools or manually prepared by reviewers to be accepted without requiring exact
	internal column names.

	Attributes:
		_df_manifest (pd.DataFrame): Most recently loaded and normalized manifest DataFrame.
		_records (List[BatchManifestRecord]): Most recently parsed manifest records.
		_column_map (Dict[str, str]): Supported source-column aliases mapped to canonical names.
		_required_columns (List[str]): Canonical columns required for batch verification.
		_optional_columns (List[str]): Canonical columns accepted when present.
		_errors (List[str]): Blocking manifest processing or validation errors.
		_warnings (List[str]): Non-blocking manifest processing or validation warnings.
	"""
	
	_df_manifest: pd.DataFrame
	_records: List[ BatchManifestRecord ]
	_column_map: Dict[ str, str ]
	_required_columns: List[ str ]
	_optional_columns: List[ str ]
	_errors: List[ str ]
	_warnings: List[ str ]
	
	def __init__( self ) -> None:
		"""Initialize manifest state, required columns, optional columns, and aliases.

		The constructor prepares empty record, error, and warning collections. It also defines
		the canonical required and optional manifest columns used by the batch verifier and the
		alias map used to normalize reviewer-supplied CSV headers.

		The required-column list represents the minimum application data needed to run batch
		verification in the current prototype. Optional fields are accepted when present and are
		passed through to ``BatchManifestRecord`` objects.

		Returns:
			None.
		"""
		self._records = [ ]
		self._errors = [ ]
		self._warnings = [ ]
		
		self._required_columns = [
				'file_name',
				'brand_name',
				'class_type',
				'beverage_type',
				'alcohol_content',
				'net_contents',
				'producer_bottler'
		]
		
		self._optional_columns = [
				'proof',
				'imported',
				'importer',
				'country_of_origin',
				'cola_id',
				'notes'
		]
		
		self._column_map = {
				'file': 'file_name',
				'filename': 'file_name',
				'file name': 'file_name',
				'file_name': 'file_name',
				'label_file': 'file_name',
				'label file': 'file_name',
				'brand': 'brand_name',
				'brand name': 'brand_name',
				'brand_name': 'brand_name',
				'class': 'class_type',
				'type': 'class_type',
				'class type': 'class_type',
				'class/type': 'class_type',
				'class_type': 'class_type',
				'beverage': 'beverage_type',
				'beverage type': 'beverage_type',
				'beverage_type': 'beverage_type',
				'abv': 'alcohol_content',
				'alcohol content': 'alcohol_content',
				'alcohol_content': 'alcohol_content',
				'alcohol content (% abv)': 'alcohol_content',
				'proof': 'proof',
				'net contents': 'net_contents',
				'net_contents': 'net_contents',
				'contents': 'net_contents',
				'producer': 'producer_bottler',
				'bottler': 'producer_bottler',
				'producer bottler': 'producer_bottler',
				'producer/bottler': 'producer_bottler',
				'producer_bottler': 'producer_bottler',
				'imported': 'imported',
				'importer': 'importer',
				'country': 'country_of_origin',
				'country of origin': 'country_of_origin',
				'country_of_origin': 'country_of_origin',
				'cola': 'cola_id',
				'cola id': 'cola_id',
				'cola_id': 'cola_id',
				'application reference': 'cola_id',
				'notes': 'notes'
		}
	
	@property
	def required_columns( self ) -> List[ str ]:
		"""Return the canonical manifest columns required for batch verification.

		The returned list defines the minimum normalized columns that must be present after
		column-name normalization. These fields are required because the batch verifier needs a
		file name for matching, core product identity fields, alcohol content, net contents,
		and producer/bottler data to construct meaningful application records.

		Returns:
			List[str]: Required canonical manifest column names.
		"""
		return self._required_columns
	
	@property
	def optional_columns( self ) -> List[ str ]:
		"""Return the optional manifest columns supported by the verifier.

		Optional columns are accepted when present and are included in parsed
		``BatchManifestRecord`` objects. They are not required for a manifest to load, but they
		provide additional application context such as proof, import status, importer, country of
		origin, COLA reference, and reviewer notes.

		Returns:
			List[str]: Optional canonical manifest column names.
		"""
		return self._optional_columns
	
	def normalize_column_name( self, column_name: str ) -> str:
		"""Normalize one manifest column header to a canonical internal column name.

		This method standardizes a source column header by trimming whitespace, lowercasing the
		text, replacing hyphens and underscores with spaces, and collapsing repeated spaces. The
		standardized header is then resolved through the alias map. Recognized aliases are mapped
		to canonical names such as ``file_name``, ``brand_name``, ``class_type``, and
		``alcohol_content``. Unrecognized headers are still normalized into snake-style names so
		they can remain available to downstream code without breaking DataFrame handling.

		Args:
			column_name (str): Source manifest column header from a CSV file or DataFrame.

		Returns:
			str: Canonical column name when the source header is recognized; otherwise, a
			normalized fallback name based on the original header. If normalization fails, the
			exception is logged and an empty string is returned, preserving the original fallback.
		"""
		try:
			throw_if( 'column_name', column_name )
			
			key = column_name.strip( ).lower( ).replace( '-', ' ' ).replace( '_', ' ' )
			key = ' '.join( key.split( ) )
			
			if key in self._column_map:
				return self._column_map[ key ]
			
			return key.replace( ' ', '_' )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_column_name( column_name: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_columns( self, df_manifest: pd.DataFrame ) -> pd.DataFrame:
		"""Normalize all manifest DataFrame columns to canonical names.

		This method applies ``normalize_column_name`` to every column in the supplied manifest
		DataFrame and returns a renamed DataFrame. Empty or missing manifests are converted to an
		empty DataFrame so downstream validation can produce clear required-column messages.

		Args:
			df_manifest: Source manifest DataFrame read from CSV or supplied by a caller.

		Returns:
			pd.DataFrame: Manifest DataFrame with normalized column names. If column normalization
			fails unexpectedly, the exception is logged and the original DataFrame fallback is
			returned.
		"""
		try:
			if df_manifest is None or df_manifest.empty:
				return pd.DataFrame( )
			
			rename_map = {
					column: self.normalize_column_name( str( column ) )
					for column in df_manifest.columns
			}
			
			return df_manifest.rename( columns=rename_map )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_columns( df_manifest: pd.DataFrame ) -> pd.DataFrame'
			Logger( ).write( error )
			return df_manifest
	
	def read_csv( self, file_path: str | Path ) -> pd.DataFrame:
		"""Read and normalize a manifest CSV file using encoding fallbacks.

		The method validates the supplied file path, confirms that the path exists, reads the
		file as bytes, and then attempts to parse it using common encodings in a stable order:
		``utf-8-sig``, ``utf-8``, ``cp1252``, and ``latin1``. If all strict decoding attempts
		fail, it performs a final Latin-1 read with replacement behavior so reviewer-provided
		CSV files with problematic characters can still be handled when possible.

		After a successful read, the resulting DataFrame is normalized through
		``normalize_columns`` before being returned. File-not-found and read failures are
		recorded in the manifest error list so the UI can display actionable messages.

		Args:
			file_path (str | Path): Path to the manifest CSV file.

		Returns:
			pd.DataFrame: Normalized manifest DataFrame. If the file does not exist or cannot be
			read, an empty DataFrame fallback is returned after recording or logging the failure.
		"""
		try:
			throw_if( 'file_path', file_path )
			
			path = Path( file_path )
			if not path.exists( ):
				self._errors.append( f'Manifest file was not found: {path}' )
				return pd.DataFrame( )
			
			file_bytes = path.read_bytes( )
			encodings = [ 'utf-8-sig', 'utf-8', 'cp1252', 'latin1' ]
			
			for encoding in encodings:
				try:
					self._df_manifest = pd.read_csv( BytesIO( file_bytes ), encoding=encoding )
					self._df_manifest = self.normalize_columns( self._df_manifest )
					return self._df_manifest
				except UnicodeDecodeError:
					continue
			
			self._df_manifest = pd.read_csv( BytesIO( file_bytes ), encoding='latin1',
				encoding_errors='replace' )
			self._df_manifest = self.normalize_columns( self._df_manifest )
			
			return self._df_manifest
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'read_csv( file_path: str | Path ) -> pd.DataFrame'
			Logger( ).write( error )
			self._errors.append( f'Manifest CSV could not be read: {e}' )
			return pd.DataFrame( )
	
	def parse_bool( self, value: object ) -> bool:
		"""Parse a manifest value into a Boolean import indicator.

		This method converts common truthy manifest values into ``True``. Empty values,
		missing values, pandas null values, and unrecognized values are treated as ``False``.
		The accepted truthy values are ``1``, ``true``, ``yes``, ``y``, ``imported``, and ``x``
		after string conversion, trimming, and lowercasing.

		Args:
			value (object): Source manifest value from the ``imported`` column or equivalent.

		Returns:
			bool: Parsed Boolean value. If parsing fails unexpectedly, the exception is logged and
			``False`` is returned, preserving the original conservative fallback behavior.
		"""
		try:
			if value is None or pd.isna( value ):
				return False
			
			text = str( value ).strip( ).lower( )
			return text in (
					'1',
					'true',
					'yes',
					'y',
					'imported',
					'x'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'parse_bool( value: object ) -> bool'
			Logger( ).write( error )
			return False
	
	def parse_float( self, value: object ) -> Optional[ float ]:
		"""Parse a manifest value into an optional floating-point number.

		This method is used for numeric manifest fields such as ABV and proof. It accepts
		native numeric values and string values. Percent signs and comma separators are removed
		before conversion so values such as ``45%`` or ``1,000`` can be parsed when appropriate.
		Empty, missing, pandas null, and invalid numeric values are treated as unavailable.

		Args:
			value (object): Source manifest value to parse as a float.

		Returns:
			Optional[float]: Parsed floating-point value, or ``None`` when the value is empty,
			missing, invalid, or cannot be parsed. Unexpected parsing exceptions are logged before
			returning the existing ``None`` fallback.
		"""
		try:
			if value is None or pd.isna( value ):
				return None
			
			text = str( value ).strip( )
			if not text:
				return None
			
			return float( text.replace( '%', '' ).replace( ',', '' ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'parse_float( value: object ) -> Optional[float]'
			Logger( ).write( error )
			return None
	
	def get_text_value( self, row: pd.Series, column_name: str ) -> str:
		"""Safely read and trim a text value from a manifest row.

		The method checks whether the requested column exists in the row, reads the value when
		available, treats missing and pandas null values as empty strings, and returns the
		trimmed string representation. It is used by row conversion to avoid repeated null and
		column-existence checks for each text field.

		Args:
			row (pd.Series): Manifest row being converted to a record.
			column_name (str): Canonical column name to read from the row.

		Returns:
			str: Trimmed text value, or an empty string when the column is missing, null, empty, or
			cannot be read. Unexpected failures are logged before returning the existing fallback.
		"""
		try:
			throw_if( 'column_name', column_name )
			
			if column_name not in row.index:
				return ''
			
			value = row.get( column_name, '' )
			if value is None or pd.isna( value ):
				return ''
			
			return str( value ).strip( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_text_value( row: pd.Series, column_name: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def validate_required_columns( self, df_manifest: pd.DataFrame ) -> List[ str ]:
		"""Validate that a normalized manifest contains all required columns.

		This method checks the supplied DataFrame after column normalization and returns a list
		of validation errors. It does not mutate the instance error list directly; callers decide
		when to append the returned messages to ``self._errors``. Empty or unreadable manifests
		produce a single clear error message.

		Args:
			df_manifest (pd.DataFrame): Normalized manifest DataFrame to validate.

		Returns:
			List[str]: Validation error messages. An empty list indicates that all required
			columns are present. If validation itself fails unexpectedly, the exception is logged
			and the original explanatory fallback message is returned.
		"""
		errors = [ ]
		
		try:
			if df_manifest is None or df_manifest.empty:
				return [ 'Manifest is empty or could not be read.' ]
			
			available_columns = set( df_manifest.columns )
			for column in self._required_columns:
				if column not in available_columns:
					errors.append( f'Missing required manifest column: {column}' )
			
			return errors
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'validate_required_columns( df_manifest: pd.DataFrame ) -> List[str]'
			Logger( ).write( error )
			return [ f'Manifest required-column validation failed: {e}' ]
	
	def get_duplicate_file_names( self, records: List[ BatchManifestRecord ] ) -> List[ str ]:
		"""Identify duplicate manifest file names using case-insensitive comparison.

		Duplicate detection is based on trimmed lowercase file names so values that differ only
		by case are treated as duplicates. The returned values preserve the duplicate record's
		stored file name rather than the lowercase comparison key so reviewer-facing messages
		remain recognizable.

		Args:
			records (List[BatchManifestRecord]): Manifest records to inspect.

		Returns:
			List[str]: Sorted duplicate manifest file names. If duplicate detection fails, the
			exception is logged and an empty list is returned, preserving the original fallback.
		"""
		try:
			throw_if( 'records', records )
			
			seen = set( )
			duplicates = set( )
			
			for record in records:
				file_name = record.file_name.strip( ).lower( )
				if file_name in seen:
					duplicates.add( record.file_name )
				else:
					seen.add( file_name )
			
			return sorted( duplicates )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_duplicate_file_names( records: List[BatchManifestRecord] ) -> List[str]'
			Logger( ).write( error )
			return [ ]
	
	def dataframe_to_records( self, df_manifest: pd.DataFrame ) -> List[ BatchManifestRecord ]:
		"""Convert a normalized manifest DataFrame into typed manifest records.

		This method iterates through the normalized DataFrame and constructs one
		``BatchManifestRecord`` for each row. Text fields are read through ``get_text_value``;
		ABV and proof are parsed through ``parse_float``; the import indicator is parsed through
		``parse_bool``; and missing beverage type values default to distilled spirits. The method
		accumulates successfully constructed records and returns the partial list if a later row
		conversion fails.

		Args:
			df_manifest (pd.DataFrame): Normalized manifest DataFrame with canonical column names.

		Returns:
			List[BatchManifestRecord]: Parsed manifest records. If row conversion fails
			unexpectedly, the exception is logged, an existing reviewer-facing error message is
			appended, and records parsed before the failure are returned.
		"""
		records = [ ]
		
		try:
			if df_manifest is None or df_manifest.empty:
				return records
			
			for _, row in df_manifest.iterrows( ):
				record = BatchManifestRecord(
					file_name=self.get_text_value( row, 'file_name' ),
					brand_name=self.get_text_value( row, 'brand_name' ),
					class_type=self.get_text_value( row, 'class_type' ),
					beverage_type=self.get_text_value( row, 'beverage_type' )
					              or BEVERAGE_TYPE_DISTILLED_SPIRITS,
					alcohol_content=self.parse_float( row.get( 'alcohol_content', None ) ),
					proof=self.parse_float( row.get( 'proof', None ) ),
					net_contents=self.get_text_value( row, 'net_contents' ),
					producer_bottler=self.get_text_value( row, 'producer_bottler' ),
					imported=self.parse_bool( row.get( 'imported', False ) ),
					importer=self.get_text_value( row, 'importer' ),
					country_of_origin=self.get_text_value( row, 'country_of_origin' ),
					cola_id=self.get_text_value( row, 'cola_id' ),
					notes=self.get_text_value( row, 'notes' )
				)
				
				records.append( record )
			
			return records
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'dataframe_to_records( df_manifest: pd.DataFrame ) -> List[BatchManifestRecord]'
			Logger( ).write( error )
			self._errors.append( f'Manifest rows could not be converted to records: {e}' )
			return records
	
	def load_csv( self, file_path: str | Path ) -> List[ BatchManifestRecord ]:
		"""Load a CSV manifest file and convert it to manifest records.

		This method resets the current error and warning lists, reads the CSV file with encoding
		fallbacks, validates required columns, converts rows to typed records, detects duplicate
		file names, records duplicate-name errors, and returns the parsed records. It is the main
		entry point for turning a reviewer-uploaded manifest CSV into batch verification inputs.

		Args:
			file_path (str | Path): Path to the manifest CSV file.

		Returns:
			List[BatchManifestRecord]: Parsed manifest records. If loading fails or required-column
			validation fails, the method logs or records the failure and returns an empty list in
			accordance with the original behavior.
		"""
		try:
			throw_if( 'file_path', file_path )
			
			self._errors = [ ]
			self._warnings = [ ]
			
			df_manifest = self.read_csv( file_path )
			column_errors = self.validate_required_columns( df_manifest )
			
			if column_errors:
				self._errors.extend( column_errors )
				return [ ]
			
			self._records = self.dataframe_to_records( df_manifest )
			duplicate_files = self.get_duplicate_file_names( self._records )
			
			if duplicate_files:
				self._errors.append( f'Duplicate manifest file names found: {duplicate_files}' )
			
			return self._records
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'load_csv( file_path: str | Path ) -> List[BatchManifestRecord]'
			Logger( ).write( error )
			self._errors.append( f'Manifest load failed: {e}' )
			return [ ]
	
	def get_record_map( self, records: List[ BatchManifestRecord ] ) -> Dict[ str, BatchManifestRecord ]:
		"""Create a case-insensitive lookup map from file name to manifest record.

		This method builds a dictionary keyed by trimmed lowercase manifest file names. It is
		used by batch processing code to quickly find the application-data record associated
		with an uploaded label file. Records without file names are skipped because they cannot
		be matched to uploads.

		Args:
			records (List[BatchManifestRecord]): Manifest records to include in the lookup map.

		Returns:
			Dict[str, BatchManifestRecord]: Manifest record map keyed by lowercase file name. If
			mapping fails unexpectedly, the exception is logged and an empty dictionary fallback is
			returned.
		"""
		try:
			throw_if( 'records', records )
			
			return {
					record.file_name.strip( ).lower( ): record
					for record in records
					if record.file_name
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_record_map( records: List[BatchManifestRecord] ) -> Dict[str, BatchManifestRecord]'
			Logger( ).write( error )
			return { }
	
	def validate_against_files( self, records: List[ BatchManifestRecord ],
			file_paths: Iterable[ str | Path ] ) -> BatchManifestValidationResult:
		"""Validate parsed manifest records against uploaded label files.

		This method compares manifest file names to uploaded file names using case-insensitive
		matching. It returns matched manifest names, manifest rows with no corresponding upload,
		uploaded files with no corresponding manifest row, duplicate manifest file names, and the
		combined error and warning collections.

		Missing uploaded files for manifest rows are treated as errors because those rows cannot
		be processed. Extra uploaded files are treated as warnings because the batch may still
		process matched records. Duplicate manifest file names are treated as errors because they
		make file-to-record assignment ambiguous.

		Args:
			records (List[BatchManifestRecord]): Manifest records parsed from the normalized CSV.
			file_paths (Iterable[str | Path]): Uploaded label file paths selected for batch
				processing.

		Returns:
			BatchManifestValidationResult: Manifest/file matching validation result. If validation
			fails unexpectedly, the exception is logged and a validation-result fallback with
			``is_valid=False`` and the original failure message is returned.
		"""
		try:
			throw_if( 'records', records )
			throw_if( 'file_paths', file_paths )
			
			uploaded_names = sorted(
				[
						Path( file_path ).name
						for file_path in file_paths
				]
			)
			
			manifest_names = sorted(
				[
						record.file_name
						for record in records
						if record.file_name
				]
			)
			
			uploaded_lookup = {
					name.lower( )
					for name in uploaded_names
			}
			
			manifest_lookup = {
					name.lower( )
					for name in manifest_names
			}
			
			matched = sorted(
				[
						name
						for name in manifest_names
						if name.lower( ) in uploaded_lookup
				]
			)
			
			missing = sorted(
				[
						name
						for name in manifest_names
						if name.lower( ) not in uploaded_lookup
				]
			)
			
			extra = sorted(
				[
						name
						for name in uploaded_names
						if name.lower( ) not in manifest_lookup
				]
			)
			
			duplicates = self.get_duplicate_file_names( records )
			errors = list( self._errors )
			warnings = list( self._warnings )
			
			if missing:
				errors.append( f'Manifest rows without uploaded label files: {len( missing )}' )
			
			if extra:
				warnings.append( f'Uploaded label files without manifest rows: {len( extra )}' )
			
			if duplicates:
				errors.append( f'Duplicate manifest file names: {len( duplicates )}' )
			
			return BatchManifestValidationResult(
				is_valid=not errors,
				total_manifest_rows=len( records ),
				total_uploaded_files=len( uploaded_names ),
				matched_files=matched,
				missing_files=missing,
				extra_files=extra,
				duplicate_manifest_files=duplicates,
				errors=errors,
				warnings=warnings
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'validate_against_files( *args ) -> BatchManifestValidationResult'
			Logger( ).write( error )
			return BatchManifestValidationResult(
				is_valid=False,
				errors=[
						f'Manifest/file validation failed: {e}'
				]
			)
	
	def create_sample_manifest_dataframe( self ) -> pd.DataFrame:
		"""Create a sample manifest DataFrame for templates, tests, and demonstrations.

		The sample manifest includes two representative label-application records: one distilled
		spirits example and one wine example. The structure demonstrates the canonical columns
		expected by the batch manifest loader, including optional proof, import, COLA reference,
		and notes fields.

		Returns:
			pd.DataFrame: Sample application manifest with canonical column names. If sample
			construction fails unexpectedly, the exception is logged and an empty DataFrame fallback
			is returned.
		"""
		try:
			records = [
					{
							'file_name': 'old_tom_distillery.png',
							'brand_name': 'OLD TOM DISTILLERY',
							'class_type': 'Kentucky Straight Bourbon Whiskey',
							'beverage_type': BEVERAGE_TYPE_DISTILLED_SPIRITS,
							'alcohol_content': 45.0,
							'proof': 90.0,
							'net_contents': '750 mL',
							'producer_bottler': 'Old Tom Distillery',
							'imported': False,
							'importer': '',
							'country_of_origin': '',
							'cola_id': 'SAMPLE-001',
							'notes': 'Sample distilled spirits label.'
					},
					{
							'file_name': 'stones_throw.png',
							'brand_name': "STONE'S THROW",
							'class_type': 'Red Wine',
							'beverage_type': 'Wine',
							'alcohol_content': 13.5,
							'proof': None,
							'net_contents': '750 mL',
							'producer_bottler': "Stone's Throw Winery",
							'imported': False,
							'importer': '',
							'country_of_origin': '',
							'cola_id': 'SAMPLE-002',
							'notes': 'Sample wine label.'
					}
			]
			
			return pd.DataFrame( records )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_sample_manifest_dataframe( ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	@property
	def errors( self ) -> List[ str ]:
		"""Return manifest processing errors collected by this instance.

		The returned list contains blocking issues recorded during CSV reading, required-column
		validation, row conversion, duplicate detection, loading, and manifest/file matching.
		Callers can use these messages to populate reviewer-facing error panels or diagnostics.

		Returns:
			List[str]: Manifest processing errors currently stored on the instance.
		"""
		return self._errors
	
	@property
	def warnings( self ) -> List[ str ]:
		"""Return manifest processing warnings collected by this instance.

		The returned list contains non-blocking issues recorded during manifest processing or
		manifest/file matching. In the current workflow, extra uploaded files without manifest
		rows are warnings because matched manifest rows may still be processable.

		Returns:
			List[str]: Manifest processing warnings currently stored on the instance.
		"""
		return self._warnings