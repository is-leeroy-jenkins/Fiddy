'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                acceptance_checker.py
      Author:                  Terry D. Eppler
      Created:                 06-06-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-07-2026
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
        Provides requirement-level acceptance evaluation for the Fiddy prototype.

        This module converts verification results, output DataFrames, configuration posture,
        data-retention policy, deployment evidence, accessibility evidence, and supplemental
        runtime evidence into stakeholder requirement status records. It uses only the statuses
        Met, Partially Met, Not Met, and Not Applicable.

        This checker does not perform OCR, deploy infrastructure, run Streamlit, execute browser
        accessibility checks, or persist files. It evaluates the evidence produced by those
        runtime paths and classifies each stakeholder requirement based on the supplied code
        outputs and active configuration.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field

import config as cfg
from booger import Error, Logger
from config import throw_if
from src.batch_processor import BatchProcessingResult
from src.constants import STATUS_FAIL, STATUS_REVIEW, STATUS_WARNING
from src.data_retention import DataRetentionPolicy
from src.models import BatchVerificationReport, LabelVerificationReport

ACCEPTANCE_MET: str = 'Met'
ACCEPTANCE_PARTIAL: str = 'Partially Met'
ACCEPTANCE_NOT_MET: str = 'Not Met'
ACCEPTANCE_NOT_APPLICABLE: str = 'Not Applicable'

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

class RequirementStatus( BaseModel ):
	"""Represent one stakeholder requirement acceptance result.

	Purpose:
		Store a single requirement-level status result using a flat export-friendly structure.
		Each record includes the requirement identifier, requirement name, status, evidence,
		recommendation, evaluation timestamp, and optional metrics.

	Attributes:
		requirement_id (str): Stakeholder requirement identifier.
		requirement_name (str): Human-readable requirement name.
		status (str): One of Met, Partially Met, Not Met, or Not Applicable.
		evidence (str): Plain-language evidence supporting the status.
		recommendation (str): Recommended code or configuration action.
		evaluated_on (str): UTC evaluation timestamp.
		metrics (Dict[str, object]): Machine-readable supporting metrics.
	"""
	
	requirement_id: str = Field( default='' )
	requirement_name: str = Field( default='' )
	status: str = Field( default=ACCEPTANCE_NOT_MET )
	evidence: str = Field( default='' )
	recommendation: str = Field( default='' )
	evaluated_on: str = Field(
		default_factory=lambda: datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' ) )
	metrics: Dict[ str, object ] = Field( default_factory=dict )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert the requirement status into a flat record.

		Purpose:
			Create a dictionary suitable for DataFrame display, CSV export, JSON serialization,
			and Markdown rendering.

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
					'Status': ACCEPTANCE_NOT_MET,
					'Evidence': 'Requirement status record could not be rendered.',
					'Recommendation': 'Inspect the acceptance checker error log.',
					'Evaluated On': '',
					'Metrics': { }
			}

