'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                acceptance_checker.py
      Author:                  Terry D. Eppler
      Created:                 06-06-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-06-2026
    ******************************************************************************************
    <copyright file="acceptance_checker.py" company="Terry D. Eppler">

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
        Provides stakeholder acceptance-status evaluation for Fiddy prototype requirements.

        This module converts runtime batch-processing evidence into requirement-level
        acceptance records. It evaluates label extraction coverage, comparison outputs,
        batch-processing evidence, five-second SLA performance, prototype batch-size coverage,
        output availability, reliability posture, privacy and data-retention posture,
        Azure/local-OCR deployment posture, accessibility posture, and COLA non-integration
        posture.

        The checker does not perform OCR, label verification, or UI rendering. It evaluates the
        structured results already produced by the Fiddy processing workflow and returns
        auditable records for dashboards, CSV exports, Markdown reports, and stakeholder
        acceptance reviews.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd
from pydantic import BaseModel, Field

import config as cfg
from booger import Error, Logger
from config import throw_if
from src.batch_processor import BatchProcessingResult
from src.constants import STATUS_FAIL, STATUS_PASS, STATUS_REVIEW, STATUS_WARNING
from src.models import BatchVerificationReport, LabelVerificationReport

# ==========================================================================================
# Acceptance Constants
# ==========================================================================================

ACCEPTANCE_MET: str = 'Met'
ACCEPTANCE_PARTIAL: str = 'Partially Met'
ACCEPTANCE_NOT_MET: str = 'Not Met'
ACCEPTANCE_NOT_EVALUATED: str = 'Not Evaluated'

REQUIREMENT_FUNCTIONAL_EXTRACTION: str = '1.1'
REQUIREMENT_FUNCTIONAL_COMPARISON: str = '1.2'
REQUIREMENT_FUNCTIONAL_BATCH: str = '1.3'
REQUIREMENT_FUNCTIONAL_PERFORMANCE: str = '1.4'
REQUIREMENT_FUNCTIONAL_OUTPUT: str = '1.5'
REQUIREMENT_USABILITY: str = '2.1'
REQUIREMENT_RELIABILITY: str = '2.2'
REQUIREMENT_SECURITY: str = '2.3'
REQUIREMENT_SCALABILITY: str = '2.4'
REQUIREMENT_INTERFACE_SIMPLICITY: str = '3.1'
REQUIREMENT_ACCESSIBILITY: str = '3.2'
REQUIREMENT_FEEDBACK: str = '3.3'
REQUIREMENT_INFRASTRUCTURE: str = '4.1'
REQUIREMENT_COLA: str = '4.2'
REQUIREMENT_DATA_HANDLING: str = '4.3'

# ==========================================================================================
# Acceptance Models
# ==========================================================================================

