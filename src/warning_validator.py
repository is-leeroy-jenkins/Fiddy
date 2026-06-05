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
        warning_validator.py
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import re
from typing import Dict, List

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

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
	"""
	Purpose:
	--------
	Represent the complete government-warning validation outcome for one label.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
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
		"""
		Purpose:
		--------
		Convert the government-warning validation outcome into a flat record.

		Parameters:
		-----------
		None

		Returns:
		--------
		Dict[str, object]: Flat warning validation record.
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
		except Exception:
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
	"""
	Purpose:
	--------
	Validate the mandatory government warning statement using strict text checks and
	reviewer-facing visual-format safeguards.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
	"""
	
	_text: str
	_normalized_text: str
	_warning_context: str
	_normalizer: TextNormalizer
	_exact_threshold: float
	_near_threshold: float
	
	def __init__( self, exact_threshold: float = 100.0, near_threshold: float = 92.0 ) -> None:
		"""
		Purpose:
		--------
		Initialize the government warning validator.

		Parameters:
		-----------
		exact_threshold (float): Similarity score required for exact-match classification.
		near_threshold (float): Similarity score required for near-match human review.

		Returns:
		--------
		None
		"""
		self._normalizer = TextNormalizer( )
		self._exact_threshold = exact_threshold
		self._near_threshold = near_threshold
	
	@property
	def exact_threshold( self ) -> float:
		"""
		Purpose:
		--------
		Return the configured exact-match similarity threshold.

		Parameters:
		-----------
		None

		Returns:
		--------
		float: Exact-match threshold.
		"""
		return self._exact_threshold
	
	@property
	def near_threshold( self ) -> float:
		"""
		Purpose:
		--------
		Return the configured near-match similarity threshold.

		Parameters:
		-----------
		None

		Returns:
		--------
		float: Near-match threshold.
		"""
		return self._near_threshold
	
	def get_warning_context( self, text: str, window: int = 420 ) -> str:
		"""
		Purpose:
		--------
		Extract the likely government warning text span from OCR text.

		Parameters:
		-----------
		text (str): Raw OCR label text.
		window (int): Maximum number of characters to return after the warning prefix.

		Returns:
		--------
		str: Extracted warning context, or empty string when unavailable.
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
		except Exception:
			return ''
	
	def has_warning_prefix( self, text: str ) -> bool:
		"""
		Purpose:
		--------
		Determine whether OCR text contains a government-warning prefix in any case.

		Parameters:
		-----------
		text (str): Raw OCR label text.

		Returns:
		--------
		bool: True when a government-warning prefix is present; otherwise, False.
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
		except Exception:
			return False
	
	def has_all_caps_prefix( self, text: str ) -> bool:
		"""
		Purpose:
		--------
		Determine whether OCR text contains the required all-caps GOVERNMENT WARNING: prefix.

		Parameters:
		-----------
		text (str): Raw OCR label text.

		Returns:
		--------
		bool: True when the all-caps prefix is present; otherwise, False.
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
		except Exception:
			return False
	
	def has_standard_warning_text( self, text: str ) -> bool:
		"""
		Purpose:
		--------
		Determine whether normalized OCR text contains the complete standard warning text.

		Parameters:
		-----------
		text (str): Raw OCR label text.

		Returns:
		--------
		bool: True when the full normalized warning text is contained; otherwise, False.
		"""
		try:
			throw_if( 'text', text )
			
			self._normalized_text = self._normalizer.normalize_for_strict_warning( text )
			return GOVERNMENT_WARNING_TEXT_NORMALIZED in self._normalized_text
		except Exception:
			return False
	
	def calculate_warning_similarity( self, text: str ) -> float:
		"""
		Purpose:
		--------
		Calculate similarity between normalized OCR text and the standard warning text.

		Parameters:
		-----------
		text (str): Raw OCR label text.

		Returns:
		--------
		float: Similarity score from 0.0 to 100.0.
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
		except Exception:
			return 0.0
	
	def validate( self, text: str ) -> GovernmentWarningValidation:
		"""
		Purpose:
		--------
		Validate government warning presence, capitalization, exact wording, near-match
		behavior, and visual-format review requirements.

		Parameters:
		-----------
		text (str): Raw OCR label text.

		Returns:
		--------
		GovernmentWarningValidation: Structured warning validation outcome.
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
		except Exception:
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
		"""
		Purpose:
		--------
		Create a rule result for government warning presence.

		Parameters:
		-----------
		validation (GovernmentWarningValidation): Warning validation outcome.

		Returns:
		--------
		LabelCheckResult: Warning presence rule result.
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
		except Exception:
			return self.create_unavailable_result(
				rule_id=RULE_GOVERNMENT_WARNING_PRESENT,
				message='Government warning presence result could not be created.'
			)
	
	def create_prefix_caps_result( self,
			validation: GovernmentWarningValidation ) -> LabelCheckResult:
		"""
		Purpose:
		--------
		Create a rule result for the all-caps government warning prefix.

		Parameters:
		-----------
		validation (GovernmentWarningValidation): Warning validation outcome.

		Returns:
		--------
		LabelCheckResult: Warning prefix capitalization result.
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
		except Exception:
			return self.create_unavailable_result(
				rule_id=RULE_GOVERNMENT_WARNING_PREFIX_CAPS,
				message='Government warning prefix result could not be created.'
			)
	
	def create_exact_text_result( self,
			validation: GovernmentWarningValidation ) -> LabelCheckResult:
		"""
		
			Purpose:
			--------
			Create a strict rule result for exact government warning text. Near-match warning text
			does not pass because the stakeholder requirement requires exact wording.
		
			Parameters:
			-----------
			validation (GovernmentWarningValidation): Warning validation outcome.
		
			Returns:
			--------
			LabelCheckResult: Exact warning text rule result.
		
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
		except Exception:
			return self.create_unavailable_result(
				rule_id=RULE_GOVERNMENT_WARNING_EXACT,
				message='Government warning exact-text result could not be created.'
			)
	
	def create_visual_format_result( self,
			validation: GovernmentWarningValidation ) -> LabelCheckResult:
		"""
		
			Purpose:
			--------
			Create a government-warning visual-format result. OCR text can support wording checks,
			but it cannot prove boldness, minimum font size, contrast, or whether the warning is
			visually hidden. This rule therefore produces a human-review item rather than an
			automated pass.
		
			Parameters:
			-----------
			validation (GovernmentWarningValidation): Warning validation outcome.
		
			Returns:
			--------
			LabelCheckResult: Visual-format review result.
			
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
		except Exception:
			return self.create_unavailable_result(
				rule_id=RULE_GOVERNMENT_WARNING_VISUAL_FORMAT,
				message='Government warning visual-format result could not be created.'
			)
	
	def create_results( self, text: str ) -> List[ LabelCheckResult ]:
		"""
			Purpose:
			--------
			Create all government-warning rule results for a label text.
	
			Parameters:
			-----------
			text (str): Raw OCR label text.
	
			Returns:
			--------
			List[LabelCheckResult]: Government-warning rule results.
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
		except Exception:
			return [
					self.create_unavailable_result(
						rule_id='government_warning_validation_unavailable',
						message='Government warning validation results could not be created.'
					)
			]
	
	def create_unavailable_result( self, rule_id: str, message: str ) -> LabelCheckResult:
		"""
		Purpose:
		--------
		Create a fallback result when warning validation cannot complete.

		Parameters:
		-----------
		rule_id (str): Rule identifier.
		message (str): Reviewer-facing message.

		Returns:
		--------
		LabelCheckResult: Fallback warning validation result.
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
		except Exception:
			return LabelCheckResult(
				rule_id='government_warning_validation_unavailable',
				field_name=FIELD_GOVERNMENT_WARNING,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Government warning validation',
				observed='Validation unavailable',
				confidence=0.0,
				evidence='',
				message='Government warning validation could not be completed.',
				requires_human_review=True
			)
