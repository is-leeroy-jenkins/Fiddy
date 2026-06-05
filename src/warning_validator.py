'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                warning_validator.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="warning_validator.py" company="Terry D. Eppler">

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
        Provides government-warning validation for the Fiddy label verification workflow.

        This module validates government-warning presence, all-caps prefix formatting, exact
        standard warning wording, near-match review conditions, extracted warning context, and
        visual-format review requirements that cannot be proven from OCR text alone.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import re
from typing import Dict, List

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from booger import Error, Logger
from config import throw_if
from src.constants import (
	FIELD_GOVERNMENT_WARNING,
	GOVERNMENT_WARNING_PREFIX,
	GOVERNMENT_WARNING_TEXT,
	GOVERNMENT_WARNING_TEXT_NORMALIZED,
	RULE_GOVERNMENT_WARNING_EXACT,
	RULE_GOVERNMENT_WARNING_PREFIX_CAPS,
	RULE_GOVERNMENT_WARNING_PRESENT,
	RULE_GOVERNMENT_WARNING_VISUAL_FORMAT,
	SEVERITY_HIGH,
	SEVERITY_INFO,
	SEVERITY_LOW,
	SEVERITY_MEDIUM,
	STATUS_FAIL,
	STATUS_PASS,
	STATUS_REVIEW,
	STATUS_WARNING
)
from src.models import LabelCheckResult
from src.normalizer import TextNormalizer

# ==========================================================================================
# Warning Validation Models
# ==========================================================================================

