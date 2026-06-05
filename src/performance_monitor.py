'''
    ******************************************************************************************
      Assembly:                Veritas
      Filename:                performance_monitor.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="performance_monitor.py" company="Terry D. Eppler">

         Veritas: AI-Powered Alcohol Label Verification App

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
        performance_monitor.py
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field

import config as cfg
from config import throw_if
from src.constants import STATUS_PASS, STATUS_WARNING

# ==========================================================================================
# Performance Models
# ==========================================================================================

class LabelPerformanceResult( BaseModel ):
	"""
	Purpose:
	--------
	Represent timing and SLA status for one processed label.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
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
		"""
		Purpose:
		--------
		Convert one performance result into a flat display/export record.

		Parameters:
		-----------
		None

		Returns:
		--------
		Dict[str, object]: Flat performance result record.
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
		except Exception:
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
	"""
	Purpose:
	--------
	Represent batch-level timing and SLA performance summary statistics.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
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
		"""
		Purpose:
		--------
		Convert batch performance summary into a flat display/export record.

		Parameters:
		-----------
		None

		Returns:
		--------
		Dict[str, object]: Flat batch performance summary record.
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
		except Exception:
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
	"""
	Purpose:
	--------
	Track per-label processing time and evaluate the 5-second usability target.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
	"""
	
	_sla_seconds: float
	_start_times: Dict[ str, float ]
	_start_datetimes: Dict[ str, datetime ]
	_results: List[ LabelPerformanceResult ]
	
	def __init__( self, sla_seconds: float | None = None ) -> None:
		"""
		Purpose:
		--------
		Initialize the monitor with a default or configured SLA threshold.

		Parameters:
		-----------
		sla_seconds (float | None): Optional SLA threshold in seconds.

		Returns:
		--------
		None
		"""
		default_sla = getattr( cfg, 'LABEL_PROCESSING_SLA_SECONDS', 5.0 )
		self._sla_seconds = float( sla_seconds if sla_seconds is not None else default_sla )
		self._start_times = { }
		self._start_datetimes = { }
		self._results = [ ]
	
	@property
	def sla_seconds( self ) -> float:
		"""
		Purpose:
		--------
		Return the configured per-label SLA threshold in seconds.

		Parameters:
		-----------
		None

		Returns:
		--------
		float: SLA threshold in seconds.
		"""
		return self._sla_seconds
	
	@property
	def results( self ) -> List[ LabelPerformanceResult ]:
		"""
		Purpose:
		--------
		Return all collected per-label performance results.

		Parameters:
		-----------
		None

		Returns:
		--------
		List[LabelPerformanceResult]: Collected timing results.
		"""
		return self._results
	
	def start( self, file_name: str ) -> None:
		"""
		Purpose:
		--------
		Start timing one label file.

		Parameters:
		-----------
		file_name (str): Label file name being processed.

		Returns:
		--------
		None
		"""
		try:
			throw_if( 'file_name', file_name )
			
			self._start_times[ file_name ] = time.perf_counter( )
			self._start_datetimes[ file_name ] = datetime.now( )
		except Exception:
			return None
	
	def stop( self, file_name: str ) -> LabelPerformanceResult:
		"""
		Purpose:
		--------
		Stop timing one label file and create an SLA performance result.

		Parameters:
		-----------
		file_name (str): Label file name being processed.

		Returns:
		--------
		LabelPerformanceResult: Per-label performance result.
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
		except Exception:
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
		"""
		Purpose:
		--------
		Create a per-label performance result from elapsed processing time.

		Parameters:
		-----------
		file_name (str): Label file name.
		processing_seconds (float): Elapsed processing time in seconds.
		started_on (datetime): Processing start timestamp.
		completed_on (datetime): Processing completion timestamp.

		Returns:
		--------
		LabelPerformanceResult: Per-label SLA result.
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
			
			return LabelPerformanceResult(
				file_name=file_name,
				processing_seconds=seconds,
				sla_seconds=self._sla_seconds,
				within_sla=within_sla,
				status=status,
				message=message,
				started_on=started_on,
				completed_on=completed_on
			)
		except Exception:
			return LabelPerformanceResult(
				file_name=file_name,
				processing_seconds=0.0,
				sla_seconds=self._sla_seconds,
				within_sla=False,
				status=STATUS_WARNING,
				message='Performance result creation failed.'
			)
	
	def summarize( self,
			results: List[ LabelPerformanceResult ] | None = None ) -> BatchPerformanceSummary:
		"""
		Purpose:
		--------
		Summarize per-label performance results at the batch level.

		Parameters:
		-----------
		results (List[LabelPerformanceResult] | None): Optional results to summarize.

		Returns:
		--------
		BatchPerformanceSummary: Batch performance summary.
		"""
		try:
			active_results = results if results is not None else self._results
			
			if not active_results:
				return BatchPerformanceSummary(
					results=[ ],
					total_files=0,
					average_seconds=0.0,
					maximum_seconds=0.0,
					minimum_seconds=0.0,
					within_sla_count=0,
					sla_breach_count=0,
					sla_seconds=self._sla_seconds
				)
			
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
			
			return BatchPerformanceSummary(
				results=active_results,
				total_files=len( active_results ),
				average_seconds=sum( seconds ) / len( seconds ),
				maximum_seconds=max( seconds ),
				minimum_seconds=min( seconds ),
				within_sla_count=within_sla_count,
				sla_breach_count=breach_count,
				sla_seconds=self._sla_seconds
			)
		except Exception:
			return BatchPerformanceSummary(
				results=[ ],
				total_files=0,
				average_seconds=0.0,
				maximum_seconds=0.0,
				minimum_seconds=0.0,
				within_sla_count=0,
				sla_breach_count=0,
				sla_seconds=self._sla_seconds
			)
	
	def result_records( self, results: List[ LabelPerformanceResult ] | None = None ) -> List[ Dict[ str, object ] ]:
		"""
		Purpose:
		--------
		Convert performance results into flat records for display or export.

		Parameters:
		-----------
		results (List[LabelPerformanceResult] | None): Optional results to convert.

		Returns:
		--------
		List[Dict[str, object]]: Flat performance records.
		"""
		try:
			active_results = results if results is not None else self._results
			
			return [
					result.to_record( )
					for result in active_results
			]
		except Exception:
			return [ ]
