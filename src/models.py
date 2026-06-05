'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                models.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="models.py" company="Terry D. Eppler">

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
        models.py
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from config import REPORT_DATE_FORMAT, throw_if
from src.constants import (
	BEVERAGE_TYPE_DISTILLED_SPIRITS,
	FIELD_LABEL_TEXT,
	FIELD_OVERALL_STATUS,
	STATUS_FAIL,
	STATUS_PASS,
	STATUS_REVIEW,
	STATUS_WARNING,
	SEVERITY_INFO
)

class LabelApplication( BaseModel ):
	"""
	
		Purpose:
		--------
		Represent the expected application data entered by the compliance reviewer.
	
		Parameters:
		-----------
		None
	
		Returns:
		--------
		None
		
	"""
	brand_name: str = Field( default='', description='Expected brand name from the application.' )
	class_type: str = Field( default='', description='Expected class or type designation.' )
	beverage_type: str = Field( default=BEVERAGE_TYPE_DISTILLED_SPIRITS )
	alcohol_content: Optional[ float ] = Field( default=None, description='Expected ABV value.' )
	proof: Optional[ float ] = Field( default=None, description='Expected proof value.' )
	net_contents: str = Field( default='', description='Expected net contents value.' )
	producer_bottler: str = Field( default='', description='Expected producer or bottler.' )
	imported: bool = Field( default=False, description='Indicates whether the product is imported.' )
	importer: str = Field( default='', description='Expected importer name, when applicable.' )
	country_of_origin: str = Field( default='', description='Expected country of origin.' )
	government_warning: str = Field( default='',
		description='Expected government warning statement.' )
	cola_id: str = Field( default='',
		description='Optional COLA identifier or application reference.' )
	notes: str = Field( default='', description='Optional reviewer notes.' )
	
	def required_field_map( self ) -> Dict[ str, Any ]:
		"""
		
			Purpose:
			--------
			Return expected values keyed by user-facing label field names.
	
			Parameters:
			-----------
			None
	
			Returns:
			--------
			Dict[str, Any]: Dictionary of expected application field values.
			
		"""
		try:
			fields = {
					'Brand Name': self.brand_name,
					'Class / Type': self.class_type,
					'Alcohol Content': self.alcohol_content,
					'Proof': self.proof,
					'Net Contents': self.net_contents,
					'Producer / Bottler': self.producer_bottler,
					'Country of Origin': self.country_of_origin,
					'Government Warning': self.government_warning
			}
			
			if self.imported:
				fields[ 'Importer' ] = self.importer
			
			return fields
		except Exception:
			return { }

class ExtractedLabel( BaseModel ):
	"""
	
		Purpose:
		--------
		Represent OCR and structured extraction results for one uploaded label file.
	
		Parameters:
		-----------
		None
	
		Returns:
		--------
		None
	
	"""
	file_name: str = Field( default='', description='Uploaded file name.' )
	file_type: str = Field( default='', description='Detected file extension or upload type.' )
	raw_text: str = Field( default='', description='Raw OCR text extracted from the label.' )
	normalized_text: str = Field( default='', description='Normalized OCR text for matching.' )
	brand_name: str = Field( default='', description='Extracted brand name.' )
	class_type: str = Field( default='', description='Extracted class/type designation.' )
	alcohol_content: Optional[ float ] = Field( default=None, description='Extracted ABV value.' )
	net_contents: str = Field( default='', description='Extracted net contents.' )
	producer_bottler: str = Field( default='', description='Extracted producer/bottler text.' )
	country_of_origin: str = Field( default='', description='Extracted country of origin.' )
	government_warning: str = Field( default='', description='Extracted government warning text.' )
	ocr_engine: str = Field( default='', description='OCR engine used for extraction.' )
	ocr_seconds: float = Field( default=0.0, description='Elapsed OCR processing time.' )
	image_quality_notes: List[ str ] = Field( default_factory=list )
	created_on: datetime = Field( default_factory=datetime.now )
	
	def has_text( self ) -> bool:
		"""
		
			Purpose:
			--------
			Determine whether OCR produced readable label text.
	
			Parameters:
			-----------
			None
	
			Returns:
			--------
			bool: True when extracted text is present; otherwise, False.
			
		"""
		try:
			return bool( self.raw_text and self.raw_text.strip( ) )
		except Exception:
			return False
	
	def to_extracted_field_map( self ) -> Dict[ str, Any ]:
		"""
		
			Purpose:
			--------
			Return structured extracted label values keyed by reviewer-facing field names.
	
			Parameters:
			-----------
			None
	
			Returns:
			--------
			Dict[str, Any]: Structured extracted label field values.
			
		"""
		try:
			return {
					'Brand Name': self.brand_name,
					'Class / Type': self.class_type,
					'Alcohol Content': self.alcohol_content,
					'ABV': self.alcohol_content,
					'Net Contents': self.net_contents,
					'Producer / Bottler': self.producer_bottler,
					'Country of Origin': self.country_of_origin,
					'Government Warning': self.government_warning
			}
		except Exception:
			return { }

