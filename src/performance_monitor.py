'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                performance_monitor.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-06-2026
    ******************************************************************************************
    <copyright file="performance_monitor.py" company="Terry D. Eppler">

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
        Provides per-label timing, batch-level performance summaries, and SLA acceptance
        evidence for the Fiddy alcohol label verification workflow.

        This module records high-resolution processing start and stop times, evaluates whether
        each label completed within the configured per-label SLA, calculates batch statistics,
        computes median and percentile timing values, evaluates formal performance acceptance
        criteria, and converts timing outputs into flat records for dashboards, CSV exports,
        JSON exports, Markdown reports, and stakeholder acceptance evidence.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import statistics
import time
from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field

import config as cfg
from booger import Error, Logger
from config import throw_if
from src.constants import STATUS_PASS, STATUS_WARNING

def get_config_float( name: str, default: float ) -> float:
	"""Read a floating-point value from the configuration module.

	Purpose:
		Safely read optional acceptance and SLA configuration values without requiring every
		deployment or test harness to define the newest settings. Missing, empty, or invalid values
		return the supplied default.

	Parameters:
		name (str): Configuration attribute name.
		default (float): Default value used when the configuration value is unavailable.

	Returns:
		float: Parsed configuration value or the supplied default.
	"""
	try:
		throw_if( 'name', name )
		value = getattr( cfg, name, default )
		return float( value )
	except Exception as e:
		error = Error( e )
		error.cause = 'PerformanceMonitor'
		error.module = __name__
		error.method = 'get_config_float( name: str, default: float ) -> float'
		Logger( ).write( error )
		return default

def calculate_percentile( values: List[ float ], percentile: float ) -> float:
	"""Calculate a percentile from a list of numeric values.

	Purpose:
		Provide deterministic percentile calculation without adding a NumPy dependency. The
		function sorts the supplied values and uses linear interpolation between neighboring
		values when the desired percentile falls between two observed positions.

	Parameters:
		values (List[float]): Numeric values to summarize.
		percentile (float): Percentile value from ``0`` through ``100``.

	Returns:
		float: Calculated percentile value. Empty input returns ``0.0``.
	"""
	try:
		if not values:
			return 0.0
		
		clean_values = sorted( float( value ) for value in values )
		
		if len( clean_values ) == 1:
			return clean_values[ 0 ]
		
		percent = max( 0.0, min( float( percentile ), 100.0 ) )
		position = (len( clean_values ) - 1) * (percent / 100.0)
		lower_index = int( position )
		upper_index = min( lower_index + 1, len( clean_values ) - 1 )
		weight = position - lower_index
		
		lower_value = clean_values[ lower_index ]
		upper_value = clean_values[ upper_index ]
		
		return lower_value + ((upper_value - lower_value) * weight)
	except Exception as e:
		error = Error( e )
		error.cause = 'PerformanceMonitor'
		error.module = __name__
		error.method = 'calculate_percentile( values: List[float], percentile: float ) -> float'
		Logger( ).write( error )
		return 0.0

# ==========================================================================================
# Performance Models
# ==========================================================================================

