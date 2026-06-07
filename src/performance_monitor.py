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

import json
import statistics
import time
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field

import config as cfg
from booger import Error, Logger
from config import throw_if
from src.constants import STATUS_PASS, STATUS_WARNING

# ==========================================================================================
# Performance Utility Functions
# ==========================================================================================

def get_config_float( name: str, default: float ) -> float:
	"""Read a floating-point value from the configuration module.

	Purpose:
		Safely read optional acceptance and SLA configuration values without requiring every
		deployment or test harness to define the newest settings. Missing, empty, or invalid
		values return the supplied default.

	Args:
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

	Args:
		values (List[float]): Numeric values to summarize.
		percentile (float): Percentile value from ``0`` through ``100``.

	Returns:
		float: Calculated percentile value. Empty input returns ``0.0``.
	"""
	try:
		if not values:
			return 0.0
		
		clean_values = sorted(
			float( value )
			for value in values
		)
		
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

	Purpose:
		Capture the timing outcome for a single label file. The model records the file name,
		elapsed processing time, configured SLA threshold, whether the label completed within
		that threshold, reviewer-facing SLA status, reviewer-facing message, start timestamp,
		completion timestamp, and calculated breach seconds.

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
			``0.0`` so the value is safe for dashboard display, CSV export, and aggregate
			analysis.

		Returns:
			float: Non-negative number of seconds above the threshold.
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
			construction, CSV export, JSON export, or reviewer-facing performance reports.
			Numeric values are rounded to three decimal places to preserve useful timing precision
			without overloading the UI with excessive decimals.

		Returns:
			Dict[str, object]: Flat performance result record. If conversion fails, a conservative
			fallback record is returned.
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

	Purpose:
		Store the calculated acceptance outcome for a batch timing summary. The model compares
		average processing time, p95 processing time, and SLA breach rate against configured
		acceptance thresholds. This separates measured performance from acceptance judgment so
		reports can show both raw values and pass/fail determination.

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
		"""Convert the performance acceptance result into a flat record.

		Purpose:
			Convert formal performance acceptance fields into a dictionary suitable for DataFrame
			display, CSV export, JSON export, Markdown reports, and acceptance evidence packages.

		Returns:
			Dict[str, object]: Flat performance acceptance record.
		"""
		try:
			return {
					'Performance Acceptance Status': self.status,
					'Performance Acceptance Met': self.meets_acceptance,
					'Timed Files': self.total_files,
					'Acceptance Average Seconds': round( self.average_seconds, 3 ),
					'Acceptance Average Target Seconds': round( self.average_target_seconds, 3 ),
					'Acceptance P95 Seconds': round( self.p95_seconds, 3 ),
					'Acceptance P95 Target Seconds': round( self.p95_target_seconds, 3 ),
					'Acceptance SLA Breach Rate': round( self.sla_breach_rate, 4 ),
					'Acceptance Max Breach Rate': round( self.max_breach_rate, 4 ),
					'Meets Average Target': self.meets_average_target,
					'Meets P95 Target': self.meets_p95_target,
					'Meets Breach Rate Target': self.meets_breach_rate_target,
					'Acceptance Message': self.message
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
					'Timed Files': 0,
					'Acceptance Average Seconds': 0.0,
					'Acceptance Average Target Seconds': self.average_target_seconds,
					'Acceptance P95 Seconds': 0.0,
					'Acceptance P95 Target Seconds': self.p95_target_seconds,
					'Acceptance SLA Breach Rate': 0.0,
					'Acceptance Max Breach Rate': self.max_breach_rate,
					'Meets Average Target': False,
					'Meets P95 Target': False,
					'Meets Breach Rate Target': False,
					'Acceptance Message': 'Performance acceptance record could not be rendered.'
			}

