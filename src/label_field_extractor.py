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
    label_field_extractor.py
  </summary>
  ******************************************************************************************
'''
from __future__ import annotations

import re
from typing import List

from config import throw_if
from src.constants import GOVERNMENT_WARNING_TEXT
from src.models import ExtractedLabel

class LabelFieldExtractor( ):
	"""
		Purpose:
		--------
		Extract structured alcohol-label fields from OCR text using deterministic pattern matching.
	
		Parameters:
		-----------
		None
	
		Returns:
		--------
		None
	"""
	_raw_text: str
	_lines: List[ str ]
	
	def normalize_space( self, value: str ) -> str:
		"""
		
			Purpose:
			--------
			Normalize repeated whitespace in a text value.
	
			Parameters:
			-----------
			value (str): Source text.
	
			Returns:
			--------
			str: Whitespace-normalized text.
			
		"""
		try:
			throw_if( 'value', value )
			return re.sub( r'\s+', ' ', str( value ) ).strip( )
		except Exception:
			return ''
	
	def get_lines( self, raw_text: str ) -> List[ str ]:
		"""
		
			Purpose:
			--------
			Return non-empty OCR text lines.
	
			Parameters:
			-----------
			raw_text (str): OCR text.
	
			Returns:
			--------
			List[str]: Non-empty OCR text lines.
		
		"""
		try:
			throw_if( 'raw_text', raw_text )
			
			lines = [ ]
			
			for line in raw_text.splitlines( ):
				clean_line = self.normalize_space( line )
				
				if clean_line:
					lines.append( clean_line )
			
			return lines
		except Exception:
			return [ ]
	
	def is_non_brand_line( self, line: str ) -> bool:
		"""
		
			Purpose:
			--------
			Determine whether a line is unlikely to be the brand name.
	
			Parameters:
			-----------
			line (str): OCR line.
	
			Returns:
			--------
			bool: True when the line should be skipped for brand extraction.
		
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
		except Exception:
			return True
	
	def extract_brand_name( self, raw_text: str ) -> str:
		"""
		
			Purpose:
			--------
			Extract a likely brand name from the first meaningful OCR label line.
	
			Parameters:
			-----------
			raw_text (str): OCR text.
	
			Returns:
			--------
			str: Extracted brand name, or empty string when unavailable.
		
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
		except Exception:
			return ''
	
	def extract_class_type( self, raw_text: str ) -> str:
		"""
		
			Purpose:
			--------
			Extract likely class/type text from OCR lines.
	
			Parameters:
			-----------
			raw_text (str): OCR text.
	
			Returns:
			--------
			str: Extracted class/type, or empty string when unavailable.
		
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
		except Exception:
			return ''
	
	def extract_alcohol_content( self, raw_text: str ) -> float | None:
		"""
			
			Purpose:
			--------
			Extract alcohol by volume percentage from OCR text.
	
			Parameters:
			-----------
			raw_text (str): OCR text.
	
			Returns:
			--------
			float | None: Extracted ABV value, or None when unavailable.
		
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
		except Exception:
			return None
	
	def extract_net_contents( self, raw_text: str ) -> str:
		"""
			
			Purpose:
			--------
			Extract net contents from OCR text.
	
			Parameters:
			-----------
			raw_text (str): OCR text.
	
			Returns:
			--------
			str: Extracted net contents, or empty string when unavailable.
		
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
		except Exception:
			return ''
	
	def extract_producer_bottler( self, raw_text: str ) -> str:
		"""
		
			Purpose:
			--------
			Extract producer, bottler, importer, brewer, vintner, or distiller statement.
	
			Parameters:
			-----------
			raw_text (str): OCR text.
	
			Returns:
			--------
			str: Extracted producer/bottler statement, or empty string when unavailable.
		
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
		except Exception:
			return ''
	
	def extract_country_of_origin( self, raw_text: str ) -> str:
		"""
			
			Purpose:
			--------
			Extract country-of-origin statement from OCR text.
	
			Parameters:
			-----------
			raw_text (str): OCR text.
	
			Returns:
			--------
			str: Extracted country-of-origin text, or empty string when unavailable.
		
		"""
		try:
			lines = self.get_lines( raw_text )
			pattern = r'(PRODUCT OF|PRODUCED IN|MADE IN|COUNTRY OF ORIGIN)\s*:?\s*(?P<country>.+)'
			
			for line in lines:
				match = re.search( pattern, line, flags=re.IGNORECASE )
				
				if match:
					return self.normalize_space( match.group( 'country' ) )
			
			return ''
		except Exception:
			return ''
	
	def extract_government_warning( self, raw_text: str ) -> str:
		"""
		
			Purpose:
			--------
			Extract the government warning text from OCR text.
	
			Parameters:
			-----------
			raw_text (str): OCR text.
	
			Returns:
			--------
			str: Extracted warning text, or empty string when unavailable.
		
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
		except Exception:
			return ''
	
	def enrich( self, extracted_label: ExtractedLabel ) -> ExtractedLabel:
		"""
		
			Purpose:
			--------
			Populate structured label fields on an OCR ExtractedLabel instance.
	
			Parameters:
			-----------
			extracted_label (ExtractedLabel): OCR extraction result.
	
			Returns:
			--------
			ExtractedLabel: Enriched extraction result with structured fields populated.
		
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
		except Exception:
			return extracted_label