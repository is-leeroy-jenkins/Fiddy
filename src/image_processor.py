'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                image_processor.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-06-2026
    ******************************************************************************************
    <copyright file="image_processor.py" company="Terry D. Eppler">

         Fiddy: AI-Powered Alcohol Label Verification App

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
        Provides deterministic image loading, orientation correction, size normalization,
        quality-note generation, grayscale conversion, conservative deskew, contrast-aware
        preprocessing, denoising, thresholding, and sharpening services for OCR preparation in
        the Fiddy label verification workflow.

        This module intentionally uses local, deterministic image processing only. It does not
        claim to perform future-scope capabilities such as perspective correction, true glare
        removal, or automatic label cropping. Instead, it detects common image-quality risks,
        applies safe OCR-oriented preprocessing, and records reviewer-facing notes when image
        quality may still require human review.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps

import config as cfg
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
	upscales small images, optionally downscales oversized images, estimates image quality,
	selects a preprocessing profile, applies conservative deskew when safe, converts images to
	OpenCV grayscale arrays, and applies contrast-aware denoising, thresholding, and sharpening.

	The class also collects reviewer-facing quality and processing notes. These notes explain why
	an image may have produced lower-confidence OCR, what preprocessing actions were applied,
	and what image-quality risks still require reviewer attention.

	Attributes:
		_image_path (Path): Path to the image currently being processed.
		_image (Image.Image): PIL image currently being processed.
		_images (List[Image.Image]): Reserved collection of images for workflows that process
			multiple pages or frames.
		_notes (List[str]): Reviewer-facing quality and preprocessing notes.
		_minimum_width (int): Preferred minimum image width for OCR preprocessing.
		_minimum_height (int): Preferred minimum image height for OCR preprocessing.
		_maximum_dimension (int): Maximum image dimension before performance downscaling.
		_quality_metrics (Dict[str, float]): Most recent lightweight quality metric values.
		_preprocessing_profile (str): Most recent preprocessing profile selected for OCR.
	"""
	
	_image_path: Path
	_image: Image.Image
	_images: List[ Image.Image ]
	_notes: List[ str ]
	_minimum_width: int
	_minimum_height: int
	_maximum_dimension: int
	_quality_metrics: Dict[ str, float ]
	_preprocessing_profile: str
	
	def __init__( self, minimum_width: int = 800, minimum_height: int = 800 ) -> None:
		"""Initialize the image processor with OCR size thresholds.

		Purpose:
			Store the minimum preferred OCR dimensions, read the maximum image dimension from
			configuration, initialize the notes list, initialize empty quality metrics, and set the
			default preprocessing profile to ``standard``.

		Args:
			minimum_width (int): Minimum preferred image width for OCR.
			minimum_height (int): Minimum preferred image height for OCR.

		Returns:
			None.
		"""
		try:
			self._minimum_width = int( minimum_width )
			self._minimum_height = int( minimum_height )
			self._maximum_dimension = int( getattr( cfg, 'MAX_IMAGE_DIMENSION', 2400 ) )
			self._notes = [ ]
			self._quality_metrics = { }
			self._preprocessing_profile = 'standard'
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = '__init__( self, minimum_width: int = 800, minimum_height: int = 800 ) -> None'
			Logger( ).write( error )
			self._minimum_width = 800
			self._minimum_height = 800
			self._maximum_dimension = 2400
			self._notes = [ ]
			self._quality_metrics = { }
			self._preprocessing_profile = 'standard'
	
	@property
	def notes( self ) -> List[ str ]:
		"""Return image quality and preprocessing notes collected during processing.

		Purpose:
			Expose the notes list populated by image loading, quality estimation, size
			normalization, conservative deskew, preprocessing-profile selection, and OCR-oriented
			preprocessing operations. Callers use these notes to explain OCR limitations or
			preprocessing actions in downstream reports.

		

		Returns:
			List[str]: Current image quality and preprocessing notes.
		"""
		return self._notes
	
	@property
	def quality_metrics( self ) -> Dict[ str, float ]:
		"""Return the most recent lightweight quality metrics.

		Purpose:
			Expose image width, height, brightness, contrast, blur, glare ratio, dark ratio, and
			skew angle values computed during the latest quality-estimation workflow.

		

		Returns:
			Dict[str, float]: Most recent image quality metrics.
		"""
		return self._quality_metrics
	
	@property
	def preprocessing_profile( self ) -> str:
		"""Return the most recent preprocessing profile selected for OCR.

		Purpose:
			Expose the deterministic preprocessing profile selected from quality metrics. Expected
			values include ``standard``, ``dark_image``, ``low_contrast``, ``glare_review``,
			``overexposed``, and ``blur_review``.

		

		Returns:
			str: Preprocessing profile name.
		"""
		return self._preprocessing_profile
	
	def get_resample_filter( self ) -> object:
		"""Return a PIL resampling filter compatible with supported Pillow versions.

		Purpose:
			Use high-quality Lanczos resizing when the installed Pillow version exposes
			``Image.Resampling.LANCZOS`` and fall back to ``Image.LANCZOS`` for older Pillow
			versions.

		

		Returns:
			object: Pillow resampling filter constant.
		"""
		try:
			return Image.Resampling.LANCZOS
		except Exception:
			return Image.LANCZOS
	
	def create_fallback_image( self ) -> Image.Image:
		"""Create a white fallback image using configured OCR dimensions.

		Purpose:
			Return a valid PIL image when loading or processing fails. A white image is preferable
			to returning ``None`` because downstream OCR callers expect a PIL image and can still
			produce a reviewer-safe no-text result.

		

		Returns:
			Image.Image: White RGB fallback image.
		"""
		try:
			return Image.new(
				'RGB',
				(self._minimum_width, self._minimum_height),
				'white'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_fallback_image( self ) -> Image.Image'
			Logger( ).write( error )
			return Image.new( 'RGB', (800, 800), 'white' )
	
	def load_image( self, image_path: str | Path ) -> Image.Image:
		"""Load an image file from disk and apply EXIF orientation correction.

		Purpose:
			Validate the supplied image path, confirm that it exists, open it through PIL, apply
			EXIF transpose handling so phone/camera images are oriented correctly, and convert
			unsupported modes to RGB while recording reviewer-facing notes.

		Args:
			image_path (str | Path): Path to the image file to load.

		Returns:
			Image.Image: Loaded PIL image. If loading fails, the exception is logged, a processing
			note is appended, and a white RGB fallback image using configured OCR dimensions is
			returned.
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
			error.method = 'load_image( self, image_path: str | Path ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'Image could not be loaded; fallback image was used.' )
			return self.create_fallback_image( )
	
	def ensure_rgb( self, image: Image.Image ) -> Image.Image:
		"""Ensure an image is in RGB mode before OpenCV processing.

		Purpose:
			Convert PIL image modes that OpenCV conversion paths cannot consume reliably into RGB.
			The method keeps RGB images unchanged and records a reviewer-facing note when a mode
			conversion is performed.

		Args:
			image (Image.Image): PIL image to inspect and convert when necessary.

		Returns:
			Image.Image: RGB image when conversion succeeds. If conversion fails, the exception is
			logged, a note is appended, and the original image is returned.
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
			error.method = 'ensure_rgb( self, image: Image.Image ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'Image mode conversion failed; original image was used.' )
			return image
	
	def resize_for_ocr( self, image: Image.Image ) -> Image.Image:
		"""Upscale small label images to improve OCR readability.

		Purpose:
			Compare image dimensions to the configured minimum OCR dimensions. Images that already
			meet both thresholds are returned unchanged. Images below either threshold are upscaled
			proportionally using high-quality Lanczos resampling so small label text has more pixel
			information available to OCR.

		Args:
			image (Image.Image): PIL image to resize when needed.

		Returns:
			Image.Image: Original image when no resize is needed, or a proportionally upscaled image
			when dimensions are below the preferred OCR size. If resizing fails, the exception is
			logged, a note is appended, and the original image is returned.
		"""
		try:
			throw_if( 'image', image )
			
			self._image = image
			width, height = self._image.size
			
			if width >= self._minimum_width and height >= self._minimum_height:
				return self._image
			
			scale_width = self._minimum_width / max( 1, width )
			scale_height = self._minimum_height / max( 1, height )
			scale = max( scale_width, scale_height )
			
			new_width = max( 1, int( width * scale ) )
			new_height = max( 1, int( height * scale ) )
			
			self._notes.append(
				f'Upscaled image from {width}x{height} to {new_width}x{new_height} for OCR.'
			)
			
			return self._image.resize(
				(new_width, new_height),
				self.get_resample_filter( )
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'resize_for_ocr( self, image: Image.Image ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'Image resize step failed; original image was used.' )
			return image
	
	def downscale_for_ocr( self, image: Image.Image ) -> Image.Image:
		"""Downscale oversized images to improve processing predictability.

		Purpose:
			Reduce very large label images before OCR preprocessing so memory use and processing
			time remain predictable under the prototype SLA. Aspect ratio is preserved and the image
			is unchanged when its largest dimension is already within the configured maximum.

		Args:
			image (Image.Image): PIL image to inspect and possibly downscale.

		Returns:
			Image.Image: Original image or proportionally downscaled image. If downscaling fails,
			the exception is logged, a note is appended, and the original image is returned.
		"""
		try:
			throw_if( 'image', image )
			
			if self._maximum_dimension <= 0:
				return image
			
			width, height = image.size
			max_dimension = max( width, height )
			
			if max_dimension <= self._maximum_dimension:
				return image
			
			scale = self._maximum_dimension / float( max_dimension )
			new_width = max( 1, int( width * scale ) )
			new_height = max( 1, int( height * scale ) )
			
			self._notes.append(
				f'Downscaled image from {width}x{height} to {new_width}x{new_height} '
				f'for OCR performance.'
			)
			
			return image.resize(
				(new_width, new_height),
				self.get_resample_filter( )
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'downscale_for_ocr( self, image: Image.Image ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'Image downscale step failed; original image was used.' )
			return image
	
	def to_cv_gray( self, image: Image.Image ) -> np.ndarray:
		"""Convert a PIL image to an OpenCV grayscale array.

		Purpose:
			Ensure the supplied image is RGB-compatible, convert it to a NumPy array, and then
			convert the array to grayscale using OpenCV. The resulting array is used by quality
			estimation, deskew, thresholding, and OCR preprocessing steps.

		Args:
			image (Image.Image): PIL image to convert.

		Returns:
			np.ndarray: Grayscale OpenCV image array. If conversion fails, the exception is logged,
			a note is appended, and a white fallback grayscale array using configured OCR
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
			error.method = 'to_cv_gray( self, image: Image.Image ) -> np.ndarray'
			Logger( ).write( error )
			self._notes.append( 'Grayscale conversion failed.' )
			return np.full(
				(self._minimum_height, self._minimum_width),
				255,
				dtype=np.uint8
			)
	
	def calculate_quality_metrics( self, image: Image.Image ) -> Dict[ str, float ]:
		"""Calculate lightweight image-quality metrics for preprocessing decisions.

		Purpose:
			Measure width, height, brightness, contrast, blur score, glare ratio, dark ratio, and
			estimated skew angle from a PIL image. These metrics drive reviewer-facing notes and
			deterministic preprocessing-profile selection.

		Args:
			image (Image.Image): PIL image to evaluate.

		Returns:
			Dict[str, float]: Quality metrics. If calculation fails, the exception is logged and a
			zero-valued metric dictionary is returned.
		"""
		try:
			throw_if( 'image', image )
			
			width, height = image.size
			gray = self.to_cv_gray( image )
			brightness = float( np.mean( gray ) )
			contrast = float( np.std( gray ) )
			blur_score = float( cv2.Laplacian( gray, cv2.CV_64F ).var( ) )
			glare_ratio = float( np.mean( gray >= 245 ) )
			dark_ratio = float( np.mean( gray <= 35 ) )
			skew_angle = float( self.estimate_skew_angle( gray ) )
			
			self._quality_metrics = {
					'width': float( width ),
					'height': float( height ),
					'brightness': brightness,
					'contrast': contrast,
					'blur_score': blur_score,
					'glare_ratio': glare_ratio,
					'dark_ratio': dark_ratio,
					'skew_angle': skew_angle
			}
			
			return self._quality_metrics
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'calculate_quality_metrics( self, image: Image.Image ) -> Dict[str, float]'
			Logger( ).write( error )
			self._notes.append( 'Image quality metric calculation failed.' )
			self._quality_metrics = {
					'width': 0.0,
					'height': 0.0,
					'brightness': 0.0,
					'contrast': 0.0,
					'blur_score': 0.0,
					'glare_ratio': 0.0,
					'dark_ratio': 0.0,
					'skew_angle': 0.0
			}
			return self._quality_metrics
	
	def estimate_skew_angle( self, gray: np.ndarray ) -> float:
		"""Estimate a conservative skew angle from grayscale text-like pixels.

		Purpose:
			Use thresholded foreground pixels and ``cv2.minAreaRect`` to estimate the dominant text
			angle. The method returns ``0.0`` when there are too few foreground pixels, when the
			estimated angle is outside a conservative range, or when estimation fails. This prevents
			aggressive rotation from damaging labels with complex artwork.

		Args:
			gray (np.ndarray): Grayscale image array.

		Returns:
			float: Estimated skew angle in degrees. Positive and negative values indicate rotation
			direction; ``0.0`` means no safe skew estimate is available.
		"""
		try:
			throw_if( 'gray', gray )
			
			blurred = cv2.GaussianBlur( gray, (3, 3), 0 )
			thresholded = cv2.threshold(
				blurred,
				0,
				255,
				cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
			)[ 1 ]
			
			coordinates = np.column_stack( np.where( thresholded > 0 ) )
			
			if coordinates.shape[ 0 ] < 200:
				return 0.0
			
			angle = cv2.minAreaRect( coordinates )[ -1 ]
			
			if angle < -45:
				angle = 90 + angle
			
			if angle > 45:
				angle = angle - 90
			
			if abs( angle ) > 15:
				return 0.0
			
			return float( angle )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'estimate_skew_angle( self, gray: np.ndarray ) -> float'
			Logger( ).write( error )
			return 0.0
	
	def deskew_image( self, image: Image.Image ) -> Image.Image:
		"""Apply conservative deskew when the estimated rotation is safe.

		Purpose:
			Rotate the image only when the estimated skew angle is within a small, safe range. This
			supports imperfect-image OCR without claiming full perspective correction or arbitrary
			geometric repair.

		Args:
			image (Image.Image): PIL image to deskew when safe.

		Returns:
			Image.Image: Deskewed image when a safe correction is applied, otherwise the original
			image. If deskew fails, the exception is logged and the original image is returned.
		"""
		try:
			throw_if( 'image', image )
			
			gray = self.to_cv_gray( image )
			angle = self.estimate_skew_angle( gray )
			
			if abs( angle ) < 1.0:
				return image
			
			if abs( angle ) > 12.0:
				self._notes.append(
					f'Skew estimate {angle:.1f} degrees was not corrected because it exceeded '
					f'the conservative deskew threshold.'
				)
				return image
			
			rgb = self.ensure_rgb( image )
			array = np.array( rgb )
			height, width = array.shape[ :2 ]
			center = (width // 2, height // 2)
			matrix = cv2.getRotationMatrix2D( center, angle, 1.0 )
			rotated = cv2.warpAffine(
				array,
				matrix,
				(width, height),
				flags=cv2.INTER_CUBIC,
				borderMode=cv2.BORDER_CONSTANT,
				borderValue=(255, 255, 255)
			)
			
			self._notes.append(
				f'Applied conservative deskew correction of {angle:.1f} degrees.'
			)
			
			return Image.fromarray( rotated )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'deskew_image( self, image: Image.Image ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'Conservative deskew failed; original image was used.' )
			return image
	
	def get_preprocessing_profile( self, metrics: Dict[ str, float ] ) -> str:
		"""Select an OCR preprocessing profile from image-quality metrics.

		Purpose:
			Classify the image into a deterministic preprocessing profile based on brightness,
			contrast, blur, glare, and dark-pixel ratio. The profile selects local preprocessing
			steps but does not change the compliance interpretation of OCR results.

		Args:
			metrics (Dict[str, float]): Quality metrics from ``calculate_quality_metrics``.

		Returns:
			str: Preprocessing profile name.
		"""
		try:
			throw_if( 'metrics', metrics )
			
			brightness = float( metrics.get( 'brightness', 0.0 ) )
			contrast = float( metrics.get( 'contrast', 0.0 ) )
			blur_score = float( metrics.get( 'blur_score', 0.0 ) )
			glare_ratio = float( metrics.get( 'glare_ratio', 0.0 ) )
			dark_ratio = float( metrics.get( 'dark_ratio', 0.0 ) )
			
			if glare_ratio >= 0.18:
				return 'glare_review'
			
			if dark_ratio >= 0.30 or brightness < 70:
				return 'dark_image'
			
			if brightness > 230:
				return 'overexposed'
			
			if contrast < 28:
				return 'low_contrast'
			
			if blur_score < 80:
				return 'blur_review'
			
			return 'standard'
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_preprocessing_profile( self, metrics: Dict[str, float] ) -> str'
			Logger( ).write( error )
			return 'standard'
	
	def apply_profile_enhancement( self, gray: np.ndarray, profile: str ) -> np.ndarray:
		"""Apply profile-specific grayscale enhancement before thresholding.

		Purpose:
			Use deterministic local operations to improve OCR preparation for dark, low-contrast,
			overexposed, glare-risk, or blurred images. The method records reviewer-facing notes
			when it applies profile-specific processing and explicitly avoids claiming true glare
			removal or perspective correction.

		Args:
			gray (np.ndarray): Grayscale OpenCV image array.
			profile (str): Selected preprocessing profile.

		Returns:
			np.ndarray: Enhanced grayscale image array. If enhancement fails, the exception is
			logged and the original grayscale array is returned.
		"""
		try:
			throw_if( 'gray', gray )
			throw_if( 'profile', profile )
			
			if profile == 'dark_image':
				normalized = cv2.normalize( gray, None, 0, 255, cv2.NORM_MINMAX )
				self._notes.append( 'Applied brightness normalization for a dark image.' )
				return normalized
			
			if profile == 'low_contrast':
				clahe = cv2.createCLAHE( clipLimit=2.0, tileGridSize=(8, 8) )
				self._notes.append( 'Applied CLAHE contrast enhancement for low-contrast text.' )
				return clahe.apply( gray )
			
			if profile == 'overexposed':
				clahe = cv2.createCLAHE( clipLimit=1.5, tileGridSize=(8, 8) )
				self._notes.append(
					'Applied conservative contrast balancing for overexposed image.' )
				return clahe.apply( gray )
			
			if profile == 'glare_review':
				clahe = cv2.createCLAHE( clipLimit=1.2, tileGridSize=(8, 8) )
				self._notes.append(
					'Glare risk detected. Applied conservative contrast balancing, but true glare '
					'removal is not performed by this prototype.'
				)
				return clahe.apply( gray )
			
			if profile == 'blur_review':
				self._notes.append(
					'Blur risk detected. Applied standard sharpening, but reviewer should inspect '
					'OCR output carefully.'
				)
				return gray
			
			return gray
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'apply_profile_enhancement( self, gray: np.ndarray, profile: str ) -> np.ndarray'
			Logger( ).write( error )
			self._notes.append(
				'Profile-specific enhancement failed; standard grayscale was used.' )
			return gray
	
	def threshold_for_ocr( self, gray: np.ndarray, profile: str ) -> np.ndarray:
		"""Threshold a grayscale image for OCR.

		Purpose:
			Use adaptive thresholding for most labels and Otsu thresholding for glare-risk or
			overexposed labels where adaptive local thresholding can over-amplify bright regions.

		Args:
			gray (np.ndarray): Grayscale OpenCV image array.
			profile (str): Selected preprocessing profile.

		Returns:
			np.ndarray: Binary thresholded image array.
		"""
		try:
			throw_if( 'gray', gray )
			throw_if( 'profile', profile )
			
			if profile in ('glare_review', 'overexposed'):
				_, thresholded = cv2.threshold(
					gray,
					0,
					255,
					cv2.THRESH_BINARY + cv2.THRESH_OTSU
				)
				self._notes.append( 'Applied Otsu thresholding for bright/glare-risk image.' )
				return thresholded
			
			thresholded = cv2.adaptiveThreshold(
				gray,
				255,
				cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
				cv2.THRESH_BINARY,
				31,
				11
			)
			
			self._notes.append( 'Applied adaptive Gaussian thresholding for OCR.' )
			return thresholded
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'threshold_for_ocr( self, gray: np.ndarray, profile: str ) -> np.ndarray'
			Logger( ).write( error )
			self._notes.append( 'Thresholding failed; grayscale image was used.' )
			return gray
	
	def sharpen_for_ocr( self, image_array: np.ndarray ) -> np.ndarray:
		"""Sharpen a grayscale or thresholded image array for OCR.

		Purpose:
			Apply a small deterministic sharpening kernel to make character strokes more distinct
			after thresholding. This is intentionally conservative so it does not over-process label
			artwork.

		Args:
			image_array (np.ndarray): Image array to sharpen.

		Returns:
			np.ndarray: Sharpened image array. If sharpening fails, the original array is returned.
		"""
		try:
			throw_if( 'image_array', image_array )
			
			kernel = np.array(
				[
						[ 0, -1, 0 ],
						[ -1, 5, -1 ],
						[ 0, -1, 0 ]
				]
			)
			
			return cv2.filter2D( image_array, -1, kernel )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'sharpen_for_ocr( self, image_array: np.ndarray ) -> np.ndarray'
			Logger( ).write( error )
			self._notes.append( 'Sharpening failed; unsharpened image was used.' )
			return image_array
	
	def preprocess_for_ocr( self, image: Image.Image ) -> Image.Image:
		"""Apply deterministic preprocessing to improve OCR extraction.

		Purpose:
			Apply the full local preprocessing pipeline: size normalization, conservative deskew,
			quality-profile selection, grayscale conversion, profile-specific enhancement,
			denoising, thresholding, sharpening, and conversion back to a PIL image. The method
			records all major actions in reviewer-facing notes.

		Args:
			image (Image.Image): PIL image to preprocess for OCR.

		Returns:
			Image.Image: OCR-prepared PIL image. If preprocessing fails, the exception is logged,
			a note is appended, and the original image is returned.
		"""
		try:
			throw_if( 'image', image )
			
			self._image = self.downscale_for_ocr( image )
			self._image = self.resize_for_ocr( self._image )
			self._image = self.deskew_image( self._image )
			
			metrics = self.calculate_quality_metrics( self._image )
			self._preprocessing_profile = self.get_preprocessing_profile( metrics )
			self._notes.append(
				f'Selected OCR preprocessing profile: {self._preprocessing_profile}.' )
			
			gray = self.to_cv_gray( self._image )
			enhanced = self.apply_profile_enhancement( gray, self._preprocessing_profile )
			denoised = cv2.fastNlMeansDenoising( enhanced, None, 10, 7, 21 )
			thresholded = self.threshold_for_ocr( denoised, self._preprocessing_profile )
			sharpened = self.sharpen_for_ocr( thresholded )
			
			processed = Image.fromarray( sharpened )
			self._notes.append(
				'Applied local OCR preprocessing: size normalization, optional conservative '
				'deskew, grayscale conversion, denoise, threshold, and sharpen.'
			)
			
			return processed
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'preprocess_for_ocr( self, image: Image.Image ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'Image preprocessing failed; original image was used.' )
			return image
	
	def estimate_quality_notes( self, image: Image.Image ) -> List[ str ]:
		"""Estimate image quality issues that may reduce OCR confidence.

		Purpose:
			Calculate lightweight image-quality metrics and convert them into plain-language
			reviewer notes. The method records small image size, darkness, overexposure, low
			contrast, blur risk, glare risk, and skew risk. These notes are advisory and do not
			replace human review.

		Args:
			image (Image.Image): PIL image to evaluate.

		Returns:
			List[str]: Current image quality and preprocessing notes.
		"""
		try:
			throw_if( 'image', image )
			
			self._image = image
			metrics = self.calculate_quality_metrics( self._image )
			width = int( metrics.get( 'width', 0.0 ) )
			height = int( metrics.get( 'height', 0.0 ) )
			brightness = float( metrics.get( 'brightness', 0.0 ) )
			contrast = float( metrics.get( 'contrast', 0.0 ) )
			blur_score = float( metrics.get( 'blur_score', 0.0 ) )
			glare_ratio = float( metrics.get( 'glare_ratio', 0.0 ) )
			dark_ratio = float( metrics.get( 'dark_ratio', 0.0 ) )
			skew_angle = float( metrics.get( 'skew_angle', 0.0 ) )
			initial_count = len( self._notes )
			
			self._notes.append(
				f'Image metrics: {width}x{height}; brightness {brightness:.1f}; '
				f'contrast {contrast:.1f}; blur {blur_score:.1f}; glare {glare_ratio:.3f}; '
				f'dark {dark_ratio:.3f}; skew {skew_angle:.1f}.'
			)
			
			if width < self._minimum_width or height < self._minimum_height:
				self._notes.append( 'Image is smaller than preferred OCR dimensions.' )
			
			if brightness < 60:
				self._notes.append( 'Image may be too dark for reliable OCR.' )
			
			if brightness > 235:
				self._notes.append( 'Image may be overexposed for reliable OCR.' )
			
			if contrast < 25:
				self._notes.append( 'Image may have low contrast.' )
			
			if blur_score < 80:
				self._notes.append( 'Image may be blurry; OCR results require careful review.' )
			
			if glare_ratio >= 0.18:
				self._notes.append(
					'Image may contain glare or excessive bright regions; this prototype flags '
					'glare risk but does not perform true glare removal.'
				)
			
			if dark_ratio >= 0.30:
				self._notes.append(
					'Image contains a large dark region that may reduce OCR reliability.' )
			
			if abs( skew_angle ) >= 1.0:
				self._notes.append(
					f'Image may be skewed by approximately {skew_angle:.1f} degrees.' )
			
			if len( self._notes ) == initial_count + 1:
				self._notes.append( 'No obvious image quality issues detected.' )
			
			return self._notes
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'estimate_quality_notes( self, image: Image.Image ) -> List[str]'
			Logger( ).write( error )
			self._notes.append( 'Image quality estimation failed.' )
			return self._notes
	
	def process_image_file( self, image_path: str | Path ) -> Image.Image:
		"""Load, evaluate, and preprocess an image file for OCR.

		Purpose:
			Reset processing notes, load an image from disk, apply EXIF orientation correction,
			estimate image quality, and apply deterministic OCR preprocessing. This is the primary
			file-based OCR preparation entry point.

		Args:
			image_path (str | Path): Path to the image file to load and preprocess.

		Returns:
			Image.Image: OCR-prepared image. If processing fails, the exception is logged, a note is
			appended, and a white RGB fallback image using configured OCR dimensions is returned.
		"""
		try:
			throw_if( 'image_path', image_path )
			
			self._notes = [ ]
			self._quality_metrics = { }
			self._preprocessing_profile = 'standard'
			self._image = self.load_image( image_path )
			self.estimate_quality_notes( self._image )
			
			return self.preprocess_for_ocr( self._image )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'process_image_file( self, image_path: str | Path ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'Image file processing failed; fallback image was used.' )
			return self.create_fallback_image( )
	
	def process_pil_image( self, image: Image.Image ) -> Image.Image:
		"""Evaluate and preprocess an in-memory PIL image for OCR.

		Purpose:
			Reset processing notes, apply EXIF orientation correction to the supplied PIL image,
			estimate image quality, and apply the same deterministic OCR preprocessing used by
			file-based images. This entry point is used for images extracted from PDFs and images
			already loaded by another component.

		Args:
			image (Image.Image): PIL image to evaluate and preprocess.

		Returns:
			Image.Image: OCR-prepared image. If processing fails, the exception is logged, a note is
			appended, and the original image is returned.
		"""
		try:
			throw_if( 'image', image )
			
			self._notes = [ ]
			self._quality_metrics = { }
			self._preprocessing_profile = 'standard'
			self._image = ImageOps.exif_transpose( image )
			self.estimate_quality_notes( self._image )
			
			return self.preprocess_for_ocr( self._image )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'process_pil_image( self, image: Image.Image ) -> Image.Image'
			Logger( ).write( error )
			self._notes.append( 'In-memory image processing failed; original image was used.' )
			return image