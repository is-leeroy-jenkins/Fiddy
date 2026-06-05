'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                image_processor.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="image_processor.py" company="Terry D. Eppler">

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
        Provides deterministic image loading, orientation correction, quality-note generation,
        resizing, grayscale conversion, denoising, thresholding, and sharpening services for
        OCR preparation in the Fiddy label verification workflow.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from pathlib import Path
from typing import List

import cv2
import numpy as np
from PIL import Image, ImageOps

from booger import Error, Logger
from config import throw_if

# ==========================================================================================
# Image Processor
# ==========================================================================================

class ImageProcessor( ):
	"""Prepare uploaded label artwork for OCR processing.

	The ``ImageProcessor`` class contains deterministic preprocessing routines used before OCR
	is executed against uploaded alcohol label artwork. It supports file-based images and
	in-memory PIL images, applies EXIF orientation correction, converts unsupported image modes,
	upscales small images, converts images to OpenCV grayscale arrays, and applies grayscale,
	denoise, adaptive threshold, and sharpen operations.

	The class also collects reviewer-facing quality and processing notes. These notes are used
	by upstream OCR and verification workflows to explain why an image may have produced lower
	confidence OCR, why it was modified during preprocessing, or why a fallback image was used.

	Attributes:
		_image_path (Path): Path to the image currently being processed.
		_image (Image.Image): PIL image currently being processed.
		_images (List[Image.Image]): Reserved collection of images for workflows that process
			multiple pages or frames.
		_notes (List[str]): Reviewer-facing quality and preprocessing notes.
		_minimum_width (int): Preferred minimum image width for OCR preprocessing.
		_minimum_height (int): Preferred minimum image height for OCR preprocessing.
	"""
	
	_image_path: Path
	_image: Image.Image
	_images: List[ Image.Image ]
	_notes: List[ str ]
	_minimum_width: int
	_minimum_height: int
	
	def __init__( self, minimum_width: int = 800, minimum_height: int = 800 ) -> None:
		"""Initialize the image processor with minimum preferred OCR dimensions.

		The minimum dimensions are used by ``resize_for_ocr`` and fallback image creation. Images
		smaller than either threshold are upscaled proportionally so OCR receives larger text and
		line features without changing the image aspect ratio.

		Args:
			minimum_width (int): Minimum preferred image width for OCR.
			minimum_height (int): Minimum preferred image height for OCR.

		Returns:
			None.
		"""
		self._minimum_width = minimum_width
		self._minimum_height = minimum_height
		self._notes = [ ]
	
	@property
	def notes( self ) -> List[ str ]:
		"""Return image quality and preprocessing notes collected during processing.

		The notes list is reset by the high-level image processing methods and then populated by
		load, quality-estimation, resize, conversion, and preprocessing operations. Callers can
		use the notes to explain OCR limitations or preprocessing actions in downstream reports.

		Returns:
			List[str]: Current image quality and preprocessing notes.
		"""
		return self._notes
	
	def load_image( self, image_path: str | Path ) -> Image.Image:
		"""Load an image file from disk and apply EXIF orientation correction.

		This method validates the supplied path, confirms that it exists, opens the image through
		PIL, and applies EXIF transpose handling so images captured on phones or cameras are
		oriented correctly before OCR preprocessing begins. Images in modes other than ``RGB`` or
		``L`` are converted to ``RGB`` and a note is recorded for reviewer visibility.

		Args:
			image_path (str | Path): Path to the image file to load.

		Returns:
			Image.Image: Loaded PIL image. If loading fails, the exception is logged, a processing
			note is appended, and a white RGB fallback image using the configured minimum
			dimensions is returned.
		"""
		try:
			throw_if( 'image_path', image_path )
			
			self._image_path = Path( image_path )
			throw_if( 'image_path', self._image_path.exists( ) )
			
			self._image = Image.open( self._image_path )
			self._image = ImageOps.exif_transpose( self._image )
			
			if self._image.mode not in ('RGB', 'L'):
				self._notes.append( f'Converted image mode from {self._image.mode} to RGB.' )
				self._image = self._image.convert( 'RGB' )
			
			return self._image
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'load_image( image_path: str | Path ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'Image could not be loaded.' )
			return Image.new( 'RGB', (self._minimum_width, self._minimum_height), 'white' )
	
	def ensure_rgb( self, image: Image.Image ) -> Image.Image:
		"""Ensure an image is in RGB mode before OpenCV processing.

		OpenCV conversion paths in this module expect an RGB-compatible image array. This method
		keeps RGB images unchanged and converts all other modes to RGB while recording a note that
		the conversion occurred. The method does not resize, threshold, or otherwise enhance the
		image.

		Args:
			image (Image.Image): PIL image to inspect and convert when necessary.

		Returns:
			Image.Image: RGB image when conversion succeeds. If conversion fails, the exception is
			logged, a note is appended, and the original image fallback is returned.
		"""
		try:
			throw_if( 'image', image )
			
			self._image = image
			if self._image.mode != 'RGB':
				self._notes.append( f'Converted image mode from {self._image.mode} to RGB.' )
				self._image = self._image.convert( 'RGB' )
			
			return self._image
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'ensure_rgb( image: Image.Image ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'Image mode conversion failed.' )
			return image
	
	def resize_for_ocr( self, image: Image.Image ) -> Image.Image:
		"""Upscale small label images to improve OCR readability.

		This method compares the image dimensions to the configured minimum OCR dimensions. When
		the image already meets both thresholds, it is returned unchanged. When either dimension
		is below the threshold, the method calculates a proportional scale factor that satisfies
		both minimums, records the original and new dimensions in the notes list, and resizes the
		image using high-quality Lanczos resampling.

		Args:
			image (Image.Image): PIL image to resize when needed.

		Returns:
			Image.Image: Original image when no resize is needed, or a proportionally upscaled
			image when dimensions are below the preferred OCR size. If resizing fails, the
			exception is logged, a note is appended, and the original image fallback is returned.
		"""
		try:
			throw_if( 'image', image )
			
			self._image = image
			width, height = self._image.size
			
			if width >= self._minimum_width and height >= self._minimum_height:
				return self._image
			
			scale_width = self._minimum_width / width
			scale_height = self._minimum_height / height
			scale = max( scale_width, scale_height )
			
			new_width = int( width * scale )
			new_height = int( height * scale )
			
			self._notes.append(
				f'Upscaled image from {width}x{height} to {new_width}x{new_height} for OCR.'
			)
			
			return self._image.resize( (new_width, new_height), Image.Resampling.LANCZOS )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'resize_for_ocr( image: Image.Image ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'Image resize step failed.' )
			return image
	
	def to_cv_gray( self, image: Image.Image ) -> np.ndarray:
		"""Convert a PIL image to an OpenCV grayscale array.

		This method first ensures the input image is RGB, converts it to a NumPy array, and then
		uses OpenCV to convert the RGB array into grayscale. The grayscale result is used by
		quality estimation and OCR preprocessing routines that require single-channel intensity
		data.

		Args:
			image (Image.Image): PIL image to convert.

		Returns:
			np.ndarray: Grayscale OpenCV image array. If conversion fails, the exception is logged,
			a note is appended, and a white fallback grayscale array using the configured minimum
			dimensions is returned.
		"""
		try:
			throw_if( 'image', image )
			
			self._image = self.ensure_rgb( image )
			array = np.array( self._image )
			return cv2.cvtColor( array, cv2.COLOR_RGB2GRAY )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_cv_gray( image: Image.Image ) -> np.ndarray'
			Logger( ).write( error )
			self._notes.append( 'Grayscale conversion failed.' )
			return np.full(
				(self._minimum_height, self._minimum_width),
				255,
				dtype=np.uint8
			)
	
	def preprocess_for_ocr( self, image: Image.Image ) -> Image.Image:
		"""Apply deterministic preprocessing to improve OCR extraction.

		The preprocessing pipeline first resizes small images, then converts the result to
		grayscale. It applies OpenCV non-local means denoising, adaptive Gaussian thresholding,
		and a simple sharpening kernel. The output is converted back into a PIL image for
		compatibility with OCR engines that accept PIL images.

		This method is intentionally deterministic and does not call remote services. It provides
		a consistent preprocessing path for local OCR and records a note describing the major
		operations applied.

		Args:
			image (Image.Image): PIL image to preprocess for OCR.

		Returns:
			Image.Image: OCR-prepared PIL image. If preprocessing fails, the exception is logged,
			a note is appended, and the original image fallback is returned.
		"""
		try:
			throw_if( 'image', image )
			
			self._image = self.resize_for_ocr( image )
			gray = self.to_cv_gray( self._image )
			
			denoised = cv2.fastNlMeansDenoising( gray, None, 10, 7, 21 )
			thresholded = cv2.adaptiveThreshold(
				denoised,
				255,
				cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
				cv2.THRESH_BINARY,
				31,
				11
			)
			
			kernel = np.array(
				[
						[ 0, -1, 0 ],
						[ -1, 5, -1 ],
						[ 0, -1, 0 ]
				]
			)
			
			sharpened = cv2.filter2D( thresholded, -1, kernel )
			processed = Image.fromarray( sharpened )
			self._notes.append( 'Applied grayscale, denoise, threshold, and sharpen steps.' )
			
			return processed
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'preprocess_for_ocr( image: Image.Image ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'Image preprocessing failed; using original image.' )
			return image
	
	def estimate_quality_notes( self, image: Image.Image ) -> List[ str ]:
		"""Estimate basic image quality issues that may reduce OCR confidence.

		This method performs lightweight quality checks intended to produce reviewer-facing
		notes. It records whether the image is smaller than preferred OCR dimensions, whether
		the average grayscale brightness suggests the image may be too dark or overexposed, and
		whether grayscale standard deviation suggests low contrast. If no issue is detected and
		no prior note exists, it records that no obvious image quality issues were found.

		Args:
			image (Image.Image): PIL image to evaluate.

		Returns:
			List[str]: Current image quality and preprocessing notes. If quality estimation fails,
			the exception is logged, a failure note is appended, and the current notes list is
			returned.
		"""
		try:
			throw_if( 'image', image )
			
			self._image = image
			width, height = self._image.size
			gray = self.to_cv_gray( self._image )
			
			brightness = float( np.mean( gray ) )
			contrast = float( np.std( gray ) )
			
			if width < self._minimum_width or height < self._minimum_height:
				self._notes.append( 'Image is smaller than preferred OCR dimensions.' )
			
			if brightness < 60:
				self._notes.append( 'Image may be too dark for reliable OCR.' )
			
			if brightness > 235:
				self._notes.append( 'Image may be overexposed for reliable OCR.' )
			
			if contrast < 25:
				self._notes.append( 'Image may have low contrast.' )
			
			if not self._notes:
				self._notes.append( 'No obvious image quality issues detected.' )
			
			return self._notes
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'estimate_quality_notes( image: Image.Image ) -> List[str]'
			Logger( ).write( error )
			self._notes.append( 'Image quality estimation failed.' )
			return self._notes
	
	def process_image_file( self, image_path: str | Path ) -> Image.Image:
		"""Load, evaluate, and preprocess an image file for OCR.

		This high-level file workflow resets the notes list, loads the image from disk, estimates
		basic quality issues, and applies deterministic OCR preprocessing. It is the primary
		entry point for file-based OCR preparation.

		Args:
			image_path (str | Path): Path to the image file to load and preprocess.

		Returns:
			Image.Image: OCR-prepared image. If processing fails, the exception is logged, a note
			is appended, and a white RGB fallback image using the configured minimum dimensions is
			returned.
		"""
		try:
			throw_if( 'image_path', image_path )
			
			self._notes = [ ]
			self._image = self.load_image( image_path )
			self.estimate_quality_notes( self._image )
			
			return self.preprocess_for_ocr( self._image )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'process_image_file( image_path: str | Path ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'Image file processing failed.' )
			return Image.new( 'RGB', (self._minimum_width, self._minimum_height), 'white' )
	
	def process_pil_image( self, image: Image.Image ) -> Image.Image:
		"""Evaluate and preprocess an in-memory PIL image for OCR.

		This high-level in-memory workflow resets the notes list, applies EXIF orientation
		correction to the supplied PIL image, estimates basic quality issues, and applies the
		same deterministic OCR preprocessing used by file-based images. It is useful for images
		already loaded by another component, images extracted from PDFs, or images supplied by
		tests.

		Args:
			image (Image.Image): PIL image to evaluate and preprocess.

		Returns:
			Image.Image: OCR-prepared image. If processing fails, the exception is logged, a note
			is appended, and the original image fallback is returned.
		"""
		try:
			throw_if( 'image', image )
			
			self._notes = [ ]
			self._image = ImageOps.exif_transpose( image )
			self.estimate_quality_notes( self._image )
			
			return self.preprocess_for_ocr( self._image )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'process_pil_image( image: Image.Image ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'In-memory image processing failed.' )
			return image