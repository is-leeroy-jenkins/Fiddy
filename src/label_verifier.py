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

     THE SOFTWARE IS PROVIDED AS IS WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
     INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
     FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT.
     IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
     DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
     ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
     DEALINGS IN THE SOFTWARE.

     You can contact me at:  terryeppler@gmail.com

    </copyright>
    <summary>
        Coordinates OCR extraction, deterministic field enrichment, alcohol-label rule
        execution, verification report creation, batch verification, and reviewer-facing status
        summaries for the Fiddy label verification workflow.

        This module preserves reviewer-safe fallback behavior by logging structured Booger
        error metadata in guarded execution paths before returning conservative report objects
        or status messages.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable, List

from booger import Error, Logger
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

class AlcoholLabelVerifier( ):
	"""Coordinate OCR, rule execution, and verification report generation.

	The ``AlcoholLabelVerifier`` is the high-level service object used by the Fiddy
	application to process alcohol label artwork or manually supplied OCR text. It connects
	the local OCR engine, structured field extractor, deterministic rule engine, and
	verification report models without requiring the user interface to manage those components
	directly.

	The class supports three primary workflows. First, ``verify_file`` accepts one image or PDF
	path, extracts OCR text, enriches the extracted label, and verifies the label against the
	expected application data. Second, ``verify_files`` applies that same logic to a collection
	of uploaded files and returns a batch-level report. Third, ``verify_text`` bypasses OCR and
	verifies manually supplied label text, which supports testing, troubleshooting, and
	reviewer-entered text scenarios.

	The verifier uses conservative fallback behavior. Existing exception handlers return
	reviewer-safe report objects or status messages rather than propagating exceptions to the
	Streamlit interface. Each guarded failure path records structured Booger metadata before
	returning the original fallback value.

	Attributes:
		_application (LabelApplication): Expected application values for the active verification
			workflow.
		_file_path (Path): Path to the active label image or PDF file.
		_file_paths (List[Path]): Normalized paths used by the active batch workflow.
		_extracted_label (ExtractedLabel): OCR and structured extraction result currently being
			verified.
		_report (LabelVerificationReport): Report currently being constructed for one label.
		_batch_report (BatchVerificationReport): Batch report currently being constructed.
		_rules (AlcoholLabelRules): Deterministic rule engine used for compliance checks.
		_ocr_engine (OcrEngine): Local OCR engine used to extract label text.
		_started (float): ``time.perf_counter`` value used to measure verification time.
		_processing_seconds (float): Processing duration retained by the active workflow.
		_field_extractor (LabelFieldExtractor): Deterministic field extractor used during label
			enrichment.
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
		"""Initialize the verifier and its deterministic processing components.

		The constructor creates one local OCR engine, one deterministic field extractor, and one
		deterministic alcohol-label rules engine. These collaborators are reused by the instance
		for single-file, multi-file, and manual-text verification paths.

		No external service calls are made by this constructor. OCR backend configuration is
		delegated to ``OcrEngine`` and rule configuration is delegated to ``AlcoholLabelRules``.

		Returns:
			None.
		"""
		self._ocr_engine = OcrEngine( )
		self._field_extractor = LabelFieldExtractor( )
		self._rules = AlcoholLabelRules( )
	
	def create_ocr_review_result( self, extracted_label: ExtractedLabel ) -> LabelCheckResult:
		"""Create a human-review rule result for unusable OCR output.

		This method constructs the standard ``LabelCheckResult`` used when OCR completes but
		does not produce readable label text. The result intentionally marks the item as
		``Needs Review`` with high severity because the verifier cannot reliably execute
		text-based compliance checks without usable extracted text.

		Image-quality notes from the ``ExtractedLabel`` are joined into the result evidence
		field so reviewers can see why OCR may have failed, such as blur, glare, low contrast,
		skew, or other preprocessing diagnostics captured upstream.

		Args:
			extracted_label (ExtractedLabel): OCR extraction result for the uploaded label. The
				value is expected to contain image-quality notes and file metadata even when
				readable OCR text is unavailable.

		Returns:
			LabelCheckResult: A reviewer-facing OCR review result. If construction fails, the
			method logs the exception and returns a conservative fallback result that still
			requires human review.
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
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_ocr_review_result( self, *args ) -> LabelCheckResult'
			Logger( ).write( error )
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
		"""Verify an already extracted label against expected application values.

		This method is the central report-construction path for the verifier. It accepts a
		``LabelApplication`` containing expected values and an ``ExtractedLabel`` containing OCR
		output. The extracted label is passed through the existing enrichment path, wrapped in a
		``LabelVerificationReport``, evaluated by the deterministic rules engine, and finalized
		with processing time and overall status.

		When the extracted label does not contain usable text, the method does not attempt
		field-level compliance checks. Instead, it adds the standard OCR human-review result,
		sets the processing duration, determines the report-level status, and returns the report
		for reviewer handling.

		Args:
			application (LabelApplication): Expected application data entered or loaded for the
				label being reviewed.
			extracted_label (ExtractedLabel): OCR output, normalized text, file metadata,
				image-quality notes, and timing data for the uploaded label.

		Returns:
			LabelVerificationReport: Complete verification report for the extracted label. If
			verification fails unexpectedly, the method logs the exception and returns the
			existing empty-report fallback using the extracted label file name when available.
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
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'verify_extracted_label( self, *args ) -> LabelVerificationReport'
			Logger( ).write( error )
			return LabelVerificationReport.empty(
				file_name=extracted_label.file_name if extracted_label else ''
			)
	
	def verify_file( self, application: LabelApplication,
			file_path: str | Path ) -> LabelVerificationReport:
		"""Extract OCR text from one label file and verify the extracted label.

		This method is the primary single-file workflow used by the application. It validates
		the expected application model and uploaded file path, normalizes the file path to a
		``Path`` object, invokes the local OCR engine, enriches the extracted label fields, and
		delegates final rule execution and report construction to ``verify_extracted_label``.

		The method accepts image and document paths supported by the OCR engine. It does not
		perform user-interface operations, does not persist uploaded artwork, and does not modify
		the application model supplied by the caller.

		Args:
			application (LabelApplication): Expected application values entered by the reviewer
				or loaded from a manifest row.
			file_path (str | Path): Path to the uploaded label image or PDF file.

		Returns:
			LabelVerificationReport: Complete verification report for the uploaded label. If OCR
			or verification fails unexpectedly, the method logs the exception and returns the
			existing empty-report fallback containing the supplied file path string.
		"""
		try:
			throw_if( 'application', application )
			throw_if( 'file_path', file_path )
			
			self._application = application
			self._file_path = Path( file_path )
			self._extracted_label = self._ocr_engine.extract_text( self._file_path )
			self._extracted_label = self.enrich_extracted_label( self._extracted_label )
			
			return self.verify_extracted_label( self._application, self._extracted_label )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'verify_file( application: LabelApplication, file_path: str | Path ) -> LabelVerificationReport'
			Logger( ).write( error )
			return LabelVerificationReport.empty( file_name=str( file_path ) )
	
	def verify_files( self, application: LabelApplication,
			file_paths: Iterable[ str | Path ] ) -> BatchVerificationReport:
		"""Verify multiple label files against one shared application model.

		This method supports batch verification when all uploaded labels should be evaluated
		against the same expected application values. The iterable of file paths is converted to
		``Path`` objects, each file is processed through ``verify_file``, and each resulting
		``LabelVerificationReport`` is added to a ``BatchVerificationReport``.

		This workflow is intentionally simple and sequential. It preserves per-file fallback
		behavior from ``verify_file`` while returning a batch container suitable for summary and
		detail reporting.

		Args:
			application (LabelApplication): Expected application values to apply to every file in
				the batch.
			file_paths (Iterable[str | Path]): Uploaded label image or PDF file paths to verify.

		Returns:
			BatchVerificationReport: Batch verification report containing one child report per
			file. If batch setup fails unexpectedly, the method logs the exception and returns the
			existing batch fallback containing an empty report named
			``Batch verification unavailable``.
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
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'verify_files( application: LabelApplication, file_paths: Iterable[str | Path] ) -> BatchVerificationReport'
			Logger( ).write( error )
			return BatchVerificationReport(
				reports=[
						LabelVerificationReport.empty( file_name='Batch verification unavailable' )
				]
			)
	
	def verify_text( self, application: LabelApplication, text: str,
			file_name: str = 'manual_text_entry.txt' ) -> LabelVerificationReport:
		"""Verify manually supplied label text without invoking OCR.

		This method supports testing, troubleshooting, and reviewer-entered text workflows. It
		creates an ``ExtractedLabel`` from the supplied text, marks the OCR engine as ``manual``,
		records zero OCR seconds, and adds an image-quality note explaining that OCR was
		bypassed. The constructed extracted label is then passed through the standard
		``verify_extracted_label`` path so rule execution and report construction remain
		consistent with OCR-based verification.

		Args:
			application (LabelApplication): Expected application values entered by the reviewer
				or loaded from a manifest row.
			text (str): Manually supplied label text to verify.
			file_name (str): Logical file name assigned to the manual text entry. The default
				preserves the original source contract and identifies the report as manual text.

		Returns:
			LabelVerificationReport: Complete verification report for the supplied text. If
			manual-text report construction fails unexpectedly, the method logs the exception and
			returns the existing empty-report fallback using the supplied logical file name.
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
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'verify_text( application: LabelApplication, text: str, file_name: str ) -> LabelVerificationReport'
			Logger( ).write( error )
			return LabelVerificationReport.empty( file_name=file_name )
	
	def summarize_report_status( self, report: LabelVerificationReport ) -> str:
		"""Summarize one verification report for compact reviewer display.

		This method recalculates the report-level status, counts failure, warning, and human
		review results, and returns a compact sentence suitable for status banners, result cards,
		log messages, or quick dashboard summaries. The method does not alter rule results; it
		only ensures the overall status reflects the current report contents before
		summarization.

		Args:
			report (LabelVerificationReport): Verification report to summarize.

		Returns:
			str: Reviewer-facing status summary in the form
			``<Overall Status>: <n> failures, <n> warnings, <n> review items``. If summary
			construction fails unexpectedly, the method logs the exception and returns the
			existing reviewer-safe fallback message.
		"""
		try:
			throw_if( 'report', report )
			self._report = report
			self._report.determine_overall_status( )
			failures = sum( result.is_failure( ) for result in self._report.results )
			warnings = sum( result.is_warning( ) for result in self._report.results )
			reviews = sum( result.is_review( ) for result in self._report.results )
			
			return (f'{self._report.overall_status}: '
			        f'{failures} failures, {warnings} warnings, {reviews} review items')
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'summarize_report_status( report: LabelVerificationReport ) -> str'
			Logger( ).write( error )
			return 'Needs Review: report summary unavailable.'