class LabelPerformanceResult( BaseModel ):
	"""Represent timing and SLA status for one processed label.

	The ``LabelPerformanceResult`` model captures the timing outcome for a single label file.
	It records the file name, elapsed processing time, configured SLA threshold, whether the
	label completed within that threshold, reviewer-facing SLA status, reviewer-facing message,
	start timestamp, completion timestamp, and calculated breach seconds.

	This model is used by batch processing and reporting workflows to show whether the prototype
	met the per-label usability target. It intentionally stores both numeric timing values and
	formatted timestamps so the raw model can support dashboards, exports, and diagnostics.

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
	
	@property
	def breach_seconds( self ) -> float:
		"""Return seconds above the configured SLA threshold.

		Purpose:
			Calculate how far the label exceeded the SLA threshold. Labels within SLA return
			``0.0`` so the value is safe for dashboard display, CSV export, and aggregate analysis.

		Parameters:
			None.

		Returns:
			float: Non-negative number of seconds above the SLA threshold.
		"""
		try:
			return max( 0.0, float( self.processing_seconds ) - float( self.sla_seconds ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'breach_seconds( self ) -> float'
			Logger( ).write( error )
			return 0.0
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert one performance result into a flat display/export record.

		Purpose:
			Convert the timing result into a dictionary suitable for Streamlit tables, DataFrame
			construction, CSV export, JSON export, or reviewer-facing performance reports. Numeric
			values are rounded to three decimal places to preserve useful timing precision without
			overloading the UI with excessive decimals.

		Parameters:
			None.

		Returns:
			Dict[str, object]: Flat performance result record. If conversion fails, the exception
			is logged and a conservative fallback record is returned.
		"""
		try:
			return {
					'File Name': self.file_name,
					'Processing Seconds': round( self.processing_seconds, 3 ),
					'SLA Seconds': round( self.sla_seconds, 3 ),
					'Within SLA': self.within_sla,
					'SLA Breach Seconds': round( self.breach_seconds, 3 ),
					'SLA Status': self.status,
					'Performance Message': self.message,
					'Started On': self.started_on.strftime( '%Y-%m-%d %H:%M:%S' ),
					'Completed On': self.completed_on.strftime( '%Y-%m-%d %H:%M:%S' )
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'File Name': self.file_name,
					'Processing Seconds': 0.0,
					'SLA Seconds': self.sla_seconds,
					'Within SLA': False,
					'SLA Breach Seconds': 0.0,
					'SLA Status': STATUS_WARNING,
					'Performance Message': 'Performance record could not be rendered.',
					'Started On': '',
					'Completed On': ''
			}

