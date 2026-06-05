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
        batch_processor.py
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, Field

from config import throw_if
from src.batch_manifest import BatchManifest, BatchManifestRecord, BatchManifestValidationResult
from src.constants import SEVERITY_HIGH, STATUS_REVIEW
from src.label_verifier import AlcoholLabelVerifier
from src.models import BatchVerificationReport, LabelApplication, LabelCheckResult, \
	LabelVerificationReport
from src.performance_monitor import BatchPerformanceSummary, LabelPerformanceResult, \
	PerformanceMonitor

# ==========================================================================================
# Batch Processing Result
# ==========================================================================================

class BatchProcessingResult( BaseModel ):
	"""
	Purpose:
	--------
	Represent the complete result of a manifest-driven batch verification run.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
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
	
	def to_summary_record( self ) -> Dict[ str, object ]:
		"""
		Purpose:
		--------
		Convert the batch processing result into a flat summary record.

		Parameters:
		-----------
		None

		Returns:
		--------
		Dict[str, object]: Flat batch processing summary record.
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
		except Exception:
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

# ==========================================================================================
# Batch Processor
# ==========================================================================================

class BatchProcessor( ):
	"""
	Purpose:
	--------
	Process a manifest-driven batch of uploaded alcohol label files by matching each uploaded
	file to its own application record, running OCR/rule verification, isolating per-file
	errors, and collecting SLA performance metrics.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
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
		"""
		Purpose:
		--------
		Initialize the batch processor with manifest and performance-monitor services.

		Parameters:
		-----------
		max_workers (int): Maximum number of parallel worker threads.
		sla_seconds (float | None): Optional per-label SLA threshold in seconds.

		Returns:
		--------
		None
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
		"""
		Purpose:
		--------
		Return the configured maximum number of worker threads.

		Parameters:
		-----------
		None

		Returns:
		--------
		int: Maximum worker count.
		"""
		return self._max_workers
	
	@property
	def performance_results( self ) -> List[ LabelPerformanceResult ]:
		"""
		Purpose:
		--------
		Return per-label performance results from the most recent batch run.

		Parameters:
		-----------
		None

		Returns:
		--------
		List[LabelPerformanceResult]: Per-label performance results.
		"""
		return self._performance_results
	
	def create_file_map( self, file_paths: Iterable[ str | Path ] ) -> Dict[ str, Path ]:
		"""
		Purpose:
		--------
		Create a case-insensitive uploaded-file map keyed by file name.

		Parameters:
		-----------
		file_paths (Iterable[str | Path]): Uploaded label file paths.

		Returns:
		--------
		Dict[str, Path]: Uploaded-file map keyed by lowercase file name.
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
		except Exception:
			return { }
	
	def create_record_map( self, records: List[ BatchManifestRecord ] ) -> Dict[
		str, BatchManifestRecord ]:
		"""
		Purpose:
		--------
		Create a case-insensitive manifest-record map keyed by expected label file name.

		Parameters:
		-----------
		records (List[BatchManifestRecord]): Manifest records.

		Returns:
		--------
		Dict[str, BatchManifestRecord]: Manifest-record map keyed by lowercase file name.
		"""
		try:
			throw_if( 'records', records )
			
			self._records = records
			self._record_map = self._manifest.get_record_map( self._records )
			
			return self._record_map
		except Exception:
			return { }
	
	def create_error_report( self, file_name: str, message: str ) -> LabelVerificationReport:
		"""
		Purpose:
		--------
		Create a verification report for a file that could not be processed.

		Parameters:
		-----------
		file_name (str): Label file name.
		message (str): Error message to include in the report.

		Returns:
		--------
		LabelVerificationReport: Error report marked as Needs Review.
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
		except Exception:
			return LabelVerificationReport.empty( file_name=file_name )
	
	def process_one( self, record: BatchManifestRecord, file_path: str | Path ) -> Tuple[
		LabelVerificationReport, LabelPerformanceResult ]:
		"""
		Purpose:
		--------
		Process one manifest record and matching uploaded label file.

		Parameters:
		-----------
		record (BatchManifestRecord): Manifest row for the uploaded label.
		file_path (str | Path): Matching uploaded label file path.

		Returns:
		--------
		Tuple[LabelVerificationReport, LabelPerformanceResult]: Verification and performance
		results for one label file.
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
			progress_callback: Optional[
				Callable[ [ int, int, str ], None ] ] = None ) -> BatchProcessingResult:
		"""
		Purpose:
		--------
		Process manifest records and uploaded label files after both have already been loaded.

		Parameters:
		-----------
		records (List[BatchManifestRecord]): Manifest records.
		file_paths (Iterable[str | Path]): Uploaded label file paths.
		progress_callback (Optional[Callable[[int, int, str], None]]): Optional callback that
		receives completed count, total count, and current file name.

		Returns:
		--------
		BatchProcessingResult: Complete batch processing result.
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
			
			self._validation_result = self._manifest.validate_against_files(
				self._records,
				self._file_paths
			)
			
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
						self._errors.append( f'Batch future failed for {file_name}: {e}' )
						report = self.create_error_report( file_name, str( e ) )
						self._batch_report.add_report( report )
						self._skipped_files.append( file_name )
					
					if progress_callback:
						progress_callback( completed, total, file_name )
			
			return self.create_result( )
		except Exception as e:
			self._errors.append( f'Batch processing failed: {e}' )
			return self.create_result( )
	
	def process_manifest_csv( self, manifest_path: str | Path, file_paths: Iterable[ str | Path ],
			progress_callback: Optional[ Callable[ [ int, int, str ], None ] ] = None ) -> BatchProcessingResult:
		"""
			Purpose:
			--------
			Load a manifest CSV file and process the matching uploaded label files.
	
			Parameters:
			-----------
			manifest_path (str | Path): Path to the application manifest CSV.
			file_paths (Iterable[str | Path]): Uploaded label file paths.
			progress_callback (Optional[Callable[[int, int, str], None]]): Optional callback that
			receives completed count, total count, and current file name.
	
			Returns:
			--------
			BatchProcessingResult: Complete batch processing result.
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
			self._errors.append( f'Manifest batch processing failed: {e}' )
			return self.create_result( )
	
	def create_result( self ) -> BatchProcessingResult:
		"""
		Purpose:
		--------
		Create the complete batch processing result from the current processor state.

		Parameters:
		-----------
		None

		Returns:
		--------
		BatchProcessingResult: Complete batch processing result.
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
			return BatchProcessingResult( batch_report=self._batch_report,
				validation_result=BatchManifestValidationResult( is_valid=False,
					errors=[ f'Batch processing result creation failed: {e}' ] ),
				performance_summary=BatchPerformanceSummary( ),
				performance_results=self._performance_results,
				processed_files=self._processed_files,
				skipped_files=self._skipped_files,
				errors=[ f'Batch processing result creation failed: {e}' ],
				warnings=self._warnings )