# ==========================================================================================
# Rule Result Model
# ==========================================================================================

class LabelCheckResult( BaseModel ):
	"""
	Purpose:
	--------
	Represent the result of one deterministic label verification rule.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
	"""
	
	rule_id: str = Field( default='', description='Machine-readable rule identifier.' )
	field_name: str = Field( default='', description='User-facing field name.' )
	status: str = Field( default=STATUS_REVIEW,
		description='Pass, Warning, Fail, or Needs Review.' )
	severity: str = Field( default=SEVERITY_INFO, description='Relative issue severity.' )
	expected: str = Field( default='', description='Expected value from application data.' )
	observed: str = Field( default='', description='Observed value from label text.' )
	confidence: float = Field( default=0.0, description='Rule confidence from 0.0 to 100.0.' )
	evidence: str = Field( default='', description='Relevant extracted label text span.' )
	message: str = Field( default='', description='Reviewer-facing explanation.' )
	requires_human_review: bool = Field( default=False )
	created_on: datetime = Field( default_factory=datetime.now )
	
	def is_pass( self ) -> bool:
		"""
		Purpose:
		--------
		Determine whether the rule result is a passing result.

		Parameters:
		-----------
		None

		Returns:
		--------
		bool: True when the status is Pass; otherwise, False.
		"""
		try:
			return self.status == STATUS_PASS
		except Exception:
			return False
	
	def is_warning( self ) -> bool:
		"""
		Purpose:
		--------
		Determine whether the rule result is a warning result.

		Parameters:
		-----------
		None

		Returns:
		--------
		bool: True when the status is Warning; otherwise, False.
		"""
		try:
			return self.status == STATUS_WARNING
		except Exception:
			return False
	
	def is_failure( self ) -> bool:
		"""
		Purpose:
		--------
		Determine whether the rule result is a failing result.

		Parameters:
		-----------
		None

		Returns:
		--------
		bool: True when the status is Fail; otherwise, False.
		"""
		try:
			return self.status == STATUS_FAIL
		except Exception:
			return False
	
	def is_review( self ) -> bool:
		"""
		Purpose:
		--------
		Determine whether the rule result requires human review.

		Parameters:
		-----------
		None

		Returns:
		--------
		bool: True when human review is required; otherwise, False.
		"""
		try:
			return self.status == STATUS_REVIEW or self.requires_human_review
		except Exception:
			return False
	
	def to_record( self, file_name: str ) -> Dict[ str, Any ]:
		"""
		Purpose:
		--------
		Convert the rule result into a flat dictionary suitable for DataFrame display.

		Parameters:
		-----------
		file_name (str): Name of the uploaded file associated with the rule result.

		Returns:
		--------
		Dict[str, Any]: Flat dictionary containing display-ready result fields.
		"""
		try:
			throw_if( 'file_name', file_name )
			
			return {
					'File Name': file_name,
					'Field Name': self.field_name,
					'Rule ID': self.rule_id,
					'Status': self.status,
					'Severity': self.severity,
					'Expected': self.expected,
					'Observed': self.observed,
					'Confidence': round( self.confidence, 2 ),
					'Evidence': self.evidence,
					'Message': self.message
			}
		except Exception:
			return {
					'File Name': file_name,
					'Field Name': self.field_name,
					'Rule ID': self.rule_id,
					'Status': STATUS_REVIEW,
					'Severity': self.severity,
					'Expected': self.expected,
					'Observed': self.observed,
					'Confidence': 0.0,
					'Evidence': self.evidence,
					'Message': 'Unable to convert rule result to a flat record.'
			}

# ==========================================================================================
# Verification Report Model
# ==========================================================================================

