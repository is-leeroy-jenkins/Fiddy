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
        report_writer.py
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from config import REPORT_DATE_FORMAT, REPORT_FILENAME_PREFIX, throw_if
from src.constants import FIELD_OVERALL_STATUS, RESULT_COLUMNS
from src.models import BatchVerificationReport, LabelVerificationReport

class ReportWriter( ):
	"""
	Purpose:
	--------
	Convert Fiddy verification reports into DataFrames, JSON, CSV, Markdown, and optional
	file outputs for reviewer use and downstream testing.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
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
		"""
		Purpose:
		--------
		Convert one verification report into a one-row summary DataFrame.

		Parameters:
		-----------
		report (LabelVerificationReport): Verification report to convert.

		Returns:
		--------
		pd.DataFrame: One-row report summary DataFrame.
		"""
		try:
			throw_if( 'report', report )
			
			self._report = report
			self._summary_records = [
					self._report.to_summary_record( )
			]
			
			self._df_summary = pd.DataFrame( self._summary_records )
			return self._df_summary
		except Exception:
			return pd.DataFrame( )
	
	def report_to_detail_dataframe( self, report: LabelVerificationReport ) -> pd.DataFrame:
		"""
		Purpose:
		--------
		Convert one verification report into a detail DataFrame containing one row per rule.

		Parameters:
		-----------
		report (LabelVerificationReport): Verification report to convert.

		Returns:
		--------
		pd.DataFrame: Rule-level detail DataFrame.
		"""
		try:
			throw_if( 'report', report )
			
			self._report = report
			self._detail_records = self._report.to_records( )
			self._df_details = pd.DataFrame( self._detail_records )
			
			if self._df_details.empty:
				return pd.DataFrame( columns=RESULT_COLUMNS )
			
			return self._df_details
		except Exception:
			return pd.DataFrame( columns=RESULT_COLUMNS )
	
	def batch_to_summary_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame:
		"""
		Purpose:
		--------
		Convert a batch verification report into a summary DataFrame.

		Parameters:
		-----------
		batch_report (BatchVerificationReport): Batch report to convert.

		Returns:
		--------
		pd.DataFrame: Batch summary DataFrame.
		"""
		try:
			throw_if( 'batch_report', batch_report )
			
			self._batch_report = batch_report
			self._summary_records = self._batch_report.to_summary_records( )
			self._df_summary = pd.DataFrame( self._summary_records )
			
			return self._df_summary
		except Exception:
			return pd.DataFrame( )
	
	def batch_to_detail_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame:
		"""
		Purpose:
		--------
		Convert a batch verification report into a rule-level detail DataFrame.

		Parameters:
		-----------
		batch_report (BatchVerificationReport): Batch report to convert.

		Returns:
		--------
		pd.DataFrame: Batch detail DataFrame.
		"""
		try:
			throw_if( 'batch_report', batch_report )
			
			self._batch_report = batch_report
			self._detail_records = self._batch_report.to_detail_records( )
			self._df_details = pd.DataFrame( self._detail_records )
			
			if self._df_details.empty:
				return pd.DataFrame( columns=RESULT_COLUMNS )
			
			return self._df_details
		except Exception:
			return pd.DataFrame( columns=RESULT_COLUMNS )
	
	def report_to_json( self, report: LabelVerificationReport ) -> str:
		"""
		Purpose:
		--------
		Convert one verification report to formatted JSON.

		Parameters:
		-----------
		report (LabelVerificationReport): Verification report to convert.

		Returns:
		--------
		str: JSON report text.
		"""
		try:
			throw_if( 'report', report )
			
			self._report = report
			return self._report.model_dump_json( indent=4 )
		except Exception:
			return '{}'
	
	def batch_to_json( self, batch_report: BatchVerificationReport ) -> str:
		"""
		Purpose:
		--------
		Convert a batch verification report to formatted JSON.

		Parameters:
		-----------
		batch_report (BatchVerificationReport): Batch report to convert.

		Returns:
		--------
		str: JSON report text.
		"""
		try:
			throw_if( 'batch_report', batch_report )
			
			self._batch_report = batch_report
			return self._batch_report.model_dump_json( indent=4 )
		except Exception:
			return '{}'
	
	def dataframe_to_csv( self, df_data: pd.DataFrame ) -> str:
		"""
		Purpose:
		--------
		Convert a DataFrame into CSV text without the DataFrame index.

		Parameters:
		-----------
		df_data (pd.DataFrame): DataFrame to convert.

		Returns:
		--------
		str: CSV text.
		"""
		try:
			throw_if( 'df_data', df_data )
			
			self._df_details = df_data
			return self._df_details.to_csv( index=False )
		except Exception:
			return ''
	
	def report_to_markdown( self, report: LabelVerificationReport ) -> str:
		"""
		Purpose:
		--------
		Convert one verification report into reviewer-facing Markdown.

		Parameters:
		-----------
		report (LabelVerificationReport): Verification report to convert.

		Returns:
		--------
		str: Markdown report text.
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
			
			lines.extend(
				[
						'',
						'## Extracted Label Text',
						'',
						'```text',
						self._report.extracted_label.raw_text or 'No OCR text extracted.',
						'```',
						'',
						'## Reviewer Disclaimer',
						'',
						self._report.reviewer_disclaimer
				]
			)
			
			return '\n'.join( lines )
		except Exception:
			return '# Fiddy Label Verification Report\n\nReport generation failed.'
	
	def batch_to_markdown( self, batch_report: BatchVerificationReport ) -> str:
		"""
		Purpose:
		--------
		Convert a batch verification report into reviewer-facing Markdown.

		Parameters:
		-----------
		batch_report (BatchVerificationReport): Batch report to convert.

		Returns:
		--------
		str: Markdown report text.
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
			
			return '\n'.join( lines )
		except Exception:
			return '# Fiddy Batch Verification Report\n\nBatch report generation failed.'
	
	def write_text_file( self, text: str, output_path: str | Path ) -> Path:
		"""
		
			Purpose:
			--------
			Write text output to disk using UTF-8 encoding.
	
			Parameters:
			-----------
			text (str): Text content to write.
			output_path (str | Path): Destination file path.
	
			Returns:
			--------
			Path: Written output path.
			
		"""
		try:
			throw_if( 'text', text )
			throw_if( 'output_path', output_path )
			
			self._output_path = Path( output_path )
			self._output_path.parent.mkdir( parents=True, exist_ok=True )
			self._output_path.write_text( text, encoding='utf-8' )
			
			return self._output_path
		except Exception:
			return Path( '' )
	
	def create_default_report_name( self, suffix: str = 'md' ) -> str:
		"""
		
			Purpose:
			--------
			Create a timestamped default report file name.
	
			Parameters:
			-----------
			suffix (str): File extension without leading period.
	
			Returns:
			--------
			str: Default report file name.
			
		"""
		try:
			throw_if( 'suffix', suffix )
			
			timestamp = datetime.now( ).strftime( '%Y%m%d_%H%M%S' )
			return f'{REPORT_FILENAME_PREFIX}_{timestamp}.{suffix}'
		except Exception:
			return f'{REPORT_FILENAME_PREFIX}.txt'
	
	def get_status_counts( self, report: LabelVerificationReport ) -> Dict[ str, int ]:
		"""
		
			Purpose:
			--------
			Return status counts for a single verification report.
	
			Parameters:
			-----------
			report (LabelVerificationReport): Verification report to count.
	
			Returns:
			--------
			Dict[str, int]: Status counts keyed by status value.
			
		"""
		try:
			throw_if( 'report', report )
			
			self._report = report
			counts = { }
			
			for result in self._report.results:
				counts[ result.status ] = counts.get( result.status, 0 ) + 1
			
			counts[ FIELD_OVERALL_STATUS ] = self._report.overall_status
			return counts
		except Exception:
			return { }
