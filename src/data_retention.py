'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                data_retention.py
      Author:                  Terry D. Eppler
      Created:                 06-07-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-07-2026
    ******************************************************************************************
    <copyright file="data_retention.py" company="Terry D. Eppler">

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
        Provides centralized redaction and no-persistence policy enforcement for Fiddy.

        This module defines the runtime policy used to prevent long-term storage of uploaded
        label images, raw OCR text, extracted label values, application values, local file paths,
        and sensitive evidence text. It supports reviewer and stakeholder evidence packages by
        preserving operational information such as requirement identifiers, rule identifiers,
        statuses, severity, confidence, timing, counts, SLA metrics, acceptance status, and
        reviewer action categories while redacting sensitive label and application content.

        The module does not write files unless explicitly asked by a caller. It does not persist
        images. It does not call external services. It provides reusable functions that later
        application, report-writing, and acceptance-harness code can call before producing CSV,
        JSON, Markdown, or disk-based evidence outputs.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
from pydantic import BaseModel, Field

import config as cfg
from booger import Error, Logger
from config import throw_if

# ==========================================================================================
# Data Retention Constants
# ==========================================================================================

REDACTION_TEXT: str = '[REDACTED]'
RAW_OCR_REDACTION_NOTICE: str = 'Raw OCR text redacted by Fiddy no-persistence policy.'
EXPORT_DISABLED_NOTICE: str = 'Export disabled by Fiddy no-persistence policy.'

SENSITIVE_COLUMN_KEYWORDS: tuple[ str, ... ] = (
		'application',
		'application value',
		'expected',
		'extracted',
		'observed',
		'ocr',
		'raw text',
		'raw_text',
		'label text',
		'text',
		'evidence',
		'message',
		'warning context',
		'context',
		'file path',
		'filepath',
		'path',
		'image',
		'image path',
		'label image',
		'brand',
		'brand name',
		'class',
		'class type',
		'type',
		'abv',
		'alcohol',
		'alcohol content',
		'net contents',
		'producer',
		'bottler',
		'importer',
		'country',
		'country of origin',
		'address',
		'government warning'
)

SAFE_COLUMN_KEYWORDS: tuple[ str, ... ] = (
		'id',
		'rule id',
		'check id',
		'item id',
		'requirement id',
		'category',
		'name',
		'requirement name',
		'field',
		'status',
		'severity',
		'confidence',
		'reviewer action',
		'requires human review',
		'overall status',
		'processing seconds',
		'sla',
		'seconds',
		'breach',
		'rate',
		'count',
		'total',
		'minimum',
		'maximum',
		'average',
		'median',
		'p50',
		'p90',
		'p95',
		'throughput',
		'met',
		'partially met',
		'not met',
		'not evaluated',
		'not applicable',
		'created on',
		'evaluated on',
		'started on',
		'completed on',
		'acceptance',
		'keyboard',
		'high contrast',
		'large text',
		'deployment target'
)

SENSITIVE_DICT_KEYS: tuple[ str, ... ] = (
		'application_label',
		'extracted_label',
		'raw_text',
		'raw_ocr_text',
		'ocr_text',
		'image_path',
		'file_path',
		'path',
		'evidence',
		'message',
		'expected',
		'observed',
		'brand_name',
		'class_type',
		'alcohol_content',
		'net_contents',
		'producer_bottler',
		'country_of_origin',
		'government_warning',
		'warning_context'
)

SAFE_DICT_KEYS: tuple[ str, ... ] = (
		'rule_id',
		'check_id',
		'item_id',
		'requirement_id',
		'field_name',
		'status',
		'severity',
		'confidence',
		'requires_human_review',
		'overall_status',
		'processing_seconds',
		'sla_seconds',
		'within_sla',
		'sla_breach_count',
		'sla_breach_rate',
		'total_files',
		'average_seconds',
		'median_seconds',
		'p95_seconds',
		'acceptance_status',
		'acceptance_percentage',
		'created_on',
		'evaluated_on',
		'started_on',
		'completed_on'
)

# ==========================================================================================
# Data Retention Models
# ==========================================================================================