class AcceptanceSummary( BaseModel ):
	"""Represent the complete acceptance evaluation for one Fiddy run.

	Purpose:
		Aggregate all requirement-level status records and provide display/export helpers for
		counts, percentage, DataFrame conversion, JSON serialization, and Markdown reporting.

	Attributes:
		requirements (List[RequirementStatus]): Requirement-level status records.
		created_on (str): UTC timestamp when the summary was created.
	"""
	
	requirements: List[ RequirementStatus ] = Field( default_factory=list )
	created_on: str = Field(
		default_factory=lambda: datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' ) )
	
	def status_counts( self ) -> Dict[ str, int ]:
		"""Count requirement records by status.

		Purpose:
			Return status counts for dashboards, reports, and package manifests.

		Returns:
			Dict[str, int]: Counts keyed by status.
		"""
		try:
			counts = {
					ACCEPTANCE_MET: 0,
					ACCEPTANCE_PARTIAL: 0,
					ACCEPTANCE_NOT_MET: 0,
					ACCEPTANCE_NOT_APPLICABLE: 0
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
					ACCEPTANCE_NOT_APPLICABLE: 0
			}
	
	def acceptance_percentage( self ) -> float:
		"""Calculate the percentage of applicable requirements marked Met.

		Purpose:
			Calculate acceptance percentage by dividing Met requirements by all requirements that
			are not marked Not Applicable.

		Returns:
			float: Acceptance percentage rounded to two decimal places.
		"""
		try:
			applicable = [
					requirement
					for requirement in self.requirements
					if requirement.status != ACCEPTANCE_NOT_APPLICABLE
			]
			
			if not applicable:
				return 0.0
			
			met_count = sum(
				1
				for requirement in applicable
				if requirement.status == ACCEPTANCE_MET
			)
			
			return round( (met_count / len( applicable )) * 100.0, 2 )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'acceptance_percentage( self ) -> float'
			Logger( ).write( error )
			return 0.0
	
	def to_records( self ) -> List[ Dict[ str, object ] ]:
		"""Convert requirement statuses into flat records.

		Purpose:
			Return every requirement status as a dictionary for display and export.

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
		"""Convert the acceptance summary into a DataFrame.

		Purpose:
			Create a DataFrame for Streamlit display, CSV export, and acceptance package output.

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
	
	def to_json( self ) -> str:
		"""Serialize the acceptance summary as formatted JSON.

		Purpose:
			Create a JSON payload containing creation time, acceptance percentage, status counts,
			and requirement records.

		Returns:
			str: Formatted JSON string.
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
		"""Render the acceptance summary as Markdown.

		Purpose:
			Create a stakeholder-readable Markdown report containing counts and each requirement
			status.

		Returns:
			str: Markdown acceptance report.
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
					f'- Not Applicable: {counts.get( ACCEPTANCE_NOT_APPLICABLE, 0 )}',
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

class AcceptanceChecker( ):
	"""Evaluate Fiddy runtime evidence against stakeholder requirements.

	Purpose:
		Inspect completed verification results, output DataFrames, configuration flags,
		data-retention settings, deployment settings, accessibility outputs, and supplemental
		evidence to create requirement-level acceptance records.

	Attributes:
		_result (BatchProcessingResult): Active batch processing result.
		_summary_dataframe (pd.DataFrame): Batch summary DataFrame.
		_detail_dataframe (pd.DataFrame): Detail DataFrame.
		_comparison_dataframe (pd.DataFrame): Comparison DataFrame.
		_performance_dataframe (pd.DataFrame): Performance DataFrame.
		_accessibility_dataframe (pd.DataFrame): Accessibility checklist DataFrame.
		_deployment_dataframe (pd.DataFrame): Deployment evidence DataFrame.
		_evidence (Dict[str, object]): Supplemental evidence dictionary.
		_requirements (List[RequirementStatus]): Evaluated requirement statuses.
		_policy (DataRetentionPolicy): Active no-persistence policy.
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
	_policy: DataRetentionPolicy
	
	def __init__( self ) -> None:
		"""Initialize the acceptance checker.

		Purpose:
			Create empty DataFrame placeholders, an empty evidence dictionary, an empty
			requirement list, and the active data-retention policy.

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
		self._policy = DataRetentionPolicy( )
	
	def create_status( self, requirement_id: str, requirement_name: str, status: str,
			evidence: str, recommendation: str = '',
			metrics: Optional[ Dict[ str, object ] ] = None ) -> RequirementStatus:
		"""Create one requirement status record.

		Purpose:
			Centralize requirement status construction and enforce valid status text.

		Args:
			requirement_id (str): Stakeholder requirement identifier.
			requirement_name (str): Human-readable requirement name.
			status (str): Met, Partially Met, Not Met, or Not Applicable.
			evidence (str): Evidence statement.
			recommendation (str): Recommended action.
			metrics (Optional[Dict[str, object]]): Supporting metrics.

		Returns:
			RequirementStatus: Requirement status record.
		"""
		try:
			throw_if( 'requirement_id', requirement_id )
			throw_if( 'requirement_name', requirement_name )
			throw_if( 'status', status )
			throw_if( 'evidence', evidence )
			
			if status not in (
						ACCEPTANCE_MET,
						ACCEPTANCE_PARTIAL,
						ACCEPTANCE_NOT_MET,
						ACCEPTANCE_NOT_APPLICABLE):
				raise ValueError( f'Unsupported acceptance status: {status}' )
			
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
				status=ACCEPTANCE_NOT_MET,
				evidence='Requirement status could not be created.',
				recommendation='Inspect the acceptance checker error log.',
				metrics=metrics or { }
			)
	
	def normalize_dataframe( self, dataframe: Optional[ pd.DataFrame ] ) -> pd.DataFrame:
		"""Normalize an optional DataFrame.

		Purpose:
			Return an empty DataFrame when callers pass ``None``.

		Args:
			dataframe (Optional[pd.DataFrame]): Optional DataFrame.

		Returns:
			pd.DataFrame: Source DataFrame or empty fallback.
		"""
		try:
			return dataframe if dataframe is not None else pd.DataFrame( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_dataframe( self, dataframe: Optional[pd.DataFrame] ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def get_evidence_bool( self, name: str, default: bool = False ) -> bool:
		"""Read a Boolean value from supplemental evidence or configuration.

		Purpose:
			Prefer runtime evidence and fall back to configuration.

		Args:
			name (str): Evidence key.
			default (bool): Default value.

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
		"""Read an integer value from supplemental evidence or configuration.

		Purpose:
			Prefer runtime evidence and fall back to configuration.

		Args:
			name (str): Evidence key.
			default (int): Default value.

		Returns:
			int: Resolved integer value.
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
		"""Read a text value from supplemental evidence or configuration.

		Purpose:
			Prefer runtime evidence and fall back to configuration.

		Args:
			name (str): Evidence key.
			default (str): Default value.

		Returns:
			str: Resolved text value.
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
	
	def get_batch_report( self ) -> BatchVerificationReport:
		"""Return the active batch verification report.

		Purpose:
			Return the batch report from the active processing result.

		Returns:
			BatchVerificationReport: Active batch report or empty fallback.
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
		"""Return all active label-level reports.

		Purpose:
			Flatten the batch report into label-level reports.

		Returns:
			List[LabelVerificationReport]: Label reports.
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
		"""Return all rule-result objects.

		Purpose:
			Flatten every report's rule results into one list.

		Returns:
			List[object]: Rule-result objects.
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
	
	def dataframe_has_columns( self, dataframe: pd.DataFrame, columns: List[ str ] ) -> bool:
		"""Determine whether a DataFrame has all required columns.

		Purpose:
			Check reviewer-facing output schemas.

		Args:
			dataframe (pd.DataFrame): DataFrame to inspect.
			columns (List[str]): Required columns.

		Returns:
			bool: True when all columns are present.
		"""
		try:
			if dataframe is None or dataframe.empty:
				return False
			
			return set( columns ).issubset( set( dataframe.columns ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'dataframe_has_columns( self, *args ) -> bool'
			Logger( ).write( error )
			return False
	
	def count_reports_with_ocr_text( self ) -> int:
		"""Count reports with OCR text.

		Purpose:
			Count extracted labels that contain readable text.

		Returns:
			int: Count of reports with OCR text.
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
		"""Count reports with structured extracted fields.

		Purpose:
			Count reports where at least one target label field was populated.

		Returns:
			int: Count of reports with structured extracted values.
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
		"""Count reports with rule results.

		Purpose:
			Count label reports that contain verification rule results.

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
			Count reviewer-visible non-pass report outcomes.

		Returns:
			int: Count of reports with non-pass status.
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
		"""Evaluate label extraction.

		Purpose:
			Classify extraction based on label reports, OCR text, structured fields, and
			imperfect-image support evidence.

		Returns:
			RequirementStatus: Label extraction status.
		"""
		try:
			total_reports = len( self.get_reports( ) )
			ocr_text_count = self.count_reports_with_ocr_text( )
			structured_count = self.count_reports_with_structured_fields( )
			imperfect_image_evidence = self.get_evidence_bool( 'IMPERFECT_IMAGE_TESTED', False )
			
			if total_reports > 0 and ocr_text_count > 0 and structured_count > 0:
				status = ACCEPTANCE_MET
				evidence = (
						f'OCR text was produced for {ocr_text_count} reports and structured fields '
						f'were produced for {structured_count} reports.'
				)
				recommendation = 'Retain extraction and visual-quality outputs.'
			else:
				status = ACCEPTANCE_NOT_MET
				evidence = (
						f'Total reports: {total_reports}; OCR text count: {ocr_text_count}; '
						f'structured-field report count: {structured_count}.'
				)
				recommendation = 'Correct OCR, preprocessing, or field extraction.'
			
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
						'imperfect_image_evidence': imperfect_image_evidence
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
				ACCEPTANCE_NOT_MET,
				'Label extraction could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_application_comparison( self ) -> RequirementStatus:
		"""Evaluate application-versus-label comparison.

		Purpose:
			Check comparison records, reviewer columns, fuzzy rule results, and government warning
			rules.

		Returns:
			RequirementStatus: Comparison status.
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
			rule_ids = [
					str( getattr( result, 'rule_id', '' ) )
					for result in self.get_result_values( )
			]
			has_fuzzy_rules = any(
				rule_id in ('brand_name_match', 'class_type_match')
				for rule_id in rule_ids
			)
			has_warning_exact_rule = 'government_warning_exact' in rule_ids
			has_warning_visual_rule = 'government_warning_visual_format' in rule_ids
			
			if (
					total_reports > 0
					and rule_report_count > 0
					and has_required_columns
					and has_fuzzy_rules
					and has_warning_exact_rule
					and has_warning_visual_rule):
				status = ACCEPTANCE_MET
				evidence = 'Comparison output, fuzzy rules, exact warning rule, and visual warning rule are present.'
				recommendation = 'Retain redacted comparison output.'
			elif total_reports > 0 and rule_report_count > 0:
				status = ACCEPTANCE_PARTIAL
				evidence = (
						f'Rule results exist, but required columns or expected rule coverage are incomplete. '
						f'Required columns present: {has_required_columns}; fuzzy rules: {has_fuzzy_rules}; '
						f'exact warning rule: {has_warning_exact_rule}; visual warning rule: {has_warning_visual_rule}.'
				)
				recommendation = 'Complete comparison schema and rule coverage.'
			else:
				status = ACCEPTANCE_NOT_MET
				evidence = 'No usable application-versus-label rule comparison evidence was found.'
				recommendation = 'Correct label verifier and comparison output generation.'
			
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
						'has_government_warning_visual_rule': has_warning_visual_rule
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
				ACCEPTANCE_NOT_MET,
				'Application comparison could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_batch_processing( self ) -> RequirementStatus:
		"""Evaluate batch processing.

		Purpose:
			Classify whether multiple uploaded labels produced per-label reports.

		Returns:
			RequirementStatus: Batch processing status.
		"""
		try:
			report_count = len( self.get_reports( ) )
			processed_count = len( self._result.processed_files )
			skipped_count = len( self._result.skipped_files )
			
			if report_count > 1 and processed_count > 1:
				status = ACCEPTANCE_MET
				evidence = f'Batch run produced {report_count} reports and {processed_count} processed files.'
				recommendation = 'Retain batch summary output.'
			elif report_count == 1 or processed_count == 1:
				status = ACCEPTANCE_PARTIAL
				evidence = 'One label was processed; batch capability was not fully exercised.'
				recommendation = 'Run a multi-label manifest or ZIP upload.'
			else:
				status = ACCEPTANCE_NOT_MET
				evidence = 'No batch-processing reports were produced.'
				recommendation = 'Correct manifest/file matching and batch execution.'
			
			return self.create_status(
				REQUIREMENT_FUNCTIONAL_BATCH,
				'Batch Processing',
				status,
				evidence,
				recommendation,
				{
						'report_count': report_count,
						'processed_count': processed_count,
						'skipped_count': skipped_count
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
				ACCEPTANCE_NOT_MET,
				'Batch processing could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_performance( self ) -> RequirementStatus:
		"""Evaluate five-second performance.

		Purpose:
			Classify performance based on performance summary and supplemental SLA flags.

		Returns:
			RequirementStatus: Performance status.
		"""
		try:
			summary = self._result.performance_summary
			total_files = int( getattr( summary, 'total_files', 0 ) )
			acceptance = getattr( summary, 'acceptance_result', None )
			manual_sla_tested = self.get_evidence_bool( 'PERFORMANCE_SLA_TESTED', False )
			manual_sla_passed = self.get_evidence_bool( 'PERFORMANCE_SLA_PASSED', False )
			
			if acceptance is not None and bool( getattr( acceptance, 'meets_acceptance', False ) ):
				status = ACCEPTANCE_MET
				evidence = str(
					getattr(
						acceptance,
						'message',
						'Measured performance met configured five-second targets.'
					)
				)
				recommendation = 'Retain performance output.'
			elif manual_sla_tested and manual_sla_passed:
				status = ACCEPTANCE_MET
				evidence = 'Supplemental performance evidence indicates the five-second SLA passed.'
				recommendation = 'Retain performance output.'
			elif total_files > 0 or manual_sla_tested:
				status = ACCEPTANCE_NOT_MET
				evidence = str(
					getattr(
						acceptance,
						'message',
						'Performance did not meet configured five-second targets.'
					)
				)
				recommendation = 'Implement hard deadline behavior or optimize OCR path.'
			else:
				status = ACCEPTANCE_NOT_MET
				evidence = 'No timed performance results were supplied.'
				recommendation = 'Run verification with performance monitoring enabled.'
			
			metrics = summary.to_record( ) if hasattr( summary, 'to_record' ) else { }
			metrics.update(
				{
						'performance_sla_tested': manual_sla_tested,
						'performance_sla_passed': manual_sla_passed
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
				ACCEPTANCE_NOT_MET,
				'Performance could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_output( self ) -> RequirementStatus:
		"""Evaluate output availability.

		Purpose:
			Check summary, detail, comparison, performance, and acceptance export availability.

		Returns:
			RequirementStatus: Output status.
		"""
		try:
			has_summary = not self._summary_dataframe.empty
			has_detail = not self._detail_dataframe.empty
			has_comparison = not self._comparison_dataframe.empty
			has_performance = not self._performance_dataframe.empty
			has_acceptance_export = self.get_evidence_bool( 'ACCEPTANCE_EXPORT_AVAILABLE', False )
			
			if has_summary and has_detail and has_comparison and has_performance and has_acceptance_export:
				status = ACCEPTANCE_MET
				evidence = 'Summary, detail, comparison, performance, and acceptance outputs are available.'
				recommendation = 'Retain redacted outputs.'
			elif has_summary and has_detail and has_comparison:
				status = ACCEPTANCE_PARTIAL
				evidence = 'Core outputs are available, but performance or acceptance output is missing.'
				recommendation = 'Wire performance and acceptance outputs.'
			else:
				status = ACCEPTANCE_NOT_MET
				evidence = 'Required reviewer outputs are incomplete.'
				recommendation = 'Correct report generation and download preparation.'
			
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
				ACCEPTANCE_NOT_MET,
				'Output could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_reliability( self ) -> RequirementStatus:
		"""Evaluate reliability.

		Purpose:
			Check completed reports, warnings, skipped files, low-quality-image handling, and
			false-positive variation handling.

		Returns:
			RequirementStatus: Reliability status.
		"""
		try:
			report_count = len( self.get_reports( ) )
			error_count = len( self._result.errors )
			warning_count = len( self._result.warnings )
			skipped_count = len( self._result.skipped_files )
			low_quality_tested = self.get_evidence_bool( 'LOW_QUALITY_IMAGE_TESTED', False )
			false_positive_tested = self.get_evidence_bool(
				'FALSE_POSITIVE_VARIATION_TESTED',
				False
			)
			
			if report_count > 0 and error_count == 0:
				status = ACCEPTANCE_MET
				evidence = (
						f'Run produced {report_count} reports with {warning_count} warnings and '
						f'{skipped_count} skipped files.'
				)
				recommendation = 'Retain warning/review outputs.'
			elif report_count > 0:
				status = ACCEPTANCE_PARTIAL
				evidence = f'Run produced reports but also had {error_count} batch-level errors.'
				recommendation = 'Correct batch-level errors.'
			else:
				status = ACCEPTANCE_NOT_MET
				evidence = 'No completed reports were available.'
				recommendation = 'Correct processing failures.'
			
			return self.create_status(
				REQUIREMENT_RELIABILITY,
				'Reliability and Graceful Error Handling',
				status,
				evidence,
				recommendation,
				{
						'report_count': report_count,
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
				ACCEPTANCE_NOT_MET,
				'Reliability could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_scalability( self ) -> RequirementStatus:
		"""Evaluate 20–50 label scalability.

		Purpose:
			Classify prototype-scale processing based on processed report count and configured
			batch bounds.

		Returns:
			RequirementStatus: Scalability status.
		"""
		try:
			processed_count = len( self._result.processed_files )
			report_count = len( self.get_reports( ) )
			effective_count = max( processed_count, report_count )
			min_files = self.get_evidence_int( 'BATCH_ACCEPTANCE_MIN_FILES', 20 )
			max_files = self.get_evidence_int( 'BATCH_ACCEPTANCE_MAX_FILES', 50 )
			
			if min_files <= effective_count <= max_files:
				status = ACCEPTANCE_MET
				evidence = f'Processed/report count {effective_count} is within required {min_files}–{max_files} range.'
				recommendation = 'Retain batch summary and performance outputs.'
			elif effective_count > 0:
				status = ACCEPTANCE_PARTIAL
				evidence = f'Processed/report count is {effective_count}; required range is {min_files}–{max_files}.'
				recommendation = 'Run a representative 20–50 label batch.'
			else:
				status = ACCEPTANCE_NOT_MET
				evidence = 'No processed-label count was available.'
				recommendation = 'Run manifest-driven batch verification.'
			
			return self.create_status(
				REQUIREMENT_SCALABILITY,
				'Prototype Scalability',
				status,
				evidence,
				recommendation,
				{
						'effective_count': effective_count,
						'minimum_files': min_files,
						'maximum_files': max_files
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
				'Prototype Scalability',
				ACCEPTANCE_NOT_MET,
				'Scalability could not be evaluated.',
				'Inspect the acceptance checker error log.'
			)
	
	def evaluate_security_and_data_handling( self ) -> List[ RequirementStatus ]:
		"""Evaluate security and no-long-term-storage requirements.

		Purpose:
			Check local OCR, external ML disablement, raw text logging disablement,
			no-persistence mode, redacted evidence export, upload persistence disablement,
			extracted-data export disablement, raw OCR export disablement, and file-path export
			disablement.

		Returns:
			List[RequirementStatus]: Security and data-handling statuses.
		"""
		try:
			retention = self._policy.to_acceptance_evidence( )
			merged = dict( retention )
			merged.update(
				{
						key: value
						for key, value in self._evidence.items( )
						if key in retention
				}
			)
			
			require_local_ocr = self.get_evidence_bool( 'REQUIRE_LOCAL_OCR', True )
			allow_external_ml = self.get_evidence_bool( 'ALLOW_EXTERNAL_ML_ENDPOINTS', False )
			raw_text_logging = bool( merged.get( 'ENABLE_RAW_TEXT_LOGGING', False ) )
			no_persistence_mode = bool( merged.get( 'NO_PERSISTENCE_MODE', True ) )
			long_term_storage_disabled = bool( merged.get( 'LONG_TERM_STORAGE_DISABLED', True ) )
			upload_persistence = bool( merged.get( 'ENABLE_UPLOAD_PERSISTENCE', False ) )
			raw_ocr_export = bool( merged.get( 'ENABLE_RAW_OCR_EXPORT', False ) )
			extracted_data_export = bool( merged.get( 'ENABLE_EXTRACTED_DATA_EXPORT', False ) )
			redacted_export = bool( merged.get( 'ENABLE_REDACTED_EVIDENCE_EXPORT', True ) )
			file_path_export = bool( merged.get( 'ENABLE_FILE_PATH_EXPORT', False ) )
			
			security_met = (
					require_local_ocr
					and not allow_external_ml
					and not raw_text_logging
					and no_persistence_mode
					and redacted_export
			)
			data_met = (
					no_persistence_mode
					and long_term_storage_disabled
					and not upload_persistence
					and not raw_text_logging
					and not raw_ocr_export
					and not extracted_data_export
					and not file_path_export
					and redacted_export
			)
			
			security_status = ACCEPTANCE_MET if security_met else ACCEPTANCE_NOT_MET
			data_status = ACCEPTANCE_MET if data_met else ACCEPTANCE_NOT_MET
			
			security_evidence = (
					f'Local OCR required: {require_local_ocr}; external ML endpoints allowed: '
					f'{allow_external_ml}; raw text logging enabled: {raw_text_logging}; '
					f'no-persistence mode: {no_persistence_mode}; redacted export enabled: {redacted_export}.'
			)
			data_evidence = (
					f'No-persistence mode: {no_persistence_mode}; long-term storage disabled: '
					f'{long_term_storage_disabled}; upload persistence enabled: {upload_persistence}; '
					f'raw OCR export enabled: {raw_ocr_export}; extracted data export enabled: '
					f'{extracted_data_export}; file path export enabled: {file_path_export}; '
					f'redacted export enabled: {redacted_export}.'
			)
			
			return [
					self.create_status(
						REQUIREMENT_SECURITY,
						'Security and Firewall-Safe Prototype Posture',
						security_status,
						security_evidence,
						'Keep local OCR required, external ML disabled, no-persistence active, and redacted export enabled.',
						{
								'require_local_ocr': require_local_ocr,
								'allow_external_ml_endpoints': allow_external_ml,
								'enable_raw_text_logging': raw_text_logging,
								'no_persistence_mode': no_persistence_mode,
								'enable_redacted_evidence_export': redacted_export
						}
					),
					self.create_status(
						REQUIREMENT_DATA_HANDLING,
						'No Long-Term Storage of Images or Extracted Data',
						data_status,
						data_evidence,
						'Keep upload persistence, raw OCR export, extracted-data export, and file-path export disabled.',
						{
								'no_persistence_mode': no_persistence_mode,
								'long_term_storage_disabled': long_term_storage_disabled,
								'enable_upload_persistence': upload_persistence,
								'enable_raw_text_logging': raw_text_logging,
								'enable_raw_ocr_export': raw_ocr_export,
								'enable_extracted_data_export': extracted_data_export,
								'enable_file_path_export': file_path_export,
								'enable_redacted_evidence_export': redacted_export
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
						ACCEPTANCE_NOT_MET,
						'Security posture could not be evaluated.',
						'Inspect configuration and data-retention policy.'
					),
					self.create_status(
						REQUIREMENT_DATA_HANDLING,
						'No Long-Term Storage of Images or Extracted Data',
						ACCEPTANCE_NOT_MET,
						'Data-handling posture could not be evaluated.',
						'Inspect configuration and data-retention policy.'
					)
			]
	
	def evaluate_accessibility_and_usability( self ) -> List[ RequirementStatus ]:
		"""Evaluate usability, interface simplicity, accessibility, and feedback.

		Purpose:
			Check Simple Mode, large controls, keyboard evidence, progress evidence, confidence
			evidence, and non-hover reviewer guidance.

		Returns:
			List[RequirementStatus]: Usability, interface, accessibility, and feedback statuses.
		"""
		try:
			default_simple_mode = self.get_evidence_bool( 'DEFAULT_SIMPLE_MODE', True )
			default_high_contrast = self.get_evidence_bool( 'DEFAULT_HIGH_CONTRAST_MODE', False )
			default_large_text = self.get_evidence_bool( 'DEFAULT_LARGE_TEXT_MODE', False )
			keyboard_passed = self.get_evidence_bool( 'KEYBOARD_ACCESSIBILITY_PASSED', False )
			workflow_validated = self.get_evidence_bool(
				'LOW_TECH_REVIEWER_WORKFLOW_VALIDATED',
				False
			)
			large_buttons_present = self.get_evidence_bool( 'LARGE_BUTTONS_PRESENT', True )
			minimal_navigation_validated = self.get_evidence_bool(
				'MINIMAL_NAVIGATION_VALIDATED',
				False
			)
			has_reviewer_action = 'Reviewer Action' in self._comparison_dataframe.columns
			has_confidence = (
					'Confidence' in self._comparison_dataframe.columns
					or 'Confidence' in self._detail_dataframe.columns
			)
			has_progress = (
					bool( getattr( self._result.performance_summary, 'total_files', 0 ) )
					or self.get_evidence_bool( 'PROGRESS_INDICATORS_DISPLAYED', False )
			)
			has_non_hover_guidance = (
					has_reviewer_action
					or self.get_evidence_bool( 'NON_HOVER_MISMATCH_GUIDANCE_DISPLAYED', False )
			)
			
			usability_status = ACCEPTANCE_MET if default_simple_mode else ACCEPTANCE_PARTIAL
			interface_status = ACCEPTANCE_MET if large_buttons_present and default_simple_mode else ACCEPTANCE_PARTIAL
			accessibility_status = ACCEPTANCE_MET if (
					(default_high_contrast or self.get_evidence_bool( 'HIGH_CONTRAST_AVAILABLE',
						True ))
					and (default_large_text or self.get_evidence_bool( 'LARGE_TEXT_AVAILABLE',
				True ))
					and keyboard_passed
			) else ACCEPTANCE_PARTIAL
			feedback_status = ACCEPTANCE_MET if (
					has_progress and has_confidence and has_non_hover_guidance
			) else ACCEPTANCE_PARTIAL
			
			return [
					self.create_status(
						REQUIREMENT_USABILITY,
						'Simple Low-Technical-Comfort Usability',
						usability_status,
						f'Default Simple Mode: {default_simple_mode}; workflow validated: {workflow_validated}.',
						'Keep Simple Mode as the default reviewer workflow.',
						{
								'default_simple_mode': default_simple_mode,
								'workflow_validated': workflow_validated
						}
					),
					self.create_status(
						REQUIREMENT_INTERFACE_SIMPLICITY,
						'Interface Simplicity',
						interface_status,
						f'Large buttons present: {large_buttons_present}; Simple Mode default: {default_simple_mode}.',
						'Keep technical diagnostics out of Simple Mode.',
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
						'Run and retain the browser keyboard accessibility checklist.',
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
								f'Progress evidence: {has_progress}; confidence evidence: {has_confidence}; '
								f'non-hover guidance: {has_non_hover_guidance}.'
						),
						'Keep visible explanation and reviewer-action columns in results.',
						{
								'has_progress_evidence': has_progress,
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
						ACCEPTANCE_NOT_MET,
						'Accessibility posture could not be evaluated.',
						'Inspect accessibility outputs and configuration.'
					)
			]
	
	def evaluate_infrastructure_and_integration( self ) -> List[ RequirementStatus ]:
		"""Evaluate Azure infrastructure and COLA non-integration.

		Purpose:
			Check deployment target, Azure artifacts, smoke-test evidence, local OCR posture,
			external ML disablement, and COLA integration disablement.

		Returns:
			List[RequirementStatus]: Infrastructure and COLA statuses.
		"""
		try:
			deployment_target = self.get_evidence_text( 'DEPLOYMENT_TARGET', 'local' )
			require_local_ocr = self.get_evidence_bool( 'REQUIRE_LOCAL_OCR', True )
			allow_external_ml = self.get_evidence_bool( 'ALLOW_EXTERNAL_ML_ENDPOINTS', False )
			azure_ready = self.get_evidence_bool( 'AZURE_READY_ARTIFACTS_PRESENT', False )
			azure_smoke = self.get_evidence_bool( 'AZURE_SMOKE_TEST_PASSED', False )
			cola_enabled = self.get_evidence_bool( 'COLA_INTEGRATION_ENABLED', False )
			
			if (
					deployment_target.lower( ) == 'azure'
					and azure_ready
					and require_local_ocr
					and not allow_external_ml):
				infrastructure_status = ACCEPTANCE_MET
			elif azure_smoke and require_local_ocr and not allow_external_ml:
				infrastructure_status = ACCEPTANCE_MET
			elif azure_ready and require_local_ocr and not allow_external_ml:
				infrastructure_status = ACCEPTANCE_PARTIAL
			else:
				infrastructure_status = ACCEPTANCE_NOT_MET
			
			cola_status = ACCEPTANCE_MET if not cola_enabled else ACCEPTANCE_NOT_MET
			
			return [
					self.create_status(
						REQUIREMENT_INFRASTRUCTURE,
						'Azure Infrastructure and Local OCR Deployment Posture',
						infrastructure_status,
						(
								f'Deployment target: {deployment_target}; Azure artifacts present: {azure_ready}; '
								f'Azure smoke test passed: {azure_smoke}; local OCR required: {require_local_ocr}; '
								f'external ML endpoints allowed: {allow_external_ml}.'
						),
						'Add Azure runtime artifacts and keep external ML endpoints disabled.',
						{
								'deployment_target': deployment_target,
								'azure_ready_artifacts_present': azure_ready,
								'azure_smoke_test_passed': azure_smoke,
								'require_local_ocr': require_local_ocr,
								'allow_external_ml_endpoints': allow_external_ml
						}
					),
					self.create_status(
						REQUIREMENT_COLA,
						'No Direct COLA Integration',
						cola_status,
						f'Direct COLA integration enabled: {cola_enabled}.',
						'Keep COLA integration disabled for prototype scope.',
						{
								'cola_integration_enabled': cola_enabled
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
						'Azure Infrastructure and Local OCR Deployment Posture',
						ACCEPTANCE_NOT_MET,
						'Infrastructure posture could not be evaluated.',
						'Inspect deployment evidence.'
					),
					self.create_status(
						REQUIREMENT_COLA,
						'No Direct COLA Integration',
						ACCEPTANCE_NOT_MET,
						'COLA integration posture could not be evaluated.',
						'Inspect configuration.'
					)
			]
	
	def evaluate_batch_result( self, result: BatchProcessingResult,
			summary_dataframe: Optional[ pd.DataFrame ] = None,
			detail_dataframe: Optional[ pd.DataFrame ] = None,
			comparison_dataframe: Optional[ pd.DataFrame ] = None,
			performance_dataframe: Optional[ pd.DataFrame ] = None,
			accessibility_dataframe: Optional[ pd.DataFrame ] = None,
			deployment_dataframe: Optional[ pd.DataFrame ] = None,
			evidence: Optional[ Dict[ str, object ] ] = None ) -> AcceptanceSummary:
		"""Evaluate a batch processing result against all stakeholder requirements.

		Purpose:
			Store the supplied runtime artifacts, merge data-retention evidence, evaluate every
			stakeholder requirement, and return an acceptance summary.

		Args:
			result (BatchProcessingResult): Batch processing result.
			summary_dataframe (Optional[pd.DataFrame]): Summary DataFrame.
			detail_dataframe (Optional[pd.DataFrame]): Detail DataFrame.
			comparison_dataframe (Optional[pd.DataFrame]): Comparison DataFrame.
			performance_dataframe (Optional[pd.DataFrame]): Performance DataFrame.
			accessibility_dataframe (Optional[pd.DataFrame]): Accessibility DataFrame.
			deployment_dataframe (Optional[pd.DataFrame]): Deployment DataFrame.
			evidence (Optional[Dict[str, object]]): Supplemental evidence.

		Returns:
			AcceptanceSummary: Requirement-level acceptance summary.
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
			
			retention_evidence = self._policy.to_acceptance_evidence( )
			
			for key, value in retention_evidence.items( ):
				self._evidence.setdefault( key, value )
			
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
			
			requirement_map = {
					requirement.requirement_id: requirement
					for requirement in self._requirements
			}
			ordered_requirements = [
					requirement_map[ requirement_id ]
					for requirement_id in REQUIREMENT_ORDER
					if requirement_id in requirement_map
			]
			
			return AcceptanceSummary(
				requirements=ordered_requirements
			)
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
							ACCEPTANCE_NOT_MET,
							'Acceptance evaluation failed.',
							'Inspect the acceptance checker error log.'
						)
				]
			)
	
	def evaluate_manual_or_batch_result( self, result: BatchProcessingResult,
			summary_dataframe: Optional[ pd.DataFrame ] = None,
			detail_dataframe: Optional[ pd.DataFrame ] = None,
			comparison_dataframe: Optional[ pd.DataFrame ] = None,
			performance_dataframe: Optional[ pd.DataFrame ] = None,
			accessibility_dataframe: Optional[ pd.DataFrame ] = None,
			deployment_dataframe: Optional[ pd.DataFrame ] = None,
			evidence: Optional[ Dict[ str, object ] ] = None ) -> AcceptanceSummary:
		"""Evaluate either manual or batch result artifacts.

		Purpose:
			Provide a compatibility wrapper around ``evaluate_batch_result`` for app code that
			uses one evaluator for both manual single-label and manifest batch workflows.

		Args:
			result (BatchProcessingResult): Batch-style processing result.
			summary_dataframe (Optional[pd.DataFrame]): Summary DataFrame.
			detail_dataframe (Optional[pd.DataFrame]): Detail DataFrame.
			comparison_dataframe (Optional[pd.DataFrame]): Comparison DataFrame.
			performance_dataframe (Optional[pd.DataFrame]): Performance DataFrame.
			accessibility_dataframe (Optional[pd.DataFrame]): Accessibility DataFrame.
			deployment_dataframe (Optional[pd.DataFrame]): Deployment DataFrame.
			evidence (Optional[Dict[str, object]]): Supplemental evidence.

		Returns:
			AcceptanceSummary: Requirement-level acceptance summary.
		"""
		try:
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
							ACCEPTANCE_NOT_MET,
							'Manual or batch acceptance evaluation failed.',
							'Inspect the acceptance checker error log.'
						)
				]
			)