class PerformanceAcceptanceResult( BaseModel ):
	"""Represent formal SLA acceptance evidence for one batch.

	The ``PerformanceAcceptanceResult`` model stores the calculated acceptance outcome for a
	batch timing summary. It compares average processing time, p95 processing time, and SLA
	breach rate against configured acceptance thresholds. This separates measured performance
	from acceptance judgment so reports can show both the raw values and the pass/fail
	determination.

	Attributes:
		total_files (int): Number of timed label files represented in the acceptance result.
		average_seconds (float): Average elapsed processing time.
		p95_seconds (float): Ninety-fifth percentile elapsed processing time.
		sla_breach_rate (float): Fraction of labels exceeding the SLA threshold.
		average_target_seconds (float): Acceptance target for average processing time.
		p95_target_seconds (float): Acceptance target for p95 processing time.
		max_breach_rate (float): Maximum allowed SLA breach rate.
		meets_average_target (bool): Indicates whether average time met the target.
		meets_p95_target (bool): Indicates whether p95 time met the target.
		meets_breach_rate_target (bool): Indicates whether breach rate met the target.
		meets_acceptance (bool): Indicates whether all evaluated performance criteria passed.
		status (str): Acceptance status text.
		message (str): Reviewer-facing acceptance explanation.
	"""
	
	total_files: int = Field( default=0 )
	average_seconds: float = Field( default=0.0 )
	p95_seconds: float = Field( default=0.0 )
	sla_breach_rate: float = Field( default=0.0 )
	average_target_seconds: float = Field( default=5.0 )
	p95_target_seconds: float = Field( default=5.0 )
	max_breach_rate: float = Field( default=0.0 )
	meets_average_target: bool = Field( default=False )
	meets_p95_target: bool = Field( default=False )
	meets_breach_rate_target: bool = Field( default=False )
	meets_acceptance: bool = Field( default=False )
	status: str = Field( default='Not Evaluated' )
	message: str = Field( default='' )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert the SLA acceptance result into a flat display/export record.

		Purpose:
			Create a compact dictionary containing acceptance status, measured values, target
			values, Boolean outcomes, and a plain-language message for dashboards, reports, and
			acceptance evidence exports.

		Parameters:
			None.

		Returns:
			Dict[str, object]: Flat performance acceptance record.
		"""
		try:
			return {
					'Performance Acceptance Status': self.status,
					'Performance Acceptance Met': self.meets_acceptance,
					'Acceptance Message': self.message,
					'Acceptance Total Files': self.total_files,
					'Acceptance Average Seconds': round( self.average_seconds, 3 ),
					'Acceptance P95 Seconds': round( self.p95_seconds, 3 ),
					'Acceptance SLA Breach Rate': round( self.sla_breach_rate, 4 ),
					'Average Target Seconds': round( self.average_target_seconds, 3 ),
					'P95 Target Seconds': round( self.p95_target_seconds, 3 ),
					'Maximum Breach Rate': round( self.max_breach_rate, 4 ),
					'Meets Average Target': self.meets_average_target,
					'Meets P95 Target': self.meets_p95_target,
					'Meets Breach Rate Target': self.meets_breach_rate_target
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Performance Acceptance Status': 'Not Evaluated',
					'Performance Acceptance Met': False,
					'Acceptance Message': 'Performance acceptance record could not be rendered.',
					'Acceptance Total Files': 0,
					'Acceptance Average Seconds': 0.0,
					'Acceptance P95 Seconds': 0.0,
					'Acceptance SLA Breach Rate': 0.0,
					'Average Target Seconds': self.average_target_seconds,
					'P95 Target Seconds': self.p95_target_seconds,
					'Maximum Breach Rate': self.max_breach_rate,
					'Meets Average Target': False,
					'Meets P95 Target': False,
					'Meets Breach Rate Target': False
			}

class BatchPerformanceSummary( BaseModel ):
	"""Represent batch-level timing and SLA summary statistics.

	The ``BatchPerformanceSummary`` model aggregates per-label performance results into
	batch-level metrics. It stores the source results, total file count, average elapsed time,
	maximum elapsed time, minimum elapsed time, median elapsed time, p50, p90, p95, number of
	files within SLA, number of SLA breaches, SLA breach rate, SLA threshold, and formal
	performance acceptance result.

	This model is returned by ``PerformanceMonitor.summarize`` and is intended for batch
	dashboards, report summaries, QA checks, acceptance checks, and export records.

	Attributes:
		results (List[LabelPerformanceResult]): Per-label timing results summarized by this model.
		total_files (int): Number of label files represented in the summary.
		average_seconds (float): Average elapsed processing time.
		maximum_seconds (float): Maximum elapsed processing time.
		minimum_seconds (float): Minimum elapsed processing time.
		median_seconds (float): Median elapsed processing time.
		p50_seconds (float): Fiftieth percentile elapsed processing time.
		p90_seconds (float): Ninetieth percentile elapsed processing time.
		p95_seconds (float): Ninety-fifth percentile elapsed processing time.
		within_sla_count (int): Count of labels completed within the SLA threshold.
		sla_breach_count (int): Count of labels that exceeded the SLA threshold.
		sla_breach_rate (float): Fraction of labels exceeding the SLA threshold.
		sla_seconds (float): SLA threshold used for the batch summary.
		acceptance_result (PerformanceAcceptanceResult): Formal performance acceptance outcome.
	"""
	
	results: List[ LabelPerformanceResult ] = Field( default_factory=list )
	total_files: int = Field( default=0 )
	average_seconds: float = Field( default=0.0 )
	maximum_seconds: float = Field( default=0.0 )
	minimum_seconds: float = Field( default=0.0 )
	median_seconds: float = Field( default=0.0 )
	p50_seconds: float = Field( default=0.0 )
	p90_seconds: float = Field( default=0.0 )
	p95_seconds: float = Field( default=0.0 )
	within_sla_count: int = Field( default=0 )
	sla_breach_count: int = Field( default=0 )
	sla_breach_rate: float = Field( default=0.0 )
	sla_seconds: float = Field( default=5.0 )
	acceptance_result: PerformanceAcceptanceResult = Field(
		default_factory=PerformanceAcceptanceResult )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert batch performance summary into a flat display/export record.

		Purpose:
			Convert aggregate timing metrics and acceptance evidence into a dictionary suitable for
			dashboard cards, summary tables, CSV export, JSON export, and report writing. Timing
			values are rounded to three decimal places for compact display while retaining enough
			precision to assess the five-second usability target.

		Parameters:
			None.

		Returns:
			Dict[str, object]: Flat batch performance summary record. If conversion fails, the
			exception is logged and a conservative fallback summary is returned.
		"""
		try:
			record = {
					'Total Files': self.total_files,
					'Average Seconds': round( self.average_seconds, 3 ),
					'Median Seconds': round( self.median_seconds, 3 ),
					'P50 Seconds': round( self.p50_seconds, 3 ),
					'P90 Seconds': round( self.p90_seconds, 3 ),
					'P95 Seconds': round( self.p95_seconds, 3 ),
					'Maximum Seconds': round( self.maximum_seconds, 3 ),
					'Minimum Seconds': round( self.minimum_seconds, 3 ),
					'Within SLA Count': self.within_sla_count,
					'SLA Breach Count': self.sla_breach_count,
					'SLA Breach Rate': round( self.sla_breach_rate, 4 ),
					'SLA Seconds': round( self.sla_seconds, 3 )
			}
			
			record.update( self.acceptance_result.to_record( ) )
			return record
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Total Files': 0,
					'Average Seconds': 0.0,
					'Median Seconds': 0.0,
					'P50 Seconds': 0.0,
					'P90 Seconds': 0.0,
					'P95 Seconds': 0.0,
					'Maximum Seconds': 0.0,
					'Minimum Seconds': 0.0,
					'Within SLA Count': 0,
					'SLA Breach Count': 0,
					'SLA Breach Rate': 0.0,
					'SLA Seconds': self.sla_seconds,
					'Performance Acceptance Status': 'Not Evaluated',
					'Performance Acceptance Met': False,
					'Acceptance Message': 'Performance summary could not be rendered.'
			}