class PerformanceEvidence( BaseModel ):
	"""Represent exportable performance evidence for acceptance review.

	Purpose:
		Provide a compact evidence object that can be generated from a batch performance summary.
		The object reports whether the under-five-second SLA was tested, whether all timed labels
		were within SLA, whether the average target was met, whether the p95 target was met,
		whether the breach-rate target was met, and whether the evidence supports stakeholder
		acceptance.

	Attributes:
		sla_tested (bool): Indicates whether timed label evidence exists.
		under_five_seconds_per_label (bool): Indicates whether all timed labels met the SLA.
		meets_average_target (bool): Indicates whether the average target was met.
		meets_p95_target (bool): Indicates whether the p95 target was met.
		meets_zero_breach_target (bool): Indicates whether the configured breach-rate target was
			met.
		meets_acceptance (bool): Indicates whether overall performance acceptance passed.
		message (str): Reviewer-facing evidence message.
	"""
	
	sla_tested: bool = Field( default=False )
	under_five_seconds_per_label: bool = Field( default=False )
	meets_average_target: bool = Field( default=False )
	meets_p95_target: bool = Field( default=False )
	meets_zero_breach_target: bool = Field( default=False )
	meets_acceptance: bool = Field( default=False )
	message: str = Field( default='' )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert performance evidence into a flat record.

		Purpose:
			Create a compact dictionary suitable for acceptance summary tables, CSV export, JSON
			output, and Markdown reporting.

		Returns:
			Dict[str, object]: Flat performance evidence record.
		"""
		try:
			return {
					'SLA Tested': self.sla_tested,
					'Under Five Seconds Per Label': self.under_five_seconds_per_label,
					'Meets Average Target': self.meets_average_target,
					'Meets P95 Target': self.meets_p95_target,
					'Meets Zero Breach Target': self.meets_zero_breach_target,
					'Meets Performance Acceptance': self.meets_acceptance,
					'Performance Evidence Message': self.message
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'SLA Tested': False,
					'Under Five Seconds Per Label': False,
					'Meets Average Target': False,
					'Meets P95 Target': False,
					'Meets Zero Breach Target': False,
					'Meets Performance Acceptance': False,
					'Performance Evidence Message': 'Performance evidence could not be rendered.'
			}

class BatchPerformanceSummary( BaseModel ):
	"""Represent batch-level performance statistics.

	Purpose:
		Aggregate one or more per-label timing results into batch-level performance metrics. The
		summary stores raw per-label results, total file count, average seconds, maximum seconds,
		minimum seconds, median, p50, p90, p95, within-SLA count, SLA breach count, breach rate,
		configured SLA threshold, and formal performance acceptance result.

	Attributes:
		results (List[LabelPerformanceResult]): Per-label timing results included in the summary.
		total_files (int): Number of timing results summarized.
		average_seconds (float): Average processing seconds.
		maximum_seconds (float): Maximum processing seconds.
		minimum_seconds (float): Minimum processing seconds.
		median_seconds (float): Median processing seconds.
		p50_seconds (float): Fiftieth percentile processing seconds.
		p90_seconds (float): Ninetieth percentile processing seconds.
		p95_seconds (float): Ninety-fifth percentile processing seconds.
		within_sla_count (int): Count of labels processed within SLA.
		sla_breach_count (int): Count of labels exceeding SLA.
		sla_breach_rate (float): Fraction of labels exceeding SLA.
		sla_seconds (float): SLA threshold used for the summary.
		acceptance_result (PerformanceAcceptanceResult): Formal acceptance result.
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
		default_factory=PerformanceAcceptanceResult
	)
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert the batch performance summary into a flat record.

		Purpose:
			Convert summary metrics and formal acceptance fields into a dictionary suitable for
			Streamlit metrics, DataFrame display, CSV export, JSON export, Markdown reports, and
			stakeholder acceptance evidence.

		Returns:
			Dict[str, object]: Flat batch performance summary record.
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
	
	def to_dataframe( self ) -> pd.DataFrame:
		"""Convert the batch performance summary into a one-row DataFrame.

		Purpose:
			Create a DataFrame containing the batch-level performance summary. This is useful for
			Streamlit display, CSV export, and acceptance evidence packages.

		Returns:
			pd.DataFrame: One-row batch performance summary DataFrame.
		"""
		try:
			return pd.DataFrame( [ self.to_record( ) ] )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_dataframe( self ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def to_acceptance_record( self ) -> Dict[ str, object ]:
		"""Convert the summary into compact acceptance evidence.

		Purpose:
			Build a compact acceptance-focused dictionary from the batch performance summary.
			This method is intended for acceptance dashboards and evidence packages where the
			raw performance detail table is not required.

		Returns:
			Dict[str, object]: Compact performance acceptance evidence record.
		"""
		try:
			evidence = self.to_performance_evidence( )
			record = {
					'Total Files': self.total_files,
					'Average Seconds': round( self.average_seconds, 3 ),
					'P95 Seconds': round( self.p95_seconds, 3 ),
					'Maximum Seconds': round( self.maximum_seconds, 3 ),
					'SLA Seconds': round( self.sla_seconds, 3 ),
					'SLA Breach Count': self.sla_breach_count,
					'SLA Breach Rate': round( self.sla_breach_rate, 4 )
			}
			record.update( evidence.to_record( ) )
			return record
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_acceptance_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Total Files': 0,
					'SLA Tested': False,
					'Under Five Seconds Per Label': False,
					'Meets Performance Acceptance': False,
					'Performance Evidence Message': 'Performance acceptance record could not be rendered.'
			}
	
	def to_performance_evidence( self ) -> PerformanceEvidence:
		"""Create a compact performance evidence object.

		Purpose:
			Translate batch-level metrics and the formal acceptance result into an evidence model
			that directly answers the stakeholder performance requirement.

		Returns:
			PerformanceEvidence: Compact performance evidence object.
		"""
		try:
			sla_tested = self.total_files > 0
			under_five_seconds = sla_tested and self.sla_breach_count == 0
			meets_zero_breach = bool( self.acceptance_result.meets_breach_rate_target )
			meets_acceptance = bool( self.acceptance_result.meets_acceptance )
			
			if not sla_tested:
				message = 'No timed label files were available for performance evidence.'
			elif meets_acceptance:
				message = (
						f'Performance evidence passed for {self.total_files} timed labels. '
						f'Average {self.average_seconds:.3f}s and p95 {self.p95_seconds:.3f}s '
						f'were within configured targets.'
				)
			else:
				message = (
						f'Performance evidence did not pass for {self.total_files} timed labels. '
						f'Average {self.average_seconds:.3f}s, p95 {self.p95_seconds:.3f}s, '
						f'and breach rate {self.sla_breach_rate:.4f} should be reviewed.'
				)
			
			return PerformanceEvidence(
				sla_tested=sla_tested,
				under_five_seconds_per_label=under_five_seconds,
				meets_average_target=bool( self.acceptance_result.meets_average_target ),
				meets_p95_target=bool( self.acceptance_result.meets_p95_target ),
				meets_zero_breach_target=meets_zero_breach,
				meets_acceptance=meets_acceptance,
				message=message
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_performance_evidence( self ) -> PerformanceEvidence'
			Logger( ).write( error )
			return PerformanceEvidence(
				message='Performance evidence could not be created.'
			)
	
	def to_json( self ) -> str:
		"""Serialize the batch performance summary as formatted JSON.

		Purpose:
			Create a JSON payload containing summary metrics, acceptance status, and per-label
			performance results for evidence packages and test harness outputs.

		Returns:
			str: Formatted JSON string. If serialization fails, returns an empty JSON object.
		"""
		try:
			payload = {
					'summary': self.to_record( ),
					'acceptance_evidence': self.to_acceptance_record( ),
					'results': [
							result.to_record( )
							for result in self.results
					]
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
		"""Render the batch performance summary as Markdown.

		Purpose:
			Create a stakeholder-readable performance report containing summary metrics,
			acceptance status, and the formal acceptance message.

		Returns:
			str: Markdown performance report.
		"""
		try:
			lines = [
					'# Fiddy Performance Summary',
					'',
					f'Total Files: {self.total_files}',
					f'Average Seconds: {self.average_seconds:.3f}',
					f'Median Seconds: {self.median_seconds:.3f}',
					f'P95 Seconds: {self.p95_seconds:.3f}',
					f'Maximum Seconds: {self.maximum_seconds:.3f}',
					f'SLA Seconds: {self.sla_seconds:.3f}',
					f'SLA Breach Count: {self.sla_breach_count}',
					f'SLA Breach Rate: {self.sla_breach_rate:.4f}',
					'',
					'## Acceptance',
					'',
					f'Status: {self.acceptance_result.status}',
					f'Meets Acceptance: {self.acceptance_result.meets_acceptance}',
					f'Message: {self.acceptance_result.message}',
					''
			]
			return '\n'.join( lines )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_markdown( self ) -> str'
			Logger( ).write( error )
			return '# Fiddy Performance Summary\n\nPerformance summary could not be rendered.'

class PerformanceMonitor( ):
	"""Track per-label processing time and evaluate SLA performance.

	Purpose:
		Provide start/stop timing for label processing workflows. The monitor records
		high-resolution start times with ``time.perf_counter`` and human-readable start
		timestamps with ``datetime.now``. When processing stops, it creates a
		``LabelPerformanceResult`` that records elapsed seconds, SLA status, timestamps, breach
		seconds, and a reviewer-facing performance message.

		The monitor stores all generated timing results for later summarization. Batch processors
		can either summarize the monitor's internal results or provide an explicit list of
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
		"""Initialize the performance monitor.

		Purpose:
			Store the per-label SLA threshold and initialize empty timing and result collections.
			When no SLA is supplied by the caller, ``cfg.LABEL_PROCESSING_SLA_SECONDS`` is used
			with a fallback of five seconds.

		Args:
			sla_seconds (float | None): Optional per-label SLA threshold in seconds.

		Returns:
			None.
		"""
		try:
			if sla_seconds is None:
				self._sla_seconds = get_config_float( 'LABEL_PROCESSING_SLA_SECONDS', 5.0 )
			else:
				self._sla_seconds = float( sla_seconds )
			
			if self._sla_seconds <= 0:
				self._sla_seconds = 5.0
		except Exception:
			self._sla_seconds = 5.0
		
		self._start_times = { }
		self._start_datetimes = { }
		self._results = [ ]
	
	@property
	def sla_seconds( self ) -> float:
		"""Return the configured per-label SLA threshold.

		Purpose:
			Expose the SLA threshold used by start/stop timing and summary acceptance
			calculations.

		Returns:
			float: SLA threshold in seconds.
		"""
		return self._sla_seconds
	
	@property
	def results( self ) -> List[ LabelPerformanceResult ]:
		"""Return collected per-label performance results.

		Purpose:
			Expose timing results collected by this monitor instance.

		Returns:
			List[LabelPerformanceResult]: Collected per-label performance results.
		"""
		return self._results
	
	def start( self, file_name: str ) -> None:
		"""Start timing one label file.

		Purpose:
			Record both a high-resolution start time and a human-readable start timestamp for the
			supplied file name. Repeated calls for the same file name overwrite the active start
			time for that key.

		Args:
			file_name (str): Label file name or identifier to time.

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
		"""Stop timing one label file and create a performance result.

		Purpose:
			Read the active start time for the supplied file name, calculate elapsed processing
			seconds, determine whether the label met the configured SLA threshold, create a
			``LabelPerformanceResult``, store the result, and remove the active start time. If no
			start time exists, a zero-second reviewer-safe warning result is returned.

		Args:
			file_name (str): Label file name or identifier to stop timing.

		Returns:
			LabelPerformanceResult: Per-label performance result.
		"""
		try:
			throw_if( 'file_name', file_name )
			completed_on = datetime.now( )
			started_on = self._start_datetimes.get( file_name, completed_on )
			started = self._start_times.get( file_name, None )
			
			if started is None:
				result = LabelPerformanceResult(
					file_name=file_name,
					processing_seconds=0.0,
					sla_seconds=self._sla_seconds,
					within_sla=False,
					status=STATUS_WARNING,
					message='Performance timer was not started before stop was called.',
					started_on=started_on,
					completed_on=completed_on
				)
				self._results.append( result )
				return result
			
			processing_seconds = max( 0.0, time.perf_counter( ) - started )
			within_sla = processing_seconds <= self._sla_seconds
			status = STATUS_PASS if within_sla else STATUS_WARNING
			
			if within_sla:
				message = (
						f'Processed in {processing_seconds:.3f} seconds, within the '
						f'{self._sla_seconds:.3f}-second SLA.'
				)
			else:
				message = (
						f'Processed in {processing_seconds:.3f} seconds, exceeding the '
						f'{self._sla_seconds:.3f}-second SLA.'
				)
			
			result = LabelPerformanceResult(
				file_name=file_name,
				processing_seconds=processing_seconds,
				sla_seconds=self._sla_seconds,
				within_sla=within_sla,
				status=status,
				message=message,
				started_on=started_on,
				completed_on=completed_on
			)
			self._results.append( result )
			self._start_times.pop( file_name, None )
			self._start_datetimes.pop( file_name, None )
			
			return result
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'stop( self, file_name: str ) -> LabelPerformanceResult'
			Logger( ).write( error )
			return LabelPerformanceResult(
				file_name=file_name,
				processing_seconds=0.0,
				sla_seconds=self._sla_seconds,
				within_sla=False,
				status=STATUS_WARNING,
				message='Performance timing failed.',
				started_on=datetime.now( ),
				completed_on=datetime.now( )
			)
	
	def create_acceptance_result( self, total_files: int, average_seconds: float,
			p95_seconds: float, sla_breach_rate: float ) -> PerformanceAcceptanceResult:
		"""Create formal performance acceptance evidence.

		Purpose:
			Compare average seconds, p95 seconds, and SLA breach rate against configured
			acceptance thresholds. The result marks performance as ``Met`` only when all evaluated
			criteria pass. Empty timing sets are marked ``Not Evaluated``.

		Args:
			total_files (int): Number of timed files.
			average_seconds (float): Average processing seconds.
			p95_seconds (float): P95 processing seconds.
			sla_breach_rate (float): Fraction of labels exceeding the SLA threshold.

		Returns:
			PerformanceAcceptanceResult: Formal performance acceptance result.
		"""
		try:
			average_target = get_config_float(
				'BATCH_ACCEPTANCE_MAX_AVERAGE_SECONDS',
				self._sla_seconds
			)
			p95_target = get_config_float(
				'BATCH_ACCEPTANCE_MAX_P95_SECONDS',
				self._sla_seconds
			)
			max_breach_rate = get_config_float( 'BATCH_ACCEPTANCE_MAX_BREACH_RATE', 0.0 )
			
			if total_files <= 0:
				return PerformanceAcceptanceResult(
					total_files=0,
					average_seconds=0.0,
					p95_seconds=0.0,
					sla_breach_rate=0.0,
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
			results: Optional[ List[ LabelPerformanceResult ] ] = None ) -> BatchPerformanceSummary:
		"""Summarize per-label performance results at the batch level.

		Purpose:
			Summarize either an explicit list of timing results or the monitor's collected
			internal results. The summary calculates total file count, average seconds, maximum
			seconds, minimum seconds, median seconds, p50, p90, p95, number of results within
			SLA, number of SLA breaches, breach rate, and formal performance acceptance status.
			Empty result sets return a valid zero-valued summary using the configured SLA
			threshold.

		Args:
			results (Optional[List[LabelPerformanceResult]]): Optional results to summarize.
				When ``None``, the monitor's collected results are summarized.

		Returns:
			BatchPerformanceSummary: Batch performance summary. If summarization fails, a
			zero-valued summary fallback is returned.
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
			error.method = 'summarize( self, *args ) -> BatchPerformanceSummary'
			Logger( ).write( error )
			acceptance_result = PerformanceAcceptanceResult(
				status='Not Evaluated',
				message='Performance summary could not be created.'
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
	
	def result_records( self,
			results: Optional[ List[ LabelPerformanceResult ] ] = None ) -> List[
		Dict[ str, object ] ]:
		"""Convert per-label performance results into flat records.

		Purpose:
			Convert either explicitly supplied timing results or internally collected timing
			results into dictionaries suitable for DataFrame construction, CSV export, and
			reporting.

		Args:
			results (Optional[List[LabelPerformanceResult]]): Optional results to convert.

		Returns:
			List[Dict[str, object]]: Per-label performance records.
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
	
	def to_dataframe( self,
			results: Optional[ List[ LabelPerformanceResult ] ] = None ) -> pd.DataFrame:
		"""Convert per-label performance results into a DataFrame.

		Purpose:
			Build a DataFrame from per-label timing records for display, CSV export, and
			stakeholder evidence.

		Args:
			results (Optional[List[LabelPerformanceResult]]): Optional results to convert.

		Returns:
			pd.DataFrame: Per-label performance DataFrame.
		"""
		try:
			return pd.DataFrame( self.result_records( results ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_dataframe( self, *args ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def summary_dataframe( self,
			results: Optional[ List[ LabelPerformanceResult ] ] = None ) -> pd.DataFrame:
		"""Convert summary performance metrics into a one-row DataFrame.

		Purpose:
			Summarize timing results and return the batch-level performance summary as a one-row
			DataFrame.

		Args:
			results (Optional[List[LabelPerformanceResult]]): Optional results to summarize.

		Returns:
			pd.DataFrame: One-row performance summary DataFrame.
		"""
		try:
			return self.summarize( results ).to_dataframe( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'summary_dataframe( self, *args ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def acceptance_record( self,
			results: Optional[ List[ LabelPerformanceResult ] ] = None ) -> Dict[ str, object ]:
		"""Return compact performance acceptance evidence.

		Purpose:
			Summarize timing results and return compact acceptance evidence for dashboards,
			exports, and stakeholder acceptance checks.

		Args:
			results (Optional[List[LabelPerformanceResult]]): Optional results to summarize.

		Returns:
			Dict[str, object]: Compact performance acceptance record.
		"""
		try:
			return self.summarize( results ).to_acceptance_record( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'acceptance_record( self, *args ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'SLA Tested': False,
					'Under Five Seconds Per Label': False,
					'Meets Performance Acceptance': False,
					'Performance Evidence Message': 'Performance acceptance record could not be created.'
			}