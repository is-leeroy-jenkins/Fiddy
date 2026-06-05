'''
    ******************************************************************************************
      Assembly:                Veritas
      Filename:                normalizer.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="normalizer.py" company="Terry D. Eppler">

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
        normalizer.py
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from config import throw_if

# ==========================================================================================
# Text Normalizer
# ==========================================================================================

class TextNormalizer( ):
	"""
		Purpose:
		--------
		Provide deterministic text normalization helpers for OCR output, reviewer-entered
		application values, units of measure, ABV values, proof values, and government-warning
		comparisons.
	
		Parameters:
		-----------
		None
	
		Returns:
		--------
		None
	"""
	
	apostrophe_chars: tuple[ str, ... ] = ( "'",
			"’",
			"‘",
			"`",
			"´",
			"ʼ" )
	
	dash_chars: tuple[ str, ... ] = ( "-", "–", "—", "−" )
	
	whitespace_pattern: str = r'\s+'
	punctuation_pattern: str = r'[^\w\s.%/]'
	non_alphanumeric_pattern: str = r'[^a-z0-9]+'
	
	def normalize_unicode( self, text: str ) -> str:
		"""
			Purpose:
			--------
			Normalize Unicode text to a stable ASCII-compatible form where possible.
	
			Parameters:
			-----------
			text (str): Text value to normalize.
	
			Returns:
			--------
			str: Unicode-normalized text.
		"""
		try:
			throw_if( 'text', text )
			
			value = unicodedata.normalize( 'NFKD', text )
			return value.encode( 'ascii', 'ignore' ).decode( 'ascii' )
		except Exception:
			return ''
	
	def normalize_whitespace( self, text: str ) -> str:
		"""
			Purpose:
			--------
			Collapse repeated whitespace and trim leading or trailing whitespace.
	
			Parameters:
			-----------
			text (str): Text value to normalize.
	
			Returns:
			--------
			str: Whitespace-normalized text.
		"""
		try:
			throw_if( 'text', text )
			
			value = re.sub( self.whitespace_pattern, ' ', text )
			return value.strip( )
		except Exception:
			return ''
	
	def normalize_apostrophes( self, text: str ) -> str:
		"""
			Purpose:
			--------
			Convert curly, typographic, and alternate apostrophe characters to a plain apostrophe.
	
			Parameters:
			-----------
			text (str): Text value to normalize.
	
			Returns:
			--------
			str: Text with normalized apostrophe characters.
		"""
		try:
			throw_if( 'text', text )
			
			value = text
			for apostrophe in self.apostrophe_chars:
				value = value.replace( apostrophe, "'" )
			
			return value
		except Exception:
			return ''
	
	def normalize_dashes( self, text: str ) -> str:
		"""
			Purpose:
			--------
			Convert typographic dash characters to a plain hyphen.
	
			Parameters:
			-----------
			text (str): Text value to normalize.
	
			Returns:
			--------
			str: Text with normalized dash characters.
		"""
		try:
			throw_if( 'text', text )
			
			value = text
			for dash in self.dash_chars:
				value = value.replace( dash, '-' )
			
			return value
		except Exception:
			return ''
	
	def normalize_case( self, text: str ) -> str:
		"""
			Purpose:
			--------
			Convert text to lowercase using invariant Python casefold behavior.
	
			Parameters:
			-----------
			text (str): Text value to normalize.
	
			Returns:
			--------
			str: Lowercase normalized text.
		"""
		try:
			throw_if( 'text', text )
			
			return text.casefold( )
		except Exception:
			return ''
	
	def normalize_text( self, text: str ) -> str:
		"""
			Purpose:
			--------
			Normalize general OCR or application text for matching and field extraction.
	
			Parameters:
			-----------
			text (str): Text value to normalize.
	
			Returns:
			--------
			str: General normalized text.
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
		except Exception:
			return ''
	
	def normalize_for_match( self, text: str ) -> str:
		"""
			Purpose:
			--------
			Normalize text for fuzzy matching by removing punctuation differences and collapsing
			non-alphanumeric separators.
	
			Parameters:
			-----------
			text (str): Text value to normalize.
	
			Returns:
			--------
			str: Matching-normalized text.
		"""
		try:
			throw_if( 'text', text )
			
			value = self.normalize_text( text )
			value = re.sub( self.non_alphanumeric_pattern, ' ', value )
			value = self.normalize_whitespace( value )
			
			return value
		except Exception:
			return ''
	
	def normalize_for_strict_warning( self, text: str ) -> str:
		"""
			Purpose:
			--------
			Normalize government-warning text for strict wording comparison while ignoring
			formatting artifacts introduced by OCR.
	
			Parameters:
			-----------
			text (str): Government warning or OCR text to normalize.
	
			Returns:
			--------
			str: Warning-normalized text.
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
		except Exception:
			return ''
	
	def normalize_brand_name( self, brand_name: str ) -> str:
		"""
			Purpose:
			--------
			Normalize a brand name for judgment-sensitive matching.
	
			Parameters:
			-----------
			brand_name (str): Brand name to normalize.
	
			Returns:
			--------
			str: Normalized brand name.
		"""
		try:
			throw_if( 'brand_name', brand_name )
			
			return self.normalize_for_match( brand_name )
		except Exception:
			return ''
	
	def normalize_class_type( self, class_type: str ) -> str:
		"""
			Purpose:
			--------
			Normalize a class or type designation for judgment-sensitive matching.
	
			Parameters:
			-----------
			class_type (str): Class or type designation to normalize.
	
			Returns:
			--------
			str: Normalized class or type designation.
		"""
		try:
			throw_if( 'class_type', class_type )
			
			return self.normalize_for_match( class_type )
		except Exception:
			return ''
	
	def normalize_net_contents( self, net_contents: str ) -> str:
		"""
			Purpose:
			--------
			Normalize net contents values into a consistent unit representation.
	
			Parameters:
			-----------
			net_contents (str): Net contents value to normalize.
	
			Returns:
			--------
			str: Normalized net contents value.
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
		except Exception:
			return ''
	
	def normalize_abv_text( self, alcohol_content: str ) -> str:
		"""
			Purpose:
			--------
			Normalize alcohol-content text into a consistent ABV phrase representation.
	
			Parameters:
			-----------
			alcohol_content (str): Alcohol-content text to normalize.
	
			Returns:
			--------
			str: Normalized alcohol-content text.
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
		except Exception:
			return ''
	
	def normalize_numeric_string( self, value: str ) -> str:
		"""
			Purpose:
			--------
			Normalize numeric text by removing non-numeric characters except decimal points.
	
			Parameters:
			-----------
			value (str): Numeric string to normalize.
	
			Returns:
			--------
			str: Normalized numeric string.
		"""
		try:
			throw_if( 'value', value )
			
			text = self.normalize_text( value )
			text = re.sub( r'[^0-9.]', '', text )
			
			if text.count( '.' ) <= 1:
				return text
			
			parts = text.split( '.' )
			return f'{parts[ 0 ]}.{''.join( parts[ 1: ] )}'
		except Exception:
			return ''
	
	def parse_float( self, value: str ) -> Optional[ float ]:
		"""
			Purpose:
			--------
			Parse a normalized numeric value into a floating-point number.
	
			Parameters:
			-----------
			value (str): Numeric value to parse.
	
			Returns:
			--------
			Optional[float]: Parsed float value, or None when parsing fails.
		"""
		try:
			throw_if( 'value', value )
			
			text = self.normalize_numeric_string( value )
			return float( text ) if text else None
		except Exception:
			return None
	
	def normalize_abv_value( self, value: str | float | int | None ) -> Optional[ float ]:
		"""
			Purpose:
			--------
			Normalize an ABV value to a numeric percentage.
	
			Parameters:
			-----------
			value (str | float | int | None): ABV value to normalize.
	
			Returns:
			--------
			Optional[float]: Normalized ABV percentage, or None when unavailable.
		"""
		try:
			throw_if( 'value', value )
			
			if isinstance( value, float | int ):
				return float( value )
			
			return self.parse_float( value )
		except Exception:
			return None
	
	def normalize_proof_value( self, value: str | float | int | None ) -> Optional[ float ]:
		"""
			Purpose:
			--------
			Normalize a proof value to a numeric value.
	
			Parameters:
			-----------
			value (str | float | int | None): Proof value to normalize.
	
			Returns:
			--------
			Optional[float]: Normalized proof value, or None when unavailable.
		"""
		try:
			throw_if( 'value', value )
			
			if isinstance( value, float | int ):
				return float( value )
			
			return self.parse_float( value )
		except Exception:
			return None
	
	def proof_from_abv( self, abv: float | int | None ) -> Optional[ float ]:
		"""
			Purpose:
			--------
			Calculate expected proof from ABV for distilled spirits.
	
			Parameters:
			-----------
			abv (float | int | None): Alcohol by volume percentage.
	
			Returns:
			--------
			Optional[float]: Calculated proof, or None when ABV is unavailable.
		"""
		try:
			throw_if( 'abv', abv )
			
			return float( abv ) * 2.0
		except Exception:
			return None
	
	def values_close( self, left: float | int | None, right: float | int | None,
			tolerance: float ) -> bool:
		"""
			Purpose:
			--------
			Determine whether two numeric values are within an allowed tolerance.
	
			Parameters:
			-----------
			left (float | int | None): First numeric value.
			right (float | int | None): Second numeric value.
			tolerance (float): Allowed absolute difference.
	
			Returns:
			--------
			bool: True when values are within tolerance; otherwise, False.
		"""
		try:
			throw_if( 'left', left )
			throw_if( 'right', right )
			throw_if( 'tolerance', tolerance )
			
			return abs( float( left ) - float( right ) ) <= float( tolerance )
		except Exception:
			return False
	
	def contains_phrase( self, text: str, phrase: str ) -> bool:
		"""
			Purpose:
			--------
			Determine whether normalized text contains a normalized phrase.
	
			Parameters:
			-----------
			text (str): Text to search.
			phrase (str): Phrase to locate.
	
			Returns:
			--------
			bool: True when the phrase is present; otherwise, False.
		"""
		try:
			throw_if( 'text', text )
			throw_if( 'phrase', phrase )
			
			haystack = self.normalize_for_match( text )
			needle = self.normalize_for_match( phrase )
			
			return needle in haystack
		except Exception:
			return False
	
	def contains_strict_warning_prefix( self, text: str ) -> bool:
		"""
			Purpose:
			--------
			Determine whether raw OCR text contains the required all-caps government-warning
			prefix.
	
			Parameters:
			-----------
			text (str): Raw OCR text to search.
	
			Returns:
			--------
			bool: True when GOVERNMENT WARNING: appears as an all-caps prefix; otherwise,
			False.
		"""
		try:
			throw_if( 'text', text )
			
			return bool( re.search( r'\bGOVERNMENT\s+WARNING\s*:', text ) )
		except Exception:
			return False
	
	def clean_ocr_artifacts( self, text: str ) -> str:
		"""
			Purpose:
			--------
			Remove common OCR artifacts while preserving meaningful label content.
	
			Parameters:
			-----------
			text (str): OCR text to clean.
	
			Returns:
			--------
			str: Cleaned OCR text.
		"""
		try:
			throw_if( 'text', text )
			
			value = text.replace( '|', ' ' )
			value = value.replace( '¬', ' ' )
			value = value.replace( '™', ' ' )
			value = value.replace( '®', ' ' )
			value = value.replace( '©', ' ' )
			value = re.sub( r'[_~^]+', ' ', value )
			value = self.normalize_whitespace( value )
			
			return value
		except Exception:
			return ''
	
	def normalize_label_text( self, text: str ) -> str:
		"""
			Purpose:
			--------
			Normalize full OCR label text for downstream field extraction and rule checks.
	
			Parameters:
			-----------
			text (str): Raw OCR label text.
	
			Returns:
			--------
			str: Normalized label text.
		"""
		try:
			throw_if( 'text', text )
			
			value = self.clean_ocr_artifacts( text )
			value = self.normalize_text( value )
			
			return value
		except Exception:
			return ''
	
	def extract_context( self, text: str, phrase: str, window: int = 80 ) -> str:
		"""
			Purpose:
			--------
			Extract a short context window around a phrase for reviewer-facing evidence.
	
			Parameters:
			-----------
			text (str): Source text.
			phrase (str): Phrase around which context should be extracted.
			window (int): Number of characters to include before and after the phrase.
	
			Returns:
			--------
			str: Extracted context text.
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
		except Exception:
			return ''