class DataRetentionSettings( BaseModel ):
	"""Represents resolved data-retention and export settings.

	Purpose:
		Store the effective no-persistence and export policy values resolved from configuration.
		The model is serializable and can be displayed in the UI, written into acceptance status
		tables, or used by downstream code to explain why sensitive values were redacted.

	Attributes:
		no_persistence_mode (bool): Indicates whether strict no-persistence behavior is active.
		long_term_storage_disabled (bool): Indicates whether long-term storage is disabled.
		upload_persistence_enabled (bool): Indicates whether uploaded files may be persisted.
		raw_text_logging_enabled (bool): Indicates whether raw OCR text may be logged.
		raw_ocr_export_enabled (bool): Indicates whether raw OCR text may be exported.
		extracted_data_export_enabled (bool): Indicates whether extracted/application values may
			be exported.
		redacted_evidence_export_enabled (bool): Indicates whether redacted evidence exports are
			allowed.
		file_path_export_enabled (bool): Indicates whether local file paths may be exported.
	"""
	
	no_persistence_mode: bool = Field( default=True )
	long_term_storage_disabled: bool = Field( default=True )
	upload_persistence_enabled: bool = Field( default=False )
	raw_text_logging_enabled: bool = Field( default=False )
	raw_ocr_export_enabled: bool = Field( default=False )
	extracted_data_export_enabled: bool = Field( default=False )
	redacted_evidence_export_enabled: bool = Field( default=True )
	file_path_export_enabled: bool = Field( default=False )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert retention settings into a flat record.

		Purpose:
			Return a dictionary suitable for Streamlit display, CSV export, JSON serialization,
			Markdown reporting, and acceptance evaluation.

		Returns:
			Dict[str, object]: Flat data-retention settings record.
		"""
		try:
			return {
					'No Persistence Mode': self.no_persistence_mode,
					'Long-Term Storage Disabled': self.long_term_storage_disabled,
					'Upload Persistence Enabled': self.upload_persistence_enabled,
					'Raw Text Logging Enabled': self.raw_text_logging_enabled,
					'Raw OCR Export Enabled': self.raw_ocr_export_enabled,
					'Extracted Data Export Enabled': self.extracted_data_export_enabled,
					'Redacted Evidence Export Enabled': self.redacted_evidence_export_enabled,
					'File Path Export Enabled': self.file_path_export_enabled
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'No Persistence Mode': True,
					'Long-Term Storage Disabled': True,
					'Upload Persistence Enabled': False,
					'Raw Text Logging Enabled': False,
					'Raw OCR Export Enabled': False,
					'Extracted Data Export Enabled': False,
					'Redacted Evidence Export Enabled': True,
					'File Path Export Enabled': False
			}

class RedactionResult( BaseModel ):
	"""Represents the result of a redaction operation.

	Purpose:
		Provide a compact summary of a redaction operation, including whether redaction was
		applied, the number of fields redacted, and a reviewer-facing message.

	Attributes:
		redaction_applied (bool): Indicates whether redaction changed the source content.
		redacted_fields (List[str]): Field or column names redacted by policy.
		message (str): Reviewer-facing redaction summary.
	"""
	
	redaction_applied: bool = Field( default=False )
	redacted_fields: List[ str ] = Field( default_factory=list )
	message: str = Field( default='' )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert redaction outcome into a flat record.

		Purpose:
			Return a dictionary suitable for audit tables, acceptance evidence, or debugging
			output.

		Returns:
			Dict[str, object]: Flat redaction result record.
		"""
		try:
			return {
					'Redaction Applied': self.redaction_applied,
					'Redacted Field Count': len( self.redacted_fields ),
					'Redacted Fields': ', '.join( self.redacted_fields ),
					'Message': self.message
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Redaction Applied': True,
					'Redacted Field Count': 0,
					'Redacted Fields': '',
					'Message': 'Redaction result could not be rendered.'
			}

