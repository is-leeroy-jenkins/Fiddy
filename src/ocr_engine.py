'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                ocr_engine.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-06-2026
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
        PDF-to-image conversion, OCR timeout handling, page limiting, image downscaling,
        progress status callbacks, note collection, normalized text generation, and structured
        ExtractedLabel creation for downstream label verification.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, List, Optional

import pytesseract
from pdf2image import convert_from_path
from PIL import Image

import config as cfg
from booger import Error, Logger
from config import throw_if
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

	The engine remains local-first and deterministic. It delegates image preparation to
	``ImageProcessor``, visual diagnostics to ``VisualQualityAnalyzer``, and text normalization
	to ``TextNormalizer``. OCR notes are collected throughout extraction so reviewers can
	understand timeout conditions, preprocessing steps, unsupported file types, quality warnings,
	PDF page-limit behavior, and OCR fallback behavior.

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
		_timeout_seconds (int): Tesseract timeout threshold.
		_ocr_config (str): Tesseract configuration string.
		_max_pdf_pages (int): Maximum PDF pages processed per uploaded PDF.
		_max_image_dimension (int): Maximum image width or height before downscaling.
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
	_timeout_seconds: int
	_ocr_config: str
	_max_pdf_pages: int
	_max_image_dimension: int
	
	def __init__( self ) -> None:
		"""Initialize the OCR engine and local helper services.

		Purpose:
			Create the image processor, text normalizer, visual-quality analyzer, and note
			collection used by OCR extraction runs. The constructor also reads timeout, OCR config,
			PDF page limit, image-size limit, and optional Tesseract executable settings from
			configuration. When ``TESSERACT_CMD`` is configured, the command path is assigned to
			``pytesseract``.

		Parameters:
			None.

		Returns:
			None.
		"""
		try:
			self._processor = ImageProcessor(
				minimum_width=int( getattr( cfg, 'OCR_MINIMUM_WIDTH', 800 ) ),
				minimum_height=int( getattr( cfg, 'OCR_MINIMUM_HEIGHT', 800 ) )
			)
			
			self._normalizer = TextNormalizer( )
			self._quality_analyzer = VisualQualityAnalyzer( )
			self._notes = [ ]
			self._timeout_seconds = int( getattr( cfg, 'OCR_TIMEOUT_SECONDS', 5 ) )
			self._ocr_config = str( getattr( cfg, 'OCR_CONFIG', '--oem 3 --psm 6' ) )
			self._max_pdf_pages = int( getattr( cfg, 'MAX_PDF_PAGES', 1 ) )
			self._max_image_dimension = int( getattr( cfg, 'MAX_IMAGE_DIMENSION', 2400 ) )
			
			if getattr( cfg, 'TESSERACT_CMD', None ):
				pytesseract.pytesseract.tesseract_cmd = str( cfg.TESSERACT_CMD )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = '__init__( self ) -> None'
			Logger( ).write( error )
			self._processor = ImageProcessor( )
			self._normalizer = TextNormalizer( )
			self._quality_analyzer = VisualQualityAnalyzer( )
			self._notes = [ ]
			self._timeout_seconds = 5
			self._ocr_config = '--oem 3 --psm 6'
			self._max_pdf_pages = 1
			self._max_image_dimension = 2400
	
	@property
	def notes( self ) -> List[ str ]:
		"""Return OCR, preprocessing, and image-quality notes.

		Purpose:
			Expose the note list from the most recent extraction workflow. The notes may include
			visual quality status, readability metrics, preprocessing actions, OCR timeout
			messages, unsupported file-type messages, PDF page-limit messages, and extraction
			failure messages.

		Parameters:
			None.

		Returns:
			List[str]: OCR and image-quality notes from the latest extraction run.
		"""
		return self._notes
	
	def report_progress( self, progress_callback: Optional[ Callable[ [ str ], None ] ],
			message: str ) -> None:
		"""Send a status message to an optional OCR progress callback.

		Purpose:
			Allow Streamlit or batch-processing callers to display OCR progress without coupling
			the OCR engine to any specific UI framework. Callback failures are logged and do not
			interrupt OCR extraction.

		Parameters:
			progress_callback (Optional[Callable[[str], None]]): Optional callback that receives a
				status message.
			message (str): Progress message to send.

		Returns:
			None.
		"""
		try:
			if progress_callback:
				progress_callback( message )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'report_progress( self, progress_callback: Optional[Callable[[str], None]], message: str ) -> None'
			Logger( ).write( error )
			return None
	
	def get_file_type( self, file_path: str | Path ) -> str:
		"""Return a lowercase file extension without the leading period.

		Purpose:
			Normalize a file path to ``Path`` and extract the suffix used by supported file-type
			checks. The method does not validate whether the file exists or whether the extension is
			supported.

		Parameters:
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
			error.method = 'get_file_type( self, file_path: str | Path ) -> str'
			Logger( ).write( error )
			return ''
	
	def is_supported_image( self, file_path: str | Path ) -> bool:
		"""Determine whether a file path points to a supported image type.

		Purpose:
			Extract the file extension through ``get_file_type`` and check it against
			``SUPPORTED_IMAGE_TYPES``. This method is used by ``extract_text`` to route image
			files through image OCR.

		Parameters:
			file_path (str | Path): File path to inspect.

		Returns:
			bool: ``True`` when the file extension is a supported image type; otherwise, ``False``.
		"""
		try:
			throw_if( 'file_path', file_path )
			
			file_type = self.get_file_type( file_path )
			return file_type in SUPPORTED_IMAGE_TYPES
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'is_supported_image( self, file_path: str | Path ) -> bool'
			Logger( ).write( error )
			return False
	
	def is_supported_pdf( self, file_path: str | Path ) -> bool:
		"""Determine whether a file path points to a supported document type.

		Purpose:
			Extract the file extension through ``get_file_type`` and check it against
			``SUPPORTED_DOCUMENT_TYPES``. In the current workflow, this routes PDF files to
			page-image conversion before OCR.

		Parameters:
			file_path (str | Path): File path to inspect.

		Returns:
			bool: ``True`` when the file extension is a supported document type; otherwise,
			``False``.
		"""
		try:
			throw_if( 'file_path', file_path )
			
			file_type = self.get_file_type( file_path )
			return file_type in SUPPORTED_DOCUMENT_TYPES
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'is_supported_pdf( self, file_path: str | Path ) -> bool'
			Logger( ).write( error )
			return False
	
	def create_quality_notes( self, quality_result: VisualQualityResult ) -> List[ str ]:
		"""Convert a visual-quality result into reviewer-facing OCR notes.

		Purpose:
			Translate the structured ``VisualQualityResult`` into plain-language notes carried on
			the final ``ExtractedLabel``. The notes include visual quality status, readability score,
			brightness, contrast, blur score, glare ratio, skew angle, warnings, and
			recommendations.

		Parameters:
			quality_result (VisualQualityResult): Visual-quality analysis result.

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
			error.method = 'create_quality_notes( self, quality_result: VisualQualityResult ) -> List[str]'
			Logger( ).write( error )
			return [
					'Visual quality notes could not be created.'
			]
	
	def normalize_label_text( self, raw_text: str ) -> str:
		"""Normalize raw OCR text using the configured text normalizer.

		Purpose:
			Call ``TextNormalizer.normalize_label_text`` when available and return a safe fallback
			when normalization fails. This preserves OCR output flow even when normalizer behavior
			changes during development.

		Parameters:
			raw_text (str): Raw OCR text to normalize.

		Returns:
			str: Normalized OCR text, or an empty string when normalization fails.
		"""
		try:
			if not raw_text:
				return ''
			
			return self._normalizer.normalize_label_text( raw_text )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'normalize_label_text( self, raw_text: str ) -> str'
			Logger( ).write( error )
			self._notes.append( 'OCR text normalization failed.' )
			return ''
	
	def downscale_image_for_ocr( self, image: Image.Image, file_name: str = '' ) -> Image.Image:
		"""Downscale oversized images before OCR processing.

		Purpose:
			Reduce very large image dimensions before preprocessing and OCR so the five-second SLA
			is more predictable. Images whose maximum dimension is already below the configured
			limit are returned unchanged. Aspect ratio is preserved.

		Parameters:
			image (Image.Image): PIL image to inspect and possibly resize.
			file_name (str): Logical file name used in reviewer-facing notes.

		Returns:
			Image.Image: Original image or resized copy. If resizing fails, the original image is
			returned.
		"""
		try:
			throw_if( 'image', image )
			
			width, height = image.size
			max_dimension = max( width, height )
			
			if self._max_image_dimension <= 0:
				return image
			
			if max_dimension <= self._max_image_dimension:
				return image
			
			scale = self._max_image_dimension / float( max_dimension )
			new_width = max( 1, int( width * scale ) )
			new_height = max( 1, int( height * scale ) )
			
			self._notes.append(
				f'Downscaled oversized image {file_name or "label"} from '
				f'{width}x{height} to {new_width}x{new_height} for OCR performance.'
			)
			
			return image.resize( (new_width, new_height), Image.Resampling.LANCZOS )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'downscale_image_for_ocr( self, image: Image.Image, file_name: str = "" ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'Image downscaling failed; original image was used.' )
			return image
	
	def analyze_image_quality_file( self, file_path: str | Path ) -> VisualQualityResult:
		"""Analyze one image file and append visual-quality notes.

		Purpose:
			Run visual-quality analysis for a file-based image using
			``VisualQualityAnalyzer.analyze_file``. The resulting metrics and recommendations are
			converted to OCR notes and appended to the engine note collection before returning the
			structured visual-quality result.

		Parameters:
			file_path (str | Path): Uploaded image file path.

		Returns:
			VisualQualityResult: Visual-quality analysis result. If analysis fails, the exception is
			logged, a failure note is appended, and a fallback ``VisualQualityResult`` is returned.
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
			error.method = 'analyze_image_quality_file( self, file_path: str | Path ) -> VisualQualityResult'
			Logger( ).write( error )
			self._notes.append( 'Visual quality analysis failed for image file.' )
			return VisualQualityResult( file_name=str( file_path ) )
	
	def analyze_image_quality_pil( self, image: Image.Image,
			file_name: str = '' ) -> VisualQualityResult:
		"""Analyze one in-memory PIL image and append visual-quality notes.

		Purpose:
			Run visual-quality analysis for an in-memory image using
			``VisualQualityAnalyzer.analyze_image``. The result is converted to OCR notes and
			appended to the engine note collection. The optional file name is used only as a logical
			reporting name for the returned result.

		Parameters:
			image (Image.Image): Image to analyze.
			file_name (str): Logical file name for reporting.

		Returns:
			VisualQualityResult: Visual-quality analysis result. If analysis fails, the exception is
			logged, a failure note is appended, and a fallback result is returned.
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
			error.method = 'analyze_image_quality_pil( self, image: Image.Image, file_name: str = "" ) -> VisualQualityResult'
			Logger( ).write( error )
			self._notes.append( 'Visual quality analysis failed for image.' )
			return VisualQualityResult( file_name=file_name )
	
	def image_to_text( self, image: Image.Image, file_name: str = '',
			progress_callback: Optional[ Callable[ [ str ], None ] ] = None ) -> str:
		"""Extract text from one in-memory image using local OCR.

		Purpose:
			Analyze image quality, downscale oversized images, preprocess the image through
			``ImageProcessor.process_pil_image``, carry processor notes into the OCR note
			collection, and invoke ``pytesseract.image_to_string`` using configured OCR language,
			timeout, and Tesseract config.

		Parameters:
			image (Image.Image): PIL image to process with OCR.
			file_name (str): Logical file name used in quality-analysis reporting.
			progress_callback (Optional[Callable[[str], None]]): Optional progress callback.

		Returns:
			str: OCR-extracted text with leading and trailing whitespace removed. If OCR times out
			or fails, the exception is logged, a reviewer-facing note is appended, and an empty
			string is returned.
		"""
		try:
			throw_if( 'image', image )
			
			self.report_progress( progress_callback, f'Analyzing image quality: {file_name}' )
			image = self.downscale_image_for_ocr( image, file_name )
			self.analyze_image_quality_pil( image, file_name )
			
			self.report_progress( progress_callback, f'Preprocessing image for OCR: {file_name}' )
			processed = self._processor.process_pil_image( image )
			self._notes.extend( self._processor.notes )
			
			self.report_progress( progress_callback, f'Running OCR: {file_name}' )
			text = pytesseract.image_to_string(
				processed,
				lang=str( getattr( cfg, 'OCR_LANGUAGE', 'eng' ) ),
				timeout=self._timeout_seconds,
				config=self._ocr_config
			)
			
			self.report_progress( progress_callback, f'OCR complete: {file_name}' )
			return text.strip( )
		except RuntimeError as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'image_to_text( self, image: Image.Image, file_name: str = "", progress_callback: Optional[Callable[[str], None]] = None ) -> str'
			Logger( ).write( error )
			self._notes.append( 'OCR timed out before completing image extraction.' )
			self.report_progress( progress_callback, f'OCR timeout: {file_name}' )
			return ''
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'image_to_text( self, image: Image.Image, file_name: str = "", progress_callback: Optional[Callable[[str], None]] = None ) -> str'
			Logger( ).write( error )
			self._notes.append( 'OCR extraction failed for one image.' )
			self.report_progress( progress_callback, f'OCR failed: {file_name}' )
			return ''
	
	def extract_image_file_text( self, file_path: str | Path,
			progress_callback: Optional[ Callable[ [ str ], None ] ] = None ) -> str:
		"""Extract OCR text from a supported image file.

		Purpose:
			Perform file-based visual-quality analysis, load the image through ``ImageProcessor``,
			downscale oversized images, preprocess the image, extend OCR notes with processor notes,
			and invoke Tesseract OCR with configured language, timeout, and OCR config.

		Parameters:
			file_path (str | Path): Path to the uploaded image file.
			progress_callback (Optional[Callable[[str], None]]): Optional progress callback.

		Returns:
			str: OCR-extracted text with leading and trailing whitespace removed. If OCR times out
			or fails, the exception is logged, a reviewer-facing note is appended, and an empty
			string is returned.
		"""
		try:
			throw_if( 'file_path', file_path )
			
			self._file_path = Path( file_path )
			self.report_progress( progress_callback,
				f'Analyzing file quality: {self._file_path.name}' )
			self.analyze_image_quality_file( self._file_path )
			
			self.report_progress( progress_callback, f'Loading image: {self._file_path.name}' )
			image = self._processor.load_image( self._file_path )
			image = self.downscale_image_for_ocr( image, self._file_path.name )
			
			self.report_progress( progress_callback,
				f'Preprocessing image: {self._file_path.name}' )
			processed = self._processor.process_pil_image( image )
			self._notes.extend( self._processor.notes )
			
			self.report_progress( progress_callback, f'Running OCR: {self._file_path.name}' )
			text = pytesseract.image_to_string(
				processed,
				lang=str( getattr( cfg, 'OCR_LANGUAGE', 'eng' ) ),
				timeout=self._timeout_seconds,
				config=self._ocr_config
			)
			
			self.report_progress( progress_callback, f'OCR complete: {self._file_path.name}' )
			return text.strip( )
		except RuntimeError as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_image_file_text( self, file_path: str | Path, progress_callback: Optional[Callable[[str], None]] = None ) -> str'
			Logger( ).write( error )
			self._notes.append( 'OCR timed out before completing image file extraction.' )
			self.report_progress( progress_callback, f'OCR timeout: {Path( file_path ).name}' )
			return ''
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_image_file_text( self, file_path: str | Path, progress_callback: Optional[Callable[[str], None]] = None ) -> str'
			Logger( ).write( error )
			self._notes.append( 'OCR extraction failed for image file.' )
			self.report_progress( progress_callback,
				f'OCR failed: {Path( file_path ).name if file_path else ""}' )
			return ''
	
	def convert_pdf_to_pages( self, file_path: str | Path ) -> List[ Image.Image ]:
		"""Convert a PDF into a bounded list of page images.

		Purpose:
			Convert the supplied PDF into images while respecting the configured page limit. The
			prototype defaults to processing the first page to keep per-label processing predictable
			under the five-second SLA. When the limit is less than one, it is treated as one.

		Parameters:
			file_path (str | Path): Path to the uploaded PDF file.

		Returns:
			List[Image.Image]: Converted PDF page images. If conversion fails, the exception is
			logged and an empty list is returned.
		"""
		try:
			throw_if( 'file_path', file_path )
			
			self._file_path = Path( file_path )
			page_limit = max( 1, int( self._max_pdf_pages ) )
			
			pages = convert_from_path(
				self._file_path,
				dpi=200,
				first_page=1,
				last_page=page_limit
			)
			
			if page_limit == 1:
				self._notes.append(
					'PDF processing limited to first page for prototype SLA control.' )
			else:
				self._notes.append(
					f'PDF processing limited to first {page_limit} pages for prototype SLA control.'
				)
			
			return pages
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'convert_pdf_to_pages( self, file_path: str | Path ) -> List[Image.Image]'
			Logger( ).write( error )
			self._notes.append( 'PDF conversion failed before OCR could run.' )
			return [ ]
	
	def extract_pdf_file_text( self, file_path: str | Path,
			progress_callback: Optional[ Callable[ [ str ], None ] ] = None ) -> str:
		"""Convert a PDF into images and extract OCR text from bounded pages.

		Purpose:
			Convert the supplied PDF into page images using the configured page limit and process
			each converted page through ``image_to_text``. Non-empty page OCR output is collected
			and joined with blank lines so the final raw OCR text preserves page separation.

		Parameters:
			file_path (str | Path): Path to the uploaded PDF file.
			progress_callback (Optional[Callable[[str], None]]): Optional progress callback.

		Returns:
			str: OCR-extracted text from converted PDF pages. If PDF conversion or page OCR fails
			at the method level, the exception is logged, a reviewer-facing note is appended, and an
			empty string is returned.
		"""
		try:
			throw_if( 'file_path', file_path )
			
			self._file_path = Path( file_path )
			self.report_progress( progress_callback, f'Converting PDF: {self._file_path.name}' )
			pages = self.convert_pdf_to_pages( self._file_path )
			text_parts = [ ]
			
			for index, page in enumerate( pages, start=1 ):
				page_name = f'{self._file_path.name} page {index}'
				self.report_progress( progress_callback, f'Running OCR on {page_name}' )
				text = self.image_to_text( page, page_name, progress_callback )
				
				if text:
					text_parts.append( text )
			
			self.report_progress( progress_callback, f'PDF OCR complete: {self._file_path.name}' )
			return '\n\n'.join( text_parts ).strip( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_pdf_file_text( self, file_path: str | Path, progress_callback: Optional[Callable[[str], None]] = None ) -> str'
			Logger( ).write( error )
			self._notes.append( 'OCR extraction failed for PDF file.' )
			self.report_progress( progress_callback,
				f'PDF OCR failed: {Path( file_path ).name if file_path else ""}' )
			return ''
	
	def create_extracted_label( self ) -> ExtractedLabel:
		"""Create the structured OCR extraction result for the active file.

		Purpose:
			Build the ``ExtractedLabel`` object returned to the verifier. The method preserves the
			existing model contract by returning file name, file type, raw text, normalized text, OCR
			engine name, OCR duration, and image-quality notes.

		Parameters:
			None.

		Returns:
			ExtractedLabel: Structured OCR result. If object creation fails, a reviewer-safe
			fallback result is returned.
		"""
		try:
			return ExtractedLabel(
				file_name=self._file_name,
				file_type=self._file_type,
				raw_text=self._raw_text,
				normalized_text=self._normalized_text,
				ocr_engine=str( getattr( cfg, 'OCR_ENGINE', 'tesseract' ) ),
				ocr_seconds=self._ocr_seconds,
				image_quality_notes=self._notes
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_extracted_label( self ) -> ExtractedLabel'
			Logger( ).write( error )
			return ExtractedLabel(
				file_name=getattr( self, '_file_name', '' ),
				file_type=getattr( self, '_file_type', '' ),
				raw_text='',
				normalized_text='',
				ocr_engine=str( getattr( cfg, 'OCR_ENGINE', 'tesseract' ) ),
				ocr_seconds=0.0,
				image_quality_notes=[
						'OCR result could not be created.'
				]
			)
	
	def create_fallback_label( self, file_path: str | Path,
			message: str = 'OCR extraction could not be completed.' ) -> ExtractedLabel:
		"""Create a reviewer-safe fallback extracted-label result.

		Purpose:
			Return a structured OCR fallback result without exposing raw exception details to the
			reviewer. The fallback includes the file name when available, the detected file type
			when available, the configured OCR engine name, zero OCR seconds, and one
			reviewer-facing note.

		Parameters:
			file_path (str | Path): File path associated with the failed extraction.
			message (str): Reviewer-facing fallback note.

		Returns:
			ExtractedLabel: Reviewer-safe fallback OCR result.
		"""
		try:
			file_name = Path( file_path ).name if file_path else ''
			file_type = self.get_file_type( file_path ) if file_path else ''
			
			return ExtractedLabel(
				file_name=file_name,
				file_type=file_type,
				raw_text='',
				normalized_text='',
				ocr_engine=str( getattr( cfg, 'OCR_ENGINE', 'tesseract' ) ),
				ocr_seconds=0.0,
				image_quality_notes=[
						message
				]
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_fallback_label( self, file_path: str | Path, message: str ) -> ExtractedLabel'
			Logger( ).write( error )
			return ExtractedLabel(
				file_name='',
				file_type='',
				raw_text='',
				normalized_text='',
				ocr_engine=str( getattr( cfg, 'OCR_ENGINE', 'tesseract' ) ),
				ocr_seconds=0.0,
				image_quality_notes=[
						'OCR extraction could not be completed.'
				]
			)
	
	def extract_text( self, file_path: str | Path,
			progress_callback: Optional[ Callable[ [ str ], None ] ] = None ) -> ExtractedLabel:
		"""Extract text from one uploaded label file and return a structured result.

		Purpose:
			Serve as the main OCR entry point for the verifier. The method resets OCR notes,
			records start time, captures file metadata, routes supported images through image OCR,
			routes supported PDFs through bounded PDF page conversion and OCR, records an
			unsupported-file note when the type is not supported, normalizes raw OCR text, measures
			elapsed OCR time, and returns an ``ExtractedLabel``.

		Parameters:
			file_path (str | Path): Path to the uploaded image or PDF label file.
			progress_callback (Optional[Callable[[str], None]]): Optional progress callback.

		Returns:
			ExtractedLabel: Structured OCR result. If extraction fails unexpectedly, the exception
			is logged and a reviewer-safe fallback result is returned.
		"""
		try:
			throw_if( 'file_path', file_path )
			
			started = time.perf_counter( )
			self._notes = [ ]
			self._file_path = Path( file_path )
			self._file_name = self._file_path.name
			self._file_type = self.get_file_type( self._file_path )
			
			self.report_progress( progress_callback, f'Starting OCR: {self._file_name}' )
			
			if not self._file_path.exists( ):
				self._notes.append(
					'Uploaded file could not be found in temporary processing storage.' )
				self._raw_text = ''
			elif self.is_supported_image( self._file_path ):
				self._raw_text = self.extract_image_file_text(
					self._file_path,
					progress_callback=progress_callback
				)
			elif self.is_supported_pdf( self._file_path ):
				self._raw_text = self.extract_pdf_file_text(
					self._file_path,
					progress_callback=progress_callback
				)
			else:
				self._notes.append( f'Unsupported file type: {self._file_type}' )
				self._raw_text = ''
			
			self.report_progress( progress_callback, f'Normalizing OCR text: {self._file_name}' )
			self._normalized_text = self.normalize_label_text( self._raw_text )
			self._ocr_seconds = time.perf_counter( ) - started
			
			if not self._raw_text:
				self._notes.append( 'No readable OCR text was extracted from the uploaded file.' )
			
			self._notes.append( f'OCR completed in {self._ocr_seconds:.3f} seconds.' )
			self.report_progress( progress_callback, f'OCR finished: {self._file_name}' )
			
			return self.create_extracted_label( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'extract_text( self, file_path: str | Path, progress_callback: Optional[Callable[[str], None]] = None ) -> ExtractedLabel'
			Logger( ).write( error )
			self.report_progress( progress_callback, 'OCR extraction failed.' )
			return self.create_fallback_label(
				file_path=file_path,
				message='OCR extraction could not be completed.'
			)