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
        Provides local OCR extraction services for Fiddy image and PDF label files.

        This module coordinates image preprocessing, visual-quality analysis, Tesseract OCR,
        PDF-to-image conversion, OCR timing, note collection, normalized text generation, and
        structured ExtractedLabel creation for downstream label verification.
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

from booger import Error, Logger
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
	"""Extract text from alcohol label images and PDF files using local OCR.

	The ``OcrEngine`` class is the OCR coordination layer for the Fiddy verification workflow.
	It determines file type, checks whether uploaded files are supported image or document
	types, runs image-quality analysis, preprocesses images, invokes local Tesseract OCR,
	converts PDFs into page images, normalizes extracted text, records processing time, and
	returns structured ``ExtractedLabel`` objects.

	The engine is intentionally local and deterministic from the application perspective. It
	delegates image preparation to ``ImageProcessor``, visual diagnostics to
	``VisualQualityAnalyzer``, and text normalization to ``TextNormalizer``. OCR notes are
	collected throughout extraction so reviewers can understand timeout conditions,
	preprocessing steps, unsupported file types, quality warnings, and OCR fallback behavior.

	Attributes:
		_file_path (Path): Path to the file currently being processed.
		_file_name (str): Name of the file currently being processed.
		_file_type (str): Lowercase extension for the current file without the leading period.
		_raw_text (str): Raw OCR text extracted from the current file.
		_normalized_text (str): Normalized OCR text generated from the raw OCR output.
		_ocr_seconds (float): OCR extraction duration in seconds.
		_processor (ImageProcessor): Image preprocessing service.
		_normalizer (TextNormalizer): Text normalization service.
		_quality_analyzer (VisualQualityAnalyzer): Visual-quality analysis service.
		_quality_result (VisualQualityResult): Visual-quality result for the current image.
		_notes (List[str]): OCR, preprocessing, and image-quality notes from the latest run.
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
		"""Initialize the OCR engine and local helper services.

		The constructor creates the image processor, text normalizer, visual-quality analyzer,
		and empty notes collection used by OCR extraction runs. When ``TESSERACT_CMD`` is
		configured, the constructor also assigns it to ``pytesseract`` so local OCR uses the
		explicit executable path.

		Returns:
			None.
		"""
		self._processor = ImageProcessor( )
		self._normalizer = TextNormalizer( )
		self._quality_analyzer = VisualQualityAnalyzer( )
		self._notes = [ ]
		
		if TESSERACT_CMD:
			pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
	
	@property
	def notes( self ) -> List[ str ]:
		"""Return OCR, preprocessing, and image-quality notes.

		The notes list reflects the most recent extraction workflow. It may include visual
		quality status, readability metrics, preprocessing actions, OCR timeout messages,
		unsupported file-type messages, and extraction failure messages.

		Returns:
			List[str]: OCR and image-quality notes from the latest extraction run.
		"""
		return self._notes
	
	def get_file_type( self, file_path: str | Path ) -> str:
		"""Return a lowercase file extension without the leading period.

		This helper normalizes a file path to ``Path`` and extracts the suffix used by supported
		file-type checks. It does not validate whether the file exists or whether the extension is
		supported.

		Args:
			file_path (str | Path): File path to inspect.

		Returns:
			str: Lowercase file type without the leading period. If inspection fails, the
			exception is logged and an empty string is returned.
		"""
		try:
			throw_if( 'file_path', file_path )
			
			self._file_path = Path( file_path )
			return self._file_path.suffix.lower( ).replace( '.', '' )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_file_type( file_path: str | Path ) -> str'
			Logger( ).write( error )
			return ''
	
	def is_supported_image( self, file_path: str | Path ) -> bool:
		"""Determine whether a file path points to a supported image type.

		This method extracts the file extension through ``get_file_type`` and checks it against
		``SUPPORTED_IMAGE_TYPES``. It is used by ``extract_text`` to decide whether to route the
		file through image OCR.

		Args:
			file_path (str | Path): File path to inspect.

		Returns:
			bool: ``True`` when the file extension is a supported image type; otherwise,
			``False``. If the check fails, the exception is logged and ``False`` is returned.
		"""
		try:
			throw_if( 'file_path', file_path )
			
			file_type = self.get_file_type( file_path )
			return file_type in SUPPORTED_IMAGE_TYPES
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'is_supported_image( file_path: str | Path ) -> bool'
			Logger( ).write( error )
			return False
	
	def is_supported_pdf( self, file_path: str | Path ) -> bool:
		"""Determine whether a file path points to a supported document type.

		This method extracts the file extension through ``get_file_type`` and checks it against
		``SUPPORTED_DOCUMENT_TYPES``. In the current workflow this is used to route PDF files to
		page-image conversion before OCR.

		Args:
			file_path (str | Path): File path to inspect.

		Returns:
			bool: ``True`` when the file extension is a supported document type; otherwise,
			``False``. If the check fails, the exception is logged and ``False`` is returned.
		"""
		try:
			throw_if( 'file_path', file_path )
			
			file_type = self.get_file_type( file_path )
			return file_type in SUPPORTED_DOCUMENT_TYPES
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'is_supported_pdf( file_path: str | Path ) -> bool'
			Logger( ).write( error )
			return False
	
	def create_quality_notes( self, quality_result: VisualQualityResult ) -> List[ str ]:
		"""Convert a visual-quality result into reviewer-facing OCR notes.

		This method translates the structured ``VisualQualityResult`` into plain-language notes
		that can be carried on the final ``ExtractedLabel``. The notes include visual quality
		status, readability score, brightness, contrast, blur score, glare ratio, skew angle,
		warnings, and recommendations.

		Args:
			quality_result (VisualQualityResult): Visual quality analysis result.

		Returns:
			List[str]: Reviewer-facing quality notes. If note creation fails, the exception is
			logged and a fallback note is returned.
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
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_quality_notes( quality_result: VisualQualityResult ) -> List[str]'
			Logger( ).write( error )
			return [ 'Visual quality notes could not be created.' ]
	
	def analyze_image_quality_file( self, file_path: str | Path ) -> VisualQualityResult:
		"""Analyze one image file and append visual-quality notes.

		This method runs visual-quality analysis for a file-based image using
		``VisualQualityAnalyzer.analyze_file``. The resulting metrics and recommendations are
		converted to OCR notes and appended to the engine note collection before returning the
		structured visual-quality result.

		Args:
			file_path (str | Path): Uploaded image file path.

		Returns:
			VisualQualityResult: Visual quality analysis result. If analysis fails, the exception
			is logged, a failure note is appended, and a fallback ``VisualQualityResult`` is
			returned with the supplied file name.
		"""
		try:
			throw_if( 'file_path', file_path )
			self._file_path = Path( file_path )
			self._quality_result = self._quality_analyzer.analyze_file( self._file_path )
			self._notes.extend( self.create_quality_notes( self._quality_result ) )
			
			return self._quality_result
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'analyze_image_quality_file( file_path: str | Path ) -> VisualQualityResult'
			Logger( ).write( error )
			self._notes.append( 'Visual quality analysis failed for image file.' )
			return VisualQualityResult( file_name=str( file_path ) )
	
	def analyze_image_quality_pil( self, image: Image.Image,
			file_name: str = '' ) -> VisualQualityResult:
		"""Analyze one in-memory PIL image and append visual-quality notes.

		This method runs visual-quality analysis for an in-memory image using
		``VisualQualityAnalyzer.analyze_image``. The result is converted to OCR notes and appended
		to the engine note collection. The optional file name is used only as a logical reporting
		name for the returned result.

		Args:
			image (Image.Image): Image to analyze.
			file_name (str): Logical file name for reporting.

		Returns:
			VisualQualityResult: Visual quality analysis result. If analysis fails, the exception
			is logged, a failure note is appended, and a fallback ``VisualQualityResult`` is
			returned using the supplied logical file name.
		"""
		try:
			throw_if( 'image', image )
			self._quality_result = self._quality_analyzer.analyze_image( image, file_name )
			self._notes.extend( self.create_quality_notes( self._quality_result ) )
			
			return self._quality_result
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'analyze_image_quality_pil( self, *args ) -> VisualQualityResult'
			Logger( ).write( error )
			self._notes.append( 'Visual quality analysis failed for image.' )
			return VisualQualityResult( file_name=file_name )
	
	def image_to_text( self, image: Image.Image, file_name: str = '' ) -> str:
		"""Extract text from one in-memory image using local OCR.

		This method analyzes the image quality, preprocesses the image through
		``ImageProcessor.process_pil_image``, carries processor notes into the OCR note
		collection, and invokes ``pytesseract.image_to_string`` using the configured OCR
		language, timeout, and page-segmentation mode.

		Args:
			image (Image.Image): PIL image to process with OCR.
			file_name (str): Logical file name used in quality-analysis reporting.

		Returns:
			str: OCR-extracted text with leading and trailing whitespace removed. If OCR times out
			or fails, the exception is logged, the original reviewer-facing note is appended, and
			an empty string is returned.
		"""
		try:
			throw_if( 'image', image )
			self.analyze_image_quality_pil( image, file_name )
			processed = self._processor.process_pil_image( image )
			self._notes.extend( self._processor.notes )
			text = pytesseract.image_to_string( processed, lang=OCR_LANGUAGE,
				timeout=OCR_TIMEOUT_SECONDS, config='--psm 6' )
			
			return text.strip( )
		except RuntimeError as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'image_to_text( image: Image.Image, file_name: str ) -> str'
			Logger( ).write( error )
			self._notes.append( 'OCR timed out before completing image extraction.' )
			return ''
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'image_to_text( image: Image.Image, file_name: str ) -> str'
			Logger( ).write( error )
			self._notes.append( 'OCR extraction failed for one image.' )
			return ''
	
	def extract_image_file_text( self, file_path: str | Path ) -> str:
		"""Extract OCR text from a supported image file.

		This method performs file-based visual-quality analysis, preprocesses the image file
		through ``ImageProcessor.process_image_file``, extends the OCR note collection with
		processor notes, and invokes Tesseract OCR with the configured language, timeout, and
		page-segmentation mode.

		Args:
			file_path (str | Path): Path to the uploaded image file.

		Returns:
			str: OCR-extracted text with leading and trailing whitespace removed. If OCR times out
			or fails, the exception is logged, the original reviewer-facing note is appended, and
			an empty string is returned.
		"""
		try:
			throw_if( 'file_path', file_path )
			self._file_path = Path( file_path )
			self.analyze_image_quality_file( self._file_path )
			processed = self._processor.process_image_file( self._file_path )
			self._notes.extend( self._processor.notes )
			text = pytesseract.image_to_string( processed, lang=OCR_LANGUAGE,
				timeout=OCR_TIMEOUT_SECONDS, config='--psm 6' )
			
			return text.strip( )
		except RuntimeError as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_image_file_text( file_path: str | Path ) -> str'
			Logger( ).write( error )
			self._notes.append( 'OCR timed out before completing image file extraction.' )
			return ''
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_image_file_text( file_path: str | Path ) -> str'
			Logger( ).write( error )
			self._notes.append( 'OCR extraction failed for image file.' )
			return ''
	
	def extract_pdf_file_text( self, file_path: str | Path ) -> str:
		"""Convert a PDF into images and extract OCR text from each page.

		This method converts the supplied PDF into page images at 200 DPI and processes each page
		through ``image_to_text``. Non-empty page OCR output is collected and joined with blank
		lines so the final raw OCR text preserves page separation.

		Args:
			file_path (str | Path): Path to the uploaded PDF file.

		Returns:
			str: OCR-extracted text from all PDF pages. If PDF conversion or page OCR processing
			fails at the method level, the exception is logged, the original failure note is
			appended, and an empty string is returned.
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
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_pdf_file_text( file_path: str | Path ) -> str'
			Logger( ).write( error )
			self._notes.append( 'OCR extraction failed for PDF file.' )
			return ''
	
	def extract_text( self, file_path: str | Path ) -> ExtractedLabel:
		"""Extract text from one uploaded label file and return a structured result.

		This method is the main OCR entry point for the verifier. It resets OCR notes, records
		start time, captures file metadata, routes supported images through image OCR, routes
		supported PDFs through PDF page conversion and OCR, records an unsupported-file note when
		the type is not supported, normalizes raw OCR text, measures elapsed OCR time, and returns
		an ``ExtractedLabel`` containing raw text, normalized text, OCR engine name, processing
		seconds, and accumulated notes.

		Args:
			file_path (str | Path): Path to the uploaded image or PDF label file.

		Returns:
			ExtractedLabel: Structured OCR result. If extraction fails unexpectedly, the exception
			is logged and the original fallback ``ExtractedLabel`` is returned with a
			reviewer-facing OCR failure note.
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
			return ExtractedLabel( file_name=self._file_name, file_type=self._file_type,
				raw_text=self._raw_text, normalized_text=self._normalized_text,
				ocr_engine=OCR_ENGINE, ocr_seconds=self._ocr_seconds,
				image_quality_notes=self._notes )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_text( file_path: str | Path ) -> ExtractedLabel'
			Logger( ).write( error )
			return ExtractedLabel( file_name=Path( file_path ).name if file_path else '',
				file_type='', raw_text='', normalized_text='', ocr_engine=OCR_ENGINE,
				ocr_seconds=0.0, image_quality_notes=[ 'OCR extraction could not be completed.' ] )