class DataRetentionPolicy( ):
	"""Enforces no-persistence and redacted-export behavior.

	Purpose:
		Centralize all Fiddy decisions about whether raw OCR text, extracted label values,
		application values, evidence text, local file paths, and report payloads may be exported
		or written. The default behavior is conservative: no long-term storage, no upload
		persistence, no raw OCR export, no extracted-data export, no file-path export, and
		redacted operational evidence only.

	Attributes:
		_settings (DataRetentionSettings): Effective retention/export settings resolved from
			configuration.
		_last_redaction_result (RedactionResult): Summary of the most recent redaction operation.
	"""
	
	_settings: DataRetentionSettings
	_last_redaction_result: RedactionResult
	
	def __init__( self ) -> None:
		"""Initialize the retention policy from configuration.

		Purpose:
			Resolve active retention settings from ``config.py`` using secure defaults when
			settings are missing. The object can then be reused by app downloads, report writing,
			acceptance evidence generation, and command-line harnesses.

		Returns:
			None.
		"""
		self._settings = self.get_settings( )
		self._last_redaction_result = RedactionResult( )
	
	@property
	def settings( self ) -> DataRetentionSettings:
		"""Return active retention settings.

		Purpose:
			Expose the resolved retention settings to callers that need to display or evaluate
			the active data-handling posture.

		Returns:
			DataRetentionSettings: Active retention settings.
		"""
		return self._settings
	
	@property
	def no_persistence_mode( self ) -> bool:
		"""Return whether no-persistence mode is active.

		Purpose:
			Expose whether strict no-persistence behavior is enabled.

		Returns:
			bool: True when no-persistence mode is active.
		"""
		return self._settings.no_persistence_mode
	
	@property
	def redacted_exports_enabled( self ) -> bool:
		"""Return whether redacted exports are enabled.

		Purpose:
			Expose whether redacted evidence may be exported or written to disk.

		Returns:
			bool: True when redacted evidence exports are enabled.
		"""
		return self._settings.redacted_evidence_export_enabled
	
	@property
	def last_redaction_result( self ) -> RedactionResult:
		"""Return the last redaction result.

		Purpose:
			Expose the most recent redaction summary for diagnostics, acceptance evidence, or UI
			display.

		Returns:
			RedactionResult: Most recent redaction result.
		"""
		return self._last_redaction_result
	
	def get_config_bool( self, name: str, default: bool ) -> bool:
		"""Read a Boolean configuration setting safely.

		Purpose:
			Return a Boolean configuration value while using the supplied default when the
			setting is unavailable or invalid.

		Args:
			name (str): Configuration setting name.
			default (bool): Default value.

		Returns:
			bool: Resolved Boolean configuration value.
		"""
		try:
			throw_if( 'name', name )
			return bool( getattr( cfg, name, default ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_config_bool( self, name: str, default: bool ) -> bool'
			Logger( ).write( error )
			return default
	
	def get_settings( self ) -> DataRetentionSettings:
		"""Resolve data-retention settings from configuration.

		Purpose:
			Read all no-persistence and export settings from ``config.py`` with conservative
			defaults. Missing settings default to no-persistence behavior.

		Returns:
			DataRetentionSettings: Effective retention settings.
		"""
		try:
			return DataRetentionSettings(
				no_persistence_mode=self.get_config_bool( 'NO_PERSISTENCE_MODE', True ),
				long_term_storage_disabled=self.get_config_bool(
					'LONG_TERM_STORAGE_DISABLED',
					True
				),
				upload_persistence_enabled=self.get_config_bool(
					'ENABLE_UPLOAD_PERSISTENCE',
					False
				),
				raw_text_logging_enabled=self.get_config_bool(
					'ENABLE_RAW_TEXT_LOGGING',
					False
				),
				raw_ocr_export_enabled=self.get_config_bool(
					'ENABLE_RAW_OCR_EXPORT',
					False
				),
				extracted_data_export_enabled=self.get_config_bool(
					'ENABLE_EXTRACTED_DATA_EXPORT',
					False
				),
				redacted_evidence_export_enabled=self.get_config_bool(
					'ENABLE_REDACTED_EVIDENCE_EXPORT',
					True
				),
				file_path_export_enabled=self.get_config_bool(
					'ENABLE_FILE_PATH_EXPORT',
					False
				)
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_settings( self ) -> DataRetentionSettings'
			Logger( ).write( error )
			return DataRetentionSettings( )
	
	def can_export_sensitive_values( self ) -> bool:
		"""Return whether sensitive values may be exported.

		Purpose:
			Determine whether application values, extracted values, observed values, expected
			values, and detailed evidence text may be exported without redaction.

		Returns:
			bool: True only when no-persistence mode is disabled and extracted-data export is
			explicitly enabled.
		"""
		try:
			return (
					not self._settings.no_persistence_mode
					and self._settings.extracted_data_export_enabled
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'can_export_sensitive_values( self ) -> bool'
			Logger( ).write( error )
			return False
	
	def can_export_raw_ocr( self ) -> bool:
		"""Return whether raw OCR text may be exported.

		Purpose:
			Determine whether raw OCR text may appear in JSON, Markdown, CSV, or other export
			outputs.

		Returns:
			bool: True only when no-persistence mode is disabled and raw OCR export is explicitly
			enabled.
		"""
		try:
			return (
					not self._settings.no_persistence_mode
					and self._settings.raw_ocr_export_enabled
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'can_export_raw_ocr( self ) -> bool'
			Logger( ).write( error )
			return False
	
	def can_export_file_paths( self ) -> bool:
		"""Return whether local file paths may be exported.

		Purpose:
			Determine whether local filesystem paths may appear in evidence outputs.

		Returns:
			bool: True only when file path export is explicitly enabled and no-persistence mode is
			disabled.
		"""
		try:
			return (
					not self._settings.no_persistence_mode
					and self._settings.file_path_export_enabled
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'can_export_file_paths( self ) -> bool'
			Logger( ).write( error )
			return False
	
	def can_write_evidence_files( self ) -> bool:
		"""Return whether evidence files may be written.

		Purpose:
			Determine whether callers may write evidence files. Redacted evidence files are
			allowed only when redacted evidence export is enabled. Unredacted sensitive evidence
			is not allowed by this method.

		Returns:
			bool: True when redacted evidence file output is allowed.
		"""
		try:
			return bool( self._settings.redacted_evidence_export_enabled )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'can_write_evidence_files( self ) -> bool'
			Logger( ).write( error )
			return False
	
	def is_safe_column( self, column_name: str ) -> bool:
		"""Determine whether a column is safe to export unchanged.

		Purpose:
			Identify operational columns that can be retained in redacted evidence exports.

		Args:
			column_name (str): Column name to evaluate.

		Returns:
			bool: True when the column is safe to export unchanged.
		"""
		try:
			throw_if( 'column_name', column_name )
			
			normalized = str( column_name ).strip( ).lower( )
			return any( keyword in normalized for keyword in SAFE_COLUMN_KEYWORDS )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'is_safe_column( self, column_name: str ) -> bool'
			Logger( ).write( error )
			return False
	
	def is_sensitive_column( self, column_name: str ) -> bool:
		"""Determine whether a column should be redacted.

		Purpose:
			Classify columns containing sensitive application data, extracted label data, raw OCR
			text, evidence text, or local file paths. Safe operational columns are preserved.

		Args:
			column_name (str): Column name to evaluate.

		Returns:
			bool: True when the column should be redacted.
		"""
		try:
			throw_if( 'column_name', column_name )
			
			normalized = str( column_name ).strip( ).lower( )
			
			if self.is_safe_column( normalized ):
				return False
			
			return any( keyword in normalized for keyword in SENSITIVE_COLUMN_KEYWORDS )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'is_sensitive_column( self, column_name: str ) -> bool'
			Logger( ).write( error )
			return True
	
	def is_safe_key( self, key: str ) -> bool:
		"""Determine whether a dictionary key is safe to export unchanged.

		Purpose:
			Identify safe model or dictionary keys that contain operational status information
			rather than sensitive label content.

		Args:
			key (str): Dictionary or model key.

		Returns:
			bool: True when the key is safe to export unchanged.
		"""
		try:
			throw_if( 'key', key )
			
			normalized = str( key ).strip( ).lower( )
			return normalized in SAFE_DICT_KEYS or any(
				keyword in normalized for keyword in SAFE_COLUMN_KEYWORDS
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'is_safe_key( self, key: str ) -> bool'
			Logger( ).write( error )
			return False
	
	def is_sensitive_key( self, key: str ) -> bool:
		"""Determine whether a dictionary key should be redacted.

		Purpose:
			Classify nested model or dictionary keys that contain sensitive report content.

		Args:
			key (str): Dictionary or model key.

		Returns:
			bool: True when the key should be redacted.
		"""
		try:
			throw_if( 'key', key )
			
			normalized = str( key ).strip( ).lower( )
			
			if self.is_safe_key( normalized ):
				return False
			
			return normalized in SENSITIVE_DICT_KEYS or any(
				keyword in normalized for keyword in SENSITIVE_COLUMN_KEYWORDS
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'is_sensitive_key( self, key: str ) -> bool'
			Logger( ).write( error )
			return True
	
	def redact_value( self, value: Any ) -> Any:
		"""Redact one scalar value.

		Purpose:
			Replace sensitive scalar content with the standard redaction marker while preserving
			empty and null-like values as empty strings.

		Args:
			value (Any): Value to redact.

		Returns:
			Any: Redacted value.
		"""
		try:
			if value is None:
				return ''
			
			if isinstance( value, float ) and pd.isna( value ):
				return ''
			
			text = str( value )
			
			if not text.strip( ):
				return ''
			
			return REDACTION_TEXT
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'redact_value( self, value: Any ) -> Any'
			Logger( ).write( error )
			return REDACTION_TEXT
	
	def redact_raw_ocr_text( self, raw_text: str ) -> str:
		"""Return raw OCR text or the policy redaction notice.

		Purpose:
			Prevent raw OCR text from appearing in exported or persisted artifacts unless raw OCR
			export is explicitly enabled and no-persistence mode is disabled.

		Args:
			raw_text (str): Raw OCR text.

		Returns:
			str: Raw OCR text when allowed; otherwise, a redaction notice.
		"""
		try:
			if self.can_export_raw_ocr( ):
				return raw_text or ''
			
			return RAW_OCR_REDACTION_NOTICE
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'redact_raw_ocr_text( self, raw_text: str ) -> str'
			Logger( ).write( error )
			return RAW_OCR_REDACTION_NOTICE
	
	def redact_dataframe( self, dataframe: pd.DataFrame ) -> pd.DataFrame:
		"""Return a redacted DataFrame copy.

		Purpose:
			Redact sensitive DataFrame columns while preserving safe operational columns. When
			sensitive value export is explicitly enabled and no-persistence mode is disabled, the
			DataFrame is returned unchanged.

		Args:
			dataframe (pd.DataFrame): Source DataFrame.

		Returns:
			pd.DataFrame: Redacted DataFrame.
		"""
		try:
			throw_if( 'dataframe', dataframe )
			
			if dataframe.empty:
				self._last_redaction_result = RedactionResult(
					redaction_applied=False,
					redacted_fields=[ ],
					message='DataFrame was empty; no redaction was required.'
				)
				return dataframe.copy( )
			
			if self.can_export_sensitive_values( ):
				self._last_redaction_result = RedactionResult(
					redaction_applied=False,
					redacted_fields=[ ],
					message='Sensitive export is enabled; DataFrame was not redacted.'
				)
				return dataframe.copy( )
			
			redacted = dataframe.copy( )
			redacted_fields = [ ]
			
			for column in redacted.columns:
				column_name = str( column )
				
				if self.is_sensitive_column( column_name ):
					redacted[ column ] = redacted[ column ].apply( self.redact_value )
					redacted_fields.append( column_name )
			
			self._last_redaction_result = RedactionResult(
				redaction_applied=bool( redacted_fields ),
				redacted_fields=redacted_fields,
				message=(
						f'Redacted {len( redacted_fields )} sensitive DataFrame field(s).'
						if redacted_fields
						else 'No sensitive DataFrame fields were detected.'
				)
			)
			
			return redacted
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'redact_dataframe( self, dataframe: pd.DataFrame ) -> pd.DataFrame'
			Logger( ).write( error )
			self._last_redaction_result = RedactionResult(
				redaction_applied=True,
				redacted_fields=[ ],
				message='DataFrame redaction failed; returned empty DataFrame.'
			)
			return pd.DataFrame( )
	
	def dataframe_to_csv( self, dataframe: pd.DataFrame ) -> str:
		"""Convert a DataFrame to redacted CSV text.

		Purpose:
			Apply the active retention policy before serializing a DataFrame to CSV. Redacted CSV
			is returned only when evidence export is allowed.

		Args:
			dataframe (pd.DataFrame): Source DataFrame.

		Returns:
			str: Redacted CSV text, or an empty string when export is unavailable.
		"""
		try:
			throw_if( 'dataframe', dataframe )
			
			if dataframe.empty:
				return ''
			
			if not self.can_write_evidence_files( ):
				return ''
			
			return self.redact_dataframe( dataframe ).to_csv( index=False )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'dataframe_to_csv( self, dataframe: pd.DataFrame ) -> str'
			Logger( ).write( error )
			return ''
	
	def dataframe_to_json( self, dataframe: pd.DataFrame ) -> str:
		"""Convert a DataFrame to redacted JSON text.

		Purpose:
			Apply the active retention policy before serializing DataFrame records to JSON.

		Args:
			dataframe (pd.DataFrame): Source DataFrame.

		Returns:
			str: Redacted JSON array text.
		"""
		try:
			throw_if( 'dataframe', dataframe )
			
			if dataframe.empty:
				return '[]'
			
			records = self.redact_dataframe( dataframe ).to_dict( orient='records' )
			return json.dumps( records, indent=2, default=str )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'dataframe_to_json( self, dataframe: pd.DataFrame ) -> str'
			Logger( ).write( error )
			return '[]'
	
	def redact_mapping( self, source: Dict[ str, Any ] ) -> Dict[ str, Any ]:
		"""Return a redacted copy of a dictionary.

		Purpose:
			Redact sensitive keys in nested dictionary structures while preserving operational
			keys. Nested dictionaries and lists are processed recursively.

		Args:
			source (Dict[str, Any]): Source dictionary.

		Returns:
			Dict[str, Any]: Redacted dictionary.
		"""
		try:
			throw_if( 'source', source )
			
			if self.can_export_sensitive_values( ):
				return dict( source )
			
			redacted: Dict[ str, Any ] = { }
			
			for key, value in source.items( ):
				key_text = str( key )
				
				if self.is_sensitive_key( key_text ):
					redacted[ key_text ] = self.redact_value( value )
				else:
					redacted[ key_text ] = self.redact_object( value )
			
			return redacted
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'redact_mapping( self, source: Dict[str, Any] ) -> Dict[str, Any]'
			Logger( ).write( error )
			return { }
	
	def redact_sequence( self, source: Iterable[ Any ] ) -> List[ Any ]:
		"""Return a redacted copy of a sequence.

		Purpose:
			Apply object redaction to each item in a sequence.

		Args:
			source (Iterable[Any]): Source sequence.

		Returns:
			List[Any]: Redacted list.
		"""
		try:
			throw_if( 'source', source )
			
			return [
					self.redact_object( item )
					for item in source
			]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'redact_sequence( self, source: Iterable[Any] ) -> List[Any]'
			Logger( ).write( error )
			return [ ]
	
	def redact_object( self, value: Any ) -> Any:
		"""Redact an arbitrary report-like object.

		Purpose:
			Convert Pydantic models, dictionaries, lists, tuples, paths, and scalar values into
			redacted JSON-compatible structures. This method is used by report writers and
			acceptance package generators to avoid storing sensitive extracted/application data.

		Args:
			value (Any): Source object.

		Returns:
			Any: Redacted object.
		"""
		try:
			if value is None:
				return None
			
			if isinstance( value, Path ):
				return str( value ) if self.can_export_file_paths( ) else REDACTION_TEXT
			
			if isinstance( value, pd.DataFrame ):
				return self.redact_dataframe( value ).to_dict( orient='records' )
			
			if hasattr( value, 'model_dump' ):
				return self.redact_mapping( value.model_dump( ) )
			
			if isinstance( value, dict ):
				return self.redact_mapping( value )
			
			if isinstance( value, list ) or isinstance( value, tuple ) or isinstance( value, set ):
				return self.redact_sequence( value )
			
			return value
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'redact_object( self, value: Any ) -> Any'
			Logger( ).write( error )
			return REDACTION_TEXT
	
	def object_to_json( self, value: Any ) -> str:
		"""Serialize an object as redacted JSON.

		Purpose:
			Apply redaction to a report-like object and serialize it as formatted JSON.

		Args:
			value (Any): Source object.

		Returns:
			str: Redacted JSON text.
		"""
		try:
			throw_if( 'value', value )
			
			payload = self.redact_object( value )
			return json.dumps( payload, indent=2, default=str )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'object_to_json( self, value: Any ) -> str'
			Logger( ).write( error )
			return '{}'
	
	def write_text_file( self, text: str, output_path: str | Path ) -> Path:
		"""Write redacted evidence text when policy permits.

		Purpose:
			Write text to disk only when evidence-file output is allowed. The caller is expected
			to provide already-redacted text. This method centralizes the final write/no-write
			decision.

		Args:
			text (str): Text content to write.
			output_path (str | Path): Destination path.

		Returns:
			Path: Destination path, whether or not content was written.
		"""
		try:
			throw_if( 'output_path', output_path )
			
			path = Path( output_path )
			
			if not self.can_write_evidence_files( ):
				return path
			
			path.parent.mkdir( parents=True, exist_ok=True )
			path.write_text( text or '', encoding='utf-8' )
			
			return path
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'write_text_file( self, *args ) -> Path'
			Logger( ).write( error )
			return Path( output_path )
	
	def write_dataframe_csv( self, dataframe: pd.DataFrame, output_path: str | Path ) -> Path:
		"""Write a DataFrame as redacted CSV when policy permits.

		Purpose:
			Redact a DataFrame and write it as CSV only when redacted evidence output is allowed.

		Args:
			dataframe (pd.DataFrame): Source DataFrame.
			output_path (str | Path): Destination CSV path.

		Returns:
			Path: Destination path, whether or not content was written.
		"""
		try:
			throw_if( 'dataframe', dataframe )
			throw_if( 'output_path', output_path )
			
			path = Path( output_path )
			
			if not self.can_write_evidence_files( ):
				return path
			
			path.parent.mkdir( parents=True, exist_ok=True )
			path.write_text( self.dataframe_to_csv( dataframe ), encoding='utf-8' )
			
			return path
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'write_dataframe_csv( self, *args ) -> Path'
			Logger( ).write( error )
			return Path( output_path )
	
	def to_acceptance_evidence( self ) -> Dict[ str, object ]:
		"""Return data-retention evidence flags for acceptance evaluation.

		Purpose:
			Convert the active retention policy into a dictionary that can be merged into
			acceptance-checker evidence.

		Returns:
			Dict[str, object]: Acceptance evidence values.
		"""
		try:
			return {
					'NO_PERSISTENCE_MODE': self._settings.no_persistence_mode,
					'LONG_TERM_STORAGE_DISABLED': self._settings.long_term_storage_disabled,
					'ENABLE_UPLOAD_PERSISTENCE': self._settings.upload_persistence_enabled,
					'ENABLE_RAW_TEXT_LOGGING': self._settings.raw_text_logging_enabled,
					'ENABLE_RAW_OCR_EXPORT': self._settings.raw_ocr_export_enabled,
					'ENABLE_EXTRACTED_DATA_EXPORT': self._settings.extracted_data_export_enabled,
					'ENABLE_REDACTED_EVIDENCE_EXPORT':
						self._settings.redacted_evidence_export_enabled,
					'ENABLE_FILE_PATH_EXPORT': self._settings.file_path_export_enabled
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_acceptance_evidence( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'NO_PERSISTENCE_MODE': True,
					'LONG_TERM_STORAGE_DISABLED': True,
					'ENABLE_UPLOAD_PERSISTENCE': False,
					'ENABLE_RAW_TEXT_LOGGING': False,
					'ENABLE_RAW_OCR_EXPORT': False,
					'ENABLE_EXTRACTED_DATA_EXPORT': False,
					'ENABLE_REDACTED_EVIDENCE_EXPORT': True,
					'ENABLE_FILE_PATH_EXPORT': False
			}
	
	def to_dataframe( self ) -> pd.DataFrame:
		"""Return active retention settings as a DataFrame.

		Purpose:
			Create a one-row DataFrame representing the active data-retention settings.

		Returns:
			pd.DataFrame: One-row data-retention settings DataFrame.
		"""
		try:
			return pd.DataFrame( [ self._settings.to_record( ) ] )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_dataframe( self ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def to_json( self ) -> str:
		"""Return active retention settings as formatted JSON.

		Purpose:
			Serialize active data-retention settings for diagnostics, acceptance evidence, or
			reporting.

		Returns:
			str: Formatted JSON text.
		"""
		try:
			return json.dumps( self._settings.to_record( ), indent=2, default=str )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_json( self ) -> str'
			Logger( ).write( error )
			return '{}'