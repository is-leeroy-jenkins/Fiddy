'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                report_writer.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-07-2026
    ******************************************************************************************
    <copyright file="report_writer.py" company="Terry D. Eppler">

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
        Provides redacted report conversion and export helpers for Fiddy verification results.

        This module converts single-label and batch verification reports into summary
        DataFrames, detail DataFrames, JSON, CSV, Markdown, status-count dictionaries, default
        report names, and optional UTF-8 text-file outputs. All export paths are routed through
        the centralized data-retention policy so raw OCR text, extracted label values,
        application values, evidence text, and local file paths are redacted by default.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from booger import Error, Logger
from config import REPORT_DATE_FORMAT, REPORT_FILENAME_PREFIX, throw_if
from src.constants import FIELD_OVERALL_STATUS, RESULT_COLUMNS
from src.data_retention import DataRetentionPolicy
from src.models import BatchVerificationReport, LabelVerificationReport

class ReportWriter( ):
	"""Convert Fiddy verification reports into redacted display and export formats.

	Purpose:
		Provide report-formatting services for single-label and batch verification outputs. The
		writer converts ``LabelVerificationReport`` and ``BatchVerificationReport`` objects into
		summary DataFrames, detail DataFrames, redacted JSON, redacted CSV, reviewer-facing
		redacted Markdown, timestamped default report names, and policy-governed UTF-8 text
		files.

		The class preserves operational evidence such as status, severity, confidence,
		processing seconds, reviewer action categories, and aggregate counts while preventing
		long-term export of raw OCR text, extracted values, application values, local file paths,
		and detailed evidence text by default.

	Attributes:
		_report (LabelVerificationReport): Active single-label report being converted.
		_batch_report (BatchVerificationReport): Active batch report being converted.
		_records (List[Dict[str, Any]]): Generic record collection reserved for conversion flows.
		_summary_records (List[Dict[str, Any]]): Summary records used to build summary DataFrames.
		_detail_records (List[Dict[str, Any]]): Detail records used to build detail DataFrames.
		_output_path (Path): Destination path used by text-file writing.
		_df_summary (pd.DataFrame): Most recently generated summary DataFrame.
		_df_details (pd.DataFrame): Most recently generated detail DataFrame.
		_policy (DataRetentionPolicy): Active no-persistence and redaction policy.
	"""
	
	_report: LabelVerificationReport
	_batch_report: BatchVerificationReport
	_records: List[ Dict[ str, Any ] ]
	_summary_records: List[ Dict[ str, Any ] ]
	_detail_records: List[ Dict[ str, Any ] ]
	_output_path: Path
	_df_summary: pd.DataFrame
	_df_details: pd.DataFrame
	_policy: DataRetentionPolicy
	
	def __init__( self ) -> None:
		"""Initialize the report writer.

		Purpose:
			Create the centralized data-retention policy used by all report conversion and file
			output methods.

		Returns:
			None.
		"""
		self._policy = DataRetentionPolicy( )
	
	def report_to_summary_dataframe( self, report: LabelVerificationReport ) -> pd.DataFrame:
		"""Convert one verification report into a redacted one-row summary DataFrame.

		Purpose:
			Delegate summary-record construction to ``LabelVerificationReport``, build a
			DataFrame, and redact sensitive fields before returning the output for display or
			export.

		Args:
			report (LabelVerificationReport): Verification report to convert.

		Returns:
			pd.DataFrame: Redacted one-row report summary DataFrame. If conversion fails, an
			empty DataFrame is returned.
		"""
		try:
			throw_if( 'report', report )
			
			self._report = report
			self._summary_records = [
					self._report.to_summary_record( )
			]
			self._df_summary = pd.DataFrame( self._summary_records )
			
			return self._policy.redact_dataframe( self._df_summary )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'report_to_summary_dataframe( self, report: LabelVerificationReport ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def report_to_detail_dataframe( self, report: LabelVerificationReport ) -> pd.DataFrame:
		"""Convert one verification report into a redacted rule-level detail DataFrame.

		Purpose:
			Delegate detail-record construction to ``LabelVerificationReport``, build a DataFrame
			containing one row per rule result, and redact sensitive fields before returning the
			output. If no detail records exist, an empty DataFrame with ``RESULT_COLUMNS`` is
			returned.

		Args:
			report (LabelVerificationReport): Verification report to convert.

		Returns:
			pd.DataFrame: Redacted rule-level detail DataFrame. If conversion fails, an empty
			DataFrame with ``RESULT_COLUMNS`` is returned.
		"""
		try:
			throw_if( 'report', report )
			
			self._report = report
			self._detail_records = self._report.to_records( )
			self._df_details = pd.DataFrame( self._detail_records )
			
			if self._df_details.empty:
				return pd.DataFrame( columns=RESULT_COLUMNS )
			
			return self._policy.redact_dataframe( self._df_details )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'report_to_detail_dataframe( self, report: LabelVerificationReport ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( columns=RESULT_COLUMNS )
	
	def batch_to_summary_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame:
		"""Convert a batch verification report into a redacted summary DataFrame.

		Purpose:
			Delegate batch summary-record construction to ``BatchVerificationReport``, build a
			DataFrame containing one row per label report, and redact sensitive fields before
			returning the output for dashboards, downloads, or test evidence.

		Args:
			batch_report (BatchVerificationReport): Batch report to convert.

		Returns:
			pd.DataFrame: Redacted batch summary DataFrame. If conversion fails, an empty
			DataFrame is returned.
		"""
		try:
			throw_if( 'batch_report', batch_report )
			
			self._batch_report = batch_report
			self._summary_records = self._batch_report.to_summary_records( )
			self._df_summary = pd.DataFrame( self._summary_records )
			
			return self._policy.redact_dataframe( self._df_summary )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'batch_to_summary_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def batch_to_detail_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame:
		"""Convert a batch verification report into a redacted rule-level detail DataFrame.

		Purpose:
			Delegate detail-record construction to ``BatchVerificationReport``, build a DataFrame
			containing one row per rule result across all reports, and redact sensitive fields
			before returning the output.

		Args:
			batch_report (BatchVerificationReport): Batch report to convert.

		Returns:
			pd.DataFrame: Redacted batch detail DataFrame. If conversion fails, an empty DataFrame
			with ``RESULT_COLUMNS`` is returned.
		"""
		try:
			throw_if( 'batch_report', batch_report )
			
			self._batch_report = batch_report
			self._detail_records = self._batch_report.to_detail_records( )
			self._df_details = pd.DataFrame( self._detail_records )
			
			if self._df_details.empty:
				return pd.DataFrame( columns=RESULT_COLUMNS )
			
			return self._policy.redact_dataframe( self._df_details )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'batch_to_detail_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( columns=RESULT_COLUMNS )
	
	def report_to_json( self, report: LabelVerificationReport ) -> str:
		"""Convert one verification report to formatted redacted JSON.

		Purpose:
			Serialize a single verification report through ``DataRetentionPolicy`` so raw OCR
			text, extracted label values, application values, local file paths, and detailed
			evidence text are redacted by default.

		Args:
			report (LabelVerificationReport): Verification report to convert.

		Returns:
			str: Formatted redacted JSON report text. If conversion fails, an empty JSON object is
			returned.
		"""
		try:
			throw_if( 'report', report )
			
			self._report = report
			return self._policy.object_to_json( self._report )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'report_to_json( self, report: LabelVerificationReport ) -> str'
			Logger( ).write( error )
			return '{}'
	
	def batch_to_json( self, batch_report: BatchVerificationReport ) -> str:
		"""Convert a batch verification report to formatted redacted JSON.

		Purpose:
			Serialize a batch verification report through ``DataRetentionPolicy`` so nested raw
			OCR text, extracted label values, application values, local file paths, and detailed
			evidence text are redacted by default.

		Args:
			batch_report (BatchVerificationReport): Batch report to convert.

		Returns:
			str: Formatted redacted JSON report text. If conversion fails, an empty JSON object is
			returned.
		"""
		try:
			throw_if( 'batch_report', batch_report )
			
			self._batch_report = batch_report
			return self._policy.object_to_json( self._batch_report )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'batch_to_json( self, batch_report: BatchVerificationReport ) -> str'
			Logger( ).write( error )
			return '{}'
	
	def dataframe_to_csv( self, df_data: pd.DataFrame ) -> str:
		"""Convert a DataFrame into redacted CSV text.

		Purpose:
			Serialize a DataFrame through ``DataRetentionPolicy`` so sensitive values are
			redacted before CSV output is returned.

		Args:
			df_data (pd.DataFrame): DataFrame to convert.

		Returns:
			str: Redacted CSV text. If conversion fails, an empty string is returned.
		"""
		try:
			throw_if( 'df_data', df_data )
			
			self._df_details = df_data
			return self._policy.dataframe_to_csv( self._df_details )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'dataframe_to_csv( self, df_data: pd.DataFrame ) -> str'
			Logger( ).write( error )
			return ''
	
	def report_to_markdown( self, report: LabelVerificationReport ) -> str:
		"""Convert one verification report into reviewer-facing redacted Markdown.

		Purpose:
			Build a Markdown report for one label verification result while enforcing
			no-persistence behavior. Application values, extracted values, raw OCR text, local
			file paths, and detailed evidence text are redacted by default. Operational content
			such as overall status, processing seconds, rule status, severity, confidence, and
			human-review flags remains available.

		Args:
			report (LabelVerificationReport): Verification report to convert.

		Returns:
			str: Redacted Markdown report text. If report generation fails, a reviewer-safe
			failure message is returned.
		"""
		try:
			throw_if( 'report', report )
			
			self._report = report
			self._report.determine_overall_status( )
			df_details = self.report_to_detail_dataframe( self._report )
			file_name = self._policy.redact_value( self._report.file_name )
			raw_text = self._policy.redact_raw_ocr_text(
				self._report.extracted_label.raw_text or '' )
			
			lines = [
					'# Fiddy Label Verification Report',
					'',
					f'**File:** {file_name}',
					f'**Overall Status:** {self._report.overall_status}',
					f'**Created On:** {self._report.created_on.strftime( REPORT_DATE_FORMAT )}',
					f'**Processing Seconds:** {self._report.processing_seconds:.2f}',
					'',
					'## Application Values',
					'',
					'Application values are redacted by the Fiddy no-persistence policy.',
					'',
					'## Rule Results',
					''
			]
			
			if df_details.empty:
				lines.append( 'No rule results were available.' )
			else:
				lines.append( df_details.to_markdown( index=False ) )
			
			lines.extend(
				[
						'',
						'## Extracted Label Text',
						'',
						'```text',
						raw_text,
						'```',
						'',
						'## Data Retention Notice',
						'',
						'Raw OCR text, extracted label values, application values, local file paths, '
						'and detailed evidence text are redacted by default.',
						'',
						'## Reviewer Disclaimer',
						'',
						self._report.reviewer_disclaimer
				]
			)
			
			return '\n'.join( lines )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'report_to_markdown( self, report: LabelVerificationReport ) -> str'
			Logger( ).write( error )
			return '# Fiddy Label Verification Report\n\nReport generation failed.'
	
	def batch_to_markdown( self, batch_report: BatchVerificationReport ) -> str:
		"""Convert a batch verification report into reviewer-facing redacted Markdown.

		Purpose:
			Build a Markdown report for a batch verification result while enforcing
			no-persistence behavior. Summary and detail tables are redacted before rendering.
			Operational fields such as status, severity, confidence, counts, and timing are
			preserved.

		Args:
			batch_report (BatchVerificationReport): Batch report to convert.

		Returns:
			str: Redacted Markdown report text. If report generation fails, a reviewer-safe
			failure message is returned.
		"""
		try:
			throw_if( 'batch_report', batch_report )
			
			self._batch_report = batch_report
			df_summary = self.batch_to_summary_dataframe( self._batch_report )
			df_details = self.batch_to_detail_dataframe( self._batch_report )
			
			lines = [
					'# Fiddy Batch Verification Report',
					'',
					f'**Created On:** {self._batch_report.created_on.strftime( REPORT_DATE_FORMAT )}',
					f'**Total Files:** {self._batch_report.total_files( )}',
					f'**Files With Failures:** {self._batch_report.total_failures( )}',
					f'**Files With Warnings:** {self._batch_report.total_warnings( )}',
					f'**Files Requiring Review:** {self._batch_report.total_reviews( )}',
					'',
					'## Batch Summary',
					''
			]
			
			if df_summary.empty:
				lines.append( 'No batch summary records were available.' )
			else:
				lines.append( df_summary.to_markdown( index=False ) )
			
			lines.extend(
				[
						'',
						'## Rule Details',
						''
				]
			)
			
			if df_details.empty:
				lines.append( 'No rule detail records were available.' )
			else:
				lines.append( df_details.to_markdown( index=False ) )
			
			lines.extend(
				[
						'',
						'## Data Retention Notice',
						'',
						'Raw OCR text, extracted label values, application values, local file paths, '
						'and detailed evidence text are redacted by default.'
				]
			)
			
			return '\n'.join( lines )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'batch_to_markdown( self, batch_report: BatchVerificationReport ) -> str'
			Logger( ).write( error )
			return '# Fiddy Batch Verification Report\n\nBatch report generation failed.'
	
	def write_text_file( self, text: str, output_path: str | Path ) -> Path:
		"""Write text output using the active no-persistence policy.

		Purpose:
			Write text output only through ``DataRetentionPolicy`` so disk output follows the
			same retention policy used for JSON, CSV, and Markdown serialization. The caller is
			expected to pass already-redacted text.

		Args:
			text (str): Text content to write.
			output_path (str | Path): Destination file path.

		Returns:
			Path: Output path. If writing is disabled or fails, the destination path is returned
			when possible.
		"""
		try:
			throw_if( 'output_path', output_path )
			
			self._output_path = Path( output_path )
			return self._policy.write_text_file( text or '', self._output_path )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'write_text_file( self, *args ) -> Path'
			Logger( ).write( error )
			return Path( output_path )
	
	def create_default_report_name( self, suffix: str = 'md' ) -> str:
		"""Create a timestamped default report file name.

		Purpose:
			Create a default report name using ``REPORT_FILENAME_PREFIX``, the current local
			timestamp in ``YYYYMMDD_HHMMSS`` format, and the supplied suffix.

		Args:
			suffix (str): File extension without leading period.

		Returns:
			str: Default report file name. If name creation fails, a fallback text-file name is
			returned.
		"""
		try:
			throw_if( 'suffix', suffix )
			
			timestamp = datetime.now( ).strftime( '%Y%m%d_%H%M%S' )
			return f'{REPORT_FILENAME_PREFIX}_{timestamp}.{suffix}'
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_default_report_name( self, suffix: str = "md" ) -> str'
			Logger( ).write( error )
			return f'{REPORT_FILENAME_PREFIX}.txt'
	
	def get_status_counts( self, report: LabelVerificationReport ) -> Dict[ str, int ]:
		"""Return status counts for a single verification report.

		Purpose:
			Count rule results by status value and add the report-level overall status under the
			``FIELD_OVERALL_STATUS`` key. The returned dictionary supports dashboards, summaries,
			tests, and report metadata.

		Args:
			report (LabelVerificationReport): Verification report to count.

		Returns:
			Dict[str, int]: Status counts keyed by status value, plus the overall status entry. If
			counting fails, an empty dictionary is returned.
		"""
		try:
			throw_if( 'report', report )
			
			self._report = report
			counts = { }
			
			for result in self._report.results:
				counts[ result.status ] = counts.get( result.status, 0 ) + 1
			
			counts[ FIELD_OVERALL_STATUS ] = self._report.overall_status
			return counts
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_status_counts( self, report: LabelVerificationReport ) -> Dict[str, int]'
			Logger( ).write( error )
			return { }