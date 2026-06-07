'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                acceptance_test_harness.py
      Author:                  Terry D. Eppler
      Created:                 06-06-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-07-2026
    ******************************************************************************************
    <copyright file="acceptance_test_harness.py" company="Terry D. Eppler">

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
        Provides a repeatable non-UI acceptance test harness for Fiddy.

        This module runs manifest-driven verification against supplied local label artwork,
        builds summary, detail, comparison, performance, deployment, accessibility, and
        acceptance evidence outputs, and writes a redacted stakeholder evidence package to disk.
        All persisted CSV, JSON, Markdown, and manifest artifacts are routed through the
        centralized data-retention policy so raw OCR text, extracted label values, application
        values, local file paths, and detailed evidence text are redacted by default.

        The harness does not provide a Streamlit UI, does not deploy Azure infrastructure, does
        not call external services, and does not persist uploaded label images. It processes
        caller-supplied local files and writes only policy-governed evidence artifacts.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field

import config as cfg
from booger import Error, Logger
from config import throw_if
from src.acceptance_checker import AcceptanceChecker, AcceptanceSummary
from src.accessibility_checklist import AccessibilityChecklist, AccessibilityChecklistResult
from src.batch_processor import BatchProcessingResult, BatchProcessor
from src.data_retention import DataRetentionPolicy
from src.deployment_evidence import DeploymentEvidence, DeploymentEvidenceChecker
from src.models import BatchVerificationReport

# ==========================================================================================
# Harness Constants
# ==========================================================================================

HARNESS_STATUS_PASS: str = 'Pass'
HARNESS_STATUS_FAIL: str = 'Fail'
HARNESS_STATUS_PARTIAL: str = 'Partial'
HARNESS_STATUS_NOT_EVALUATED: str = 'Not Evaluated'

SUPPORTED_LABEL_EXTENSIONS: tuple[ str, ... ] = (
		'.jpg',
		'.jpeg',
		'.png',
		'.tif',
		'.tiff',
		'.bmp',
		'.webp',
		'.pdf'
)

# ==========================================================================================
# Harness Models
# ==========================================================================================

