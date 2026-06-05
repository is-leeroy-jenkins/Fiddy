'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                performance_monitor.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="performance_monitor.py" company="Terry D. Eppler">

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
        Provides per-label and batch-level processing-time monitoring for Fiddy.

        This module records label processing start and stop times, evaluates whether each
        label completed within the configured SLA threshold, and summarizes timing results for
        reviewer dashboards, batch reports, and export records.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field

import config as cfg
from booger import Error, Logger
from config import throw_if
from src.constants import STATUS_PASS, STATUS_WARNING

# ==========================================================================================
# Performance Models
# ==========================================================================================

class LabelPerformanceResult( BaseModel ):
	"""Represent timing and SLA status for one processed label.

	The ``LabelPerformanceResult`` model captures the timing outcome for a single label file.
	It records the file name, elapsed processing time, configured SLA threshold, whether the
	label completed within that threshold, reviewer-facing SLA status, reviewer-facing message,
	and start/completion timestamps.

	This model is used by batch processing and reporting workflows to show whether the
	prototype met the per-label usability target. It intentionally stores both numeric timing
	values and formatted timestamps so the raw model can support dashboards, exports, and
	diagnostics.

	Attributes:
		file_name (str): Label file name associated with the timing result.
		processing_seconds (float): Measured elapsed processing time in seconds.
		sla_seconds (float): SLA threshold used for the timing comparison.
		within_sla (bool): Indicates whether elapsed processing time was within the SLA.
		status (str): SLA status value used by reports and dashboards.
		message (str): Reviewer-facing performance message.
		started_on (datetime): Processing start timestamp.
		completed_on (datetime): Processing completion timestamp.
	"""
	
	file_name: str = Field( default='' )
	processing_seconds: float = Field( default=0.0 )
	sla_seconds: float = Field( default=5.0 )
	within_sla: bool = Field( default=False )
	status: str = Field( default=STATUS_WARNING )
	message: str = Field( default='' )
	started_on: datetime = Field( default_factory=datetime.now )
	completed_on: datetime = Field( default_factory=datetime.now )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert one performance result into a flat display/export record.

		This method converts the timing result into a dictionary suitable for Streamlit tables,
		DataFrame construction, CSV export, JSON export, or reviewer-facing performance reports.
		Numeric values are rounded to three decimal places to preserve useful timing precision
		without overloading the UI with excessive decimals.

		Returns:
			Dict[str, object]: Flat performance result record. If conversion fails, the exception
			is logged and a conservative fallback record is returned with zero processing time,
			``Within SLA`` set to ``False``, and the original fallback message.
		"""
		try:
			return {
					'File Name': self.file_name,
					'Processing Seconds': round( self.processing_seconds, 3 ),
					'SLA Seconds': round( self.sla_seconds, 3 ),
					'Within SLA': self.within_sla,
					'SLA Status': self.status,
					'Performance Message': self.message,
					'Started On': self.started_on.strftime( '%Y-%m-%d %H:%M:%S' ),
					'Completed On': self.completed_on.strftime( '%Y-%m-%d %H:%M:%S' )
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'File Name': self.file_name,
					'Processing Seconds': 0.0,
					'SLA Seconds': self.sla_seconds,
					'Within SLA': False,
					'SLA Status': STATUS_WARNING,
					'Performance Message': 'Performance record could not be rendered.',
					'Started On': '',
					'Completed On': ''
			}

class BatchPerformanceSummary( BaseModel ):
	"""Represent batch-level timing and SLA summary statistics.

	The ``BatchPerformanceSummary`` model aggregates per-label performance results into
	batch-level metrics. It stores the source results, total file count, average elapsed time,
	maximum elapsed time, minimum elapsed time, number of files within SLA, number of SLA
	breaches, and the SLA threshold used for the comparison.

	This model is returned by ``PerformanceMonitor.summarize`` and is intended for batch
	dashboards, report summaries, QA checks, and export records.

	Attributes:
		results (List[LabelPerformanceResult]): Per-label timing results summarized by this
			model.
		total_files (int): Number of label files represented in the summary.
		average_seconds (float): Average elapsed processing time.
		maximum_seconds (float): Maximum elapsed processing time.
		minimum_seconds (float): Minimum elapsed processing time.
		within_sla_count (int): Count of labels completed within the SLA threshold.
		sla_breach_count (int): Count of labels that exceeded the SLA threshold.
		sla_seconds (float): SLA threshold used for the batch summary.
	"""
	
	results: List[ LabelPerformanceResult ] = Field( default_factory=list )
	total_files: int = Field( default=0 )
	average_seconds: float = Field( default=0.0 )
	maximum_seconds: float = Field( default=0.0 )
	minimum_seconds: float = Field( default=0.0 )
	within_sla_count: int = Field( default=0 )
	sla_breach_count: int = Field( default=0 )
	sla_seconds: float = Field( default=5.0 )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert batch performance summary into a flat display/export record.

		This method converts aggregate timing metrics into a dictionary suitable for dashboard
		cards, summary tables, CSV export, JSON export, and report writing. Timing values are
		rounded to three decimal places for compact display while retaining enough precision to
		assess the five-second usability target.

		Returns:
			Dict[str, object]: Flat batch performance summary record. If conversion fails, the
			exception is logged and a conservative fallback summary is returned with zero counts
			and the current SLA threshold.
		"""
		try:
			return {
					'Total Files': self.total_files,
					'Average Seconds': round( self.average_seconds, 3 ),
					'Maximum Seconds': round( self.maximum_seconds, 3 ),
					'Minimum Seconds': round( self.minimum_seconds, 3 ),
					'Within SLA Count': self.within_sla_count,
					'SLA Breach Count': self.sla_breach_count,
					'SLA Seconds': round( self.sla_seconds, 3 )
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Total Files': 0,
					'Average Seconds': 0.0,
					'Maximum Seconds': 0.0,
					'Minimum Seconds': 0.0,
					'Within SLA Count': 0,
					'SLA Breach Count': 0,
					'SLA Seconds': self.sla_seconds
			}

