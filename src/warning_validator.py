'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                warning_validator.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-06-2026
    ******************************************************************************************
    <copyright file="warning_validator.py" company="Terry D. Eppler">

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
        Provides deterministic government-warning validation for the Fiddy label verification
        workflow.

        This module validates government-warning presence, all-caps prefix formatting, strict
        standard warning wording, near-match review conditions, extracted warning context, and
        visual-format review requirements that cannot be proven from OCR text alone.

        The validator enforces exact warning wording through normalized text containment and
        treats near matches as failures for the exact-text rule. It deliberately does not claim
        that OCR can prove boldness, font size, visual prominence, contrast, or whether the
        warning is hidden. Those visual-format requirements are surfaced as mandatory reviewer
        confirmation items.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import re
from typing import Dict, List, Optional

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
	SEVERITY_MEDIUM,
	STATUS_FAIL,
	STATUS_PASS,
	STATUS_REVIEW,
	STATUS_WARNING
)
from src.models import LabelCheckResult
from src.normalizer import TextNormalizer

class GovernmentWarningVisualEvidence( BaseModel ):
	"""Represents visual-format evidence for the government warning.

	Purpose:
		Store reviewer-facing visual-format evidence for the mandatory government warning. OCR
		text can help identify whether warning language appears to exist, but it cannot prove
		boldness, minimum readable size, label placement, contrast, visual prominence, or whether
		the warning is hidden. This model records that boundary explicitly so downstream reports
		and acceptance checks can distinguish text validation from visual-format confirmation.

	Attributes:
		warning_text_detected (bool): Indicates whether warning text was detected by OCR.
		visual_format_verified (bool): Indicates whether the visual format was automatically
			verified. This prototype leaves the value false because OCR text is insufficient.
		visual_review_required (bool): Indicates whether reviewer visual confirmation is required.
		risk_level (str): Reviewer-facing visual-risk level.
		image_quality_notes (List[str]): Optional OCR or image-quality notes that increase visual
			review concern.
		reviewer_instruction (str): Plain-language instruction for the reviewer.
	"""
	
	warning_text_detected: bool = Field( default=False )
	visual_format_verified: bool = Field( default=False )
	visual_review_required: bool = Field( default=True )
	risk_level: str = Field( default=SEVERITY_MEDIUM )
	image_quality_notes: List[ str ] = Field( default_factory=list )
	reviewer_instruction: str = Field( default='' )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert the visual evidence model into a flat record.

		Purpose:
			Create a dictionary suitable for Streamlit display, pandas DataFrame construction,
			CSV export, JSON export, and stakeholder acceptance evidence.

		Returns:
			Dict[str, object]: Flat visual evidence record. If rendering fails, a conservative
			fallback record is returned.
		"""
		try:
			return {
					'Warning Text Detected': self.warning_text_detected,
					'Visual Format Verified': self.visual_format_verified,
					'Visual Review Required': self.visual_review_required,
					'Risk Level': self.risk_level,
					'Image Quality Notes': '; '.join( self.image_quality_notes ),
					'Reviewer Instruction': self.reviewer_instruction
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Warning Text Detected': False,
					'Visual Format Verified': False,
					'Visual Review Required': True,
					'Risk Level': SEVERITY_HIGH,
					'Image Quality Notes': '',
					'Reviewer Instruction': 'Government-warning visual evidence could not be rendered.'
			}

class GovernmentWarningValidation( BaseModel ):
	"""Represents the complete government-warning validation outcome for one label.

	Purpose:
		Store the intermediate and final determinations used by government-warning rule-result
		creation. The model records whether warning text appears to be present, whether a warning
		prefix was detected in any case, whether the required all-caps prefix appears, whether the
		standard warning text matches exactly after strict normalization, whether text is a near
		match requiring review, the similarity score, extracted warning context, visual-format
		evidence, and reviewer-facing validation messages.

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
		visual_format_verified (bool): Indicates whether visual formatting was automatically
			verified.
		visual_format_review_required (bool): Indicates whether visual review is required.
		visual_evidence (GovernmentWarningVisualEvidence): Structured visual-format evidence.
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
	visual_evidence: GovernmentWarningVisualEvidence = Field(
		default_factory=GovernmentWarningVisualEvidence )
	warning_context: str = Field( default='' )
	messages: List[ str ] = Field( default_factory=list )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert the government-warning validation outcome into a flat record.

		Purpose:
			Convert validation flags, similarity score, warning context, visual-format evidence,
			and validation messages into a dictionary suitable for Streamlit tables, pandas
			DataFrames, CSV export, JSON export, or report-writing workflows.

		Returns:
			Dict[str, object]: Flat warning validation record. If conversion fails, the exception
			is logged and a conservative fallback record is returned.
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
					'Visual Risk Level': self.visual_evidence.risk_level,
					'Warning Context': self.warning_context,
					'Messages': '; '.join( self.messages ),
					'Reviewer Instruction': self.visual_evidence.reviewer_instruction
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( self ) -> Dict[str, object]'
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
					'Visual Risk Level': SEVERITY_HIGH,
					'Warning Context': '',
					'Messages': 'Warning validation record could not be rendered.',
					'Reviewer Instruction': 'Review the government warning manually.'
			}