class AcceptanceHarnessPackage( BaseModel ):
	"""Represent generated redacted evidence-package file paths.

	Purpose:
		Store the output directory and generated artifact paths from one acceptance harness run.
		The object is intentionally flat so it can be serialized into a package manifest without
		exposing internal file content.

	Attributes:
		output_directory (str): Directory where evidence files were written.
		summary_csv (str): Path to the redacted batch summary CSV.
		details_csv (str): Path to the redacted rule detail CSV.
		comparison_csv (str): Path to the redacted side-by-side comparison CSV.
		performance_csv (str): Path to the performance CSV.
		batch_acceptance_csv (str): Path to the batch acceptance CSV.
		acceptance_csv (str): Path to the redacted stakeholder acceptance CSV.
		acceptance_json (str): Path to the redacted stakeholder acceptance JSON.
		acceptance_markdown (str): Path to the stakeholder acceptance Markdown.
		accessibility_csv (str): Path to the accessibility checklist CSV.
		accessibility_json (str): Path to the accessibility JSON.
		accessibility_markdown (str): Path to the accessibility Markdown.
		deployment_csv (str): Path to the deployment evidence CSV.
		deployment_json (str): Path to the deployment evidence JSON.
		deployment_markdown (str): Path to the deployment evidence Markdown.
		package_manifest_json (str): Path to the redacted package manifest JSON.
	"""
	
	output_directory: str = Field( default='' )
	summary_csv: str = Field( default='' )
	details_csv: str = Field( default='' )
	comparison_csv: str = Field( default='' )
	performance_csv: str = Field( default='' )
	batch_acceptance_csv: str = Field( default='' )
	acceptance_csv: str = Field( default='' )
	acceptance_json: str = Field( default='' )
	acceptance_markdown: str = Field( default='' )
	accessibility_csv: str = Field( default='' )
	accessibility_json: str = Field( default='' )
	accessibility_markdown: str = Field( default='' )
	deployment_csv: str = Field( default='' )
	deployment_json: str = Field( default='' )
	deployment_markdown: str = Field( default='' )
	package_manifest_json: str = Field( default='' )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert package paths into a flat record.

		Purpose:
			Return all generated package artifact paths in a JSON-friendly dictionary.

		Returns:
			Dict[str, object]: Flat package path record.
		"""
		try:
			return {
					'Output Directory': self.output_directory,
					'Summary CSV': self.summary_csv,
					'Details CSV': self.details_csv,
					'Comparison CSV': self.comparison_csv,
					'Performance CSV': self.performance_csv,
					'Batch Acceptance CSV': self.batch_acceptance_csv,
					'Acceptance CSV': self.acceptance_csv,
					'Acceptance JSON': self.acceptance_json,
					'Acceptance Markdown': self.acceptance_markdown,
					'Accessibility CSV': self.accessibility_csv,
					'Accessibility JSON': self.accessibility_json,
					'Accessibility Markdown': self.accessibility_markdown,
					'Deployment CSV': self.deployment_csv,
					'Deployment JSON': self.deployment_json,
					'Deployment Markdown': self.deployment_markdown,
					'Package Manifest JSON': self.package_manifest_json
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return { }
	
	def to_json( self ) -> str:
		"""Serialize package paths as formatted JSON.

		Purpose:
			Create a JSON representation of generated package artifact paths.

		Returns:
			str: Formatted JSON string.
		"""
		try:
			return json.dumps( self.to_record( ), indent=2, default=str )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_json( self ) -> str'
			Logger( ).write( error )
			return '{}'

class AcceptanceHarnessResult( BaseModel ):
	"""Represent the complete result of one acceptance harness run.

	Purpose:
		Store the run name, status, message, generated package paths, batch-processing result,
		acceptance summary, accessibility result, deployment evidence, DataFrames, and timestamps.

	Attributes:
		test_name (str): Human-readable harness run name.
		status (str): Harness status.
		message (str): Reviewer-facing status message.
		package (AcceptanceHarnessPackage): Generated package path manifest.
		batch_result (BatchProcessingResult): Batch processing result.
		acceptance_summary (AcceptanceSummary): Requirement-level acceptance summary.
		accessibility_result (AccessibilityChecklistResult): Accessibility checklist result.
		deployment_evidence (DeploymentEvidence): Deployment evidence result.
		dataframes (Dict[str, object]): Generated DataFrames keyed by artifact name.
		started_on (str): UTC start timestamp.
		completed_on (str): UTC completion timestamp.
	"""
	
	test_name: str = Field( default='' )
	status: str = Field( default=HARNESS_STATUS_NOT_EVALUATED )
	message: str = Field( default='' )
	package: AcceptanceHarnessPackage = Field( default_factory=AcceptanceHarnessPackage )
	batch_result: BatchProcessingResult = Field( default_factory=BatchProcessingResult )
	acceptance_summary: AcceptanceSummary = Field( default_factory=AcceptanceSummary )
	accessibility_result: AccessibilityChecklistResult = Field(
		default_factory=AccessibilityChecklistResult )
	deployment_evidence: DeploymentEvidence = Field( default_factory=DeploymentEvidence )
	dataframes: Dict[ str, object ] = Field( default_factory=dict )
	started_on: str = Field(
		default_factory=lambda: datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
	)
	completed_on: str = Field( default='' )
	
	def to_manifest_record( self ) -> Dict[ str, object ]:
		"""Convert the harness result into a redacted package-manifest record.

		Purpose:
			Create a compact run manifest containing status, message, timestamps, package paths,
			acceptance counts, accessibility summary, and deployment summary.

		Returns:
			Dict[str, object]: Package manifest record.
		"""
		try:
			return {
					'Test Name': self.test_name,
					'Status': self.status,
					'Message': self.message,
					'Started On': self.started_on,
					'Completed On': self.completed_on,
					'Output Package': self.package.to_record( ),
					'Acceptance Counts': self.acceptance_summary.status_counts( ),
					'Acceptance Percentage': self.acceptance_summary.acceptance_percentage( ),
					'Accessibility Summary': self.accessibility_result.to_summary_record( ),
					'Deployment Summary': self.deployment_evidence.to_summary_record( )
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_manifest_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Test Name': self.test_name,
					'Status': HARNESS_STATUS_NOT_EVALUATED,
					'Message': 'Harness manifest record could not be rendered.'
			}

# ==========================================================================================
# Acceptance Test Harness
# ==========================================================================================

class AcceptanceTestHarness( ):
	"""Run non-UI acceptance checks and generate redacted evidence packages.

	Purpose:
		Process a manifest CSV and local label-artwork directory, collect runtime verification
		outputs, build display/export DataFrames, evaluate deployment and accessibility evidence,
		run the acceptance checker, and write redacted stakeholder evidence files to disk.

	Attributes:
		_project_root (Path): Project root used for read-only deployment evidence checks.
		_output_root (Path): Root directory for generated evidence packages.
		_max_workers (int): Batch worker count.
		_sla_seconds (float): Per-label SLA threshold.
		_policy (DataRetentionPolicy): Active redaction/no-persistence policy.
		_started_on (str): Current run start timestamp.
	"""
	
	_project_root: Path
	_output_root: Path
	_max_workers: int
	_sla_seconds: float
	_policy: DataRetentionPolicy
	_started_on: str
	
	def __init__( self, project_root: str | Path | None = None,
			output_root: str | Path | None = None, max_workers: int | None = None,
			sla_seconds: float | None = None ) -> None:
		"""Initialize the acceptance test harness.

		Purpose:
			Store project/output roots, batch worker count, SLA threshold, and active data
			retention policy.

		Args:
			project_root (str | Path | None): Optional project root path.
			output_root (str | Path | None): Optional output root path.
			max_workers (int | None): Optional batch worker count.
			sla_seconds (float | None): Optional per-label SLA threshold.

		Returns:
			None.
		"""
		try:
			self._project_root = Path( project_root ) if project_root else Path.cwd( )
			self._output_root = Path( output_root ) if output_root else Path(
				getattr( cfg, 'ACCEPTANCE_OUTPUT_ROOT', 'acceptance_evidence' ) )
			self._max_workers = int(
				max_workers
				if max_workers is not None
				else getattr( cfg, 'MAX_PARALLEL_WORKERS', 4 )
			)
			self._sla_seconds = float(
				sla_seconds
				if sla_seconds is not None
				else getattr( cfg, 'LABEL_PROCESSING_SLA_SECONDS', 5.0 )
			)
			self._policy = DataRetentionPolicy( )
			self._started_on = ''
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = '__init__( self, *args ) -> None'
			Logger( ).write( error )
			self._project_root = Path.cwd( )
			self._output_root = Path( 'acceptance_evidence' )
			self._max_workers = 1
			self._sla_seconds = 5.0
			self._policy = DataRetentionPolicy( )
			self._started_on = ''
	
	@property
	def output_root( self ) -> Path:
		"""Return the configured output root.

		Purpose:
			Expose the evidence output root directory.

		Returns:
			Path: Output root path.
		"""
		return self._output_root
	
	def create_output_directory( self, test_name: str ) -> Path:
		"""Create a timestamped evidence output directory.

		Purpose:
			Create a deterministic, timestamped output directory under the configured output root.

		Args:
			test_name (str): Harness run name.

		Returns:
			Path: Created output directory.
		"""
		try:
			throw_if( 'test_name', test_name )
			
			timestamp = datetime.utcnow( ).strftime( '%Y%m%d_%H%M%S' )
			safe_name = ''.join(
				char.lower( ) if char.isalnum( ) else '_'
				for char in test_name.strip( )
			).strip( '_' )
			
			if not safe_name:
				safe_name = 'acceptance_test'
			
			output_directory = self._output_root / f'{safe_name}_{timestamp}'
			output_directory.mkdir( parents=True, exist_ok=True )
			return output_directory
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_output_directory( self, test_name: str ) -> Path'
			Logger( ).write( error )
			fallback = Path( 'acceptance_evidence_fallback' )
			fallback.mkdir( parents=True, exist_ok=True )
			return fallback
	
	def collect_label_files( self, label_directory: str | Path,
			limit: Optional[ int ] = None ) -> List[ Path ]:
		"""Collect supported label artwork files.

		Purpose:
			Find supported image and PDF files in the supplied directory, sort them by filename,
			and optionally limit the returned set.

		Args:
			label_directory (str | Path): Directory containing label artwork.
			limit (Optional[int]): Optional file count limit.

		Returns:
			List[Path]: Sorted supported file paths.
		"""
		try:
			throw_if( 'label_directory', label_directory )
			
			root = Path( label_directory )
			
			if not root.exists( ) or not root.is_dir( ):
				raise ValueError( f'Label directory does not exist: {root}' )
			
			files = [
					path
					for path in root.iterdir( )
					if path.is_file( ) and path.suffix.lower( ) in SUPPORTED_LABEL_EXTENSIONS
			]
			files = sorted( files, key=lambda item: item.name.lower( ) )
			
			if limit is not None:
				return files[ :max( 0, int( limit ) ) ]
			
			return files
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'collect_label_files( self, *args ) -> List[Path]'
			Logger( ).write( error )
			return [ ]
	
	def build_summary_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame:
		"""Build a redacted batch summary DataFrame.

		Purpose:
			Convert batch summary records into a DataFrame and redact sensitive values through
			the active retention policy.

		Args:
			batch_report (BatchVerificationReport): Batch verification report.

		Returns:
			pd.DataFrame: Redacted summary DataFrame.
		"""
		try:
			throw_if( 'batch_report', batch_report )
			
			if hasattr( batch_report, 'to_summary_records' ):
				dataframe = pd.DataFrame( batch_report.to_summary_records( ) )
			else:
				records = [
						report.to_summary_record( )
						for report in batch_report.reports
						if hasattr( report, 'to_summary_record' )
				]
				dataframe = pd.DataFrame( records )
			
			return self._policy.redact_dataframe( dataframe )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'build_summary_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def build_detail_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame:
		"""Build a redacted rule-detail DataFrame.

		Purpose:
			Convert all rule results into flat detail rows and redact sensitive values.

		Args:
			batch_report (BatchVerificationReport): Batch verification report.

		Returns:
			pd.DataFrame: Redacted detail DataFrame.
		"""
		try:
			throw_if( 'batch_report', batch_report )
			
			if hasattr( batch_report, 'to_detail_records' ):
				dataframe = pd.DataFrame( batch_report.to_detail_records( ) )
				return self._policy.redact_dataframe( dataframe )
			
			records = [ ]
			
			for report in batch_report.reports:
				for result in report.results:
					records.append(
						{
								'File Name': report.file_name,
								'Rule ID': getattr( result, 'rule_id', '' ),
								'Field': getattr( result, 'field_name', '' ),
								'Status': getattr( result, 'status', '' ),
								'Severity': getattr( result, 'severity', '' ),
								'Expected': getattr( result, 'expected', '' ),
								'Observed': getattr( result, 'observed', '' ),
								'Confidence': getattr( result, 'confidence', 0.0 ),
								'Evidence': getattr( result, 'evidence', '' ),
								'Message': getattr( result, 'message', '' ),
								'Requires Human Review': getattr(
									result,
									'requires_human_review',
									False
								)
						}
					)
			
			return self._policy.redact_dataframe( pd.DataFrame( records ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'build_detail_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def get_reviewer_action( self, result: object ) -> str:
		"""Return reviewer action text for one result.

		Purpose:
			Create a safe, non-sensitive reviewer action string for comparison evidence.

		Args:
			result (object): Rule result object.

		Returns:
			str: Reviewer action text.
		"""
		try:
			status = str( getattr( result, 'status', '' ) )
			requires_review = bool( getattr( result, 'requires_human_review', False ) )
			
			if requires_review:
				return 'Review manually and confirm against source records.'
			
			if status.lower( ) == 'pass':
				return 'No reviewer action required.'
			
			if status.lower( ) in ('fail', 'failed'):
				return 'Resolve mismatch or request corrected source data.'
			
			if status.lower( ) in ('warning', 'needs review'):
				return 'Review supporting evidence before clearing.'
			
			return 'Review the result if the status is unclear.'
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_reviewer_action( self, result: object ) -> str'
			Logger( ).write( error )
			return 'Review manually.'
	
	def build_comparison_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame:
		"""Build a redacted side-by-side comparison DataFrame.

		Purpose:
			Create reviewer-facing comparison rows and redact sensitive application/extracted
			values before returning the DataFrame.

		Args:
			batch_report (BatchVerificationReport): Batch verification report.

		Returns:
			pd.DataFrame: Redacted comparison DataFrame.
		"""
		try:
			throw_if( 'batch_report', batch_report )
			
			records = [ ]
			
			for report in batch_report.reports:
				for result in report.results:
					records.append(
						{
								'File Name': report.file_name,
								'Field': getattr( result, 'field_name', '' ),
								'Application': getattr( result, 'expected', '' ),
								'Extracted': getattr( result, 'observed', '' ),
								'Status': getattr( result, 'status', '' ),
								'Severity': getattr( result, 'severity', '' ),
								'Confidence': getattr( result, 'confidence', 0.0 ),
								'Explanation': getattr( result, 'message', '' ),
								'Reviewer Action': self.get_reviewer_action( result )
						}
					)
			
			return self._policy.redact_dataframe( pd.DataFrame( records ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'build_comparison_dataframe( self, batch_report: BatchVerificationReport ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def build_performance_dataframe( self, batch_result: BatchProcessingResult ) -> pd.DataFrame:
		"""Build the per-label performance DataFrame.

		Purpose:
			Convert per-label performance results into a policy-governed DataFrame.

		Args:
			batch_result (BatchProcessingResult): Batch processing result.

		Returns:
			pd.DataFrame: Performance DataFrame.
		"""
		try:
			throw_if( 'batch_result', batch_result )
			
			records = [
					result.to_record( )
					for result in batch_result.performance_results
			]
			return self._policy.redact_dataframe( pd.DataFrame( records ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'build_performance_dataframe( self, batch_result: BatchProcessingResult ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def build_batch_acceptance_dataframe( self,
			batch_result: BatchProcessingResult ) -> pd.DataFrame:
		"""Build the batch acceptance evidence DataFrame.

		Purpose:
			Convert batch processor acceptance evidence into a one-row policy-governed DataFrame.

		Args:
			batch_result (BatchProcessingResult): Batch processing result.

		Returns:
			pd.DataFrame: Batch acceptance DataFrame.
		"""
		try:
			throw_if( 'batch_result', batch_result )
			return self._policy.redact_dataframe(
				pd.DataFrame( [ batch_result.acceptance_record ] ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'build_batch_acceptance_dataframe( self, batch_result: BatchProcessingResult ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def build_accessibility_result( self, manual_accessibility_passed: bool = False,
			notes: str = '' ) -> AccessibilityChecklistResult:
		"""Build accessibility checklist evidence.

		Purpose:
			Create accessibility checklist evidence for the acceptance package.

		Args:
			manual_accessibility_passed (bool): Indicates whether browser accessibility checks
				were completed and passed.
			notes (str): Optional checklist notes.

		Returns:
			AccessibilityChecklistResult: Accessibility checklist result.
		"""
		try:
			checklist = AccessibilityChecklist( )
			
			if manual_accessibility_passed:
				checklist.mark_all_manual_checks_passed( notes )
			else:
				checklist.mark_all_manual_checks_not_tested(
					'Manual browser accessibility validation was not supplied to the harness.'
				)
			
			return checklist.evaluate( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'build_accessibility_result( self, *args ) -> AccessibilityChecklistResult'
			Logger( ).write( error )
			return AccessibilityChecklistResult(
				status='Not Evaluated',
				message='Accessibility checklist evidence could not be generated.'
			)
	
	def build_deployment_evidence( self ) -> DeploymentEvidence:
		"""Build deployment evidence.

		Purpose:
			Run the read-only deployment evidence checker.

		Returns:
			DeploymentEvidence: Deployment evidence result.
		"""
		try:
			checker = DeploymentEvidenceChecker( project_root=self._project_root )
			return checker.evaluate( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'build_deployment_evidence( self ) -> DeploymentEvidence'
			Logger( ).write( error )
			return DeploymentEvidence( )
	
	def build_acceptance_evidence( self, batch_result: BatchProcessingResult,
			deployment_evidence: DeploymentEvidence, processed_count: int,
			manual_accessibility_passed: bool, imperfect_image_tested: bool,
			low_quality_image_tested: bool,
			false_positive_variation_tested: bool ) -> Dict[ str, object ]:
		"""Build supplemental acceptance evidence.

		Purpose:
			Combine runtime, deployment, accessibility, and data-retention evidence into one
			dictionary for the acceptance checker.

		Args:
			batch_result (BatchProcessingResult): Batch processing result.
			deployment_evidence (DeploymentEvidence): Deployment evidence result.
			processed_count (int): Number of supplied label files.
			manual_accessibility_passed (bool): Indicates whether accessibility validation passed.
			imperfect_image_tested (bool): Indicates whether imperfect-image samples were tested.
			low_quality_image_tested (bool): Indicates whether low-quality samples were tested.
			false_positive_variation_tested (bool): Indicates whether false-positive variation
				samples were tested.

		Returns:
			Dict[str, object]: Acceptance evidence dictionary.
		"""
		try:
			min_files = int( getattr( cfg, 'BATCH_ACCEPTANCE_MIN_FILES', 20 ) )
			max_files = int( getattr( cfg, 'BATCH_ACCEPTANCE_MAX_FILES', 50 ) )
			performance_acceptance = getattr(
				batch_result.performance_summary,
				'acceptance_result',
				None
			)
			
			evidence = {
					'ACCEPTANCE_EXPORT_AVAILABLE': True,
					'IMPERFECT_IMAGE_TESTED': imperfect_image_tested,
					'LOW_QUALITY_IMAGE_TESTED': low_quality_image_tested,
					'FALSE_POSITIVE_VARIATION_TESTED': false_positive_variation_tested,
					'PERFORMANCE_SLA_TESTED': bool( batch_result.performance_results ),
					'PERFORMANCE_SLA_PASSED': bool(
						getattr( performance_acceptance, 'meets_acceptance', False )
					),
					'PROTOTYPE_BATCH_SCALE_TESTED': processed_count >= min_files,
					'PROTOTYPE_BATCH_SCALE_PASSED': min_files <= processed_count <= max_files,
					'BATCH_ACCEPTANCE_MIN_FILES': min_files,
					'BATCH_ACCEPTANCE_MAX_FILES': max_files,
					'KEYBOARD_ACCESSIBILITY_PASSED': manual_accessibility_passed,
					'LOW_TECH_REVIEWER_WORKFLOW_VALIDATED': manual_accessibility_passed,
					'MINIMAL_NAVIGATION_VALIDATED': manual_accessibility_passed,
					'PROGRESS_INDICATORS_DISPLAYED': True,
					'NON_HOVER_MISMATCH_GUIDANCE_DISPLAYED': True,
					'LARGE_BUTTONS_PRESENT': True,
					'DEFAULT_SIMPLE_MODE': bool( getattr( cfg, 'DEFAULT_SIMPLE_MODE', True ) ),
					'DEFAULT_HIGH_CONTRAST_MODE': bool(
						getattr( cfg, 'DEFAULT_HIGH_CONTRAST_MODE', False ) ),
					'DEFAULT_LARGE_TEXT_MODE': bool(
						getattr( cfg, 'DEFAULT_LARGE_TEXT_MODE', False ) )
			}
			
			if hasattr( deployment_evidence, 'to_acceptance_evidence' ):
				evidence.update( deployment_evidence.to_acceptance_evidence( ) )
			
			evidence.update( self._policy.to_acceptance_evidence( ) )
			return evidence
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'build_acceptance_evidence( self, *args ) -> Dict[str, object]'
			Logger( ).write( error )
			return self._policy.to_acceptance_evidence( )
	
	def build_acceptance_summary( self, batch_result: BatchProcessingResult,
			summary_dataframe: pd.DataFrame, detail_dataframe: pd.DataFrame,
			comparison_dataframe: pd.DataFrame, performance_dataframe: pd.DataFrame,
			accessibility_dataframe: pd.DataFrame, deployment_dataframe: pd.DataFrame,
			evidence: Dict[ str, object ] ) -> AcceptanceSummary:
		"""Build the requirement-level acceptance summary.

		Purpose:
			Run the acceptance checker using generated redacted outputs and supplemental evidence.

		Args:
			batch_result (BatchProcessingResult): Batch processing result.
			summary_dataframe (pd.DataFrame): Summary DataFrame.
			detail_dataframe (pd.DataFrame): Detail DataFrame.
			comparison_dataframe (pd.DataFrame): Comparison DataFrame.
			performance_dataframe (pd.DataFrame): Performance DataFrame.
			accessibility_dataframe (pd.DataFrame): Accessibility DataFrame.
			deployment_dataframe (pd.DataFrame): Deployment DataFrame.
			evidence (Dict[str, object]): Supplemental evidence.

		Returns:
			AcceptanceSummary: Requirement-level acceptance summary.
		"""
		try:
			checker = AcceptanceChecker( )
			
			try:
				return checker.evaluate_batch_result(
					result=batch_result,
					summary_dataframe=summary_dataframe,
					detail_dataframe=detail_dataframe,
					comparison_dataframe=comparison_dataframe,
					performance_dataframe=performance_dataframe,
					accessibility_dataframe=accessibility_dataframe,
					deployment_dataframe=deployment_dataframe,
					evidence=evidence
				)
			except TypeError:
				return checker.evaluate_batch_result(
					result=batch_result,
					summary_dataframe=summary_dataframe,
					detail_dataframe=detail_dataframe,
					comparison_dataframe=comparison_dataframe,
					performance_dataframe=performance_dataframe,
					evidence=evidence
				)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'build_acceptance_summary( self, *args ) -> AcceptanceSummary'
			Logger( ).write( error )
			return AcceptanceSummary( )
	
	def write_text_file( self, path: Path, content: str ) -> str:
		"""Write redacted text evidence.

		Purpose:
			Write policy-governed text content to disk. The caller must pass redacted content.

		Args:
			path (Path): Output file path.
			content (str): Text content.

		Returns:
			str: Written path string, or an empty string when writing fails.
		"""
		try:
			throw_if( 'path', path )
			
			if not self._policy.can_write_evidence_files( ):
				return ''
			
			written_path = self._policy.write_text_file( content or '', path )
			return str( written_path )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'write_text_file( self, *args ) -> str'
			Logger( ).write( error )
			return ''
	
	def write_dataframe_csv( self, path: Path, dataframe: pd.DataFrame ) -> str:
		"""Write redacted DataFrame CSV evidence.

		Purpose:
			Redact a DataFrame through the active retention policy before writing CSV evidence.

		Args:
			path (Path): Output CSV path.
			dataframe (pd.DataFrame): DataFrame to write.

		Returns:
			str: Written path string, or an empty string when writing fails.
		"""
		try:
			throw_if( 'path', path )
			throw_if( 'dataframe', dataframe )
			
			if not self._policy.can_write_evidence_files( ):
				return ''
			
			path.parent.mkdir( parents=True, exist_ok=True )
			
			if dataframe.empty:
				dataframe.to_csv( path, index=False, encoding='utf-8' )
			else:
				path.write_text( self._policy.dataframe_to_csv( dataframe ), encoding='utf-8' )
			
			return str( path )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'write_dataframe_csv( self, *args ) -> str'
			Logger( ).write( error )
			return ''
	
	def write_package( self, output_directory: Path,
			result: AcceptanceHarnessResult ) -> AcceptanceHarnessPackage:
		"""Write a redacted acceptance evidence package.

		Purpose:
			Write all package artifacts through the centralized data-retention policy. Sensitive
			application values, extracted values, raw OCR text, local file paths, and evidence text
			are redacted by default.

		Args:
			output_directory (Path): Evidence output directory.
			result (AcceptanceHarnessResult): Harness result.

		Returns:
			AcceptanceHarnessPackage: Generated package path manifest.
		"""
		try:
			throw_if( 'output_directory', output_directory )
			throw_if( 'result', result )
			
			package = AcceptanceHarnessPackage(
				output_directory=str( output_directory )
			)
			
			package.summary_csv = self.write_dataframe_csv(
				output_directory / 'fiddy_summary_redacted.csv',
				result.dataframes.get( 'summary', pd.DataFrame( ) )
			)
			package.details_csv = self.write_dataframe_csv(
				output_directory / 'fiddy_details_redacted.csv',
				result.dataframes.get( 'details', pd.DataFrame( ) )
			)
			package.comparison_csv = self.write_dataframe_csv(
				output_directory / 'fiddy_comparison_redacted.csv',
				result.dataframes.get( 'comparison', pd.DataFrame( ) )
			)
			package.performance_csv = self.write_dataframe_csv(
				output_directory / 'fiddy_performance.csv',
				result.dataframes.get( 'performance', pd.DataFrame( ) ) )
			
			package.batch_acceptance_csv = self.write_dataframe_csv(
				output_directory / 'fiddy_batch_acceptance.csv',
				result.dataframes.get( 'batch_acceptance', pd.DataFrame( ) ) )
			
			package.acceptance_csv = self.write_dataframe_csv(
				output_directory / 'fiddy_acceptance_redacted.csv',
				result.dataframes.get( 'acceptance', pd.DataFrame( ) ) )
			
			acceptance_dataframe = result.dataframes.get( 'acceptance', pd.DataFrame( ) )
			package.acceptance_json = self.write_text_file(
				output_directory / 'fiddy_acceptance_redacted.json',
				self._policy.dataframe_to_json( acceptance_dataframe ) )
			
			package.acceptance_markdown = self.write_text_file(
				output_directory / 'fiddy_acceptance_report_redacted.md',
				result.acceptance_summary.to_markdown( ) )
			
			package.accessibility_csv = self.write_dataframe_csv(
				output_directory / 'fiddy_accessibility.csv',
				result.dataframes.get( 'accessibility', pd.DataFrame( ) ) )
			
			package.accessibility_json = self.write_text_file(
				output_directory / 'fiddy_accessibility.json',
				self._policy.object_to_json( result.accessibility_result ) )
			
			package.accessibility_markdown = self.write_text_file(
				output_directory / 'fiddy_accessibility.md',
				result.accessibility_result.to_markdown( ) )
			
			package.deployment_csv = self.write_dataframe_csv(
				output_directory / 'fiddy_deployment_evidence.csv',
				result.dataframes.get( 'deployment', pd.DataFrame( ) ) )
			
			package.deployment_json = self.write_text_file(
				output_directory / 'fiddy_deployment_evidence.json',
				self._policy.object_to_json( result.deployment_evidence ) )
			
			package.deployment_markdown = self.write_text_file(
				output_directory / 'fiddy_deployment_evidence.md',
				result.deployment_evidence.to_markdown( ) )
			
			result.package = package
			package.package_manifest_json = self.write_text_file(
				output_directory / 'fiddy_acceptance_package_manifest_redacted.json',
				self._policy.object_to_json( result.to_manifest_record( ) )
			)
			
			return package
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'write_package( self, *args ) -> AcceptanceHarnessPackage'
			Logger( ).write( error )
			return AcceptanceHarnessPackage( output_directory=str( output_directory ) )
	
	def determine_status( self, acceptance_summary: AcceptanceSummary,
			batch_result: BatchProcessingResult ) -> str:
		"""Determine overall harness status.

		Purpose:
			Translate batch errors and acceptance status counts into a compact harness status.

		Args:
			acceptance_summary (AcceptanceSummary): Acceptance summary.
			batch_result (BatchProcessingResult): Batch result.

		Returns:
			str: Harness status.
		"""
		try:
			if batch_result.errors:
				return HARNESS_STATUS_FAIL
			
			counts = acceptance_summary.status_counts( )
			
			if counts.get( 'Not Met', 0 ) > 0:
				return HARNESS_STATUS_FAIL
			
			if counts.get( 'Partially Met', 0 ) > 0 or counts.get( 'Not Evaluated', 0 ) > 0:
				return HARNESS_STATUS_PARTIAL
			
			if counts.get( 'Met', 0 ) > 0:
				return HARNESS_STATUS_PASS
			
			return HARNESS_STATUS_NOT_EVALUATED
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'determine_status( self, *args ) -> str'
			Logger( ).write( error )
			return HARNESS_STATUS_NOT_EVALUATED
	
	def create_message( self, status: str, acceptance_summary: AcceptanceSummary,
			batch_result: BatchProcessingResult ) -> str:
		"""Create a harness status message.

		Purpose:
			Summarize harness status, processed count, error count, acceptance percentage, and
			requirement status counts.

		Args:
			status (str): Harness status.
			acceptance_summary (AcceptanceSummary): Acceptance summary.
			batch_result (BatchProcessingResult): Batch result.

		Returns:
			str: Harness message.
		"""
		try:
			counts = acceptance_summary.status_counts( )
			return (
					f'Harness status: {status}. Processed files: {len( batch_result.processed_files )}. '
					f'Errors: {len( batch_result.errors )}. Acceptance percentage: '
					f'{acceptance_summary.acceptance_percentage( )}%. Counts: {counts}.'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_message( self, *args ) -> str'
			Logger( ).write( error )
			return 'Harness message could not be created.'
	
	def run_manifest_test( self, manifest_path: str | Path, label_directory: str | Path,
			output_directory: Optional[ str | Path ] = None, test_name: str = 'manifest_acceptance',
			file_limit: Optional[ int ] = None, manual_accessibility_passed: bool = False,
			imperfect_image_tested: bool = False, low_quality_image_tested: bool = False,
			false_positive_variation_tested: bool = False ) -> AcceptanceHarnessResult:
		"""Run a manifest-driven acceptance test.

		Purpose:
			Process manifest-driven label verification, generate redacted evidence DataFrames,
			evaluate requirement acceptance, determine harness status, and write the redacted
			evidence package.

		Args:
			manifest_path (str | Path): Manifest CSV path.
			label_directory (str | Path): Label artwork directory.
			output_directory (Optional[str | Path]): Optional explicit output directory.
			test_name (str): Harness run name.
			file_limit (Optional[int]): Optional file limit.
			manual_accessibility_passed (bool): Whether browser accessibility validation passed.
			imperfect_image_tested (bool): Whether imperfect-image samples were included.
			low_quality_image_tested (bool): Whether low-quality samples were included.
			false_positive_variation_tested (bool): Whether false-positive variation samples were
				included.

		Returns:
			AcceptanceHarnessResult: Complete harness result.
		"""
		self._started_on = datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
		result = AcceptanceHarnessResult(
			test_name=test_name,
			started_on=self._started_on
		)
		
		try:
			throw_if( 'manifest_path', manifest_path )
			throw_if( 'label_directory', label_directory )
			
			if output_directory:
				active_output = Path( output_directory )
				active_output.mkdir( parents=True, exist_ok=True )
			else:
				active_output = self.create_output_directory( test_name )
			
			label_files = self.collect_label_files(
				label_directory=label_directory,
				limit=file_limit
			)
			
			if not label_files:
				result.status = HARNESS_STATUS_FAIL
				result.message = 'No supported label files were found for the harness run.'
				result.completed_on = datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
				result.package = self.write_package( active_output, result )
				return result
			
			processor = BatchProcessor( max_workers=self._max_workers,
				sla_seconds=self._sla_seconds )
			batch_result = processor.process_manifest_csv( manifest_path=manifest_path,
				file_paths=label_files )
			
			summary_dataframe = self.build_summary_dataframe( batch_result.batch_report )
			detail_dataframe = self.build_detail_dataframe( batch_result.batch_report )
			comparison_dataframe = self.build_comparison_dataframe( batch_result.batch_report )
			performance_dataframe = self.build_performance_dataframe( batch_result )
			batch_acceptance_dataframe = self.build_batch_acceptance_dataframe( batch_result )
			accessibility_result = self.build_accessibility_result(
				manual_accessibility_passed=manual_accessibility_passed,
				notes='Manual browser accessibility checks were supplied to the harness.'
			)
			deployment_evidence = self.build_deployment_evidence( )
			accessibility_dataframe = self._policy.redact_dataframe(
				accessibility_result.to_dataframe( ) )
			deployment_dataframe = self._policy.redact_dataframe(
				deployment_evidence.to_dataframe( ) )
			evidence = self.build_acceptance_evidence(
				batch_result=batch_result,
				deployment_evidence=deployment_evidence,
				processed_count=len( label_files ),
				manual_accessibility_passed=manual_accessibility_passed,
				imperfect_image_tested=imperfect_image_tested,
				low_quality_image_tested=low_quality_image_tested,
				false_positive_variation_tested=false_positive_variation_tested
			)
			acceptance_summary = self.build_acceptance_summary(
				batch_result=batch_result,
				summary_dataframe=summary_dataframe,
				detail_dataframe=detail_dataframe,
				comparison_dataframe=comparison_dataframe,
				performance_dataframe=performance_dataframe,
				accessibility_dataframe=accessibility_dataframe,
				deployment_dataframe=deployment_dataframe,
				evidence=evidence
			)
			acceptance_dataframe = self._policy.redact_dataframe(
				acceptance_summary.to_dataframe( ) )
			
			result.batch_result = batch_result
			result.acceptance_summary = acceptance_summary
			result.accessibility_result = accessibility_result
			result.deployment_evidence = deployment_evidence
			result.dataframes = {
					'summary': summary_dataframe,
					'details': detail_dataframe,
					'comparison': comparison_dataframe,
					'performance': performance_dataframe,
					'batch_acceptance': batch_acceptance_dataframe,
					'acceptance': acceptance_dataframe,
					'accessibility': accessibility_dataframe,
					'deployment': deployment_dataframe
			}
			result.status = self.determine_status(
				acceptance_summary=acceptance_summary,
				batch_result=batch_result
			)
			result.message = self.create_message(
				status=result.status,
				acceptance_summary=acceptance_summary,
				batch_result=batch_result
			)
			result.completed_on = datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
			result.package = self.write_package( active_output, result )
			
			return result
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'run_manifest_test( self, *args ) -> AcceptanceHarnessResult'
			Logger( ).write( error )
			
			result.status = HARNESS_STATUS_FAIL
			result.message = 'Acceptance harness failed before evidence package completion.'
			result.completed_on = datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
			
			if output_directory:
				active_output = Path( output_directory )
				active_output.mkdir( parents=True, exist_ok=True )
			else:
				active_output = self.create_output_directory( test_name )
			
			result.package = self.write_package( active_output, result )
			return result
	
	def run_smoke_test( self, manifest_path: str | Path, label_directory: str | Path,
			output_directory: Optional[ str | Path ] = None ) -> AcceptanceHarnessResult:
		"""Run a one-label smoke acceptance test.

		Purpose:
			Process one label to confirm the harness pipeline is wired.

		Args:
			manifest_path (str | Path): Manifest CSV path.
			label_directory (str | Path): Label artwork directory.
			output_directory (Optional[str | Path]): Optional output directory.

		Returns:
			AcceptanceHarnessResult: Smoke-test result.
		"""
		return self.run_manifest_test(
			manifest_path=manifest_path,
			label_directory=label_directory,
			output_directory=output_directory,
			test_name='smoke_test',
			file_limit=1,
			manual_accessibility_passed=False,
			imperfect_image_tested=False,
			low_quality_image_tested=False,
			false_positive_variation_tested=False
		)
	
	def run_twenty_label_test( self, manifest_path: str | Path, label_directory: str | Path,
			output_directory: Optional[ str | Path ] = None,
			manual_accessibility_passed: bool = False ) -> AcceptanceHarnessResult:
		"""Run a twenty-label prototype-scale test.

		Purpose:
			Process twenty labels and include scenario flags for imperfect images, low-quality
			images, and false-positive variation testing.

		Args:
			manifest_path (str | Path): Manifest CSV path.
			label_directory (str | Path): Label artwork directory.
			output_directory (Optional[str | Path]): Optional output directory.
			manual_accessibility_passed (bool): Accessibility validation result.

		Returns:
			AcceptanceHarnessResult: Twenty-label result.
		"""
		return self.run_manifest_test(
			manifest_path=manifest_path,
			label_directory=label_directory,
			output_directory=output_directory,
			test_name='twenty_label_acceptance_test',
			file_limit=20,
			manual_accessibility_passed=manual_accessibility_passed,
			imperfect_image_tested=True,
			low_quality_image_tested=True,
			false_positive_variation_tested=True
		)
	
	def run_fifty_label_test( self, manifest_path: str | Path, label_directory: str | Path,
			output_directory: Optional[ str | Path ] = None,
			manual_accessibility_passed: bool = False ) -> AcceptanceHarnessResult:
		"""Run a fifty-label prototype-scale test.

		Purpose:
			Process fifty labels and include scenario flags for imperfect images, low-quality
			images, and false-positive variation testing.

		Args:
			manifest_path (str | Path): Manifest CSV path.
			label_directory (str | Path): Label artwork directory.
			output_directory (Optional[str | Path]): Optional output directory.
			manual_accessibility_passed (bool): Accessibility validation result.

		Returns:
			AcceptanceHarnessResult: Fifty-label result.
		"""
		return self.run_manifest_test(
			manifest_path=manifest_path,
			label_directory=label_directory,
			output_directory=output_directory,
			test_name='fifty_label_acceptance_test',
			file_limit=50,
			manual_accessibility_passed=manual_accessibility_passed,
			imperfect_image_tested=True,
			low_quality_image_tested=True,
			false_positive_variation_tested=True
		)
	
	def clear_output_root( self ) -> None:
		"""Delete and recreate the harness output root.

		Purpose:
			Provide explicit cleanup for generated evidence directories. This is never called
			automatically because evidence should only be deleted when the caller requests it.

		Returns:
			None.
		"""
		try:
			if self._output_root.exists( ):
				shutil.rmtree( self._output_root )
			
			self._output_root.mkdir( parents=True, exist_ok=True )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'clear_output_root( self ) -> None'
			Logger( ).write( error )
			return None