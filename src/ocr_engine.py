'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                ocr_engine.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="ocr_engine.py" company="Terry D. Eppler">

         Fiddy: AI-Powered Alcohol Label Verification App

     Permission is hereby granted, free of charge, to any person obtaining a copy
     of this software and associated documentation files
     to deal in the Software without restriction,
     including without limitation the rights to use,
     copy, modify, merge, publish, distribute, sublicense,
     and/or sell copies of the Software,
     and to permit persons to whom the Software is furnished to do so,
     subject to the following conditions:

     The above copyright notice and this permission notice shall be included in all
     copies or substantial portions of the Software.

     THE SOFTWARE IS PROVIDED WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
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
from src.visual_quality import VisualQualityAnalyzer, VisualQualityResult

# ==========================================================================================
# OCR Engine
# ==========================================================================================

class OcrEngine( ):
	"""
		Purpose:
		--------
		Extract text from alcohol label images and PDF files using a local OCR backend while
		collecting image-quality and readability diagnostics.
	
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
	_quality_analyzer: VisualQualityAnalyzer
	_quality_result: VisualQualityResult
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
		self._quality_analyzer = VisualQualityAnalyzer( )
		self._notes = [ ]
		
		if TESSERACT_CMD:
			pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
	
	@property
	def notes( self ) -> List[ str ]:
		"""
			Purpose:
			--------
			Return OCR, preprocessing, and image-quality notes from the latest extraction run.
	
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
	
	def create_quality_notes( self, quality_result: VisualQualityResult ) -> List[ str ]:
		"""
			Purpose:
			--------
			Convert a visual quality result into reviewer-facing OCR notes.
	
			Parameters:
			-----------
			quality_result (VisualQualityResult): Visual quality analysis result.
	
			Returns:
			--------
			List[str]: Reviewer-facing quality notes.
		"""
		try:
			throw_if( 'quality_result', quality_result )
			
			notes = [
					f'Visual quality status: {quality_result.status}.',
					f'Readability score: {quality_result.readability_score:.1f}/100.',
					f'Brightness: {quality_result.brightness:.1f}; '
					f'contrast: {quality_result.contrast:.1f}; '
					f'blur score: {quality_result.blur_score:.1f}; '
					f'glare ratio: {quality_result.glare_ratio:.3f}; '
					f'skew angle: {quality_result.skew_angle:.1f}.'
			]
			
			for warning in quality_result.warnings:
				notes.append( f'Visual warning: {warning}' )
			
			for recommendation in quality_result.recommendations:
				notes.append( f'Visual recommendation: {recommendation}' )
			
			return notes
		except Exception:
			return [
					'Visual quality notes could not be created.'
			]
	
	def analyze_image_quality_file( self, file_path: str | Path ) -> VisualQualityResult:
		"""
			Purpose:
			--------
			Analyze one image file and append visual quality notes to the OCR note collection.
	
			Parameters:
			-----------
			file_path (str | Path): Uploaded image file path.
	
			Returns:
			--------
			VisualQualityResult: Visual quality analysis result.
		"""
		try:
			throw_if( 'file_path', file_path )
			
			self._file_path = Path( file_path )
			self._quality_result = self._quality_analyzer.analyze_file( self._file_path )
			self._notes.extend( self.create_quality_notes( self._quality_result ) )
			
			return self._quality_result
		except Exception:
			self._notes.append( 'Visual quality analysis failed for image file.' )
			return VisualQualityResult( file_name=str( file_path ) )
	
	def analyze_image_quality_pil( self, image: Image.Image,
			file_name: str = '' ) -> VisualQualityResult:
		"""
			Purpose:
			--------
			Analyze one in-memory PIL image and append visual quality notes to OCR notes.
	
			Parameters:
			-----------
			image (Image.Image): Image to analyze.
			file_name (str): Logical file name for reporting.
	
			Returns:
			--------
			VisualQualityResult: Visual quality analysis result.
		"""
		try:
			throw_if( 'image', image )
			
			self._quality_result = self._quality_analyzer.analyze_image( image, file_name )
			self._notes.extend( self.create_quality_notes( self._quality_result ) )
			
			return self._quality_result
		except Exception:
			self._notes.append( 'Visual quality analysis failed for image.' )
			return VisualQualityResult( file_name=file_name )
	
	def image_to_text( self, image: Image.Image, file_name: str = '' ) -> str:
		"""
			Purpose:
			--------
			Extract text from a single in-memory image using local OCR.
	
			Parameters:
			-----------
			image (Image.Image): PIL image to process with OCR.
			file_name (str): Logical file name for reporting.
	
			Returns:
			--------
			str: OCR-extracted text.
		"""
		try:
			throw_if( 'image', image )
			
			self.analyze_image_quality_pil( image, file_name )
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
			self.analyze_image_quality_file( self._file_path )
			
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
			
			for index, page in enumerate( pages, start=1 ):
				page_name = f'{self._file_path.name} page {index}'
				text = self.image_to_text( page, page_name )
				
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
				file_name=Path( file_path ).name if file_path else '',
				file_type='',
				raw_text='',
				normalized_text='',
				ocr_engine=OCR_ENGINE,
				ocr_seconds=0.0,
				image_quality_notes=[
						'OCR extraction could not be completed.'
				]
			)
