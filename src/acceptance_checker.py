'''******************************************************************************************
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

        This module converts runtime verification evidence into requirement-level acceptance
        records for stakeholder review. It evaluates the full prototype requirement set,
        including extraction coverage, application-versus-label comparison, batch processing,
        five-second performance, output availability, usability, reliability, security posture,
        prototype scalability, interface simplicity, accessibility, feedback, Azure-compatible
        local-OCR posture, COLA non-integration, and data-handling posture.

        The checker does not perform OCR, label verification, UI rendering, deployment, or
        browser automation. It evaluates structured results, output tables, configuration
        values, and optional externally supplied evidence records. This separation prevents the
        application from claiming that evidence-dependent requirements are met solely because
        supporting code exists.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field

import config as cfg
from booger import Error, Logger
from config import throw_if
from src.batch_processor import BatchProcessingResult
from src.constants import STATUS_FAIL, STATUS_REVIEW, STATUS_WARNING
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

REQUIREMENT_ORDER: List[ str ] = [
		REQUIREMENT_FUNCTIONAL_EXTRACTION,
		REQUIREMENT_FUNCTIONAL_COMPARISON,
		REQUIREMENT_FUNCTIONAL_BATCH,
		REQUIREMENT_FUNCTIONAL_PERFORMANCE,
		REQUIREMENT_FUNCTIONAL_OUTPUT,
		REQUIREMENT_USABILITY,
		REQUIREMENT_RELIABILITY,
		REQUIREMENT_SECURITY,
		REQUIREMENT_SCALABILITY,
		REQUIREMENT_INTERFACE_SIMPLICITY,
		REQUIREMENT_ACCESSIBILITY,
		REQUIREMENT_FEEDBACK,
		REQUIREMENT_INFRASTRUCTURE,
		REQUIREMENT_COLA,
		REQUIREMENT_DATA_HANDLING
]

# ==========================================================================================
# Acceptance Models
# ==========================================================================================

class RequirementStatus( BaseModel ):
	"""Represents one stakeholder requirement acceptance determination.

	Purpose:
		Store one requirement-level evaluation result using a flat, export-friendly structure.
		Each instance contains the stakeholder requirement identifier, plain-language name,
		acceptance status, evidence statement, recommendation, evaluation timestamp, and optional
		supporting metrics. The model is intentionally simple so it can be displayed in Streamlit,
		exported as CSV, serialized as JSON, or embedded in a Markdown stakeholder acceptance
		report.

	Attributes:
		requirement_id (str): Requirement identifier from the stakeholder requirements document.
		requirement_name (str): Human-readable name for the requirement being evaluated.
		status (str): Acceptance status. Expected values are ``Met``, ``Partially Met``,
			``Not Met``, or ``Not Evaluated``.
		evidence (str): Plain-language evidence supporting the status determination.
		recommendation (str): Recommended action needed to preserve or improve acceptance.
		evaluated_on (str): UTC timestamp when the requirement status was created.
		metrics (Dict[str, object]): Optional machine-readable metric values supporting the
			determination.
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
		"""Converts the requirement status into a flat dictionary record.

		Purpose:
			Convert the requirement status object into a dictionary suitable for pandas DataFrame
			construction, Streamlit table display, CSV export, JSON serialization, and Markdown
			report construction.

		Returns:
			Dict[str, object]: Flat requirement status record. If rendering fails, a conservative
			record is returned with ``Not Evaluated`` status and diagnostic guidance.
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
	"""Represents the complete acceptance evaluation for one Fiddy run.

	Purpose:
		Aggregate all requirement-level acceptance records produced by ``AcceptanceChecker``.
		The model also provides convenience methods for status counts, acceptance percentage,
		DataFrame conversion, JSON serialization, and Markdown report generation.

	Attributes:
		requirements (List[RequirementStatus]): Requirement-level acceptance results.
		created_on (str): UTC timestamp when the summary object was created.
	"""
	
	requirements: List[ RequirementStatus ] = Field( default_factory=list )
	created_on: str = Field(
		default_factory=lambda: datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' ) )
	
	def status_counts( self ) -> Dict[ str, int ]:
		"""Counts requirement records by acceptance status.

		Purpose:
			Count requirement records by acceptance status for dashboard display, export records,
			Markdown reports, and stakeholder acceptance summaries.

		Returns:
			Dict[str, int]: Count of requirements keyed by status text. If counting fails, all
			status counts are returned as zero.
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
		"""Calculates the percentage of evaluated requirements marked as fully met.

		Purpose:
			Calculate a simple stakeholder acceptance percentage by dividing fully met
			requirements by evaluated requirements. Requirements marked ``Not Evaluated`` are
			excluded from the denominator so small smoke tests or partial reviewer runs do not
			distort formal acceptance scoring.

		Returns:
			float: Percentage of evaluated requirements marked ``Met``, rounded to two decimals.
			If no requirements have been evaluated, returns ``0.0``.
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
		"""Converts all requirement statuses into flat dictionary records.

		Purpose:
			Convert every requirement status in the summary into a flat dictionary record so the
			full summary can be displayed, exported, serialized, or included in a stakeholder
			report.

		Returns:
			List[Dict[str, object]]: Requirement status records suitable for table display and
			export. If conversion fails, returns an empty list.
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
		"""Converts the acceptance summary into a pandas DataFrame.

		Purpose:
			Build a DataFrame from the flat requirement records so the acceptance summary can be
			displayed in Streamlit, exported as CSV, or passed into downstream reporting
			utilities.

		Returns:
			pd.DataFrame: Acceptance summary DataFrame. If conversion fails, returns an empty
			DataFrame.
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
	
	def to_json( self ) -> str:
		"""Serializes the acceptance summary as formatted JSON.

		Purpose:
			Create a JSON acceptance payload containing creation time, acceptance percentage,
			status counts, and every requirement record. The payload is intended for audit files,
			test harness output, and stakeholder evidence packages.

		Returns:
			str: Formatted JSON string. If serialization fails, returns an empty JSON object.
		"""
		try:
			payload = {
					'created_on': self.created_on,
					'acceptance_percentage': self.acceptance_percentage( ),
					'status_counts': self.status_counts( ),
					'requirements': self.to_records( )
			}
			return json.dumps( payload, indent=2, default=str )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_json( self ) -> str'
			Logger( ).write( error )
			return '{}'
	
	def to_markdown( self ) -> str:
		"""Renders the acceptance summary as stakeholder-readable Markdown.

		Purpose:
			Create a Markdown acceptance report containing creation time, acceptance percentage,
			status counts, and a requirement-by-requirement discussion of status, evidence, and
			recommendation.

		Returns:
			str: Markdown acceptance report. If rendering fails, returns a fallback Markdown
			message.
		"""
		try:
			counts = self.status_counts( )
			lines = [
					'# Fiddy Acceptance Summary',
					'',
					f'Created On: {self.created_on}',
					f'Acceptance Percentage: {self.acceptance_percentage( )}%',
					'',
					'## Status Counts',
					'',
					f'- Met: {counts.get( ACCEPTANCE_MET, 0 )}',
					f'- Partially Met: {counts.get( ACCEPTANCE_PARTIAL, 0 )}',
					f'- Not Met: {counts.get( ACCEPTANCE_NOT_MET, 0 )}',
					f'- Not Evaluated: {counts.get( ACCEPTANCE_NOT_EVALUATED, 0 )}',
					'',
					'## Requirement Results',
					''
			]
			
			for requirement in self.requirements:
				lines.extend(
					[
							f'### {requirement.requirement_id} - {requirement.requirement_name}',
							'',
							f'Status: {requirement.status}',
							'',
							f'Evidence: {requirement.evidence}',
							'',
							f'Recommendation: {requirement.recommendation}',
							''
					]
				)
			
			return '\n'.join( lines )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_markdown( self ) -> str'
			Logger( ).write( error )
			return '# Fiddy Acceptance Summary\n\nAcceptance summary could not be rendered.'

# ==========================================================================================
# Acceptance Checker
# ==========================================================================================

class AcceptanceChecker( ):
	"""Evaluates Fiddy runtime evidence against stakeholder prototype requirements.

	Purpose:
		Inspect completed batch or manual verification evidence and return requirement-level
		acceptance records. The checker evaluates report objects, performance summaries,
		validation outputs, configuration switches, output DataFrames, accessibility evidence,
		deployment evidence, and supplemental evidence flags.

		The checker deliberately does not perform OCR, execute label verification, deploy
		infrastructure, or automate browser accessibility checks. Those activities are performed
		elsewhere. This class only evaluates their outputs so the final acceptance package can
		distinguish between implemented capabilities and proven capabilities.

	Attributes:
		_result (BatchProcessingResult): Active processing result under evaluation.
		_summary_dataframe (pd.DataFrame): Optional summary output DataFrame.
		_detail_dataframe (pd.DataFrame): Optional detail output DataFrame.
		_comparison_dataframe (pd.DataFrame): Optional comparison output DataFrame.
		_performance_dataframe (pd.DataFrame): Optional performance output DataFrame.
		_accessibility_dataframe (pd.DataFrame): Optional accessibility checklist DataFrame.
		_deployment_dataframe (pd.DataFrame): Optional deployment evidence DataFrame.
		_evidence (Dict[str, object]): Optional supplemental evidence supplied by UI or tests.
		_requirements (List[RequirementStatus]): Current acceptance records.
	"""
	
	_result: BatchProcessingResult
	_summary_dataframe: pd.DataFrame
	_detail_dataframe: pd.DataFrame
	_comparison_dataframe: pd.DataFrame
	_performance_dataframe: pd.DataFrame
	_accessibility_dataframe: pd.DataFrame
	_deployment_dataframe: pd.DataFrame
	_evidence: Dict[ str, object ]
	_requirements: List[ RequirementStatus ]
	
	def __init__( self ) -> None:
		"""Initializes the acceptance checker.

		Purpose:
			Create empty DataFrame placeholders, an empty supplemental evidence dictionary, and an
			empty requirement list. Evaluation does not occur until ``evaluate_batch_result`` or
			``evaluate_manual_or_batch_result`` is called.

		Returns:
			None.
		"""
		self._summary_dataframe = pd.DataFrame( )
		self._detail_dataframe = pd.DataFrame( )
		self._comparison_dataframe = pd.DataFrame( )
		self._performance_dataframe = pd.DataFrame( )
		self._accessibility_dataframe = pd.DataFrame( )
		self._deployment_dataframe = pd.DataFrame( )
		self._evidence = { }
		self._requirements = [ ]
	
	def create_status( self, requirement_id: str, requirement_name: str, status: str,
			evidence: str, recommendation: str = '',
			metrics: Optional[ Dict[ str, object ] ] = None ) -> RequirementStatus:
		"""Creates one requirement acceptance status record.

		Purpose:
			Centralize ``RequirementStatus`` construction so all evaluations produce consistent
			records. Required values are validated before the record is created. If record creation
			fails, a reviewer-safe fallback record is returned.

		Args:
			requirement_id (str): Stakeholder requirement identifier.
			requirement_name (str): Human-readable requirement name.
			status (str): Acceptance status.
			evidence (str): Evidence supporting the status.
			recommendation (str): Recommended next action.
			metrics (Optional[Dict[str, object]]): Optional supporting metrics.

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
	
	def get_evidence_bool( self, name: str, default: bool = False ) -> bool:
		"""Reads a Boolean value from supplemental evidence or configuration.

		Purpose:
			Return a Boolean evidence value using supplemental runtime evidence before falling
			back to configuration. This makes test-harness evidence and UI-provided acceptance
			flags authoritative while preserving configuration defaults.

		Args:
			name (str): Evidence or configuration key.
			default (bool): Default value used when no value is available.

		Returns:
			bool: Resolved Boolean value.
		"""
		try:
			throw_if( 'name', name )
			if name in self._evidence:
				return bool( self._evidence.get( name, default ) )
			
			return bool( getattr( cfg, name, default ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_evidence_bool( self, name: str, default: bool ) -> bool'
			Logger( ).write( error )
			return default
	
	def get_evidence_int( self, name: str, default: int = 0 ) -> int:
		"""Reads an integer value from supplemental evidence or configuration.

		Purpose:
			Return an integer evidence value using supplemental runtime evidence before falling
			back to configuration. Invalid, missing, or unavailable values return the supplied
			default.

		Args:
			name (str): Evidence or configuration key.
			default (int): Default value used when no value is available.

		Returns:
			int: Resolved integer value. If parsing fails, returns the supplied default.
		"""
		try:
			throw_if( 'name', name )
			if name in self._evidence:
				return int( self._evidence.get( name, default ) )
			
			return int( getattr( cfg, name, default ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_evidence_int( self, name: str, default: int ) -> int'
			Logger( ).write( error )
			return default
	
	def get_evidence_text( self, name: str, default: str = '' ) -> str:
		"""Reads a text value from supplemental evidence or configuration.

		Purpose:
			Return a text evidence value using supplemental runtime evidence before falling back
			to configuration. Invalid, missing, or unavailable values return the supplied default.

		Args:
			name (str): Evidence or configuration key.
			default (str): Default value used when no value is available.

		Returns:
			str: Resolved text value. If resolution fails, returns the supplied default.
		"""
		try:
			throw_if( 'name', name )
			if name in self._evidence:
				return str( self._evidence.get( name, default ) )
			
			return str( getattr( cfg, name, default ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_evidence_text( self, name: str, default: str ) -> str'
			Logger( ).write( error )
			return default
	
	def normalize_dataframe( self, df_source: Optional[ pd.DataFrame ] ) -> pd.DataFrame:
		"""Normalizes an optional DataFrame argument.

		Purpose:
			Return the supplied DataFrame when available and return an empty fallback DataFrame
			when the caller supplies ``None``. This lets evaluation logic safely inspect DataFrame
			columns and row counts without repeated null checks.

		Args:
			df_source (Optional[pd.DataFrame]): Optional DataFrame value.

		Returns:
			pd.DataFrame: Original DataFrame when provided, otherwise an empty fallback DataFrame.
		"""
		try:
			return df_source if df_source is not None else pd.DataFrame( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_dataframe( self, df_source: Optional[pd.DataFrame] ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def get_batch_report( self ) -> BatchVerificationReport:
		"""Returns the active batch verification report.

		Purpose:
			Return the batch report from the active processing result while protecting the caller
			from missing or invalid result state.

		Returns:
			BatchVerificationReport: Active batch report from the current processing result, or an
			empty fallback report if unavailable.
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
		"""Returns all label-level verification reports from the active result.

		Purpose:
			Flatten the active batch report into its label-level verification reports for
			requirement checks that operate on per-label evidence.

		Returns:
			List[LabelVerificationReport]: Label-level reports. If retrieval fails, returns an
			empty list.
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
	
	def get_result_values( self ) -> List[ object ]:
		"""Returns all rule-result objects from all active reports.

		Purpose:
			Flatten rule results from every label report into one list so requirement checks can
			inspect rule identifiers, statuses, confidence values, and human-review flags.

		Returns:
			List[object]: Flattened rule-result objects from all label reports.
		"""
		try:
			results = [ ]
			for report in self.get_reports( ):
				results.extend( list( report.results ) )
			
			return results
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_result_values( self ) -> List[object]'
			Logger( ).write( error )
			return [ ]
	
	def count_reports_with_ocr_text( self ) -> int:
		"""Counts reports containing readable OCR text.

		Purpose:
			Count label reports whose extracted label contains readable raw OCR text. This is one
			of the primary evidence points for the label data extraction requirement.

		Returns:
			int: Number of reports whose extracted label contains readable raw OCR text.
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
	
	def count_reports_with_structured_fields( self ) -> int:
		"""Counts reports containing one or more structured extracted fields.

		Purpose:
			Count reports where OCR or field extraction populated at least one label-side
			structured field. This supports the stakeholder requirement for extracting key label
			fields instead of only raw OCR text.

		Returns:
			int: Number of reports where OCR or extraction produced at least one structured
			label-side field value.
		"""
		try:
			count = 0
			for report in self.get_reports( ):
				label = report.extracted_label
				if not label:
					continue
				
				values = [
						label.brand_name,
						label.class_type,
						label.alcohol_content,
						label.net_contents,
						label.producer_bottler,
						label.country_of_origin,
						label.government_warning
				]
				
				if any( value not in (None, '') for value in values ):
					count += 1
			
			return count
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'count_reports_with_structured_fields( self ) -> int'
			Logger( ).write( error )
			return 0
	
	def count_reports_with_rule_results( self ) -> int:
		"""Counts reports containing one or more rule results.

		Purpose:
			Count label reports where deterministic verification rules produced structured
			results. This supports application-versus-label comparison acceptance.

		Returns:
			int: Number of reports where deterministic rule evaluation produced structured
			results.
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
		"""Counts reports with fail, warning, or review status.

		Purpose:
			Count label reports with reviewer-visible non-pass outcomes. This supports reliability
			and feedback evaluation because the app must surface mismatches and review conditions
			clearly.

		Returns:
			int: Number of reports with reviewer-visible non-pass outcomes.
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
	
	def count_results_requiring_review( self ) -> int:
		"""Counts rule results requiring human review.

		Purpose:
			Count rule-level results where reviewer judgment is required. This is especially
			important for OCR quality issues and government-warning visual-format review.

		Returns:
			int: Number of rule results where ``requires_human_review`` is true.
		"""
		try:
			return sum(
				1
				for result in self.get_result_values( )
				if bool( getattr( result, 'requires_human_review', False ) )
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'count_results_requiring_review( self ) -> int'
			Logger( ).write( error )
			return 0
	
	def dataframe_has_columns( self, df_source: pd.DataFrame, columns: List[ str ] ) -> bool:
		"""Determines whether a DataFrame contains all required columns.

		Purpose:
			Validate that a DataFrame contains the expected reviewer-facing columns needed for
			display, export, and acceptance evidence.

		Args:
			df_source (pd.DataFrame): DataFrame to inspect.
			columns (List[str]): Required column names.

		Returns:
			bool: True when all required columns are present; otherwise, False.
		"""
		try:
			if df_source is None or df_source.empty:
				return False
			
			return set( columns ).issubset( set( df_source.columns ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'dataframe_has_columns( self, *args ) -> bool'
			Logger( ).write( error )
			return False
	
	def evaluate_label_extraction( self ) -> RequirementStatus:
		"""Evaluates label data extraction evidence.

		Purpose:
			Determine whether the run produced label reports, readable OCR text, structured
			extracted fields, visual-quality evidence, and externally supplied imperfect-image
			evidence.

		Returns:
			RequirementStatus: Label extraction acceptance record.
		"""
		try:
			reports = self.get_reports( )
			total_reports = len( reports )
			ocr_text_count = self.count_reports_with_ocr_text( )
			structured_count = self.count_reports_with_structured_fields( )
			imperfect_image_evidence = self.get_evidence_bool( 'IMPERFECT_IMAGE_TESTED', False )
			visual_quality_evidence = any(
				bool( getattr( report.extracted_label, 'image_quality_notes', [ ] ) )
				for report in reports
			)
			
			if total_reports <= 0:
				status = ACCEPTANCE_NOT_EVALUATED
				evidence = 'No label reports were available to evaluate extraction.'
				recommendation = 'Run at least one label through OCR and verification.'
			elif ocr_text_count == total_reports and structured_count == total_reports and imperfect_image_evidence:
				status = ACCEPTANCE_MET
				evidence = (
						f'OCR text and structured fields were produced for {total_reports} of '
						f'{total_reports} reports, with imperfect-image evidence supplied.'
				)
				recommendation = 'Retain OCR, visual-quality, and structured-field evidence in the acceptance package.'
			elif ocr_text_count > 0 and structured_count > 0:
				status = ACCEPTANCE_PARTIAL
				evidence = (
						f'OCR text was extracted for {ocr_text_count} of {total_reports} reports and '
						f'structured fields were produced for {structured_count} reports. Imperfect-image '
						f'evidence supplied: {imperfect_image_evidence}.'
				)
				recommendation = 'Run skewed, low-contrast, glare-affected, and normal sample labels through the harness.'
			else:
				status = ACCEPTANCE_NOT_MET
				evidence = f'Readable OCR text was extracted for {ocr_text_count} of {total_reports} reports.'
				recommendation = 'Verify OCR dependencies, file types, Tesseract configuration, and preprocessing.'
			
			return self.create_status(
				REQUIREMENT_FUNCTIONAL_EXTRACTION,
				'Label Data Extraction',
				status,
				evidence,
				recommendation,
				{
						'total_reports': total_reports,
						'ocr_text_count': ocr_text_count,
						'structured_field_report_count': structured_count,
						'imperfect_image_evidence': imperfect_image_evidence,
						'visual_quality_evidence': visual_quality_evidence
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
		"""Evaluates application-versus-label comparison evidence.

		Purpose:
			Check whether rule results were produced, whether comparison output contains
			reviewer-facing fields, whether fuzzy brand/class rules exist, and whether government
			warning exact-text and visual-review rules were exercised.

		Returns:
			RequirementStatus: Application comparison acceptance record.
		"""
		try:
			total_reports = len( self.get_reports( ) )
			rule_report_count = self.count_reports_with_rule_results( )
			required_columns = [
					'File Name',
					'Field',
					'Application',
					'Extracted',
					'Status',
					'Severity',
					'Confidence',
					'Explanation',
					'Reviewer Action'
			]
			has_required_columns = self.dataframe_has_columns(
				self._comparison_dataframe,
				required_columns
			)
			results = self.get_result_values( )
			rule_ids = [ str( getattr( result, 'rule_id', '' ) ) for result in results ]
			has_fuzzy_rules = any(
				rule_id in ('brand_name_match', 'class_type_match')
				for rule_id in rule_ids
			)
			has_warning_exact_rule = 'government_warning_exact' in rule_ids
			has_warning_visual_rule = 'government_warning_visual_format' in rule_ids
			
			if total_reports <= 0:
				status = ACCEPTANCE_NOT_EVALUATED
				evidence = 'No verification reports were available to evaluate comparison.'
				recommendation = 'Run verification against label artwork and CAV data.'
			elif rule_report_count == total_reports and has_required_columns and has_warning_exact_rule:
				status = ACCEPTANCE_MET if has_fuzzy_rules and has_warning_visual_rule else ACCEPTANCE_PARTIAL
				evidence = (
						f'Rule results were created for {rule_report_count} of {total_reports} reports. '
						f'Comparison output includes reviewer columns: {has_required_columns}; fuzzy-rule '
						f'evidence: {has_fuzzy_rules}; exact-warning rule: {has_warning_exact_rule}; '
						f'visual-warning review rule: {has_warning_visual_rule}.'
				)
				recommendation = 'Retain comparison CSV evidence and near-match warning cases.'
			elif rule_report_count > 0:
				status = ACCEPTANCE_PARTIAL
				evidence = (
						f'Rule results were created for {rule_report_count} of {total_reports} reports; '
						f'comparison columns complete: {has_required_columns}.'
				)
				recommendation = 'Verify comparison table generation and required reviewer columns.'
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
						'has_fuzzy_rules': has_fuzzy_rules,
						'has_government_warning_exact_rule': has_warning_exact_rule,
						'has_government_warning_visual_rule': has_warning_visual_rule,
						'available_columns': sorted( list( self._comparison_dataframe.columns ) )
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
		"""Evaluates batch upload and per-label result evidence.

		Purpose:
			Determine whether verification evidence proves the system can process multiple labels
			and return one result set per label.

		Returns:
			RequirementStatus: Batch processing acceptance record.
		"""
		try:
			report_count = len( self.get_reports( ) )
			processed_count = len( self._result.processed_files )
			skipped_count = len( self._result.skipped_files )
			uploaded_count = self._result.validation_result.total_uploaded_files
			matched_count = len( self._result.validation_result.matched_files )
			
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
						'uploaded_count': uploaded_count,
						'matched_count': matched_count
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
		"""Evaluates five-second SLA evidence.

		Purpose:
			Inspect measured performance output and optional supplemental evidence to determine
			whether the five-second-per-label requirement is proven.

		Returns:
			RequirementStatus: Performance acceptance record.
		"""
		try:
			summary = self._result.performance_summary
			total_files = int( getattr( summary, 'total_files', 0 ) )
			acceptance = getattr( summary, 'acceptance_result', None )
			manual_sla_met = self.get_evidence_bool( 'PERFORMANCE_SLA_PASSED', False )
			manual_sla_tested = self.get_evidence_bool( 'PERFORMANCE_SLA_TESTED', False )
			
			if total_files <= 0 and not manual_sla_tested:
				status = ACCEPTANCE_NOT_EVALUATED
				evidence = 'No timed files were available for SLA evaluation.'
				recommendation = 'Run verification with performance monitoring enabled.'
			elif acceptance is not None and bool(
					getattr( acceptance, 'meets_acceptance', False ) ):
				status = ACCEPTANCE_MET
				evidence = str(
					getattr( acceptance, 'message',
						'Measured performance met configured acceptance targets.' )
				)
				recommendation = 'Retain the performance CSV as acceptance evidence.'
			elif manual_sla_tested and manual_sla_met:
				status = ACCEPTANCE_MET
				evidence = 'Supplemental performance evidence indicates the five-second SLA test passed.'
				recommendation = 'Attach performance CSV or test-harness output to the acceptance package.'
			else:
				status = ACCEPTANCE_NOT_MET
				evidence = str(
					getattr( acceptance, 'message',
						'Measured performance did not prove the five-second SLA.' )
				)
				recommendation = 'Profile OCR preprocessing, PDF conversion, image size, and worker settings.'
			
			metrics = summary.to_record( ) if hasattr( summary, 'to_record' ) else { }
			metrics.update(
				{
						'performance_sla_tested': manual_sla_tested,
						'performance_sla_passed': manual_sla_met
				}
			)
			
			return self.create_status(
				REQUIREMENT_FUNCTIONAL_PERFORMANCE,
				'Performance Under Five Seconds Per Label',
				status,
				evidence,
				recommendation,
				metrics
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
		"""Evaluates report and download output evidence.

		Purpose:
			Determine whether the application produced the expected summary, detail, comparison,
			performance, and acceptance outputs required for reviewer use and stakeholder review.

		Returns:
			RequirementStatus: Output acceptance record.
		"""
		try:
			has_summary = not self._summary_dataframe.empty
			has_detail = not self._detail_dataframe.empty
			has_comparison = not self._comparison_dataframe.empty
			has_performance = not self._performance_dataframe.empty
			has_acceptance_export = self.get_evidence_bool( 'ACCEPTANCE_EXPORT_AVAILABLE', False )
			required_output_count = sum( [ has_summary, has_detail, has_comparison ] )
			
			if required_output_count == 3 and has_performance and has_acceptance_export:
				status = ACCEPTANCE_MET
				evidence = 'Summary, detail, comparison, performance, and acceptance outputs are available.'
				recommendation = 'Export CSV, JSON, and Markdown outputs for stakeholder review.'
			elif required_output_count == 3:
				status = ACCEPTANCE_PARTIAL
				evidence = (
						'Summary, detail, and comparison outputs are available; performance or acceptance '
						'output is not populated.'
				)
				recommendation = 'Run manifest batch processing and wire acceptance export into downloads.'
			elif required_output_count > 0:
				status = ACCEPTANCE_PARTIAL
				evidence = 'Some reviewer outputs are available, but the full output set is incomplete.'
				recommendation = 'Verify ReportWriter, comparison DataFrame, and acceptance DataFrame generation.'
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
						'has_performance': has_performance,
						'has_acceptance_export': has_acceptance_export
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
		"""Evaluates reliability and graceful-failure evidence.

		Purpose:
			Determine whether processing completed with useful reviewer-facing outputs, isolated
			failures, actionable warnings, bad-image handling evidence, and false-positive
			variation evidence.

		Returns:
			RequirementStatus: Reliability acceptance record.
		"""
		try:
			report_count = len( self.get_reports( ) )
			review_count = self.count_review_or_failure_reports( )
			error_count = len( self._result.errors )
			warning_count = len( self._result.warnings )
			skipped_count = len( self._result.skipped_files )
			low_quality_tested = self.get_evidence_bool( 'LOW_QUALITY_IMAGE_TESTED', False )
			false_positive_tested = self.get_evidence_bool( 'FALSE_POSITIVE_VARIATION_TESTED',
				False )
			
			if report_count > 0 and error_count == 0 and low_quality_tested and false_positive_tested:
				status = ACCEPTANCE_MET
				evidence = (
						f'Run completed with {report_count} reports, no batch-level blocking errors, '
						'low-quality image evidence, and false-positive variation evidence.'
				)
				recommendation = 'Retain bad-image and near-match test outputs in the acceptance package.'
			elif report_count > 0:
				status = ACCEPTANCE_PARTIAL
				evidence = (
						f'Run completed with {report_count} reports, {error_count} errors, '
						f'{warning_count} warnings, and {skipped_count} skipped files. Low-quality '
						f'evidence: {low_quality_tested}; false-positive evidence: {false_positive_tested}.'
				)
				recommendation = 'Run deliberate bad-image and minor textual variation cases.'
			else:
				status = ACCEPTANCE_NOT_EVALUATED
				evidence = 'No completed label reports were available to evaluate reliability.'
				recommendation = 'Run valid and invalid test cases through processing.'
			
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
						'skipped_count': skipped_count,
						'low_quality_image_tested': low_quality_tested,
						'false_positive_variation_tested': false_positive_tested
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
		"""Evaluates 20–50 label prototype scalability evidence.

		Purpose:
			Determine whether processing evidence proves the prototype can handle a representative
			small-to-medium batch in the 20-to-50-label range.

		Returns:
			RequirementStatus: Scalability acceptance record.
		"""
		try:
			processed_count = len( self._result.processed_files )
			report_count = len( self.get_reports( ) )
			min_files = self.get_evidence_int( 'BATCH_ACCEPTANCE_MIN_FILES', 20 )
			max_files = self.get_evidence_int( 'BATCH_ACCEPTANCE_MAX_FILES', 50 )
			batch_tested = self.get_evidence_bool( 'PROTOTYPE_BATCH_SCALE_TESTED', False )
			batch_passed = self.get_evidence_bool( 'PROTOTYPE_BATCH_SCALE_PASSED', False )
			effective_count = max( processed_count, report_count )
			
			if min_files <= effective_count <= max_files and batch_passed:
				status = ACCEPTANCE_MET
				evidence = f'Prototype-scale run processed {effective_count} labels within the {min_files}–{max_files} target range.'
				recommendation = 'Retain batch summary, performance, and acceptance exports.'
			elif min_files <= effective_count <= max_files:
				status = ACCEPTANCE_PARTIAL
				evidence = f'Run size was within range at {effective_count} labels, but explicit pass evidence was not supplied.'
				recommendation = 'Mark the acceptance harness batch-scale result after reviewing outputs.'
			elif effective_count > 0:
				status = ACCEPTANCE_PARTIAL
				evidence = f'Run processed {effective_count} labels; required prototype range is {min_files}–{max_files}.'
				recommendation = 'Run a representative 20–50 label batch.'
			elif batch_tested and not batch_passed:
				status = ACCEPTANCE_NOT_MET
				evidence = 'Supplemental batch-scale evidence indicates the prototype-scale test did not pass.'
				recommendation = 'Review failed files, timing, manifest matching, and worker settings.'
			else:
				status = ACCEPTANCE_NOT_EVALUATED
				evidence = 'No processed-label count was available for prototype-scale evaluation.'
				recommendation = 'Run a representative 20–50 label batch.'
			
			return self.create_status(
				REQUIREMENT_SCALABILITY,
				'Prototype-Level Scalability',
				status,
				evidence,
				recommendation,
				{
						'processed_count': processed_count,
						'report_count': report_count,
						'effective_count': effective_count,
						'minimum_target_files': min_files,
						'maximum_target_files': max_files,
						'prototype_batch_scale_tested': batch_tested,
						'prototype_batch_scale_passed': batch_passed
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
				'Inspect batch-processing evidence and the acceptance checker error log.'
			)
	
	def evaluate_security_and_data_handling( self ) -> List[ RequirementStatus ]:
		"""Evaluates security and data-handling posture.

		Purpose:
			Determine whether the prototype is configured for local OCR, avoids external ML
			endpoints, avoids raw OCR text logging, avoids persistent upload storage, and supports
			the no-long-term-storage requirement.

		Returns:
			List[RequirementStatus]: Security and data-handling acceptance records.
		"""
		try:
			allow_external_ml = self.get_evidence_bool( 'ALLOW_EXTERNAL_ML_ENDPOINTS', False )
			require_local_ocr = self.get_evidence_bool( 'REQUIRE_LOCAL_OCR', True )
			enable_raw_text_logging = self.get_evidence_bool( 'ENABLE_RAW_TEXT_LOGGING', False )
			enable_file_path_logging = self.get_evidence_bool( 'ENABLE_FILE_PATH_LOGGING', False )
			enable_upload_persistence = self.get_evidence_bool( 'ENABLE_UPLOAD_PERSISTENCE', False )
			long_term_storage_disabled = self.get_evidence_bool( 'LONG_TERM_STORAGE_DISABLED',
				True )
			log_retention_days = self.get_evidence_int( 'LOG_RETENTION_DAYS', 14 )
			security_met = require_local_ocr and not allow_external_ml and not enable_raw_text_logging
			data_met = not enable_upload_persistence and long_term_storage_disabled and not enable_raw_text_logging
			
			security_status = ACCEPTANCE_MET if security_met else ACCEPTANCE_NOT_MET
			data_status = ACCEPTANCE_MET if data_met else ACCEPTANCE_NOT_MET
			
			security_evidence = (
					f'Local OCR required: {require_local_ocr}; external ML endpoints allowed: '
					f'{allow_external_ml}; raw text logging enabled: {enable_raw_text_logging}; '
					f'file path logging enabled: {enable_file_path_logging}.'
			)
			data_evidence = (
					f'Upload persistence enabled: {enable_upload_persistence}; long-term storage disabled: '
					f'{long_term_storage_disabled}; raw text logging enabled: {enable_raw_text_logging}; '
					f'log retention days: {log_retention_days}.'
			)
			
			return [
					self.create_status(
						REQUIREMENT_SECURITY,
						'Security and Firewall-Safe Prototype Posture',
						security_status,
						security_evidence,
						'Keep local OCR enabled, external ML endpoints disabled, and raw OCR text out of logs.',
						{
								'require_local_ocr': require_local_ocr,
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
						'Use temporary-file cleanup and avoid persistent image or OCR data storage.',
						{
								'enable_upload_persistence': enable_upload_persistence,
								'long_term_storage_disabled': long_term_storage_disabled,
								'enable_raw_text_logging': enable_raw_text_logging,
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
		"""Evaluates accessibility, usability, feedback, and interface simplicity posture.

		Purpose:
			Evaluate whether the prototype provides Simple Mode, low-technical-comfort workflow
			evidence, large controls, minimal navigation, high contrast, large text, keyboard
			validation, progress evidence, confidence evidence, and non-hover mismatch guidance.

		Returns:
			List[RequirementStatus]: Usability, interface simplicity, accessibility, and feedback
			acceptance records.
		"""
		try:
			default_simple_mode = self.get_evidence_bool( 'DEFAULT_SIMPLE_MODE', True )
			default_high_contrast = self.get_evidence_bool( 'DEFAULT_HIGH_CONTRAST_MODE', False )
			default_large_text = self.get_evidence_bool( 'DEFAULT_LARGE_TEXT_MODE', False )
			keyboard_passed = self.get_evidence_bool( 'KEYBOARD_ACCESSIBILITY_PASSED', False )
			workflow_validated = self.get_evidence_bool( 'LOW_TECH_REVIEWER_WORKFLOW_VALIDATED',
				False )
			large_buttons_present = self.get_evidence_bool( 'LARGE_BUTTONS_PRESENT', True )
			minimal_navigation_validated = self.get_evidence_bool( 'MINIMAL_NAVIGATION_VALIDATED',
				False )
			has_reviewer_action = 'Reviewer Action' in self._comparison_dataframe.columns
			has_confidence = (
					'Confidence' in self._comparison_dataframe.columns
					or 'Confidence' in self._detail_dataframe.columns
			)
			has_progress_evidence = (
					self._result.performance_summary.total_files > 0
					or self.get_evidence_bool( 'PROGRESS_INDICATORS_DISPLAYED', False )
			)
			has_non_hover_guidance = (
					has_reviewer_action
					or self.get_evidence_bool( 'NON_HOVER_MISMATCH_GUIDANCE_DISPLAYED', False )
			)
			
			usability_status = ACCEPTANCE_MET if default_simple_mode and workflow_validated else ACCEPTANCE_PARTIAL
			interface_status = ACCEPTANCE_MET if large_buttons_present and minimal_navigation_validated else ACCEPTANCE_PARTIAL
			accessibility_status = ACCEPTANCE_MET if (
					default_high_contrast and default_large_text and keyboard_passed
			) else ACCEPTANCE_PARTIAL
			feedback_status = ACCEPTANCE_MET if (
					has_progress_evidence and has_confidence and has_non_hover_guidance
			) else ACCEPTANCE_PARTIAL
			
			return [
					self.create_status(
						REQUIREMENT_USABILITY,
						'Simple Low-Technical-Comfort Usability',
						usability_status,
						(
								f'Default Simple Mode configured: {default_simple_mode}; low-technical-comfort '
								f'workflow validated: {workflow_validated}.'
						),
						'Complete and retain a reviewer walkthrough with non-technical users.',
						{
								'default_simple_mode': default_simple_mode,
								'workflow_validated': workflow_validated
						}
					),
					self.create_status(
						REQUIREMENT_INTERFACE_SIMPLICITY,
						'Interface Simplicity',
						interface_status,
						(
								f'Large buttons present: {large_buttons_present}; minimal navigation validated: '
								f'{minimal_navigation_validated}; Simple Mode default: {default_simple_mode}.'
						),
						'Confirm upload-run-review flow requires no more than two or three reviewer actions.',
						{
								'large_buttons_present': large_buttons_present,
								'minimal_navigation_validated': minimal_navigation_validated,
								'default_simple_mode': default_simple_mode
						}
					),
					self.create_status(
						REQUIREMENT_ACCESSIBILITY,
						'Accessibility',
						accessibility_status,
						(
								f'High contrast default: {default_high_contrast}; large text default: '
								f'{default_large_text}; keyboard validation passed: {keyboard_passed}.'
						),
						'Run and export the manual browser keyboard accessibility checklist.',
						{
								'default_high_contrast': default_high_contrast,
								'default_large_text': default_large_text,
								'keyboard_accessibility_passed': keyboard_passed,
								'accessibility_dataframe_rows': len( self._accessibility_dataframe )
						}
					),
					self.create_status(
						REQUIREMENT_FEEDBACK,
						'Reviewer Feedback, Progress, Confidence, and Mismatch Guidance',
						feedback_status,
						(
								f'Progress evidence: {has_progress_evidence}; confidence evidence: '
								f'{has_confidence}; non-hover mismatch guidance: {has_non_hover_guidance}.'
						),
						'Retain screenshots and output CSVs showing progress, confidence, and mismatch guidance.',
						{
								'has_progress_evidence': has_progress_evidence,
								'has_confidence_evidence': has_confidence,
								'has_non_hover_mismatch_guidance': has_non_hover_guidance,
								'has_reviewer_action_column': has_reviewer_action
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
		"""Evaluates Azure/local OCR posture and COLA non-integration posture.

		Purpose:
			Evaluate whether the prototype has Azure-compatible local-OCR deployment evidence,
			whether external ML endpoints remain disabled, whether Azure readiness or smoke-test
			evidence is available, and whether the prototype remains standalone without direct
			COLA integration.

		Returns:
			List[RequirementStatus]: Infrastructure and integration acceptance records.
		"""
		try:
			deployment_target = self.get_evidence_text( 'DEPLOYMENT_TARGET', 'local' )
			require_local_ocr = self.get_evidence_bool( 'REQUIRE_LOCAL_OCR', True )
			allow_external_ml = self.get_evidence_bool( 'ALLOW_EXTERNAL_ML_ENDPOINTS', False )
			azure_smoke_test_passed = self.get_evidence_bool( 'AZURE_SMOKE_TEST_PASSED', False )
			azure_ready_artifacts_present = self.get_evidence_bool( 'AZURE_READY_ARTIFACTS_PRESENT',
				False )
			cola_integration_enabled = self.get_evidence_bool( 'COLA_INTEGRATION_ENABLED', False )
			
			if azure_smoke_test_passed and require_local_ocr and not allow_external_ml:
				infrastructure_status = ACCEPTANCE_MET
			elif azure_ready_artifacts_present and require_local_ocr and not allow_external_ml:
				infrastructure_status = ACCEPTANCE_PARTIAL
			else:
				infrastructure_status = ACCEPTANCE_NOT_MET if allow_external_ml else ACCEPTANCE_PARTIAL
			
			cola_status = ACCEPTANCE_NOT_MET if cola_integration_enabled else ACCEPTANCE_MET
			
			return [
					self.create_status(
						REQUIREMENT_INFRASTRUCTURE,
						'Azure-Compatible Local OCR Infrastructure',
						infrastructure_status,
						(
								f'Deployment target: {deployment_target}; local OCR required: {require_local_ocr}; '
								f'external ML endpoints allowed: {allow_external_ml}; Azure-ready artifacts: '
								f'{azure_ready_artifacts_present}; Azure smoke test passed: {azure_smoke_test_passed}.'
						),
						'Add and test Docker/Azure deployment artifacts, then retain Azure smoke-test evidence.',
						{
								'deployment_target': deployment_target,
								'require_local_ocr': require_local_ocr,
								'allow_external_ml_endpoints': allow_external_ml,
								'azure_ready_artifacts_present': azure_ready_artifacts_present,
								'azure_smoke_test_passed': azure_smoke_test_passed,
								'deployment_dataframe_rows': len( self._deployment_dataframe )
						}
					),
					self.create_status(
						REQUIREMENT_COLA,
						'No Direct COLA Integration',
						cola_status,
						f'COLA integration enabled: {cola_integration_enabled}.',
						'Keep the prototype standalone unless future procurement scope changes.',
						{
								'cola_integration_enabled': cola_integration_enabled
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
	
	def order_requirements( self, requirements: List[ RequirementStatus ] ) -> List[
		RequirementStatus ]:
		"""Sorts requirement results by stakeholder requirement order.

		Purpose:
			Order requirement records according to the stakeholder requirements sequence so
			dashboards, CSV exports, JSON exports, and Markdown reports appear in a predictable
			and review-friendly order.

		Args:
			requirements (List[RequirementStatus]): Requirement records to sort.

		Returns:
			List[RequirementStatus]: Sorted requirement records.
		"""
		try:
			order_map = {
					requirement_id: index
					for index, requirement_id in enumerate( REQUIREMENT_ORDER )
			}
			return sorted(
				requirements,
				key=lambda requirement: order_map.get( requirement.requirement_id, 999 )
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'order_requirements( self, requirements: List[RequirementStatus] ) -> List[RequirementStatus]'
			Logger( ).write( error )
			return requirements
	
	def evaluate_batch_result( self, result: BatchProcessingResult,
			summary_dataframe: Optional[ pd.DataFrame ] = None,
			detail_dataframe: Optional[ pd.DataFrame ] = None,
			comparison_dataframe: Optional[ pd.DataFrame ] = None,
			performance_dataframe: Optional[ pd.DataFrame ] = None,
			accessibility_dataframe: Optional[ pd.DataFrame ] = None,
			deployment_dataframe: Optional[ pd.DataFrame ] = None,
			evidence: Optional[ Dict[ str, object ] ] = None ) -> AcceptanceSummary:
		"""Evaluates a completed batch-processing result against stakeholder requirements.

		Purpose:
			Evaluate a completed batch-processing result and optional supporting evidence against
			the full stakeholder requirement set. This method is the primary batch acceptance
			entry point and produces an ``AcceptanceSummary`` suitable for dashboard display and
			export.

		Args:
			result (BatchProcessingResult): Completed batch-processing result.
			summary_dataframe (Optional[pd.DataFrame]): Optional summary output DataFrame.
			detail_dataframe (Optional[pd.DataFrame]): Optional rule-detail output DataFrame.
			comparison_dataframe (Optional[pd.DataFrame]): Optional comparison output DataFrame.
			performance_dataframe (Optional[pd.DataFrame]): Optional performance output DataFrame.
			accessibility_dataframe (Optional[pd.DataFrame]): Optional accessibility checklist
				DataFrame.
			deployment_dataframe (Optional[pd.DataFrame]): Optional deployment evidence DataFrame.
			evidence (Optional[Dict[str, object]]): Optional supplemental acceptance evidence.

		Returns:
			AcceptanceSummary: Complete stakeholder acceptance summary.
		"""
		try:
			throw_if( 'result', result )
			
			self._result = result
			self._summary_dataframe = self.normalize_dataframe( summary_dataframe )
			self._detail_dataframe = self.normalize_dataframe( detail_dataframe )
			self._comparison_dataframe = self.normalize_dataframe( comparison_dataframe )
			self._performance_dataframe = self.normalize_dataframe( performance_dataframe )
			self._accessibility_dataframe = self.normalize_dataframe( accessibility_dataframe )
			self._deployment_dataframe = self.normalize_dataframe( deployment_dataframe )
			self._evidence = evidence or { }
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
			self._requirements = self.order_requirements( self._requirements )
			
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
	
	def evaluate_manual_or_batch_result( self, result: Optional[ BatchProcessingResult ] = None,
			report: Optional[ LabelVerificationReport ] = None,
			summary_dataframe: Optional[ pd.DataFrame ] = None,
			detail_dataframe: Optional[ pd.DataFrame ] = None,
			comparison_dataframe: Optional[ pd.DataFrame ] = None,
			performance_dataframe: Optional[ pd.DataFrame ] = None,
			accessibility_dataframe: Optional[ pd.DataFrame ] = None,
			deployment_dataframe: Optional[ pd.DataFrame ] = None,
			evidence: Optional[ Dict[ str, object ] ] = None ) -> AcceptanceSummary:
		"""Evaluates either a batch result or one manual label report.

		Purpose:
			Use the same acceptance pipeline for both manifest-driven batch runs and manual
			single-label runs. When a batch result is supplied, it is evaluated directly. When
			only a single label report is supplied, the report is wrapped in a temporary
			``BatchProcessingResult`` so all requirement evaluators and export formats remain
			consistent.

		Args:
			result (Optional[BatchProcessingResult]): Optional completed batch-processing result.
			report (Optional[LabelVerificationReport]): Optional manual single-label report.
			summary_dataframe (Optional[pd.DataFrame]): Optional summary output DataFrame.
			detail_dataframe (Optional[pd.DataFrame]): Optional detail output DataFrame.
			comparison_dataframe (Optional[pd.DataFrame]): Optional comparison output DataFrame.
			performance_dataframe (Optional[pd.DataFrame]): Optional performance output DataFrame.
			accessibility_dataframe (Optional[pd.DataFrame]): Optional accessibility checklist
				DataFrame.
			deployment_dataframe (Optional[pd.DataFrame]): Optional deployment evidence DataFrame.
			evidence (Optional[Dict[str, object]]): Optional supplemental acceptance evidence.

		Returns:
			AcceptanceSummary: Complete stakeholder acceptance summary.
		"""
		try:
			if result is None:
				throw_if( 'report', report )
				result = BatchProcessingResult( )
				result.batch_report.add_report( report )
				result.processed_files.append( report.file_name )
			
			return self.evaluate_batch_result(
				result=result,
				summary_dataframe=summary_dataframe,
				detail_dataframe=detail_dataframe,
				comparison_dataframe=comparison_dataframe,
				performance_dataframe=performance_dataframe,
				accessibility_dataframe=accessibility_dataframe,
				deployment_dataframe=deployment_dataframe,
				evidence=evidence
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate_manual_or_batch_result( self, *args ) -> AcceptanceSummary'
			Logger( ).write( error )
			return AcceptanceSummary(
				requirements=[
						self.create_status(
							'ACCEPTANCE',
							'Acceptance Evaluation',
							ACCEPTANCE_NOT_EVALUATED,
							'Acceptance evaluation could not be completed for the supplied manual or batch result.',
							'Inspect the acceptance checker error log.'
						)
				]
			)