class LabelVerificationReport( BaseModel ):
	"""
	Purpose:
	--------
	Represent the complete verification report for one uploaded alcohol label.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
	"""
	
	file_name: str = Field( default='', description='Uploaded file name.' )
	application: LabelApplication = Field( default_factory=LabelApplication )
	extracted_label: ExtractedLabel = Field( default_factory=ExtractedLabel )
	results: List[ LabelCheckResult ] = Field( default_factory=list )
	overall_status: str = Field( default=STATUS_REVIEW )
	processing_seconds: float = Field( default=0.0 )
	reviewer_disclaimer: str = Field(
		default=( 'AI-assisted preliminary review only. Final regulatory determinations remain '
				'with authorized compliance personnel.' ) )
	created_on: datetime = Field( default_factory=datetime.now )
	
	def determine_overall_status( self ) -> str:
		"""
		
			Purpose:
			--------
			Determine the overall report status from individual rule results.
			
			Parameters:
			-----------
			None
			
			Returns:
			--------
			str: Overall status value.
			
		"""
		try:
			if not self.results:
				self.overall_status = STATUS_REVIEW
			elif any( result.is_failure( ) for result in self.results ):
				self.overall_status = STATUS_FAIL
			elif any( result.is_review( ) for result in self.results ):
				self.overall_status = STATUS_REVIEW
			elif any( result.is_warning( ) for result in self.results ):
				self.overall_status = STATUS_WARNING
			else:
				self.overall_status = STATUS_PASS
			
			return self.overall_status
		except Exception:
			self.overall_status = STATUS_REVIEW
			return self.overall_status
	
	def has_failures( self ) -> bool:
		"""
		Purpose:
		--------
		Determine whether the report contains any failing rule results.

		Parameters:
		-----------
		None

		Returns:
		--------
		bool: True when one or more failures exist; otherwise, False.
		"""
		try:
			return any( result.is_failure( ) for result in self.results )
		except Exception:
			return False
	
	def has_reviews( self ) -> bool:
		"""
		Purpose:
		--------
		Determine whether the report contains any human-review rule results.

		Parameters:
		-----------
		None

		Returns:
		--------
		bool: True when one or more human-review items exist; otherwise, False.
		"""
		try:
			return any( result.is_review( ) for result in self.results )
		except Exception:
			return False
	
	def has_warnings( self ) -> bool:
		"""
		Purpose:
		--------
		Determine whether the report contains any warning rule results.

		Parameters:
		-----------
		None

		Returns:
		--------
		bool: True when one or more warning items exist; otherwise, False.
		"""
		try:
			return any( result.is_warning( ) for result in self.results )
		except Exception:
			return False
	
	def to_records( self ) -> List[ Dict[ str, Any ] ]:
		"""
		Purpose:
		--------
		Convert all rule results into flat dictionaries suitable for DataFrame display.

		Parameters:
		-----------
		None

		Returns:
		--------
		List[Dict[str, Any]]: Flat verification result records.
		"""
		try:
			return [
					result.to_record( self.file_name )
					for result in self.results
			]
		except Exception:
			return [ ]
	
	def to_summary_record( self ) -> Dict[ str, Any ]:
		"""
		Purpose:
		--------
		Convert the report into a one-row summary dictionary for batch display.

		Parameters:
		-----------
		None

		Returns:
		--------
		Dict[str, Any]: Batch summary record.
		"""
		try:
			self.determine_overall_status( )
			
			return {
					'File Name': self.file_name,
					'Brand Name': self.application.brand_name,
					'Beverage Type': self.application.beverage_type,
					FIELD_LABEL_TEXT: 'Found' if self.extracted_label.has_text( ) else 'Not Found',
					FIELD_OVERALL_STATUS: self.overall_status,
					'Failures': sum( result.is_failure( ) for result in self.results ),
					'Warnings': sum( result.is_warning( ) for result in self.results ),
					'Needs Review': 1 if not self.results else sum( result.is_review( ) for result in self.results ),
					'Processing Seconds': round( self.processing_seconds, 2 ),
					'Created On': self.created_on.strftime( REPORT_DATE_FORMAT )
			}
		except Exception:
			return {
					'File Name': self.file_name,
					'Brand Name': self.application.brand_name,
					'Beverage Type': self.application.beverage_type,
					FIELD_LABEL_TEXT: 'Unknown',
					FIELD_OVERALL_STATUS: STATUS_REVIEW,
					'Failures': 0,
					'Warnings': 0,
					'Needs Review': 1,
					'Processing Seconds': round( self.processing_seconds, 2 ),
					'Created On': self.created_on.strftime( REPORT_DATE_FORMAT )
			}
	
	def add_result( self, result: LabelCheckResult ) -> None:
		"""
		Purpose:
		--------
		Add one rule result to the verification report.

		Parameters:
		-----------
		result (LabelCheckResult): Rule result to append.

		Returns:
		--------
		None
		"""
		try:
			throw_if( 'result', result )
			self.results.append( result )
			self.determine_overall_status( )
		except Exception:
			self.overall_status = STATUS_REVIEW
	
	@classmethod
	def empty( cls, file_name: str = '' ) -> 'LabelVerificationReport':
		"""
		Purpose:
		--------
		Create an empty review report when verification cannot be completed.

		Parameters:
		-----------
		file_name (str): Optional uploaded file name.

		Returns:
		--------
		LabelVerificationReport: Empty report marked as Needs Review.
		"""
		try:
			return cls( file_name=file_name, overall_status=STATUS_REVIEW,
				results=[ LabelCheckResult(
							rule_id='verification_unavailable',
							field_name='Verification',
							status=STATUS_REVIEW,
							severity='High',
							expected='Readable label and application data',
							observed='Verification could not be completed',
							confidence=0.0,
							evidence='',
							message='The label could not be verified and requires human review.',
							requires_human_review=True ) ] )
		except Exception:
			return cls( )

