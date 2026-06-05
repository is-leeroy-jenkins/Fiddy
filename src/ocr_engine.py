'''
    ******************************************************************************************
      Assembly:                Veritas
      Filename:                ocr_engine.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="ocr_engine.py" company="Terry D. Eppler">

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
        ocr_engine.py
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import time
from pathlib import Path
from typing import List

import pytesseract
from pdf2image import convert_from_path
from PIL import Image

from config import OCR_ENGINE, OCR_LANGUAGE, OCR_TIMEOUT_SECONDS, TESSERACT_CMD, throw_if
from src.constants import SUPPORTED_DOCUMENT_TYPES, SUPPORTED_IMAGE_TYPES
from src.image_processor import ImageProcessor
from src.models import ExtractedLabel
from src.normalizer import TextNormalizer

class OcrEngine( ):
	"""
	Purpose:
	--------
	Extract text from alcohol label images and PDF files using a local OCR backend.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
	"""
	
	_file_path: Path
	_file_name: str
	_file_type: str
	_raw_text: str
	_normalized_text: str
	_ocr_seconds: float
	_processor: ImageProcessor
	_normalizer: TextNormalizer
	_notes: List[ str ]
	
	def __init__( self ) -> None:
		"""
		Purpose:
		--------
		Initialize the OCR engine and configure local Tesseract when a command path is
		provided through configuration.

		Parameters:
		-----------
		None

		Returns:
		--------
		None
		"""
		self._processor = ImageProcessor( )
		self._normalizer = TextNormalizer( )
		self._notes = [ ]
		
		if TESSERACT_CMD:
			pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
	
	@property
	def notes( self ) -> List[ str ]:
		"""
		Purpose:
		--------
		Return OCR and image quality notes from the latest extraction run.

		Parameters:
		-----------
		None

		Returns:
		--------
		List[str]: OCR and image quality notes.
		"""
		return self._notes
	
	def get_file_type( self, file_path: str | Path ) -> str:
		"""
		Purpose:
		--------
		Return a lowercase file extension without the leading period.

		Parameters:
		-----------
		file_path (str | Path): File path to inspect.

		Returns:
		--------
		str: Lowercase file type.
		"""
		try:
			throw_if( 'file_path', file_path )
			
			self._file_path = Path( file_path )
			return self._file_path.suffix.lower( ).replace( '.', '' )
		except Exception:
			return ''
	
	def is_supported_image( self, file_path: str | Path ) -> bool:
		"""
		
			Purpose:
			--------
			Determine whether a file path points to a supported image type.
	
			Parameters:
			-----------
			file_path (str | Path): File path to inspect.
	
			Returns:
			--------
			bool: True when the extension is a supported image type; otherwise, False.
			
		"""
		try:
			throw_if( 'file_path', file_path )
			
			file_type = self.get_file_type( file_path )
			return file_type in SUPPORTED_IMAGE_TYPES
		except Exception:
			return False
	
	def is_supported_pdf( self, file_path: str | Path ) -> bool:
		"""
			
			Purpose:
			--------
			Determine whether a file path points to a supported PDF type.
	
			Parameters:
			-----------
			file_path (str | Path): File path to inspect.
	
			Returns:
			--------
			bool: True when the extension is PDF; otherwise, False.
		
		"""
		try:
			throw_if( 'file_path', file_path )
			
			file_type = self.get_file_type( file_path )
			return file_type in SUPPORTED_DOCUMENT_TYPES
		except Exception:
			return False
	
	def image_to_text( self, image: Image.Image ) -> str:
		"""
		
			Purpose:
			--------
			Extract text from a single in-memory image using local OCR.
	
			Parameters:
			-----------
			image (Image.Image): PIL image to process with OCR.
	
			Returns:
			--------
			str: OCR-extracted text.
			
		"""
		try:
			throw_if( 'image', image )
			
			processed = self._processor.process_pil_image( image )
			self._notes.extend( self._processor.notes )
			
			text = pytesseract.image_to_string(
				processed,
				lang=OCR_LANGUAGE,
				timeout=OCR_TIMEOUT_SECONDS,
				config='--psm 6'
			)
			
			return text.strip( )
		except RuntimeError:
			self._notes.append( 'OCR timed out before completing image extraction.' )
			return ''
		except Exception:
			self._notes.append( 'OCR extraction failed for one image.' )
			return ''
	
	def extract_image_file_text( self, file_path: str | Path ) -> str:
		"""
		
			Purpose:
			--------
			Extract OCR text from a supported image file.
	
			Parameters:
			-----------
			file_path (str | Path): Path to the uploaded image file.
	
			Returns:
			--------
			str: OCR-extracted text.
			
		"""
		try:
			throw_if( 'file_path', file_path )
			
			self._file_path = Path( file_path )
			processed = self._processor.process_image_file( self._file_path )
			self._notes.extend( self._processor.notes )
			
			text = pytesseract.image_to_string(
				processed,
				lang=OCR_LANGUAGE,
				timeout=OCR_TIMEOUT_SECONDS,
				config='--psm 6'
			)
			
			return text.strip( )
		except RuntimeError:
			self._notes.append( 'OCR timed out before completing image file extraction.' )
			return ''
		except Exception:
			self._notes.append( 'OCR extraction failed for image file.' )
			return ''
	
	def extract_pdf_file_text( self, file_path: str | Path ) -> str:
		"""
		
			Purpose:
			--------
			Convert a PDF into images and extract OCR text from each page.
	
			Parameters:
			-----------
			file_path (str | Path): Path to the uploaded PDF file.
	
			Returns:
			--------
			str: OCR-extracted text from all PDF pages.
			
		"""
		try:
			throw_if( 'file_path', file_path )
			
			self._file_path = Path( file_path )
			pages = convert_from_path( self._file_path, dpi=200 )
			text_parts = [ ]
			
			for page in pages:
				text = self.image_to_text( page )
				if text:
					text_parts.append( text )
			
			return '\n\n'.join( text_parts ).strip( )
		except Exception:
			self._notes.append( 'OCR extraction failed for PDF file.' )
			return ''
	
	def extract_text( self, file_path: str | Path ) -> ExtractedLabel:
		"""
		
			Purpose:
			--------
			Extract text from one uploaded label file and return a structured extraction result.
	
			Parameters:
			-----------
			file_path (str | Path): Path to the uploaded image or PDF file.
	
			Returns:
			--------
			ExtractedLabel: Structured OCR result.
			
		"""
		try:
			throw_if( 'file_path', file_path )
			
			started = time.perf_counter( )
			self._notes = [ ]
			self._file_path = Path( file_path )
			self._file_name = self._file_path.name
			self._file_type = self.get_file_type( self._file_path )
			
			if self.is_supported_image( self._file_path ):
				self._raw_text = self.extract_image_file_text( self._file_path )
			elif self.is_supported_pdf( self._file_path ):
				self._raw_text = self.extract_pdf_file_text( self._file_path )
			else:
				self._notes.append( f'Unsupported file type: {self._file_type}' )
				self._raw_text = ''
			
			self._normalized_text = self._normalizer.normalize_label_text( self._raw_text )
			self._ocr_seconds = time.perf_counter( ) - started
			
			return ExtractedLabel(
				file_name=self._file_name,
				file_type=self._file_type,
				raw_text=self._raw_text,
				normalized_text=self._normalized_text,
				ocr_engine=OCR_ENGINE,
				ocr_seconds=self._ocr_seconds,
				image_quality_notes=self._notes
			)
		except Exception:
			return ExtractedLabel(
				file_name=str( file_path ),
				file_type='',
				raw_text='',
				normalized_text='',
				ocr_engine=OCR_ENGINE,
				ocr_seconds=0.0,
				image_quality_notes=[
						'OCR extraction could not be completed.'
				]
			)
