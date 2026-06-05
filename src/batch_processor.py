'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                batch_processor.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="batch_processor.py" company="Terry D. Eppler">

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
        Provides manifest-driven batch processing for Fiddy label verification workflows.

        This module matches uploaded label files to manifest records, runs per-label
        verification, isolates item-level processing failures, tracks processed and skipped
        files, and returns batch verification, validation, and performance results suitable
        for reviewer display and export.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, Field

from booger import Error, Logger
from config import throw_if
from src.batch_manifest import BatchManifest, BatchManifestRecord, BatchManifestValidationResult
from src.constants import SEVERITY_HIGH, STATUS_REVIEW
from src.label_verifier import AlcoholLabelVerifier
from src.models import BatchVerificationReport, LabelApplication, LabelCheckResult, \
	LabelVerificationReport
from src.performance_monitor import BatchPerformanceSummary, LabelPerformanceResult, \
	PerformanceMonitor

class BatchProcessingResult( BaseModel ):
	"""Represent the complete result of a manifest-driven batch verification run.

	The ``BatchProcessingResult`` model is the return contract for batch processing operations.
	It combines the batch verification report, manifest/file validation result, performance
	summary, per-file timing results, processed file names, skipped file names, errors, and
	warnings into one object that can be displayed by the Streamlit application or passed to
	report-writing utilities.

	This model intentionally separates validation results from processing results. A batch may
	include validation errors or warnings before verification begins, while item-level OCR or
	rule execution failures may occur later during processing. Keeping these values together in
	one model gives the UI a complete view of what happened during a batch run.

	Attributes:
		batch_report (BatchVerificationReport): Aggregated verification report containing one
			child report per processed or error-reported file.
		validation_result (BatchManifestValidationResult): Result of matching manifest records
			to uploaded label files.
		performance_summary (BatchPerformanceSummary): Batch-level timing and SLA summary.
		performance_results (List[LabelPerformanceResult]): Per-label processing timing results.
		processed_files (List[str]): File names successfully processed through the batch workflow.
		skipped_files (List[str]): File names skipped because they were missing, extra, or failed
			during future handling.
		errors (List[str]): Blocking or reviewer-significant batch processing errors.
		warnings (List[str]): Non-blocking batch processing warnings.
	"""
	
	batch_report: BatchVerificationReport = Field( default_factory=BatchVerificationReport )
	validation_result: BatchManifestValidationResult = Field( default_factory=BatchManifestValidationResult )
	performance_summary: BatchPerformanceSummary = Field( default_factory=BatchPerformanceSummary )
	performance_results: List[ LabelPerformanceResult ] = Field( default_factory=list )
	processed_files: List[ str ] = Field( default_factory=list )
	skipped_files: List[ str ] = Field( default_factory=list )
	errors: List[ str ] = Field( default_factory=list )
	warnings: List[ str ] = Field( default_factory=list )
	
	def to_summary_record( self ) -> Dict[ str, object ]:
		"""Convert the batch processing result into a flat summary record.

		This method converts nested batch result state into a compact dictionary suitable for
		Streamlit metric panels, summary tables, CSV export, or JSON serialization. It reports
		processed and skipped file counts, manifest validity, manifest/upload matching counts,
		performance metrics, SLA breach counts, and aggregate error/warning counts.

		The method intentionally reports counts instead of full nested lists because this summary
		is intended for dashboards and top-level review. Detailed lists remain available on the
		model itself through ``validation_result``, ``processed_files``, ``skipped_files``,
		``errors``, and ``warnings``.

		Returns:
			Dict[str, object]: Flat batch processing summary record. If rendering fails, the
			exception is logged and a conservative fallback record is returned with zero counts,
			``Manifest Valid`` set to ``False``, and ``Errors`` set to ``1``.
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
					'Maximum Seconds': round( self.performance_summary.maximum_seconds, 3 ),
					'SLA Breaches': self.performance_summary.sla_breach_count,
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
					'Maximum Seconds': 0.0,
					'SLA Breaches': 0,
					'Errors': 1,
					'Warnings': 0
			}

class BatchProcessor( ):
	"""Process manifest-driven batches of uploaded alcohol label files.

	The ``BatchProcessor`` class coordinates the batch verification workflow after reviewers
	provide application data and uploaded label files. It creates lookup maps for uploaded
	files and manifest records, validates the manifest/file relationship, processes matched
	items, records skipped files, collects per-label timing data, and returns a complete
	``BatchProcessingResult``.

	The class supports two entry points. ``process_manifest_csv`` loads records from a manifest
	CSV before processing, while ``process_records`` accepts already parsed
	``BatchManifestRecord`` objects. Both paths preserve the same validation, processing,
	performance, and fallback behavior.

	Item-level processing is isolated through ``process_one`` so a failure in one file does not
	need to prevent the batch container from returning a usable result. When an individual item
	fails, the processor creates a reviewable error report for that file and captures a
	performance result so the batch output remains structurally complete.

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
		_processed_files (List[str]): File names successfully processed.
		_skipped_files (List[str]): File names skipped or not processable.
		_errors (List[str]): Batch-level processing errors.
		_warnings (List[str]): Batch-level processing warnings.
		_max_workers (int): Maximum number of parallel worker threads used by the executor.
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
		"""Initialize the batch processor and its supporting services.

		The constructor creates a manifest service, a performance monitor, an empty batch report,
		and empty collections for performance results, processed files, skipped files, errors,
		and warnings. The worker count is normalized to at least one worker to prevent invalid
		thread-pool configuration.

		Args:
			max_workers (int): Maximum number of parallel worker threads used by
				``ThreadPoolExecutor`` during matched-file processing. Values below one are
				normalized to one.
			sla_seconds (float | None): Optional per-label service-level threshold in seconds.
				When ``None``, the ``PerformanceMonitor`` applies its configured default.

		Returns:
			None.
		"""
		self._manifest = BatchManifest( )
		self._performance_monitor = PerformanceMonitor( sla_seconds=sla_seconds )
		self._batch_report = BatchVerificationReport( )
		self._performance_results = [ ]
		self._processed_files = [ ]
		self._skipped_files = [ ]
		self._errors = [ ]
		self._warnings = [ ]
		self._max_workers = max( 1, int( max_workers ) )
	
	@property
	def max_workers( self ) -> int:
		"""Return the configured maximum number of worker threads.

		This property exposes the normalized worker count that will be passed to the thread-pool
		executor when batch records are processed. It is useful for diagnostics, UI display, and
		tests that verify constructor normalization.

		Returns:
			int: Maximum worker count used by this processor instance.
		"""
		return self._max_workers
	
	@property
	def performance_results( self ) -> List[ LabelPerformanceResult ]:
		"""Return per-label performance results from the most recent batch run.

		The returned list contains the performance result for each processed label item captured
		during the most recent call to ``process_records`` or ``process_manifest_csv``. The list is
		reset at the beginning of each ``process_records`` run.

		Returns:
			List[LabelPerformanceResult]: Per-label performance results for the active or most
			recent batch run.
		"""
		return self._performance_results
	
	def create_file_map( self, file_paths: Iterable[ str | Path ] ) -> Dict[ str, Path ]:
		"""Create a case-insensitive uploaded-file lookup map.

		This method normalizes the supplied file-path iterable into ``Path`` objects and builds a
		dictionary keyed by each file name in trimmed lowercase form. The resulting map is used to
		match uploaded files against manifest records by file name, regardless of case.

		If duplicate uploaded file names are supplied with different paths, later dictionary
		assignments will overwrite earlier entries because the original implementation uses a
		dictionary keyed by lowercased file name. That behavior is preserved.

		Args:
			file_paths (Iterable[str | Path]): Uploaded label file paths to map.

		Returns:
			Dict[str, Path]: Uploaded-file map keyed by lowercase file name. If mapping fails,
			the exception is logged and an empty dictionary fallback is returned.
		"""
		try:
			throw_if( 'file_paths', file_paths )
			
			self._file_paths = [
					Path( file_path )
					for file_path in file_paths
			]
			
			self._file_map = {
					file_path.name.strip( ).lower( ): file_path
					for file_path in self._file_paths
			}
			
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

		This method stores the supplied manifest records on the processor and delegates mapping
		to ``BatchManifest.get_record_map``. The returned map is keyed by lowercase file name and
		is used to locate the application-data record associated with each matched uploaded file.

		Args:
			records (List[BatchManifestRecord]): Manifest records parsed from the application
				manifest.

		Returns:
			Dict[str, BatchManifestRecord]: Manifest-record map keyed by lowercase expected label
			file name. If mapping fails, the exception is logged and an empty dictionary fallback
			is returned.
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
	
	def create_error_report( self, file_name: str, message: str ) -> LabelVerificationReport:
		"""Create a reviewable verification report for an unprocessed batch item.

		This method creates an empty ``LabelVerificationReport`` for the affected file and then
		replaces its results with a single ``LabelCheckResult`` describing the batch-processing
		failure. The result is marked ``Needs Review`` with high severity so the reviewer can see
		that the file was not verified normally and requires manual attention.

		Args:
			file_name (str): Label file name to place on the fallback report.
			message (str): Reviewer-facing error message to include as evidence and result text.

		Returns:
			LabelVerificationReport: Error report marked as needing review. If construction fails,
			the exception is logged and the original empty-report fallback is returned for the
			supplied file name.
		"""
		try:
			throw_if( 'file_name', file_name )
			throw_if( 'message', message )
			
			report = LabelVerificationReport.empty( file_name=file_name )
			report.results = [
					LabelCheckResult(
						rule_id='batch_processing_error',
						field_name='Batch Processing',
						status=STATUS_REVIEW,
						severity=SEVERITY_HIGH,
						expected='Processable manifest row and uploaded label file',
						observed='Batch processing failed',
						confidence=0.0,
						evidence=message,
						message=message,
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
	
	def process_one( self, record: BatchManifestRecord, file_path: str | Path ) -> Tuple[ LabelVerificationReport, LabelPerformanceResult ]:
		"""Process one manifest record and its matching uploaded label file.

		This method converts one manifest record into a ``LabelApplication``, creates an
		``AlcoholLabelVerifier``, starts a per-item ``PerformanceMonitor``, verifies the
		matching uploaded file, stops the monitor, assigns the measured processing time to the
		report, recalculates overall status, and returns both the verification report and
		performance result.

		The method creates a fresh verifier and monitor for each item so individual batch items
		remain isolated from one another. If item processing fails, a separate monitor is used to
		return a performance object, and ``create_error_report`` creates a reviewer-facing error
		report for the affected file.

		Args:
			record (BatchManifestRecord): Manifest row containing the application data for the
				uploaded label.
			file_path (str | Path): Uploaded label file path matched to the manifest row.

		Returns:
			Tuple[LabelVerificationReport, LabelPerformanceResult]: Verification report and
			performance result for one label file. If item processing fails, the exception is
			logged and the tuple contains a reviewable error report plus a fallback timing result.
		"""
		file_name = Path( file_path ).name
		
		try:
			throw_if( 'record', record )
			throw_if( 'file_path', file_path )
			
			application = record.to_label_application( )
			verifier = AlcoholLabelVerifier( )
			monitor = PerformanceMonitor( sla_seconds=self._performance_monitor.sla_seconds )
			
			monitor.start( file_name )
			report = verifier.verify_file( application, Path( file_path ) )
			performance = monitor.stop( file_name )
			
			report.processing_seconds = performance.processing_seconds
			report.determine_overall_status( )
			
			return report, performance
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'process_one( self, *args ) -> Tuple[LabelVerificationReport, LabelPerformanceResult]'
			Logger( ).write( error )
			
			monitor = PerformanceMonitor( sla_seconds=self._performance_monitor.sla_seconds )
			monitor.start( file_name )
			performance = monitor.stop( file_name )
			
			report = self.create_error_report(
				file_name=file_name,
				message=f'Batch item failed: {e}'
			)
			
			return report, performance
	
	def process_records( self, records: List[ BatchManifestRecord ],
			file_paths: Iterable[ str | Path ],
			progress_callback: Optional[ Callable[ [ int, int, str ], None ] ] = None ) -> BatchProcessingResult:
		"""Process already loaded manifest records and uploaded label files.

		This method is the primary batch execution workflow when manifest records have already
		been parsed. It resets batch state, normalizes uploaded file paths, creates file and
		record lookup maps, validates the manifest records against uploaded files, records
		validation errors and warnings, identifies matched files, records missing and extra files
		as skipped, and processes matched files in a thread pool.

		Each completed future contributes a verification report, performance result, and processed
		file name. If a future raises unexpectedly, the method records a batch-level error,
		creates a reviewable error report for that file, and marks the file as skipped. The
		optional progress callback is invoked after each completed matched item.

		Args:
			records (List[BatchManifestRecord]): Manifest records containing application data.
			file_paths (Iterable[str | Path]): Uploaded label file paths.
			progress_callback (Optional[Callable[[int, int, str], None]]): Optional callback that
				receives completed count, total matched count, and the current file name after each
				future completes.

		Returns:
			BatchProcessingResult: Complete batch processing result assembled from current
			processor state. If setup or processing fails unexpectedly, the exception is logged,
			a batch-level error is appended, and ``create_result`` returns a conservative result.
		"""
		try:
			throw_if( 'records', records )
			throw_if( 'file_paths', file_paths )
			
			self._records = records
			self._file_paths = [
					Path( file_path )
					for file_path in file_paths
			]
			
			self._errors = [ ]
			self._warnings = [ ]
			self._processed_files = [ ]
			self._skipped_files = [ ]
			self._performance_results = [ ]
			self._batch_report = BatchVerificationReport( )
			self._file_map = self.create_file_map( self._file_paths )
			self._record_map = self.create_record_map( self._records )
			self._validation_result = self._manifest.validate_against_files( self._records,
				self._file_paths )
			
			self._errors.extend( self._validation_result.errors )
			self._warnings.extend( self._validation_result.warnings )
			
			matched_names = [
					file_name
					for file_name in self._validation_result.matched_files
					if
					file_name.lower( ) in self._file_map and file_name.lower( ) in self._record_map
			]
			
			for missing_file in self._validation_result.missing_files:
				self._skipped_files.append( missing_file )
			
			for extra_file in self._validation_result.extra_files:
				self._skipped_files.append( extra_file )
			
			total = len( matched_names )
			
			if total == 0:
				return self.create_result( )
			
			with ThreadPoolExecutor( max_workers=self._max_workers ) as executor:
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
						error.method = 'process_records( self, *args ) -> BatchProcessingResult'
						Logger( ).write( error )
						self._errors.append( f'Batch future failed for {file_name}: {e}' )
						report = self.create_error_report( file_name, str( e ) )
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
			self._errors.append( f'Batch processing failed: {e}' )
			return self.create_result( )
	
	def process_manifest_csv( self, manifest_path: str | Path, file_paths: Iterable[ str | Path ],
			progress_callback: Optional[ Callable[ [ int, int, str ], None ] ] = None ) -> BatchProcessingResult:
		"""Load a manifest CSV and process its matching uploaded label files.

		This method is the CSV-driven entry point for batch processing. It validates the manifest
		path and uploaded file iterable, loads records through ``BatchManifest.load_csv``, carries
		manifest loading errors and warnings forward when no records are returned, and delegates
		successful record processing to ``process_records``.

		If the manifest cannot be loaded or produces no records, the method creates a validation
		result marked invalid and returns a batch processing result from current state. This keeps
		the UI response structured even when the manifest file itself is invalid.

		Args:
			manifest_path (str | Path): Path to the application-data manifest CSV.
			file_paths (Iterable[str | Path]): Uploaded label file paths.
			progress_callback (Optional[Callable[[int, int, str], None]]): Optional callback that
				receives completed count, total matched count, and current file name.

		Returns:
			BatchProcessingResult: Complete batch processing result. If manifest loading or
			delegated processing fails unexpectedly, the exception is logged, a batch-level error
			is appended, and the current state is converted into a result.
		"""
		try:
			throw_if( 'manifest_path', manifest_path )
			throw_if( 'file_paths', file_paths )
			
			records = self._manifest.load_csv( manifest_path )
			
			if not records:
				self._errors.extend( self._manifest.errors )
				self._warnings.extend( self._manifest.warnings )
				self._validation_result = BatchManifestValidationResult( is_valid=False,
					errors=self._errors, warnings=self._warnings )
				
				return self.create_result( )
			
			return self.process_records( records, file_paths, progress_callback )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'process_manifest_csv( self, *ars ) -> BatchProcessingResult'
			Logger( ).write( error )
			self._errors.append( f'Manifest batch processing failed: {e}' )
			return self.create_result( )
	
	def create_result( self ) -> BatchProcessingResult:
		"""Create the complete batch processing result from current processor state.

		This method summarizes per-label performance results, ensures a validation result exists,
		and returns a ``BatchProcessingResult`` containing the current batch report, validation
		result, performance summary, per-label performance results, processed file names, skipped
		file names, errors, and warnings.

		The method is used both after successful processing and after guarded failure paths. That
		allows the caller to receive a structurally consistent result object even when an earlier
		stage failed and only partial state is available.

		Returns:
			BatchProcessingResult: Complete batch processing result assembled from current state.
			If result construction itself fails, the exception is logged and a conservative
			``BatchProcessingResult`` fallback is returned with an invalid validation result and
			the original fallback error message.
		"""
		try:
			performance_summary = self._performance_monitor.summarize( self._performance_results )
			
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
				warnings=self._warnings
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_result( ) -> BatchProcessingResult'
			Logger( ).write( error )
			return BatchProcessingResult( batch_report=self._batch_report,
				validation_result=BatchManifestValidationResult( is_valid=False,
					errors=[ f'Batch processing result creation failed: {e}' ] ),
				performance_summary=BatchPerformanceSummary( ),
				performance_results=self._performance_results,
				processed_files=self._processed_files,
				skipped_files=self._skipped_files,
				errors=[ f'Batch processing result creation failed: {e}' ],
				warnings=self._warnings )