class GovernmentWarningValidation( BaseModel ):
	"""Represent the complete government-warning validation outcome for one label.

	The ``GovernmentWarningValidation`` model stores the intermediate and final determinations
	used by government-warning rule-result creation. It records whether warning text appears to
	be present, whether the warning prefix is present in any case, whether the required all-caps
	prefix appears, whether the standard warning text matches exactly after normalization,
	whether the text is a near match requiring review, the similarity score, visual-format review
	flags, extracted warning context, and reviewer-facing validation messages.

	The model intentionally separates text validation from visual-format validation. OCR can
	support wording and prefix checks, but it cannot reliably prove boldness, font size,
	contrast, placement, or whether the warning is visually hidden. Those visual-format concerns
	remain review items.

	Attributes:
		text_present (bool): Indicates whether government-warning language appears to be present.
		prefix_present (bool): Indicates whether a government-warning prefix was detected in any
			case.
		prefix_all_caps (bool): Indicates whether the required all-caps prefix was detected.
		exact_text_match (bool): Indicates whether normalized OCR text contains the complete
			standard warning text.
		near_text_match (bool): Indicates whether warning text is similar enough to require
			review but not exact enough to pass.
		normalized_similarity (float): Similarity score from 0.0 to 100.0.
		visual_format_verified (bool): Indicates whether visual formatting was verified.
		visual_format_review_required (bool): Indicates whether visual review is required.
		warning_context (str): Extracted OCR context around the warning prefix.
		messages (List[str]): Reviewer-facing validation messages.
	"""
	
	text_present: bool = Field( default=False )
	prefix_present: bool = Field( default=False )
	prefix_all_caps: bool = Field( default=False )
	exact_text_match: bool = Field( default=False )
	near_text_match: bool = Field( default=False )
	normalized_similarity: float = Field( default=0.0 )
	visual_format_verified: bool = Field( default=False )
	visual_format_review_required: bool = Field( default=True )
	warning_context: str = Field( default='' )
	messages: List[ str ] = Field( default_factory=list )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert the government-warning validation outcome into a flat record.

		This method converts validation flags, similarity score, warning context, and validation
		messages into a dictionary suitable for Streamlit tables, pandas DataFrames, CSV export,
		JSON export, or report-writing workflows. The similarity value is rounded to two decimal
		places, and messages are joined into a semicolon-delimited string for compact display.

		Returns:
			Dict[str, object]: Flat warning validation record. If conversion fails, the exception
			is logged and a conservative fallback record is returned with all validation flags set
			to false or review-required values.
		"""
		try:
			return {
					'Text Present': self.text_present,
					'Prefix Present': self.prefix_present,
					'Prefix All Caps': self.prefix_all_caps,
					'Exact Text Match': self.exact_text_match,
					'Near Text Match': self.near_text_match,
					'Similarity': round( self.normalized_similarity, 2 ),
					'Visual Format Verified': self.visual_format_verified,
					'Visual Review Required': self.visual_format_review_required,
					'Warning Context': self.warning_context,
					'Messages': '; '.join( self.messages )
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Text Present': False,
					'Prefix Present': False,
					'Prefix All Caps': False,
					'Exact Text Match': False,
					'Near Text Match': False,
					'Similarity': 0.0,
					'Visual Format Verified': False,
					'Visual Review Required': True,
					'Warning Context': '',
					'Messages': 'Warning validation record could not be rendered.'
			}

# ==========================================================================================
# Government Warning Validator
# ==========================================================================================

class GovernmentWarningValidator( ):
	"""Validate mandatory government-warning text and related review conditions.

	The ``GovernmentWarningValidator`` class performs deterministic validation of the mandatory
	government warning statement. It checks whether a government-warning prefix is present,
	whether the prefix appears in the required all-caps form, whether normalized OCR text
	contains the complete standard warning text, whether similar but non-exact text requires
	reviewer attention, and whether visual-format review is required.

	The validator deliberately treats near matches as failures for the exact-text rule because
	the warning wording requirement is strict. Near matches are retained only to provide useful
	reviewer evidence and to distinguish likely OCR or wording variation from complete absence.

	Attributes:
		_text (str): Raw OCR label text currently being validated.
		_normalized_text (str): Normalized OCR text used for strict warning comparison.
		_warning_context (str): Extracted context surrounding the warning prefix.
		_normalizer (TextNormalizer): Normalization helper used for strict warning checks.
		_exact_threshold (float): Similarity score required for exact-match classification.
		_near_threshold (float): Similarity score required for near-match review classification.
	"""
	
	_text: str
	_normalized_text: str
	_warning_context: str
	_normalizer: TextNormalizer
	_exact_threshold: float
	_near_threshold: float
	
	def __init__( self, exact_threshold: float = 100.0, near_threshold: float = 92.0 ) -> None:
		"""Initialize the government-warning validator.

		The constructor creates the text normalizer and stores the similarity thresholds used by
		warning validation. The exact threshold is retained for configuration transparency, while
		the current exact-text rule is based on containment of the normalized required warning
		text. The near threshold is used to identify non-exact warning text that is close enough
		to require reviewer attention.

		Args:
			exact_threshold (float): Similarity score required for exact-match classification.
			near_threshold (float): Similarity score required for near-match human review.

		Returns:
			None.
		"""
		self._normalizer = TextNormalizer( )
		self._exact_threshold = exact_threshold
		self._near_threshold = near_threshold
	
	@property
	def exact_threshold( self ) -> float:
		"""Return the configured exact-match similarity threshold.

		Returns:
			float: Exact-match threshold stored on this validator instance.
		"""
		return self._exact_threshold
	
	@property
	def near_threshold( self ) -> float:
		"""Return the configured near-match similarity threshold.

		Returns:
			float: Near-match threshold stored on this validator instance.
		"""
		return self._near_threshold
	
	def get_warning_context( self, text: str, window: int = 420 ) -> str:
		"""Extract the likely government-warning text span from OCR text.

		This method searches for the government-warning prefix using case-insensitive matching.
		When the prefix is found, it returns a bounded text span starting at the prefix and
		continuing for the configured window length. The context is used as evidence in warning
		rule results so reviewers can inspect the OCR text surrounding the warning.

		Args:
			text (str): Raw OCR label text.
			window (int): Maximum number of characters to return after the warning prefix.

		Returns:
			str: Extracted warning context, or an empty string when unavailable. If extraction
			fails, the exception is logged and an empty string is returned.
		"""
		try:
			throw_if( 'text', text )
			throw_if( 'window', window )
			
			self._text = text
			match = re.search(
				r'\bgovernment\s+warning\s*:',
				self._text,
				flags=re.IGNORECASE
			)
			
			if not match:
				return ''
			
			start = match.start( )
			end = min( len( self._text ), start + int( window ) )
			
			return self._text[ start:end ].strip( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_warning_context( text: str, window: int ) -> str'
			Logger( ).write( error )
			return ''
	
	def has_warning_prefix( self, text: str ) -> bool:
		"""Determine whether OCR text contains a government-warning prefix in any case.

		This method performs a case-insensitive search for ``government warning:`` with flexible
		whitespace before the colon. It identifies whether warning language begins with the
		expected prefix, regardless of capitalization.

		Args:
			text (str): Raw OCR label text.

		Returns:
			bool: ``True`` when a government-warning prefix is present; otherwise, ``False``. If
			the check fails, the exception is logged and ``False`` is returned.
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			return bool(
				re.search(
					r'\bgovernment\s+warning\s*:',
					self._text,
					flags=re.IGNORECASE
				)
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'has_warning_prefix( text: str ) -> bool'
			Logger( ).write( error )
			return False
	
	def has_all_caps_prefix( self, text: str ) -> bool:
		"""Determine whether OCR text contains the required all-caps warning prefix.

		This method searches raw OCR text for ``GOVERNMENT WARNING:`` with flexible whitespace
		before the colon. It intentionally does not normalize case because capitalization is the
		requirement being checked.

		Args:
			text (str): Raw OCR label text.

		Returns:
			bool: ``True`` when the all-caps prefix is present; otherwise, ``False``. If the check
			fails, the exception is logged and ``False`` is returned.
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			return bool(
				re.search(
					r'\bGOVERNMENT\s+WARNING\s*:',
					self._text
				)
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'has_all_caps_prefix( text: str ) -> bool'
			Logger( ).write( error )
			return False
	
	def has_standard_warning_text( self, text: str ) -> bool:
		"""Determine whether normalized OCR text contains the standard warning text.

		This method normalizes the supplied OCR text using strict government-warning
		normalization and checks whether the normalized required warning text is contained within
		that normalized OCR value. This supports strict wording validation while reducing false
		negatives from punctuation and formatting artifacts.

		Args:
			text (str): Raw OCR label text.

		Returns:
			bool: ``True`` when the full normalized warning text is contained; otherwise,
			``False``. If the check fails, the exception is logged and ``False`` is returned.
		"""
		try:
			throw_if( 'text', text )
			
			self._normalized_text = self._normalizer.normalize_for_strict_warning( text )
			return GOVERNMENT_WARNING_TEXT_NORMALIZED in self._normalized_text
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'has_standard_warning_text( text: str ) -> bool'
			Logger( ).write( error )
			return False
	
	def calculate_warning_similarity( self, text: str ) -> float:
		"""Calculate similarity between OCR text and the standard warning text.

		This method normalizes the supplied OCR text for strict warning comparison, then uses
		``rapidfuzz.fuzz.partial_ratio`` to compare the normalized standard warning text to the
		normalized OCR text. The score is used to identify near-match text that should be reviewed
		but must not pass exact-text validation.

		Args:
			text (str): Raw OCR label text.

		Returns:
			float: Similarity score from ``0.0`` to ``100.0``. If similarity cannot be calculated,
			the exception is logged and ``0.0`` is returned.
		"""
		try:
			throw_if( 'text', text )
			
			self._normalized_text = self._normalizer.normalize_for_strict_warning( text )
			
			if not self._normalized_text:
				return 0.0
			
			return float(
				fuzz.partial_ratio(
					GOVERNMENT_WARNING_TEXT_NORMALIZED,
					self._normalized_text
				)
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'calculate_warning_similarity( text: str ) -> float'
			Logger( ).write( error )
			return 0.0
	
	def validate( self, text: str ) -> GovernmentWarningValidation:
		"""Validate government-warning text and visual-format review requirements.

		This method performs the full government-warning validation workflow. It extracts warning
		context, checks prefix presence, checks all-caps prefix presence, checks exact normalized
		standard-warning text, calculates similarity, identifies near matches, determines whether
		warning text is present, and creates reviewer-facing validation messages. It always marks
		visual-format review as required because OCR text cannot prove visual properties such as
		boldness, minimum font size, contrast, prominence, or hidden placement.

		Args:
			text (str): Raw OCR label text.

		Returns:
			GovernmentWarningValidation: Structured warning validation outcome. If validation
			fails, the exception is logged and the original reviewer-safe fallback validation
			object is returned.
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			self._warning_context = self.get_warning_context( self._text )
			
			prefix_present = self.has_warning_prefix( self._text )
			prefix_all_caps = self.has_all_caps_prefix( self._text )
			exact_text_match = self.has_standard_warning_text( self._text )
			similarity = self.calculate_warning_similarity( self._text )
			near_match = not exact_text_match and similarity >= self._near_threshold
			text_present = prefix_present or exact_text_match or similarity >= self._near_threshold
			messages = [ ]
			
			if not prefix_present:
				messages.append( 'Government warning prefix was not detected.' )
			
			if prefix_present and not prefix_all_caps:
				messages.append( 'Government warning prefix is present but is not all caps.' )
			
			if exact_text_match:
				messages.append( 'Standard government warning text was detected exactly.' )
			elif near_match:
				messages.append(
					'Government warning text is similar to the standard warning but requires '
					'human review for exact wording.'
				)
			else:
				messages.append( 'Standard government warning text was not detected.' )
			
			messages.append(
				'OCR text checks cannot verify boldness, minimum font size, or whether the '
				'warning is visually hidden; reviewer visual confirmation is required.'
			)
			
			return GovernmentWarningValidation(
				text_present=text_present,
				prefix_present=prefix_present,
				prefix_all_caps=prefix_all_caps,
				exact_text_match=exact_text_match,
				near_text_match=near_match,
				normalized_similarity=similarity,
				visual_format_verified=False,
				visual_format_review_required=True,
				warning_context=self._warning_context,
				messages=messages
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'validate( text: str ) -> GovernmentWarningValidation'
			Logger( ).write( error )
			return GovernmentWarningValidation(
				text_present=False,
				prefix_present=False,
				prefix_all_caps=False,
				exact_text_match=False,
				near_text_match=False,
				normalized_similarity=0.0,
				visual_format_verified=False,
				visual_format_review_required=True,
				warning_context='',
				messages=[
						'Government warning validation could not be completed.'
				]
			)
	
	def create_presence_result( self, validation: GovernmentWarningValidation ) -> LabelCheckResult:
		"""Create a rule result for government-warning presence.

		This method converts the structured validation outcome into the presence rule result. A
		present warning passes, while missing warning language fails and requires human review.
		The extracted warning context is preserved as evidence.

		Args:
			validation (GovernmentWarningValidation): Warning validation outcome.

		Returns:
			LabelCheckResult: Warning presence rule result. If result creation fails, the
			exception is logged and the original unavailable-result fallback is returned.
		"""
		try:
			throw_if( 'validation', validation )
			
			status = STATUS_PASS if validation.text_present else STATUS_FAIL
			
			return LabelCheckResult(
				rule_id=RULE_GOVERNMENT_WARNING_PRESENT,
				field_name=FIELD_GOVERNMENT_WARNING,
				status=status,
				severity=SEVERITY_INFO if status == STATUS_PASS else SEVERITY_HIGH,
				expected='Government warning statement',
				observed='Found' if validation.text_present else 'Not found',
				confidence=95.0 if validation.text_present else 90.0,
				evidence=validation.warning_context,
				message=(
						'Government warning language was detected.'
						if validation.text_present
						else 'Government warning language was not detected.'
				),
				requires_human_review=status != STATUS_PASS
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_presence_result( validation: GovernmentWarningValidation ) -> LabelCheckResult'
			Logger( ).write( error )
			return self.create_unavailable_result(
				rule_id=RULE_GOVERNMENT_WARNING_PRESENT,
				message='Government warning presence result could not be created.'
			)
	
	def create_prefix_caps_result( self,
			validation: GovernmentWarningValidation ) -> LabelCheckResult:
		"""Create a rule result for the all-caps government-warning prefix.

		This method converts the structured validation outcome into the prefix-capitalization
		rule result. The result passes only when ``GOVERNMENT WARNING:`` appears in the required
		all-caps form. Any other condition fails and requires human review.

		Args:
			validation (GovernmentWarningValidation): Warning validation outcome.

		Returns:
			LabelCheckResult: Warning prefix capitalization result. If result creation fails, the
			exception is logged and the original unavailable-result fallback is returned.
		"""
		try:
			throw_if( 'validation', validation )
			
			status = STATUS_PASS if validation.prefix_all_caps else STATUS_FAIL
			observed = GOVERNMENT_WARNING_PREFIX if validation.prefix_all_caps else 'Not found as all caps'
			
			return LabelCheckResult(
				rule_id=RULE_GOVERNMENT_WARNING_PREFIX_CAPS,
				field_name=FIELD_GOVERNMENT_WARNING,
				status=status,
				severity=SEVERITY_INFO if status == STATUS_PASS else SEVERITY_HIGH,
				expected=GOVERNMENT_WARNING_PREFIX,
				observed=observed,
				confidence=98.0 if validation.prefix_all_caps else 90.0,
				evidence=validation.warning_context,
				message=(
						'The required all-caps GOVERNMENT WARNING: prefix was detected.'
						if validation.prefix_all_caps
						else 'The required all-caps GOVERNMENT WARNING: prefix was not detected.'
				),
				requires_human_review=status != STATUS_PASS
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_prefix_caps_result( validation: GovernmentWarningValidation ) -> LabelCheckResult'
			Logger( ).write( error )
			return self.create_unavailable_result(
				rule_id=RULE_GOVERNMENT_WARNING_PREFIX_CAPS,
				message='Government warning prefix result could not be created.'
			)
	
	def create_exact_text_result( self,
			validation: GovernmentWarningValidation ) -> LabelCheckResult:
		"""Create a strict rule result for exact government-warning text.

		This method creates the exact-text rule result from the structured validation outcome.
		The result passes only when the normalized OCR text contains the normalized required
		warning text. Near-match text fails because the warning wording requirement is exact; the
		near-match state is used only to support reviewer attention and evidence.

		Args:
			validation (GovernmentWarningValidation): Warning validation outcome.

		Returns:
			LabelCheckResult: Exact warning text rule result. If result creation fails, the
			exception is logged and the original unavailable-result fallback is returned.
		"""
		try:
			throw_if( 'validation', validation )
			
			if validation.exact_text_match:
				status = STATUS_PASS
				severity = SEVERITY_INFO
				observed = 'Exact standard warning text detected'
				message = (
						'Government warning wording matches the required standard text exactly after '
						'normalization.'
				)
				confidence = 100.0
				requires_review = False
			elif validation.near_text_match:
				status = STATUS_FAIL
				severity = SEVERITY_HIGH
				observed = 'Similar but non-exact warning text detected'
				message = (
						'Government warning wording is similar to the required text, but exact '
						'wording is mandatory. Similar warning text must not be accepted as a pass.'
				)
				confidence = validation.normalized_similarity
				requires_review = True
			else:
				status = STATUS_FAIL
				severity = SEVERITY_HIGH
				observed = 'Exact warning text not detected'
				message = (
						'Government warning wording does not match the required standard text.'
				)
				confidence = validation.normalized_similarity
				requires_review = True
			
			return LabelCheckResult(
				rule_id=RULE_GOVERNMENT_WARNING_EXACT,
				field_name=FIELD_GOVERNMENT_WARNING,
				status=status,
				severity=severity,
				expected=GOVERNMENT_WARNING_TEXT,
				observed=observed,
				confidence=round( float( confidence or 0.0 ), 1 ),
				evidence=validation.warning_context,
				message=message,
				requires_human_review=requires_review
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_exact_text_result( validation: GovernmentWarningValidation ) -> LabelCheckResult'
			Logger( ).write( error )
			return self.create_unavailable_result(
				rule_id=RULE_GOVERNMENT_WARNING_EXACT,
				message='Government warning exact-text result could not be created.'
			)
	
	def create_visual_format_result( self,
			validation: GovernmentWarningValidation ) -> LabelCheckResult:
		"""Create a government-warning visual-format review result.

		This method creates the visual-format rule result from the structured validation outcome.
		OCR can support warning presence and wording checks, but it cannot prove visual
		presentation requirements such as boldness, readable size, contrast, prominence, or
		whether the warning is hidden. For that reason, this method always returns a human-review
		result rather than an automated pass.

		Args:
			validation (GovernmentWarningValidation): Warning validation outcome.

		Returns:
			LabelCheckResult: Visual-format review result. If result creation fails, the exception
			is logged and the original unavailable-result fallback is returned.
		"""
		try:
			throw_if( 'validation', validation )
			
			if validation.text_present:
				status = STATUS_REVIEW
				severity = SEVERITY_MEDIUM
				observed = 'Warning text detected; visual formatting requires human confirmation'
				confidence = 0.0
				message = (
						'OCR confirms warning text is present, but OCR cannot verify required visual '
						'presentation such as boldness, readable size, contrast, or whether the '
						'warning is visually hidden. Reviewer visual confirmation is required.'
				)
			else:
				status = STATUS_REVIEW
				severity = SEVERITY_HIGH
				observed = 'Warning text not detected; visual formatting cannot be evaluated'
				confidence = 0.0
				message = (
						'Government warning visual formatting cannot be evaluated because the warning '
						'text was not detected. Reviewer must inspect the label artwork manually.'
				)
			
			return LabelCheckResult(
				rule_id=RULE_GOVERNMENT_WARNING_VISUAL_FORMAT,
				field_name=FIELD_GOVERNMENT_WARNING,
				status=status,
				severity=severity,
				expected='Reviewer confirmation of warning boldness, readability, contrast, and visibility',
				observed=observed,
				confidence=confidence,
				evidence=validation.warning_context,
				message=message,
				requires_human_review=True
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_visual_format_result( validation: GovernmentWarningValidation ) -> LabelCheckResult'
			Logger( ).write( error )
			return self.create_unavailable_result(
				rule_id=RULE_GOVERNMENT_WARNING_VISUAL_FORMAT,
				message='Government warning visual-format result could not be created.'
			)
	
	def create_results( self, text: str ) -> List[ LabelCheckResult ]:
		"""Create all government-warning rule results for label text.

		This method validates the supplied OCR text once and then creates the government-warning
		presence, exact-text, prefix-capitalization, and visual-format rule results from the same
		validation outcome. Reusing one validation object keeps warning evidence and similarity
		values consistent across the related rule results.

		Args:
			text (str): Raw OCR label text.

		Returns:
			List[LabelCheckResult]: Government-warning rule results. If result creation fails, the
			exception is logged and a single unavailable-result fallback is returned.
		"""
		try:
			throw_if( 'text', text )
			
			validation = self.validate( text )
			
			return [
					self.create_presence_result( validation ),
					self.create_exact_text_result( validation ),
					self.create_prefix_caps_result( validation ),
					self.create_visual_format_result( validation )
			]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_results( text: str ) -> List[LabelCheckResult]'
			Logger( ).write( error )
			return [
					self.create_unavailable_result(
						rule_id='government_warning_validation_unavailable',
						message='Government warning validation results could not be created.'
					)
			]
	
	def create_unavailable_result( self, rule_id: str, message: str ) -> LabelCheckResult:
		"""Create a fallback result when warning validation cannot complete.

		This method builds the standard reviewer-safe fallback result used when warning
		validation or warning-result creation fails. The result is marked ``Needs Review`` with
		high severity and indicates that validation is unavailable.

		Args:
			rule_id (str): Rule identifier to assign to the fallback result.
			message (str): Reviewer-facing message explaining the unavailable result.

		Returns:
			LabelCheckResult: Fallback warning validation result. If fallback creation itself
			fails, the exception is logged and a final hardcoded unavailable result is returned.
		"""
		try:
			throw_if( 'rule_id', rule_id )
			throw_if( 'message', message )
			
			return LabelCheckResult(
				rule_id=rule_id,
				field_name=FIELD_GOVERNMENT_WARNING,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Government warning validation',
				observed='Validation unavailable',
				confidence=0.0,
				evidence='',
				message=message,
				requires_human_review=True
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_unavailable_result( rule_id: str, message: str ) -> LabelCheckResult'
			Logger( ).write( error )
			return LabelCheckResult( rule_id='government_warning_validation_unavailable',
				field_name=FIELD_GOVERNMENT_WARNING, status=STATUS_REVIEW,
				severity=SEVERITY_HIGH, expected='Government warning validation',
				observed='Validation unavailable', confidence=0.0, evidence='',
				message='Government warning validation could not be completed.',
				requires_human_review=True )