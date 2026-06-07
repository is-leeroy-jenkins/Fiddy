''' ******************************************************************************************
    <summary>
        Provides the UI and workflow controller for Fiddy.

        This module initializes reviewer session state, configures the page, manages manifest
        and artwork uploads, synchronizes CAV form values, runs manifest-driven and manual
        verification workflows, displays readiness checks, accessibility guidance, dashboards, side-by-side comparison
        tables, OCR diagnostics, result details, and report downloads.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import base64
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

import config as cfg
from booger import Error, Logger
from src.batch_manifest import BatchManifest, BatchManifestRecord
from src.batch_processor import BatchProcessingResult, BatchProcessor
from src.constants import (
	APP_DISPLAY_NAME,
	BEVERAGE_TYPE_DISTILLED_SPIRITS,
	BEVERAGE_TYPES,
	GOVERNMENT_WARNING_TEXT,
	STATUS_FAIL,
	STATUS_PASS,
	STATUS_REVIEW,
	STATUS_WARNING,
	SUPPORTED_UPLOAD_TYPES
)
from src.data_retention import DataRetentionPolicy
from src.label_verifier import AlcoholLabelVerifier
from src.models import BatchVerificationReport, LabelApplication, LabelVerificationReport
from src.report_writer import ReportWriter
from src.synthetic_data_generator import SyntheticDataGenerator

# ==========================================================================================
# Session State
# ==========================================================================================

def initialize_session_state( ) -> None:
	"""Initialize all Streamlit session-state keys used by the application.

	Purpose:
		Prepare batch results, report objects, display DataFrames, manifest state, generated report
		text, verification flags, selected report index, reviewer mode, accessibility options,
		keyboard guidance state, and CAV form fields before widgets or display functions read those
		keys. The function is idempotent and preserves existing state across Streamlit reruns.

	Returns:
		None.
	"""
	if 'batch_result' not in st.session_state:
		st.session_state[ 'batch_result' ] = BatchProcessingResult( )
		
	if 'app_reset_token' not in st.session_state:
		st.session_state[ 'app_reset_token' ] = 0
		
	if 'batch_report' not in st.session_state:
		st.session_state[ 'batch_report' ] = BatchVerificationReport( )
	
	if 'summary_dataframe' not in st.session_state:
		st.session_state[ 'summary_dataframe' ] = pd.DataFrame( )
	
	if 'detail_dataframe' not in st.session_state:
		st.session_state[ 'detail_dataframe' ] = pd.DataFrame( )
	
	if 'comparison_dataframe' not in st.session_state:
		st.session_state[ 'comparison_dataframe' ] = pd.DataFrame( )
	
	if 'performance_dataframe' not in st.session_state:
		st.session_state[ 'performance_dataframe' ] = pd.DataFrame( )
	
	if 'manifest_dataframe' not in st.session_state:
		st.session_state[ 'manifest_dataframe' ] = pd.DataFrame( )
	
	if 'manifest_records' not in st.session_state:
		st.session_state[ 'manifest_records' ] = [ ]
	
	if 'manifest_loaded' not in st.session_state:
		st.session_state[ 'manifest_loaded' ] = False
	
	if 'manifest_signature' not in st.session_state:
		st.session_state[ 'manifest_signature' ] = ''
	
	if 'manifest_file_name' not in st.session_state:
		st.session_state[ 'manifest_file_name' ] = ''
	
	if 'current_manifest_record_index' not in st.session_state:
		st.session_state[ 'current_manifest_record_index' ] = 0
	
	if 'json_report' not in st.session_state:
		st.session_state[ 'json_report' ] = '{}'
	
	if 'markdown_report' not in st.session_state:
		st.session_state[ 'markdown_report' ] = ''
	
	if 'verification_complete' not in st.session_state:
		st.session_state[ 'verification_complete' ] = False
	
	if 'selected_report_index' not in st.session_state:
		st.session_state[ 'selected_report_index' ] = 0
	
	if 'simple_mode' not in st.session_state:
		st.session_state[ 'simple_mode' ] = bool( getattr( cfg, 'DEFAULT_SIMPLE_MODE', True ) )
	
	if 'high_contrast_mode' not in st.session_state:
		st.session_state[ 'high_contrast_mode' ] = bool(
			getattr( cfg, 'DEFAULT_HIGH_CONTRAST_MODE', False ) )
	
	if 'large_text_mode' not in st.session_state:
		st.session_state[ 'large_text_mode' ] = bool(
			getattr( cfg, 'DEFAULT_LARGE_TEXT_MODE', False ) )
	
	if 'show_keyboard_notes' not in st.session_state:
		st.session_state[ 'show_keyboard_notes' ] = bool(
			getattr( cfg, 'SHOW_KEYBOARD_ACCESSIBILITY_NOTES', True ) )
	
	if 'processing_status_message' not in st.session_state:
		st.session_state[ 'processing_status_message' ] = ''
	
	if 'processing_status_history' not in st.session_state:
		st.session_state[ 'processing_status_history' ] = [ ]
	
	initialize_cav_form_state( )

def reset_application_state( ) -> None:
	"""Reset the Streamlit application back to its initial reviewer state.

	Purpose:
		Clear all Streamlit session-state values used by Fiddy, increment the upload-widget reset
		token, reinitialize default state, and allow the application to rerender as if it had just
		started. The reset token is used by file uploader keys so uploaded manifest and artwork
		widgets are cleared on rerun.

	Returns:
		None.
	"""
	try:
		current_token = int( st.session_state.get( 'app_reset_token', 0 ) )
		next_token = current_token + 1
		
		for key in list( st.session_state.keys( ) ):
			del st.session_state[ key ]
		
		st.session_state[ 'app_reset_token' ] = next_token
		initialize_session_state( )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'reset_application_state( ) -> None'
		Logger( ).write( error )
		st.warning( f'Application reset failed: {e}' )
		
def clear_results( ) -> None:
	"""Clear prior verification outputs while preserving current input widget values.

	Purpose:
		This function resets generated verification outputs, report objects, display DataFrames,
		download text, completion state, and selected report index. It intentionally does not clear
		uploaded file widgets, manifest state, reviewer mode, accessibility settings, or CAV form
		values because those are input-side state rather than generated result state.

	Returns:
		None.
	"""
	st.session_state[ 'batch_result' ] = BatchProcessingResult( )
	st.session_state[ 'batch_report' ] = BatchVerificationReport( )
	st.session_state[ 'summary_dataframe' ] = pd.DataFrame( )
	st.session_state[ 'detail_dataframe' ] = pd.DataFrame( )
	st.session_state[ 'comparison_dataframe' ] = pd.DataFrame( )
	st.session_state[ 'performance_dataframe' ] = pd.DataFrame( )
	st.session_state[ 'json_report' ] = '{}'
	st.session_state[ 'markdown_report' ] = ''
	st.session_state[ 'verification_complete' ] = False
	st.session_state[ 'selected_report_index' ] = 0

# ==========================================================================================
# CAV Manifest State
# ==========================================================================================

def get_cav_form_defaults( ) -> Dict[ str, Any ]:
	"""Return default session-state values for the CAV application form.

	Purpose:
		The defaults provide stable initial values for manual CAV review and for clearing the form
		when a manifest is unloaded. The government warning defaults to the configured standard
		warning text so reviewers have an expected warning value available unless a manifest record
		or manual edit overrides it.

	Returns:
		Dict[str, Any]: Default CAV form values keyed by Streamlit session-state key.
	"""
	return {
			'cav_file_name': '',
			'cav_brand_name': '',
			'cav_class_type': '',
			'cav_beverage_type': BEVERAGE_TYPE_DISTILLED_SPIRITS,
			'cav_abv': '',
			'cav_proof': '',
			'cav_net_contents': '',
			'cav_producer_bottler': '',
			'cav_imported': False,
			'cav_importer': '',
			'cav_country_of_origin': '',
			'cav_government_warning': GOVERNMENT_WARNING_TEXT,
			'cav_cola_id': '',
			'cav_notes': ''
	}

def initialize_cav_form_state( ) -> None:
	"""Initialize CAV application data form keys before widgets are rendered.

	Purpose:
		This function adds missing CAV form keys to Streamlit session state while preserving any
		existing values. It supports both manual review and manifest-loaded workflows by ensuring
		the form can be read safely by processing readiness checks and application model creation.

	Returns:
		None.
	"""
	defaults = get_cav_form_defaults( )
	
	for key, value in defaults.items( ):
		if key not in st.session_state:
			st.session_state[ key ] = value

def clear_cav_form_state( ) -> None:
	"""Reset all CAV application form fields to their default values.

	Purpose:
		This function is used when the manifest CSV is unloaded or when manifest state is cleared.
		It restores the CAV fields to the same baseline created during session initialization.

	Returns:
		None.
	"""
	defaults = get_cav_form_defaults( )
	
	for key, value in defaults.items( ):
		st.session_state[ key ] = value

def clear_manifest_state( ) -> None:
	"""Clear manifest records, manifest navigation state, and loaded CAV values.

	Purpose:
		This function resets the manifest DataFrame, parsed manifest records, loaded flag,
		manifest signature, manifest file name, current record pointer, and CAV form values. It is
		called when the user removes an uploaded manifest so stale manifest data cannot remain in
		the reviewer workflow.

	Returns:
		None.
	"""
	st.session_state[ 'manifest_dataframe' ] = pd.DataFrame( )
	st.session_state[ 'manifest_records' ] = [ ]
	st.session_state[ 'manifest_loaded' ] = False
	st.session_state[ 'manifest_signature' ] = ''
	st.session_state[ 'manifest_file_name' ] = ''
	st.session_state[ 'current_manifest_record_index' ] = 0
	
	clear_cav_form_state( )

def parse_optional_float( value: object ) -> float | None:
	"""Parse optional numeric input into a float value.

	Purpose:
		This helper accepts blank, text, percentage-style, or numeric values from Streamlit widgets
		and manifest-derived form state. Empty values and invalid numeric text are treated as
		unavailable rather than as errors because the surrounding workflow may still be able to
		display readiness guidance or collect additional reviewer input.

	Args:
		value (object): Text, numeric, or empty value to parse.

	Returns:
		float | None: Parsed float value, or ``None`` when the value is empty, missing, invalid,
		or cannot be parsed.
	"""
	try:
		if value is None:
			return None
		
		text = str( value ).replace( '%', '' ).strip( )
		
		if not text:
			return None
		
		return float( text )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'parse_optional_float( value: object ) -> float | None'
		Logger( ).write( error )
		return None

def get_manifest_upload_signature( uploaded_manifest: object ) -> str:
	"""Create a stable signature for the uploaded manifest file.

	Purpose:
		The signature combines the uploaded file name and size. It is used to detect whether the
		current uploaded manifest is the same file already parsed into session state, avoiding
		unnecessary reprocessing on Streamlit reruns.

	Args:
		uploaded_manifest (object): Streamlit uploaded manifest object.

	Returns:
		str: Manifest upload signature in ``name:size`` form, or an empty string when the
		signature cannot be created.
	"""
	try:
		cfg.throw_if( 'uploaded_manifest', uploaded_manifest )
		
		file_name = getattr( uploaded_manifest, 'name', '' )
		file_size = getattr( uploaded_manifest, 'size', 0 )
		
		return f'{file_name}:{file_size}'
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_manifest_upload_signature( uploaded_manifest: object ) -> str'
		Logger( ).write( error )
		return ''

def read_manifest_upload_dataframe( uploaded_manifest: object ) -> pd.DataFrame:
	"""Read an uploaded manifest CSV using common encoding fallbacks.

	Purpose:
		This function reads the uploaded manifest bytes and attempts CSV parsing using common
		encodings in a stable order. The uploaded file pointer is reset when the upload object
		supports ``seek`` so the same upload can be reused by other workflow steps.

	Args:
		uploaded_manifest (object): Streamlit uploaded manifest object.

	Returns:
		pd.DataFrame: Parsed manifest DataFrame. If parsing fails, an empty DataFrame is
		returned.
	"""
	try:
		cfg.throw_if( 'uploaded_manifest', uploaded_manifest )
		
		file_bytes = bytes( uploaded_manifest.getbuffer( ) )
		encodings = [ 'utf-8-sig', 'utf-8', 'cp1252', 'latin1' ]
		
		for encoding in encodings:
			try:
				df_manifest = pd.read_csv( BytesIO( file_bytes ), encoding=encoding )
				
				if hasattr( uploaded_manifest, 'seek' ):
					uploaded_manifest.seek( 0 )
				
				return df_manifest
			except UnicodeDecodeError:
				continue
		
		df_manifest = pd.read_csv( BytesIO( file_bytes ), encoding='latin1',
			encoding_errors='replace' )
		
		if hasattr( uploaded_manifest, 'seek' ):
			uploaded_manifest.seek( 0 )
		
		return df_manifest
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'read_manifest_upload_dataframe( uploaded_manifest: object ) -> pd.DataFrame'
		Logger( ).write( error )
		return pd.DataFrame( )

def get_manifest_records_from_dataframe( df_manifest: pd.DataFrame ) -> List[ Any ]:
	"""Convert an uploaded manifest DataFrame into navigable manifest records.

	Purpose:
		This function normalizes manifest columns through ``BatchManifest`` and converts the
		normalized rows into manifest record objects. It is used by the upload synchronization
		workflow so CAV values can be navigated and applied to the form.

	Args:
		df_manifest (pd.DataFrame): Uploaded manifest DataFrame.

	Returns:
		List[Any]: Parsed manifest records, or an empty list when the DataFrame is empty or
		conversion fails.
	"""
	try:
		if df_manifest is None or df_manifest.empty:
			return [ ]
		
		manifest = BatchManifest( )
		df_normalized = manifest.normalize_columns( df_manifest )
		return manifest.dataframe_to_records( df_normalized )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_manifest_records_from_dataframe( df_manifest: pd.DataFrame ) -> List[Any]'
		Logger( ).write( error )
		return [ ]

def get_record_value( record: object, field_name: str, default: object = '' ) -> object:
	"""Read a field value from a manifest record using attribute access.

	Purpose:
		This helper centralizes safe manifest-record field access. It returns the caller-supplied
		default when the record is missing, the field name is missing, the attribute is unavailable,
		or lookup fails.

	Args:
		record (object): Manifest record.
		field_name (str): Field name to read.
		default (object): Default value returned when the field is unavailable.

	Returns:
		object: Field value or default value.
	"""
	try:
		cfg.throw_if( 'record', record )
		cfg.throw_if( 'field_name', field_name )
		
		return getattr( record, field_name, default )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_record_value( record: object, field_name: str, default: object ) -> object'
		Logger( ).write( error )
		return default

def apply_manifest_record_to_form_state( record: object ) -> None:
	"""Write one manifest record into the CAV form session-state fields.

	Purpose:
		This function maps canonical manifest-record attributes into the Streamlit session-state keys
		used by the CAV form. Numeric ABV and proof values are converted to display strings when
		available, while missing values are represented as blank text. The function mutates session
		state only and returns no value.

	Args:
		record (object): Manifest record to display in the CAV form.

	Returns:
		None.
	"""
	try:
		cfg.throw_if( 'record', record )
		
		alcohol_content = get_record_value( record, 'alcohol_content', None )
		proof = get_record_value( record, 'proof', None )
		
		st.session_state[ 'cav_file_name' ] = str( get_record_value( record, 'file_name', '' ) )
		st.session_state[ 'cav_brand_name' ] = str( get_record_value( record, 'brand_name', '' ) )
		st.session_state[ 'cav_class_type' ] = str( get_record_value( record, 'class_type', '' ) )
		st.session_state[ 'cav_beverage_type' ] = str(
			get_record_value( record, 'beverage_type', BEVERAGE_TYPE_DISTILLED_SPIRITS ) )
		st.session_state[ 'cav_abv' ] = '' if alcohol_content is None else str( alcohol_content )
		st.session_state[ 'cav_proof' ] = '' if proof is None else str( proof )
		st.session_state[ 'cav_net_contents' ] = str(
			get_record_value( record, 'net_contents', '' ) )
		st.session_state[ 'cav_producer_bottler' ] = str(
			get_record_value( record, 'producer_bottler', '' ) )
		st.session_state[ 'cav_imported' ] = bool(
			get_record_value( record, 'imported', False ) )
		st.session_state[ 'cav_importer' ] = str( get_record_value( record, 'importer', '' ) )
		st.session_state[ 'cav_country_of_origin' ] = str(
			get_record_value( record, 'country_of_origin', '' ) )
		st.session_state[ 'cav_government_warning' ] = str(
			get_record_value( record, 'government_warning', GOVERNMENT_WARNING_TEXT ) )
		st.session_state[ 'cav_cola_id' ] = str( get_record_value( record, 'cola_id', '' ) )
		st.session_state[ 'cav_notes' ] = str( get_record_value( record, 'notes', '' ) )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'apply_manifest_record_to_form_state( record: object ) -> None'
		Logger( ).write( error )
		return None

def get_current_manifest_record( ) -> object | None:
	"""Return the currently selected manifest record.

	Purpose:
		This function reads the manifest records and current record index from session state,
		clamps the index to the valid record range, updates session state with the clamped index,
		and returns the active manifest record.

	Returns:
		object | None: Current manifest record, or ``None`` when no record is available.
	"""
	try:
		records = st.session_state.get( 'manifest_records', [ ] )
		
		if not records:
			return None
		
		index = int( st.session_state.get( 'current_manifest_record_index', 0 ) )
		index = max( 0, min( index, len( records ) - 1 ) )
		st.session_state[ 'current_manifest_record_index' ] = index
		
		return records[ index ]
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_current_manifest_record( ) -> object | None'
		Logger( ).write( error )
		return None

def load_current_manifest_record( ) -> None:
	"""Load the current manifest record into the CAV form fields.

	Purpose:
		This function retrieves the currently selected manifest record and applies it to the CAV form
		state when available. It is used by the manifest navigation reload control.

	Returns:
		None.
	"""
	try:
		record = get_current_manifest_record( )
		
		if record:
			apply_manifest_record_to_form_state( record )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'load_current_manifest_record( ) -> None'
		Logger( ).write( error )
		return None

def move_manifest_record( step: int ) -> None:
	"""Move the active manifest record pointer and load the selected record.

	Purpose:
		This function increments or decrements the manifest record index by the supplied step,
		clamps the result to the valid record range, stores the updated index in session state, and
		applies the selected record to the CAV form.

	Args:
		step (int): Relative movement amount, typically ``-1`` or ``1``.

	Returns:
		None.
	"""
	try:
		records = st.session_state.get( 'manifest_records', [ ] )
		
		if not records:
			return None
		
		index = int( st.session_state.get( 'current_manifest_record_index', 0 ) )
		index = max( 0, min( index + step, len( records ) - 1 ) )
		st.session_state[ 'current_manifest_record_index' ] = index
		
		apply_manifest_record_to_form_state( records[ index ] )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'move_manifest_record( step: int ) -> None'
		Logger( ).write( error )
		return None

def sync_manifest_upload_state( uploaded_manifest: object ) -> None:
	"""Synchronize manifest upload state with parsed records and CAV form values.

	Purpose:
		This function initializes CAV state, clears manifest state when the upload is removed,
		avoids reprocessing when the uploaded file signature has not changed, parses a new manifest
		upload into a DataFrame and manifest records, stores the manifest state, and loads the first
		record into the CAV form when records are available.

	Args:
		uploaded_manifest (object): Streamlit uploaded manifest file.

	Returns:
		None.
	"""
	try:
		initialize_cav_form_state( )
		
		if not uploaded_manifest:
			if st.session_state.get( 'manifest_loaded', False ):
				clear_manifest_state( )
			
			return None
		
		signature = get_manifest_upload_signature( uploaded_manifest )
		current_signature = st.session_state.get( 'manifest_signature', '' )
		
		if signature == current_signature and st.session_state.get( 'manifest_loaded', False ):
			return None
		
		df_manifest = read_manifest_upload_dataframe( uploaded_manifest )
		records = get_manifest_records_from_dataframe( df_manifest )
		
		st.session_state[ 'manifest_dataframe' ] = df_manifest
		st.session_state[ 'manifest_records' ] = records
		st.session_state[ 'manifest_loaded' ] = True
		st.session_state[ 'manifest_signature' ] = signature
		st.session_state[ 'manifest_file_name' ] = getattr( uploaded_manifest, 'name', '' )
		st.session_state[ 'current_manifest_record_index' ] = 0
		
		if records:
			apply_manifest_record_to_form_state( records[ 0 ] )
		else:
			clear_cav_form_state( )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'sync_manifest_upload_state( uploaded_manifest: object ) -> None'
		Logger( ).write( error )
		clear_manifest_state( )

def display_manifest_record_navigation( key_prefix: str = 'cav_form' ) -> None:
	"""Display controls for navigating parsed manifest records.

	Purpose:
		This function renders Previous, Next, and Reload buttons when manifest records are loaded.
		The controls update the current manifest record index and reload the selected record into
		the CAV form.

	Args:
		key_prefix (str): Unique Streamlit key prefix for navigation buttons.

	Returns:
		None.
	"""
	records = st.session_state.get( 'manifest_records', [ ] )
	
	if not records:
		return
	
	current_index = int( st.session_state.get( 'current_manifest_record_index', 0 ) )
	total_records = len( records )
	
	st.caption( f'CAV manifest record {current_index + 1} of {total_records}' )
	
	previous_column, next_column, reload_column = st.columns( [ 0.30, 0.30, 0.40 ] )
	
	with previous_column:
		st.button(
			'Previous Record',
			key=f'{key_prefix}_previous_record_button',
			disabled=current_index <= 0,
			use_container_width=True,
			on_click=move_manifest_record,
			args=(-1,)
		)
	
	with next_column:
		st.button(
			'Next Record',
			key=f'{key_prefix}_next_record_button',
			disabled=current_index >= total_records - 1,
			use_container_width=True,
			on_click=move_manifest_record,
			args=(1,)
		)
	
	with reload_column:
		st.button(
			'Reload Current Record',
			key=f'{key_prefix}_reload_current_record_button',
			use_container_width=True,
			on_click=load_current_manifest_record
		)

# ==========================================================================================
# Page Configuration
# ==========================================================================================

def get_configured_image_path( value: object ) -> str:
	"""Return a display-safe image path from a configured path value.

	Purpose:
		This function supports absolute and relative image paths from configuration. Relative paths
		are checked against the current working directory, project root, current file directory, and
		parent directory so the app can locate branding assets across typical Streamlit launch
		contexts.

	Args:
		value (object): Configured image path value.

	Returns:
		str: Existing image path, or an empty string when no display-safe path is available.
	"""
	try:
		if value is None:
			return ''
		
		raw_value = str( value ).strip( )
		
		if not raw_value:
			return ''
		
		image_path = Path( raw_value )
		
		if image_path.is_absolute( ) and image_path.exists( ):
			return str( image_path )
		
		candidate_paths = [
				Path.cwd( ) / image_path,
				cfg.ROOT_DIR / image_path,
				Path( __file__ ).resolve( ).parent / image_path,
				Path( __file__ ).resolve( ).parent.parent / image_path
		]
		
		for candidate_path in candidate_paths:
			if candidate_path.exists( ):
				return str( candidate_path.resolve( ) )
		
		return ''
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_configured_image_path( value: object ) -> str'
		Logger( ).write( error )
		return ''

def get_accessibility_css( ) -> str:
	"""Return accessibility CSS overrides based on current reviewer settings.

	Purpose:
		Build the base accessibility layer for keyboard navigation, visible focus, high contrast,
		large text, large touch targets, readable disabled states, and table readability. The CSS is
		generated from session-state flags so Simple and Advanced workflows share the same
		accessibility behavior.

	Returns:
		str: CSS override block, or an empty string when CSS generation fails.
	"""
	try:
		large_text = bool( st.session_state.get( 'large_text_mode', False ) )
		high_contrast = bool( st.session_state.get( 'high_contrast_mode', False ) )
		minimum_target = int( getattr( cfg, 'MINIMUM_TOUCH_TARGET_PX', 44 ) )
		large_text_css = ''
		high_contrast_css = ''
		
		base_accessibility_css = f"""
		button,
		div.stButton > button,
		div.stDownloadButton > button,
		div[data-testid="stFileUploader"] button,
		input,
		textarea,
		select,
		div[data-baseweb="select"] > div,
		div[role="button"] {{
			min-height: {minimum_target}px !important;
		}}

		button:focus,
		button:focus-visible,
		input:focus,
		input:focus-visible,
		textarea:focus,
		textarea:focus-visible,
		div[role="button"]:focus,
		div[role="button"]:focus-visible,
		div[data-baseweb="select"]:focus-within,
		div[data-testid="stFileUploader"] section:focus-within {{
			outline: 3px solid #00A3FF !important;
			outline-offset: 3px !important;
			box-shadow: 0 0 0 3px rgba(0, 163, 255, 0.25) !important;
		}}

		button:disabled,
		button[disabled],
		div.stButton > button:disabled,
		div.stDownloadButton > button:disabled {{
			opacity: 0.70 !important;
			cursor: not-allowed !important;
		}}

		.fiddy-keyboard-note {{
			border: 1px solid #007AFC;
			border-radius: 0.75rem;
			padding: 0.85rem 1.0rem;
			background: rgba(0, 122, 252, 0.12);
			color: #EAF3FF;
			font-size: 0.96rem;
			line-height: 1.45;
			margin-bottom: 1.0rem;
		}}

		.fiddy-primary-action button {{
			font-size: 1.08rem !important;
			font-weight: 800 !important;
		}}

		div[data-testid="stDataFrame"] div[role="gridcell"],
		div[data-testid="stDataEditor"] div[role="gridcell"] {{
			line-height: 1.35 !important;
		}}
		"""
		
		if large_text:
			large_text_css = """
			html, body, [class*="css"] {
				font-size: 18px !important;
			}

			div.stButton > button,
			div.stDownloadButton > button {
				min-height: 3.15rem !important;
				font-size: 1.05rem !important;
			}

			div[data-testid="stTextInput"] input,
			div[data-testid="stNumberInput"] input,
			textarea,
			div[data-baseweb="select"] > div {
				font-size: 1.05rem !important;
				min-height: 3.00rem !important;
			}

			.fiddy-title {
				font-size: 2.20rem !important;
			}

			.fiddy-panel-title {
				font-size: 1.30rem !important;
			}

			.fiddy-panel-text,
			.fiddy-keyboard-note {
				font-size: 1.08rem !important;
			}
			"""
		
		if high_contrast:
			high_contrast_css = """
			section[data-testid="stSidebar"] {
				background: #000000 !important;
				border-right: 2px solid #FFFFFF !important;
			}

			.block-container {
				background: #000000 !important;
			}

			.fiddy-header,
			.fiddy-panel,
			.fiddy-keyboard-note {
				background: #000000 !important;
				border: 2px solid #FFFFFF !important;
			}

			.fiddy-title,
			.fiddy-panel-title,
			label,
			p,
			span,
			div,
			.fiddy-keyboard-note {
				color: #FFFFFF !important;
			}

			.fiddy-eyebrow {
				color: #00A3FF !important;
			}

			.fiddy-subtitle,
			.fiddy-panel-text {
				color: #FFFFFF !important;
			}

			div.stButton > button,
			div.stDownloadButton > button {
				background: #000000 !important;
				border: 2px solid #FFFFFF !important;
				color: #FFFFFF !important;
			}

			div.stButton > button:hover,
			div.stDownloadButton > button:hover,
			div.stButton > button:focus,
			div.stDownloadButton > button:focus {
				background: #003B73 !important;
				border: 2px solid #00A3FF !important;
				color: #FFFFFF !important;
			}

			div[data-testid="stTextInput"] input,
			div[data-testid="stNumberInput"] input,
			textarea,
			div[data-baseweb="select"] > div {
				background-color: #000000 !important;
				border: 2px solid #FFFFFF !important;
				color: #FFFFFF !important;
			}
			"""
		
		return f"""
		<style>
			{base_accessibility_css}
			{large_text_css}
			{high_contrast_css}
		</style>
		"""
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_accessibility_css( ) -> str'
		Logger( ).write( error )
		return ''

def configure_page( ) -> None:
	"""Configure the Streamlit page and inject base application styling.

	Purpose:
		This function resolves the configured favicon path, sets Streamlit page metadata, injects
		the primary Fiddy CSS theme, and applies accessibility-specific CSS overrides. The styling
		controls layout width, sidebar appearance, upload controls, buttons, panels, status text,
		and metric cards.

	Returns:
		None.
	"""
	favicon_path = get_configured_image_path( getattr( cfg, 'FAVICON', '' ) )
	page_icon = favicon_path if favicon_path else getattr( cfg, 'APP_ICON', '' )
	
	st.set_page_config( page_title=cfg.APP_TITLE, page_icon=page_icon,
		layout='wide', initial_sidebar_state='expanded' )
	
	st.markdown(
		"""
		<style>
			.block-container {
				padding-top: 1.8rem;
				padding-bottom: 2.0rem;
				max-width: 1320px;
			}

			section[data-testid="stSidebar"] {
				background: #282829;
				border-right: 1px solid #49A0FC;
			}

			section[data-testid="stSidebar"] img {
				max-width: 190px;
				margin: 0 auto 1.0rem auto;
				display: block;
			}

			div[data-testid="stSidebarContent"] {
				padding-top: 1.2rem;
			}

			div[data-testid="stTextInput"] input,
			div[data-testid="stNumberInput"] input,
			textarea,
			div[data-baseweb="select"] > div {
				border-radius: 0.55rem !important;
				border: 1px solid #007AFC !important;
				background-color: #5C5C5C !important;
			}

			div[data-testid="stFileUploader"] section {
				border-radius: 0.85rem;
				border: 1px dashed #656569;
				background: linear-gradient(180deg, #202022 0%, #18181A 100%);
				padding: 1.1rem;
			}

			div.stButton > button {
				border-radius: 0.55rem;
				border: 1px solid #007AFC;
				background: linear-gradient(180deg, #141414 0%, #292929 100%);
				color: #FFFFFF;
				font-weight: 700;
				min-height: 2.65rem;
			}

			div.stButton > button:hover {
				border: 1px solid #007AFC;
				background: linear-gradient(180deg, #292929 0%, #023B78 100%);
				color: #FFFFFF;
			}

			div.stDownloadButton > button {
				border-radius: 0.55rem;
				border: 1px solid #3A3A3D;
				background: #292929;
				color: #F5F5F5;
				font-weight: 650;
				min-height: 2.5rem;
			}

			div.stDownloadButton > button:hover {
				border: 1px solid #023B78;
				color: #FFFFFF;
			}

			.fiddy-header {
				border-bottom: 1px solid #2A2A2D;
				margin-bottom: 1.1rem;
				padding-bottom: 0.85rem;
			}

			.fiddy-eyebrow {
				color: #B3B3B3;
				font-size: 0.74rem;
				font-weight: 800;
				letter-spacing: 0.15rem;
				text-transform: uppercase;
				margin-bottom: 0.25rem;
				line-height: 1.4;
			}

			.fiddy-title {
				font-size: 1.85rem;
				line-height: 1.25;
				font-weight: 850;
				color: #007AFC;
				margin-bottom: 0.30rem;
			}

			.fiddy-subtitle {
				font-size: 0.96rem;
				color: #B3B3B3;
				line-height: 1.45;
				max-width: 1000px;
			}

			.fiddy-panel {
				border: 1px solid #343437;
				border-radius: 0.85rem;
				background: linear-gradient(180deg, #141414 0%, #282828 100%);
				padding: 1.05rem 1.10rem;
				margin-bottom: 1.0rem;
			}

			.fiddy-panel-title {
				color: #F5F5F5;
				font-size: 1.08rem;
				font-weight: 800;
				margin-bottom: 0.30rem;
			}

			.fiddy-panel-text {
				color: #C8C8C8;
				font-size: 0.93rem;
				line-height: 1.50;
			}

			.status-pass {
				color: #75D68C;
				font-weight: 800;
			}

			.status-warning {
				color: #FFD166;
				font-weight: 800;
			}

			.status-fail {
				color: #FF6B6B;
				font-weight: 800;
			}

			.status-review {
				color: #8AB4F8;
				font-weight: 800;
			}

			div[data-testid="stMetric"] {
				border: 1px solid #2A2A2D;
				border-radius: 0.85rem;
				background: #171717;
				padding: 0.75rem 0.85rem;
			}
		</style>
		""",
		unsafe_allow_html=True
	)
	
	st.markdown( get_accessibility_css( ), unsafe_allow_html=True )

# ==========================================================================================
# Sidebar / Manual Input
# ==========================================================================================

def display_synthetic_generator_expander( ) -> None:
	"""Display sidebar controls for the local synthetic demonstration data generator.

	Purpose:
		Render a Streamlit sidebar expander named ``Synthetic Generator``. The controls create or
		clear the standard fictional Fiddy demonstration pack under ``samples/manifests`` and
		``samples/labels``. The generated files are not automatically loaded into Streamlit upload
		widgets; reviewers use the normal manifest and artwork upload controls after generation.

	Returns:
		None.
	"""
	try:
		if not bool( getattr( cfg, 'SYNTHETIC_DEMO_ENABLED', True ) ):
			with st.sidebar.expander( 'Synthetic Generator', expanded=False ):
				st.caption( 'Synthetic generator is disabled by configuration.' )
			
			return None
		
		with st.sidebar.expander( 'Synthetic Data Generator', expanded=False ):
			st.caption( 'Generate or clear fictional local demo files under samples/manifests and '
				'samples/labels.' )
			
			overwrite_demo_pack = st.checkbox( 'Overwrite existing demo pack', value=False,
				key='synthetic_generator_overwrite_checkbox',
				help='Replace existing generated fiddy_v2 demo files when they already exist.' )
			
			generate_button = st.button( 'Create Synthetic Data',
				key='synthetic_generator_generate_button',
				use_container_width=True
			)
			
			clear_button = st.button( 'Clear Synthetic Data',
				key='synthetic_generator_clear_button',
				use_container_width=True )
			
			if generate_button:
				generator = SyntheticDataGenerator( )
				result = generator.generate_standard_demo_pack( overwrite=overwrite_demo_pack )
				
				st.session_state[ 'synthetic_generator_last_action' ] = 'generated'
				st.session_state[ 'synthetic_generator_manifest_path' ] = result.manifest_path
				st.session_state[ 'synthetic_generator_label_directory' ] = result.label_directory
				st.session_state[ 'synthetic_generator_generated_count' ] = len( result.generated_files )
				st.session_state[ 'synthetic_generator_deleted_count' ] = 0
				st.session_state[ 'synthetic_generator_record_count' ] = result.record_count
				st.session_state[ 'synthetic_generator_last_message' ] = result.message
				st.session_state[ 'synthetic_generator_last_success' ] = result.success
				
				if result.success:
					st.success( result.message )
				else:
					st.warning( result.message )
			
			if clear_button:
				generator = SyntheticDataGenerator( )
				result = generator.clear_demo_pack( )
				
				st.session_state[ 'synthetic_generator_last_action' ] = 'cleared'
				st.session_state[ 'synthetic_generator_manifest_path' ] = ''
				st.session_state[ 'synthetic_generator_label_directory' ] = ''
				st.session_state[ 'synthetic_generator_generated_count' ] = 0
				st.session_state[ 'synthetic_generator_deleted_count' ] = len( result.deleted_files )
				st.session_state[ 'synthetic_generator_record_count' ] = 0
				st.session_state[ 'synthetic_generator_last_message' ] = result.message
				st.session_state[ 'synthetic_generator_last_success' ] = result.success
				
				if result.success:
					st.success( result.message )
				else:
					st.warning( result.message )
			
			last_action = st.session_state.get(
				'synthetic_generator_last_action',
				''
			)
			last_message = st.session_state.get(
				'synthetic_generator_last_message',
				''
			)
			manifest_path = st.session_state.get(
				'synthetic_generator_manifest_path',
				''
			)
			label_directory = st.session_state.get(
				'synthetic_generator_label_directory',
				''
			)
			generated_count = int(
				st.session_state.get( 'synthetic_generator_generated_count', 0 )
			)
			deleted_count = int(
				st.session_state.get( 'synthetic_generator_deleted_count', 0 )
			)
			record_count = int(
				st.session_state.get( 'synthetic_generator_record_count', 0 )
			)
			
			if last_message:
				st.caption( last_message )
			
			if last_action == 'generated':
				if manifest_path:
					st.caption( f'Manifest: {manifest_path}' )
				
				if label_directory:
					st.caption( f'Labels: {label_directory}' )
				
				st.caption(
					f'Generated files: {generated_count} | Manifest records: {record_count}'
				)
				
				st.caption(
					'Upload the generated manifest and labels using the normal application '
					'upload controls.'
				)
			
			if last_action == 'cleared':
				st.caption(
					f'Deleted files: {deleted_count}'
				)
				
				st.caption(
					'Generated synthetic demo files have been removed. Generate a new demo pack '
					'to create fresh manifest and label files.'
				)
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'display_synthetic_generator_expander( ) -> None'
		Logger( ).write( error )
		st.sidebar.warning( f'Synthetic Generator could not be displayed: {e}' )
		return None

def display_sidebar_header( ) -> None:
	"""Display the application logo and reviewer controls in the sidebar.

	Purpose:
		Render the configured Fiddy logo, reviewer controls, reset control, demo asset guidance,
		and local synthetic generator controls. Session-state values are updated immediately so
		the main workflow can hide technical controls, apply accessibility CSS consistently, and
		reset the application to its initial state when requested.

	Returns:
		None.
	"""
	logo_path = get_configured_image_path( getattr( cfg, 'LOGO', '' ) )
	
	if logo_path:
		left_column, center_column, right_column = st.sidebar.columns( [ 0.15, 0.70, 0.15 ] )
		
		with center_column:
			st.image(
				logo_path,
				width=90
			)
	else:
		st.sidebar.caption( 'Logo file not found. Check cfg.LOGO path.' )
	
	st.sidebar.divider( )
	
	with st.sidebar.expander( 'Reviewer Controls', expanded=False ):
		st.radio(
			'Review Mode',
			options=[
					'Simple',
					'Advanced'
			],
			index=0 if st.session_state.get( 'simple_mode', True ) else 1,
			key='review_mode',
			help='Simple mode hides technical OCR, diagnostics, rule detail, and methodology sections.'
		)
		
		st.session_state[ 'simple_mode' ] = st.session_state[ 'review_mode' ] == 'Simple'
		
		st.toggle(
			'High Contrast',
			key='high_contrast_mode',
			help='Increase contrast for visual accessibility.'
		)
		
		st.toggle(
			'Large Text',
			key='large_text_mode',
			help='Increase text and control size for readability.'
		)
		
		st.toggle(
			'Keyboard Tips',
			key='show_keyboard_notes',
			help='Show keyboard navigation guidance in the reviewer workflow.'
		)
	
	display_synthetic_generator_expander( )
	
	with st.sidebar.expander( 'Application State', expanded=False ):
		st.caption(
			'Reset clears uploaded widget state, manifest records, CAV values, verification '
			'results, generated reports, and display tables.'
		)
		
		if st.button(
				'Reset Application',
				key='reset_application_button',
				use_container_width=True,
				help='Return Fiddy to its initial startup state.'
		):
			reset_application_state( )
			st.rerun( )

def is_previewable_artwork_name( file_name: str ) -> bool:
	"""Determine whether a file name can be previewed in the reviewer artwork panel.

	Args:
		file_name (str): File name to inspect.

	Returns:
		bool: ``True`` when the file extension is supported by the preview panel; otherwise,
		``False``.
	"""
	try:
		cfg.throw_if( 'file_name', file_name )
		
		file_extension = Path( file_name ).suffix.lower( )
		
		return file_extension in (
				'.png',
				'.jpg',
				'.jpeg',
				'.webp',
				'.bmp',
				'.tif',
				'.tiff',
				'.pdf'
		)
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'is_previewable_artwork_name( file_name: str ) -> bool'
		Logger( ).write( error )
		return False

def is_previewable_image_name( file_name: str ) -> bool:
	"""Determine whether a file name can be previewed directly as an image.

	Args:
		file_name (str): File name to inspect.

	Returns:
		bool: ``True`` when the file extension is supported by ``st.image``; otherwise,
		``False``.
	"""
	try:
		cfg.throw_if( 'file_name', file_name )
		
		file_extension = Path( file_name ).suffix.lower( )
		
		return file_extension in (
				'.png',
				'.jpg',
				'.jpeg',
				'.webp',
				'.bmp',
				'.tif',
				'.tiff'
		)
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'is_previewable_image_name( file_name: str ) -> bool'
		Logger( ).write( error )
		return False

def is_previewable_pdf_name( file_name: str ) -> bool:
	"""Determine whether a file name can be previewed as a PDF.

	Args:
		file_name (str): File name to inspect.

	Returns:
		bool: ``True`` when the file extension is ``.pdf``; otherwise, ``False``.
	"""
	try:
		cfg.throw_if( 'file_name', file_name )
		
		return Path( file_name ).suffix.lower( ) == '.pdf'
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'is_previewable_pdf_name( file_name: str ) -> bool'
		Logger( ).write( error )
		return False

def get_uploaded_artwork_bytes_by_name( uploaded_files: List[ object ],
		target_file_name: str ) -> bytes:
	"""Return uploaded artwork bytes matching a target file name.

	Purpose:
		Locate an uploaded image or PDF by file name. The function checks direct uploads first
		and then supported artwork members inside uploaded ZIP archives. It is used only by the
		reviewer preview panel and does not alter the verification workflow.

	Args:
		uploaded_files (List[object]): Uploaded artwork files from Streamlit.
		target_file_name (str): Manifest or CAV file name to locate.

	Returns:
		bytes: Matching artwork bytes, or empty bytes when no previewable match is available.
	"""
	try:
		cfg.throw_if( 'uploaded_files', uploaded_files )
		cfg.throw_if( 'target_file_name', target_file_name )
		
		target_name = Path( target_file_name ).name
		
		if not is_previewable_artwork_name( target_name ):
			return b''
		
		for uploaded_file in uploaded_files:
			uploaded_name = Path( getattr( uploaded_file, 'name', '' ) ).name
			
			if not is_zip_upload( uploaded_file ):
				if uploaded_name == target_name and is_previewable_artwork_name( uploaded_name ):
					return bytes( uploaded_file.getbuffer( ) )
				
				continue
			
			file_bytes = bytes( uploaded_file.getbuffer( ) )
			
			with zipfile.ZipFile( BytesIO( file_bytes ) ) as archive:
				for info in archive.infolist( ):
					member_name = info.filename
					
					if not is_safe_archive_member_name( member_name ):
						continue
					
					member_file_name = Path( member_name ).name
					
					if member_file_name != target_name:
						continue
					
					if not is_previewable_artwork_name( member_file_name ):
						continue
					
					return archive.read( info )
		
		return b''
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_uploaded_artwork_bytes_by_name( self, *args ) -> bytes'
		Logger( ).write( error )
		return b''

def display_pdf_preview( pdf_bytes: bytes, file_name: str ) -> None:
	"""Display a PDF preview with a safe fallback when PDF viewing is unavailable.

	Purpose:
		Render a PDF in the reviewer preview panel using Streamlit's PDF viewer when available.
		If the runtime does not expose ``st.pdf``, the function displays a clear fallback message
		and offers the PDF as a download instead of interrupting the workflow.

	Args:
		pdf_bytes (bytes): PDF bytes to display.
		file_name (str): PDF file name.

	Returns:
		None.
	"""
	try:
		cfg.throw_if( 'pdf_bytes', pdf_bytes )
		cfg.throw_if( 'file_name', file_name )
		
		if hasattr( st, 'pdf' ):
			st.pdf( pdf_bytes )
			st.caption( file_name )
			return
		
		st.info(
			'PDF preview is unavailable in this Streamlit runtime. The PDF will still be '
			'processed during verification.'
		)
		st.download_button(
			label='Download PDF Preview File',
			data=pdf_bytes,
			file_name=Path( file_name ).name,
			mime='application/pdf',
			use_container_width=True,
			key=f'pdf_preview_download_{Path( file_name ).stem}'
		)
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'display_pdf_preview( pdf_bytes: bytes, file_name: str ) -> None'
		Logger( ).write( error )
		st.warning( f'Unable to display PDF preview: {e}' )

def display_label_artwork_preview( uploaded_files: List[ object ], file_name: str ) -> None:
	"""Display a synchronized label artwork preview for the active CAV or manifest record.

	Purpose:
		Show the uploaded label artwork that matches the active manifest/CAV file name. The
		preview supports common image formats and PDF files from direct uploads and ZIP archive
		members. The preview does not alter the verification workflow.

	Args:
		uploaded_files (List[object]): Uploaded artwork files from Streamlit.
		file_name (str): Active manifest/CAV file name.

	Returns:
		None.
	"""
	try:
		if not file_name:
			st.info( 'No manifest file name is selected.' )
			return
		
		if not uploaded_files:
			st.info( 'Upload label artwork to display the matching preview.' )
			return
		
		if not is_previewable_artwork_name( file_name ):
			st.info( 'Preview is available for image and PDF artwork files.' )
			st.caption( f'Selected file: {file_name}' )
			return
		
		artwork_bytes = get_uploaded_artwork_bytes_by_name( uploaded_files, file_name )
		
		if not artwork_bytes:
			st.warning( f'No uploaded preview file matches: {file_name}' )
			return
		
		if is_previewable_pdf_name( file_name ):
			display_pdf_preview( artwork_bytes, file_name )
			return
		
		if is_previewable_image_name( file_name ):
			image = Image.open( BytesIO( artwork_bytes ) )
			st.image(
				image,
				caption=file_name,
				use_container_width=True
			)
			return
		
		st.info( 'No preview renderer is available for the selected file.' )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'display_label_artwork_preview( uploaded_files: List[object], file_name: str ) -> None'
		Logger( ).write( error )
		st.warning( f'Unable to display label preview: {e}' )

def create_simple_label_application( uploaded_manifest: object,
		uploaded_files: List[ object ] ) -> LabelApplication:
	"""Create application data and display the Simple Mode CAV/artwork preview panel.

	Purpose:
		Display expected CAV or manifest values and a synchronized label artwork preview inside
		one expander. The top row contains manifest navigation controls. The middle area places
		the six primary fields in the left two-thirds using a three-row by two-column layout and
		the matching image/PDF preview in the right one-third. The government warning occupies a
		full-width bottom row. When a manifest is uploaded, the active manifest record controls
		both the form values and the previewed artwork.

	Args:
		uploaded_manifest (object): Streamlit uploaded manifest file.
		uploaded_files (List[object]): Uploaded label artwork files.

	Returns:
		LabelApplication: Expected label application values for manual review, or an empty
		application object when manifest mode is active.
	"""
	initialize_cav_form_state( )
	
	with st.expander( 'Application / Manifest Data and Label Preview', expanded=True ):
		if uploaded_manifest:
			st.caption(
				'Review the active manifest record. Use the navigation controls to move through '
				'the manifest.'
			)
			display_manifest_record_navigation( key_prefix='simple_cav_form' )
		else:
			st.caption(
				'Complete these fields only when reviewing artwork without a manifest CSV.'
			)
		
		form_column, preview_column = st.columns( [ 0.67, 0.33 ] )
		
		with form_column:
			row_1_left, row_1_right = st.columns( 2 )
			
			with row_1_left:
				st.text_input(
					'Brand Name',
					key='cav_brand_name',
					help='Used for fuzzy matching against the brand name extracted from the label.'
				)
			
			with row_1_right:
				st.text_input(
					'Class / Type',
					key='cav_class_type',
					help='Product class/type designation.'
				)
			
			row_2_left, row_2_right = st.columns( 2 )
			
			with row_2_left:
				st.text_input(
					'ABV',
					key='cav_abv',
					help='Alcohol by volume value used for numeric comparison.'
				)
			
			with row_2_right:
				st.text_input(
					'Net Contents',
					key='cav_net_contents',
					help='Container volume used for comparison.'
				)
			
			row_3_left, row_3_right = st.columns( 2 )
			
			with row_3_left:
				st.text_input(
					'Producer / Bottler',
					key='cav_producer_bottler',
					help='Producer, bottler, brewer, vintner, importer, or responsible party text.'
				)
			
			with row_3_right:
				st.text_input(
					'Country of Origin',
					key='cav_country_of_origin',
					help='Country of origin value when applicable.'
				)
		
		with preview_column:
			st.markdown( '**Label Preview**' )
			
			active_file_name = str( st.session_state.get( 'cav_file_name', '' ) ).strip( )
			
			if uploaded_manifest:
				current_record = get_current_manifest_record( )
				
				if current_record:
					active_file_name = str(
						get_record_value( current_record, 'file_name', active_file_name )
					).strip( )
			
			display_label_artwork_preview( uploaded_files, active_file_name )
		
		st.text_area(
			'Government Warning',
			key='cav_government_warning',
			height=120,
			help='Expected government warning text. Exact-match review is required.'
		)
	
	if uploaded_manifest:
		return LabelApplication( )
	
	alcohol_content = parse_optional_float( st.session_state.get( 'cav_abv', '' ) )
	proof = alcohol_content * 2.0 if alcohol_content is not None else None
	
	return LabelApplication(
		brand_name=st.session_state.get( 'cav_brand_name', '' ),
		class_type=st.session_state.get( 'cav_class_type', '' ),
		beverage_type=st.session_state.get(
			'cav_beverage_type',
			BEVERAGE_TYPE_DISTILLED_SPIRITS
		),
		alcohol_content=alcohol_content,
		proof=proof,
		net_contents=st.session_state.get( 'cav_net_contents', '' ),
		producer_bottler=st.session_state.get( 'cav_producer_bottler', '' ),
		imported=bool( st.session_state.get( 'cav_imported', False ) ),
		importer=st.session_state.get( 'cav_importer', '' ),
		country_of_origin=st.session_state.get( 'cav_country_of_origin', '' ),
		government_warning=st.session_state.get( 'cav_government_warning', '' ),
		cola_id=st.session_state.get( 'cav_cola_id', '' ),
		notes=st.session_state.get( 'cav_notes', '' )
	)

def create_manual_label_application( ) -> LabelApplication:
	"""Display the full CAV form and return entered or loaded application values.

	Purpose:
		This function renders the Advanced Mode CAV data panel, manifest record navigation, all
		core application fields, import-related fields, government warning text, and reviewer notes.
		It then parses ABV and proof values from session state and returns a populated
		``LabelApplication``.

	Returns:
		LabelApplication: Expected label application values entered manually or loaded from the
		current manifest record.
	"""
	initialize_cav_form_state( )
	
	st.markdown(
		"""
		<div class="fiddy-panel">
			<div class="fiddy-panel-title">CAV Application Data</div>
			<div class="fiddy-panel-text">
				Review, paste, or load the expected CAV application values. These values are
				compared against the extracted label artwork.
			</div>
		</div>
		""",
		unsafe_allow_html=True
	)
	
	display_manifest_record_navigation( key_prefix='cav_form' )
	
	left_column, right_column = st.columns( [ 0.50, 0.50 ] )
	
	with left_column:
		st.text_input(
			'Manifest File Name',
			key='cav_file_name',
			help='Expected uploaded label artwork filename from the CAV manifest.'
		)
		
		st.text_input(
			'Brand Name',
			key='cav_brand_name',
			help='Used for fuzzy matching against the brand name extracted from the label.'
		)
		
		st.text_input(
			'Class / Type',
			key='cav_class_type',
			help='Spirits, wine, beer, or other product class/type designation.'
		)
		
		st.text_input(
			'ABV',
			key='cav_abv',
			help='Alcohol by volume value used for numeric comparison.'
		)
		
		st.text_input(
			'Net Contents',
			key='cav_net_contents',
			help='Container volume used for label-to-application comparison.'
		)
	
	with right_column:
		st.selectbox(
			'Beverage Type',
			options=BEVERAGE_TYPES,
			key='cav_beverage_type',
			help='Product category used to guide label review context.'
		)
		
		st.text_input(
			'Producer / Bottler',
			key='cav_producer_bottler',
			help='Producer, bottler, brewer, vintner, importer, or responsible party text.'
		)
		
		st.text_input(
			'Country of Origin',
			key='cav_country_of_origin',
			help='Country of origin value used for comparison when applicable.'
		)
		
		st.checkbox(
			'Imported Product',
			key='cav_imported',
			help='Select when importer and country-of-origin review should apply.'
		)
		
		st.text_input(
			'Importer',
			key='cav_importer',
			help='Importer name required for imported products.'
		)
	
	st.text_area(
		'Government Warning',
		key='cav_government_warning',
		height=130,
		help='Expected government warning text. Exact-match review is required.'
	)
	
	st.text_area(
		'Reviewer Notes',
		key='cav_notes',
		height=85,
		help='Optional notes for reviewer context.'
	)
	
	alcohol_content = parse_optional_float( st.session_state.get( 'cav_abv', '' ) )
	proof = parse_optional_float( st.session_state.get( 'cav_proof', '' ) )
	
	if proof is None and alcohol_content is not None:
		proof = alcohol_content * 2.0
	
	return LabelApplication(
		brand_name=st.session_state.get( 'cav_brand_name', '' ),
		class_type=st.session_state.get( 'cav_class_type', '' ),
		beverage_type=st.session_state.get(
			'cav_beverage_type',
			BEVERAGE_TYPE_DISTILLED_SPIRITS
		),
		alcohol_content=alcohol_content,
		proof=proof,
		net_contents=st.session_state.get( 'cav_net_contents', '' ),
		producer_bottler=st.session_state.get( 'cav_producer_bottler', '' ),
		imported=bool( st.session_state.get( 'cav_imported', False ) ),
		importer=st.session_state.get( 'cav_importer', '' ),
		country_of_origin=st.session_state.get( 'cav_country_of_origin', '' ),
		government_warning=st.session_state.get( 'cav_government_warning', '' ),
		cola_id=st.session_state.get( 'cav_cola_id', '' ),
		notes=st.session_state.get( 'cav_notes', '' )
	)

# ==========================================================================================
# Header / Status Helpers
# ==========================================================================================

def display_header( ) -> None:
	"""Display the compact application header in the main workspace.

	Purpose:
		The header identifies the workspace, displays the configured application display name, and
		briefly states the upload, verification, review, and export workflow. It intentionally does
		not duplicate the sidebar logo.

	Returns:
		None.
	"""
	st.markdown(
		f"""
        <div class="fiddy-header">
            <div class="fiddy-eyebrow">Alcohol Label Review Workspace</div>
            <div class="fiddy-title">{APP_DISPLAY_NAME}</div>
            <div class="fiddy-subtitle">
                Upload an application manifest and matching label artwork, run local OCR/rule
                verification, review flagged items, and export batch results.
            </div>
        </div>
        """,
		unsafe_allow_html=True
	)

def get_status_html( status: str ) -> str:
	"""Return styled HTML for a verification status value.

	Purpose:
		This function maps known status values to CSS classes used by the application theme. Unknown
		status text is returned unchanged so unrecognized values can still be displayed.

	Args:
		status (str): Verification status.

	Returns:
		str: HTML status markup, or ``STATUS_REVIEW`` when formatting fails.
	"""
	try:
		cfg.throw_if( 'status', status )
		
		if status == STATUS_PASS:
			return f'<span class="status-pass">{status}</span>'
		
		if status == STATUS_WARNING:
			return f'<span class="status-warning">{status}</span>'
		
		if status == STATUS_FAIL:
			return f'<span class="status-fail">{status}</span>'
		
		if status == STATUS_REVIEW:
			return f'<span class="status-review">{status}</span>'
		
		return status
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_status_html( status: str ) -> str'
		Logger( ).write( error )
		return STATUS_REVIEW

def get_batch_metrics( batch_report: BatchVerificationReport,
		batch_result: BatchProcessingResult ) -> Tuple[ int, int, int, int, int ]:
	"""Calculate top-level batch metrics for dashboard display.

	Purpose:
		This function summarizes the active batch into file count, failure count, warning count,
		review count, and SLA breach count. It delegates report counts to ``BatchVerificationReport``
		and performance counts to ``BatchProcessingResult``.

	Args:
		batch_report (BatchVerificationReport): Batch verification report.
		batch_result (BatchProcessingResult): Batch processing result.

	Returns:
		Tuple[int, int, int, int, int]: Files, failures, warnings, reviews, and SLA breaches.
	"""
	try:
		cfg.throw_if( 'batch_report', batch_report )
		cfg.throw_if( 'batch_result', batch_result )
		
		return (
				batch_report.total_files( ),
				batch_report.total_failures( ),
				batch_report.total_warnings( ),
				batch_report.total_reviews( ),
				batch_result.performance_summary.sla_breach_count
		)
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_batch_metrics( self, *args ) -> Tuple[int, int, int, int, int]'
		Logger( ).write( error )
		return 0, 0, 0, 0, 0

# ==========================================================================================
# Upload / Save Helpers
# ==========================================================================================

def get_supported_upload_type_values( ) -> List[ str ]:
	"""Return Streamlit uploader type values for artwork and ZIP archives.

	Purpose:
		This function starts with configured supported upload types and ensures ZIP archives are
		included because the UI accepts either individual image/PDF artwork files or a ZIP archive
		containing supported artwork files.

	Returns:
		List[str]: Supported uploader type values.
	"""
	try:
		values = list( SUPPORTED_UPLOAD_TYPES )
		
		if 'zip' not in values:
			values.append( 'zip' )
		
		return values
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_supported_upload_type_values( ) -> List[str]'
		Logger( ).write( error )
		return [
				'png',
				'jpg',
				'jpeg',
				'webp',
				'bmp',
				'tif',
				'tiff',
				'pdf',
				'zip'
		]

def is_zip_upload( uploaded_file: object ) -> bool:
	"""Determine whether an uploaded file is a ZIP archive.

	Args:
		uploaded_file (object): Streamlit uploaded file object.

	Returns:
		bool: ``True`` when the uploaded file name has a ``.zip`` extension; otherwise,
		``False``.
	"""
	try:
		cfg.throw_if( 'uploaded_file', uploaded_file )
		
		file_name = str( getattr( uploaded_file, 'name', '' ) ).lower( )
		return Path( file_name ).suffix.lower( ) == '.zip'
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'is_zip_upload( uploaded_file: object ) -> bool'
		Logger( ).write( error )
		return False

def is_supported_artwork_name( file_name: str ) -> bool:
	"""Determine whether a file name has a supported image or PDF extension.

	Args:
		file_name (str): File name to inspect.

	Returns:
		bool: ``True`` when the file extension is supported for OCR; otherwise, ``False``.
	"""
	try:
		cfg.throw_if( 'file_name', file_name )
		
		file_type = Path( file_name ).suffix.lower( ).replace( '.', '' )
		return file_type in list( SUPPORTED_UPLOAD_TYPES )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'is_supported_artwork_name( file_name: str ) -> bool'
		Logger( ).write( error )
		return False

def is_safe_archive_member_name( member_name: str ) -> bool:
	"""Determine whether a ZIP member path is safe to extract.

	Purpose:
		This function blocks empty names, directory entries, absolute paths, parent traversal, macOS
		metadata directories, hidden dot-files, and entries without a basename. It is part of the
		ZIP extraction guardrails used before writing uploaded archive contents to disk.

	Args:
		member_name (str): ZIP member path.

	Returns:
		bool: ``True`` when the member path is safe and extractable; otherwise, ``False``.
	"""
	try:
		cfg.throw_if( 'member_name', member_name )
		
		path = PurePosixPath( member_name )
		parts = path.parts
		
		if not parts:
			return False
		
		if member_name.endswith( '/' ):
			return False
		
		if path.is_absolute( ):
			return False
		
		if '..' in parts:
			return False
		
		if parts[ 0 ] == '__MACOSX':
			return False
		
		if Path( member_name ).name.startswith( '.' ):
			return False
		
		return bool( Path( member_name ).name )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'is_safe_archive_member_name( member_name: str ) -> bool'
		Logger( ).write( error )
		return False

def get_archive_member_file_names( uploaded_file: object ) -> List[ str ]:
	"""Return supported artwork file names contained in an uploaded ZIP archive.

	Purpose:
		This function reads the ZIP upload, filters archive members through the safe-member check,
		filters by supported artwork extension, and returns only the member basenames displayed to
		the reviewer and used in manifest matching summaries.

	Args:
		uploaded_file (object): Streamlit uploaded ZIP file.

	Returns:
		List[str]: Supported ZIP member basenames, or an empty list when inspection fails.
	"""
	try:
		cfg.throw_if( 'uploaded_file', uploaded_file )
		
		file_names = [ ]
		file_bytes = bytes( uploaded_file.getbuffer( ) )
		
		with zipfile.ZipFile( BytesIO( file_bytes ) ) as archive:
			for info in archive.infolist( ):
				member_name = info.filename
				
				if not is_safe_archive_member_name( member_name ):
					continue
				
				member_file_name = Path( member_name ).name
				
				if is_supported_artwork_name( member_file_name ):
					file_names.append( member_file_name )
		
		return file_names
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_archive_member_file_names( uploaded_file: object ) -> List[str]'
		Logger( ).write( error )
		return [ ]

def save_zip_artwork_files( uploaded_file: object, temp_dir: str ) -> List[ Path ]:
	"""Safely extract supported artwork files from a ZIP archive.

	Purpose:
		This function extracts only safe ZIP members with supported artwork extensions. Files are
		written under the supplied temporary directory using the member basename, and resolved paths
		are checked to prevent path traversal outside the temporary root.

	Args:
		uploaded_file (object): Streamlit uploaded ZIP file.
		temp_dir (str): Temporary extraction directory.

	Returns:
		List[Path]: Extracted image/PDF file paths. If extraction fails, any files extracted
		before the failure remain in the returned list.
	"""
	file_paths = [ ]
	
	try:
		cfg.throw_if( 'uploaded_file', uploaded_file )
		cfg.throw_if( 'temp_dir', temp_dir )
		
		root_path = Path( temp_dir ).resolve( )
		file_bytes = bytes( uploaded_file.getbuffer( ) )
		
		with zipfile.ZipFile( BytesIO( file_bytes ) ) as archive:
			for info in archive.infolist( ):
				member_name = info.filename
				
				if not is_safe_archive_member_name( member_name ):
					continue
				
				member_file_name = Path( member_name ).name
				
				if not is_supported_artwork_name( member_file_name ):
					continue
				
				output_path = (root_path / member_file_name).resolve( )
				
				if root_path not in output_path.parents and output_path != root_path:
					continue
				
				output_path.write_bytes( archive.read( info ) )
				file_paths.append( output_path )
		
		return file_paths
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'save_zip_artwork_files( uploaded_file: object, temp_dir: str ) -> List[Path]'
		Logger( ).write( error )
		st.warning( f'Unable to extract ZIP archive {getattr( uploaded_file, "name", "" )}: {e}' )
		return file_paths

def save_uploaded_files( uploaded_files: List[ object ], temp_dir: str ) -> List[ Path ]:
	"""Save uploaded artwork files and safely extract supported ZIP contents.

	Purpose:
		Write individual supported image/PDF uploads to a temporary directory and expand ZIP
		uploads through ``save_zip_artwork_files``. All output paths are resolved and checked
		against the temporary root to prevent writes outside the working directory. The returned
		file names are the names used by the batch processor for manifest-to-artwork matching.

	Args:
		uploaded_files (List[object]): Streamlit uploaded file objects.
		temp_dir (str): Temporary directory path.

	Returns:
		List[Path]: Paths to temporary image/PDF files saved for OCR processing.
	"""
	file_paths = [ ]
	
	try:
		cfg.throw_if( 'uploaded_files', uploaded_files )
		cfg.throw_if( 'temp_dir', temp_dir )
		
		root_path = Path( temp_dir ).resolve( )
		root_path.mkdir( parents=True, exist_ok=True )
		
		for uploaded_file in uploaded_files:
			if is_zip_upload( uploaded_file ):
				file_paths.extend( save_zip_artwork_files( uploaded_file, temp_dir ) )
				continue
			
			file_name = Path( str( getattr( uploaded_file, 'name', '' ) ) ).name
			
			if not file_name:
				continue
			
			if not is_supported_artwork_name( file_name ):
				continue
			
			file_path = (root_path / file_name).resolve( )
			
			if root_path not in file_path.parents and file_path != root_path:
				continue
			
			file_path.write_bytes( bytes( uploaded_file.getbuffer( ) ) )
			
			if file_path.exists( ) and file_path.stat( ).st_size > 0:
				file_paths.append( file_path )
		
		return file_paths
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'save_uploaded_files( uploaded_files: List[object], temp_dir: str ) -> List[Path]'
		Logger( ).write( error )
		st.error( f'Unable to save uploaded files: {e}' )
		return file_paths

def save_manifest_file( uploaded_manifest: object, temp_dir: str ) -> Path:
	"""Save an uploaded manifest CSV to a temporary directory.

	Args:
		uploaded_manifest (object): Streamlit uploaded manifest object.
		temp_dir (str): Temporary directory path.

	Returns:
		Path: Saved manifest path, or ``Path('')`` when saving fails.
	"""
	try:
		cfg.throw_if( 'uploaded_manifest', uploaded_manifest )
		cfg.throw_if( 'temp_dir', temp_dir )
		
		manifest_path = Path( temp_dir ) / uploaded_manifest.name
		manifest_path.write_bytes( uploaded_manifest.getbuffer( ) )
		
		return manifest_path
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'save_manifest_file( uploaded_manifest: object, temp_dir: str ) -> Path'
		Logger( ).write( error )
		return Path( '' )

def create_uploaded_file_dataframe( uploaded_files: List[ object ] ) -> pd.DataFrame:
	"""Create a display table for uploaded artwork and ZIP archive contents.

	Purpose:
		This function creates one row for each individual uploaded artwork file and one row for
		each supported artwork member inside uploaded ZIP archives. The result is used by Advanced
		Mode upload previews.

	Args:
		uploaded_files (List[object]): Uploaded label files.

	Returns:
		pd.DataFrame: Uploaded file summary DataFrame.
	"""
	try:
		records = [ ]
		
		for uploaded_file in uploaded_files:
			if is_zip_upload( uploaded_file ):
				file_bytes = bytes( uploaded_file.getbuffer( ) )
				
				with zipfile.ZipFile( BytesIO( file_bytes ) ) as archive:
					for info in archive.infolist( ):
						member_name = info.filename
						
						if not is_safe_archive_member_name( member_name ):
							continue
						
						member_file_name = Path( member_name ).name
						
						if not is_supported_artwork_name( member_file_name ):
							continue
						
						records.append(
							{
									'Source': uploaded_file.name,
									'File Name': member_file_name,
									'Size KB': round( info.file_size / 1024.0, 2 ),
									'Type': Path( member_file_name ).suffix.lower( )
									.replace( '.', '' ),
									'Input Type': 'ZIP Member'
							}
						)
				
				continue
			
			records.append(
				{
						'Source': uploaded_file.name,
						'File Name': uploaded_file.name,
						'Size KB': round( len( uploaded_file.getbuffer( ) ) / 1024.0, 2 ),
						'Type': Path( uploaded_file.name ).suffix.lower( ).replace( '.', '' ),
						'Input Type': 'Uploaded File'
				}
			)
		
		return pd.DataFrame( records )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'create_uploaded_file_dataframe( uploaded_files: List[object] ) -> pd.DataFrame'
		Logger( ).write( error )
		return pd.DataFrame(
			columns=[
					'Source',
					'File Name',
					'Size KB',
					'Type',
					'Input Type'
			]
		)

# ==========================================================================================
# Verification Actions
# ==========================================================================================

@st.cache_resource( show_spinner=False )
def load_batch_processor( max_workers: int, sla_seconds: float ) -> BatchProcessor:
	"""Load and cache the batch processor resource for Streamlit execution.

	Args:
		max_workers (int): Maximum number of batch worker threads.
		sla_seconds (float): Per-label SLA threshold in seconds.

	Returns:
		BatchProcessor: Cached batch processor.
	"""
	return BatchProcessor( max_workers=max_workers, sla_seconds=sla_seconds )

def run_manifest_batch_verification( uploaded_manifest: object, uploaded_files: List[ object ],
		max_workers: int, sla_seconds: float ) -> None:
	"""Run manifest-driven batch verification for uploaded label artwork.

	Purpose:
		Save the manifest and artwork files to a temporary directory, run the cached batch
		processor, build summary, detail, comparison, performance, JSON, and Markdown outputs,
		store those outputs in session state, and update Streamlit progress indicators. The
		function also verifies that saved artwork filenames match the manifest before invoking the
		batch processor so the UI can distinguish upload/save problems from OCR/rule problems.

	Args:
		uploaded_manifest (object): Uploaded application manifest CSV.
		uploaded_files (List[object]): Uploaded label artwork files.
		max_workers (int): Maximum number of worker threads.
		sla_seconds (float): Per-label SLA threshold.

	Returns:
		None.
	"""
	try:
		cfg.throw_if( 'uploaded_manifest', uploaded_manifest )
		cfg.throw_if( 'uploaded_files', uploaded_files )
		
		writer = ReportWriter( )
		progress_bar = st.progress( 0 )
		status_text = st.empty( )
		
		with tempfile.TemporaryDirectory( ) as temp_dir:
			manifest_path = save_manifest_file( uploaded_manifest, temp_dir )
			file_paths = save_uploaded_files( uploaded_files, temp_dir )
			
			expected_names = get_manifest_expected_file_names( )
			saved_names = [
					path.name
					for path in file_paths
			]
			expected_lookup = {
					name.strip( ).lower( )
					for name in expected_names
					if name
			}
			saved_lookup = {
					name.strip( ).lower( )
					for name in saved_names
					if name
			}
			missing_after_save = sorted(
				[
						name
						for name in expected_names
						if name.strip( ).lower( ) not in saved_lookup
				]
			)
			
			if expected_lookup and not saved_lookup:
				st.error(
					'No uploaded label artwork files were saved for verification. Re-upload the '
					'manifest and label files, then run verification again.'
				)
				st.session_state[ 'verification_complete' ] = False
				return None
			
			if missing_after_save:
				st.warning(
					f'{len( missing_after_save )} manifest file(s) did not match saved artwork '
					'files after upload processing.'
				)
				
				if not st.session_state.get( 'simple_mode', True ):
					st.write(
						{
								'Expected Manifest Files': expected_names,
								'Saved Artwork Files': saved_names,
								'Missing After Save': missing_after_save
						}
					)
			
			processor = load_batch_processor( max_workers, sla_seconds )
			
			def update_progress( completed: int, total: int, file_name: str ) -> None:
				"""Update Streamlit progress from the batch processor.

				Args:
					completed (int): Completed file count.
					total (int): Total file count.
					file_name (str): Current file name.

				Returns:
					None.
				"""
				percent = int( completed / total * 100 ) if total else 0
				progress_bar.progress( min( 100, percent ) )
				status_text.info( f'Processed {completed} of {total}: {file_name}' )
			
			result = processor.process_manifest_csv(
				manifest_path=manifest_path,
				file_paths=file_paths,
				progress_callback=update_progress
			)
		
		df_summary = writer.batch_to_summary_dataframe( result.batch_report )
		df_details = writer.batch_to_detail_dataframe( result.batch_report )
		df_comparison = writer.batch_to_comparison_dataframe( result.batch_report )
		df_performance = writer.performance_to_dataframe( result.performance_results )
		json_report = writer.batch_to_json( result.batch_report )
		markdown_report = writer.batch_to_markdown( result.batch_report )
		
		st.session_state[ 'batch_result' ] = result
		st.session_state[ 'df_summary' ] = df_summary
		st.session_state[ 'df_details' ] = df_details
		st.session_state[ 'df_comparison' ] = df_comparison
		st.session_state[ 'df_performance' ] = df_performance
		st.session_state[ 'json_report' ] = json_report
		st.session_state[ 'markdown_report' ] = markdown_report
		st.session_state[ 'verification_complete' ] = True
		st.session_state[ 'selected_report_index' ] = 0
		
		progress_bar.progress( 100 )
		status_text.success( 'Batch verification complete.' )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'run_manifest_batch_verification( *args ) -> None'
		Logger( ).write( error )
		st.error( f'Batch verification failed: {e}' )
		st.session_state[ 'verification_complete' ] = False

def run_manual_fallback_verification( application: LabelApplication,
		uploaded_files: List[ object ] ) -> None:
	"""Run single-application fallback verification when no manifest is supplied.

	Purpose:
		This function saves uploaded artwork to a temporary directory, verifies every saved file
		against one manually supplied ``LabelApplication``, builds display/export outputs, and
		stores results in Streamlit session state.

	Args:
		application (LabelApplication): Manual expected application values.
		uploaded_files (List[object]): Uploaded label artwork files.

	Returns:
		None.
	"""
	try:
		cfg.throw_if( 'application', application )
		cfg.throw_if( 'uploaded_files', uploaded_files )
		
		verifier = AlcoholLabelVerifier( )
		writer = ReportWriter( )
		
		with tempfile.TemporaryDirectory( ) as temp_dir:
			file_paths = save_uploaded_files( uploaded_files, temp_dir )
			batch_report = verifier.verify_files( application, file_paths )
		
		df_summary = writer.batch_to_summary_dataframe( batch_report )
		df_details = writer.batch_to_detail_dataframe( batch_report )
		df_comparison = create_batch_comparison_dataframe( batch_report )
		
		result = BatchProcessingResult(
			batch_report=batch_report,
			processed_files=[
					report.file_name
					for report in batch_report.reports
			]
		)
		
		st.session_state[ 'batch_result' ] = result
		st.session_state[ 'batch_report' ] = batch_report
		st.session_state[ 'summary_dataframe' ] = df_summary
		st.session_state[ 'detail_dataframe' ] = df_details
		st.session_state[ 'comparison_dataframe' ] = df_comparison
		st.session_state[ 'performance_dataframe' ] = pd.DataFrame( )
		st.session_state[ 'json_report' ] = writer.batch_to_json( batch_report )
		st.session_state[ 'markdown_report' ] = writer.batch_to_markdown( batch_report )
		st.session_state[ 'verification_complete' ] = True
		st.session_state[ 'selected_report_index' ] = 0
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'run_manual_fallback_verification( application: LabelApplication, uploaded_files: List[object] ) -> None'
		Logger( ).write( error )
		st.error( f'Manual fallback verification failed: {e}' )
		st.session_state[ 'verification_complete' ] = False

# ==========================================================================================
# Processing Controller
# ==========================================================================================

def get_uploaded_file_names( uploaded_files: List[ object ] ) -> List[ str ]:
	"""Return uploaded artwork file names, including supported ZIP members.

	Args:
		uploaded_files (List[object]): Uploaded label artwork files.

	Returns:
		List[str]: Uploaded or archived artwork file names.
	"""
	try:
		if not uploaded_files:
			return [ ]
		
		file_names = [ ]
		
		for uploaded_file in uploaded_files:
			if is_zip_upload( uploaded_file ):
				file_names.extend( get_archive_member_file_names( uploaded_file ) )
				continue
			
			file_name = getattr( uploaded_file, 'name', '' )
			
			if file_name and is_supported_artwork_name( file_name ):
				file_names.append( file_name )
		
		return file_names
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_uploaded_file_names( uploaded_files: List[object] ) -> List[str]'
		Logger( ).write( error )
		return [ ]

def get_manifest_expected_file_names( ) -> List[ str ]:
	"""Return expected label artwork file names from loaded manifest records.

	Returns:
		List[str]: Expected manifest file names.
	"""
	try:
		records = st.session_state.get( 'manifest_records', [ ] )
		
		if not records:
			return [ ]
		
		file_names = [ ]
		
		for record in records:
			file_name = str( get_record_value( record, 'file_name', '' ) ).strip( )
			
			if file_name:
				file_names.append( file_name )
		
		return file_names
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_manifest_expected_file_names( ) -> List[str]'
		Logger( ).write( error )
		return [ ]

def get_manifest_file_match_summary( uploaded_files: List[ object ] ) -> Dict[ str, object ]:
	"""Compare manifest expected file names against uploaded artwork file names.

	Purpose:
		This function calculates expected, uploaded, matched, missing, and extra file names. It is
		used by readiness checks and Advanced Mode diagnostic display.

	Args:
		uploaded_files (List[object]): Uploaded label artwork files.

	Returns:
		Dict[str, object]: Manifest/upload file matching summary.
	"""
	try:
		expected_names = get_manifest_expected_file_names( )
		uploaded_names = get_uploaded_file_names( uploaded_files )
		
		expected_set = set( expected_names )
		uploaded_set = set( uploaded_names )
		
		matched_files = sorted( expected_set.intersection( uploaded_set ) )
		missing_files = sorted( expected_set.difference( uploaded_set ) )
		extra_files = sorted( uploaded_set.difference( expected_set ) )
		
		return {
				'expected_files': expected_names,
				'uploaded_files': uploaded_names,
				'matched_files': matched_files,
				'missing_files': missing_files,
				'extra_files': extra_files,
				'matched_count': len( matched_files ),
				'missing_count': len( missing_files ),
				'extra_count': len( extra_files )
		}
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_manifest_file_match_summary( uploaded_files: List[object] ) -> Dict[str, object]'
		Logger( ).write( error )
		return {
				'expected_files': [ ],
				'uploaded_files': [ ],
				'matched_files': [ ],
				'missing_files': [ ],
				'extra_files': [ ],
				'matched_count': 0,
				'missing_count': 0,
				'extra_count': 0
		}

def has_minimum_cav_application_data( application: LabelApplication ) -> bool:
	"""Determine whether manual CAV values are sufficient for artwork verification.

	Purpose:
		This readiness helper requires brand name, class/type, ABV, net contents, producer/bottler,
		and government warning. It is used only for the manual CAV plus artwork workflow when no
		manifest is uploaded.

	Args:
		application (LabelApplication): CAV application data.

	Returns:
		bool: ``True`` when minimum manual-review fields are populated; otherwise, ``False``.
	"""
	try:
		if not application:
			return False
		
		required_values = [
				application.brand_name,
				application.class_type,
				application.alcohol_content,
				application.net_contents,
				application.producer_bottler,
				application.government_warning
		]
		
		return all( value is not None and str( value ).strip( ) for value in required_values )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'has_minimum_cav_application_data( application: LabelApplication ) -> bool'
		Logger( ).write( error )
		return False

def get_processing_mode( uploaded_manifest: object, uploaded_files: List[ object ],
		application: LabelApplication ) -> str:
	"""Determine the active Fiddy processing mode.

	Args:
		uploaded_manifest (object): Uploaded manifest file.
		uploaded_files (List[object]): Uploaded label artwork files.
		application (LabelApplication): CAV application data.

	Returns:
		str: Processing mode name.
	"""
	try:
		has_manifest = uploaded_manifest is not None
		has_artwork = bool( uploaded_files )
		
		if has_manifest and has_artwork:
			return 'Manifest + Artwork Batch'
		
		if not has_manifest and has_artwork and has_minimum_cav_application_data( application ):
			return 'Manual CAV + Artwork Review'
		
		return 'Not Ready'
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_processing_mode( uploaded_manifest: object, uploaded_files: List[object], application: LabelApplication ) -> str'
		Logger( ).write( error )
		return 'Not Ready'

def get_processing_readiness( uploaded_manifest: object, uploaded_files: List[ object ],
		application: LabelApplication ) -> Dict[ str, object ]:
	"""Determine whether verification can run and explain readiness status.

	Purpose:
		This function evaluates the active upload and application-data state, identifies the
		processing mode, checks manifest record availability, checks artwork presence, checks
		manifest/artwork filename matching, and verifies required manual CAV fields for the manual
		workflow.

	Args:
		uploaded_manifest (object): Uploaded manifest file.
		uploaded_files (List[object]): Uploaded label artwork files.
		application (LabelApplication): CAV application data.

	Returns:
		Dict[str, object]: Processing readiness information with readiness flag, mode, message,
		and file matching summary.
	"""
	try:
		has_manifest = uploaded_manifest is not None
		has_artwork = bool( uploaded_files )
		records = st.session_state.get( 'manifest_records', [ ] )
		mode = get_processing_mode( uploaded_manifest, uploaded_files, application )
		
		if has_manifest and not records:
			return {
					'is_ready': False,
					'mode': 'Not Ready',
					'message': 'The manifest is uploaded, but no valid manifest records were loaded.',
					'match_summary': get_manifest_file_match_summary( uploaded_files )
			}
		
		if has_manifest and not has_artwork:
			return {
					'is_ready': False,
					'mode': 'Not Ready',
					'message': 'Upload matching label artwork files to run the manifest batch.',
					'match_summary': get_manifest_file_match_summary( uploaded_files )
			}
		
		if has_manifest and has_artwork:
			match_summary = get_manifest_file_match_summary( uploaded_files )
			
			if int( match_summary.get( 'matched_count', 0 ) ) <= 0:
				return {
						'is_ready': False,
						'mode': 'Not Ready',
						'message': (
								'No uploaded label artwork filenames match the manifest file_name '
								'values.'
						),
						'match_summary': match_summary
				}
			
			return {
					'is_ready': True,
					'mode': mode,
					'message': 'Ready to run manifest-driven batch verification.',
					'match_summary': match_summary
			}
		
		if not has_manifest and not has_artwork:
			return {
					'is_ready': False,
					'mode': 'Not Ready',
					'message': 'Upload label artwork to enable manual CAV verification.',
					'match_summary': get_manifest_file_match_summary( uploaded_files )
			}
		
		if not has_manifest and has_artwork and not has_minimum_cav_application_data( application ):
			return {
					'is_ready': False,
					'mode': 'Not Ready',
					'message': (
							'Complete the required CAV fields before running manual artwork '
							'verification.'
					),
					'match_summary': get_manifest_file_match_summary( uploaded_files )
			}
		
		return {
				'is_ready': True,
				'mode': mode,
				'message': 'Ready to run manual CAV artwork verification.',
				'match_summary': get_manifest_file_match_summary( uploaded_files )
		}
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_processing_readiness( uploaded_manifest: object, uploaded_files: List[object], application: LabelApplication ) -> Dict[str, object]'
		Logger( ).write( error )
		return {
				'is_ready': False,
				'mode': 'Not Ready',
				'message': f'Processing readiness could not be determined: {e}',
				'match_summary': get_manifest_file_match_summary( uploaded_files )
		}

def display_processing_readiness( readiness: Dict[ str, object ] ) -> None:
	"""Display processing mode, readiness status, and matching details.

	Purpose:
		This function displays a compact readiness message in all modes and, when Advanced Mode is
		active, displays manifest-file matching metrics and expandable lists of missing or extra
		files.

	Args:
		readiness (Dict[str, object]): Processing readiness information.

	Returns:
		None.
	"""
	try:
		mode = str( readiness.get( 'mode', 'Not Ready' ) )
		message = str( readiness.get( 'message', '' ) )
		is_ready = bool( readiness.get( 'is_ready', False ) )
		match_summary = readiness.get( 'match_summary', { } )
		
		status = 'Ready' if is_ready else 'Not Ready'
		
		st.caption( f'Processing Mode: {mode}' )
		
		if is_ready:
			st.success( f'{status}: {message}' )
		else:
			st.warning( f'{status}: {message}' )
		
		if st.session_state.get( 'simple_mode', True ):
			return
		
		if match_summary and match_summary.get( 'expected_files', [ ] ):
			match_columns = st.columns( 3 )
			
			match_columns[ 0 ].metric(
				'Manifest Files',
				len( match_summary.get( 'expected_files', [ ] ) )
			)
			
			match_columns[ 1 ].metric(
				'Matched Files',
				int( match_summary.get( 'matched_count', 0 ) )
			)
			
			match_columns[ 2 ].metric(
				'Missing Files',
				int( match_summary.get( 'missing_count', 0 ) )
			)
			
			missing_files = match_summary.get( 'missing_files', [ ] )
			extra_files = match_summary.get( 'extra_files', [ ] )
			
			if missing_files:
				with st.expander( 'Missing Manifest Files', expanded=False ):
					for file_name in missing_files:
						st.write( f'- {file_name}' )
			
			if extra_files:
				with st.expander( 'Extra Uploaded Files', expanded=False ):
					for file_name in extra_files:
						st.write( f'- {file_name}' )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'display_processing_readiness( readiness: Dict[str, object] ) -> None'
		Logger( ).write( error )
		st.warning( f'Unable to display processing readiness: {e}' )

def display_keyboard_accessibility_notes( ) -> None:
	"""Display keyboard navigation guidance for reviewer workflows.

	Purpose:
		Provide visible keyboard guidance that does not depend on mouse-hover behavior. The note
		supports the accessibility requirement by telling reviewers how to traverse controls,
		activate buttons, move backward, and reach downloads using standard keyboard operations.

	

	Returns:
		None.
	"""
	try:
		if not bool( st.session_state.get( 'show_keyboard_notes', True ) ):
			return
		
		st.markdown(
			"""
			<div class="fiddy-keyboard-note">
				<strong>Keyboard access:</strong> Press <strong>Tab</strong> to move through uploads,
				buttons, tables, and downloads. Press <strong>Shift + Tab</strong> to move backward.
				Press <strong>Enter</strong> or <strong>Space</strong> to activate the selected button.
				Visible blue outlines show the active control.
			</div>
			""",
			unsafe_allow_html=True
		)
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'display_keyboard_accessibility_notes( ) -> None'
		Logger( ).write( error )
		return None

# ==========================================================================================
# Display Panels
# ==========================================================================================

def display_upload_panel( ) -> Tuple[ object, List[ object ] ]:
	"""Display manifest and label artwork upload controls.

	Purpose:
		Render the first workflow panel and return the uploaded manifest CSV plus the uploaded
		artwork files. The artwork uploader accepts individual supported image/PDF files and ZIP
		archives. Upload widget keys include the application reset token so the Reset Application
		control can clear uploaded files on rerun.

	Returns:
		Tuple[object, List[object]]: Uploaded manifest and uploaded label files.
	"""
	st.markdown(
		"""
		<div class="fiddy-panel">
			<div class="fiddy-panel-title">1. Upload Application Data and Label Artwork</div>
			<div class="fiddy-panel-text">
				Upload a manifest CSV and matching label artwork. If no manifest is uploaded,
				Fiddy uses the CAV form values for manual review.
			</div>
		</div>
		""",
		unsafe_allow_html=True
	)
	
	reset_token = int( st.session_state.get( 'app_reset_token', 0 ) )
	left_column, right_column = st.columns( [ 0.45, 0.55 ] )
	
	with left_column:
		uploaded_manifest = st.file_uploader(
			'Application Manifest CSV',
			type=[ 'csv' ],
			accept_multiple_files=False,
			key=f'application_manifest_csv_upload_{reset_token}',
			help='CSV should include file_name, brand_name, class_type, beverage_type, '
			     'alcohol_content, net_contents, producer_bottler, and optional fields.'
		)
	
	with right_column:
		uploaded_files = st.file_uploader(
			'Label Artwork Files or ZIP Archive',
			type=get_supported_upload_type_values( ),
			accept_multiple_files=True,
			key=f'label_artwork_files_upload_{reset_token}',
			help='Upload individual image/PDF files or a ZIP archive containing image/PDF labels.'
		)
	
	return uploaded_manifest, uploaded_files or [ ]

def display_upload_preview( uploaded_manifest: object, uploaded_files: List[ object ] ) -> None:
	"""Display manifest and uploaded-file previews in Advanced Mode.

	Purpose:
		This function displays a manifest preview and uploaded artwork summary only when Simple Mode
		is disabled. Empty or unreadable manifests produce a warning, while file previews include
		individual uploads and supported ZIP members.

	Args:
		uploaded_manifest (object): Uploaded manifest file.
		uploaded_files (List[object]): Uploaded label files.

	Returns:
		None.
	"""
	try:
		if st.session_state.get( 'simple_mode', True ):
			return
		
		if uploaded_manifest:
			df_manifest = st.session_state.get( 'manifest_dataframe', pd.DataFrame( ) )
			
			if df_manifest.empty:
				st.warning( 'Manifest preview unavailable: CSV is empty or could not be read.' )
			else:
				st.subheader( 'Manifest Preview' )
				st.dataframe( df_manifest.head( 20 ), use_container_width=True, hide_index=True )
		
		if uploaded_files:
			st.subheader( 'Uploaded Label Artwork Preview' )
			st.dataframe(
				create_uploaded_file_dataframe( uploaded_files ),
				use_container_width=True,
				hide_index=True
			)
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'display_upload_preview( uploaded_manifest: object, uploaded_files: List[object] ) -> None'
		Logger( ).write( error )
		st.warning( f'Upload preview unavailable: {e}' )

def display_processing_controls( uploaded_manifest: object, uploaded_files: List[ object ],
		application: LabelApplication ) -> None:
	"""Display the unified processing controller.

	Purpose:
		Render readiness guidance, reviewer action buttons, and workflow dispatch logic for both
		manifest-driven and manual CAV verification. Simple Mode hides technical worker and SLA
		controls to preserve a low-navigation reviewer experience, while Advanced Mode exposes
		those controls for testing and tuning.

	Args:
		uploaded_manifest (object): Uploaded manifest file.
		uploaded_files (List[object]): Uploaded label files.
		application (LabelApplication): CAV application values.

	Returns:
		None.
	"""
	st.markdown(
		"""
		<div class="fiddy-panel">
			<div class="fiddy-panel-title">2. Run Verification</div>
			<div class="fiddy-panel-text">
				Confirm readiness and run local OCR/rule verification. Processing runs locally without
				external OCR or AI endpoints.
			</div>
		</div>
		""",
		unsafe_allow_html=True
	)
	
	readiness = get_processing_readiness( uploaded_manifest, uploaded_files, application )
	display_processing_readiness( readiness )
	
	simple_mode = bool( st.session_state.get( 'simple_mode', True ) )
	max_workers = int( getattr( cfg, 'MAX_PARALLEL_WORKERS', 4 ) )
	sla_seconds = float( getattr( cfg, 'LABEL_PROCESSING_SLA_SECONDS', 5.0 ) )
	
	if simple_mode:
		left_column, right_column = st.columns( [ 0.50, 0.50 ] )
		
		with left_column:
			run_button = st.button(
				'Run Verification',
				type='primary',
				disabled=not bool( readiness.get( 'is_ready', False ) ),
				use_container_width=True,
				key='simple_run_verification_button'
			)
		
		with right_column:
			clear_button = st.button(
				'Clear Results',
				use_container_width=True,
				key='simple_clear_results_button'
			)
	else:
		col1, col2, col3, col4 = st.columns( [ 0.22, 0.22, 0.28, 0.28 ] )
		
		with col1:
			max_workers = st.number_input(
				'Workers',
				min_value=1,
				max_value=int( getattr( cfg, 'MAX_PARALLEL_WORKERS', 8 ) ),
				value=min( 4, int( getattr( cfg, 'MAX_PARALLEL_WORKERS', 4 ) ) ),
				step=1,
				help='Parallel workers for batch processing.',
				key='advanced_max_workers_input'
			)
		
		with col2:
			sla_seconds = st.number_input(
				'SLA Seconds',
				min_value=1.0,
				max_value=30.0,
				value=float( getattr( cfg, 'LABEL_PROCESSING_SLA_SECONDS', 5.0 ) ),
				step=0.5,
				help='Per-label processing target.',
				key='advanced_sla_seconds_input'
			)
		
		with col3:
			run_button = st.button(
				'Run Verification',
				type='primary',
				disabled=not bool( readiness.get( 'is_ready', False ) ),
				use_container_width=True,
				key='advanced_run_verification_button'
			)
		
		with col4:
			clear_button = st.button(
				'Clear Results',
				use_container_width=True,
				key='advanced_clear_results_button'
			)
	
	if clear_button:
		clear_results( )
		st.rerun( )
	
	if not run_button:
		return
	
	st.session_state[ 'processing_status_message' ] = 'Starting verification.'
	st.session_state[ 'processing_status_history' ] = [ 'Starting verification.' ]
	mode = str( readiness.get( 'mode', 'Not Ready' ) )
	
	if mode == 'Manifest + Artwork Batch':
		run_manifest_batch_verification(
			uploaded_manifest=uploaded_manifest,
			uploaded_files=uploaded_files,
			max_workers=int( max_workers ),
			sla_seconds=float( sla_seconds )
		)
		return
	
	if mode == 'Manual CAV + Artwork Review':
		run_manual_fallback_verification( application, uploaded_files )
		return

def display_batch_dashboard( ) -> None:
	"""Display batch-level metrics and Advanced Mode diagnostics.

	Purpose:
		This function shows file, failure, warning, review, and SLA breach metrics after
		verification completes. Advanced Mode also displays manifest validation and performance
		summary records, plus expandable error, warning, and per-file performance detail.

	Returns:
		None.
	"""
	batch_report = st.session_state[ 'batch_report' ]
	batch_result = st.session_state[ 'batch_result' ]
	total_files, failures, warnings, reviews, sla_breaches = get_batch_metrics( batch_report,
		batch_result )
	
	st.markdown(
		"""
		<div class="fiddy-panel">
			<div class="fiddy-panel-title">3. Batch Dashboard</div>
			<div class="fiddy-panel-text">
				Review the batch status, failed checks, warnings, human-review items, and SLA
				breaches.
			</div>
		</div>
		""",
		unsafe_allow_html=True )
	
	col1, col2, col3, col4, col5 = st.columns( 5 )
	col1.metric( 'Files Reviewed', total_files )
	col2.metric( 'Failures', failures )
	col3.metric( 'Warnings', warnings )
	col4.metric( 'Needs Review', reviews )
	col5.metric( 'SLA Breaches', sla_breaches )
	
	if st.session_state.get( 'simple_mode', True ):
		return
	
	validation_record = batch_result.validation_result.to_record( )
	performance_record = batch_result.performance_summary.to_record( )
	
	left_column, right_column = st.columns( 2 )
	
	with left_column:
		st.subheader( 'Manifest Validation' )
		st.data_editor(
			pd.DataFrame( [ validation_record ] ),
			use_container_width=True,
			hide_index=True
		)
		
		if batch_result.validation_result.errors:
			with st.expander( 'Manifest Errors', expanded=False ):
				for error in batch_result.validation_result.errors:
					st.error( error )
		
		if batch_result.validation_result.warnings:
			with st.expander( 'Manifest Warnings', expanded=False ):
				for warning in batch_result.validation_result.warnings:
					st.warning( warning )
	
	with right_column:
		st.subheader( 'Performance Summary' )
		st.data_editor(
			pd.DataFrame( [ performance_record ] ),
			use_container_width=True,
			hide_index=True
		)
		
		if not st.session_state[ 'performance_dataframe' ].empty:
			with st.expander( 'Per-File Performance', expanded=False ):
				st.data_editor(
					st.session_state[ 'performance_dataframe' ],
					use_container_width=True,
					hide_index=True
				)

def get_comparison_status_icon( status: str ) -> str:
	"""Return a compact status icon and label for comparison tables.

	Args:
		status (str): Rule status value.

	Returns:
		str: Display-ready status value.
	"""
	try:
		cfg.throw_if( 'status', status )
		
		if status == STATUS_PASS:
			return '✅ Match'
		
		if status == STATUS_FAIL:
			return '❌ Mismatch'
		
		if status == STATUS_WARNING:
			return '⚠️ Warning'
		
		if status == STATUS_REVIEW:
			return '⚠️ Needs Review'
		
		return status
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_comparison_status_icon( status: str ) -> str'
		Logger( ).write( error )
		return '⚠️ Needs Review'

def get_reviewer_action( status: str, severity: str ) -> str:
	"""Return a reviewer-facing action statement based on status and severity.

	Args:
		status (str): Rule status value.
		severity (str): Rule severity value.

	Returns:
		str: Recommended reviewer action.
	"""
	try:
		cfg.throw_if( 'status', status )
		
		if status == STATUS_PASS:
			return 'No action required.'
		
		if status == STATUS_FAIL:
			return 'Correct the application, request corrected artwork, or escalate for review.'
		
		if status == STATUS_WARNING:
			return 'Review the field and confirm whether the variation is acceptable.'
		
		if status == STATUS_REVIEW:
			return 'Human review required before final determination.'
		
		return 'Review the field before final determination.'
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_reviewer_action( status: str, severity: str ) -> str'
		Logger( ).write( error )
		return 'Human review required before final determination.'

def get_tooltip_text( field_name: str, expected: object, observed: object, message: str,
		evidence: str ) -> str:
	"""Create a tooltip-ready explanation for one comparison row.

	Purpose:
			The tooltip combines field name, application value, extracted value, rule explanation, and
			OCR evidence into one compact text string suitable for detail captions and exported
			comparison records.

	Args:
		field_name (str): Reviewer-facing field name.
		expected (object): Application-side expected value.
		observed (object): Label-side observed value.
		message (str): Rule explanation message.
		evidence (str): OCR evidence or extracted context.

	Returns:
		str: Tooltip-ready explanation text.
	"""
	try:
		cfg.throw_if( 'field_name', field_name )
		
		expected_text = str( expected or '' ).strip( )
		observed_text = str( observed or '' ).strip( )
		message_text = str( message or '' ).strip( )
		evidence_text = str( evidence or '' ).strip( )
		
		parts = [
				f'Field: {field_name}',
				f'Application value: {expected_text or "Not provided"}',
				f'Extracted value: {observed_text or "Not detected"}'
		]
		
		if message_text:
			parts.append( f'Explanation: {message_text}' )
		
		if evidence_text:
			parts.append( f'Evidence: {evidence_text}' )
		
		return ' | '.join( parts )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_tooltip_text( field_name: str, expected: object, observed: object, message: str, evidence: str ) -> str'
		Logger( ).write( error )
		return 'Reviewer should inspect this field manually.'

def get_result_explanation_record( report: LabelVerificationReport, result: object ) -> Dict[ str, object ]:
	"""Create one enriched side-by-side comparison record.


	Purpose:
			This function combines a rule result with structured extracted-label fields when available.
			It produces a reviewer-facing row containing application value, extracted value, status,
			severity, confidence, explanation, recommended action, and detailed tooltip text.

	Args:
		report (LabelVerificationReport): Verification report containing the rule result.
		result (object): Rule result to convert.

	Returns:
		Dict[str, object]: Enriched side-by-side comparison record.
	"""
	try:
		cfg.throw_if( 'report', report )
		cfg.throw_if( 'result', result )
		
		field_name = result.field_name
		expected = result.expected
		observed = result.observed
		status = result.status
		severity = result.severity
		confidence = result.confidence
		message = result.message
		evidence = result.evidence
		
		extracted_fields = report.extracted_label.to_extracted_field_map( )
		structured_observed = extracted_fields.get( field_name, '' )
		
		if structured_observed is not None and str( structured_observed ).strip( ):
			observed = structured_observed
		
		return {
				'File Name': report.file_name,
				'Field': field_name,
				'Application': expected,
				'Extracted': observed,
				'Status': get_comparison_status_icon( status ),
				'Severity': severity,
				'Confidence': round( float( confidence or 0.0 ), 1 ),
				'Explanation': message,
				'Reviewer Action': get_reviewer_action( status, severity ),
				'Tooltip': get_tooltip_text( field_name, expected, observed, message, evidence )
		}
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_result_explanation_record( report: LabelVerificationReport, result: object ) -> Dict[str, object]'
		Logger( ).write( error )
		return {
				'File Name': report.file_name if report else '',
				'Field': '',
				'Application': '',
				'Extracted': '',
				'Status': '⚠️ Needs Review',
				'Severity': '',
				'Confidence': 0.0,
				'Explanation': 'Comparison record could not be created.',
				'Reviewer Action': 'Human review required before final determination.',
				'Tooltip': 'Reviewer should inspect this field manually.'
		}

def create_side_by_side_comparison_dataframe( report: LabelVerificationReport ) -> pd.DataFrame:
	"""Create a side-by-side comparison table from one verification report.

	Purpose:
		This function converts each rule result into an enriched comparison record and drops the
		file-name column for single-report display. Empty reports return an empty DataFrame with the
		expected comparison columns.

	Args:
		report (LabelVerificationReport): Verification report to convert.

	Returns:
		pd.DataFrame: Side-by-side comparison table.
	"""
	try:
		cfg.throw_if( 'report', report )
		
		records = [
				get_result_explanation_record( report, result )
				for result in report.results
		]
		
		if not records:
			return pd.DataFrame(
				columns=[
						'Field',
						'Application',
						'Extracted',
						'Status',
						'Severity',
						'Confidence',
						'Explanation',
						'Reviewer Action',
						'Tooltip'
				]
			)
		
		df_comparison = pd.DataFrame( records )
		
		if 'File Name' in df_comparison.columns:
			df_comparison = df_comparison.drop( columns=[ 'File Name' ] )
		
		return df_comparison
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'create_side_by_side_comparison_dataframe( report: LabelVerificationReport ) -> pd.DataFrame'
		Logger( ).write( error )
		return pd.DataFrame(
			columns=[
					'Field',
					'Application',
					'Extracted',
					'Status',
					'Severity',
					'Confidence',
					'Explanation',
					'Reviewer Action',
					'Tooltip'
			]
		)

def get_display_comparison_dataframe( df_comparison: pd.DataFrame ) -> pd.DataFrame:
	"""Return the reviewer-facing comparison DataFrame without internal columns.

	Purpose:
		This function removes internal tooltip/detail columns before display while preserving those
		values in the underlying comparison DataFrame for Advanced Mode explanation cards and CSV
		downloads.

	Args:
		df_comparison (pd.DataFrame): Source comparison DataFrame.

	Returns:
		pd.DataFrame: Display-safe comparison DataFrame.
	"""
	try:
		if df_comparison is None or df_comparison.empty:
			return pd.DataFrame( )
		
		drop_columns = [
				'Tooltip'
		]
		
		display_dataframe = df_comparison.copy( )
		
		for column in drop_columns:
			if column in display_dataframe.columns:
				display_dataframe = display_dataframe.drop( columns=[ column ] )
		
		return display_dataframe
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_display_comparison_dataframe( df_comparison: pd.DataFrame ) -> pd.DataFrame'
		Logger( ).write( error )
		return pd.DataFrame( )

def display_side_by_side_comparison_table( report: LabelVerificationReport ) -> None:
	"""Display one report's side-by-side comparison table.

	Purpose:
		This function creates and displays the reviewer-facing comparison table for a selected
		report. In Advanced Mode, it also displays mismatch explanation cards containing evidence,
		reviewer action, and tooltip detail for flagged fields.

	Args:
		report (LabelVerificationReport): Verification report to display.

	Returns:
		None.
	"""
	try:
		cfg.throw_if( 'report', report )
		
		df_comparison = create_side_by_side_comparison_dataframe( report )
		df_display = get_display_comparison_dataframe( df_comparison )
		
		st.markdown(
			"""
			<div class="fiddy-panel">
				<div class="fiddy-panel-title">Side-by-Side Comparison Table</div>
				<div class="fiddy-panel-text">
					Compare application values against extracted label values.
				</div>
			</div>
			""",
			unsafe_allow_html=True
		)
		
		if df_display.empty:
			st.info( 'No side-by-side comparison records are available for this label.' )
			return
		
		st.data_editor(
			df_display,
			use_container_width=True,
			hide_index=True,
			column_config={
					'Field': st.column_config.TextColumn(
						'Field',
						width='medium',
						help='The label field being checked.'
					),
					'Application': st.column_config.TextColumn(
						'Application',
						width='large',
						help='Expected value from the CAV application or manifest.'
					),
					'Extracted': st.column_config.TextColumn(
						'Extracted',
						width='large',
						help='Structured extracted value when available; otherwise OCR/rule observation.'
					),
					'Status': st.column_config.TextColumn(
						'Status',
						width='medium',
						help='Match, mismatch, warning, or needs-review status.'
					),
					'Severity': st.column_config.TextColumn(
						'Severity',
						width='small',
						help='Relative review significance.'
					),
					'Confidence': st.column_config.NumberColumn(
						'Confidence',
						format='%.1f',
						width='small',
						help='Rule confidence score.'
					),
					'Explanation': st.column_config.TextColumn(
						'Explanation',
						width='large',
						help='Plain-language explanation of the rule result.'
					),
					'Reviewer Action': st.column_config.TextColumn(
						'Reviewer Action',
						width='large',
						help='Recommended reviewer action for this result.'
					)
			}
		)
		
		if st.session_state.get( 'simple_mode', True ):
			return
		
		df_flagged = df_comparison[
			df_comparison[ 'Status' ].astype( str ).str.contains(
				'Mismatch|Warning|Needs Review',
				case=False,
				na=False
			)
		]
		
		if not df_flagged.empty:
			with st.expander( 'Mismatch Explanation Cards', expanded=False ):
				for _, row in df_flagged.iterrows( ):
					st.markdown( f"**{row.get( 'Field', '' )} — {row.get( 'Status', '' )}**" )
					st.write( row.get( 'Explanation', '' ) )
					st.caption( f"Application: {row.get( 'Application', '' )}" )
					st.caption( f"Extracted: {row.get( 'Extracted', '' )}" )
					st.caption( f"Reviewer Action: {row.get( 'Reviewer Action', '' )}" )
					
					tooltip_text = str( row.get( 'Tooltip', '' ) ).strip( )
					
					if tooltip_text:
						st.caption( f'Detail: {tooltip_text}' )
					
					st.divider( )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'display_side_by_side_comparison_table( report: LabelVerificationReport ) -> None'
		Logger( ).write( error )
		st.warning( f'Unable to display side-by-side comparison table: {e}' )

def create_batch_comparison_dataframe( batch_report: BatchVerificationReport ) -> pd.DataFrame:
	"""Create a batch-level side-by-side comparison DataFrame.

	Purpose:
		This function converts every rule result in every batch report into enriched comparison
		rows. The file name is retained for batch-level display and export.

	Args:
		batch_report (BatchVerificationReport): Batch verification report to convert.

	Returns:
		pd.DataFrame: Batch-level side-by-side comparison DataFrame.
	"""
	try:
		cfg.throw_if( 'batch_report', batch_report )
		
		records = [ ]
		
		for report in batch_report.reports:
			for result in report.results:
				records.append( get_result_explanation_record( report, result ) )
		
		if not records:
			return pd.DataFrame(
				columns=[
						'File Name',
						'Field',
						'Application',
						'Extracted',
						'Status',
						'Severity',
						'Confidence',
						'Explanation',
						'Reviewer Action',
						'Tooltip'
				]
			)
		
		return pd.DataFrame( records )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'create_batch_comparison_dataframe( batch_report: BatchVerificationReport ) -> pd.DataFrame'
		Logger( ).write( error )
		return pd.DataFrame(
			columns=[
					'File Name',
					'Field',
					'Application',
					'Extracted',
					'Status',
					'Severity',
					'Confidence',
					'Explanation',
					'Reviewer Action',
					'Tooltip'
			]
		)

def get_image_diagnostic_status( report: LabelVerificationReport ) -> str:
	"""Determine OCR and image diagnostic status for one label report.

	Args:
		report (LabelVerificationReport): Verification report to inspect.

	Returns:
		str: Diagnostic status.
	"""
	try:
		cfg.throw_if( 'report', report )
		
		if not report.extracted_label.has_text( ):
			return STATUS_REVIEW
		
		if report.extracted_label.image_quality_notes:
			return STATUS_WARNING
		
		return STATUS_PASS
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_image_diagnostic_status( report: LabelVerificationReport ) -> str'
		Logger( ).write( error )
		return STATUS_REVIEW

def get_image_diagnostic_recommendation( report: LabelVerificationReport ) -> str:
	"""Return a reviewer-facing recommendation based on OCR diagnostics.

	Purpose:
		This function inspects OCR text presence and image-quality notes to provide a practical
		action recommendation for clearer artwork, manual review, improved lighting, sharper focus,
		deskewing, or higher resolution.

	Args:
		report (LabelVerificationReport): Verification report to inspect.

	Returns:
		str: Recommended reviewer action.
	"""
	try:
		cfg.throw_if( 'report', report )
		
		if not report.extracted_label.has_text( ):
			return (
					'Request clearer artwork or manually review the submitted label because OCR '
					'did not return readable text.'
			)
		
		notes = report.extracted_label.image_quality_notes
		
		if not notes:
			return 'No image-quality issues were reported by the OCR preprocessing pipeline.'
		
		note_text = ' '.join( notes ).lower( )
		
		if 'glare' in note_text or 'overexposure' in note_text:
			return (
					'Review the label manually or request a new image with reduced glare and more '
					'even lighting.'
			)
		
		if 'contrast' in note_text or 'dark' in note_text or 'brightness' in note_text:
			return (
					'Review the label manually or request a better-lit image with stronger text '
					'contrast.'
			)
		
		if 'blur' in note_text or 'sharp' in note_text:
			return (
					'Review the label manually or request a sharper image captured with better '
					'focus.'
			)
		
		if 'skew' in note_text or 'angle' in note_text or 'orientation' in note_text:
			return (
					'Review the label manually or request a straighter image with less rotation or '
					'perspective distortion.'
			)
		
		if 'small' in note_text or 'resolution' in note_text or 'resize' in note_text:
			return (
					'Review the label manually or request a higher-resolution image so OCR can '
					'read small text.'
			)
		
		return 'Review the OCR output and image-quality notes before making a final determination.'
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'get_image_diagnostic_recommendation( report: LabelVerificationReport ) -> str'
		Logger( ).write( error )
		return 'Human review is recommended because image diagnostics could not be evaluated.'

def create_image_diagnostics_dataframe( report: LabelVerificationReport ) -> pd.DataFrame:
	"""Create a structured image and OCR diagnostics DataFrame.

	Purpose:
		This function converts one report's OCR status, OCR engine, OCR timing, and image-quality
		notes into reviewer-facing diagnostic records.

	Args:
		report (LabelVerificationReport): Verification report to convert.

	Returns:
		pd.DataFrame: Image diagnostics DataFrame.
	"""
	try:
		cfg.throw_if( 'report', report )
		
		status = get_image_diagnostic_status( report )
		recommendation = get_image_diagnostic_recommendation( report )
		has_text = report.extracted_label.has_text( )
		notes = report.extracted_label.image_quality_notes
		
		records = [
				{
						'Diagnostic': 'OCR Text Found',
						'Status': get_comparison_status_icon(
							STATUS_PASS if has_text else STATUS_REVIEW
						),
						'Value': 'Yes' if has_text else 'No',
						'Reviewer Guidance': recommendation
				},
				{
						'Diagnostic': 'OCR Engine',
						'Status': get_comparison_status_icon( status ),
						'Value': report.extracted_label.ocr_engine or 'Not reported',
						'Reviewer Guidance': 'Confirm OCR output before relying on automated checks.'
				},
				{
						'Diagnostic': 'OCR Seconds',
						'Status': get_comparison_status_icon( status ),
						'Value': round( float( report.extracted_label.ocr_seconds or 0.0 ), 3 ),
						'Reviewer Guidance': 'Longer timing may indicate large files or preprocessing overhead.'
				}
		]
		
		if notes:
			for index, note in enumerate( notes, start=1 ):
				records.append(
					{
							'Diagnostic': f'Image Quality Note {index}',
							'Status': get_comparison_status_icon( STATUS_WARNING ),
							'Value': note,
							'Reviewer Guidance': recommendation
					}
				)
		else:
			records.append(
				{
						'Diagnostic': 'Image Quality Notes',
						'Status': get_comparison_status_icon( STATUS_PASS ),
						'Value': 'No image-quality notes reported.',
						'Reviewer Guidance': recommendation
				}
			)
		
		return pd.DataFrame( records )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'create_image_diagnostics_dataframe( report: LabelVerificationReport ) -> pd.DataFrame'
		Logger( ).write( error )
		return pd.DataFrame(
			columns=[
					'Diagnostic',
					'Status',
					'Value',
					'Reviewer Guidance'
			]
		)

def display_image_diagnostics_panel( report: LabelVerificationReport ) -> None:
	"""Display OCR and image-quality diagnostics for one selected label report.

	Purpose:
		This function shows diagnostic status, OCR text presence, OCR seconds, diagnostic records,
		and a reviewer-facing recommendation. It is displayed only through Advanced Mode report
		detail.

	Args:
		report (LabelVerificationReport): Verification report to display.

	Returns:
		None.
	"""
	try:
		cfg.throw_if( 'report', report )
		
		df_diagnostics = create_image_diagnostics_dataframe( report )
		status = get_image_diagnostic_status( report )
		recommendation = get_image_diagnostic_recommendation( report )
		
		st.markdown(
			"""
			<div class="fiddy-panel">
				<div class="fiddy-panel-title">Image and OCR Diagnostics</div>
				<div class="fiddy-panel-text">
					Review OCR readability, processing metadata, and image-quality notes before
					making a final determination.
				</div>
			</div>
			""",
			unsafe_allow_html=True
		)
		
		status_column, text_column, time_column = st.columns( [ 0.34, 0.33, 0.33 ] )
		
		with status_column:
			st.metric( 'Diagnostic Status', status )
		
		with text_column:
			st.metric(
				'OCR Text Found',
				'Yes' if report.extracted_label.has_text( ) else 'No'
			)
		
		with time_column:
			st.metric(
				'OCR Seconds',
				round( float( report.extracted_label.ocr_seconds or 0.0 ), 3 )
			)
		
		if df_diagnostics.empty:
			st.info( 'No image diagnostics are available for this label.' )
		else:
			st.dataframe(
				df_diagnostics,
				use_container_width=True,
				hide_index=True,
				column_config={
						'Diagnostic': st.column_config.TextColumn(
							'Diagnostic',
							width='medium',
							help='Image or OCR diagnostic item.'
						),
						'Status': st.column_config.TextColumn(
							'Status',
							width='medium',
							help='Diagnostic status.'
						),
						'Value': st.column_config.TextColumn(
							'Value',
							width='large',
							help='Diagnostic value or note.'
						),
						'Reviewer Guidance': st.column_config.TextColumn(
							'Reviewer Guidance',
							width='large',
							help='Recommended reviewer action.'
						)
				}
			)
		
		st.info( recommendation )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'display_image_diagnostics_panel( report: LabelVerificationReport ) -> None'
		Logger( ).write( error )
		st.warning( f'Unable to display image diagnostics: {e}' )

def display_report_detail( report: LabelVerificationReport ) -> None:
	"""Display one report's comparison and optional technical detail.

	Purpose:
		This function displays the selected label header, side-by-side comparison table, and, in
		Advanced Mode, image diagnostics, rule-by-rule explanations, extracted OCR text, and the
		reviewer disclaimer.

	Args:
		report (LabelVerificationReport): Verification report to display.

	Returns:
		None.
	"""
	try:
		cfg.throw_if( 'report', report )
		
		st.markdown(
			f"""
            <div class="fiddy-panel">
                <div class="fiddy-panel-title">Selected Label: {report.file_name}</div>
                <div class="fiddy-panel-text">
                    Overall Status: {get_status_html( report.overall_status )}
                </div>
            </div>
            """,
			unsafe_allow_html=True
		)
		
		display_side_by_side_comparison_table( report )
		
		if st.session_state.get( 'simple_mode', True ):
			return
		
		display_image_diagnostics_panel( report )
		
		with st.expander( 'Rule-by-Rule Explanation', expanded=False ):
			for result in report.results:
				st.markdown( f'**{result.field_name} — {result.status}**' )
				st.write( result.message )
				st.caption( f'Expected: {result.expected}' )
				st.caption( f'Observed: {result.observed}' )
				st.caption( f'Confidence: {result.confidence:.1f}' )
				st.caption(
					f'Reviewer Action: {get_reviewer_action( result.status, result.severity )}' )
				
				if result.evidence:
					st.code( result.evidence, language='text' )
				
				st.divider( )
		
		with st.expander( 'Extracted Label Text', expanded=False ):
			st.text_area(
				'OCR Text',
				value=report.extracted_label.raw_text or 'No OCR text extracted.',
				height=250,
				disabled=True
			)
		
		with st.expander( 'Reviewer Disclaimer', expanded=False ):
			st.write( report.reviewer_disclaimer )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'display_report_detail( report: LabelVerificationReport ) -> None'
		Logger( ).write( error )
		st.warning( f'Unable to display report details: {e}' )

def display_results_viewer( ) -> None:
	"""Display verification results, selected-label review, and downloads.

	Purpose:
		This function displays the batch summary table, batch comparison table, optional rule detail
		table, selected flagged label review, and download controls after verification completes.
		Simple Mode hides technical rule-detail output.

	Returns:
		None.
	"""
	batch_report = st.session_state[ 'batch_report' ]
	df_summary = st.session_state[ 'summary_dataframe' ]
	df_details = st.session_state[ 'detail_dataframe' ]
	df_comparison = st.session_state[ 'comparison_dataframe' ]
	df_display_comparison = get_display_comparison_dataframe( df_comparison )
	
	st.success( 'Verification complete. Review the findings below.' )
	
	with st.expander( 'Batch Summary Table', expanded=True ):
		if df_summary.empty:
			st.info( 'No summary records are available.' )
		else:
			st.dataframe( df_summary, use_container_width=True, hide_index=True )
	
	with st.expander( 'Side-by-Side Comparison Table', expanded=True ):
		if df_display_comparison.empty:
			st.info( 'No side-by-side comparison records are available.' )
		else:
			st.dataframe(
				df_display_comparison,
				use_container_width=True,
				hide_index=True,
				column_config={
						'File Name': st.column_config.TextColumn(
							'File Name',
							width='medium',
							help='Uploaded label artwork filename.'
						),
						'Field': st.column_config.TextColumn(
							'Field',
							width='medium',
							help='The label field being checked.'
						),
						'Application': st.column_config.TextColumn(
							'Application',
							width='large',
							help='Expected value from CAV data or manifest.'
						),
						'Extracted': st.column_config.TextColumn(
							'Extracted',
							width='large',
							help='Structured extracted value when available; otherwise OCR/rule observation.'
						),
						'Status': st.column_config.TextColumn(
							'Status',
							width='medium',
							help='Match, mismatch, warning, or needs-review status.'
						),
						'Severity': st.column_config.TextColumn(
							'Severity',
							width='small',
							help='Relative review significance.'
						),
						'Confidence': st.column_config.NumberColumn(
							'Confidence',
							format='%.1f',
							width='small',
							help='Rule confidence score.'
						),
						'Explanation': st.column_config.TextColumn(
							'Explanation',
							width='large',
							help='Plain-language explanation of the rule result.'
						),
						'Reviewer Action': st.column_config.TextColumn(
							'Reviewer Action',
							width='large',
							help='Recommended reviewer action.'
						)
				}
			)
	
	if not st.session_state.get( 'simple_mode', True ):
		with st.expander( 'Rule Detail Table', expanded=False ):
			if df_details.empty:
				st.info( 'No rule detail records are available.' )
			else:
				st.dataframe( df_details, use_container_width=True, hide_index=True )
	
	if batch_report.reports:
		flagged_reports = [
				report
				for report in batch_report.reports
				if report.overall_status in (STATUS_FAIL, STATUS_WARNING, STATUS_REVIEW)
		]
		
		report_source = flagged_reports if flagged_reports else batch_report.reports
		report_names = [
				report.file_name
				for report in report_source
		]
		
		selected_name = st.selectbox(
			'Review flagged label',
			options=report_names,
			index=min( st.session_state[ 'selected_report_index' ], len( report_names ) - 1 )
		)
		
		selected_index = report_names.index( selected_name )
		st.session_state[ 'selected_report_index' ] = selected_index
		display_report_detail( report_source[ selected_index ] )
	
	display_downloads( )

def display_downloads( ) -> None:
	"""Display redacted verification report download controls.

	Purpose:
		Render reviewer-facing download controls while enforcing the Fiddy no-persistence policy.
		Summary, comparison, detail, and performance DataFrames are serialized through
		``DataRetentionPolicy`` before download. Raw OCR text, extracted label values,
		application values, local file paths, and detailed evidence text are redacted by default.
		Operational evidence such as status, severity, confidence, timing, and reviewer action
		categories remains available.

	Returns:
		None.
	"""
	try:
		policy = DataRetentionPolicy( )
		df_summary = st.session_state.get( 'summary_dataframe', pd.DataFrame( ) )
		df_details = st.session_state.get( 'detail_dataframe', pd.DataFrame( ) )
		df_comparison = st.session_state.get( 'comparison_dataframe', pd.DataFrame( ) )
		df_performance = st.session_state.get( 'performance_dataframe', pd.DataFrame( ) )
		json_report = st.session_state.get( 'json_report', '{}' )
		markdown_report = st.session_state.get( 'markdown_report', '' )
		csv_summary = policy.dataframe_to_csv( df_summary )
		csv_details = policy.dataframe_to_csv( df_details )
		csv_comparison = policy.dataframe_to_csv( df_comparison )
		csv_performance = policy.dataframe_to_csv( df_performance )
		
		st.subheader( 'Downloads' )
		
		if policy.no_persistence_mode:
			st.caption(
				'No-persistence mode is active. Download files are redacted and exclude raw OCR text, '
				'extracted label values, application values, local file paths, and detailed evidence text.'
			)
		else:
			st.caption( 'Download verification outputs for the current run.' )
		
		col1, col2, col3, col4, col5, col6 = st.columns( 6 )
		
		col1.download_button(
			label='Summary CSV',
			data=csv_summary,
			file_name='fiddy_summary_redacted.csv',
			mime='text/csv',
			disabled=df_summary.empty or not bool( csv_summary ),
			use_container_width=True
		)
		
		col2.download_button(
			label='Comparison CSV',
			data=csv_comparison,
			file_name='fiddy_comparison_redacted.csv',
			mime='text/csv',
			disabled=df_comparison.empty or not bool( csv_comparison ),
			use_container_width=True
		)
		
		col3.download_button(
			label='Details CSV',
			data=csv_details,
			file_name='fiddy_details_redacted.csv',
			mime='text/csv',
			disabled=df_details.empty or not bool( csv_details ),
			use_container_width=True
		)
		
		col4.download_button( label='Performance CSV',
			data=csv_performance,
			file_name='fiddy_performance.csv',
			mime='text/csv',
			disabled=df_performance.empty or not bool( csv_performance ),
			use_container_width=True )
		
		col5.download_button( label='JSON Report',
			data=json_report,
			file_name='fiddy_report_redacted.json',
			mime='application/json',
			disabled=not bool( json_report ) or json_report == '{}',
			use_container_width=True )
		
		col6.download_button( label='Markdown Report',
			data=markdown_report, file_name='fiddy_report_redacted.md',
			mime='text/markdown',
			disabled=not bool( markdown_report ),
			use_container_width=True )
		
		with st.expander( 'No-Persistence Policy', expanded=False ):
			st.dataframe( policy.to_dataframe( ), use_container_width=True, hide_index=True )
	except Exception as e:
		error = Error( e )
		error.cause = 'Application'
		error.module = __name__
		error.method = 'display_downloads( ) -> None'
		Logger( ).write( error )
		st.warning( f'Download controls could not be displayed: {e}' )

def display_methodology_expander( ) -> None:
	"""Display methodology and safeguard notes in Advanced Mode.

	Purpose:
		This function explains the local OCR approach, deterministic rules, fuzzy matching, strict
		warning handling, image-quality risk scoring, SLA tracking, and reviewer responsibility. It
		is intentionally hidden in Simple Mode.

	Returns:
		None.
	"""
	if not st.session_state[ 'simple_mode' ]:
		with st.expander( 'Methodology and Safeguards', expanded=False ):
			st.write(
				'Fiddy uses local OCR, deterministic rules, fuzzy matching for judgment-sensitive '
				'comparisons, strict government-warning validation, image-quality risk scoring, '
				'and batch-level SLA tracking.'
			)
			
			st.markdown(
				"""
				- No external OCR or AI endpoint is required.
				- OCR failures and low-readability images produce review flags.
				- Near-match warning text does not pass automatically.
				- Batch processing isolates per-file failures.
				- Final determinations remain with authorized reviewers.
				"""
			)

def display_simple_workflow( uploaded_manifest: object, uploaded_files: List[ object ] ) -> None:
	"""Display the streamlined reviewer workflow for Simple Mode.

	Purpose:
		Render the low-navigation reviewer workflow consisting of upload, application/manifest
		data review, synchronized label artwork preview, run verification, and review results.
		Technical processing controls, manifest previews, diagnostics, methodology, and raw rule
		tables remain hidden unless Advanced Mode is selected.

	Args:
		uploaded_manifest (object): Uploaded manifest file.
		uploaded_files (List[object]): Uploaded label artwork files.

	Returns:
		None.
	"""
	display_keyboard_accessibility_notes( )
	application = create_simple_label_application( uploaded_manifest, uploaded_files )
	display_processing_controls( uploaded_manifest, uploaded_files, application )
	
	if st.session_state[ 'verification_complete' ]:
		display_batch_dashboard( )
		display_results_viewer( )

def display_advanced_workflow( uploaded_manifest: object, uploaded_files: List[ object ] ) -> None:
	"""Display the full reviewer workflow for Advanced Mode.

	Purpose:
		Render the full CAV form, upload preview, processing controls, dashboard, results content,
		diagnostics, rule detail, downloads, and methodology material for testing, tuning, and
		developer-level inspection.

	Args:
		uploaded_manifest (object): Uploaded manifest file.
		uploaded_files (List[object]): Uploaded label artwork files.

	Returns:
		None.
	"""
	display_keyboard_accessibility_notes( )
	application = create_manual_label_application( )
	display_upload_preview( uploaded_manifest, uploaded_files )
	display_processing_controls( uploaded_manifest, uploaded_files, application )
	
	if st.session_state[ 'verification_complete' ]:
		display_batch_dashboard( )
		display_results_viewer( )
	
	display_methodology_expander( )

# ==========================================================================================
# Main
# ==========================================================================================

def main( ) -> None:
	"""Run the Fiddy Streamlit application.

	Purpose:
		This function configures the page, initializes session state, renders sidebar controls,
		displays the header and upload panel, synchronizes manifest upload state, and routes the
		reviewer into Simple or Advanced workflow rendering based on the current review mode.

	Returns:
		None.
	"""
	configure_page( )
	initialize_session_state( )
	
	with st.sidebar:
		display_sidebar_header( )
	
	display_header( )
	
	uploaded_manifest, uploaded_files = display_upload_panel( )
	sync_manifest_upload_state( uploaded_manifest )
	
	if st.session_state.get( 'simple_mode', True ):
		display_simple_workflow( uploaded_manifest, uploaded_files )
	else:
		display_advanced_workflow( uploaded_manifest, uploaded_files )

if __name__ == '__main__':
	main( )