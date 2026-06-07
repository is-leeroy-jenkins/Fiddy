'''
  ******************************************************************************************
      Assembly:                Name
      Filename:                label_field_extractor.py
      Author:                  Terry D. Eppler
      Created:                 06-31-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-01-2026
  ******************************************************************************************
  <copyright file="label_field_extractor.py" company="Terry D. Eppler">

	     label_field_extractor.py
	     Copyright ©  2026  Terry Eppler

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

     You can contact me at:  terryeppler@gmail.com or eppler.terry@epa.gov

  </copyright>
  <summary>
    Provides deterministic OCR text parsing for alcohol-label field extraction.

    This module extracts likely brand, class/type, ABV, net contents, producer or bottler,
    country of origin, and government-warning values from OCR text so downstream verification
    rules can compare structured label data against application data.
  </summary>
  ******************************************************************************************
'''
from __future__ import annotations

import re
from typing import List

from booger import Error, Logger
from config import throw_if
from src.constants import GOVERNMENT_WARNING_TEXT
from src.models import ExtractedLabel

class LabelFieldExtractor( ):
	"""Extract structured alcohol-label fields from OCR text.

	Purpose:
		The ``LabelFieldExtractor`` class provides deterministic pattern-based extraction helpers
		for converting raw OCR output into structured fields on an ``ExtractedLabel`` model. The
		class intentionally uses regular expressions, line filtering, whitespace normalization, and
		simple keyword detection rather than probabilistic classification so field extraction remains
		predictable and easy to audit.
	
		The extractor supports the fields required by the Fiddy prototype workflow: brand name,
		class/type, alcohol content, net contents, producer or bottler statement, country of origin,
		and government warning text. The extraction results are best-effort values intended to
		support downstream rule checks and human review, not to replace reviewer judgment when OCR
		is incomplete or ambiguous.

	Attributes:
		_raw_text (str): Raw OCR text currently being inspected.
		_lines (List[str]): Non-empty normalized OCR lines derived from the raw text.
	"""
	_raw_text: str
	_lines: List[ str ]
	
	def normalize_space( self, value: str ) -> str:
		"""Normalize repeated whitespace in a text value.

		Purpose:
			This method converts the supplied value to a string, collapses runs of whitespace into a
			single space, and trims leading or trailing whitespace. It is used throughout the
			extractor to stabilize OCR text before applying line-based or regular-expression
			matching.

		Args:
			value (str): Source text value to normalize.

		Returns:
			str: Whitespace-normalized text. If normalization fails, the exception is logged and
			an empty string is returned, preserving the original fallback behavior.
		"""
		try:
			throw_if( 'value', value )
			return re.sub( r'\s+', ' ', str( value ) ).strip( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_space( value: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def get_lines( self, raw_text: str ) -> List[ str ]:
		"""Return non-empty normalized OCR text lines.

		Purpose:
			This method splits OCR text into lines, normalizes each line with ``normalize_space``,
			and returns only non-empty results. The returned list is used by field-specific extraction
			methods that depend on label layout or line-level context, including brand, class/type,
			producer/bottler, and country-of-origin extraction.

		Args:
			raw_text (str): Raw OCR text to split and normalize.

		Returns:
			List[str]: Non-empty normalized OCR text lines. If line extraction fails, the exception
			is logged and an empty list is returned.
		"""
		try:
			throw_if( 'raw_text', raw_text )
			
			lines = [ ]
			
			for line in raw_text.splitlines( ):
				clean_line = self.normalize_space( line )
				
				if clean_line:
					lines.append( clean_line )
			
			return lines
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_lines( raw_text: str ) -> List[str]'
			Logger( ).write( error )
			return [ ]
	
	def is_non_brand_line( self, line: str ) -> bool:
		"""Determine whether an OCR line is unlikely to be a brand name.

		Purpose:
			This method applies a conservative exclusion list for common regulatory, alcohol-content,
			net-contents, producer, importer, and government-warning terms. Lines containing these
			terms are skipped during brand extraction because they usually describe compliance text
			or product metadata rather than the brand itself.

		Args:
			line (str): Normalized OCR line to inspect.

		Returns:
			bool: ``True`` when the line should be skipped for brand extraction; otherwise,
			``False``. If evaluation fails, the exception is logged and ``True`` is returned so
			ambiguous lines are not incorrectly promoted to brand names.
		"""
		try:
			throw_if( 'line', line )
			
			text = line.upper( )
			exclusions = [
					'GOVERNMENT WARNING',
					'ALC.',
					'ALCOHOL',
					'NET CONTENTS',
					'BOTTLED BY',
					'PRODUCED BY',
					'DISTILLED BY',
					'IMPORTED BY',
					'CONTAINS',
					'PREGNANCY',
					'HEALTH PROBLEMS'
			]
			
			for exclusion in exclusions:
				if exclusion in text:
					return True
			
			return False
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'is_non_brand_line( line: str ) -> bool'
			Logger( ).write( error )
			return True
	
	def extract_brand_name( self, raw_text: str ) -> str:
		"""Extract a likely brand name from the first meaningful OCR label line.

		Purpose:
			The method examines normalized OCR lines in their original order and returns the first
			line that is not excluded by ``is_non_brand_line`` and is at least three characters long.
			This follows the common label-layout assumption that the brand or trade name appears near
			the top of the recognized label text, while regulatory lines and metadata should be
			ignored.

		Args:
			raw_text (str): Raw OCR text from the uploaded label.

		Returns:
			str: Extracted brand name, or an empty string when no suitable candidate is found. If
			extraction fails, the exception is logged and an empty string is returned.
		"""
		try:
			lines = self.get_lines( raw_text )
			
			for line in lines:
				if self.is_non_brand_line( line ):
					continue
				
				if len( line ) < 3:
					continue
				
				return line
			
			return ''
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_brand_name( raw_text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def extract_class_type( self, raw_text: str ) -> str:
		"""Extract likely class or type text from OCR lines.

		Purpose:
			This method scans normalized OCR lines for common alcohol beverage terms such as whiskey,
			bourbon, vodka, wine, beer, ale, cider, mezcal, and scotch. The first line containing a
			known class/type keyword is returned unchanged so downstream comparison retains the label
			wording observed by OCR.

		Args:
			raw_text (str): Raw OCR text from the uploaded label.

		Returns:
			str: Extracted class/type line, or an empty string when no keyword match is found. If
			extraction fails, the exception is logged and an empty string is returned.
		"""
		try:
			lines = self.get_lines( raw_text )
			keywords = [
					'WHISKEY',
					'WHISKY',
					'BOURBON',
					'VODKA',
					'GIN',
					'RUM',
					'TEQUILA',
					'BRANDY',
					'LIQUEUR',
					'WINE',
					'BEER',
					'ALE',
					'LAGER',
					'STOUT',
					'PORTER',
					'CIDER',
					'MEZCAL',
					'SCOTCH'
			]
			
			for line in lines:
				text = line.upper( )
				
				for keyword in keywords:
					if keyword in text:
						return line
			
			return ''
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_class_type( raw_text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def extract_alcohol_content( self, raw_text: str ) -> float | None:
		"""Extract alcohol by volume percentage from OCR text.

		Purpose:
			This method applies multiple regular-expression patterns to find common ABV expressions,
			including values followed by percent and alcohol indicators, values after ``ALC`` or
			``ALCOHOL``, and values followed directly by ``ABV``. The first matching numeric capture
			group is converted to ``float`` and returned.
	
			The method does not validate whether the resulting value is legally plausible for a
			particular beverage class. It only extracts the numeric value that OCR appears to have
			captured. Downstream rule logic remains responsible for comparison and tolerance handling.

		Args:
			raw_text (str): Raw OCR text from the uploaded label.

		Returns:
			float | None: Extracted ABV value, or ``None`` when no supported pattern is found or
			when parsing fails. Unexpected failures are logged before returning ``None``.
		"""
		try:
			throw_if( 'raw_text', raw_text )
			
			patterns = [
					r'(?P<value>\d{1,3}(?:\.\d+)?)\s*%\s*(?:ALC|ABV|ALCOHOL|BY\s+VOL)',
					r'(?:ALC\.?|ALCOHOL)\s*(?P<value>\d{1,3}(?:\.\d+)?)\s*%\s*(?:BY\s+VOL|ABV)?',
					r'(?P<value>\d{1,3}(?:\.\d+)?)\s*ABV'
			]
			
			for pattern in patterns:
				match = re.search( pattern, raw_text, flags=re.IGNORECASE )
				
				if match:
					return float( match.group( 'value' ) )
			
			return None
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_alcohol_content( raw_text: str ) -> float | None'
			Logger( ).write( error )
			return None
	
	def extract_net_contents( self, raw_text: str ) -> str:
		"""Extract the net contents statement from OCR text.

		Purpose:
			This method searches for a ``NET CONTENTS`` or ``CONTENTS`` label followed by a numeric
			amount and a supported unit of measure. Supported units include milliliters, liters,
			ounces, fluid ounces, gallons, and common abbreviations. When a match is found, the method
			returns a compact ``amount unit`` string.

		Args:
			raw_text (str): Raw OCR text from the uploaded label.

		Returns:
			str: Extracted net contents value, or an empty string when no supported pattern is
			found. If extraction fails, the exception is logged and an empty string is returned.
		"""
		try:
			throw_if( 'raw_text', raw_text )
			
			pattern = (
					r'(?:NET\s+CONTENTS?|CONTENTS?)\s*:?\s*'
					r'(?P<amount>\d+(?:\.\d+)?)\s*'
					r'(?P<unit>ML|MILLILITERS?|L|LITERS?|LITRES?|OZ|FL\.?\s*OZ|GALLON|GAL)'
			)
			match = re.search( pattern, raw_text, flags=re.IGNORECASE )
			
			if not match:
				return ''
			
			amount = match.group( 'amount' )
			unit = self.normalize_space( match.group( 'unit' ) )
			
			return f'{amount} {unit}'
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_net_contents( raw_text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def extract_producer_bottler( self, raw_text: str ) -> str:
		"""Extract the producer, bottler, importer, brewer, vintner, or distiller statement.

		Purpose:
			This method scans normalized OCR lines for common responsibility phrases such as
			``BOTTLED BY``, ``PRODUCED BY``, ``DISTILLED BY``, ``BREWED BY``, ``IMPORTED BY``,
			``PRODUCED AND BOTTLED BY``, and ``BOTTLED FOR``. The first matching line is returned
			unchanged to preserve the label wording captured by OCR.

		Args:
			raw_text (str): Raw OCR text from the uploaded label.

		Returns:
			str: Extracted producer, bottler, importer, brewer, vintner, or distiller statement,
			or an empty string when unavailable. If extraction fails, the exception is logged and
			an empty string is returned.
		"""
		try:
			lines = self.get_lines( raw_text )
			pattern = (
					r'(BOTTLED BY|PRODUCED BY|DISTILLED BY|BREWED BY|VINTED BY|'
					r'IMPORTED BY|PRODUCED AND BOTTLED BY|BOTTLED FOR)'
			)
			
			for line in lines:
				if re.search( pattern, line, flags=re.IGNORECASE ):
					return line
			
			return ''
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_producer_bottler( raw_text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def extract_country_of_origin( self, raw_text: str ) -> str:
		"""Extract a country-of-origin statement from OCR text.

		Purpose:
			This method scans normalized OCR lines for common origin phrases including
			``PRODUCT OF``, ``PRODUCED IN``, ``MADE IN``, and ``COUNTRY OF ORIGIN``. When a phrase is
			found, the text after the phrase is returned as the extracted country-of-origin value.

		Args:
			raw_text (str): Raw OCR text from the uploaded label.

		Returns:
			str: Extracted country-of-origin text, or an empty string when no supported origin
			statement is found. If extraction fails, the exception is logged and an empty string is
			returned.
		"""
		try:
			lines = self.get_lines( raw_text )
			pattern = r'(PRODUCT OF|PRODUCED IN|MADE IN|COUNTRY OF ORIGIN)\s*:?\s*(?P<country>.+)'
			
			for line in lines:
				match = re.search( pattern, line, flags=re.IGNORECASE )
				
				if match:
					return self.normalize_space( match.group( 'country' ) )
			
			return ''
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_country_of_origin( raw_text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def extract_government_warning( self, raw_text: str ) -> str:
		"""Extract the government warning statement from OCR text.

		Purpose:
			This method first normalizes the full OCR text and compares it to the canonical
			``GOVERNMENT_WARNING_TEXT``. If the canonical warning appears in the normalized OCR text,
			the canonical warning text is returned. Otherwise, the method searches for a line or text
			segment beginning with ``GOVERNMENT WARNING`` and returns the normalized matching segment.
	
			This method intentionally does not perform final legal validation of the warning. It only
			extracts the best available warning text so the warning validator and label rules can
			perform exact-text, near-match, prefix, and review checks.

		Args:
			raw_text (str): Raw OCR text from the uploaded label.

		Returns:
			str: Extracted government warning text, canonical warning text when exact canonical
			text is found, or an empty string when unavailable. If extraction fails, the exception
			is logged and an empty string is returned.
		"""
		try:
			throw_if( 'raw_text', raw_text )
			
			normalized_text = self.normalize_space( raw_text )
			canonical = self.normalize_space( GOVERNMENT_WARNING_TEXT )
			
			if canonical.upper( ) in normalized_text.upper( ):
				return GOVERNMENT_WARNING_TEXT
			
			match = re.search(
				r'(GOVERNMENT\s+WARNING\s*:?.+)',
				normalized_text,
				flags=re.IGNORECASE
			)
			
			if match:
				return self.normalize_space( match.group( 1 ) )
			
			return ''
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_government_warning( raw_text: str ) -> str'
			Logger( ).write( error )
			return ''
	
	def enrich( self, extracted_label: ExtractedLabel ) -> ExtractedLabel:
		"""Populate structured fields on an OCR ``ExtractedLabel`` instance.

		Purpose:
			This method reads ``raw_text`` from an existing ``ExtractedLabel`` and populates the
			structured extraction fields used by downstream verification. The method assigns brand
			name, class/type, alcohol content, net contents, producer/bottler, country of origin,
			and government warning values using the deterministic extraction helpers in this class.
	
			The method mutates and returns the same ``ExtractedLabel`` instance supplied by the
			caller. This preserves the original object identity and allows upstream OCR metadata,
			file metadata, normalized text, OCR timing, and image-quality notes to remain attached to
			the enriched object.

		Args:
			extracted_label: OCR extraction result to enrich with structured fields.

		Returns:
			ExtractedLabel: The supplied extraction result with structured fields populated when
			possible. If enrichment fails, the exception is logged and the original
			``extracted_label`` fallback is returned.
		"""
		try:
			throw_if( 'extracted_label', extracted_label )
			
			raw_text = extracted_label.raw_text or ''
			
			extracted_label.brand_name = self.extract_brand_name( raw_text )
			extracted_label.class_type = self.extract_class_type( raw_text )
			extracted_label.alcohol_content = self.extract_alcohol_content( raw_text )
			extracted_label.net_contents = self.extract_net_contents( raw_text )
			extracted_label.producer_bottler = self.extract_producer_bottler( raw_text )
			extracted_label.country_of_origin = self.extract_country_of_origin( raw_text )
			extracted_label.government_warning = self.extract_government_warning( raw_text )
			
			return extracted_label
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'enrich( extracted_label: ExtractedLabel ) -> ExtractedLabel'
			Logger( ).write( error )
			return extracted_label