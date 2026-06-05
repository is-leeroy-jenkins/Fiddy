'''
    ******************************************************************************************
      Assembly:                Veritas
      Filename:                label_rules.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="label_rules.py" company="Terry D. Eppler">

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
        label_rules.py
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import re
from typing import List, Optional

from rapidfuzz import fuzz

from config import (
	BRAND_MATCH_THRESHOLD,
	CLASS_TYPE_MATCH_THRESHOLD,
	LOW_CONFIDENCE_THRESHOLD,
	throw_if
)

from src.constants import (
	ABV_PATTERN,
	BEVERAGE_TYPE_DISTILLED_SPIRITS,
	COUNTRY_OF_ORIGIN_PATTERN,
	DEFAULT_ABV_TOLERANCE,
	DEFAULT_PROOF_TOLERANCE,
	DEFAULT_WARNING_MATCH_THRESHOLD,
	FIELD_ALCOHOL_CONTENT,
	FIELD_BRAND_NAME,
	FIELD_CLASS_TYPE,
	FIELD_COUNTRY_OF_ORIGIN,
	FIELD_GOVERNMENT_WARNING,
	FIELD_IMPORTER,
	FIELD_NET_CONTENTS,
	FIELD_PRODUCER_BOTTLER,
	FIELD_PROOF,
	GOVERNMENT_WARNING_TEXT,
	GOVERNMENT_WARNING_TEXT_NORMALIZED,
	IMPORTER_PATTERN,
	NET_CONTENTS_PATTERN,
	PRODUCER_BOTTLER_PATTERN,
	PROOF_PATTERN,
	RULE_ALCOHOL_CONTENT_MATCH,
	RULE_ALCOHOL_CONTENT_PRESENT,
	RULE_BRAND_NAME_MATCH,
	RULE_CLASS_TYPE_MATCH,
	RULE_COUNTRY_OF_ORIGIN_PRESENT,
	RULE_GOVERNMENT_WARNING_EXACT,
	RULE_GOVERNMENT_WARNING_PREFIX_CAPS,
	RULE_GOVERNMENT_WARNING_PRESENT,
	RULE_GOVERNMENT_WARNING_VISUAL_FORMAT,
	RULE_IMPORTER_PRESENT,
	RULE_NET_CONTENTS_MATCH,
	RULE_NET_CONTENTS_PRESENT,
	RULE_PRODUCER_BOTTLER_PRESENT,
	RULE_PROOF_CONSISTENCY,
	RULE_PROOF_PRESENT,
	SEVERITY_HIGH,
	SEVERITY_INFO,
	SEVERITY_LOW,
	SEVERITY_MEDIUM,
	STATUS_FAIL,
	STATUS_NOT_APPLICABLE,
	STATUS_PASS,
	STATUS_REVIEW,
	STATUS_WARNING
)

from src.models import LabelApplication, LabelCheckResult
from src.normalizer import TextNormalizer

# ==========================================================================================
# Alcohol Label Rules
# ==========================================================================================

class AlcoholLabelRules( ):
	"""
	Purpose:
	--------
	Execute deterministic alcohol label verification rules against OCR-extracted label text
	and reviewer-entered application data.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
	"""
	
	_application: LabelApplication
	_text: str
	_normalized_text: str
	_expected: str
	_observed: str
	_field_name: str
	_rule_id: str
	_status: str
	_severity: str
	_confidence: float
	_evidence: str
	_message: str
	_requires_human_review: bool
	_normalizer: TextNormalizer
	
	def __init__( self ) -> None:
		"""
		Purpose:
		--------
		Initialize the alcohol label rule engine.

		Parameters:
		-----------
		None

		Returns:
		--------
		None
		"""
		self._normalizer = TextNormalizer( )
	
	def create_result( self, rule_id: str, field_name: str, status: str, severity: str,
			expected: str = '', observed: str = '', confidence: float = 0.0, evidence: str = '',
			message: str = '', requires_human_review: bool = False ) -> LabelCheckResult:
		"""
		Purpose:
		--------
		Create a structured label check result.

		Parameters:
		-----------
		rule_id (str): Machine-readable rule identifier.
		field_name (str): User-facing field name.
		status (str): Pass, Warning, Fail, Needs Review, or Not Applicable.
		severity (str): Relative severity value.
		expected (str): Expected application value or requirement.
		observed (str): Observed label value or condition.
		confidence (float): Rule confidence from 0.0 to 100.0.
		evidence (str): Extracted evidence supporting the result.
		message (str): Reviewer-facing explanation.
		requires_human_review (bool): Indicates whether human review is required.

		Returns:
		--------
		LabelCheckResult: Structured rule result.
		"""
		try:
			throw_if( 'rule_id', rule_id )
			throw_if( 'field_name', field_name )
			throw_if( 'status', status )
			throw_if( 'severity', severity )
			
			self._rule_id = rule_id
			self._field_name = field_name
			self._status = status
			self._severity = severity
			self._expected = expected
			self._observed = observed
			self._confidence = confidence
			self._evidence = evidence
			self._message = message
			self._requires_human_review = requires_human_review
			
			return LabelCheckResult(
				rule_id=self._rule_id,
				field_name=self._field_name,
				status=self._status,
				severity=self._severity,
				expected=self._expected,
				observed=self._observed,
				confidence=self._confidence,
				evidence=self._evidence,
				message=self._message,
				requires_human_review=self._requires_human_review
			)
		except Exception:
			return LabelCheckResult(
				rule_id='rule_result_unavailable',
				field_name='Rule Result',
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Valid rule result',
				observed='Result creation failed',
				confidence=0.0,
				evidence='',
				message='The verification rule could not create a result.',
				requires_human_review=True
			)
	
	def verify( self, application: LabelApplication, text: str ) -> List[ LabelCheckResult ]:
		"""
		Purpose:
		--------
		Run all applicable alcohol label verification rules.

		Parameters:
		-----------
		application (LabelApplication): Expected application values.
		text (str): Raw or normalized OCR label text.

		Returns:
		--------
		List[LabelCheckResult]: Verification rule results.
		"""
		try:
			throw_if( 'application', application )
			throw_if( 'text', text )
			
			self._application = application
			self._text = text
			self._normalized_text = self._normalizer.normalize_label_text( self._text )
			
			results = [
					self.check_brand_name( self._application, self._text ),
					self.check_class_type( self._application, self._text ),
					self.check_alcohol_content_present( self._text ),
					self.check_alcohol_content_match( self._application, self._text ),
					self.check_proof_present( self._application, self._text ),
					self.check_proof_consistency( self._application, self._text ),
					self.check_net_contents_present( self._text ),
					self.check_net_contents_match( self._application, self._text ),
					self.check_producer_bottler_present( self._text ),
					self.check_government_warning_present( self._text ),
					self.check_government_warning_exact( self._text ),
					self.check_government_warning_prefix_caps( self._text ),
					self.check_government_warning_visual_format( self._text )
			]
			
			if self._application.imported:
				results.append( self.check_importer_present( self._text ) )
				results.append(
					self.check_country_of_origin_present( self._application, self._text ) )
			
			return results
		except Exception:
			return [
					self.create_result(
						rule_id='verification_rules_unavailable',
						field_name='Verification Rules',
						status=STATUS_REVIEW,
						severity=SEVERITY_HIGH,
						expected='Executable rule set',
						observed='Rules could not be executed',
						confidence=0.0,
						evidence='',
						message='The label rule engine could not complete verification.',
						requires_human_review=True
					)
			]
	
	def check_brand_name( self, application: LabelApplication, text: str ) -> LabelCheckResult:
		"""
		Purpose:
		--------
		Compare expected brand name against OCR label text using judgment-sensitive fuzzy
		matching.

		Parameters:
		-----------
		application (LabelApplication): Expected application values.
		text (str): OCR label text.

		Returns:
		--------
		LabelCheckResult: Brand-name rule result.
		"""
		try:
			throw_if( 'application', application )
			throw_if( 'text', text )
			
			self._application = application
			self._text = text
			
			expected = self._normalizer.normalize_brand_name( self._application.brand_name )
			observed_text = self._normalizer.normalize_for_match( self._text )
			
			if not expected:
				return self.create_result(
					rule_id=RULE_BRAND_NAME_MATCH,
					field_name=FIELD_BRAND_NAME,
					status=STATUS_REVIEW,
					severity=SEVERITY_MEDIUM,
					expected='Brand name from application',
					observed='No expected brand name provided',
					confidence=0.0,
					evidence='',
					message='A brand name was not provided for comparison.',
					requires_human_review=True
				)
			
			confidence = float( fuzz.partial_ratio( expected, observed_text ) )
			status = STATUS_PASS if confidence >= BRAND_MATCH_THRESHOLD else STATUS_REVIEW
			severity = SEVERITY_INFO if status == STATUS_PASS else SEVERITY_MEDIUM
			message = (
					'Brand name appears to match the label text.'
					if status == STATUS_PASS
					else 'Brand name does not clearly match and requires reviewer judgment.'
			)
			
			return self.create_result(
				rule_id=RULE_BRAND_NAME_MATCH,
				field_name=FIELD_BRAND_NAME,
				status=status,
				severity=severity,
				expected=self._application.brand_name,
				observed='Found in label text' if status == STATUS_PASS else 'Not clearly found',
				confidence=confidence,
				evidence=self._normalizer.extract_context( self._text,
					self._application.brand_name ),
				message=message,
				requires_human_review=status != STATUS_PASS
			)
		except Exception:
			return self.create_result(
				rule_id=RULE_BRAND_NAME_MATCH,
				field_name=FIELD_BRAND_NAME,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Brand name comparison',
				observed='Rule execution failed',
				confidence=0.0,
				evidence='',
				message='Brand-name verification could not be completed.',
				requires_human_review=True
			)
	
	def check_class_type( self, application: LabelApplication, text: str ) -> LabelCheckResult:
		"""
		Purpose:
		--------
		Compare expected class or type designation against OCR label text.

		Parameters:
		-----------
		application (LabelApplication): Expected application values.
		text (str): OCR label text.

		Returns:
		--------
		LabelCheckResult: Class/type rule result.
		"""
		try:
			throw_if( 'application', application )
			throw_if( 'text', text )
			
			self._application = application
			self._text = text
			
			expected = self._normalizer.normalize_class_type( self._application.class_type )
			observed_text = self._normalizer.normalize_for_match( self._text )
			
			if not expected:
				return self.create_result(
					rule_id=RULE_CLASS_TYPE_MATCH,
					field_name=FIELD_CLASS_TYPE,
					status=STATUS_REVIEW,
					severity=SEVERITY_MEDIUM,
					expected='Class/type designation from application',
					observed='No expected class/type provided',
					confidence=0.0,
					evidence='',
					message='A class/type designation was not provided for comparison.',
					requires_human_review=True
				)
			
			confidence = float( fuzz.partial_ratio( expected, observed_text ) )
			status = STATUS_PASS if confidence >= CLASS_TYPE_MATCH_THRESHOLD else STATUS_REVIEW
			severity = SEVERITY_INFO if status == STATUS_PASS else SEVERITY_MEDIUM
			message = (
					'Class/type designation appears to match the label text.'
					if status == STATUS_PASS
					else 'Class/type designation does not clearly match and requires review.'
			)
			
			return self.create_result(
				rule_id=RULE_CLASS_TYPE_MATCH,
				field_name=FIELD_CLASS_TYPE,
				status=status,
				severity=severity,
				expected=self._application.class_type,
				observed='Found in label text' if status == STATUS_PASS else 'Not clearly found',
				confidence=confidence,
				evidence=self._normalizer.extract_context( self._text,
					self._application.class_type ),
				message=message,
				requires_human_review=status != STATUS_PASS
			)
		except Exception:
			return self.create_result(
				rule_id=RULE_CLASS_TYPE_MATCH,
				field_name=FIELD_CLASS_TYPE,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Class/type comparison',
				observed='Rule execution failed',
				confidence=0.0,
				evidence='',
				message='Class/type verification could not be completed.',
				requires_human_review=True
			)
	
	def extract_abv( self, text: str ) -> Optional[ float ]:
		"""
		Purpose:
		--------
		Extract an ABV value from label text.

		Parameters:
		-----------
		text (str): OCR label text.

		Returns:
		--------
		Optional[float]: Extracted ABV value, or None when unavailable.
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			match = re.search( ABV_PATTERN, self._text, flags=re.IGNORECASE )
			
			if not match:
				return None
			
			value = match.group( 'abv' )
			return self._normalizer.normalize_abv_value( value )
		except Exception:
			return None
	
	def extract_proof( self, text: str ) -> Optional[ float ]:
		"""
		Purpose:
		--------
		Extract a proof value from label text.

		Parameters:
		-----------
		text (str): OCR label text.

		Returns:
		--------
		Optional[float]: Extracted proof value, or None when unavailable.
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			match = re.search( PROOF_PATTERN, self._text, flags=re.IGNORECASE )
			
			if not match:
				return None
			
			value = match.group( 'proof' )
			return self._normalizer.normalize_proof_value( value )
		except Exception:
			return None
	
	def extract_net_contents( self, text: str ) -> str:
		"""
		Purpose:
		--------
		Extract net contents text from label text.

		Parameters:
		-----------
		text (str): OCR label text.

		Returns:
		--------
		str: Extracted net contents value, or empty string when unavailable.
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			match = re.search( NET_CONTENTS_PATTERN, self._text, flags=re.IGNORECASE )
			
			if not match:
				return ''
			
			amount = match.group( 'amount' )
			unit = match.group( 'unit' )
			return self._normalizer.normalize_net_contents( f'{amount} {unit}' )
		except Exception:
			return ''
	
	def check_alcohol_content_present( self, text: str ) -> LabelCheckResult:
		"""
		Purpose:
		--------
		Determine whether the label contains an alcohol-content statement.

		Parameters:
		-----------
		text (str): OCR label text.

		Returns:
		--------
		LabelCheckResult: Alcohol-content presence rule result.
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			observed_abv = self.extract_abv( self._text )
			
			if observed_abv is None:
				return self.create_result(
					rule_id=RULE_ALCOHOL_CONTENT_PRESENT,
					field_name=FIELD_ALCOHOL_CONTENT,
					status=STATUS_FAIL,
					severity=SEVERITY_HIGH,
					expected='Alcohol content statement',
					observed='Not found',
					confidence=90.0,
					evidence='',
					message='Alcohol content was not detected in the label text.',
					requires_human_review=True
				)
			
			return self.create_result(
				rule_id=RULE_ALCOHOL_CONTENT_PRESENT,
				field_name=FIELD_ALCOHOL_CONTENT,
				status=STATUS_PASS,
				severity=SEVERITY_INFO,
				expected='Alcohol content statement',
				observed=f'{observed_abv:g}% ABV',
				confidence=95.0,
				evidence=f'{observed_abv:g}% ABV',
				message='Alcohol content was detected in the label text.',
				requires_human_review=False
			)
		except Exception:
			return self.create_result(
				rule_id=RULE_ALCOHOL_CONTENT_PRESENT,
				field_name=FIELD_ALCOHOL_CONTENT,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Alcohol content statement',
				observed='Rule execution failed',
				confidence=0.0,
				evidence='',
				message='Alcohol-content presence verification could not be completed.',
				requires_human_review=True
			)
	
	def check_alcohol_content_match( self, application: LabelApplication,
			text: str ) -> LabelCheckResult:
		"""
		Purpose:
		--------
		Compare expected application ABV against the ABV detected on the label.

		Parameters:
		-----------
		application (LabelApplication): Expected application values.
		text (str): OCR label text.

		Returns:
		--------
		LabelCheckResult: Alcohol-content match rule result.
		"""
		try:
			throw_if( 'application', application )
			throw_if( 'text', text )
			
			self._application = application
			self._text = text
			
			expected_abv = self._normalizer.normalize_abv_value( self._application.alcohol_content )
			observed_abv = self.extract_abv( self._text )
			
			if expected_abv is None:
				return self.create_result(
					rule_id=RULE_ALCOHOL_CONTENT_MATCH,
					field_name=FIELD_ALCOHOL_CONTENT,
					status=STATUS_REVIEW,
					severity=SEVERITY_MEDIUM,
					expected='Expected ABV from application',
					observed='No expected ABV provided',
					confidence=0.0,
					evidence='',
					message='Expected alcohol content was not provided for comparison.',
					requires_human_review=True
				)
			
			if observed_abv is None:
				return self.create_result(
					rule_id=RULE_ALCOHOL_CONTENT_MATCH,
					field_name=FIELD_ALCOHOL_CONTENT,
					status=STATUS_FAIL,
					severity=SEVERITY_HIGH,
					expected=f'{expected_abv:g}% ABV',
					observed='Not found',
					confidence=90.0,
					evidence='',
					message='Expected alcohol content could not be found on the label.',
					requires_human_review=True
				)
			
			is_match = self._normalizer.values_close(
				expected_abv,
				observed_abv,
				DEFAULT_ABV_TOLERANCE
			)
			
			status = STATUS_PASS if is_match else STATUS_FAIL
			severity = SEVERITY_INFO if is_match else SEVERITY_HIGH
			confidence = 98.0 if is_match else 95.0
			
			return self.create_result(
				rule_id=RULE_ALCOHOL_CONTENT_MATCH,
				field_name=FIELD_ALCOHOL_CONTENT,
				status=status,
				severity=severity,
				expected=f'{expected_abv:g}% ABV',
				observed=f'{observed_abv:g}% ABV',
				confidence=confidence,
				evidence=f'{observed_abv:g}% ABV',
				message=(
						'Expected alcohol content matches detected label alcohol content.'
						if is_match
						else 'Expected alcohol content does not match detected label alcohol content.'
				),
				requires_human_review=not is_match
			)
		except Exception:
			return self.create_result(
				rule_id=RULE_ALCOHOL_CONTENT_MATCH,
				field_name=FIELD_ALCOHOL_CONTENT,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Alcohol-content comparison',
				observed='Rule execution failed',
				confidence=0.0,
				evidence='',
				message='Alcohol-content matching could not be completed.',
				requires_human_review=True
			)
	
	def check_proof_present( self, application: LabelApplication, text: str ) -> LabelCheckResult:
		"""
		Purpose:
		--------
		Determine whether proof is present when proof is relevant to the beverage type.

		Parameters:
		-----------
		application (LabelApplication): Expected application values.
		text (str): OCR label text.

		Returns:
		--------
		LabelCheckResult: Proof presence rule result.
		"""
		try:
			throw_if( 'application', application )
			throw_if( 'text', text )
			
			self._application = application
			self._text = text
			
			if self._application.beverage_type != BEVERAGE_TYPE_DISTILLED_SPIRITS:
				return self.create_result(
					rule_id=RULE_PROOF_PRESENT,
					field_name=FIELD_PROOF,
					status=STATUS_NOT_APPLICABLE,
					severity=SEVERITY_INFO,
					expected='Proof statement for distilled spirits',
					observed='Not applicable to selected beverage type',
					confidence=100.0,
					evidence='',
					message='Proof check is not applicable to the selected beverage type.',
					requires_human_review=False
				)
			
			observed_proof = self.extract_proof( self._text )
			status = STATUS_PASS if observed_proof is not None else STATUS_WARNING
			severity = SEVERITY_INFO if status == STATUS_PASS else SEVERITY_LOW
			
			return self.create_result(
				rule_id=RULE_PROOF_PRESENT,
				field_name=FIELD_PROOF,
				status=status,
				severity=severity,
				expected='Proof statement for distilled spirits',
				observed=f'{observed_proof:g} Proof' if observed_proof is not None else 'Not found',
				confidence=95.0 if observed_proof is not None else 75.0,
				evidence=f'{observed_proof:g} Proof' if observed_proof is not None else '',
				message=(
						'Proof statement was detected.'
						if observed_proof is not None
						else 'Proof statement was not detected; reviewer should confirm if required.'
				),
				requires_human_review=False
			)
		except Exception:
			return self.create_result(
				rule_id=RULE_PROOF_PRESENT,
				field_name=FIELD_PROOF,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Proof statement',
				observed='Rule execution failed',
				confidence=0.0,
				evidence='',
				message='Proof presence verification could not be completed.',
				requires_human_review=True
			)
	
	def check_proof_consistency( self, application: LabelApplication,
			text: str ) -> LabelCheckResult:
		"""
		Purpose:
		--------
		Check whether detected proof is consistent with ABV for distilled spirits.

		Parameters:
		-----------
		application (LabelApplication): Expected application values.
		text (str): OCR label text.

		Returns:
		--------
		LabelCheckResult: Proof consistency rule result.
		"""
		try:
			throw_if( 'application', application )
			throw_if( 'text', text )
			
			self._application = application
			self._text = text
			
			if self._application.beverage_type != BEVERAGE_TYPE_DISTILLED_SPIRITS:
				return self.create_result(
					rule_id=RULE_PROOF_CONSISTENCY,
					field_name=FIELD_PROOF,
					status=STATUS_NOT_APPLICABLE,
					severity=SEVERITY_INFO,
					expected='Proof equals twice ABV',
					observed='Not applicable to selected beverage type',
					confidence=100.0,
					evidence='',
					message='Proof consistency check is not applicable to the selected beverage type.',
					requires_human_review=False
				)
			
			observed_abv = self.extract_abv( self._text )
			observed_proof = self.extract_proof( self._text )
			
			if observed_abv is None or observed_proof is None:
				return self.create_result(
					rule_id=RULE_PROOF_CONSISTENCY,
					field_name=FIELD_PROOF,
					status=STATUS_WARNING,
					severity=SEVERITY_LOW,
					expected='Proof equals twice ABV',
					observed='ABV or proof missing',
					confidence=70.0,
					evidence='',
					message='ABV/proof consistency could not be fully evaluated from label text.',
					requires_human_review=False
				)
			
			expected_proof = self._normalizer.proof_from_abv( observed_abv )
			is_match = self._normalizer.values_close(
				expected_proof,
				observed_proof,
				DEFAULT_PROOF_TOLERANCE
			)
			
			status = STATUS_PASS if is_match else STATUS_FAIL
			severity = SEVERITY_INFO if is_match else SEVERITY_HIGH
			
			return self.create_result(
				rule_id=RULE_PROOF_CONSISTENCY,
				field_name=FIELD_PROOF,
				status=status,
				severity=severity,
				expected=f'{expected_proof:g} Proof',
				observed=f'{observed_proof:g} Proof',
				confidence=98.0 if is_match else 95.0,
				evidence=f'{observed_abv:g}% ABV / {observed_proof:g} Proof',
				message=(
						'Detected proof is consistent with detected ABV.'
						if is_match
						else 'Detected proof is not consistent with detected ABV.'
				),
				requires_human_review=not is_match
			)
		except Exception:
			return self.create_result(
				rule_id=RULE_PROOF_CONSISTENCY,
				field_name=FIELD_PROOF,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Proof consistency',
				observed='Rule execution failed',
				confidence=0.0,
				evidence='',
				message='Proof consistency verification could not be completed.',
				requires_human_review=True
			)
	
	def check_net_contents_present( self, text: str ) -> LabelCheckResult:
		"""
		
			Purpose:
			--------
			Determine whether net contents are present on the label.
	
			Parameters:
			-----------
			text (str): OCR label text.
	
			Returns:
			--------
			LabelCheckResult: Net contents presence rule result.
			
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			observed = self.extract_net_contents( self._text )
			
			return self.create_result( rule_id=RULE_NET_CONTENTS_PRESENT,
				field_name=FIELD_NET_CONTENTS,
				status=STATUS_PASS if observed else STATUS_FAIL,
				severity=SEVERITY_INFO if observed else SEVERITY_HIGH,
				expected='Net contents statement',
				observed=observed if observed else 'Not found',
				confidence=95.0 if observed else 90.0,
				evidence=observed,
				message=(
						'Net contents were detected in the label text.'
						if observed
						else 'Net contents were not detected in the label text.' ),
				requires_human_review=not bool( observed ) )
		except Exception:
			return self.create_result( rule_id=RULE_NET_CONTENTS_PRESENT,
				field_name=FIELD_NET_CONTENTS, status=STATUS_REVIEW,
				severity=SEVERITY_HIGH, expected='Net contents statement',
				observed='Rule execution failed',
				confidence=0.0,
				evidence='',
				message='Net-contents presence verification could not be completed.',
				requires_human_review=True )
	
	def check_net_contents_match( self, application: LabelApplication,
			text: str ) -> LabelCheckResult:
		"""
		
			Purpose:
			--------
			Compare expected net contents against detected label net contents.
	
			Parameters:
			-----------
			application (LabelApplication): Expected application values.
			text (str): OCR label text.
	
			Returns:
			--------
			LabelCheckResult: Net contents match rule result.
			
		"""
		try:
			throw_if( 'application', application )
			throw_if( 'text', text )
			
			self._application = application
			self._text = text
			
			expected = self._normalizer.normalize_net_contents( self._application.net_contents )
			observed = self.extract_net_contents( self._text )
			
			if not expected:
				return self.create_result( rule_id=RULE_NET_CONTENTS_MATCH,
					field_name=FIELD_NET_CONTENTS, status=STATUS_REVIEW,
					severity=SEVERITY_MEDIUM, expected='Expected net contents from application',
					observed='No expected net contents provided',
					confidence=0.0, evidence='',
					message='Expected net contents were not provided for comparison.',
					requires_human_review=True )
			
			if not observed:
				return self.create_result(
					rule_id=RULE_NET_CONTENTS_MATCH,
					field_name=FIELD_NET_CONTENTS,
					status=STATUS_FAIL,
					severity=SEVERITY_HIGH,
					expected=expected,
					observed='Not found',
					confidence=90.0,
					evidence='',
					message='Expected net contents could not be found on the label.',
					requires_human_review=True
				)
			
			confidence = float( fuzz.ratio( expected, observed ) )
			status = STATUS_PASS if expected == observed or confidence >= 95.0 else STATUS_FAIL
			
			return self.create_result( rule_id=RULE_NET_CONTENTS_MATCH,
				field_name=FIELD_NET_CONTENTS, status=status,
				severity=SEVERITY_INFO if status == STATUS_PASS else SEVERITY_HIGH,
				expected=expected, observed=observed, confidence=confidence,
				evidence=observed,
				message=(
						'Expected net contents match detected label net contents.'
						if status == STATUS_PASS
						else 'Expected net contents do not match detected label net contents.' ),
				requires_human_review=status != STATUS_PASS )
		except Exception:
			return self.create_result(
				rule_id=RULE_NET_CONTENTS_MATCH,
				field_name=FIELD_NET_CONTENTS,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Net contents comparison',
				observed='Rule execution failed',
				confidence=0.0,
				evidence='',
				message='Net-contents matching could not be completed.',
				requires_human_review=True
			)
	
	def check_producer_bottler_present( self, text: str ) -> LabelCheckResult:
		"""
		
			Purpose:
			--------
			Determine whether the label includes producer, bottler, brewer, or distiller language.
	
			Parameters:
			-----------
			text (str): OCR label text.
	
			Returns:
			--------
			LabelCheckResult: Producer/bottler presence rule result.
			
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			match = re.search( PRODUCER_BOTTLER_PATTERN, self._text, flags=re.IGNORECASE )
			
			return self.create_result( rule_id=RULE_PRODUCER_BOTTLER_PRESENT,
				field_name=FIELD_PRODUCER_BOTTLER, status=STATUS_PASS if match else STATUS_FAIL,
				severity=SEVERITY_INFO if match else SEVERITY_HIGH,
				expected='Producer, bottler, brewer, or distiller statement',
				observed=match.group( 0 ) if match else 'Not found',
				confidence=95.0 if match else 85.0,
				evidence=match.group( 0 ) if match else '',
				message=(
						'Producer/bottler language was detected.'
						if match
						else 'Producer/bottler language was not detected.' ),
				requires_human_review=not bool( match )
			)
		except Exception:
			return self.create_result( rule_id=RULE_PRODUCER_BOTTLER_PRESENT,
				field_name=FIELD_PRODUCER_BOTTLER, status=STATUS_REVIEW,
				severity=SEVERITY_HIGH, expected='Producer/bottler statement',
				observed='Rule execution failed', confidence=0.0, evidence='',
				message='Producer/bottler verification could not be completed.',
				requires_human_review=True )
	
	def check_importer_present( self, text: str ) -> LabelCheckResult:
		"""
		
			Purpose:
			--------
			Determine whether imported-product label text includes importer language.
	
			Parameters:
			-----------
			text (str): OCR label text.
	
			Returns:
			--------
			LabelCheckResult: Importer presence rule result.
			
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			match = re.search( IMPORTER_PATTERN, self._text, flags=re.IGNORECASE )
			
			return self.create_result( rule_id=RULE_IMPORTER_PRESENT, field_name=FIELD_IMPORTER,
				status=STATUS_PASS if match else STATUS_FAIL,
				severity=SEVERITY_INFO if match else SEVERITY_HIGH,
				expected='Importer statement for imported product',
				observed=match.group( 0 ) if match else 'Not found',
				confidence=95.0 if match else 85.0,
				evidence=match.group( 0 ) if match else '',
				message=(
						'Importer language was detected for the imported product.'
						if match
						else 'Importer language was not detected for the imported product.'
				),
				requires_human_review=not bool( match )
			)
		except Exception:
			return self.create_result( rule_id=RULE_IMPORTER_PRESENT,
				field_name=FIELD_IMPORTER, status=STATUS_REVIEW,
				severity=SEVERITY_HIGH, expected='Importer statement',
				observed='Rule execution failed', confidence=0.0,
				evidence='', message='Importer verification could not be completed.',
				requires_human_review=True )
	
	def check_country_of_origin_present( self, application: LabelApplication,
			text: str ) -> LabelCheckResult:
		"""
		
			Purpose:
			--------
			Determine whether imported-product label text includes country-of-origin language.
	
			Parameters:
			-----------
			application (LabelApplication): Expected application values.
			text (str): OCR label text.
	
			Returns:
			--------
			LabelCheckResult: Country-of-origin presence rule result.
			
		"""
		try:
			throw_if( 'application', application )
			throw_if( 'text', text )
			
			self._application = application
			self._text = text
			
			match = re.search( COUNTRY_OF_ORIGIN_PATTERN, self._text, flags=re.IGNORECASE )
			expected = self._application.country_of_origin or 'Country of origin for imported product'
			
			return self.create_result(
				rule_id=RULE_COUNTRY_OF_ORIGIN_PRESENT,
				field_name=FIELD_COUNTRY_OF_ORIGIN,
				status=STATUS_PASS if match else STATUS_FAIL,
				severity=SEVERITY_INFO if match else SEVERITY_HIGH,
				expected=expected,
				observed=match.group( 0 ) if match else 'Not found',
				confidence=95.0 if match else 85.0,
				evidence=match.group( 0 ) if match else '',
				message=(
						'Country-of-origin language was detected for the imported product.'
						if match
						else 'Country-of-origin language was not detected for the imported product.'
				),
				requires_human_review=not bool( match )
			)
		except Exception:
			return self.create_result(
				rule_id=RULE_COUNTRY_OF_ORIGIN_PRESENT,
				field_name=FIELD_COUNTRY_OF_ORIGIN,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Country-of-origin statement',
				observed='Rule execution failed',
				confidence=0.0,
				evidence='',
				message='Country-of-origin verification could not be completed.',
				requires_human_review=True
			)
	
	def check_government_warning_present( self, text: str ) -> LabelCheckResult:
		"""
		
			Purpose:
			--------
			Determine whether the label contains government-warning language.
	
			Parameters:
			-----------
			text (str): OCR label text.
	
			Returns:
			--------
			LabelCheckResult: Government-warning presence rule result.
			
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			normalized = self._normalizer.normalize_for_strict_warning( self._text )
			expected_prefix = self._normalizer.normalize_for_strict_warning( 'GOVERNMENT WARNING' )
			found = expected_prefix in normalized
			
			return self.create_result( rule_id=RULE_GOVERNMENT_WARNING_PRESENT,
				field_name=FIELD_GOVERNMENT_WARNING, status=STATUS_PASS if found else STATUS_FAIL,
				severity=SEVERITY_INFO if found else SEVERITY_HIGH,
				expected='Government warning statement',
				observed='Found' if found else 'Not found',
				confidence=95.0 if found else 90.0,
				evidence='GOVERNMENT WARNING' if found else '',
				message=(
						'Government warning language was detected.'
						if found
						else 'Government warning language was not detected.'
				),
				requires_human_review=not found
			)
		except Exception:
			return self.create_result( rule_id=RULE_GOVERNMENT_WARNING_PRESENT,
				field_name=FIELD_GOVERNMENT_WARNING, status=STATUS_REVIEW, severity=SEVERITY_HIGH,
				expected='Government warning statement', observed='Rule execution failed',
				confidence=0.0, evidence='',
				message='Government-warning presence verification could not be completed.',
				requires_human_review=True )
	
	def check_government_warning_exact( self, text: str ) -> LabelCheckResult:
		"""
		
			Purpose:
			--------
			Determine whether OCR label text appears to contain the standard government-warning
			wording.
	
			Parameters:
			-----------
			text (str): OCR label text.
	
			Returns:
			--------
			LabelCheckResult: Government-warning exact-text rule result.
			
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			observed_warning = self._normalizer.normalize_for_strict_warning( self._text )
			expected_warning = GOVERNMENT_WARNING_TEXT_NORMALIZED
			confidence = float( fuzz.partial_ratio( expected_warning, observed_warning ) )
			status = STATUS_PASS if confidence >= DEFAULT_WARNING_MATCH_THRESHOLD else STATUS_FAIL
			
			return self.create_result( rule_id=RULE_GOVERNMENT_WARNING_EXACT,
				field_name=FIELD_GOVERNMENT_WARNING, status=status,
				severity=SEVERITY_INFO if status == STATUS_PASS else SEVERITY_HIGH,
				expected=GOVERNMENT_WARNING_TEXT,
				observed='Standard warning text detected' if status == STATUS_PASS else 'Exact text not detected',
				confidence=confidence,
				evidence='Government warning text' if status == STATUS_PASS else '',
				message=( 'Government warning wording appears to match the standard required text.'
						if status == STATUS_PASS
						else 'Government warning wording does not appear to match the standard text.' ),
				requires_human_review=status != STATUS_PASS )
		except Exception:
			return self.create_result(
				rule_id=RULE_GOVERNMENT_WARNING_EXACT,
				field_name=FIELD_GOVERNMENT_WARNING,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Standard government warning text',
				observed='Rule execution failed',
				confidence=0.0,
				evidence='',
				message='Government-warning exact-text verification could not be completed.',
				requires_human_review=True
			)
	
	def check_government_warning_prefix_caps( self, text: str ) -> LabelCheckResult:
		"""
			Purpose:
			--------
			Determine whether raw OCR text contains the all-caps GOVERNMENT WARNING: prefix.
	
			Parameters:
			-----------
			text (str): Raw OCR label text.
	
			Returns:
			--------
			LabelCheckResult: Government-warning prefix capitalization rule result.
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			found = self._normalizer.contains_strict_warning_prefix( self._text )
			
			return self.create_result( rule_id=RULE_GOVERNMENT_WARNING_PREFIX_CAPS,
				field_name=FIELD_GOVERNMENT_WARNING,
				status=STATUS_PASS if found else STATUS_FAIL,
				severity=SEVERITY_INFO if found else SEVERITY_HIGH,
				expected='GOVERNMENT WARNING:',
				observed='GOVERNMENT WARNING:' if found else 'Not found as all-caps prefix',
				confidence=98.0 if found else 90.0,
				evidence='GOVERNMENT WARNING:' if found else '',
				message=( 'The required all-caps government-warning prefix was detected.'
						if found
						else 'The required all-caps government-warning prefix was not detected.' ),
				requires_human_review=not found )
		except Exception:
			return self.create_result(
				rule_id=RULE_GOVERNMENT_WARNING_PREFIX_CAPS,
				field_name=FIELD_GOVERNMENT_WARNING,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='All-caps government-warning prefix',
				observed='Rule execution failed',
				confidence=0.0,
				evidence='',
				message='Government-warning prefix verification could not be completed.',
				requires_human_review=True
			)
	
	def check_government_warning_visual_format( self, text: str ) -> LabelCheckResult:
		"""
		
			Purpose:
			--------
			Flag the warning-statement visual-format requirement for reviewer confirmation because
			plain OCR cannot reliably prove bold formatting.
	
			Parameters:
			-----------
			text (str): Raw OCR label text.
	
			Returns:
			--------
			LabelCheckResult: Government-warning visual-format rule result.
			
		"""
		try:
			throw_if( 'text', text )
			
			self._text = text
			found = self._normalizer.contains_strict_warning_prefix( self._text )
			
			return self.create_result(
				rule_id=RULE_GOVERNMENT_WARNING_VISUAL_FORMAT,
				field_name=FIELD_GOVERNMENT_WARNING,
				status=STATUS_WARNING if found else STATUS_REVIEW,
				severity=SEVERITY_LOW if found else SEVERITY_MEDIUM,
				expected='Government warning visual format, including bold prefix where applicable',
				observed='OCR text found; visual bold formatting not confirmed' if found else 'Warning prefix not found',
				confidence=LOW_CONFIDENCE_THRESHOLD if found else 0.0,
				evidence='GOVERNMENT WARNING:' if found else '',
				message=(
						'OCR can verify text but cannot reliably prove bold formatting; reviewer should '
						'visually confirm warning-statement formatting.'
						if found
						else 'Warning formatting cannot be evaluated because the warning prefix was not found.'
				),
				requires_human_review=not found
			)
		except Exception:
			return self.create_result(
				rule_id=RULE_GOVERNMENT_WARNING_VISUAL_FORMAT,
				field_name=FIELD_GOVERNMENT_WARNING,
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				expected='Government warning visual format',
				observed='Rule execution failed',
				confidence=0.0,
				evidence='',
				message='Government-warning visual-format verification could not be completed.',
				requires_human_review=True
			)