class GovernmentWarningValidator( ):
	"""Validates mandatory government-warning text and related review conditions.

	Purpose:
		Perform deterministic validation of the mandatory government warning statement. The
		validator checks whether a government-warning prefix is present, whether the prefix
		appears in the required all-caps form, whether normalized OCR text contains the complete
		standard warning text, whether similar but non-exact text requires reviewer attention,
		and whether visual-format review is required.

		Near matches are treated as failures for the exact-text rule because the warning wording
		requirement is strict. Near-match state is retained only to provide useful reviewer
		evidence and distinguish likely OCR or wording variation from complete absence.

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

		Purpose:
			Create the text normalizer and store the similarity thresholds used by warning
			validation. The exact threshold is retained for configuration transparency, while the
			current exact-text rule is based on containment of the normalized required warning
			text. The near threshold identifies non-exact warning text that is close enough to
			require reviewer attention.

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

		Purpose:
			Expose the exact-match similarity threshold retained by the validator for
			configuration transparency and diagnostic reporting.

		Returns:
			float: Exact-match threshold stored on this validator instance.
		"""
		return self._exact_threshold
	
	@property
	def near_threshold( self ) -> float:
		"""Return the configured near-match similarity threshold.

		Purpose:
			Expose the near-match similarity threshold used to identify warning text that is
			similar enough to require reviewer attention but not exact enough to pass.

		Returns:
			float: Near-match threshold stored on this validator instance.
		"""
		return self._near_threshold
	
	def get_warning_context( self, text: str, window: int = 420 ) -> str:
		"""Extract the likely government-warning text span from OCR text.

		Purpose:
			Search for the government-warning prefix using case-insensitive matching. When the
			prefix is found, return a bounded text span starting at the prefix and continuing for
			the configured window length. The context is used as evidence in warning rule results
			so reviewers can inspect the OCR text surrounding the warning.

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
			error.method = 'get_warning_context( self, *args ) -> str'
			Logger( ).write( error )
			return ''
	
	def has_warning_prefix( self, text: str ) -> bool:
		"""Determine whether OCR text contains a government-warning prefix in any case.

		Purpose:
			Perform a case-insensitive search for ``government warning:`` with flexible
			whitespace before the colon. This identifies whether warning language begins with the
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

		Purpose:
			Search raw OCR text for ``GOVERNMENT WARNING:`` with flexible whitespace before the
			colon. The method intentionally does not normalize case because capitalization is the
			requirement being checked.

		Args:
			text (str): Raw OCR label text.

		Returns:
			bool: ``True`` when the all-caps prefix is present; otherwise, ``False``. If the
			check fails, the exception is logged and ``False`` is returned.
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

		Purpose:
			Normalize the supplied OCR text using strict government-warning normalization and
			check whether the normalized required warning text is contained within the normalized
			OCR value. This supports strict wording validation while reducing false negatives from
			punctuation, line breaks, and OCR formatting artifacts.

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

		Purpose:
			Normalize the supplied OCR text for strict warning comparison, then use
			``rapidfuzz.fuzz.partial_ratio`` to compare the normalized standard warning text to
			the normalized OCR text. The score identifies near-match text that should be reviewed
			but must not pass exact-text validation.

		Args:
			text (str): Raw OCR label text.

		Returns:
			float: Similarity score from ``0.0`` to ``100.0``. If similarity cannot be
			calculated, the exception is logged and ``0.0`` is returned.
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
	
	def create_visual_evidence( self, validation: GovernmentWarningValidation,
			image_quality_notes: Optional[
				List[ str ] ] = None ) -> GovernmentWarningVisualEvidence:
		"""Create structured visual-format evidence for the government warning.

		Purpose:
			Build a visual-format evidence model from warning validation state and optional image
			quality notes. The method always requires reviewer confirmation because OCR text alone
			cannot prove boldness, readable font size, contrast, placement, or hidden-label
			conditions.

		Args:
			validation (GovernmentWarningValidation): Current warning validation state.
			image_quality_notes (Optional[List[str]]): Optional image-quality notes from OCR or
				preprocessing.

		Returns:
			GovernmentWarningVisualEvidence: Structured visual-format evidence. If creation
			fails, a conservative high-risk visual evidence record is returned.
		"""
		try:
			throw_if( 'validation', validation )
			
			notes = image_quality_notes or [ ]
			risk_level = SEVERITY_HIGH if notes or not validation.text_present else SEVERITY_MEDIUM
			
			if validation.text_present:
				instruction = (
						'Confirm visually that the government warning is present, bold where required, '
						'readable, prominent, sufficiently contrasted, and not hidden or obscured.'
				)
			else:
				instruction = (
						'Inspect the label artwork manually because warning text was not detected by OCR '
						'and visual formatting cannot be evaluated automatically.'
				)
			
			return GovernmentWarningVisualEvidence(
				warning_text_detected=validation.text_present,
				visual_format_verified=False,
				visual_review_required=True,
				risk_level=risk_level,
				image_quality_notes=notes,
				reviewer_instruction=instruction
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_visual_evidence( self, *args ) -> GovernmentWarningVisualEvidence'
			Logger( ).write( error )
			return GovernmentWarningVisualEvidence(
				warning_text_detected=False,
				visual_format_verified=False,
				visual_review_required=True,
				risk_level=SEVERITY_HIGH,
				image_quality_notes=[ ],
				reviewer_instruction='Review the government warning manually.'
			)
	
	def validate( self, text: str,
			image_quality_notes: Optional[ List[ str ] ] = None ) -> GovernmentWarningValidation:
		"""Validate government-warning text and visual-format review requirements.

		Purpose:
			Perform the full government-warning validation workflow. The method extracts warning
			context, checks prefix presence, checks all-caps prefix presence, checks exact
			normalized standard-warning text, calculates similarity, identifies near matches,
			determines whether warning text is present, creates reviewer-facing validation
			messages, and attaches visual-format evidence. It always marks visual-format review as
			required because OCR text cannot prove visual properties such as boldness, minimum
			font size, contrast, prominence, or hidden placement.

		Args:
			text (str): Raw OCR label text.
			image_quality_notes (Optional[List[str]]): Optional image-quality notes from OCR or
				preprocessing.

		Returns:
			GovernmentWarningValidation: Structured warning validation outcome. If validation
			fails, the exception is logged and a reviewer-safe fallback validation object is
			returned.
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
					'Government warning text is similar to the standard warning but fails the '
					'exact-text requirement and requires reviewer confirmation.'
				)
			else:
				messages.append( 'Standard government warning text was not detected.' )
			
			messages.append(
				'OCR text checks cannot verify boldness, readable size, contrast, prominence, '
				'or whether the warning is visually hidden; reviewer visual confirmation is required.'
			)
			
			validation = GovernmentWarningValidation(
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
			validation.visual_evidence = self.create_visual_evidence(
				validation,
				image_quality_notes=image_quality_notes
			)
			
			return validation
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'validate( self, *args ) -> GovernmentWarningValidation'
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
				visual_evidence=GovernmentWarningVisualEvidence(
					warning_text_detected=False,
					visual_format_verified=False,
					visual_review_required=True,
					risk_level=SEVERITY_HIGH,
					image_quality_notes=[ ],
					reviewer_instruction='Government warning validation could not be completed; review manually.'
				),
				warning_context='',
				messages=[
						'Government warning validation could not be completed.'
				]
			)
	
	def create_unavailable_result( self, rule_id: str, message: str ) -> LabelCheckResult:
		"""Create a fallback result for unavailable warning validation output.

		Purpose:
			Return a conservative ``Needs Review`` result when a warning rule cannot create its
			normal result. The fallback preserves the rule identifier, assigns high severity, and
			requires human review.

		Args:
			rule_id (str): Rule identifier that could not be evaluated normally.
			message (str): Reviewer-facing fallback message.

		Returns:
			LabelCheckResult: Conservative fallback warning result.
		"""
		try:
			throw_if( 'rule_id', rule_id )
			throw_if( 'message', message )
			
			return LabelCheckResult(
				rule_id=rule_id,
				field_name=FIELD_GOVERNMENT_WARNING,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Executable government-warning validation',
				observed='Government-warning validation unavailable',
				confidence=0.0,
				evidence='',
				message=message,
				requires_human_review=True
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_unavailable_result( self, *args ) -> LabelCheckResult'
			Logger( ).write( error )
			return LabelCheckResult(
				rule_id='government_warning_validation_unavailable',
				field_name=FIELD_GOVERNMENT_WARNING,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Executable government-warning validation',
				observed='Government-warning validation unavailable',
				confidence=0.0,
				evidence='',
				message='Government-warning validation could not be completed.',
				requires_human_review=True
			)
	
	def create_presence_result( self, validation: GovernmentWarningValidation ) -> LabelCheckResult:
		"""Create a rule result for government-warning presence.

		Purpose:
			Convert the structured validation outcome into the presence rule result. A present
			warning passes, while missing warning language fails and requires human review. The
			extracted warning context is preserved as evidence.

		Args:
			validation (GovernmentWarningValidation): Warning validation outcome.

		Returns:
			LabelCheckResult: Warning presence rule result. If result creation fails, a
			conservative unavailable-result fallback is returned.
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
			error.method = 'create_presence_result( self, *args ) -> LabelCheckResult'
			Logger( ).write( error )
			return self.create_unavailable_result(
				rule_id=RULE_GOVERNMENT_WARNING_PRESENT,
				message='Government warning presence result could not be created.'
			)
	
	def create_prefix_caps_result( self,
			validation: GovernmentWarningValidation ) -> LabelCheckResult:
		"""Create a rule result for the all-caps government-warning prefix.

		Purpose:
			Convert the structured validation outcome into the prefix-capitalization rule result.
			The result passes only when ``GOVERNMENT WARNING:`` appears in the required all-caps
			form. Any other condition fails and requires human review.

		Args:
			validation (GovernmentWarningValidation): Warning validation outcome.

		Returns:
			LabelCheckResult: Warning prefix capitalization result. If result creation fails, a
			conservative unavailable-result fallback is returned.
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
			error.method = 'create_prefix_caps_result( self, *args ) -> LabelCheckResult'
			Logger( ).write( error )
			return self.create_unavailable_result(
				rule_id=RULE_GOVERNMENT_WARNING_PREFIX_CAPS,
				message='Government warning prefix result could not be created.'
			)
	
	def create_exact_text_result( self,
			validation: GovernmentWarningValidation ) -> LabelCheckResult:
		"""Create a strict rule result for exact government-warning text.

		Purpose:
			Create the exact-text rule result from the structured validation outcome. The result
			passes only when normalized OCR text contains the normalized required warning text.
			Near-match text fails because the warning wording requirement is exact; the near-match
			state is used only to support reviewer attention and evidence.

		Args:
			validation (GovernmentWarningValidation): Warning validation outcome.

		Returns:
			LabelCheckResult: Exact warning text rule result. If result creation fails, a
			conservative unavailable-result fallback is returned.
		"""
		try:
			throw_if( 'validation', validation )
			status = STATUS_PASS if validation.exact_text_match else STATUS_FAIL
			if validation.exact_text_match:
				severity = SEVERITY_INFO
				observed = 'Exact standard warning text detected'
				message = 'The standard government warning text was detected exactly after strict normalization.'
				requires_review = False
				confidence = 100.0
			elif validation.near_text_match:
				severity = SEVERITY_HIGH
				observed = 'Near match detected but exact text requirement failed'
				message = (
						'Government warning text is similar to the required standard warning, but the '
						'exact-text rule fails because the wording requirement is strict.'
				)
				requires_review = True
				confidence = validation.normalized_similarity
			else:
				severity = SEVERITY_HIGH
				observed = 'Standard warning text not detected'
				message = 'The exact standard government warning text was not detected.'
				requires_review = True
				confidence = validation.normalized_similarity
			
			return LabelCheckResult( rule_id=RULE_GOVERNMENT_WARNING_EXACT,
				field_name=FIELD_GOVERNMENT_WARNING,
				status=status,
				severity=severity,
				expected=GOVERNMENT_WARNING_TEXT,
				observed=observed,
				confidence=confidence,
				evidence=validation.warning_context,
				message=message,
				requires_human_review=requires_review )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_exact_text_result( self, *args ) -> LabelCheckResult'
			Logger( ).write( error )
			return self.create_unavailable_result(
				rule_id=RULE_GOVERNMENT_WARNING_EXACT,
				message='Government warning exact-text result could not be created.'
			)
	
	def create_visual_format_result( self,
			validation: GovernmentWarningValidation ) -> LabelCheckResult:
		"""Create a rule result for government-warning visual-format review.

		Purpose:
			Create the visual-format rule result that tells reviewers what must be visually
			confirmed. OCR text can support presence and wording checks, but it cannot reliably
			prove required visual presentation such as boldness, readable size, contrast,
			prominence, placement, or whether the warning is hidden. For that reason, this method
			always returns a human-review result rather than an automated pass.

		Args:
			validation (GovernmentWarningValidation): Warning validation outcome.

		Returns:
			LabelCheckResult: Visual-format review result. If result creation fails, a
			conservative unavailable-result fallback is returned.
		"""
		try:
			throw_if( 'validation', validation )
			
			if validation.text_present:
				severity = validation.visual_evidence.risk_level
				observed = 'Warning text detected; visual formatting requires human confirmation'
				message = validation.visual_evidence.reviewer_instruction
			else:
				severity = SEVERITY_HIGH
				observed = 'Warning text not detected; visual formatting cannot be evaluated'
				message = (
						'Government warning visual formatting cannot be evaluated because the warning '
						'text was not detected. Reviewer must inspect the label artwork manually.'
				)
			
			return LabelCheckResult(
				rule_id=RULE_GOVERNMENT_WARNING_VISUAL_FORMAT,
				field_name=FIELD_GOVERNMENT_WARNING,
				status=STATUS_REVIEW,
				severity=severity,
				expected='Reviewer confirmation of warning boldness, readability, contrast, prominence, and visibility',
				observed=observed,
				confidence=0.0,
				evidence=validation.warning_context,
				message=message,
				requires_human_review=True
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_visual_format_result( self, *args ) -> LabelCheckResult'
			Logger( ).write( error )
			return self.create_unavailable_result(
				rule_id=RULE_GOVERNMENT_WARNING_VISUAL_FORMAT,
				message='Government warning visual-format result could not be created.'
			)
	
	def create_results( self, text: str,
			image_quality_notes: Optional[ List[ str ] ] = None ) -> List[ LabelCheckResult ]:
		"""Create all government-warning rule results for label text.

		Purpose:
			Validate supplied OCR text once and create the government-warning presence,
			exact-text, prefix-capitalization, and visual-format rule results from the same
			validation outcome. Reusing one validation object keeps warning evidence and
			similarity values consistent across related rule results.

		Args:
			text (str): Raw OCR label text.
			image_quality_notes (Optional[List[str]]): Optional image-quality notes from OCR or
				preprocessing.

		Returns:
			List[LabelCheckResult]: Government-warning rule results. If result creation fails, a
			single unavailable-result fallback is returned.
		"""
		try:
			throw_if( 'text', text )
			
			validation = self.validate( text, image_quality_notes=image_quality_notes )
			
			return [ self.create_presence_result( validation ),
					self.create_exact_text_result( validation ),
					self.create_prefix_caps_result( validation ),
					self.create_visual_format_result( validation ) ]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_results( self, *args ) -> List[LabelCheckResult]'
			Logger( ).write( error )
			return [
					self.create_unavailable_result(
						rule_id='government_warning_validation_unavailable',
						message='Government warning validation results could not be created.'
					)
			]