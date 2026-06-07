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
        Defines the Pydantic data models used by the Fiddy label verification workflow.

        This module contains application-data, OCR extraction, rule-result, single-report, and
        batch-report models used to move structured verification data between OCR, rule
        execution, Streamlit display, and report export layers.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from booger import Error, Logger
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

# ==========================================================================================
# Application Data Model
# ==========================================================================================

class LabelApplication( BaseModel ):
	"""Represent expected application data entered by the compliance reviewer.

	The ``LabelApplication`` model stores the expected values that will be compared against OCR
	label text and structured extraction results. These values may be entered manually by a
	reviewer, loaded from a CSV manifest, or constructed by another application layer before
	verification begins.

	The model intentionally separates expected application values from extracted label values.
	This allows the verifier and report writer to display side-by-side application-versus-label
	comparisons while preserving the original application context used by the rule engine.

	Attributes:
		brand_name (str): Expected brand name from the application.
		class_type (str): Expected class or type designation.
		beverage_type (str): Expected beverage category used for beverage-specific rule checks.
		alcohol_content (Optional[float]): Expected alcohol by volume value.
		proof (Optional[float]): Expected proof value when relevant.
		net_contents (str): Expected net contents value.
		producer_bottler (str): Expected producer or bottler value.
		imported (bool): Indicates whether importer and country-of-origin checks are relevant.
		importer (str): Expected importer name when applicable.
		country_of_origin (str): Expected country of origin when applicable.
		government_warning (str): Expected government warning statement.
		cola_id (str): Optional COLA identifier or application reference.
		notes (str): Optional reviewer or manifest notes.
	"""
	brand_name: str = Field( default='', description='Expected brand name from the application.' )
	class_type: str = Field( default='', description='Expected class or type designation.' )
	beverage_type: str = Field( default=BEVERAGE_TYPE_DISTILLED_SPIRITS )
	alcohol_content: Optional[ float ] = Field( default=None, description='Expected ABV value.' )
	proof: Optional[ float ] = Field( default=None, description='Expected proof value.' )
	net_contents: str = Field( default='', description='Expected net contents value.' )
	producer_bottler: str = Field( default='', description='Expected producer or bottler.' )
	imported: bool = Field( default=False,
		description='Indicates whether the product is imported.' )
	importer: str = Field( default='', description='Expected importer name, when applicable.' )
	country_of_origin: str = Field( default='', description='Expected country of origin.' )
	government_warning: str = Field( default='',
		description='Expected government warning statement.' )
	cola_id: str = Field( default='',
		description='Optional COLA identifier or application reference.' )
	notes: str = Field( default='', description='Optional reviewer notes.' )
	
	def required_field_map( self ) -> Dict[ str, Any ]:
		"""Return expected values keyed by reviewer-facing label field names.

		Purpose:
			This method creates a display-oriented dictionary from the expected application values.
			The keys are user-facing labels rather than internal attribute names so the returned
			mapping can be used directly in comparison tables, review panels, or export records.
	
			The importer field is included only when the application indicates that the product is
			imported. This preserves the original behavior and avoids showing importer expectations
			for domestic products where the importer field is not applicable.

		Returns:
			Dict[str, Any]: Dictionary of expected application field values. If mapping fails,
			the exception is logged and an empty dictionary is returned.
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
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'required_field_map( ) -> Dict[str, Any]'
			Logger( ).write( error )
			return { }

# ==========================================================================================
# Extracted Label Model
# ==========================================================================================

class ExtractedLabel( BaseModel ):
	"""Represent OCR and structured extraction results for one uploaded label file.

	Purpose:
		The ``ExtractedLabel`` model stores the raw OCR output, normalized OCR text, structured
		fields extracted from the label, OCR engine metadata, OCR timing, and image-quality notes.
		It is the label-side counterpart to ``LabelApplication`` and is used by the verifier to
		compare what appears on label artwork against what was expected from application data.
	
		Structured fields may be populated by the OCR engine, field extractor, or verifier
		enrichment step. Raw text remains available so deterministic rules can still search the full
		label text even when a structured field is missing or incomplete.

	Attributes:
		file_name (str): Uploaded file name.
		file_type (str): Detected file extension or upload type.
		raw_text (str): Raw OCR text extracted from the label.
		normalized_text (str): Normalized OCR text used for matching.
		brand_name (str): Extracted brand name.
		class_type (str): Extracted class or type designation.
		alcohol_content (Optional[float]): Extracted alcohol by volume value.
		net_contents (str): Extracted net contents value.
		producer_bottler (str): Extracted producer or bottler text.
		country_of_origin (str): Extracted country-of-origin text.
		government_warning (str): Extracted government-warning text.
		ocr_engine (str): OCR engine used for extraction.
		ocr_seconds (float): Elapsed OCR processing time.
		image_quality_notes (List[str]): OCR and image-quality notes.
		created_on (datetime): Creation timestamp for the extraction model.
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
		"""Determine whether OCR produced readable label text.

		Purpose:
			This method checks whether ``raw_text`` exists and contains non-whitespace content. The
			verifier uses this method to decide whether normal text-based rules can run or whether an
			OCR human-review result should be created instead.

		Returns:
			bool: ``True`` when extracted raw text is present; otherwise, ``False``. If the check
			fails unexpectedly, the exception is logged and ``False`` is returned.
		"""
		try:
			return bool( self.raw_text and self.raw_text.strip( ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'has_text( ) -> bool'
			Logger( ).write( error )
			return False
	
	def to_extracted_field_map( self ) -> Dict[ str, Any ]:
		"""Return extracted label values keyed by reviewer-facing field names.

		Purpose:
			This method creates a display-oriented dictionary from structured OCR extraction fields.
			The keys are user-facing labels so the mapping can be used in side-by-side comparison
			tables with the application field map. The method includes both ``Alcohol Content`` and
			``ABV`` keys for the same extracted ABV value to preserve the original return contract.

		Returns:
			Dict[str, Any]: Structured extracted label field values. If mapping fails, the
			exception is logged and an empty dictionary is returned.
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
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_extracted_field_map( ) -> Dict[str, Any]'
			Logger( ).write( error )
			return { }

class LabelCheckResult( BaseModel ):
	"""Represent the result of one deterministic label verification rule.

	Purpose:
		The ``LabelCheckResult`` model captures the outcome of an individual rule executed against
		label text and application data. Each result stores the rule identifier, field name, status,
		severity, expected value, observed value, confidence score, supporting evidence, reviewer
		message, human-review flag, and creation timestamp.
	
		The report models use these helpers to count passes, warnings, failures, and review items.
		The flat record conversion method is used by DataFrame-building and report-writing code.

	Attributes:
		rule_id (str): Machine-readable rule identifier.
		field_name (str): User-facing field name associated with the rule.
		status (str): Rule status such as Pass, Warning, Fail, or Needs Review.
		severity (str): Relative issue severity.
		expected (str): Expected value, requirement, or comparison condition.
		observed (str): Observed label value or execution condition.
		confidence (float): Rule confidence from 0.0 to 100.0.
		evidence (str): Relevant extracted label text span or supporting detail.
		message (str): Reviewer-facing explanation.
		requires_human_review (bool): Indicates whether reviewer judgment is required.
		created_on (datetime): Creation timestamp for the rule result.
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
		"""Determine whether the rule result is a passing result.

		Returns:
			bool: ``True`` when ``status`` equals ``STATUS_PASS``; otherwise, ``False``. If the
			check fails unexpectedly, the exception is logged and ``False`` is returned.
		"""
		try:
			return self.status == STATUS_PASS
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'is_pass( ) -> bool'
			Logger( ).write( error )
			return False
	
	def is_warning( self ) -> bool:
		"""Determine whether the rule result is a warning result.

		Returns:
			bool: ``True`` when ``status`` equals ``STATUS_WARNING``; otherwise, ``False``. If the
			check fails unexpectedly, the exception is logged and ``False`` is returned.
		"""
		try:
			return self.status == STATUS_WARNING
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'is_warning( ) -> bool'
			Logger( ).write( error )
			return False
	
	def is_failure( self ) -> bool:
		"""Determine whether the rule result is a failing result.

		Returns:
			bool: ``True`` when ``status`` equals ``STATUS_FAIL``; otherwise, ``False``. If the
			check fails unexpectedly, the exception is logged and ``False`` is returned.
		"""
		try:
			return self.status == STATUS_FAIL
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'is_failure( ) -> bool'
			Logger( ).write( error )
			return False
	
	def is_review( self ) -> bool:
		"""Determine whether the rule result requires human review.

		Purpose:
			A result is considered a review item when its status is ``STATUS_REVIEW`` or when its
			``requires_human_review`` flag is set. This supports rules that may have a non-review
			status but still need reviewer confirmation.

		Returns:
			bool: ``True`` when human review is required; otherwise, ``False``. If the check fails
			unexpectedly, the exception is logged and ``False`` is returned.
		"""
		try:
			return self.status == STATUS_REVIEW or self.requires_human_review
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'is_review( ) -> bool'
			Logger( ).write( error )
			return False
	
	def to_record( self, file_name: str ) -> Dict[ str, Any ]:
		"""Convert the rule result into a flat dictionary for display or export.

		Purpose:
			The returned record contains file name, field name, rule identifier, status, severity,
			expected value, observed value, rounded confidence, evidence, and reviewer-facing message.
			This shape is suitable for DataFrame display, CSV export, and detail-report generation.

		Args:
			file_name (str): Name of the uploaded file associated with the rule result.

		Returns:
			Dict[str, Any]: Flat dictionary containing display-ready result fields. If conversion
			fails, the exception is logged and a conservative fallback record is returned.
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
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( file_name: str ) -> Dict[str, Any]'
			Logger( ).write( error )
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
	"""Represent the complete verification report for one uploaded alcohol label.

	Purpose:
		The ``LabelVerificationReport`` model aggregates expected application data, OCR extraction
		data, rule results, overall status, processing time, reviewer disclaimer, and creation time
		for one label file. It is the primary single-label report object returned by the verifier.
	
		The report determines its overall status from the individual rule results. Failures take
		priority over review items, review items take priority over warnings, warnings take priority
		over pass, and a report with no results defaults to ``Needs Review``.

	Attributes:
		file_name (str): Uploaded file name.
		application (LabelApplication): Expected application values.
		extracted_label (ExtractedLabel): OCR and structured extraction result.
		results (List[LabelCheckResult]): Rule results for the label.
		overall_status (str): Current overall report status.
		processing_seconds (float): Total processing duration for the label.
		reviewer_disclaimer (str): Reviewer-facing AI-assistance disclaimer.
		created_on (datetime): Creation timestamp for the report.
	"""
	
	file_name: str = Field( default='', description='Uploaded file name.' )
	application: LabelApplication = Field( default_factory=LabelApplication )
	extracted_label: ExtractedLabel = Field( default_factory=ExtractedLabel )
	results: List[ LabelCheckResult ] = Field( default_factory=list )
	overall_status: str = Field( default=STATUS_REVIEW )
	processing_seconds: float = Field( default=0.0 )
	reviewer_disclaimer: str = Field(
		default=('AI-assisted preliminary review only. Final regulatory determinations remain '
		         'with authorized compliance personnel.') )
	created_on: datetime = Field( default_factory=datetime.now )
	
	def determine_overall_status( self ) -> str:
		"""Determine the overall report status from individual rule results.

		Purpose:
			The method applies a deterministic priority order. Empty reports are marked
			``Needs Review``. Any failure marks the report ``Fail``. If no failures exist but any
			review item exists, the report is marked ``Needs Review``. If no failures or reviews
			exist but warnings exist, the report is marked ``Warning``. Otherwise, the report passes.

		Returns:
			str: Overall status value. If status determination fails, the exception is logged,
			``overall_status`` is set to ``STATUS_REVIEW``, and that value is returned.
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
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'determine_overall_status( ) -> str'
			Logger( ).write( error )
			self.overall_status = STATUS_REVIEW
			return self.overall_status
	
	def has_failures( self ) -> bool:
		"""Determine whether the report contains any failing rule results.

		Returns:
			bool: ``True`` when one or more child results are failures; otherwise, ``False``. If
			the check fails unexpectedly, the exception is logged and ``False`` is returned.
		"""
		try:
			return any( result.is_failure( ) for result in self.results )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'has_failures( ) -> bool'
			Logger( ).write( error )
			return False
	
	def has_reviews( self ) -> bool:
		"""Determine whether the report contains any human-review rule results.

		Returns:
			bool: ``True`` when one or more child results require review; otherwise, ``False``. If
			the check fails unexpectedly, the exception is logged and ``False`` is returned.
		"""
		try:
			return any( result.is_review( ) for result in self.results )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'has_reviews( ) -> bool'
			Logger( ).write( error )
			return False
	
	def has_warnings( self ) -> bool:
		"""Determine whether the report contains any warning rule results.

		Returns:
			bool: ``True`` when one or more child results are warnings; otherwise, ``False``. If
			the check fails unexpectedly, the exception is logged and ``False`` is returned.
		"""
		try:
			return any( result.is_warning( ) for result in self.results )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'has_warnings( ) -> bool'
			Logger( ).write( error )
			return False
	
	def to_records( self ) -> List[ Dict[ str, Any ] ]:
		"""Convert all rule results into flat dictionaries.

		Purpose:
			This method delegates detail-record creation to each ``LabelCheckResult`` and passes the
			report's file name into every child record. The resulting list is suitable for detail
			DataFrames, CSV exports, or rule-level report sections.

		Returns:
			List[Dict[str, Any]]: Flat verification result records. If conversion fails, the
			exception is logged and an empty list is returned.
		"""
		try:
			return [
					result.to_record( self.file_name )
					for result in self.results
			]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_records( ) -> List[Dict[str, Any]]'
			Logger( ).write( error )
			return [ ]
	
	def to_summary_record( self ) -> Dict[ str, Any ]:
		"""Convert the report into a one-row summary dictionary.

		Purpose:
			The summary record contains the file name, brand name, beverage type, extracted-text
			presence, overall status, failure count, warning count, review count, processing seconds,
			and formatted creation timestamp. The method recalculates overall status before creating
			the summary so the record reflects the current result list.

		Returns:
			Dict[str, Any]: Batch summary record. If conversion fails, the exception is logged and
			a conservative fallback summary is returned with ``Unknown`` extracted-text status and
			``Needs Review`` overall status.
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
					'Needs Review': 1 if not self.results else sum(
						result.is_review( ) for result in self.results ),
					'Processing Seconds': round( self.processing_seconds, 2 ),
					'Created On': self.created_on.strftime( REPORT_DATE_FORMAT )
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_summary_record( ) -> Dict[str, Any]'
			Logger( ).write( error )
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
		"""Add one rule result to the verification report.

		Purpose:
			This method appends a ``LabelCheckResult`` to the report and immediately recalculates the
			overall report status. Recalculating after every append keeps the status synchronized for
			UI components that read the report before all rules have been added.

		Args:
			result (LabelCheckResult): Rule result to append.

		Returns:
			None.
		"""
		try:
			throw_if( 'result', result )
			self.results.append( result )
			self.determine_overall_status( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'add_result( result: LabelCheckResult ) -> None'
			Logger( ).write( error )
			self.overall_status = STATUS_REVIEW
	
	@classmethod
	def empty( cls, file_name: str = '' ) -> 'LabelVerificationReport':
		"""Create an empty review report when verification cannot be completed.

		Purpose:
			The fallback report contains one ``LabelCheckResult`` indicating that verification was
			unavailable and that human review is required. This classmethod is used by verifier,
			batch, and error-handling paths to return a structurally valid report instead of raising
			an exception to the UI.

		Args:
			file_name (str): Optional uploaded file name to assign to the fallback report.

		Returns:
			LabelVerificationReport: Empty report marked as ``Needs Review``. If fallback report
			creation itself fails, the exception is logged and a default report instance is
			returned.
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
		except Exception as e:
			error = Error( e )
			error.cause = cls.__name__
			error.module = __name__
			error.method = 'empty( file_name: str ) -> LabelVerificationReport'
			Logger( ).write( error )
			return cls( )

class BatchVerificationReport( BaseModel ):
	"""Represent a batch of alcohol label verification reports.

	Purpose:
		The ``BatchVerificationReport`` model aggregates single-label verification reports into a
		batch container. It provides helper methods for appending reports, flattening rule detail
		records, counting report outcomes, and creating summary records for every report in the
		batch.

	Attributes:
		reports (List[LabelVerificationReport]): Verification reports contained in the batch.
		created_on (datetime): Creation timestamp for the batch report.
	"""
	
	reports: List[ LabelVerificationReport ] = Field( default_factory=list )
	created_on: datetime = Field( default_factory=datetime.now )
	
	def add_report( self, report: LabelVerificationReport ) -> None:
		"""Add one label verification report to the batch.

		Args:
			report (LabelVerificationReport): Report to append to the batch.

		Returns:
			None.
		"""
		try:
			throw_if( 'report', report )
			self.reports.append( report )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'add_report( report: LabelVerificationReport ) -> None'
			Logger( ).write( error )
			return None
	
	def to_detail_records( self ) -> List[ Dict[ str, Any ] ]:
		"""Convert all batch rule results into flat detail records.

		Purpose:
			This method iterates through each child report and extends a single list with that
			report's flat rule records. The output is suitable for detail DataFrames or CSV exports
			that need one row per rule result across the full batch.

		Returns:
			List[Dict[str, Any]]: Flat rule result records for all reports. If conversion fails,
			the exception is logged and an empty list is returned.
		"""
		try:
			records = [ ]
			for report in self.reports:
				records.extend( report.to_records( ) )
			
			return records
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_detail_records( ) -> List[Dict[str, Any]]'
			Logger( ).write( error )
			return [ ]
	
	def total_files( self ) -> int:
		"""Count the number of reports in the batch.

		Returns:
			int: Number of reports. If counting fails, the exception is logged and ``0`` is
			returned.
		"""
		try:
			return len( self.reports )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'total_files( ) -> int'
			Logger( ).write( error )
			return 0
	
	def total_failures( self ) -> int:
		"""Count reports with one or more failing rule results.

		Returns:
			int: Number of reports containing failures. If counting fails, the exception is logged
			and ``0`` is returned.
		"""
		try:
			return sum( report.has_failures( ) for report in self.reports )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'total_failures( ) -> int'
			Logger( ).write( error )
			return 0
	
	def total_reviews( self ) -> int:
		"""Count reports requiring human review.

		Returns:
			int: Number of reports requiring review. If counting fails, the exception is logged
			and ``0`` is returned.
		"""
		try:
			return sum( report.has_reviews( ) for report in self.reports )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'total_reviews( ) -> int'
			Logger( ).write( error )
			return 0
	
	def total_warnings( self ) -> int:
		"""Count reports with one or more warning rule results.

		Returns:
			int: Number of reports containing warnings. If counting fails, the exception is logged
			and ``0`` is returned.
		"""
		try:
			return sum( report.has_warnings( ) for report in self.reports )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'total_warnings( ) -> int'
			Logger( ).write( error )
			return 0
	
	def to_summary_records( self ) -> List[ Dict[ str, Any ] ]:
		"""Convert all batch reports into flat summary records.

		Purpose:
			This method delegates summary creation to each child ``LabelVerificationReport`` and
			returns a list containing one summary row per report.

		Returns:
			List[Dict[str, Any]]: Flat summary records for all reports. If conversion fails, the
			exception is logged and an empty list is returned.
		"""
		try:
			return [ report.to_summary_record( ) for report in self.reports ]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_summary_records( ) -> List[Dict[str, Any]]'
			Logger( ).write( error )
			return [ ]