# ==========================================================================================
# Performance Monitor
# ==========================================================================================

class PerformanceMonitor( ):
	"""Track per-label processing time and evaluate SLA performance.

	The ``PerformanceMonitor`` class provides start/stop timing for label processing workflows.
	It records high-resolution start times with ``time.perf_counter`` and human-readable start
	timestamps with ``datetime.now``. When processing stops, it creates a
	``LabelPerformanceResult`` that records elapsed seconds, SLA status, timestamps, breach
	seconds, and a reviewer-facing performance message.

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

		Purpose:
			Read the default threshold from ``cfg.LABEL_PROCESSING_SLA_SECONDS`` when no explicit
			threshold is supplied. If the configuration value is unavailable, the monitor defaults to
			``5.0`` seconds. The constructor also initializes empty dictionaries for active timings
			and an empty list for completed performance results.

		Parameters:
			sla_seconds (float | None): Optional SLA threshold in seconds. When ``None``, the
				configuration value or default value is used.

		Returns:
			None.
		"""
		try:
			default_sla = getattr( cfg, 'LABEL_PROCESSING_SLA_SECONDS', 5.0 )
			self._sla_seconds = float( sla_seconds if sla_seconds is not None else default_sla )
			self._start_times = { }
			self._start_datetimes = { }
			self._results = [ ]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = '__init__( self, sla_seconds: float | None = None ) -> None'
			Logger( ).write( error )
			self._sla_seconds = 5.0
			self._start_times = { }
			self._start_datetimes = { }
			self._results = [ ]
	
	@property
	def sla_seconds( self ) -> float:
		"""Return the configured per-label SLA threshold.

		Purpose:
			Expose the active SLA threshold to batch processors and report builders.

		Parameters:
			None.

		Returns:
			float: SLA threshold in seconds used by this monitor instance.
		"""
		return self._sla_seconds
	
	@property
	def results( self ) -> List[ LabelPerformanceResult ]:
		"""Return all collected per-label performance results.

		Purpose:
			Expose completed timing results generated by ``stop`` while preserving the existing
			monitor usage pattern.

		Parameters:
			None.

		Returns:
			List[LabelPerformanceResult]: Collected timing results.
		"""
		return self._results
	
	def reset( self ) -> None:
		"""Clear active timers and collected timing results.

		Purpose:
			Reset the monitor so the same instance can be reused for a new benchmark, smoke test, or
			batch run without carrying forward previous timing results.

		Parameters:
			None.

		Returns:
			None.
		"""
		try:
			self._start_times = { }
			self._start_datetimes = { }
			self._results = [ ]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'reset( self ) -> None'
			Logger( ).write( error )
			return None
	
	def start( self, file_name: str ) -> None:
		"""Start timing one label file.

		Purpose:
			Store both a high-resolution ``time.perf_counter`` value and a human-readable
			``datetime`` timestamp for the supplied file name. The high-resolution value is used for
			elapsed-time calculation, while the datetime value is retained for reporting.

		Parameters:
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
			error.method = 'start( self, file_name: str ) -> None'
			Logger( ).write( error )
			return None
	
	def stop( self, file_name: str ) -> LabelPerformanceResult:
		"""Stop timing one label file and create an SLA performance result.

		Purpose:
			Look up the file's start time and start timestamp, calculate elapsed processing seconds,
			create a ``LabelPerformanceResult``, append it to the monitor's collected results, and
			remove active start entries for the file. If no start entry exists, the method preserves
			the original fallback behavior by using the current time, which produces a near-zero
			elapsed duration.

		Parameters:
			file_name (str): Label file name being processed.

		Returns:
			LabelPerformanceResult: Per-label performance result. If timing fails, the exception is
			logged, a warning fallback is appended, and that fallback is returned.
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
			error.method = 'stop( self, file_name: str ) -> LabelPerformanceResult'
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

		Purpose:
			Evaluate whether the supplied elapsed seconds are within the configured SLA threshold
			and build a ``LabelPerformanceResult`` with status, message, timestamps, and timing
			metadata. Passing results use ``STATUS_PASS`` and exceeded results use
			``STATUS_WARNING`` in accordance with the established behavior.

		Parameters:
			file_name (str): Label file name associated with the timing result.
			processing_seconds (float): Elapsed processing time in seconds.
			started_on (datetime): Processing start timestamp.
			completed_on (datetime): Processing completion timestamp.

		Returns:
			LabelPerformanceResult: Per-label SLA result. If result creation fails, the exception is
			logged and a warning fallback result is returned.
		"""
		try:
			throw_if( 'file_name', file_name )
			throw_if( 'started_on', started_on )
			throw_if( 'completed_on', completed_on )
			
			seconds = max( 0.0, float( processing_seconds ) )
			within_sla = seconds <= self._sla_seconds
			status = STATUS_PASS if within_sla else STATUS_WARNING
			
			message = (
					f'Processed within {self._sla_seconds:g}-second target.'
					if within_sla
					else f'Exceeded {self._sla_seconds:g}-second target by '
					     f'{seconds - self._sla_seconds:.3f} seconds.'
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
				sla_seconds=self._sla_seconds, within_sla=False,
				status=STATUS_WARNING, message='Performance result creation failed.' )
	
	def create_acceptance_result( self, total_files: int, average_seconds: float,
			p95_seconds: float, sla_breach_rate: float ) -> PerformanceAcceptanceResult:
		"""Create formal performance acceptance evidence.

		Purpose:
			Compare measured batch timing values against configured acceptance thresholds and return
			a structured acceptance result. Empty result sets are marked ``Not Evaluated``. Non-empty
			result sets are marked ``Met`` only when average seconds, p95 seconds, and breach rate
			all meet their configured targets.

		Parameters:
			total_files (int): Number of timed label files.
			average_seconds (float): Average elapsed processing time.
			p95_seconds (float): Ninety-fifth percentile elapsed processing time.
			sla_breach_rate (float): Fraction of labels that exceeded the SLA threshold.

		Returns:
			PerformanceAcceptanceResult: Formal SLA acceptance result.
		"""
		try:
			average_target = get_config_float( 'BATCH_ACCEPTANCE_MAX_AVERAGE_SECONDS',
				self._sla_seconds )
			
			p95_target = get_config_float( 'BATCH_ACCEPTANCE_MAX_P95_SECONDS',
				self._sla_seconds )
			
			max_breach_rate = get_config_float( 'BATCH_ACCEPTANCE_MAX_BREACH_RATE', 0.0 )
			
			if total_files <= 0:
				return PerformanceAcceptanceResult( total_files=0, average_seconds=0.0,
					p95_seconds=0.0, sla_breach_rate=0.0,
					average_target_seconds=average_target,
					p95_target_seconds=p95_target,
					max_breach_rate=max_breach_rate,
					meets_average_target=False,
					meets_p95_target=False,
					meets_breach_rate_target=False,
					meets_acceptance=False,
					status='Not Evaluated',
					message='No timed label files were available for performance acceptance.'
				)
			
			meets_average = average_seconds <= average_target
			meets_p95 = p95_seconds <= p95_target
			meets_breach_rate = sla_breach_rate <= max_breach_rate
			meets_acceptance = meets_average and meets_p95 and meets_breach_rate
			status = 'Met' if meets_acceptance else 'Not Met'
			
			if meets_acceptance:
				message = (
						f'Performance acceptance met for {total_files} timed label files. '
						f'Average {average_seconds:.3f}s and p95 {p95_seconds:.3f}s were within '
						f'configured targets.'
				)
			else:
				message = (
						f'Performance acceptance not met for {total_files} timed label files. '
						f'Average {average_seconds:.3f}s target {average_target:.3f}s; '
						f'p95 {p95_seconds:.3f}s target {p95_target:.3f}s; '
						f'breach rate {sla_breach_rate:.4f} target {max_breach_rate:.4f}.'
				)
			
			return PerformanceAcceptanceResult(
				total_files=total_files,
				average_seconds=average_seconds,
				p95_seconds=p95_seconds,
				sla_breach_rate=sla_breach_rate,
				average_target_seconds=average_target,
				p95_target_seconds=p95_target,
				max_breach_rate=max_breach_rate,
				meets_average_target=meets_average,
				meets_p95_target=meets_p95,
				meets_breach_rate_target=meets_breach_rate,
				meets_acceptance=meets_acceptance,
				status=status,
				message=message
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_acceptance_result( self, *args ) -> PerformanceAcceptanceResult'
			Logger( ).write( error )
			return PerformanceAcceptanceResult(
				status='Not Evaluated',
				message='Performance acceptance could not be evaluated.'
			)
	
	def summarize( self,
			results: List[ LabelPerformanceResult ] | None = None ) -> BatchPerformanceSummary:
		"""Summarize per-label performance results at the batch level.

		Purpose:
			Summarize either an explicit list of timing results or the monitor's collected internal
			results. The summary calculates total file count, average seconds, maximum seconds,
			minimum seconds, median seconds, p50, p90, p95, number of results within SLA, number of
			SLA breaches, breach rate, and formal performance acceptance status. Empty result sets
			return a valid zero-valued summary using the configured SLA threshold.

		Parameters:
			results (List[LabelPerformanceResult] | None): Optional results to summarize. When
				``None``, the monitor's collected results are summarized.

		Returns:
			BatchPerformanceSummary: Batch performance summary. If summarization fails, the
			exception is logged and a zero-valued summary fallback is returned.
		"""
		try:
			active_results = results if results is not None else self._results
			
			if not active_results:
				acceptance_result = self.create_acceptance_result(
					total_files=0,
					average_seconds=0.0,
					p95_seconds=0.0,
					sla_breach_rate=0.0
				)
				
				return BatchPerformanceSummary(
					results=[ ],
					total_files=0,
					average_seconds=0.0,
					maximum_seconds=0.0,
					minimum_seconds=0.0,
					median_seconds=0.0,
					p50_seconds=0.0,
					p90_seconds=0.0,
					p95_seconds=0.0,
					within_sla_count=0,
					sla_breach_count=0,
					sla_breach_rate=0.0,
					sla_seconds=self._sla_seconds,
					acceptance_result=acceptance_result
				)
			
			seconds = [
					max( 0.0, float( result.processing_seconds ) )
					for result in active_results
			]
			
			total_files = len( active_results )
			within_sla_count = sum(
				1
				for result in active_results
				if result.within_sla
			)
			
			breach_count = total_files - within_sla_count
			breach_rate = breach_count / total_files if total_files else 0.0
			average_seconds = sum( seconds ) / total_files
			median_seconds = float( statistics.median( seconds ) )
			p50_seconds = calculate_percentile( seconds, 50.0 )
			p90_seconds = calculate_percentile( seconds, 90.0 )
			p95_seconds = calculate_percentile( seconds, 95.0 )
			
			acceptance_result = self.create_acceptance_result(
				total_files=total_files,
				average_seconds=average_seconds,
				p95_seconds=p95_seconds,
				sla_breach_rate=breach_rate
			)
			
			return BatchPerformanceSummary(
				results=active_results,
				total_files=total_files,
				average_seconds=average_seconds,
				maximum_seconds=max( seconds ),
				minimum_seconds=min( seconds ),
				median_seconds=median_seconds,
				p50_seconds=p50_seconds,
				p90_seconds=p90_seconds,
				p95_seconds=p95_seconds,
				within_sla_count=within_sla_count,
				sla_breach_count=breach_count,
				sla_breach_rate=breach_rate,
				sla_seconds=self._sla_seconds,
				acceptance_result=acceptance_result
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'summarize( self, results: List[LabelPerformanceResult] | None = None ) -> BatchPerformanceSummary'
			Logger( ).write( error )
			
			acceptance_result = PerformanceAcceptanceResult(
				status='Not Evaluated',
				message='Performance summary could not be calculated.'
			)
			
			return BatchPerformanceSummary(
				results=[ ],
				total_files=0,
				average_seconds=0.0,
				maximum_seconds=0.0,
				minimum_seconds=0.0,
				median_seconds=0.0,
				p50_seconds=0.0,
				p90_seconds=0.0,
				p95_seconds=0.0,
				within_sla_count=0,
				sla_breach_count=0,
				sla_breach_rate=0.0,
				sla_seconds=self._sla_seconds,
				acceptance_result=acceptance_result
			)
	
	def result_records( self, results: List[ LabelPerformanceResult ] | None = None ) -> List[
		Dict[ str, object ] ]:
		"""Convert performance results into flat records for display or export.

		Purpose:
			Convert either an explicit list of performance results or the monitor's collected
			internal results into flat dictionaries by delegating to each result's ``to_record``
			method. The output is suitable for DataFrame display, CSV export, JSON export, or
			report-writing workflows.

		Parameters:
			results (List[LabelPerformanceResult] | None): Optional results to convert. When
				``None``, the monitor's collected results are converted.

		Returns:
			List[Dict[str, object]]: Flat performance records. If conversion fails, the exception is
			logged and an empty list is returned.
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