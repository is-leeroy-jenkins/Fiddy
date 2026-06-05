'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                label_verifier.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="label_verifier.py" company="Terry D. Eppler">

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
        label_verifier.py
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable, List

from config import throw_if
from src.constants import (
	FIELD_LABEL_TEXT,
	SEVERITY_HIGH,
	STATUS_REVIEW
)

from src.label_field_extractor import LabelFieldExtractor
from src.label_rules import AlcoholLabelRules
from src.models import (
	BatchVerificationReport,
	ExtractedLabel,
	LabelApplication,
	LabelCheckResult,
	LabelVerificationReport
)
from src.ocr_engine import OcrEngine

# ==========================================================================================
# Alcohol Label Verifier
# ==========================================================================================

class AlcoholLabelVerifier( ):
	"""
	Purpose:
	--------
	Coordinate OCR extraction, deterministic label-rule execution, report creation, and batch
	verification for uploaded alcohol label files.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
	"""
	
	_application: LabelApplication
	_file_path: Path
	_file_paths: List[ Path ]
	_extracted_label: ExtractedLabel
	_report: LabelVerificationReport
	_batch_report: BatchVerificationReport
	_rules: AlcoholLabelRules
	_ocr_engine: OcrEngine
	_started: float
	_processing_seconds: float
	_field_extractor: LabelFieldExtractor
	
	def __init__( self ) -> None:
		"""
		
			Purpose:
			--------
			Initialize the verifier with the local OCR engine, deterministic field extractor, and
			deterministic rule engine.
		
			Parameters:
			-----------
			None
		
			Returns:
			--------
			None
			
		"""
		self._ocr_engine = OcrEngine( )
		self._field_extractor = LabelFieldExtractor( )
		self._rules = AlcoholLabelRules( )
	
	def create_ocr_review_result( self, extracted_label: ExtractedLabel ) -> LabelCheckResult:
		"""
		Purpose:
		--------
		Create a human-review result when OCR does not produce usable label text.

		Parameters:
		-----------
		extracted_label (ExtractedLabel): OCR extraction result for the uploaded file.

		Returns:
		--------
		LabelCheckResult: OCR review result.
		"""
		try:
			throw_if( 'extracted_label', extracted_label )
			self._extracted_label = extracted_label
			
			evidence = '; '.join( self._extracted_label.image_quality_notes )
			return LabelCheckResult(
				rule_id='ocr_text_extraction',
				field_name=FIELD_LABEL_TEXT,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Readable label text from uploaded artwork',
				observed='No readable OCR text was extracted',
				confidence=0.0,
				evidence=evidence,
				message=(
						'The uploaded label could not be read reliably by OCR. The label should be '
						'reviewed manually or resubmitted with clearer artwork.'
				),
				requires_human_review=True
			)
		except Exception:
			return LabelCheckResult(
				rule_id='ocr_text_extraction',
				field_name=FIELD_LABEL_TEXT,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Readable label text from uploaded artwork',
				observed='OCR review result could not be created',
				confidence=0.0,
				evidence='',
				message='OCR extraction failed and requires human review.',
				requires_human_review=True
			)
	
	def verify_extracted_label( self, application: LabelApplication,
			extracted_label: ExtractedLabel ) -> LabelVerificationReport:
		"""
			
			Purpose:
			--------
			Verify a previously extracted label against expected application data.
		
			Parameters:
			-----------
			application (LabelApplication): Expected application values entered by the reviewer.
			extracted_label (ExtractedLabel): OCR extraction result for the uploaded label.
		
			Returns:
			--------
			LabelVerificationReport: Complete verification report for the extracted label.
		
		"""
		try:
			throw_if( 'application', application )
			throw_if( 'extracted_label', extracted_label )
			
			self._application = application
			self._extracted_label = self.enrich_extracted_label( extracted_label )
			self._started = time.perf_counter( )
			
			self._report = LabelVerificationReport(
				file_name=self._extracted_label.file_name,
				application=self._application,
				extracted_label=self._extracted_label
			)
			
			if not self._extracted_label.has_text( ):
				self._report.add_result( self.create_ocr_review_result( self._extracted_label ) )
				self._report.processing_seconds = time.perf_counter( ) - self._started
				self._report.determine_overall_status( )
				return self._report
			
			results = self._rules.verify( self._application, self._extracted_label.raw_text )
			
			for result in results:
				self._report.add_result( result )
			
			self._report.processing_seconds = (
					self._extracted_label.ocr_seconds + time.perf_counter( ) - self._started
			)
			
			self._report.determine_overall_status( )
			return self._report
		except Exception:
			return LabelVerificationReport.empty(
				file_name=extracted_label.file_name if extracted_label else ''
			)
	
	def verify_file( self, application: LabelApplication,
			file_path: str | Path ) -> LabelVerificationReport:
		"""
		
			Purpose:
			--------
			Extract text and structured fields from one uploaded label file, then verify it against
			expected application data.
		
			Parameters:
			-----------
			application (LabelApplication): Expected application values entered by the reviewer.
			file_path (str | Path): Path to the uploaded label image or PDF file.
		
			Returns:
			--------
			LabelVerificationReport: Complete verification report for the uploaded label.
			
		"""
		try:
			throw_if( 'application', application )
			throw_if( 'file_path', file_path )
			
			self._application = application
			self._file_path = Path( file_path )
			self._extracted_label = self._ocr_engine.extract_text( self._file_path )
			self._extracted_label = self.enrich_extracted_label( self._extracted_label )
			
			return self.verify_extracted_label( self._application, self._extracted_label )
		except Exception:
			return LabelVerificationReport.empty( file_name=str( file_path ) )
	
	def verify_files( self, application: LabelApplication,
			file_paths: Iterable[ str | Path ] ) -> BatchVerificationReport:
		"""
		Purpose:
		--------
		Verify multiple uploaded label files against the same expected application data.

		Parameters:
		-----------
		application (LabelApplication): Expected application values entered by the reviewer.
		file_paths (Iterable[str | Path]): Uploaded label image or PDF file paths.

		Returns:
		--------
		BatchVerificationReport: Batch verification report containing one report per file.
		"""
		try:
			throw_if( 'application', application )
			throw_if( 'file_paths', file_paths )
			
			self._application = application
			self._file_paths = [ Path( file_path ) for file_path in file_paths ]
			self._batch_report = BatchVerificationReport( )
			
			for file_path in self._file_paths:
				report = self.verify_file( self._application, file_path )
				self._batch_report.add_report( report )
			
			return self._batch_report
		except Exception:
			return BatchVerificationReport(
				reports=[
						LabelVerificationReport.empty( file_name='Batch verification unavailable' )
				]
			)
	
	def verify_text( self, application: LabelApplication, text: str,
			file_name: str = 'manual_text_entry.txt' ) -> LabelVerificationReport:
		"""
		Purpose:
		--------
		Verify manually supplied label text without running OCR.

		Parameters:
		-----------
		application (LabelApplication): Expected application values entered by the reviewer.
		text (str): Manually supplied label text.
		file_name (str): Logical file name assigned to the text entry.

		Returns:
		--------
		LabelVerificationReport: Complete verification report for the supplied text.
		"""
		try:
			throw_if( 'application', application )
			throw_if( 'text', text )
			throw_if( 'file_name', file_name )
			
			self._application = application
			self._extracted_label = ExtractedLabel(
				file_name=file_name,
				file_type='txt',
				raw_text=text,
				normalized_text=text.casefold( ),
				ocr_engine='manual',
				ocr_seconds=0.0,
				image_quality_notes=[
						'Manual text verification path used; OCR was not executed.'
				]
			)
			
			return self.verify_extracted_label( self._application, self._extracted_label )
		except Exception:
			return LabelVerificationReport.empty( file_name=file_name )
	
	def summarize_report_status( self, report: LabelVerificationReport ) -> str:
		"""
		Purpose:
		--------
		Return a compact reviewer-facing status summary for one verification report.

		Parameters:
		-----------
		report (LabelVerificationReport): Verification report to summarize.

		Returns:
		--------
		str: Compact status summary.
		"""
		try:
			throw_if( 'report', report )
			self._report = report
			self._report.determine_overall_status( )
			
			failures = sum( result.is_failure( ) for result in self._report.results )
			warnings = sum( result.is_warning( ) for result in self._report.results )
			reviews = sum( result.is_review( ) for result in self._report.results )
			
			return (
					f'{self._report.overall_status}: '
					f'{failures} failures, {warnings} warnings, {reviews} review items'
			)
		except Exception:
			return 'Needs Review: report summary unavailable.'

