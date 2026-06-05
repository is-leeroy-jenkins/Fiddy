'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                report_writer.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="report_writer.py" company="Terry D. Eppler">

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
        Provides report conversion and export helpers for Fiddy verification results.

        This module converts single-label and batch verification reports into DataFrames,
        JSON, CSV, Markdown, default file names, status-count dictionaries, and optional
        UTF-8 text-file outputs for reviewer use and downstream testing.
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
from src.models import BatchVerificationReport, LabelVerificationReport

class ReportWriter( ):
	"""Convert Fiddy verification reports into display, export, and file formats.

	The ``ReportWriter`` class is the report-formatting service for single-label and batch
	verification outputs. It converts ``LabelVerificationReport`` and
	``BatchVerificationReport`` objects into summary DataFrames, detail DataFrames, formatted
	JSON, CSV text, reviewer-facing Markdown, timestamped default report names, and UTF-8 text
	files.

	The class intentionally avoids changing report contents. It delegates summary and detail
	record construction to the report models, then formats those records for display or export.
	When an existing guarded conversion path fails, the method logs structured Booger metadata
	and returns the same conservative fallback value used by the original source.

	Attributes:
		_report (LabelVerificationReport): Active single-label report being converted.
		_batch_report (BatchVerificationReport): Active batch report being converted.
		_records (List[Dict[str, Any]]): Generic record collection reserved for conversion flows.
		_summary_records (List[Dict[str, Any]]): Summary records used to build summary DataFrames.
		_detail_records (List[Dict[str, Any]]): Detail records used to build detail DataFrames.
		_output_path (Path): Destination path used by text-file writing.
		_df_summary (pd.DataFrame): Most recently generated summary DataFrame.
		_df_details (pd.DataFrame): Most recently generated detail DataFrame.
	"""
	
	_report: LabelVerificationReport
	_batch_report: BatchVerificationReport
	_records: List[ Dict[ str, Any ] ]
	_summary_records: List[ Dict[ str, Any ] ]
	_detail_records: List[ Dict[ str, Any ] ]
	_output_path: Path
	_df_summary: pd.DataFrame
	_df_details: pd.DataFrame
	
	def report_to_summary_dataframe( self, report: LabelVerificationReport ) -> pd.DataFrame:
		"""Convert one verification report into a one-row summary DataFrame.

		This method delegates summary-record construction to ``LabelVerificationReport`` and
		wraps the resulting one-row record in a pandas DataFrame. The output is intended for
		Streamlit summary display, batch-style single-report previews, CSV export, and tests that
		need a tabular summary shape.

		Args:
			report (LabelVerificationReport): Verification report to convert.

		Returns:
			pd.DataFrame: One-row report summary DataFrame. If conversion fails, the exception is
			logged and an empty DataFrame is returned.
		"""
		try:
			throw_if( 'report', report )
			
			self._report = report
			self._summary_records = [
					self._report.to_summary_record( )
			]
			
			self._df_summary = pd.DataFrame( self._summary_records )
			return self._df_summary
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'report_to_summary_dataframe( report: LabelVerificationReport ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def report_to_detail_dataframe( self, report: LabelVerificationReport ) -> pd.DataFrame:
		"""Convert one verification report into a rule-level detail DataFrame.

		This method delegates detail-record construction to ``LabelVerificationReport`` and
		builds a DataFrame containing one row per rule result. If the report contains no detail
		records, the method returns an empty DataFrame with the configured ``RESULT_COLUMNS`` so
		downstream display code can rely on a stable column schema.

		Args:
			report (LabelVerificationReport): Verification report to convert.

		Returns:
			pd.DataFrame: Rule-level detail DataFrame. If conversion fails, the exception is
			logged and an empty DataFrame with ``RESULT_COLUMNS`` is returned.
		"""
		try:
			throw_if( 'report', report )
			
			self._report = report
			self._detail_records = self._report.to_records( )
			self._df_details = pd.DataFrame( self._detail_records )
			
			if self._df_details.empty:
				return pd.DataFrame( columns=RESULT_COLUMNS )
			
			return self._df_details
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'report_to_detail_dataframe( report: LabelVerificationReport ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( columns=RESULT_COLUMNS )
	
	def batch_to_summary_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame:
		"""Convert a batch verification report into a summary DataFrame.

		This method delegates batch summary-record construction to ``BatchVerificationReport``
		and builds a DataFrame containing one row per label report in the batch. The output is
		intended for batch dashboards, summary tables, CSV export, and testing.

		Args:
			batch_report (BatchVerificationReport): Batch report to convert.

		Returns:
			pd.DataFrame: Batch summary DataFrame. If conversion fails, the exception is logged
			and an empty DataFrame is returned.
		"""
		try:
			throw_if( 'batch_report', batch_report )
			
			self._batch_report = batch_report
			self._summary_records = self._batch_report.to_summary_records( )
			self._df_summary = pd.DataFrame( self._summary_records )
			
			return self._df_summary
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'batch_to_summary_dataframe( batch_report: BatchVerificationReport ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def batch_to_detail_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame:
		"""Convert a batch verification report into a rule-level detail DataFrame.

		This method delegates detail-record construction to ``BatchVerificationReport`` and
		builds a DataFrame containing one row per rule result across all reports in the batch.
		If no rule detail records are available, the method returns an empty DataFrame with the
		configured ``RESULT_COLUMNS`` to preserve a stable output schema.

		Args:
			batch_report (BatchVerificationReport): Batch report to convert.

		Returns:
			pd.DataFrame: Batch detail DataFrame. If conversion fails, the exception is logged and
			an empty DataFrame with ``RESULT_COLUMNS`` is returned.
		"""
		try:
			throw_if( 'batch_report', batch_report )
			
			self._batch_report = batch_report
			self._detail_records = self._batch_report.to_detail_records( )
			self._df_details = pd.DataFrame( self._detail_records )
			
			if self._df_details.empty:
				return pd.DataFrame( columns=RESULT_COLUMNS )
			
			return self._df_details
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'batch_to_detail_dataframe( batch_report: BatchVerificationReport ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( columns=RESULT_COLUMNS )
	
	def report_to_json( self, report: LabelVerificationReport ) -> str:
		"""Convert one verification report to formatted JSON.

		This method uses Pydantic's ``model_dump_json`` method with indentation to produce a
		readable JSON representation of a single verification report. The output is suitable for
		download buttons, API testing, fixture generation, or audit-oriented review.

		Args:
			report (LabelVerificationReport): Verification report to convert.

		Returns:
			str: Formatted JSON report text. If conversion fails, the exception is logged and the
			original empty JSON object fallback is returned.
		"""
		try:
			throw_if( 'report', report )
			
			self._report = report
			return self._report.model_dump_json( indent=4 )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'report_to_json( report: LabelVerificationReport ) -> str'
			Logger( ).write( error )
			return '{}'
	
	def batch_to_json( self, batch_report: BatchVerificationReport ) -> str:
		"""Convert a batch verification report to formatted JSON.

		This method uses Pydantic's ``model_dump_json`` method with indentation to produce a
		readable JSON representation of a batch verification report. The output preserves nested
		report, extraction, application, and rule-result structure for downstream inspection.

		Args:
			batch_report (BatchVerificationReport): Batch report to convert.

		Returns:
			str: Formatted JSON report text. If conversion fails, the exception is logged and the
			original empty JSON object fallback is returned.
		"""
		try:
			throw_if( 'batch_report', batch_report )
			
			self._batch_report = batch_report
			return self._batch_report.model_dump_json( indent=4 )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'batch_to_json( batch_report: BatchVerificationReport ) -> str'
			Logger( ).write( error )
			return '{}'
	
	def dataframe_to_csv( self, df_data: pd.DataFrame ) -> str:
		"""Convert a DataFrame into CSV text without the DataFrame index.

		This method serializes a DataFrame using pandas ``to_csv`` with ``index=False`` so the
		result can be used in download buttons, report exports, or test fixtures without adding
		the pandas index column.

		Args:
			df_data (pd.DataFrame): DataFrame to convert.

		Returns:
			str: CSV text. If conversion fails, the exception is logged and an empty string is
			returned.
		"""
		try:
			throw_if( 'df_data', df_data )
			
			self._df_details = df_data
			return self._df_details.to_csv( index=False )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'dataframe_to_csv( df_data: pd.DataFrame ) -> str'
			Logger( ).write( error )
			return ''
	
	def report_to_markdown( self, report: LabelVerificationReport ) -> str:
		"""Convert one verification report into reviewer-facing Markdown.

		This method builds a Markdown report for one label verification result. The output
		includes report title, file metadata, overall status, creation time, processing seconds,
		application values, a rule-results table, extracted OCR text, and the reviewer
		disclaimer. Rule results are rendered through the detail DataFrame's Markdown conversion
		when available.

		Args:
			report (LabelVerificationReport): Verification report to convert.

		Returns:
			str: Markdown report text. If report generation fails, the exception is logged and the
			original reviewer-safe Markdown failure message is returned.
		"""
		try:
			throw_if( 'report', report )
			
			self._report = report
			self._report.determine_overall_status( )
			df_details = self.report_to_detail_dataframe( self._report )
			lines = [
					f'# Fiddy Label Verification Report',
					'',
					f'**File:** {self._report.file_name}',
					f'**Overall Status:** {self._report.overall_status}',
					f'**Created On:** {self._report.created_on.strftime( REPORT_DATE_FORMAT )}',
					f'**Processing Seconds:** {self._report.processing_seconds:.2f}',
					'',
					'## Application Values',
					'',
					f'- Brand Name: {self._report.application.brand_name}',
					f'- Class / Type: {self._report.application.class_type}',
					f'- Beverage Type: {self._report.application.beverage_type}',
					f'- Alcohol Content: {self._report.application.alcohol_content}',
					f'- Proof: {self._report.application.proof}',
					f'- Net Contents: {self._report.application.net_contents}',
					f'- Producer / Bottler: {self._report.application.producer_bottler}',
					f'- Imported: {self._report.application.imported}',
					f'- Importer: {self._report.application.importer}',
					f'- Country of Origin: {self._report.application.country_of_origin}',
					'',
					'## Rule Results',
					''
			]
			
			if df_details.empty:
				lines.append( 'No rule results were available.' )
			else:
				lines.append( df_details.to_markdown( index=False ) )
			
			lines.extend( [ '', '## Extracted Label Text', '', '```text',
			                self._report.extracted_label.raw_text or 'No OCR text extracted.', '```',
			                '',  '## Reviewer Disclaimer', '', self._report.reviewer_disclaimer ] )
			
			return '\n'.join( lines )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'report_to_markdown( report: LabelVerificationReport ) -> str'
			Logger( ).write( error )
			return '# Fiddy Label Verification Report\n\nReport generation failed.'
	
	def batch_to_markdown( self, batch_report: BatchVerificationReport ) -> str:
		"""Convert a batch verification report into reviewer-facing Markdown.

		This method builds a Markdown report for a batch verification result. The output includes
		batch title, creation time, total file count, aggregate failure/warning/review counts, a
		batch summary table, and a rule-detail table across all reports. Empty summary or detail
		DataFrames are rendered as reviewer-safe explanatory text.

		Args:
			batch_report (BatchVerificationReport): Batch report to convert.

		Returns:
			str: Markdown report text. If report generation fails, the exception is logged and the
			original batch Markdown failure message is returned.
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
			
			lines.extend( [
						'',
						'## Rule Details',
						''
				] )
			
			if df_details.empty:
				lines.append( 'No rule detail records were available.' )
			else:
				lines.append( df_details.to_markdown( index=False ) )
			
			return '\n'.join( lines )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'batch_to_markdown( batch_report: BatchVerificationReport ) -> str'
			Logger( ).write( error )
			return '# Fiddy Batch Verification Report\n\nBatch report generation failed.'
	
	def write_text_file( self, text: str, output_path: str | Path ) -> Path:
		"""Write text output to disk using UTF-8 encoding.

		This method validates the text and destination path, creates the destination directory
		when needed, and writes the supplied text using UTF-8 encoding. It is used for optional
		file outputs after Markdown, JSON, CSV, or other text serialization has already been
		created.

		Args:
			text (str): Text content to write.
			output_path (str | Path): Destination file path.

		Returns:
			Path: Written output path. If writing fails, the exception is logged and ``Path('')``
			is returned.
		"""
		try:
			throw_if( 'text', text )
			throw_if( 'output_path', output_path )
			
			self._output_path = Path( output_path )
			self._output_path.parent.mkdir( parents=True, exist_ok=True )
			self._output_path.write_text( text, encoding='utf-8' )
			
			return self._output_path
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'write_text_file( self, *args ) -> Path'
			Logger( ).write( error )
			return Path( '' )
	
	def create_default_report_name( self, suffix: str = 'md' ) -> str:
		"""Create a timestamped default report file name.

		This method creates a default report name using ``REPORT_FILENAME_PREFIX``, the current
		local timestamp in ``YYYYMMDD_HHMMSS`` format, and the supplied suffix. The suffix is
		expected to be provided without a leading period.

		Args:
			suffix (str): File extension without leading period.

		Returns:
			str: Default report file name. If name creation fails, the exception is logged and the
			original fallback text-file name is returned.
		"""
		try:
			throw_if( 'suffix', suffix )
			timestamp = datetime.now( ).strftime( '%Y%m%d_%H%M%S' )
			return f'{REPORT_FILENAME_PREFIX}_{timestamp}.{suffix}'
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_default_report_name( suffix: str ) -> str'
			Logger( ).write( error )
			return f'{REPORT_FILENAME_PREFIX}.txt'
	
	def get_status_counts( self, report: LabelVerificationReport ) -> Dict[ str, int ]:
		"""Return status counts for a single verification report.

		This method counts rule results by status value and adds the report-level overall status
		under the ``FIELD_OVERALL_STATUS`` key. The returned dictionary is useful for dashboard
		badges, quick summaries, tests, and report metadata.

		Args:
			report (LabelVerificationReport): Verification report to count.

		Returns:
			Dict[str, int]: Status counts keyed by status value, plus the overall status entry.
			If counting fails, the exception is logged and an empty dictionary is returned.
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
			error.method = 'get_status_counts( report: LabelVerificationReport ) -> Dict[str, int]'
			Logger( ).write( error )
			return { }