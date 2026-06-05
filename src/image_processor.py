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
        image_processor.py
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from pathlib import Path
from typing import List

import cv2
import numpy as np
from PIL import Image, ImageOps

from config import throw_if

# ==========================================================================================
# Image Processor
# ==========================================================================================

class ImageProcessor( ):
	"""
	Purpose:
	--------
	Prepare uploaded label artwork for OCR by loading image files, converting image modes,
	correcting orientation, increasing contrast, denoising, sharpening, and producing
	reviewer-facing image quality notes.

	Parameters:
	-----------
	None

	Returns:
	--------
	None
	"""
	
	_image_path: Path
	_image: Image.Image
	_images: List[ Image.Image ]
	_notes: List[ str ]
	_minimum_width: int
	_minimum_height: int
	
	def __init__( self, minimum_width: int = 800, minimum_height: int = 800 ) -> None:
		"""
		Purpose:
		--------
		Initialize the image processor with minimum preferred OCR dimensions.

		Parameters:
		-----------
		minimum_width (int): Minimum preferred image width for OCR.
		minimum_height (int): Minimum preferred image height for OCR.

		Returns:
		--------
		None
		"""
		self._minimum_width = minimum_width
		self._minimum_height = minimum_height
		self._notes = [ ]
	
	@property
	def notes( self ) -> List[ str ]:
		"""
		Purpose:
		--------
		Return image quality and preprocessing notes collected during processing.

		Parameters:
		-----------
		None

		Returns:
		--------
		List[str]: Image quality notes.
		"""
		return self._notes
	
	def load_image( self, image_path: str | Path ) -> Image.Image:
		"""
		Purpose:
		--------
		Load an image file from disk and apply EXIF orientation correction.

		Parameters:
		-----------
		image_path (str | Path): Path to the image file.

		Returns:
		--------
		Image.Image: Loaded PIL image.
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
		except Exception:
			self._notes.append( 'Image could not be loaded.' )
			return Image.new( 'RGB', (self._minimum_width, self._minimum_height), 'white' )
	
	def ensure_rgb( self, image: Image.Image ) -> Image.Image:
		"""
		Purpose:
		--------
		Ensure an image is in RGB mode before OpenCV processing.

		Parameters:
		-----------
		image (Image.Image): PIL image to convert.

		Returns:
		--------
		Image.Image: RGB image.
		"""
		try:
			throw_if( 'image', image )
			
			self._image = image
			if self._image.mode != 'RGB':
				self._notes.append( f'Converted image mode from {self._image.mode} to RGB.' )
				self._image = self._image.convert( 'RGB' )
			
			return self._image
		except Exception:
			self._notes.append( 'Image mode conversion failed.' )
			return image
	
	def resize_for_ocr( self, image: Image.Image ) -> Image.Image:
		"""
		Purpose:
		--------
		Upscale small label images to improve OCR readability.

		Parameters:
		-----------
		image (Image.Image): PIL image to resize when needed.

		Returns:
		--------
		Image.Image: Original or resized image.
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
		except Exception:
			self._notes.append( 'Image resize step failed.' )
			return image
	
	def to_cv_gray( self, image: Image.Image ) -> np.ndarray:
		"""
		Purpose:
		--------
		Convert a PIL image to an OpenCV grayscale array.

		Parameters:
		-----------
		image (Image.Image): PIL image to convert.

		Returns:
		--------
		np.ndarray: Grayscale OpenCV image array.
		"""
		try:
			throw_if( 'image', image )
			
			self._image = self.ensure_rgb( image )
			array = np.array( self._image )
			return cv2.cvtColor( array, cv2.COLOR_RGB2GRAY )
		except Exception:
			self._notes.append( 'Grayscale conversion failed.' )
			return np.full(
				(self._minimum_height, self._minimum_width),
				255,
				dtype=np.uint8
			)
	
	def preprocess_for_ocr( self, image: Image.Image ) -> Image.Image:
		"""
		Purpose:
		--------
		Apply deterministic preprocessing to improve OCR extraction from label artwork.

		Parameters:
		-----------
		image (Image.Image): PIL image to preprocess.

		Returns:
		--------
		Image.Image: OCR-prepared image.
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
		except Exception:
			self._notes.append( 'Image preprocessing failed; using original image.' )
			return image
	
	def estimate_quality_notes( self, image: Image.Image ) -> List[ str ]:
		"""
		
			Purpose:
			--------
			Estimate simple image quality issues that may affect OCR confidence.
	
			Parameters:
			-----------
			image (Image.Image): PIL image to evaluate.
	
			Returns:
			--------
			List[str]: Image quality notes.
			
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
		except Exception:
			self._notes.append( 'Image quality estimation failed.' )
			return self._notes
	
	def process_image_file( self, image_path: str | Path ) -> Image.Image:
		"""
		
			Purpose:
			--------
			Load, evaluate, and preprocess an image file for OCR.
	
			Parameters:
			-----------
			image_path (str | Path): Path to the image file.
	
			Returns:
			--------
			Image.Image: OCR-prepared image.
			
		"""
		try:
			throw_if( 'image_path', image_path )
			
			self._notes = [ ]
			self._image = self.load_image( image_path )
			self.estimate_quality_notes( self._image )
			
			return self.preprocess_for_ocr( self._image )
		except Exception:
			self._notes.append( 'Image file processing failed.' )
			return Image.new( 'RGB', (self._minimum_width, self._minimum_height), 'white' )
	
	def process_pil_image( self, image: Image.Image ) -> Image.Image:
		"""
			
			Purpose:
			--------
			Evaluate and preprocess an in-memory PIL image for OCR.
	
			Parameters:
			-----------
			image (Image.Image): PIL image to process.
	
			Returns:
			--------
			Image.Image: OCR-prepared image.
		
		"""
		try:
			throw_if( 'image', image )
			
			self._notes = [ ]
			self._image = ImageOps.exif_transpose( image )
			self.estimate_quality_notes( self._image )
			
			return self.preprocess_for_ocr( self._image )
		except Exception:
			self._notes.append( 'In-memory image processing failed.' )
			return image