# ==========================================================================================
# Batch Report Model
# ==========================================================================================

class BatchVerificationReport( BaseModel ):
	"""
	Purpose:
	--------
	Represent a batch of alcohol label verification reports.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
	"""
	
	reports: List[ LabelVerificationReport ] = Field( default_factory=list )
	created_on: datetime = Field( default_factory=datetime.now )
	
	def add_report( self, report: LabelVerificationReport ) -> None:
		"""
		Purpose:
		--------
		Add one label verification report to the batch.

		Parameters:
		-----------
		report (LabelVerificationReport): Report to append to the batch.

		Returns:
		--------
		None
		"""
		try:
			throw_if( 'report', report )
			self.reports.append( report )
		except Exception:
			return None

	def to_detail_records( self ) -> List[ Dict[ str, Any ] ]:
		"""
		Purpose:
		--------
		Convert all batch rule results into flat detail records.

		Parameters:
		-----------
		None

		Returns:
		--------
		List[Dict[str, Any]]: Flat rule result records for all reports.
		"""
		try:
			records = [ ]
			for report in self.reports:
				records.extend( report.to_records( ) )
			
			return records
		except Exception:
			return [ ]
	
	def total_files( self ) -> int:
		"""
		Purpose:
		--------
		Count the number of reports in the batch.

		Parameters:
		-----------
		None

		Returns:
		--------
		int: Number of reports.
		"""
		try:
			return len( self.reports )
		except Exception:
			return 0
	
	def total_failures( self ) -> int:
		"""
		Purpose:
		--------
		Count reports with one or more failing rule results.

		Parameters:
		-----------
		None

		Returns:
		--------
		int: Number of reports containing failures.
		"""
		try:
			return sum( report.has_failures( ) for report in self.reports )
		except Exception:
			return 0
	
	def total_reviews( self ) -> int:
		"""
		Purpose:
		--------
		Count reports requiring human review.

		Parameters:
		-----------
		None

		Returns:
		--------
		int: Number of reports requiring review.
		"""
		try:
			return sum( report.has_reviews( ) for report in self.reports )
		except Exception:
			return 0
	
	def total_warnings( self ) -> int:
		"""
		Purpose:
		--------
		Count reports with one or more warning rule results.

		Parameters:
		-----------
		None

		Returns:
		--------
		int: Number of reports containing warnings.
		"""
		try:
			return sum( report.has_warnings( ) for report in self.reports )
		except Exception:
			return 0
			
	def to_summary_records( self ) -> List[ Dict[ str, Any ] ]:
		"""
			Purpose:
			--------
			Convert all batch reports into flat summary records.
		
			Parameters:
			-----------
			None
		
			Returns:
			--------
			List[Dict[str, Any]]: Flat summary records for all reports.
		"""
		try:
			return [
					report.to_summary_record( )
					for report in self.reports
			]
		except Exception:
			return [ ]

