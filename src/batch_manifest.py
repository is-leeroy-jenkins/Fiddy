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
        batch_manifest.py
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from io import BytesIO
import pandas as pd
from pydantic import BaseModel, Field

from config import throw_if
from src.constants import BEVERAGE_TYPE_DISTILLED_SPIRITS
from src.models import LabelApplication

class BatchManifestRecord( BaseModel ):
	"""
		Purpose:
		--------
		Represent one application-data row from a batch manifest file.
	
		Parameters:
		-----------
		None
	
		Returns:
		--------
		None
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
		"""
			Purpose:
			--------
			Convert the manifest row into a LabelApplication used by the verifier.
	
			Parameters:
			-----------
			None
	
			Returns:
			--------
			LabelApplication: Expected application values for one label file.
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
		except Exception:
			return LabelApplication( )

class BatchManifestValidationResult( BaseModel ):
	"""
		Purpose:
		--------
		Represent validation results for a manifest and uploaded label-file set.
	
		Parameters:
		-----------
		None
	
		Returns:
		--------
		None
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
		"""
		Purpose:
		--------
		Convert manifest validation results into a display-ready dictionary.

		Parameters:
		-----------
		None

		Returns:
		--------
		Dict[str, Any]: Flat validation summary record.
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
		except Exception:
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
	"""
	Purpose:
	--------
	Load, normalize, validate, and convert batch application-data manifests for label
	verification.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
	"""
	
	_df_manifest: pd.DataFrame
	_records: List[ BatchManifestRecord ]
	_column_map: Dict[ str, str ]
	_required_columns: List[ str ]
	_optional_columns: List[ str ]
	_errors: List[ str ]
	_warnings: List[ str ]
	
	def __init__( self ) -> None:
		"""
		Purpose:
		--------
		Initialize manifest column rules and supported aliases.

		Parameters:
		-----------
		None

		Returns:
		--------
		None
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
		"""
			Purpose:
			--------
			Return the manifest columns required for batch verification.
	
			Parameters:
			-----------
			None
	
			Returns:
			--------
			List[str]: Required manifest column names.
		"""
		return self._required_columns
	
	@property
	def optional_columns( self ) -> List[ str ]:
		"""
			Purpose:
			--------
			Return optional manifest columns supported by the verifier.
	
			Parameters:
			-----------
			None
	
			Returns:
			--------
			List[str]: Optional manifest column names.
		"""
		return self._optional_columns
	
	def normalize_column_name( self, column_name: str ) -> str:
		"""
			Purpose:
			--------
			Normalize one manifest column name to the canonical internal column name.
	
			Parameters:
			-----------
			column_name (str): Source manifest column name.
	
			Returns:
			--------
			str: Canonical column name when recognized; otherwise normalized original name.
		"""
		try:
			throw_if( 'column_name', column_name )
			
			key = column_name.strip( ).lower( ).replace( '-', ' ' ).replace( '_', ' ' )
			key = ' '.join( key.split( ) )
			
			if key in self._column_map:
				return self._column_map[ key ]
			
			return key.replace( ' ', '_' )
		except Exception:
			return ''
	
	def normalize_columns( self, df_manifest: pd.DataFrame ) -> pd.DataFrame:
		"""
			Purpose:
			--------
			Normalize manifest DataFrame column names to canonical names.
	
			Parameters:
			-----------
			df_manifest (pd.DataFrame): Source manifest DataFrame.
	
			Returns:
			--------
			pd.DataFrame: Manifest DataFrame with normalized column names.
		"""
		try:
			if df_manifest is None or df_manifest.empty:
				return pd.DataFrame( )
			
			rename_map = {
					column: self.normalize_column_name( str( column ) )
					for column in df_manifest.columns
			}
			
			return df_manifest.rename( columns=rename_map )
		except Exception:
			return df_manifest
	
	def read_csv( self, file_path: str | Path ) -> pd.DataFrame:
		"""
			Purpose:
			--------
			Read a manifest CSV file into a normalized DataFrame using common encoding fallbacks.
		
			Parameters:
			-----------
			file_path (str | Path): Path to the manifest CSV file.
		
			Returns:
			--------
			pd.DataFrame: Normalized manifest DataFrame.
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
			self._errors.append( f'Manifest CSV could not be read: {e}' )
			return pd.DataFrame( )
	
	def parse_bool( self, value: object ) -> bool:
		"""
			Purpose:
			--------
			Parse common truthy and falsy manifest values into a Boolean.
	
			Parameters:
			-----------
			value (object): Source manifest value.
	
			Returns:
			--------
			bool: Parsed Boolean value.
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
		except Exception:
			return False
	
	def parse_float( self, value: object ) -> Optional[ float ]:
		"""
			Purpose:
			--------
			Parse numeric manifest values into float values.
	
			Parameters:
			-----------
			value (object): Source manifest value.
	
			Returns:
			--------
			Optional[float]: Parsed float, or None when unavailable.
		"""
		try:
			if value is None or pd.isna( value ):
				return None
			
			text = str( value ).strip( )
			if not text:
				return None
			
			return float( text.replace( '%', '' ).replace( ',', '' ) )
		except Exception:
			return None
	
	def get_text_value( self, row: pd.Series, column_name: str ) -> str:
		"""
			Purpose:
			--------
			Safely read a text value from a manifest row.
	
			Parameters:
			-----------
			row (pd.Series): Manifest row.
			column_name (str): Column name to read.
	
			Returns:
			--------
			str: Text value, or empty string when unavailable.
		"""
		try:
			throw_if( 'column_name', column_name )
			
			if column_name not in row.index:
				return ''
			
			value = row.get( column_name, '' )
			if value is None or pd.isna( value ):
				return ''
			
			return str( value ).strip( )
		except Exception:
			return ''
	
	def validate_required_columns( self, df_manifest: pd.DataFrame ) -> List[ str ]:
		"""
			Purpose:
			--------
			Validate that the manifest includes the required application-data columns.
	
			Parameters:
			-----------
			df_manifest (pd.DataFrame): Manifest DataFrame to validate.
	
			Returns:
			--------
			List[str]: Validation error messages.
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
			return [ f'Manifest required-column validation failed: {e}' ]
	
	def get_duplicate_file_names( self, records: List[ BatchManifestRecord ] ) -> List[ str ]:
		"""
			Purpose:
			--------
			Identify duplicate file names in manifest records.
	
			Parameters:
			-----------
			records (List[BatchManifestRecord]): Manifest records to inspect.
	
			Returns:
			--------
			List[str]: Duplicate manifest file names.
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
		except Exception:
			return [ ]
	
	def dataframe_to_records( self, df_manifest: pd.DataFrame ) -> List[ BatchManifestRecord ]:
		"""
		Purpose:
		--------
		Convert a normalized manifest DataFrame into manifest records.

		Parameters:
		-----------
		df_manifest (pd.DataFrame): Normalized manifest DataFrame.

		Returns:
		--------
		List[BatchManifestRecord]: Parsed manifest records.
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
			self._errors.append( f'Manifest rows could not be converted to records: {e}' )
			return records
	
	def load_csv( self, file_path: str | Path ) -> List[ BatchManifestRecord ]:
		"""
			Purpose:
			--------
			Load a CSV manifest file and convert it to manifest records.
	
			Parameters:
			-----------
			file_path (str | Path): Path to the manifest CSV file.
	
			Returns:
			--------
			List[BatchManifestRecord]: Parsed manifest records.
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
			self._errors.append( f'Manifest load failed: {e}' )
			return [ ]
	
	def get_record_map( self, records: List[ BatchManifestRecord ] ) -> Dict[ str, BatchManifestRecord ]:
		"""
		Purpose:
		--------
		Create a case-insensitive map from file name to manifest record.

		Parameters:
		-----------
		records (List[BatchManifestRecord]): Manifest records.

		Returns:
		--------
		Dict[str, BatchManifestRecord]: Manifest record map keyed by lowercase file name.
		"""
		try:
			throw_if( 'records', records )
			
			return {
					record.file_name.strip( ).lower( ): record
					for record in records
					if record.file_name
			}
		except Exception:
			return { }
	
	def validate_against_files( self, records: List[ BatchManifestRecord ],
			file_paths: Iterable[ str | Path ] ) -> BatchManifestValidationResult:
		"""
		Purpose:
		--------
		Validate manifest records against uploaded label files.

		Parameters:
		-----------
		records (List[BatchManifestRecord]): Manifest records.
		file_paths (Iterable[str | Path]): Uploaded label file paths.

		Returns:
		--------
		BatchManifestValidationResult: Manifest/file matching validation result.
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
			return BatchManifestValidationResult(
				is_valid=False,
				errors=[
						f'Manifest/file validation failed: {e}'
				]
			)
	
	def create_sample_manifest_dataframe( self ) -> pd.DataFrame:
		"""
		Purpose:
		--------
		Create a sample manifest DataFrame suitable for templates and tests.

		Parameters:
		-----------
		None

		Returns:
		--------
		pd.DataFrame: Sample application manifest.
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
		except Exception:
			return pd.DataFrame( )
	
	@property
	def errors( self ) -> List[ str ]:
		"""
		Purpose:
		--------
		Return manifest processing errors.

		Parameters:
		-----------
		None

		Returns:
		--------
		List[str]: Manifest processing errors.
		"""
		return self._errors
	
	@property
	def warnings( self ) -> List[ str ]:
		"""
		Purpose:
		--------
		Return manifest processing warnings.

		Parameters:
		-----------
		None

		Returns:
		--------
		List[str]: Manifest processing warnings.
		"""
		return self._warnings
