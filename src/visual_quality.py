'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                visual_quality.py
      Author:                  Terry D. Eppler
      Created:                 06-03-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-03-2026
    ******************************************************************************************
    <copyright file="visual_quality.py" company="Terry D. Eppler">

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
        Provides visual-quality analysis for Fiddy label artwork.

        This module measures image dimensions, brightness, contrast, blur, glare, darkness,
        skew, and approximate readability so OCR risks can be surfaced to reviewers before or
        during label verification.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from booger import Error, Logger
from src.constants import (
	SEVERITY_HIGH,
	SEVERITY_INFO,
	SEVERITY_LOW,
	SEVERITY_MEDIUM,
	STATUS_FAIL,
	STATUS_PASS,
	STATUS_REVIEW,
	STATUS_WARNING
)

class VisualQualityResult( BaseModel ):
	"""Represent visual-quality measurements and review flags for one label image.

	Purpose:
		The ``VisualQualityResult`` model stores image-readability measurements produced by
		``VisualQualityAnalyzer``. It captures dimensions, brightness, contrast, blur, glare,
		darkness, skew, an approximate readability score, reviewer-facing status and severity, and
		lists of warnings and recommendations.
	
		The model is used by OCR and reporting workflows to explain why OCR may have low confidence,
		why human review may be needed, or why a clearer label image should be requested.

	Attributes:
		file_name (str): Uploaded or logical file name associated with the analyzed image.
		width (int): Image width in pixels.
		height (int): Image height in pixels.
		brightness (float): Average grayscale brightness value.
		contrast (float): Grayscale standard deviation used as a contrast score.
		blur_score (float): Variance of Laplacian score where lower values indicate more blur.
		glare_ratio (float): Ratio of near-white pixels to all pixels.
		dark_ratio (float): Ratio of near-black pixels to all pixels.
		skew_angle (float): Estimated skew angle in degrees.
		readability_score (float): Approximate readability score from 0.0 to 100.0.
		status (str): Visual-quality status for reviewer display.
		severity (str): Visual-quality severity for reviewer display.
		warnings (List[str]): Reviewer-facing warnings produced from quality measurements.
		recommendations (List[str]): Reviewer-facing recommendations produced from warnings.
	"""
	
	file_name: str = Field( default='' )
	width: int = Field( default=0 )
	height: int = Field( default=0 )
	brightness: float = Field( default=0.0 )
	contrast: float = Field( default=0.0 )
	blur_score: float = Field( default=0.0 )
	glare_ratio: float = Field( default=0.0 )
	dark_ratio: float = Field( default=0.0 )
	skew_angle: float = Field( default=0.0 )
	readability_score: float = Field( default=0.0 )
	status: str = Field( default=STATUS_REVIEW )
	severity: str = Field( default=SEVERITY_MEDIUM )
	warnings: List[ str ] = Field( default_factory=list )
	recommendations: List[ str ] = Field( default_factory=list )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert the visual-quality result into a flat display/export record.

		Purpose:
			This method converts the structured visual-quality result into a dictionary suitable for
			Streamlit tables, pandas DataFrames, CSV export, JSON export, or report-writing
			workflows. Numeric measurements are rounded to three decimal places for compact display.
			Warning and recommendation lists are joined into semicolon-delimited strings.

		Returns:
			Dict[str, object]: Flat visual-quality result record. If conversion fails, the
			exception is logged and a conservative fallback record is returned with review status,
			high severity, and reviewer-safe warning and recommendation text.
		"""
		try:
			return {
					'File Name': self.file_name,
					'Width': self.width,
					'Height': self.height,
					'Brightness': round( self.brightness, 3 ),
					'Contrast': round( self.contrast, 3 ),
					'Blur Score': round( self.blur_score, 3 ),
					'Glare Ratio': round( self.glare_ratio, 3 ),
					'Dark Ratio': round( self.dark_ratio, 3 ),
					'Skew Angle': round( self.skew_angle, 3 ),
					'Readability Score': round( self.readability_score, 3 ),
					'Status': self.status,
					'Severity': self.severity,
					'Warnings': '; '.join( self.warnings ),
					'Recommendations': '; '.join( self.recommendations )
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'File Name': self.file_name,
					'Width': 0,
					'Height': 0,
					'Brightness': 0.0,
					'Contrast': 0.0,
					'Blur Score': 0.0,
					'Glare Ratio': 0.0,
					'Dark Ratio': 0.0,
					'Skew Angle': 0.0,
					'Readability Score': 0.0,
					'Status': STATUS_REVIEW,
					'Severity': SEVERITY_HIGH,
					'Warnings': 'Visual quality record could not be rendered.',
					'Recommendations': 'Review label manually or request clearer artwork.'
			}


class VisualQualityAnalyzer( ):
	"""Analyze label artwork for OCR readability risks.

	Purpose:
		The ``VisualQualityAnalyzer`` class measures basic image-quality characteristics that can
		reduce OCR reliability. It supports file-based and in-memory PIL image analysis, applies
		EXIF orientation correction, converts images to RGB and grayscale arrays, calculates
		brightness, contrast, blur, glare ratio, dark ratio, skew angle, and a composite readability
		score, then produces reviewer-facing warnings and recommendations.
	
		The analyzer is intentionally deterministic and lightweight. It does not make regulatory
		determinations; it identifies visual conditions that may require manual review, clearer
		artwork, better lighting, deskewing, or direct digital label files.

	Attributes:
		_image (Image.Image): PIL image currently being analyzed.
		_file_name (str): Uploaded or logical file name currently being analyzed.
		_minimum_width (int): Minimum preferred image width for OCR.
		_minimum_height (int): Minimum preferred image height for OCR.
		_minimum_contrast (float): Minimum acceptable grayscale standard deviation.
		_minimum_blur_score (float): Minimum acceptable Laplacian variance blur score.
		_maximum_glare_ratio (float): Maximum acceptable near-white pixel ratio.
		_maximum_dark_ratio (float): Maximum acceptable near-black pixel ratio.
		_maximum_skew_angle (float): Maximum acceptable absolute skew angle.
		_warnings (List[str]): Current reviewer-facing warning messages.
		_recommendations (List[str]): Current reviewer-facing recommendation messages.
	"""
	
	_image: Image.Image
	_file_name: str
	_minimum_width: int
	_minimum_height: int
	_minimum_contrast: float
	_minimum_blur_score: float
	_maximum_glare_ratio: float
	_maximum_dark_ratio: float
	_maximum_skew_angle: float
	_warnings: List[ str ]
	_recommendations: List[ str ]
	
	def __init__( self, minimum_width: int = 800, minimum_height: int = 800,
			minimum_contrast: float = 20.0, minimum_blur_score: float = 35.0,
			maximum_glare_ratio: float = 0.35, maximum_dark_ratio: float = 0.25,
			maximum_skew_angle: float = 8.0 ) -> None:
		"""Initialize visual-quality thresholds used for OCR readability assessment.

		Purpose:
			The constructor stores the image-size, contrast, blur, glare, darkness, and skew
			thresholds used by warning evaluation and readability scoring. It also initializes empty
			warning and recommendation collections for the first analysis run.

		Args:
			minimum_width (int): Minimum preferred image width.
			minimum_height (int): Minimum preferred image height.
			minimum_contrast (float): Minimum acceptable grayscale standard deviation.
			minimum_blur_score (float): Minimum acceptable Laplacian variance blur score.
			maximum_glare_ratio (float): Maximum acceptable bright-pixel ratio.
			maximum_dark_ratio (float): Maximum acceptable dark-pixel ratio.
			maximum_skew_angle (float): Maximum acceptable absolute skew angle.

		Returns:
			None.
		"""
		self._minimum_width = minimum_width
		self._minimum_height = minimum_height
		self._minimum_contrast = minimum_contrast
		self._minimum_blur_score = minimum_blur_score
		self._maximum_glare_ratio = maximum_glare_ratio
		self._maximum_dark_ratio = maximum_dark_ratio
		self._maximum_skew_angle = maximum_skew_angle
		self._warnings = [ ]
		self._recommendations = [ ]
	
	def load_image( self, image_path: str | Path ) -> Image.Image:
		"""Load an image from disk and apply EXIF orientation correction.

		Purpose:
			This method validates that an image path was supplied, confirms the file exists, opens
			the file through PIL, applies EXIF transpose handling, converts non-RGB images to RGB, and
			returns the loaded image. The file name is stored for downstream reporting.

		Args:
			image_path (str | Path): Path to image file.

		Returns:
			Image.Image: Loaded RGB image. If loading fails, the exception is logged, the logical
			file name is preserved when possible, and a white fallback image using the configured
			minimum dimensions is returned.
		"""
		try:
			if image_path is None:
				raise ValueError( 'image_path is required.' )
			
			path = Path( image_path )
			
			if not path.exists( ):
				raise FileNotFoundError( f'Image file was not found: {path}' )
			
			self._file_name = path.name
			self._image = Image.open( path )
			self._image = ImageOps.exif_transpose( self._image )
			
			if self._image.mode != 'RGB':
				self._image = self._image.convert( 'RGB' )
			
			return self._image
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'load_image( image_path: str | Path ) -> Image.Image'
			Logger( ).write( error )
			self._file_name = Path( image_path ).name if image_path else ''
			return Image.new( 'RGB', (self._minimum_width, self._minimum_height), 'white' )
	
	def to_grayscale_array( self, image: Image.Image ) -> np.ndarray:
		"""Convert a PIL image into an OpenCV grayscale array.

		Purpose:
			This method converts the supplied image to RGB when necessary, converts it to a NumPy
			array, and then returns a single-channel grayscale OpenCV array. If the input array is
			already two-dimensional, it is returned directly.

		Args:
			image (Image.Image): PIL image to convert.

		Returns:
			np.ndarray: Grayscale image array. If the image is missing or conversion fails, the
			exception is logged when applicable and a white fallback grayscale array is returned.
		"""
		try:
			if image is None:
				return np.full( (self._minimum_height, self._minimum_width), 255, dtype=np.uint8 )
			
			self._image = image.convert( 'RGB' ) if image.mode != 'RGB' else image
			array = np.asarray( self._image, dtype=np.uint8 )
			
			if array.ndim == 2:
				return array
			
			return cv2.cvtColor( array, cv2.COLOR_RGB2GRAY )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_grayscale_array( image: Image.Image ) -> np.ndarray'
			Logger( ).write( error )
			return np.full( (self._minimum_height, self._minimum_width), 255, dtype=np.uint8 )
	
	def calculate_brightness( self, gray: np.ndarray ) -> float:
		"""Calculate average grayscale brightness.

		Purpose:
			This method calculates the arithmetic mean of the grayscale pixel values. Higher values
			indicate a brighter image, while lower values indicate a darker image.

		Args:
			gray (np.ndarray): Grayscale image array.

		Returns:
			float: Average brightness value. If the input is empty or calculation fails, the
			exception is logged when applicable and ``0.0`` is returned.
		"""
		try:
			if gray is None or gray.size == 0:
				return 0.0
			
			return float( np.mean( gray ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'calculate_brightness( gray: np.ndarray ) -> float'
			Logger( ).write( error )
			return 0.0
	
	def calculate_contrast( self, gray: np.ndarray ) -> float:
		"""Calculate grayscale contrast using standard deviation.

		Purpose:
			This method uses the standard deviation of grayscale pixel values as a simple contrast
			score. Higher values indicate more tonal separation, while lower values indicate flatter
			or lower-contrast imagery that may reduce OCR readability.

		Args:
			gray (np.ndarray): Grayscale image array.

		Returns:
			float: Contrast score. If the input is empty or calculation fails, the exception is
			logged when applicable and ``0.0`` is returned.
		"""
		try:
			if gray is None or gray.size == 0:
				return 0.0
			
			return float( np.std( gray ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'calculate_contrast( gray: np.ndarray ) -> float'
			Logger( ).write( error )
			return 0.0
	
	def calculate_blur_score( self, gray: np.ndarray ) -> float:
		"""Estimate blur using the variance of the Laplacian.

		Purpose:
			This method calculates the variance of the Laplacian of the grayscale image. Lower
			values generally indicate blurrier images, while higher values suggest sharper edges and
			better OCR readability.

		Args:
			gray (np.ndarray): Grayscale image array.

		Returns:
			float: Blur score where lower values indicate more blur. If the input is empty or
			calculation fails, the exception is logged when applicable and ``0.0`` is returned.
		"""
		try:
			if gray is None or gray.size == 0:
				return 0.0
			
			return float( cv2.Laplacian( gray, cv2.CV_64F ).var( ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'calculate_blur_score( gray: np.ndarray ) -> float'
			Logger( ).write( error )
			return 0.0
	
	def calculate_glare_ratio( self, gray: np.ndarray ) -> float:
		"""Estimate glare or overexposure using the ratio of near-white pixels.

		Purpose:
			This method counts pixels with grayscale values greater than or equal to 245 and divides
			that count by total pixel count. A high ratio may indicate glare, overexposure, washed-out
			areas, or white background dominance that could impair OCR.

		Args:
			gray (np.ndarray): Grayscale image array.

		Returns:
			float: Ratio of very bright pixels to all pixels. If the input is empty or calculation
			fails, the exception is logged when applicable and ``0.0`` is returned.
		"""
		try:
			if gray is None or gray.size == 0:
				return 0.0
			
			bright_pixels = np.sum( gray >= 245 )
			total_pixels = gray.size
			
			return float( bright_pixels / total_pixels ) if total_pixels else 0.0
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'calculate_glare_ratio( gray: np.ndarray ) -> float'
			Logger( ).write( error )
			return 0.0
	
	def calculate_dark_ratio( self, gray: np.ndarray ) -> float:
		"""Estimate underexposure using the ratio of near-black pixels.

		Purpose:
			This method counts pixels with grayscale values less than or equal to 35 and divides that
			count by total pixel count. A high ratio may indicate underexposure, shadows, black label
			areas, or insufficient lighting that could reduce OCR reliability.

		Args:
			gray (np.ndarray): Grayscale image array.

		Returns:
			float: Ratio of very dark pixels to all pixels. If the input is empty or calculation
			fails, the exception is logged when applicable and ``0.0`` is returned.
		"""
		try:
			if gray is None or gray.size == 0:
				return 0.0
			
			dark_pixels = np.sum( gray <= 35 )
			total_pixels = gray.size
			
			return float( dark_pixels / total_pixels ) if total_pixels else 0.0
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'calculate_dark_ratio( gray: np.ndarray ) -> float'
			Logger( ).write( error )
			return 0.0
	
	def estimate_skew_angle( self, gray: np.ndarray ) -> float:
		"""Estimate document skew angle using detected edge coordinates.

		Purpose:
			This method inverts the grayscale image, applies Otsu thresholding, extracts nonzero
			coordinates from the thresholded result, and uses OpenCV's minimum-area rectangle to
			estimate the dominant text or object angle. The returned value is intended as an
			approximate OCR-readability indicator rather than a precise geometric correction.

		Args:
			gray (np.ndarray): Grayscale image array.

		Returns:
			float: Estimated skew angle in degrees. If there are too few coordinates or estimation
			fails, the exception is logged when applicable and ``0.0`` is returned.
		"""
		try:
			if gray is None or gray.size == 0:
				return 0.0
			
			inverted = cv2.bitwise_not( gray )
			thresholded = cv2.threshold(
				inverted,
				0,
				255,
				cv2.THRESH_BINARY | cv2.THRESH_OTSU
			)[ 1 ]
			
			coordinates = np.column_stack( np.where( thresholded > 0 ) )
			
			if len( coordinates ) < 10:
				return 0.0
			
			angle = cv2.minAreaRect( coordinates )[ -1 ]
			
			if angle < -45:
				angle = 90 + angle
			
			return float( angle )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'estimate_skew_angle( gray: np.ndarray ) -> float'
			Logger( ).write( error )
			return 0.0
	
	def calculate_readability_score( self, contrast: float, blur_score: float, glare_ratio: float,
			dark_ratio: float, skew_angle: float ) -> float:
		"""Calculate an approximate readability score from visual measurements.

		Purpose:
			This method combines contrast and blur components, then subtracts glare, darkness, and
			skew penalties. The final score is clamped between ``0.0`` and ``100.0``. The score is a
			practical OCR-readability heuristic used for reviewer triage, not a calibrated statistical
			model.

		Args:
			contrast (float): Contrast score.
			blur_score (float): Blur score.
			glare_ratio (float): Glare ratio.
			dark_ratio (float): Dark ratio.
			skew_angle (float): Estimated skew angle.

		Returns:
			float: Approximate readability score from ``0.0`` to ``100.0``. If scoring fails, the
			exception is logged and ``0.0`` is returned.
		"""
		try:
			contrast_score = min( 100.0, max( 0.0, contrast / self._minimum_contrast * 100.0 ) )
			blur_component = min( 100.0, max( 0.0, blur_score / self._minimum_blur_score * 100.0 ) )
			glare_penalty = min( 25.0, glare_ratio / self._maximum_glare_ratio * 25.0 )
			dark_penalty = min( 35.0, dark_ratio / self._maximum_dark_ratio * 35.0 )
			skew_penalty = min( 25.0, abs( skew_angle ) / self._maximum_skew_angle * 25.0 )
			
			score = (contrast_score * 0.40) + (blur_component * 0.45) + 15.0
			score = score - glare_penalty - dark_penalty - skew_penalty
			
			return float( min( 100.0, max( 0.0, score ) ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'calculate_readability_score( contrast: float, blur_score: float, glare_ratio: float, dark_ratio: float, skew_angle: float ) -> float'
			Logger( ).write( error )
			return 0.0
	
	def evaluate_warnings( self, width: int, height: int, brightness: float, contrast: float,
			blur_score: float, glare_ratio: float, dark_ratio: float, skew_angle: float,
			readability_score: float ) -> None:
		"""Populate image-quality warnings and recommendations.

		Purpose:
			This method compares measured image-quality values against the configured thresholds and
			populates reviewer-facing warnings and recommendations. It flags small images, darkness,
			overexposure, low contrast, blur, glare, large dark areas, skew, and low overall
			readability.

		Args:
			width (int): Image width.
			height (int): Image height.
			brightness (float): Average brightness.
			contrast (float): Contrast score.
			blur_score (float): Blur score.
			glare_ratio (float): Glare ratio.
			dark_ratio (float): Dark ratio.
			skew_angle (float): Estimated skew angle.
			readability_score (float): Approximate readability score.

		Returns:
			None.
		"""
		try:
			self._warnings = [ ]
			self._recommendations = [ ]
			
			if width < self._minimum_width or height < self._minimum_height:
				self._warnings.append( 'Image resolution is below the preferred OCR size.' )
				self._recommendations.append( 'Request a higher-resolution label image.' )
			
			if brightness < 60.0:
				self._warnings.append( 'Image appears underexposed or too dark.' )
				self._recommendations.append( 'Request a brighter image or improve lighting.' )
			
			if brightness > 245.0 and contrast < self._minimum_contrast:
				self._warnings.append( 'Image appears overexposed or washed out.' )
				self._recommendations.append( 'Request a retake without overexposure.' )
			
			if contrast < self._minimum_contrast:
				self._warnings.append( 'Image contrast may be too low for reliable OCR.' )
				self._recommendations.append( 'Increase contrast or request clearer artwork.' )
			
			if blur_score < self._minimum_blur_score:
				self._warnings.append( 'Image may be blurry.' )
				self._recommendations.append( 'Request a sharper image or direct artwork export.' )
			
			if glare_ratio > self._maximum_glare_ratio and contrast < 45.0:
				self._warnings.append( 'Possible glare or washed-out image areas detected.' )
				self._recommendations.append( 'Request an image without glare or reflections.' )
			
			if dark_ratio > self._maximum_dark_ratio:
				self._warnings.append( 'Large dark areas may reduce OCR reliability.' )
				self._recommendations.append( 'Request better lighting or a direct digital label.' )
			
			if abs( skew_angle ) > self._maximum_skew_angle:
				self._warnings.append( 'Image appears skewed or rotated.' )
				self._recommendations.append( 'Deskew image or request a straight-on label image.' )
			
			if readability_score < 50.0:
				self._warnings.append( 'Overall readability is low.' )
				self._recommendations.append( 'Manual review or resubmission is recommended.' )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate_warnings( self, *args ) -> None'
			Logger( ).write( error )
			self._warnings.append( 'Visual quality warnings could not be evaluated.' )
			self._recommendations.append( 'Review label manually.' )
	
	def determine_status( self, readability_score: float ) -> tuple[ str, str ]:
		"""Determine status and severity from readability score.

		Purpose:
			This method maps the approximate readability score into a reviewer-facing status and
			severity pair. Scores of 75 or greater pass, scores from 55 to below 75 generate warning
			status, scores from 35 to below 55 require review, and scores below 35 fail.

		Args:
			readability_score (float): Approximate readability score.

		Returns:
			tuple[str, str]: Status and severity values. If mapping fails, the exception is logged
			and the original review/high-severity fallback is returned.
		"""
		try:
			if readability_score >= 75.0:
				return STATUS_PASS, SEVERITY_INFO
			
			if readability_score >= 55.0:
				return STATUS_WARNING, SEVERITY_LOW
			
			if readability_score >= 35.0:
				return STATUS_REVIEW, SEVERITY_MEDIUM
			
			return STATUS_FAIL, SEVERITY_HIGH
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'determine_status( readability_score: float ) -> tuple[str, str]'
			Logger( ).write( error )
			return STATUS_REVIEW, SEVERITY_HIGH
	
	def analyze_image( self, image: Image.Image, file_name: str = '' ) -> VisualQualityResult:
		"""Analyze one in-memory label image for OCR readability risks.

		Purpose:
			This method performs the full in-memory visual-quality analysis workflow. It validates
			the image, resets warning state, applies EXIF orientation correction, converts to RGB
			when necessary, measures dimensions and grayscale metrics, calculates readability score,
			populates warnings and recommendations, determines status/severity, and returns a
			structured ``VisualQualityResult``.

		Args:
			image (Image.Image): PIL image to analyze.
			file_name (str): Optional logical file name for reporting.

		Returns:
			VisualQualityResult: Structured visual-quality result. If analysis fails, the
			exception is logged and the original reviewer-safe fallback result is returned with
			failure details in the warning list.
		"""
		try:
			if image is None:
				raise ValueError( 'Image is required for visual quality analysis.' )
			
			self._file_name = file_name
			self._warnings = [ ]
			self._recommendations = [ ]
			
			self._image = ImageOps.exif_transpose( image )
			if self._image.mode != 'RGB':
				self._image = self._image.convert( 'RGB' )
			
			width, height = self._image.size
			gray = self.to_grayscale_array( self._image )
			
			brightness = self.calculate_brightness( gray )
			contrast = self.calculate_contrast( gray )
			blur_score = self.calculate_blur_score( gray )
			glare_ratio = self.calculate_glare_ratio( gray )
			dark_ratio = self.calculate_dark_ratio( gray )
			skew_angle = self.estimate_skew_angle( gray )
			
			readability_score = self.calculate_readability_score(
				contrast,
				blur_score,
				glare_ratio,
				dark_ratio,
				skew_angle
			)
			
			self.evaluate_warnings( width, height, brightness, contrast,
				blur_score, glare_ratio, dark_ratio, skew_angle, readability_score )
			
			status, severity = self.determine_status( readability_score )
			return VisualQualityResult( file_name=self._file_name, width=width,
				height=height, brightness=brightness, contrast=contrast,
				blur_score=blur_score, glare_ratio=glare_ratio, dark_ratio=dark_ratio,
				skew_angle=skew_angle, readability_score=readability_score,
				status=status, severity=severity, warnings=self._warnings,
				recommendations=self._recommendations )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'analyze_image( image: Image.Image, file_name: str ) -> VisualQualityResult'
			Logger( ).write( error )
			return VisualQualityResult( file_name=file_name, status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				warnings=[
						f'Visual quality analysis could not be completed: {type( e ).__name__}: {e}'
				],
				recommendations=[ 'Review label manually or request clearer artwork.' ] )
	
	def analyze_file( self, image_path: str | Path ) -> VisualQualityResult:
		"""Load and analyze one image file for OCR readability risks.

		This method validates the image path, confirms the file exists, opens the image through
		PIL, applies EXIF orientation correction, converts non-RGB images to RGB, and delegates
		final measurement and scoring to ``analyze_image``.

		Args:
			image_path (str | Path): Path to image file.

		Returns:
			VisualQualityResult: Structured visual-quality result. If file loading or analysis
			fails, the exception is logged and the original reviewer-safe fallback result is
			returned with failure details in the warning list.
		"""
		try:
			if image_path is None:
				raise ValueError( 'image_path is required.' )
			
			path = Path( image_path )
			
			if not path.exists( ):
				raise FileNotFoundError( f'Image file was not found: {path}' )
			
			image = Image.open( path )
			image = ImageOps.exif_transpose( image )
			
			if image.mode != 'RGB':
				image = image.convert( 'RGB' )
			
			return self.analyze_image( image, path.name )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'analyze_file( image_path: str | Path ) -> VisualQualityResult'
			Logger( ).write( error )
			return VisualQualityResult(
				file_name=Path( image_path ).name if image_path else '',
				status=STATUS_REVIEW,
				severity=SEVERITY_HIGH,
				warnings=[
						f'Visual quality file analysis could not be completed: {type( e ).__name__}: {e}'
				],
				recommendations=[
						'Review label manually or request clearer artwork.'
				]
			)