# ==========================================================================================
# Performance Monitor
# ==========================================================================================

class PerformanceMonitor( ):
	"""Track per-label processing time and evaluate SLA performance.

	The ``PerformanceMonitor`` class provides start/stop timing for label processing workflows.
	It records high-resolution start times with ``time.perf_counter`` and human-readable start
	timestamps with ``datetime.now``. When processing stops, it creates a
	``LabelPerformanceResult`` that records elapsed seconds, SLA status, timestamps, and a
	reviewer-facing performance message.

	The monitor also stores all generated timing results for later summarization. Batch
	processors can either summarize the monitor's internal results or provide an explicit list of
	results to ``summarize`` and ``result_records``.

	Attributes:
		_sla_seconds (float): Configured per-label SLA threshold in seconds.
		_start_times (Dict[str, float]): Active high-resolution start times keyed by file name.
		_start_datetimes (Dict[str, datetime]): Active human-readable start timestamps keyed by
			file name.
		_results (List[LabelPerformanceResult]): Collected per-label performance results.
	"""
	
	_sla_seconds: float
	_start_times: Dict[ str, float ]
	_start_datetimes: Dict[ str, datetime ]
	_results: List[ LabelPerformanceResult ]
	
	def __init__( self, sla_seconds: float | None = None ) -> None:
		"""Initialize the monitor with a configured or default SLA threshold.

		The constructor reads the default threshold from ``cfg.LABEL_PROCESSING_SLA_SECONDS`` when
		no explicit threshold is supplied. If the configuration value is unavailable, the monitor
		defaults to ``5.0`` seconds. It also initializes empty dictionaries for active timings and
		an empty list for completed performance results.

		Args:
			sla_seconds (float | None): Optional SLA threshold in seconds. When ``None``, the
				configuration value or default value is used.

		Returns:
			None.
		"""
		default_sla = getattr( cfg, 'LABEL_PROCESSING_SLA_SECONDS', 5.0 )
		self._sla_seconds = float( sla_seconds if sla_seconds is not None else default_sla )
		self._start_times = { }
		self._start_datetimes = { }
		self._results = [ ]
	
	@property
	def sla_seconds( self ) -> float:
		"""Return the configured per-label SLA threshold.

		Returns:
			float: SLA threshold in seconds used by this monitor instance.
		"""
		return self._sla_seconds
	
	@property
	def results( self ) -> List[ LabelPerformanceResult ]:
		"""Return all collected per-label performance results.

		Returns:
			List[LabelPerformanceResult]: Collected timing results generated by ``stop``.
		"""
		return self._results
	
	def start( self, file_name: str ) -> None:
		"""Start timing one label file.

		This method stores both a high-resolution ``time.perf_counter`` value and a
		human-readable ``datetime`` timestamp for the supplied file name. The high-resolution
		value is used for elapsed-time calculation, while the datetime value is retained for
		reporting.

		Args:
			file_name (str): Label file name being processed.

		Returns:
			None.
		"""
		try:
			throw_if( 'file_name', file_name )
			
			self._start_times[ file_name ] = time.perf_counter( )
			self._start_datetimes[ file_name ] = datetime.now( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'start( file_name: str ) -> None'
			Logger( ).write( error )
			return None
	
	def stop( self, file_name: str ) -> LabelPerformanceResult:
		"""Stop timing one label file and create an SLA performance result.

		This method looks up the file's start time and start timestamp, calculates elapsed
		processing seconds, creates a ``LabelPerformanceResult``, appends it to the monitor's
		collected results, and removes the active start entries for the file. If no start entry
		exists, the method preserves the original fallback behavior by using the current time,
		which produces a near-zero elapsed duration.

		Args:
			file_name (str): Label file name being processed.

		Returns:
			LabelPerformanceResult: Per-label performance result. If timing fails, the exception
			is logged, the original fallback result is appended, and that fallback is returned.
		"""
		try:
			throw_if( 'file_name', file_name )
			
			started = self._start_times.get( file_name, time.perf_counter( ) )
			started_on = self._start_datetimes.get( file_name, datetime.now( ) )
			completed_on = datetime.now( )
			seconds = time.perf_counter( ) - started
			
			result = self.create_result(
				file_name=file_name,
				processing_seconds=seconds,
				started_on=started_on,
				completed_on=completed_on
			)
			
			self._results.append( result )
			
			if file_name in self._start_times:
				del self._start_times[ file_name ]
			
			if file_name in self._start_datetimes:
				del self._start_datetimes[ file_name ]
			
			return result
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'stop( file_name: str ) -> LabelPerformanceResult'
			Logger( ).write( error )
			result = LabelPerformanceResult(
				file_name=file_name,
				processing_seconds=0.0,
				sla_seconds=self._sla_seconds,
				within_sla=False,
				status=STATUS_WARNING,
				message='Processing time could not be measured.'
			)
			
			self._results.append( result )
			return result
	
	def create_result( self, file_name: str, processing_seconds: float, started_on: datetime,
			completed_on: datetime ) -> LabelPerformanceResult:
		"""Create a per-label performance result from elapsed processing time.

		This method evaluates whether the supplied elapsed seconds are within the configured SLA
		threshold and builds a ``LabelPerformanceResult`` with status, message, timestamps, and
		timing metadata. Passing results use ``STATUS_PASS`` and exceeded results use
		``STATUS_WARNING`` in accordance with the original behavior.

		Args:
			file_name (str): Label file name associated with the timing result.
			processing_seconds (float): Elapsed processing time in seconds.
			started_on (datetime): Processing start timestamp.
			completed_on (datetime): Processing completion timestamp.

		Returns:
			LabelPerformanceResult: Per-label SLA result. If result creation fails, the exception
			is logged and the original warning fallback result is returned.
		"""
		try:
			throw_if( 'file_name', file_name )
			throw_if( 'started_on', started_on )
			throw_if( 'completed_on', completed_on )
			seconds = float( processing_seconds )
			within_sla = seconds <= self._sla_seconds
			status = STATUS_PASS if within_sla else STATUS_WARNING
			
			message = (
					f'Processed within {self._sla_seconds:g}-second target.'
					if within_sla
					else f'Exceeded {self._sla_seconds:g}-second target.'
			)
			
			return LabelPerformanceResult( file_name=file_name, processing_seconds=seconds,
				sla_seconds=self._sla_seconds, within_sla=within_sla,
				status=status, message=message, started_on=started_on,
				completed_on=completed_on )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_result( self, *args ) -> LabelPerformanceResult'
			Logger( ).write( error )
			return LabelPerformanceResult( file_name=file_name, processing_seconds=0.0,
				sla_seconds=self._sla_seconds, within_sla=False, status=STATUS_WARNING,
				message='Performance result creation failed.' )
	
	def summarize( self, results: List[ LabelPerformanceResult ] | None = None ) -> BatchPerformanceSummary:
		"""Summarize per-label performance results at the batch level.

		This method summarizes either an explicit list of timing results or the monitor's
		collected internal results. It calculates total file count, average seconds, maximum
		seconds, minimum seconds, number of results within SLA, and number of SLA breaches. Empty
		result sets return a valid zero-valued summary using the configured SLA threshold.

		Args:
			results (List[LabelPerformanceResult] | None): Optional results to summarize. When
				``None``, the monitor's collected results are summarized.

		Returns:
			BatchPerformanceSummary: Batch performance summary. If summarization fails, the
			exception is logged and the original zero-valued summary fallback is returned.
		"""
		try:
			active_results = results if results is not None else self._results
			if not active_results:
				return BatchPerformanceSummary( results=[ ], total_files=0, average_seconds=0.0,
					maximum_seconds=0.0, minimum_seconds=0.0, within_sla_count=0,
					sla_breach_count=0, sla_seconds=self._sla_seconds )
			
			seconds = [
					result.processing_seconds
					for result in active_results
			]
			
			within_sla_count = sum(
				1
				for result in active_results
				if result.within_sla
			)
			
			breach_count = len( active_results ) - within_sla_count
			
			return BatchPerformanceSummary( results=active_results,
				total_files=len( active_results ),
				average_seconds=sum( seconds ) / len( seconds ),
				maximum_seconds=max( seconds ),
				minimum_seconds=min( seconds ),
				within_sla_count=within_sla_count,
				sla_breach_count=breach_count,
				sla_seconds=self._sla_seconds )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'summarize( results: List[LabelPerformanceResult] | None ) -> BatchPerformanceSummary'
			Logger( ).write( error )
			return BatchPerformanceSummary( results=[ ], total_files=0, average_seconds=0.0,
				maximum_seconds=0.0, minimum_seconds=0.0, within_sla_count=0,
				sla_breach_count=0, sla_seconds=self._sla_seconds )
	
	def result_records( self, results: List[ LabelPerformanceResult ] | None = None ) -> List[
		Dict[ str, object ] ]:
		"""Convert performance results into flat records for display or export.

		This method converts either an explicit list of performance results or the monitor's
		collected internal results into flat dictionaries by delegating to each result's
		``to_record`` method. The output is suitable for DataFrame display, CSV export, JSON
		export, or report-writing workflows.

		Args:
			results (List[LabelPerformanceResult] | None): Optional results to convert. When
				``None``, the monitor's collected results are converted.

		Returns:
			List[Dict[str, object]]: Flat performance records. If conversion fails, the exception
			is logged and an empty list is returned.
		"""
		try:
			active_results = results if results is not None else self._results
			
			return [
					result.to_record( )
					for result in active_results
			]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'result_records( self, *args ) -> List[Dict[str, object]]'
			Logger( ).write( error )
			return [ ]