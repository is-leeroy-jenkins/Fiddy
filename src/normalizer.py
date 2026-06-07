'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                normalizer.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="normalizer.py" company="Terry D. Eppler">

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
        Provides deterministic text, numeric, ABV, proof, net-contents, OCR-artifact, and
        government-warning normalization helpers for the Fiddy verification workflow.

        This module standardizes OCR output and application values so field extraction,
        fuzzy matching, strict warning checks, numeric comparisons, and reviewer-facing
        evidence generation can operate on stable normalized text.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from booger import Error, Logger
from config import throw_if

# ==========================================================================================
# Text Normalizer
# ==========================================================================================

class TextNormalizer( ):
	"""Provide deterministic normalization helpers for OCR and application values.

	Purpose:
		The ``TextNormalizer`` class centralizes text and numeric normalization used by the Fiddy
		label verification workflow. It provides helpers for Unicode cleanup, whitespace
		normalization, apostrophe and dash normalization, case normalization, fuzzy-match
		preparation, strict government-warning comparison, brand and class/type normalization,
		net-contents normalization, ABV/proof parsing, numeric tolerance checks, OCR artifact
		removal, full-label normalization, and reviewer-facing context extraction.

		The class intentionally uses deterministic string operations and regular expressions so
		normalization behavior remains auditable and repeatable. These helpers are used by rule
		checks, warning validation, field extraction, and report evidence generation.

	Attributes:
		apostrophe_chars (tuple[str, ...]): Apostrophe-like characters normalized to a plain
			apostrophe.
		dash_chars (tuple[str, ...]): Dash-like characters normalized to a plain hyphen.
		whitespace_pattern (str): Regular-expression pattern used to collapse whitespace.
		punctuation_pattern (str): Regular-expression pattern reserved for punctuation-aware
			normalization workflows.
		non_alphanumeric_pattern (str): Regular-expression pattern used to collapse non-
			alphanumeric separators for fuzzy matching.
	"""
	
	apostrophe_chars: tuple[ str, ... ] = ("'",
	                                       "â€™",
	                                       "â€˜",
	                                       "`",
	                                       "Â´",
	                                       "Ê¼")
	
	dash_chars: tuple[ str, ... ] = ("-", "â€“", "â€”", "âˆ’")
	
	whitespace_pattern: str = r'\s+'
	punctuation_pattern: str = r'[^\w\s.%/]'
	non_alphanumeric_pattern: str = r'[^a-z0-9]+'
	
	def normalize_unicode( self, text: str ) -> str:
		"""Normalize Unicode text to an ASCII-compatible representation.

		Purpose:
			This method applies NFKD Unicode normalization and then encodes the value to ASCII while
			ignoring characters that cannot be represented. It is useful for reducing typographic,
			accented, and OCR-introduced Unicode variation before downstream matching logic runs.

		Args:
			text (str): Text value to normalize.

		Returns:
			str: Unicode-normalized ASCII-compatible text. If normalization fails, the exception
			is logged and an empty string is returned.
		"""
		try:
			throw_if( 'text', text )
			
			value = unicodedata.normalize( 'NFKD', text )
			return value.encode( 'ascii', 'ignore' ).decode( 'ascii' )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_unicode( text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_whitespace( self, text: str ) -> str:
		"""Collapse repeated whitespace and trim leading or trailing whitespace.

		Purpose:
			This method replaces one or more whitespace characters with a single space and trims the
			result. It is used throughout the normalization workflow to stabilize OCR text, reviewer
			input, field values, and context snippets.

		Args:
			text (str): Text value to normalize.

		Returns:
			str: Whitespace-normalized text. If normalization fails, the exception is logged and
			an empty string is returned.
		"""
		try:
			throw_if( 'text', text )
			
			value = re.sub( self.whitespace_pattern, ' ', text )
			return value.strip( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_whitespace( text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_apostrophes( self, text: str ) -> str:
		"""Convert typographic apostrophe variants to a plain apostrophe.

		Purpose:
			This method replaces each configured apostrophe-like character with the standard single
			quote character. It supports brand and producer names where OCR or source text may use
			curly quotes, accent-like marks, or other apostrophe variants.

		Args:
			text (str): Text value to normalize.

		Returns:
			str: Text with normalized apostrophe characters. If normalization fails, the exception
			is logged and an empty string is returned.
		"""
		try:
			throw_if( 'text', text )
			
			value = text
			for apostrophe in self.apostrophe_chars:
				value = value.replace( apostrophe, "'" )
			
			return value
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_apostrophes( text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_dashes( self, text: str ) -> str:
		"""Convert typographic dash variants to a plain hyphen.

		Purpose:
			This method replaces each configured dash-like character with the standard hyphen
			character. It helps stabilize label text where OCR or source documents may contain en
			dashes, em dashes, minus signs, or other dash-like glyphs.

		Args:
			text (str): Text value to normalize.

		Returns:
			str: Text with normalized dash characters. If normalization fails, the exception is
			logged and an empty string is returned.
		"""
		try:
			throw_if( 'text', text )
			
			value = text
			for dash in self.dash_chars:
				value = value.replace( dash, '-' )
			
			return value
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_dashes( text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_case( self, text: str ) -> str:
		"""Convert text to lowercase using Python casefold behavior.

		Purpose:
			This method applies ``casefold`` rather than simple lowercase conversion so matching is
			more stable across case variations. It is used as part of the general text normalization
			pipeline before fuzzy matching or strict warning normalization.

		Args:
			text (str): Text value to normalize.

		Returns:
			str: Lowercase normalized text. If normalization fails, the exception is logged and an
			empty string is returned.
		"""
		try:
			throw_if( 'text', text )
			
			return text.casefold( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_case( text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_text( self, text: str ) -> str:
		"""Normalize general OCR or application text.

		Purpose:
			This method applies the standard text-normalization pipeline: Unicode normalization,
			apostrophe normalization, dash normalization, case normalization, line-control character
			replacement, and whitespace normalization. The result is suitable for field extraction,
			display-stable comparison, and downstream specialized normalization.

		Args:
			text (str): Text value to normalize.

		Returns:
			str: General normalized text. If normalization fails, the exception is logged and an
			empty string is returned.
		"""
		try:
			throw_if( 'text', text )
			
			value = self.normalize_unicode( text )
			value = self.normalize_apostrophes( value )
			value = self.normalize_dashes( value )
			value = self.normalize_case( value )
			value = value.replace( '\r', ' ' ).replace( '\n', ' ' ).replace( '\t', ' ' )
			value = self.normalize_whitespace( value )
			
			return value
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_text( text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_for_match( self, text: str ) -> str:
		"""Normalize text for fuzzy or judgment-sensitive matching.

		Purpose:
			This method applies the general normalization pipeline and then replaces non-
			alphanumeric separators with spaces. It intentionally removes punctuation and separator
			differences that should not normally cause a mismatch, such as apostrophe, dash, slash,
			or spacing variations.

		Args:
			text (str): Text value to normalize for matching.

		Returns:
			str: Matching-normalized text. If normalization fails, the exception is logged and an
			empty string is returned.
		"""
		try:
			throw_if( 'text', text )
			
			value = self.normalize_text( text )
			value = re.sub( self.non_alphanumeric_pattern, ' ', value )
			value = self.normalize_whitespace( value )
			
			return value
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_for_match( text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_for_strict_warning( self, text: str ) -> str:
		"""Normalize government-warning text for strict wording comparison.

		Purpose:
			This method prepares government-warning text for exact wording checks while ignoring
			common punctuation and formatting artifacts introduced by OCR. It keeps the comparison
			strict with respect to word sequence while removing punctuation, slash, parenthesis, and
			separator differences that are not meaningful to the word-level warning text.

		Args:
			text (str): Government warning or OCR text to normalize.

		Returns:
			str: Warning-normalized text. If normalization fails, the exception is logged and an
			empty string is returned.
		"""
		try:
			throw_if( 'text', text )
			
			value = self.normalize_text( text )
			value = value.replace( ':', ' ' )
			value = value.replace( ';', ' ' )
			value = value.replace( ',', ' ' )
			value = value.replace( '.', ' ' )
			value = value.replace( '(', ' ' )
			value = value.replace( ')', ' ' )
			value = value.replace( '/', ' ' )
			value = re.sub( self.non_alphanumeric_pattern, ' ', value )
			value = self.normalize_whitespace( value )
			
			return value
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_for_strict_warning( text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_brand_name( self, brand_name: str ) -> str:
		"""Normalize a brand name for judgment-sensitive matching.

		Purpose:
			This method delegates to ``normalize_for_match`` so brand-name comparisons ignore
			punctuation, case, separator, apostrophe, dash, and spacing differences that should not
			normally cause a mismatch.

		Args:
			brand_name (str): Brand name to normalize.

		Returns:
			str: Normalized brand name. If normalization fails, the exception is logged and an
			empty string is returned.
		"""
		try:
			throw_if( 'brand_name', brand_name )
			
			return self.normalize_for_match( brand_name )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_brand_name( brand_name: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_class_type( self, class_type: str ) -> str:
		"""Normalize a class or type designation for matching.

		Purpose:
			This method delegates to ``normalize_for_match`` so class/type comparisons can tolerate
			common OCR and formatting differences while preserving the underlying words used by the
			rule engine.

		Args:
			class_type (str): Class or type designation to normalize.

		Returns:
			str: Normalized class or type designation. If normalization fails, the exception is
			logged and an empty string is returned.
		"""
		try:
			throw_if( 'class_type', class_type )
			
			return self.normalize_for_match( class_type )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_class_type( class_type: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_net_contents( self, net_contents: str ) -> str:
		"""Normalize net contents into a consistent unit representation.

		Purpose:
			This method normalizes general text and then standardizes common unit spellings and
			abbreviations. For example, milliliter variants become ``ml``, liter variants become
			``l``, and fluid-ounce variants become ``fl oz``. The result is used by net-contents
			match rules to reduce formatting differences between application data and OCR text.

		Args:
			net_contents (str): Net contents value to normalize.

		Returns:
			str: Normalized net contents value. If normalization fails, the exception is logged
			and an empty string is returned.
		"""
		try:
			throw_if( 'net_contents', net_contents )
			
			value = self.normalize_text( net_contents )
			value = value.replace( 'milliliters', 'ml' )
			value = value.replace( 'milliliter', 'ml' )
			value = value.replace( 'm.l.', 'ml' )
			value = value.replace( 'ml.', 'ml' )
			value = value.replace( 'liters', 'l' )
			value = value.replace( 'liter', 'l' )
			value = value.replace( 'fluid ounces', 'fl oz' )
			value = value.replace( 'fluid ounce', 'fl oz' )
			value = value.replace( 'fl. oz.', 'fl oz' )
			value = value.replace( 'fl oz.', 'fl oz' )
			value = self.normalize_whitespace( value )
			
			return value
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_net_contents( net_contents: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_abv_text( self, alcohol_content: str ) -> str:
		"""Normalize alcohol-content text into a consistent ABV phrase.

		Purpose:
			This method normalizes general text and replaces common alcohol-content phrases such as
			``alc./vol.``, ``alc/vol``, ``alc vol``, ``alcohol by volume``, and
			``alcohol/volume`` with ``abv``. The result is useful when OCR or application text uses
			different ABV phrasing for the same concept.

		Args:
			alcohol_content (str): Alcohol-content text to normalize.

		Returns:
			str: Normalized alcohol-content text. If normalization fails, the exception is logged
			and an empty string is returned.
		"""
		try:
			throw_if( 'alcohol_content', alcohol_content )
			
			value = self.normalize_text( alcohol_content )
			value = value.replace( 'alc./vol.', 'abv' )
			value = value.replace( 'alc/vol', 'abv' )
			value = value.replace( 'alc vol', 'abv' )
			value = value.replace( 'alcohol by volume', 'abv' )
			value = value.replace( 'alcohol/volume', 'abv' )
			value = self.normalize_whitespace( value )
			
			return value
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_abv_text( alcohol_content: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_numeric_string( self, value: str ) -> str:
		"""Normalize numeric text by preserving digits and decimal points.

		Purpose:
			This method first applies general text normalization and then removes all characters
			except digits and decimal points. If the resulting text contains more than one decimal
			point, the first decimal point is preserved and subsequent decimal fragments are joined
			to produce a parseable numeric string.

		Args:
			value (str): Numeric string to normalize.

		Returns:
			str: Normalized numeric string. If normalization fails, the exception is logged and an
			empty string is returned.
		"""
		try:
			throw_if( 'value', value )
			text = self.normalize_text( value )
			text = re.sub( r'[^0-9.]', '', text )
			if text.count( '.' ) <= 1:
				return text
			
			parts = text.split( '.' )
			return f'{parts[ 0 ]}.{"".join( parts[ 1: ] )}'
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_numeric_string( value: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def parse_float( self, value: str ) -> Optional[ float ]:
		"""Parse a normalized numeric value into a float.

		Purpose:
			This method normalizes the input text through ``normalize_numeric_string`` and converts
			the result to ``float`` when a numeric string remains. Empty or invalid values are treated
			as unavailable.

		Args:
			value (str): Numeric value to parse.

		Returns:
			Optional[float]: Parsed float value, or ``None`` when parsing fails or no numeric
			content remains. Unexpected failures are logged before returning ``None``.
		"""
		try:
			throw_if( 'value', value )
			
			text = self.normalize_numeric_string( value )
			return float( text ) if text else None
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'parse_float( value: str ) -> Optional[float]'
			Logger( ).write( error )
			return None
	
	def normalize_abv_value( self, value: str | float | int | None ) -> Optional[ float ]:
		"""Normalize an ABV value to a numeric percentage.

		Purpose:
			This method accepts string, float, integer, or ``None`` ABV values. Numeric inputs are
			returned as floats. String inputs are parsed through ``parse_float`` so percent signs,
			labels, and OCR artifacts can be removed before conversion.

		Args:
			value (str | float | int | None): ABV value to normalize.

		Returns:
			Optional[float]: Normalized ABV percentage, or ``None`` when unavailable or parsing
			fails. Unexpected failures are logged before returning ``None``.
		"""
		try:
			throw_if( 'value', value )
			
			if isinstance( value, float | int ):
				return float( value )
			
			return self.parse_float( value )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_abv_value( value: str | float | int | None ) -> Optional[float]'
			Logger( ).write( error )
			return None
	
	def normalize_proof_value( self, value: str | float | int | None ) -> Optional[ float ]:
		"""Normalize a proof value to a numeric value.

		Purpose:
			This method accepts string, float, integer, or ``None`` proof values. Numeric inputs are
			returned as floats. String inputs are parsed through ``parse_float`` so proof labels and
			OCR artifacts can be removed before conversion.

		Args:
			value (str | float | int | None): Proof value to normalize.

		Returns:
			Optional[float]: Normalized proof value, or ``None`` when unavailable or parsing
			fails. Unexpected failures are logged before returning ``None``.
		"""
		try:
			throw_if( 'value', value )
			
			if isinstance( value, float | int ):
				return float( value )
			
			return self.parse_float( value )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_proof_value( value: str | float | int | None ) -> Optional[float]'
			Logger( ).write( error )
			return None
	
	def proof_from_abv( self, abv: float | int | None ) -> Optional[ float ]:
		"""Calculate expected proof from alcohol by volume.

		Purpose:
			For distilled spirits, proof is generally calculated as twice the ABV percentage. This
			helper performs that calculation when an ABV value is available.

		Args:
			abv (float | int | None): Alcohol by volume percentage.

		Returns:
			Optional[float]: Calculated proof, or ``None`` when ABV is unavailable or conversion
			fails. Unexpected failures are logged before returning ``None``.
		"""
		try:
			throw_if( 'abv', abv )
			
			return float( abv ) * 2.0
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'proof_from_abv( self, *args ) -> Optional[float]'
			Logger( ).write( error )
			return None
	
	def values_close( self, left: float | int | None, right: float | int | None,
			tolerance: float ) -> bool:
		"""Determine whether two numeric values are within a tolerance.

		Purpose:
			This method converts both values and the tolerance to floats and compares the absolute
			difference against the allowed tolerance. It is used by ABV and proof comparison rules to
			avoid false mismatches caused by small decimal differences.

		Args:
			left (float | int | None): First numeric value.
			right (float | int | None): Second numeric value.
			tolerance (float): Allowed absolute difference.

		Returns:
			bool: ``True`` when values are within tolerance; otherwise, ``False``. If comparison
			fails, the exception is logged and ``False`` is returned.
		"""
		try:
			throw_if( 'left', left )
			throw_if( 'right', right )
			throw_if( 'tolerance', tolerance )
			
			return abs( float( left ) - float( right ) ) <= float( tolerance )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'values_close(  self, *args ) -> bool'
			Logger( ).write( error )
			return False
	
	def contains_phrase( self, text: str, phrase: str ) -> bool:
		"""Determine whether normalized text contains a normalized phrase.

		Purpose:
			This method normalizes both source text and target phrase for fuzzy-style matching, then
			performs a simple containment check. It is useful for cases where punctuation, case, or
			spacing differences should not prevent a phrase from being found.

		Args:
			text (str): Text to search.
			phrase (str): Phrase to locate.

		Returns:
			bool: ``True`` when the normalized phrase is present in normalized text; otherwise,
			``False``. If the check fails, the exception is logged and ``False`` is returned.
		"""
		try:
			throw_if( 'text', text )
			throw_if( 'phrase', phrase )
			
			haystack = self.normalize_for_match( text )
			needle = self.normalize_for_match( phrase )
			
			return needle in haystack
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'contains_phrase( text: str, phrase: str ) -> bool'
			Logger( ).write( error )
			return False
	
	def contains_strict_warning_prefix( self, text: str ) -> bool:
		"""Determine whether raw OCR text contains the all-caps government-warning prefix.

		Purpose:
			This method searches the raw OCR text for ``GOVERNMENT WARNING:`` with flexible
			whitespace before the colon. It intentionally checks raw text rather than fully
			case-normalized text because capitalization of the warning prefix is part of the
			requirement being evaluated.

		Args:
			text (str): Raw OCR text to search.

		Returns:
			bool: ``True`` when the required all-caps warning prefix is present; otherwise,
			``False``. If the check fails, the exception is logged and ``False`` is returned.
		"""
		try:
			throw_if( 'text', text )
			
			return bool( re.search( r'\bGOVERNMENT\s+WARNING\s*:', text ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'contains_strict_warning_prefix( text: str ) -> bool'
			Logger( ).write( error )
			return False
	
	def clean_ocr_artifacts( self, text: str ) -> str:
		"""Remove common OCR artifacts while preserving meaningful label content.

		Purpose:
			This method removes or replaces selected symbols that commonly appear as OCR artifacts,
			including pipes, trademark symbols, registered symbols, copyright symbols, and repeated
			underscore-like marks. It then normalizes whitespace so the cleaned value can be passed to
			general label-text normalization.

		Args:
			text (str): OCR text to clean.

		Returns:
			str: Cleaned OCR text. If cleanup fails, the exception is logged and an empty string is
			returned.
		"""
		try:
			throw_if( 'text', text )
			
			value = text.replace( '|', ' ' )
			value = value.replace( 'Â¬', ' ' )
			value = value.replace( 'â„¢', ' ' )
			value = value.replace( 'Â®', ' ' )
			value = value.replace( 'Â©', ' ' )
			value = re.sub( r'[_~^]+', ' ', value )
			value = self.normalize_whitespace( value )
			
			return value
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'clean_ocr_artifacts( text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def normalize_label_text( self, text: str ) -> str:
		"""Normalize full OCR label text for field extraction and rule checks.

		Purpose:
			This method first removes common OCR artifacts and then applies the standard text
			normalization pipeline. It is intended for full-label OCR output where downstream
			processors need stable text for matching, extraction, and validation.

		Args:
			text (str): Raw OCR label text.

		Returns:
			str: Normalized label text. If normalization fails, the exception is logged and an
			empty string is returned.
		"""
		try:
			throw_if( 'text', text )
			
			value = self.clean_ocr_artifacts( text )
			value = self.normalize_text( value )
			
			return value
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_label_text( text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def extract_context( self, text: str, phrase: str, window: int = 80 ) -> str:
		"""Extract a short context window around a phrase for reviewer-facing evidence.

		Purpose:
			This method normalizes the source text and phrase, locates the normalized phrase inside
			the normalized source text, and returns a bounded context window around the match. The
			result is intended for evidence fields in rule results so reviewers can see where a
			matched value appeared in the label text.

		Args:
			text (str): Source text from which evidence should be extracted.
			phrase (str): Phrase around which context should be extracted.
			window (int): Number of characters to include before and after the phrase.

		Returns:
			str: Extracted context text. If the phrase is not found or context extraction fails,
			the exception is logged when applicable and an empty string is returned.
		"""
		try:
			throw_if( 'text', text )
			throw_if( 'phrase', phrase )
			throw_if( 'window', window )
			
			normalized_text = self.normalize_text( text )
			normalized_phrase = self.normalize_text( phrase )
			index = normalized_text.find( normalized_phrase )
			
			if index < 0:
				return ''
			
			start = max( 0, index - window )
			end = min( len( normalized_text ), index + len( normalized_phrase ) + window )
			
			return normalized_text[ start:end ].strip( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_context( text: str, phrase: str, window: int ) -> str'
			Logger( ).write( error )
			return ''