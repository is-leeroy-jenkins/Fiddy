'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                batch_processor.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-06-2026
    ******************************************************************************************
    <copyright file="batch_processor.py" company="Terry D. Eppler">

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
        Provides manifest-driven batch processing for Fiddy label verification workflows.

        This module matches uploaded label files to manifest records, validates manifest and
        upload relationships, executes per-label verification with isolated item failures,
        records skipped and missing files, captures per-label timing data, calculates
        acceptance-oriented SLA and prototype-scale evidence, and returns batch verification,
        validation, and performance results suitable for reviewer display and export.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, Field

import config as cfg
from booger import Error, Logger, sanitize_text
from config import throw_if
from src.batch_manifest import BatchManifest, BatchManifestRecord, BatchManifestValidationResult
from src.constants import SEVERITY_HIGH, STATUS_REVIEW
from src.label_verifier import AlcoholLabelVerifier
from src.models import BatchVerificationReport, LabelCheckResult, LabelVerificationReport
from src.performance_monitor import BatchPerformanceSummary, LabelPerformanceResult, \
	PerformanceMonitor

# ==========================================================================================
# Batch Processing Result
# ==========================================================================================

class BatchProcessingResult( BaseModel ):
	"""Represent the complete result of a manifest-driven batch verification run.

	Purpose:
		The ``BatchProcessingResult`` model is the return contract for batch processing operations.
		It combines the batch verification report, manifest/file validation result, performance
		summary, per-file timing results, processed file names, skipped file names, errors, warnings,
		and acceptance-oriented evidence into one object that can be displayed by the Streamlit
		application or passed to report-writing utilities.

	Attributes:
		batch_report (BatchVerificationReport): Aggregated verification report containing one
			child report per processed or review-reported file.
		validation_result (BatchManifestValidationResult): Result of matching manifest records to
			uploaded label files.
		performance_summary (BatchPerformanceSummary): Batch-level timing and SLA summary.
		performance_results (List[LabelPerformanceResult]): Per-label processing timing results.
		processed_files (List[str]): File names attempted through the verification workflow.
		skipped_files (List[str]): File names skipped because they were missing, extra, or failed
			outside the isolated item runner.
		errors (List[str]): Blocking or reviewer-significant batch processing errors.
		warnings (List[str]): Non-blocking batch processing warnings.
		acceptance_record (Dict[str, object]): Acceptance evidence for SLA and prototype scale.
	"""
	
	batch_report: BatchVerificationReport = Field( default_factory=BatchVerificationReport )
	validation_result: BatchManifestValidationResult = Field(
		default_factory=BatchManifestValidationResult )
	performance_summary: BatchPerformanceSummary = Field( default_factory=BatchPerformanceSummary )
	performance_results: List[ LabelPerformanceResult ] = Field( default_factory=list )
	processed_files: List[ str ] = Field( default_factory=list )
	skipped_files: List[ str ] = Field( default_factory=list )
	errors: List[ str ] = Field( default_factory=list )
	warnings: List[ str ] = Field( default_factory=list )
	acceptance_record: Dict[ str, object ] = Field( default_factory=dict )
	
	def to_summary_record( self ) -> Dict[ str, object ]:
		"""Convert the batch processing result into a flat summary record.

		Purpose:
			Convert nested batch result state into a compact dictionary suitable for Streamlit metric
			panels, summary tables, CSV export, JSON serialization, and prototype acceptance review.
			The record reports processed and skipped file counts, manifest validity, manifest/upload
			matching counts, performance metrics, SLA breach counts, acceptance status, and aggregate
			error/warning counts.

		Returns:
			Dict[str, object]: Flat batch processing summary record. If rendering fails, the
			exception is logged and a conservative fallback record is returned.
		"""
		try:
			return {
					'Processed Files': len( self.processed_files ),
					'Skipped Files': len( self.skipped_files ),
					'Manifest Valid': self.validation_result.is_valid,
					'Manifest Rows': self.validation_result.total_manifest_rows,
					'Uploaded Files': self.validation_result.total_uploaded_files,
					'Matched Files': len( self.validation_result.matched_files ),
					'Missing Files': len( self.validation_result.missing_files ),
					'Extra Files': len( self.validation_result.extra_files ),
					'Average Seconds': round( self.performance_summary.average_seconds, 3 ),
					'Median Seconds': self.acceptance_record.get( 'Median Seconds', 0.0 ),
					'P95 Seconds': self.acceptance_record.get( 'P95 Seconds', 0.0 ),
					'Maximum Seconds': round( self.performance_summary.maximum_seconds, 3 ),
					'SLA Breaches': self.performance_summary.sla_breach_count,
					'SLA Breach Rate': self.acceptance_record.get( 'SLA Breach Rate', 0.0 ),
					'SLA Acceptance': self.acceptance_record.get( 'SLA Acceptance',
						'Not Evaluated' ),
					'Batch Size Acceptance': self.acceptance_record.get(
						'Batch Size Acceptance',
						'Not Evaluated'
					),
					'Overall Acceptance': self.acceptance_record.get(
						'Overall Acceptance',
						'Not Evaluated'
					),
					'Errors': len( self.errors ),
					'Warnings': len( self.warnings )
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_summary_record( ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Processed Files': 0,
					'Skipped Files': 0,
					'Manifest Valid': False,
					'Manifest Rows': 0,
					'Uploaded Files': 0,
					'Matched Files': 0,
					'Missing Files': 0,
					'Extra Files': 0,
					'Average Seconds': 0.0,
					'Median Seconds': 0.0,
					'P95 Seconds': 0.0,
					'Maximum Seconds': 0.0,
					'SLA Breaches': 0,
					'SLA Breach Rate': 0.0,
					'SLA Acceptance': 'Not Evaluated',
					'Batch Size Acceptance': 'Not Evaluated',
					'Overall Acceptance': 'Not Evaluated',
					'Errors': 1,
					'Warnings': 0
			}

# ==========================================================================================
# Batch Processor
# ==========================================================================================

class BatchProcessor( ):
	"""Process manifest-driven batches of uploaded alcohol label files.

	Purpose:
		The ``BatchProcessor`` class coordinates the batch verification workflow after reviewers
		provide application data and uploaded label files. It creates lookup maps for uploaded files
		and manifest records, validates the manifest/file relationship, processes matched items,
		records skipped files, creates reviewable reports for missing manifest files, collects
		per-label timing data, and returns a complete ``BatchProcessingResult`` with acceptance
		evidence.

	Attributes:
		_manifest (BatchManifest): Manifest service used for loading, mapping, and validation.
		_performance_monitor (PerformanceMonitor): Batch-level performance summarization service.
		_records (List[BatchManifestRecord]): Manifest records for the active batch.
		_file_paths (List[Path]): Uploaded label paths for the active batch.
		_file_map (Dict[str, Path]): Uploaded file lookup keyed by lowercase file name.
		_record_map (Dict[str, BatchManifestRecord]): Manifest record lookup keyed by lowercase
			file name.
		_batch_report (BatchVerificationReport): Aggregated batch verification report.
		_validation_result (BatchManifestValidationResult): Manifest/file validation result.
		_performance_results (List[LabelPerformanceResult]): Per-label timing results.
		_processed_files (List[str]): File names attempted through verification.
		_skipped_files (List[str]): File names skipped or not processable.
		_errors (List[str]): Batch-level processing errors.
		_warnings (List[str]): Batch-level processing warnings.
		_max_workers (int): Maximum number of parallel worker threads requested by the caller.
	"""
	
	_manifest: BatchManifest
	_performance_monitor: PerformanceMonitor
	_records: List[ BatchManifestRecord ]
	_file_paths: List[ Path ]
	_file_map: Dict[ str, Path ]
	_record_map: Dict[ str, BatchManifestRecord ]
	_batch_report: BatchVerificationReport
	_validation_result: BatchManifestValidationResult
	_performance_results: List[ LabelPerformanceResult ]
	_processed_files: List[ str ]
	_skipped_files: List[ str ]
	_errors: List[ str ]
	_warnings: List[ str ]
	_max_workers: int
	
	def __init__( self, max_workers: int = 4, sla_seconds: float | None = None ) -> None:
		"""Initialize the batch processor and supporting services.

		Purpose:
			Create a manifest service, performance monitor, empty batch report, validation result,
			and empty collections for performance results, processed files, skipped files, errors,
			and warnings. The worker count is normalized to at least one and capped later against
			the active batch size and configured worker ceiling.

		Args:
			max_workers (int): Requested maximum number of worker threads.
			sla_seconds (float | None): Optional per-label service-level threshold in seconds.

		Returns:
			None.
		"""
		try:
			self._max_workers = max( 1, int( max_workers ) )
		except Exception:
			self._max_workers = 1
		
		self._manifest = BatchManifest( )
		self._performance_monitor = PerformanceMonitor( sla_seconds=sla_seconds )
		self.reset_state( reset_manifest=False )
	
	@property
	def max_workers( self ) -> int:
		"""Return the configured maximum number of requested worker threads.

		Returns:
			int: Requested worker count retained by this processor instance.
		"""
		return self._max_workers
	
	@property
	def performance_results( self ) -> List[ LabelPerformanceResult ]:
		"""Return per-label performance results from the most recent batch run.

		Returns:
			List[LabelPerformanceResult]: Per-label performance results.
		"""
		return self._performance_results
	
	def reset_state( self, reset_manifest: bool = False ) -> None:
		"""Reset state for a new batch run.

		Purpose:
			Clear active records, file paths, lookup maps, batch report, validation result,
			performance results, processed files, skipped files, errors, and warnings. Optionally
			recreate the manifest service so CSV-load errors from a prior run cannot leak into a
			new manifest-processing attempt.

		Args:
			reset_manifest (bool): Indicates whether to recreate the manifest service.

		Returns:
			None.
		"""
		try:
			if reset_manifest:
				self._manifest = BatchManifest( )
			
			self._records = [ ]
			self._file_paths = [ ]
			self._file_map = { }
			self._record_map = { }
			self._batch_report = BatchVerificationReport( )
			self._validation_result = BatchManifestValidationResult( )
			self._performance_results = [ ]
			self._processed_files = [ ]
			self._skipped_files = [ ]
			self._errors = [ ]
			self._warnings = [ ]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'reset_state( reset_manifest: bool = False ) -> None'
			Logger( ).write( error )
			return None
	
	def create_file_map( self, file_paths: Iterable[ str | Path ] ) -> Dict[ str, Path ]:
		"""Create a case-insensitive uploaded-file lookup map.

		Purpose:
			Normalize supplied paths into ``Path`` objects and build a dictionary keyed by trimmed,
			lowercase file names. Duplicate uploaded filenames are recorded as warnings and later
			paths preserve the established dictionary overwrite behavior.

		Args:
			file_paths (Iterable[str | Path]): Uploaded label file paths to map.

		Returns:
			Dict[str, Path]: Uploaded-file map keyed by lowercase file name. If mapping fails, the
			exception is logged and an empty dictionary is returned.
		"""
		try:
			throw_if( 'file_paths', file_paths )
			self._file_paths = [ Path( file_path ) for file_path in file_paths ]
			self._file_map = { }
			
			for file_path in self._file_paths:
				key = file_path.name.strip( ).lower( )
				
				if not key:
					continue
				
				if key in self._file_map:
					self._warnings.append(
						f'Duplicate uploaded file name encountered: {file_path.name}' )
				
				self._file_map[ key ] = file_path
			
			return self._file_map
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_file_map( file_paths: Iterable[str | Path] ) -> Dict[str, Path]'
			Logger( ).write( error )
			return { }
	
	def create_record_map( self, records: List[ BatchManifestRecord ] ) -> Dict[
		str, BatchManifestRecord ]:
		"""Create a case-insensitive manifest-record lookup map.

		Purpose:
			Store supplied manifest records and delegate mapping to ``BatchManifest.get_record_map``.
			The returned map is keyed by lowercase file name and is used to locate the application
			record associated with each matched uploaded file.

		Args:
			records (List[BatchManifestRecord]): Manifest records parsed from the application manifest.

		Returns:
			Dict[str, BatchManifestRecord]: Manifest-record map keyed by lowercase expected label
			file name. If mapping fails, the exception is logged and an empty dictionary is returned.
		"""
		try:
			throw_if( 'records', records )
			self._records = records
			self._record_map = self._manifest.get_record_map( self._records )
			return self._record_map
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_record_map( records: List[BatchManifestRecord] ) -> Dict[str, BatchManifestRecord]'
			Logger( ).write( error )
			return { }
	
	def get_worker_count( self, matched_count: int ) -> int:
		"""Return a safe worker count for the active batch.

		Purpose:
			Cap worker count by the caller-requested worker count, active matched-file count, and
			``cfg.MAX_PARALLEL_WORKERS``. This prevents invalid or excessive executor sizes while
			preserving parallel execution for prototype batch runs.

		Args:
			matched_count (int): Number of matched files to process.

		Returns:
			int: Worker count between one and the active matched count. If no matched files exist,
			one is returned for safe fallback use.
		"""
		try:
			configured_limit = max( 1,
				int( getattr( cfg, 'MAX_PARALLEL_WORKERS', self._max_workers ) ) )
			active_count = max( 1, int( matched_count ) )
			return max( 1, min( self._max_workers, configured_limit, active_count ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_worker_count( matched_count: int ) -> int'
			Logger( ).write( error )
			return 1
	
	def create_error_report( self, file_name: str, message: str ) -> LabelVerificationReport:
		"""Create a reviewable verification report for an unprocessed batch item.

		Purpose:
			Create an empty ``LabelVerificationReport`` for the affected file and replace its rule
			results with a single ``LabelCheckResult`` describing the batch-processing failure. The
			result is marked ``Needs Review`` with high severity so the reviewer can see that the
			file was not verified normally and requires manual attention.

		Args:
			file_name (str): Label file name to place on the fallback report.
			message (str): Reviewer-facing error message to include as evidence and result text.

		Returns:
			LabelVerificationReport: Error report marked as needing review. If construction fails,
			the original empty-report fallback is returned for the supplied file name.
		"""
		try:
			throw_if( 'file_name', file_name )
			throw_if( 'message', message )
			safe_message = sanitize_text( message, 300 )
			report = LabelVerificationReport.empty( file_name=file_name )
			report.results = [
					LabelCheckResult(
						rule_id='batch_processing_error',
						field_name='Batch Processing',
						status=STATUS_REVIEW,
						severity=SEVERITY_HIGH,
						expected='Processable manifest row and uploaded label file',
						observed='Batch processing did not complete normally',
						confidence=0.0,
						evidence=safe_message,
						message=safe_message,
						requires_human_review=True
					)
			]
			report.determine_overall_status( )
			return report
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_error_report( file_name: str, message: str ) -> LabelVerificationReport'
			Logger( ).write( error )
			return LabelVerificationReport.empty( file_name=file_name )
	
	def create_missing_file_report( self, file_name: str ) -> LabelVerificationReport:
		"""Create a reviewable report for a manifest row without uploaded artwork.

		Purpose:
			Represent missing uploaded label artwork as a per-manifest-row review item. This improves
			batch output completeness because missing manifest rows appear in the report set rather
			than only in validation metadata.

		Args:
			file_name (str): Manifest file name that was not found among uploaded artwork.

		Returns:
			LabelVerificationReport: Review report for the missing file.
		"""
		try:
			throw_if( 'file_name', file_name )
			return self.create_error_report(
				file_name=file_name,
				message='Manifest row did not have a matching uploaded label file. Human review required.'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_missing_file_report( file_name: str ) -> LabelVerificationReport'
			Logger( ).write( error )
			return LabelVerificationReport.empty( file_name=file_name )
	
	def process_one( self, record: BatchManifestRecord, file_path: str | Path ) -> Tuple[
		LabelVerificationReport, LabelPerformanceResult ]:
		"""Process one manifest record and its matching uploaded label file.

		Purpose:
			Convert one manifest record into a ``LabelApplication``, create an isolated
			``AlcoholLabelVerifier``, time the work with a per-item ``PerformanceMonitor``, verify
			the matching uploaded file, assign measured processing time to the report, recalculate
			overall status, and return both verification and performance results.

		Args:
			record (BatchManifestRecord): Manifest row containing application data for the label.
			file_path (str | Path): Uploaded label file path matched to the manifest row.

		Returns:
			Tuple[LabelVerificationReport, LabelPerformanceResult]: Verification report and
			performance result for one label file. If processing fails, the tuple contains a
			reviewable error report plus a fallback timing result.
		"""
		file_name = Path( file_path ).name if file_path else 'Unknown File'
		monitor = PerformanceMonitor( sla_seconds=self._performance_monitor.sla_seconds )
		monitor.start( file_name )
		
		try:
			throw_if( 'record', record )
			throw_if( 'file_path', file_path )
			application = record.to_label_application( )
			verifier = AlcoholLabelVerifier( )
			report = verifier.verify_file( application, Path( file_path ) )
			performance = monitor.stop( file_name )
			report.processing_seconds = performance.processing_seconds
			report.determine_overall_status( )
			return report, performance
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'process_one( record: BatchManifestRecord, file_path: str | Path ) -> Tuple[LabelVerificationReport, LabelPerformanceResult]'
			Logger( ).write( error )
			performance = monitor.stop( file_name )
			report = self.create_error_report(
				file_name=file_name,
				message='Batch item failed during verification. See sanitized diagnostics for details.'
			)
			report.processing_seconds = performance.processing_seconds
			report.determine_overall_status( )
			return report, performance
	
	def add_missing_file_reports( self ) -> None:
		"""Add reviewable reports for manifest rows whose label files are missing.

		Purpose:
			Convert each validation-level missing file into a report-level review item. This ensures
			the batch report provides per-manifest-row visibility even when artwork was not uploaded.

		Returns:
			None.
		"""
		try:
			for file_name in self._validation_result.missing_files:
				self._skipped_files.append( file_name )
				self._batch_report.add_report( self.create_missing_file_report( file_name ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'add_missing_file_reports( ) -> None'
			Logger( ).write( error )
			return None
	
	def add_extra_file_warnings( self ) -> None:
		"""Record skipped uploaded files that do not have manifest records.

		Purpose:
			Carry extra uploaded files into skipped-file and warning state. Extra files cannot be
			verified because they have no application data, but the reviewer should still see that the
			files were ignored by the manifest-driven batch.

		Returns:
			None.
		"""
		try:
			for file_name in self._validation_result.extra_files:
				self._skipped_files.append( file_name )
				self._warnings.append(
					f'Uploaded file did not have a matching manifest row and was skipped: {file_name}'
				)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'add_extra_file_warnings( ) -> None'
			Logger( ).write( error )
			return None
	
	def get_matched_file_names( self ) -> List[ str ]:
		"""Return validation-matched file names that can be processed.

		Purpose:
			Filter validation-matched names to entries that exist in both the uploaded-file map and
			the manifest-record map. Missing lookup entries are retained as warnings rather than
			causing the batch to fail.

		Returns:
			List[str]: Matched file names eligible for processing.
		"""
		try:
			matched_names = [ ]
			
			for file_name in self._validation_result.matched_files:
				key = file_name.lower( )
				
				if key in self._file_map and key in self._record_map:
					matched_names.append( file_name )
				else:
					self._warnings.append(
						f'Matched file could not be resolved in processing maps and was skipped: {file_name}'
					)
					self._skipped_files.append( file_name )
			
			return matched_names
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_matched_file_names( ) -> List[str]'
			Logger( ).write( error )
			return [ ]
	
	def process_records( self, records: List[ BatchManifestRecord ],
			file_paths: Iterable[ str | Path ],
			progress_callback: Optional[
				Callable[ [ int, int, str ], None ] ] = None ) -> BatchProcessingResult:
		"""Process already loaded manifest records and uploaded label files.

		Purpose:
			Reset batch state, normalize uploaded file paths, create file and record lookup maps,
			validate the manifest records against uploaded files, record validation errors and
			warnings, create review reports for missing artwork, record extra files as skipped, and
			process matched files in a thread pool with isolated item failure handling.

		Args:
			records (List[BatchManifestRecord]): Manifest records containing application data.
			file_paths (Iterable[str | Path]): Uploaded label file paths.
			progress_callback (Optional[Callable[[int, int, str], None]]): Optional callback receiving
				completed count, total matched count, and current file name.

		Returns:
			BatchProcessingResult: Complete batch processing result assembled from current processor
			state. If setup or processing fails unexpectedly, the exception is logged, a batch-level
			error is appended, and ``create_result`` returns a conservative result.
		"""
		try:
			throw_if( 'records', records )
			throw_if( 'file_paths', file_paths )
			self.reset_state( reset_manifest=False )
			self._records = records
			self._file_paths = [ Path( file_path ) for file_path in file_paths ]
			self._file_map = self.create_file_map( self._file_paths )
			self._record_map = self.create_record_map( self._records )
			self._validation_result = self._manifest.validate_against_files(
				self._records,
				self._file_paths
			)
			self._errors.extend( self._validation_result.errors )
			self._warnings.extend( self._validation_result.warnings )
			self.add_missing_file_reports( )
			self.add_extra_file_warnings( )
			matched_names = self.get_matched_file_names( )
			total = len( matched_names )
			
			if total == 0:
				return self.create_result( )
			
			worker_count = self.get_worker_count( total )
			
			with ThreadPoolExecutor( max_workers=worker_count ) as executor:
				futures = {
						executor.submit(
							self.process_one,
							self._record_map[ file_name.lower( ) ],
							self._file_map[ file_name.lower( ) ]
						): file_name
						for file_name in matched_names
				}
				completed = 0
				
				for future in as_completed( futures ):
					file_name = futures[ future ]
					completed += 1
					
					try:
						report, performance = future.result( )
						self._batch_report.add_report( report )
						self._performance_results.append( performance )
						self._processed_files.append( file_name )
					except Exception as e:
						error = Error( e )
						error.cause = self.__class__.__name__
						error.module = __name__
						error.method = 'process_records( records: List[BatchManifestRecord], file_paths: Iterable[str | Path], progress_callback: Optional[Callable[[int, int, str], None]] = None ) -> BatchProcessingResult'
						Logger( ).write( error )
						self._errors.append(
							f'Batch future failed for {file_name}. See sanitized diagnostics.' )
						report = self.create_error_report(
							file_name=file_name,
							message='Batch future failed unexpectedly. Human review required.'
						)
						self._batch_report.add_report( report )
						self._skipped_files.append( file_name )
					
					if progress_callback:
						progress_callback( completed, total, file_name )
			
			return self.create_result( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'process_records( self, *args ) -> BatchProcessingResult'
			Logger( ).write( error )
			self._errors.append(
				'Batch processing failed before completion. See sanitized diagnostics.' )
			return self.create_result( )
	
	def process_manifest_csv( self, manifest_path: str | Path, file_paths: Iterable[ str | Path ],
			progress_callback: Optional[ Callable[ [ int, int, str ], None ] ] = None ) -> BatchProcessingResult:
		"""Load a manifest CSV and process its matching uploaded label files.

		Purpose:
			Reset processor state, load records through ``BatchManifest.load_csv``, carry manifest
			loading errors and warnings forward when no records are returned, and delegate successful
			record processing to ``process_records``. This keeps invalid-manifest responses
			structurally consistent for the UI and report writer.

		Args:
			manifest_path (str | Path): Path to the application-data manifest CSV.
			file_paths (Iterable[str | Path]): Uploaded label file paths.
			progress_callback (Optional[Callable[[int, int, str], None]]): Optional progress callback.

		Returns:
			BatchProcessingResult: Complete batch processing result.
		"""
		try:
			throw_if( 'manifest_path', manifest_path )
			throw_if( 'file_paths', file_paths )
			self.reset_state( reset_manifest=True )
			records = self._manifest.load_csv( manifest_path )
			
			if not records:
				self._errors.extend( self._manifest.errors )
				self._warnings.extend( self._manifest.warnings )
				self._file_paths = [ Path( file_path ) for file_path in file_paths ]
				self._validation_result = BatchManifestValidationResult( is_valid=False,
					total_manifest_rows=0, total_uploaded_files=len( self._file_paths ),
					errors=self._errors, warnings=self._warnings )
				return self.create_result( )
			
			return self.process_records( records, file_paths, progress_callback )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'process_manifest_csv( manifest_path: str | Path, file_paths: Iterable[str | Path], progress_callback: Optional[Callable[[int, int, str], None]] = None ) -> BatchProcessingResult'
			Logger( ).write( error )
			self._errors.append(
				'Manifest batch processing failed before completion. See sanitized diagnostics.' )
			return self.create_result( )
	
	def percentile( self, values: List[ float ], percentile_value: float ) -> float:
		"""Return a linear-interpolated percentile value.

		Purpose:
			Calculate percentile values without adding a new dependency. Empty lists return ``0.0``.
			The method sorts the values, clamps percentile input to 0 through 100, and interpolates
			between the nearest ranks.

		Args:
			values (List[float]): Numeric values to summarize.
			percentile_value (float): Percentile to calculate from 0 through 100.

		Returns:
			float: Percentile value rounded by callers as needed.
		"""
		try:
			if not values:
				return 0.0
			
			active_values = sorted( float( value ) for value in values )
			percent = max( 0.0, min( 100.0, float( percentile_value ) ) )
			position = (len( active_values ) - 1) * percent / 100.0
			lower_index = int( position )
			upper_index = min( lower_index + 1, len( active_values ) - 1 )
			fraction = position - lower_index
			return active_values[ lower_index ] + (
						(active_values[ upper_index ] - active_values[ lower_index ]) * fraction)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'percentile( values: List[float], percentile_value: float ) -> float'
			Logger( ).write( error )
			return 0.0
	
	def create_acceptance_record( self, performance_summary: BatchPerformanceSummary ) -> Dict[
		str, object ]:
		"""Create SLA and prototype-scale acceptance evidence for the batch.

		Purpose:
			Summarize processing results into stakeholder-facing acceptance evidence. The method
			reports average, median, p95, max seconds, breach count, breach rate, SLA acceptance,
			batch-size acceptance, and an overall acceptance status. Batches below the formal
			prototype acceptance minimum are marked ``Not Evaluated`` for batch-size acceptance rather
			than failed, which allows small smoke tests without misrepresenting scale readiness.

		Args:
			performance_summary (BatchPerformanceSummary): Batch-level performance summary.

		Returns:
			Dict[str, object]: Acceptance evidence record.
		"""
		try:
			seconds = [ result.processing_seconds for result in self._performance_results ]
			total = len( seconds )
			average_seconds = float( performance_summary.average_seconds or 0.0 )
			maximum_seconds = float( performance_summary.maximum_seconds or 0.0 )
			median_seconds = self.percentile( seconds, 50.0 )
			p95_seconds = self.percentile( seconds, 95.0 )
			breach_count = int( performance_summary.sla_breach_count or 0 )
			breach_rate = (breach_count / total) if total else 0.0
			configured_sla = float(
				getattr( cfg, 'LABEL_PROCESSING_SLA_SECONDS', performance_summary.sla_seconds ) )
			max_average = float(
				getattr( cfg, 'BATCH_ACCEPTANCE_MAX_AVERAGE_SECONDS', configured_sla ) )
			max_p95 = float( getattr( cfg, 'BATCH_ACCEPTANCE_MAX_P95_SECONDS', configured_sla ) )
			max_breach_rate = float( getattr( cfg, 'BATCH_ACCEPTANCE_MAX_BREACH_RATE', 0.0 ) )
			minimum_files = int( getattr( cfg, 'BATCH_ACCEPTANCE_MIN_FILES', 20 ) )
			maximum_files = int( getattr( cfg, 'BATCH_ACCEPTANCE_MAX_FILES', 50 ) )
			sla_met = bool(
				total > 0
				and average_seconds <= max_average
				and p95_seconds <= max_p95
				and breach_rate <= max_breach_rate
			)
			
			if total < minimum_files:
				batch_size_acceptance = 'Not Evaluated'
			elif total <= maximum_files:
				batch_size_acceptance = 'Met'
			else:
				batch_size_acceptance = 'Not Met'
			
			if total == 0:
				sla_acceptance = 'Not Evaluated'
			elif sla_met:
				sla_acceptance = 'Met'
			else:
				sla_acceptance = 'Not Met'
			
			if sla_acceptance == 'Met' and batch_size_acceptance in ('Met', 'Not Evaluated'):
				overall_acceptance = 'Met' if batch_size_acceptance == 'Met' else 'Partially Evaluated'
			elif sla_acceptance == 'Not Evaluated':
				overall_acceptance = 'Not Evaluated'
			else:
				overall_acceptance = 'Not Met'
			
			return {
					'Processed Files': total,
					'Minimum Acceptance Files': minimum_files,
					'Maximum Acceptance Files': maximum_files,
					'Average Seconds': round( average_seconds, 3 ),
					'Median Seconds': round( median_seconds, 3 ),
					'P95 Seconds': round( p95_seconds, 3 ),
					'Maximum Seconds': round( maximum_seconds, 3 ),
					'SLA Seconds': round( configured_sla, 3 ),
					'SLA Breaches': breach_count,
					'SLA Breach Rate': round( breach_rate, 4 ),
					'SLA Acceptance': sla_acceptance,
					'Batch Size Acceptance': batch_size_acceptance,
					'Overall Acceptance': overall_acceptance,
					'Acceptance Message': self.create_acceptance_message(
						total,
						sla_acceptance,
						batch_size_acceptance,
						overall_acceptance
					)
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_acceptance_record( performance_summary: BatchPerformanceSummary ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Processed Files': 0,
					'SLA Acceptance': 'Not Evaluated',
					'Batch Size Acceptance': 'Not Evaluated',
					'Overall Acceptance': 'Not Evaluated',
					'Acceptance Message': 'Acceptance evidence could not be generated.'
			}
	
	def create_acceptance_message( self, processed_files: int, sla_acceptance: str,
			batch_size_acceptance: str, overall_acceptance: str ) -> str:
		"""Create a human-readable acceptance message.

		Purpose:
			Explain SLA and batch-size acceptance outcomes in a compact sentence suitable for
			dashboards, exports, and acceptance reports.

		Args:
			processed_files (int): Number of files with timing results.
			sla_acceptance (str): SLA acceptance status.
			batch_size_acceptance (str): Batch-size acceptance status.
			overall_acceptance (str): Overall acceptance status.

		Returns:
			str: Reviewer-facing acceptance summary.
		"""
		try:
			return (
					f'Overall acceptance: {overall_acceptance}. Processed {processed_files} timed files. '
					f'SLA acceptance: {sla_acceptance}. Batch-size acceptance: {batch_size_acceptance}.'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_acceptance_message( self, *args ) -> str'
			Logger( ).write( error )
			return 'Acceptance message could not be generated.'
	
	def create_result( self ) -> BatchProcessingResult:
		"""Create the complete batch processing result from current processor state.

		Purpose:
			Summarize per-label performance results, ensure a validation result exists, generate
			acceptance evidence, and return a structurally consistent ``BatchProcessingResult`` from
			current state. This method is used after successful processing and guarded failure paths.

		Returns:
			BatchProcessingResult: Complete batch processing result assembled from current state. If
			result construction itself fails, a conservative fallback result is returned.
		"""
		try:
			performance_summary = self._performance_monitor.summarize( self._performance_results )
			acceptance_record = self.create_acceptance_record( performance_summary )
			
			if not hasattr( self, '_validation_result' ):
				self._validation_result = BatchManifestValidationResult(
					is_valid=False,
					errors=self._errors,
					warnings=self._warnings
				)
			
			return BatchProcessingResult(
				batch_report=self._batch_report,
				validation_result=self._validation_result,
				performance_summary=performance_summary,
				performance_results=self._performance_results,
				processed_files=self._processed_files,
				skipped_files=self._skipped_files,
				errors=self._errors,
				warnings=self._warnings,
				acceptance_record=acceptance_record
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_result( ) -> BatchProcessingResult'
			Logger( ).write( error )
			safe_message = 'Batch processing result creation failed. See sanitized diagnostics.'
			return BatchProcessingResult(
				batch_report=getattr( self, '_batch_report', BatchVerificationReport( ) ),
				validation_result=BatchManifestValidationResult(
					is_valid=False,
					errors=[ safe_message ],
					warnings=getattr( self, '_warnings', [ ] )
				),
				performance_summary=BatchPerformanceSummary( ),
				performance_results=getattr( self, '_performance_results', [ ] ),
				processed_files=getattr( self, '_processed_files', [ ] ),
				skipped_files=getattr( self, '_skipped_files', [ ] ),
				errors=[ safe_message ],
				warnings=getattr( self, '_warnings', [ ] ),
				acceptance_record={
						'Overall Acceptance': 'Not Evaluated',
						'Acceptance Message': safe_message
				}
			)