class RequirementStatus( BaseModel ):
	"""Represent one stakeholder requirement acceptance determination.

	Purpose:
		The ``RequirementStatus`` model stores a requirement identifier, requirement name,
		acceptance status, evidence statement, recommendation, evaluation timestamp, and optional
		metric values. It is intentionally flat so the record can be displayed in Streamlit,
		exported as CSV, serialized as JSON, or inserted into a stakeholder acceptance report.

	Attributes:
		requirement_id (str): Requirement identifier from the stakeholder requirements.
		requirement_name (str): Plain-language requirement name.
		status (str): Acceptance status such as ``Met``, ``Partially Met``, ``Not Met``, or
			``Not Evaluated``.
		evidence (str): Plain-language evidence used for the status determination.
		recommendation (str): Recommended next action.
		evaluated_on (str): UTC evaluation timestamp.
		metrics (Dict[str, object]): Optional metric values supporting the determination.
	"""
	
	requirement_id: str = Field( default='' )
	requirement_name: str = Field( default='' )
	status: str = Field( default=ACCEPTANCE_NOT_EVALUATED )
	evidence: str = Field( default='' )
	recommendation: str = Field( default='' )
	evaluated_on: str = Field(
		default_factory=lambda: datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' ) )
	metrics: Dict[ str, object ] = Field( default_factory=dict )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert one requirement status into a flat record.

		Purpose:
			Convert the structured requirement status into a dictionary suitable for DataFrame
			display, CSV export, JSON export, or Markdown report generation.

		

		Returns:
			Dict[str, object]: Flat requirement status record.
		"""
		try:
			return {
					'Requirement ID': self.requirement_id,
					'Requirement Name': self.requirement_name,
					'Status': self.status,
					'Evidence': self.evidence,
					'Recommendation': self.recommendation,
					'Evaluated On': self.evaluated_on,
					'Metrics': self.metrics
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Requirement ID': self.requirement_id,
					'Requirement Name': self.requirement_name,
					'Status': ACCEPTANCE_NOT_EVALUATED,
					'Evidence': 'Requirement status record could not be rendered.',
					'Recommendation': 'Inspect the acceptance checker error log.',
					'Evaluated On': '',
					'Metrics': { }
			}

class AcceptanceSummary( BaseModel ):
	"""Represent the complete acceptance evaluation for one Fiddy run.

	Purpose:
		The ``AcceptanceSummary`` model stores all requirement-level acceptance records and provides
		convenience methods for counting status outcomes, calculating an acceptance percentage, and
		converting the summary into display or export records.

	Attributes:
		requirements (List[RequirementStatus]): Requirement-level acceptance results.
		created_on (str): UTC timestamp when the summary object was created.
	"""
	
	requirements: List[ RequirementStatus ] = Field( default_factory=list )
	created_on: str = Field(
		default_factory=lambda: datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' ) )
	
	def status_counts( self ) -> Dict[ str, int ]:
		"""Return counts of requirement statuses.

		Purpose:
			Count requirement records by acceptance status for dashboard display and summary
			reporting.

		

		Returns:
			Dict[str, int]: Status counts keyed by status text.
		"""
		try:
			counts = {
					ACCEPTANCE_MET: 0,
					ACCEPTANCE_PARTIAL: 0,
					ACCEPTANCE_NOT_MET: 0,
					ACCEPTANCE_NOT_EVALUATED: 0
			}
			
			for requirement in self.requirements:
				counts[ requirement.status ] = counts.get( requirement.status, 0 ) + 1
			
			return counts
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'status_counts( self ) -> Dict[str, int]'
			Logger( ).write( error )
			return {
					ACCEPTANCE_MET: 0,
					ACCEPTANCE_PARTIAL: 0,
					ACCEPTANCE_NOT_MET: 0,
					ACCEPTANCE_NOT_EVALUATED: 0
			}
	
	def acceptance_percentage( self ) -> float:
		"""Calculate the percentage of fully met evaluated requirements.

		Purpose:
			Calculate a simple acceptance percentage using fully met requirements divided by
			evaluated requirements. Requirements marked ``Not Evaluated`` are excluded from the
			denominator so small smoke tests do not distort formal acceptance scoring.

		

		Returns:
			float: Percentage of evaluated requirements marked ``Met``.
		"""
		try:
			evaluated = [
					requirement
					for requirement in self.requirements
					if requirement.status != ACCEPTANCE_NOT_EVALUATED
			]
			
			if not evaluated:
				return 0.0
			
			met_count = sum(
				1
				for requirement in evaluated
				if requirement.status == ACCEPTANCE_MET
			)
			
			return round( (met_count / len( evaluated )) * 100.0, 2 )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'acceptance_percentage( self ) -> float'
			Logger( ).write( error )
			return 0.0
	
	def to_records( self ) -> List[ Dict[ str, object ] ]:
		"""Convert all requirement statuses into flat records.

		Purpose:
			Convert each requirement status into a dictionary so the full summary can be displayed
			or exported as a tabular dataset.

		

		Returns:
			List[Dict[str, object]]: Requirement status records.
		"""
		try:
			return [
					requirement.to_record( )
					for requirement in self.requirements
			]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_records( self ) -> List[Dict[str, object]]'
			Logger( ).write( error )
			return [ ]
	
	def to_dataframe( self ) -> pd.DataFrame:
		"""Convert the acceptance summary into a pandas DataFrame.

		Purpose:
			Return a DataFrame suitable for Streamlit display and CSV export.

		

		Returns:
			pd.DataFrame: Acceptance summary DataFrame.
		"""
		try:
			return pd.DataFrame( self.to_records( ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_dataframe( self ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )

# ==========================================================================================
# Acceptance Checker
# ==========================================================================================

class AcceptanceChecker( ):
	"""Evaluate Fiddy runtime evidence against stakeholder prototype requirements.

	Purpose:
		The ``AcceptanceChecker`` class inspects a completed ``BatchProcessingResult`` and returns
		requirement-level acceptance records. It does not rerun OCR or verification. It evaluates
		existing report objects, performance summaries, validation outputs, configuration switches,
		and export DataFrames supplied by the caller.

	Attributes:
		_result (BatchProcessingResult): Active batch-processing result under evaluation.
		_summary_dataframe (pd.DataFrame): Optional summary DataFrame generated by ReportWriter.
		_detail_dataframe (pd.DataFrame): Optional detail DataFrame generated by ReportWriter.
		_comparison_dataframe (pd.DataFrame): Optional comparison DataFrame generated by app.py.
		_performance_dataframe (pd.DataFrame): Optional performance DataFrame generated by app.py.
		_requirements (List[RequirementStatus]): Current acceptance records.
	"""
	
	_result: BatchProcessingResult
	_summary_dataframe: pd.DataFrame
	_detail_dataframe: pd.DataFrame
	_comparison_dataframe: pd.DataFrame
	_performance_dataframe: pd.DataFrame
	_requirements: List[ RequirementStatus ]
	
	def __init__( self ) -> None:
		"""Initialize the acceptance checker.

		Purpose:
			Create empty DataFrame placeholders and an empty requirement list. No evaluation occurs
			until ``evaluate_batch_result`` is called.

		Returns:
			None.
		"""
		self._summary_dataframe = pd.DataFrame( )
		self._detail_dataframe = pd.DataFrame( )
		self._comparison_dataframe = pd.DataFrame( )
		self._performance_dataframe = pd.DataFrame( )
		self._requirements = [ ]
	
	def create_status( self, requirement_id: str, requirement_name: str, status: str,
			evidence: str, recommendation: str = '',
			metrics: Dict[ str, object ] = None ) -> RequirementStatus:
		"""Create one requirement acceptance status record.

		Purpose:
			Centralize construction of requirement status records so all evaluations produce
			consistent output. Required text values are validated before record creation.

		Args:
			requirement_id (str): Stakeholder requirement identifier.
			requirement_name (str): Plain-language requirement name.
			status (str): Acceptance status.
			evidence (str): Evidence supporting the status.
			recommendation (str): Recommended next action.
			metrics (Dict[str, object]): Optional supporting metrics.

		Returns:
			RequirementStatus: Requirement acceptance record.
		"""
		try:
			throw_if( 'requirement_id', requirement_id )
			throw_if( 'requirement_name', requirement_name )
			throw_if( 'status', status )
			throw_if( 'evidence', evidence )
			
			return RequirementStatus(
				requirement_id=requirement_id,
				requirement_name=requirement_name,
				status=status,
				evidence=evidence,
				recommendation=recommendation,
				metrics=metrics or { }
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_status( self, *args ) -> RequirementStatus'
			Logger( ).write( error )
			return RequirementStatus(
				requirement_id=requirement_id or '',
				requirement_name=requirement_name or '',
				status=ACCEPTANCE_NOT_EVALUATED,
				evidence='Requirement status could not be created.',
				recommendation='Inspect the acceptance checker error log.',
				metrics=metrics or { }
			)
	
	def get_batch_report( self ) -> BatchVerificationReport:
		"""Return the active batch verification report.

		Purpose:
			Provide a safe accessor for the batch report stored inside the active
			``BatchProcessingResult``.

		Returns:
			BatchVerificationReport: Active batch report or an empty fallback report.
		"""
		try:
			return self._result.batch_report
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_batch_report( self ) -> BatchVerificationReport'
			Logger( ).write( error )
			return BatchVerificationReport( )
	
	def get_reports( self ) -> List[ LabelVerificationReport ]:
		"""Return all label-level verification reports from the active result.

		Purpose:
			Provide a safe list of reports for requirement checks that inspect extracted labels,
			rule results, status values, and reviewer flags.

		Returns:
			List[LabelVerificationReport]: Label-level reports.
		"""
		try:
			return list( self.get_batch_report( ).reports )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_reports( self ) -> List[LabelVerificationReport]'
			Logger( ).write( error )
			return [ ]
	
	def count_reports_with_ocr_text( self ) -> int:
		"""Count reports containing readable OCR text.

		Purpose:
			Support the extraction requirement by counting label reports whose extracted label
			contains raw OCR text.

		Returns:
			int: Count of reports with extracted OCR text.
		"""
		try:
			return sum(
				1
				for report in self.get_reports( )
				if report.extracted_label and report.extracted_label.has_text( )
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'count_reports_with_ocr_text( self ) -> int'
			Logger( ).write( error )
			return 0
	
	def count_reports_with_rule_results( self ) -> int:
		"""Count reports containing one or more rule results.

		Purpose:
			Support comparison-output evaluation by counting reports where deterministic rule
			evaluation produced structured results.

		Returns:
			int: Count of reports with rule results.
		"""
		try:
			return sum(
				1
				for report in self.get_reports( )
				if report.results
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'count_reports_with_rule_results( self ) -> int'
			Logger( ).write( error )
			return 0
	
	def count_review_or_failure_reports( self ) -> int:
		"""Count reports with fail, warning, or review status.

		Purpose:
			Support reliability evaluation by counting reports that generated reviewer-visible
			non-pass outcomes instead of failing silently.

		Returns:
			int: Count of reports with fail, warning, or needs-review status.
		"""
		try:
			return sum(
				1
				for report in self.get_reports( )
				if report.overall_status in (STATUS_FAIL, STATUS_WARNING, STATUS_REVIEW)
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'count_review_or_failure_reports( self ) -> int'
			Logger( ).write( error )
			return 0
	
	def evaluate_label_extraction( self ) -> RequirementStatus:
		"""Evaluate label data extraction evidence.

		Purpose:
			Determine whether the batch produced extracted-label objects and readable OCR text for
			processed labels.

		Returns:
			RequirementStatus: Label extraction acceptance record.
		"""
		try:
			reports = self.get_reports( )
			total_reports = len( reports )
			ocr_text_count = self.count_reports_with_ocr_text( )
			
			if total_reports <= 0:
				status = ACCEPTANCE_NOT_EVALUATED
				evidence = 'No label reports were available to evaluate extraction.'
				recommendation = 'Run at least one label through OCR and verification.'
			elif ocr_text_count == total_reports:
				status = ACCEPTANCE_MET
				evidence = f'OCR text was extracted for {ocr_text_count} of {total_reports} label reports.'
				recommendation = 'Use representative low-quality images to strengthen acceptance evidence.'
			elif ocr_text_count > 0:
				status = ACCEPTANCE_PARTIAL
				evidence = f'OCR text was extracted for {ocr_text_count} of {total_reports} label reports.'
				recommendation = 'Review labels without OCR text and improve image quality or preprocessing.'
			else:
				status = ACCEPTANCE_NOT_MET
				evidence = f'No readable OCR text was extracted for {total_reports} label reports.'
				recommendation = 'Verify Tesseract, Poppler, file types, and image quality.'
			
			return self.create_status(
				REQUIREMENT_FUNCTIONAL_EXTRACTION,
				'Label Data Extraction',
				status,
				evidence,
				recommendation,
				{
						'total_reports': total_reports,
						'ocr_text_count': ocr_text_count
				}
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate_label_extraction( self ) -> RequirementStatus'
			Logger( ).write( error )
			return self.create_status(
				REQUIREMENT_FUNCTIONAL_EXTRACTION,
				'Label Data Extraction',
				ACCEPTANCE_NOT_EVALUATED,
				'Label extraction could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_application_comparison( self ) -> RequirementStatus:
		"""Evaluate application-versus-label comparison evidence.

		Purpose:
			Determine whether processed label reports contain structured rule results and whether
			the comparison DataFrame includes reviewer-facing comparison fields.

		Returns:
			RequirementStatus: Application comparison acceptance record.
		"""
		try:
			total_reports = len( self.get_reports( ) )
			rule_report_count = self.count_reports_with_rule_results( )
			required_columns = {
					'File Name',
					'Field',
					'Application',
					'Extracted',
					'Status',
					'Severity',
					'Confidence',
					'Explanation',
					'Reviewer Action'
			}
			
			available_columns = set(
				self._comparison_dataframe.columns ) if not self._comparison_dataframe.empty else set( )
			has_required_columns = required_columns.issubset( available_columns )
			
			if total_reports <= 0:
				status = ACCEPTANCE_NOT_EVALUATED
				evidence = 'No verification reports were available to evaluate comparison.'
				recommendation = 'Run verification against label artwork and CAV data.'
			elif rule_report_count == total_reports and has_required_columns:
				status = ACCEPTANCE_MET
				evidence = (
						f'Rule results were created for {rule_report_count} of {total_reports} '
						f'reports and comparison output includes required reviewer columns.'
				)
				recommendation = 'Continue validating fuzzy-match and exact-warning cases with test labels.'
			elif rule_report_count > 0:
				status = ACCEPTANCE_PARTIAL
				evidence = (
						f'Rule results were created for {rule_report_count} of {total_reports} '
						f'reports; comparison column coverage is {has_required_columns}.'
				)
				recommendation = 'Verify comparison DataFrame generation and required display columns.'
			else:
				status = ACCEPTANCE_NOT_MET
				evidence = 'No structured rule comparison results were created.'
				recommendation = 'Inspect label verifier and rule engine execution.'
			
			return self.create_status(
				REQUIREMENT_FUNCTIONAL_COMPARISON,
				'Application vs. Label Comparison',
				status,
				evidence,
				recommendation,
				{
						'total_reports': total_reports,
						'rule_report_count': rule_report_count,
						'has_required_columns': has_required_columns,
						'available_columns': sorted( available_columns )
				}
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate_application_comparison( self ) -> RequirementStatus'
			Logger( ).write( error )
			return self.create_status(
				REQUIREMENT_FUNCTIONAL_COMPARISON,
				'Application vs. Label Comparison',
				ACCEPTANCE_NOT_EVALUATED,
				'Application comparison could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_batch_processing( self ) -> RequirementStatus:
		"""Evaluate batch upload and per-label result evidence.

		Purpose:
			Determine whether batch processing produced per-label reports and tracked processed or
			skipped files.

		Returns:
			RequirementStatus: Batch processing acceptance record.
		"""
		try:
			report_count = len( self.get_reports( ) )
			processed_count = len( self._result.processed_files )
			skipped_count = len( self._result.skipped_files )
			uploaded_count = self._result.validation_result.total_uploaded_files
			
			if report_count > 1 and processed_count > 1:
				status = ACCEPTANCE_MET
				evidence = f'Batch run produced {report_count} per-label reports and {processed_count} processed files.'
				recommendation = 'Use a 20–50 label batch for formal scalability acceptance.'
			elif report_count == 1:
				status = ACCEPTANCE_PARTIAL
				evidence = 'Processing produced one label report; batch capability was not fully exercised.'
				recommendation = 'Run a multi-label upload or ZIP archive to prove batch processing.'
			elif skipped_count > 0:
				status = ACCEPTANCE_PARTIAL
				evidence = f'No processed reports were produced, but {skipped_count} files were tracked as skipped.'
				recommendation = 'Resolve manifest/file matching issues and rerun.'
			else:
				status = ACCEPTANCE_NOT_EVALUATED
				evidence = 'No batch-processing report evidence was available.'
				recommendation = 'Run manifest-driven verification with multiple files.'
			
			return self.create_status(
				REQUIREMENT_FUNCTIONAL_BATCH,
				'Batch Processing',
				status,
				evidence,
				recommendation,
				{
						'report_count': report_count,
						'processed_count': processed_count,
						'skipped_count': skipped_count,
						'uploaded_count': uploaded_count
				}
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate_batch_processing( self ) -> RequirementStatus'
			Logger( ).write( error )
			return self.create_status(
				REQUIREMENT_FUNCTIONAL_BATCH,
				'Batch Processing',
				ACCEPTANCE_NOT_EVALUATED,
				'Batch processing could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_performance( self ) -> RequirementStatus:
		"""Evaluate five-second SLA evidence.

		Purpose:
			Inspect the batch performance summary and formal performance acceptance result to
			determine whether the five-second target was met, not met, or not evaluated.

		Returns:
			RequirementStatus: Performance acceptance record.
		"""
		try:
			summary = self._result.performance_summary
			acceptance = summary.acceptance_result
			
			if summary.total_files <= 0:
				status = ACCEPTANCE_NOT_EVALUATED
				evidence = 'No timed files were available for SLA evaluation.'
				recommendation = 'Run verification with performance monitoring enabled.'
			elif acceptance.meets_acceptance:
				status = ACCEPTANCE_MET
				evidence = acceptance.message
				recommendation = 'Retain the performance CSV as acceptance evidence.'
			else:
				status = ACCEPTANCE_NOT_MET
				evidence = acceptance.message
				recommendation = 'Profile OCR preprocessing, PDF conversion, image size, and worker settings.'
			
			return self.create_status(
				REQUIREMENT_FUNCTIONAL_PERFORMANCE,
				'Performance Under Five Seconds Per Label',
				status,
				evidence,
				recommendation,
				summary.to_record( )
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate_performance( self ) -> RequirementStatus'
			Logger( ).write( error )
			return self.create_status(
				REQUIREMENT_FUNCTIONAL_PERFORMANCE,
				'Performance Under Five Seconds Per Label',
				ACCEPTANCE_NOT_EVALUATED,
				'Performance could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_output( self ) -> RequirementStatus:
		"""Evaluate report and download output evidence.

		Purpose:
			Determine whether summary, detail, comparison, and performance outputs exist after a
			verification run.

		Returns:
			RequirementStatus: Output acceptance record.
		"""
		try:
			has_summary = not self._summary_dataframe.empty
			has_detail = not self._detail_dataframe.empty
			has_comparison = not self._comparison_dataframe.empty
			has_performance = not self._performance_dataframe.empty
			
			required_output_count = sum(
				[
						has_summary,
						has_detail,
						has_comparison
				]
			)
			
			if required_output_count == 3 and has_performance:
				status = ACCEPTANCE_MET
				evidence = 'Summary, detail, comparison, and performance outputs are available.'
				recommendation = 'Export CSV, JSON, and Markdown outputs for stakeholder review.'
			elif required_output_count == 3:
				status = ACCEPTANCE_PARTIAL
				evidence = 'Summary, detail, and comparison outputs are available; performance output is not populated.'
				recommendation = 'Run manifest batch processing to generate performance timing output.'
			elif required_output_count > 0:
				status = ACCEPTANCE_PARTIAL
				evidence = 'Some reviewer outputs are available, but the full output set is incomplete.'
				recommendation = 'Verify ReportWriter and comparison DataFrame generation.'
			else:
				status = ACCEPTANCE_NOT_EVALUATED
				evidence = 'No output DataFrames were supplied for acceptance evaluation.'
				recommendation = 'Run verification and pass output DataFrames to the acceptance checker.'
			
			return self.create_status(
				REQUIREMENT_FUNCTIONAL_OUTPUT,
				'Output and Downloads',
				status,
				evidence,
				recommendation,
				{
						'has_summary': has_summary,
						'has_detail': has_detail,
						'has_comparison': has_comparison,
						'has_performance': has_performance
				}
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate_output( self ) -> RequirementStatus'
			Logger( ).write( error )
			return self.create_status(
				REQUIREMENT_FUNCTIONAL_OUTPUT,
				'Output and Downloads',
				ACCEPTANCE_NOT_EVALUATED,
				'Output could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_reliability( self ) -> RequirementStatus:
		"""Evaluate reliability and graceful-failure evidence.

		Purpose:
			Determine whether the batch result captured errors, warnings, skipped files, or
			reviewer-visible non-pass reports without crashing the batch.

		Returns:
			RequirementStatus: Reliability acceptance record.
		"""
		try:
			report_count = len( self.get_reports( ) )
			review_count = self.count_review_or_failure_reports( )
			error_count = len( self._result.errors )
			warning_count = len( self._result.warnings )
			skipped_count = len( self._result.skipped_files )
			
			if report_count > 0 and error_count == 0:
				status = ACCEPTANCE_MET
				evidence = f'Batch completed with {report_count} reports and no batch-level blocking errors.'
				recommendation = 'Run deliberate bad-image and missing-file cases to expand reliability evidence.'
			elif report_count > 0:
				status = ACCEPTANCE_PARTIAL
				evidence = (
						f'Batch completed with {report_count} reports, {error_count} errors, '
						f'{warning_count} warnings, and {skipped_count} skipped files.'
				)
				recommendation = 'Review captured errors and confirm they produce actionable messages.'
			else:
				status = ACCEPTANCE_NOT_EVALUATED
				evidence = 'No completed label reports were available to evaluate reliability.'
				recommendation = 'Run valid and invalid test cases through batch processing.'
			
			return self.create_status(
				REQUIREMENT_RELIABILITY,
				'Reliability and Graceful Error Handling',
				status,
				evidence,
				recommendation,
				{
						'report_count': report_count,
						'review_or_failure_report_count': review_count,
						'error_count': error_count,
						'warning_count': warning_count,
						'skipped_count': skipped_count
				}
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate_reliability( self ) -> RequirementStatus'
			Logger( ).write( error )
			return self.create_status(
				REQUIREMENT_RELIABILITY,
				'Reliability and Graceful Error Handling',
				ACCEPTANCE_NOT_EVALUATED,
				'Reliability could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_scalability( self ) -> RequirementStatus:
		"""Evaluate 20–50 label prototype scalability evidence.

		Purpose:
			Determine whether the completed run exercised the configured prototype batch-size
			acceptance range.

		Returns:
			RequirementStatus: Scalability acceptance record.
		"""
		try:
			processed_count = len( self._result.processed_files )
			min_files = int( getattr( cfg, 'BATCH_ACCEPTANCE_MIN_FILES', 20 ) )
			max_files = int( getattr( cfg, 'BATCH_ACCEPTANCE_MAX_FILES', 50 ) )
			
			if min_files <= processed_count <= max_files:
				status = ACCEPTANCE_MET
				evidence = f'Processed file count {processed_count} is within the prototype acceptance range of {min_files}–{max_files}.'
				recommendation = 'Retain the batch output and performance CSV as scalability evidence.'
			elif 0 < processed_count < min_files:
				status = ACCEPTANCE_NOT_EVALUATED
				evidence = f'Processed file count {processed_count} is below the formal acceptance minimum of {min_files}.'
				recommendation = f'Run a representative batch containing at least {min_files} labels.'
			elif processed_count > max_files:
				status = ACCEPTANCE_NOT_MET
				evidence = f'Processed file count {processed_count} exceeds the configured prototype maximum of {max_files}.'
				recommendation = 'Confirm MAX_BATCH_FILES and prototype scope before claiming acceptance.'
			else:
				status = ACCEPTANCE_NOT_EVALUATED
				evidence = 'No processed files were available for scalability evaluation.'
				recommendation = 'Run a manifest batch with 20–50 labels.'
			
			return self.create_status(
				REQUIREMENT_SCALABILITY,
				'Prototype-Level Scalability',
				status,
				evidence,
				recommendation,
				{
						'processed_count': processed_count,
						'minimum_acceptance_files': min_files,
						'maximum_acceptance_files': max_files
				}
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate_scalability( self ) -> RequirementStatus'
			Logger( ).write( error )
			return self.create_status(
				REQUIREMENT_SCALABILITY,
				'Prototype-Level Scalability',
				ACCEPTANCE_NOT_EVALUATED,
				'Scalability could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_security_and_data_handling( self ) -> List[ RequirementStatus ]:
		"""Evaluate security and no-long-term-storage posture.

		Purpose:
			Inspect configuration switches that control external ML endpoints, raw text logging,
			file path logging, upload persistence, and log retention. Runtime proof still requires a
			deployment review, but these switches provide acceptance evidence for the prototype
			posture.
			
		Returns:
			List[RequirementStatus]: Security and data-handling acceptance records.
		"""
		try:
			allow_external_ml = bool( getattr( cfg, 'ALLOW_EXTERNAL_ML_ENDPOINTS', False ) )
			enable_raw_text_logging = bool( getattr( cfg, 'ENABLE_RAW_TEXT_LOGGING', False ) )
			enable_file_path_logging = bool( getattr( cfg, 'ENABLE_FILE_PATH_LOGGING', False ) )
			enable_upload_persistence = bool( getattr( cfg, 'ENABLE_UPLOAD_PERSISTENCE', False ) )
			log_retention_days = int( getattr( cfg, 'LOG_RETENTION_DAYS', 7 ) )
			
			security_met = not allow_external_ml and not enable_raw_text_logging and not enable_file_path_logging
			
			security_status = ACCEPTANCE_MET if security_met else ACCEPTANCE_PARTIAL
			security_evidence = (
					f'External ML endpoints allowed: {allow_external_ml}; raw text logging: '
					f'{enable_raw_text_logging}; file path logging: {enable_file_path_logging}.'
			)
			security_recommendation = (
					'Keep external ML endpoints disabled and retain sanitized logging for prototype demos.'
					if security_met
					else 'Disable external ML endpoints and raw/file-path logging before acceptance.'
			)
			
			data_met = not enable_upload_persistence and log_retention_days >= 0
			
			data_status = ACCEPTANCE_MET if data_met else ACCEPTANCE_PARTIAL
			data_evidence = (
					f'Upload persistence enabled: {enable_upload_persistence}; log retention days: '
					f'{log_retention_days}.'
			)
			data_recommendation = (
					'Continue using temporary upload storage and sanitized short-retention logs.'
					if data_met
					else 'Disable upload persistence and confirm short-retention sanitized logging.'
			)
			
			return [
					self.create_status(
						REQUIREMENT_SECURITY,
						'Security and Firewall-Safe Prototype Posture',
						security_status,
						security_evidence,
						security_recommendation,
						{
								'allow_external_ml_endpoints': allow_external_ml,
								'enable_raw_text_logging': enable_raw_text_logging,
								'enable_file_path_logging': enable_file_path_logging
						}
					),
					self.create_status(
						REQUIREMENT_DATA_HANDLING,
						'No Long-Term Storage of Images or Extracted Data',
						data_status,
						data_evidence,
						data_recommendation,
						{
								'enable_upload_persistence': enable_upload_persistence,
								'log_retention_days': log_retention_days
						}
					)
			]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate_security_and_data_handling( self ) -> List[RequirementStatus]'
			Logger( ).write( error )
			return [
					self.create_status(
						REQUIREMENT_SECURITY,
						'Security and Firewall-Safe Prototype Posture',
						ACCEPTANCE_NOT_EVALUATED,
						'Security posture could not be evaluated.',
						'Inspect configuration and the acceptance checker error log.'
					),
					self.create_status(
						REQUIREMENT_DATA_HANDLING,
						'No Long-Term Storage of Images or Extracted Data',
						ACCEPTANCE_NOT_EVALUATED,
						'Data-handling posture could not be evaluated.',
						'Inspect configuration and the acceptance checker error log.'
					)
			]
	
	def evaluate_accessibility_and_usability( self ) -> List[ RequirementStatus ]:
		"""Evaluate accessibility, usability, feedback, and interface simplicity posture.

		Purpose:
			Inspect configuration and output evidence for Simple Mode defaults, high contrast,
			large text, keyboard checklist requirement, progress/performance output, and
			reviewer-facing comparison guidance.

		Returns:
			List[RequirementStatus]: Usability, interface simplicity, accessibility, and feedback
			acceptance records.
		"""
		try:
			default_simple_mode = bool( getattr( cfg, 'DEFAULT_SIMPLE_MODE', True ) )
			default_high_contrast = bool( getattr( cfg, 'DEFAULT_HIGH_CONTRAST_MODE', False ) )
			default_large_text = bool( getattr( cfg, 'DEFAULT_LARGE_TEXT_MODE', False ) )
			keyboard_check_required = bool(
				getattr( cfg, 'REQUIRE_KEYBOARD_ACCESSIBILITY_CHECK', True ) )
			has_comparison_guidance = 'Reviewer Action' in self._comparison_dataframe.columns
			has_progress_evidence = self._result.performance_summary.total_files > 0
			
			usability_status = ACCEPTANCE_MET if default_simple_mode else ACCEPTANCE_PARTIAL
			interface_status = ACCEPTANCE_MET if default_simple_mode else ACCEPTANCE_PARTIAL
			accessibility_status = ACCEPTANCE_PARTIAL if keyboard_check_required else ACCEPTANCE_MET
			feedback_status = ACCEPTANCE_MET if has_comparison_guidance and has_progress_evidence else ACCEPTANCE_PARTIAL
			
			return [
					self.create_status(
						REQUIREMENT_USABILITY,
						'Simple Low-Technical-Comfort Usability',
						usability_status,
						f'Default Simple Mode configured: {default_simple_mode}.',
						'Complete a reviewer walkthrough with non-technical users.',
						{
								'default_simple_mode': default_simple_mode
						}
					),
					self.create_status(
						REQUIREMENT_INTERFACE_SIMPLICITY,
						'Interface Simplicity',
						interface_status,
						f'Simple Mode default is {default_simple_mode}, supporting a short upload-run-review workflow.',
						'Confirm Simple Mode hides worker and SLA controls during manual review.',
						{
								'default_simple_mode': default_simple_mode
						}
					),
					self.create_status(
						REQUIREMENT_ACCESSIBILITY,
						'Accessibility',
						accessibility_status,
						(
								f'High contrast default: {default_high_contrast}; large text default: '
								f'{default_large_text}; keyboard checklist required: {keyboard_check_required}.'
						),
						'Run the manual keyboard accessibility checklist before final acceptance.',
						{
								'default_high_contrast': default_high_contrast,
								'default_large_text': default_large_text,
								'keyboard_check_required': keyboard_check_required
						}
					),
					self.create_status(
						REQUIREMENT_FEEDBACK,
						'Reviewer Feedback, Progress, Confidence, and Mismatch Guidance',
						feedback_status,
						(
								f'Reviewer Action column present: {has_comparison_guidance}; '
								f'performance/progress evidence present: {has_progress_evidence}.'
						),
						'Retain screenshots and output CSVs showing progress, confidence, and mismatch guidance.',
						{
								'has_reviewer_action_column': has_comparison_guidance,
								'has_progress_evidence': has_progress_evidence
						}
					)
			]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate_accessibility_and_usability( self ) -> List[RequirementStatus]'
			Logger( ).write( error )
			return [
					self.create_status(
						REQUIREMENT_ACCESSIBILITY,
						'Accessibility',
						ACCEPTANCE_NOT_EVALUATED,
						'Accessibility posture could not be evaluated.',
						'Inspect configuration and the accessibility checklist.'
					)
			]
	
	def evaluate_infrastructure_and_integration( self ) -> List[ RequirementStatus ]:
		"""Evaluate Azure/local OCR posture and COLA non-integration posture.

		Purpose:
			Inspect configuration values that indicate local OCR is required, external endpoints are
			blocked, and the prototype remains standalone. Full Azure acceptance still requires a
			container or deployment artifact review, but this method records application-level
			posture.

		Returns:
			List[RequirementStatus]: Infrastructure and integration acceptance records.
		"""
		try:
			deployment_target = str( getattr( cfg, 'DEPLOYMENT_TARGET', 'local' ) )
			require_local_ocr = bool( getattr( cfg, 'REQUIRE_LOCAL_OCR', True ) )
			allow_external_ml = bool( getattr( cfg, 'ALLOW_EXTERNAL_ML_ENDPOINTS', False ) )
			infrastructure_met = require_local_ocr and not allow_external_ml
			infrastructure_status = ACCEPTANCE_PARTIAL if infrastructure_met else ACCEPTANCE_NOT_MET
			
			return [
					self.create_status(
						REQUIREMENT_INFRASTRUCTURE,
						'Azure-Compatible Local OCR Infrastructure',
						infrastructure_status,
						(
								f'Deployment target: {deployment_target}; local OCR required: '
								f'{require_local_ocr}; external ML endpoints allowed: {allow_external_ml}.'
						),
						'Add and test Docker/Azure deployment artifacts to move infrastructure from partial to met.',
						{
								'deployment_target': deployment_target,
								'require_local_ocr': require_local_ocr,
								'allow_external_ml_endpoints': allow_external_ml
						}
					),
					self.create_status(
						REQUIREMENT_COLA,
						'No Direct COLA Integration',
						ACCEPTANCE_MET,
						'Acceptance evaluation is based on manifest/manual CAV data and does not require COLA system integration.',
						'Keep the prototype standalone unless future procurement scope changes.',
						{
								'cola_integration_required': False
						}
					)
			]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate_infrastructure_and_integration( self ) -> List[RequirementStatus]'
			Logger( ).write( error )
			return [
					self.create_status(
						REQUIREMENT_INFRASTRUCTURE,
						'Azure-Compatible Local OCR Infrastructure',
						ACCEPTANCE_NOT_EVALUATED,
						'Infrastructure posture could not be evaluated.',
						'Inspect configuration and deployment artifacts.'
					)
			]
	
	def evaluate_batch_result( self, result: BatchProcessingResult,
			summary_dataframe: pd.DataFrame = None,
			detail_dataframe: pd.DataFrame = None,
			comparison_dataframe: pd.DataFrame = None,
			performance_dataframe: pd.DataFrame = None ) -> AcceptanceSummary:
		"""Evaluate a completed batch-processing result against stakeholder requirements.

		Purpose:
			Store the active batch result and optional output DataFrames, execute all requirement
			evaluations, and return a complete ``AcceptanceSummary`` containing requirement-level
			status records.

		Args:
			result (BatchProcessingResult): Completed batch-processing result.
			summary_dataframe (pd.DataFrame): Optional summary output DataFrame.
			detail_dataframe (pd.DataFrame): Optional rule-detail output DataFrame.
			comparison_dataframe (pd.DataFrame): Optional comparison output DataFrame.
			performance_dataframe (pd.DataFrame): Optional performance output DataFrame.

		Returns:
			AcceptanceSummary: Complete stakeholder acceptance summary.
		"""
		try:
			throw_if( 'result', result )
			
			self._result = result
			self._summary_dataframe = summary_dataframe if summary_dataframe is not None else pd.DataFrame( )
			self._detail_dataframe = detail_dataframe if detail_dataframe is not None else pd.DataFrame( )
			self._comparison_dataframe = comparison_dataframe if comparison_dataframe is not None else pd.DataFrame( )
			self._performance_dataframe = performance_dataframe if performance_dataframe is not None else pd.DataFrame( )
			self._requirements = [
					self.evaluate_label_extraction( ),
					self.evaluate_application_comparison( ),
					self.evaluate_batch_processing( ),
					self.evaluate_performance( ),
					self.evaluate_output( ),
					self.evaluate_reliability( ),
					self.evaluate_scalability( )
			]
			
			self._requirements.extend( self.evaluate_security_and_data_handling( ) )
			self._requirements.extend( self.evaluate_accessibility_and_usability( ) )
			self._requirements.extend( self.evaluate_infrastructure_and_integration( ) )
			
			return AcceptanceSummary( requirements=self._requirements )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate_batch_result( self, *args ) -> AcceptanceSummary'
			Logger( ).write( error )
			return AcceptanceSummary(
				requirements=[
						self.create_status(
							'ACCEPTANCE',
							'Acceptance Evaluation',
							ACCEPTANCE_NOT_EVALUATED,
							'Acceptance evaluation failed before requirement records could be completed.',
							'Inspect the acceptance checker error log.'
						)
				]
			)