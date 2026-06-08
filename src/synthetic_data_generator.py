'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                synthetic_data_generator.py
      Author:                  Terry D. Eppler
      Created:                 06-07-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-08-2026
    ******************************************************************************************
    <copyright file="synthetic_data_generator.py" company="Terry D. Eppler">

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
        Provides deterministic synthetic demonstration data generation for the Fiddy prototype.

        This module creates a fixed local demonstration pack containing fictional manifest data,
        OCR-friendly label artwork, and a ZIP archive containing the generated label images.
        Generated files are written only under the project samples directory using the configured
        Fiddy demo prefix. The generator supports creating the standard demonstration pack,
        preventing accidental overwrite, and clearing only generated files that match the Fiddy
        demo prefix or the configured demo ZIP name.

        The module does not use real COLA data, does not call external services, does not use
        external image generation, does not modify uploaded runtime files, and does not write
        outside the samples/manifests and samples/labels folders.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

import config as cfg
from booger import Error, Logger
from config import throw_if
from src.constants import (
	BEVERAGE_TYPE_DISTILLED_SPIRITS,
	GOVERNMENT_WARNING_TEXT
)

# ==========================================================================================
# Synthetic Data Constants
# ==========================================================================================

DEFAULT_SYNTHETIC_PREFIX: str = 'fiddy_v2'
DEFAULT_SYNTHETIC_MANIFEST_NAME: str = 'fiddy_v2_demo_manifest.csv'
DEFAULT_SYNTHETIC_ZIP_NAME: str = 'fiddy_v2_demo_labels.zip'
DEFAULT_SYNTHETIC_LABEL_WIDTH: int = 1600
DEFAULT_SYNTHETIC_LABEL_HEIGHT: int = 1100
DEFAULT_SYNTHETIC_LABEL_EXTENSION: str = '.png'

SCENARIO_CLEAN_PASS: str = 'clean_pass'
SCENARIO_FUZZY_BRAND: str = 'fuzzy_brand'
SCENARIO_ABV_MISMATCH: str = 'abv_mismatch'
SCENARIO_MISSING_WARNING: str = 'missing_warning'
SCENARIO_LOW_CONTRAST: str = 'low_contrast'
SCENARIO_SKEWED_LABEL: str = 'skewed_label'
SCENARIO_IMPORTED_PRODUCT: str = 'imported_product'
SCENARIO_MISSING_NET_CONTENTS: str = 'missing_net_contents'

MANIFEST_COLUMNS: List[ str ] = [
		'file_name',
		'brand_name',
		'class_type',
		'beverage_type',
		'alcohol_content',
		'proof',
		'net_contents',
		'producer_bottler',
		'imported',
		'importer',
		'country_of_origin',
		'cola_id',
		'notes',
		'government_warning'
]

# ==========================================================================================
# Synthetic Data Models
# ==========================================================================================

class SyntheticLabelRecord( BaseModel ):
	"""Represent one deterministic synthetic demonstration label.

	Purpose:
		Store the manifest-side expected values and label-side rendered values for one synthetic
		demonstration label. Keeping both sides in one model allows the generator to create
		intentional differences such as fuzzy brand variation, ABV mismatch, missing warning text,
		or missing net contents while still writing a valid manifest row for the normal Fiddy
		workflow.

	Attributes:
		index (int): One-based record index used in deterministic file naming.
		scenario (str): Demonstration scenario identifier.
		file_name (str): Generated label artwork file name.
		brand_name (str): Expected manifest brand name.
		label_brand_name (str): Brand name rendered on the synthetic label.
		class_type (str): Expected manifest class or type.
		label_class_type (str): Class or type rendered on the synthetic label.
		beverage_type (str): Expected beverage category.
		alcohol_content (float): Expected manifest ABV value.
		label_alcohol_content (Optional[float]): ABV rendered on the label, or ``None`` when
			omitted.
		proof (float): Expected manifest proof value.
		label_proof (Optional[float]): Proof rendered on the label, or ``None`` when omitted.
		net_contents (str): Expected manifest net contents.
		label_net_contents (str): Net contents rendered on the label.
		producer_bottler (str): Expected manifest producer or bottler.
		label_producer_bottler (str): Producer or bottler rendered on the label.
		imported (bool): Indicates whether importer and country-of-origin checks apply.
		importer (str): Expected importer name when applicable.
		country_of_origin (str): Expected country of origin when applicable.
		government_warning (str): Expected manifest government warning.
		label_government_warning (str): Government warning rendered on the label.
		cola_id (str): Fictional COLA/application identifier.
		notes (str): Demonstration notes describing the scenario.
	"""
	
	index: int = Field( default=0 )
	scenario: str = Field( default='' )
	file_name: str = Field( default='' )
	brand_name: str = Field( default='' )
	label_brand_name: str = Field( default='' )
	class_type: str = Field( default='' )
	label_class_type: str = Field( default='' )
	beverage_type: str = Field( default=BEVERAGE_TYPE_DISTILLED_SPIRITS )
	alcohol_content: float = Field( default=0.0 )
	label_alcohol_content: Optional[ float ] = Field( default=None )
	proof: float = Field( default=0.0 )
	label_proof: Optional[ float ] = Field( default=None )
	net_contents: str = Field( default='' )
	label_net_contents: str = Field( default='' )
	producer_bottler: str = Field( default='' )
	label_producer_bottler: str = Field( default='' )
	imported: bool = Field( default=False )
	importer: str = Field( default='' )
	country_of_origin: str = Field( default='' )
	government_warning: str = Field( default=GOVERNMENT_WARNING_TEXT )
	label_government_warning: str = Field( default=GOVERNMENT_WARNING_TEXT )
	cola_id: str = Field( default='' )
	notes: str = Field( default='' )
	
	def to_manifest_record( self ) -> Dict[ str, object ]:
		"""Convert the synthetic label record into a manifest CSV row.

		Purpose:
			Return the expected application-side values using the standard Fiddy manifest schema.

		Returns:
			Dict[str, object]: Manifest row keyed by standard manifest column names.
		"""
		try:
			return {
					'file_name': self.file_name,
					'brand_name': self.brand_name,
					'class_type': self.class_type,
					'beverage_type': self.beverage_type,
					'alcohol_content': self.alcohol_content,
					'proof': self.proof,
					'net_contents': self.net_contents,
					'producer_bottler': self.producer_bottler,
					'imported': self.imported,
					'importer': self.importer,
					'country_of_origin': self.country_of_origin,
					'cola_id': self.cola_id,
					'notes': self.notes,
					'government_warning': self.government_warning
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_manifest_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					column: ''
					for column in MANIFEST_COLUMNS
			}
	
	def to_label_lines( self ) -> List[ str ]:
		"""Create label-rendering text lines for the synthetic artwork.

		Purpose:
			Build visible label text from label-side values. Missing warning and missing net
			contents scenarios intentionally omit those lines from the generated artwork.

		Returns:
			List[str]: Ordered label text lines for image rendering.
		"""
		try:
			lines = [
					self.label_brand_name,
					self.label_class_type
			]
			
			if self.label_alcohol_content is not None:
				abv_text = f'ALC. {self.label_alcohol_content:g}% BY VOL'
				
				if self.label_proof is not None:
					abv_text = f'{abv_text} / {self.label_proof:g} PROOF'
				
				lines.append( abv_text )
			
			if self.label_net_contents.strip( ):
				lines.append( f'NET CONTENTS: {self.label_net_contents}' )
			
			if self.label_producer_bottler:
				lines.append( f'BOTTLED BY {self.label_producer_bottler}' )
			
			if self.imported and self.importer:
				lines.append( f'IMPORTED BY {self.importer}' )
			
			if self.imported and self.country_of_origin:
				lines.append( f'COUNTRY OF ORIGIN: {self.country_of_origin}' )
			
			if self.label_government_warning.strip( ):
				lines.append( self.label_government_warning )
			
			return lines
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_label_lines( self ) -> List[str]'
			Logger( ).write( error )
			return [ ]

class SyntheticGenerationResult( BaseModel ):
	"""Represent the outcome of synthetic demo data generation or cleanup.

	Purpose:
		Return structured status information from generator operations so Streamlit, tests,
		documentation examples, or command-line use can display the manifest path, label folder,
		label ZIP path, generated files, deleted files, record count, success flag, and
		user-facing message.

	Attributes:
		manifest_path (str): Path to the generated manifest file.
		label_directory (str): Path to the generated label image directory.
		zip_path (str): Path to the generated label ZIP archive.
		generated_files (List[str]): Generated file paths.
		deleted_files (List[str]): Deleted generated file paths.
		record_count (int): Number of generated manifest records.
		success (bool): Indicates whether the operation completed successfully.
		message (str): User-facing operation summary.
	"""
	
	manifest_path: str = Field( default='' )
	label_directory: str = Field( default='' )
	zip_path: str = Field( default='' )
	generated_files: List[ str ] = Field( default_factory=list )
	deleted_files: List[ str ] = Field( default_factory=list )
	record_count: int = Field( default=0 )
	success: bool = Field( default=False )
	message: str = Field( default='' )
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert the generation result into a flat display/export record.

		Purpose:
			Return a dictionary suitable for Streamlit display, pandas DataFrame construction,
			JSON serialization, or test assertions.

		Returns:
			Dict[str, object]: Flat synthetic generation result record.
		"""
		try:
			return {
					'Success': self.success,
					'Message': self.message,
					'Manifest Path': self.manifest_path,
					'Label Directory': self.label_directory,
					'Label Zip Path': self.zip_path,
					'Generated Files': len( self.generated_files ),
					'Deleted Files': len( self.deleted_files ),
					'Record Count': self.record_count
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Success': False,
					'Message': 'Synthetic generation result could not be rendered.',
					'Manifest Path': '',
					'Label Directory': '',
					'Label Zip Path': '',
					'Generated Files': 0,
					'Deleted Files': 0,
					'Record Count': 0
			}

# ==========================================================================================
# Synthetic Data Generator
# ==========================================================================================

class SyntheticDataGenerator( ):
	"""Generate deterministic fictional Fiddy demonstration assets.

	Purpose:
		Create and clear the standard synthetic demonstration pack used for local evaluation of
		the Fiddy workflow. The generator writes a fixed manifest, eight OCR-friendly label images,
		and one ZIP archive containing those label images under the project samples directory.

	Attributes:
		project_root (Path): Root folder for the Fiddy project.
		samples_directory (Path): Samples directory under the project root.
		manifest_directory (Path): Directory where generated manifest files are written.
		label_directory (Path): Directory where generated label files are written.
		manifest_path (Path): Full path to the generated manifest CSV.
		zip_path (Path): Full path to the generated label ZIP archive.
		prefix (str): Prefix used for all generated label image files.
		label_width (int): Width of generated label images.
		label_height (int): Height of generated label images.
		label_extension (str): Generated label image extension.
	"""
	
	project_root: Path
	samples_directory: Path
	manifest_directory: Path
	label_directory: Path
	manifest_path: Path
	zip_path: Path
	prefix: str
	label_width: int
	label_height: int
	label_extension: str
	
	def __init__( self, project_root: str | Path | None = None ) -> None:
		"""Initialize the synthetic data generator.

		Purpose:
			Resolve project and samples paths, read optional configuration values, and prepare
			stable path members used by all generator methods. No files are created by the
			constructor.

		Args:
			project_root (str | Path | None): Optional project root path. When omitted, the
				generator uses ``cfg.ROOT_DIR`` when available, otherwise the current working
				directory.

		Returns:
			None.
		"""
		try:
			root_value = project_root or getattr( cfg, 'ROOT_DIR', Path.cwd( ) )
			self.project_root = Path( root_value ).resolve( )
			self.prefix = str(
				getattr( cfg, 'SYNTHETIC_DEMO_PREFIX', DEFAULT_SYNTHETIC_PREFIX )
			).strip( ) or DEFAULT_SYNTHETIC_PREFIX
			self.label_width = max(
				int(
					getattr( cfg, 'SYNTHETIC_DEMO_LABEL_WIDTH',
						DEFAULT_SYNTHETIC_LABEL_WIDTH )
				),
				DEFAULT_SYNTHETIC_LABEL_WIDTH
			)
			self.label_height = max(
				int(
					getattr( cfg, 'SYNTHETIC_DEMO_LABEL_HEIGHT',
						DEFAULT_SYNTHETIC_LABEL_HEIGHT )
				),
				DEFAULT_SYNTHETIC_LABEL_HEIGHT
			)
			self.label_extension = DEFAULT_SYNTHETIC_LABEL_EXTENSION
			self.samples_directory = self.project_root / 'samples'
			self.manifest_directory = self.samples_directory / 'manifests'
			self.label_directory = self.samples_directory / 'labels'
			self.manifest_path = self.manifest_directory / str(
				getattr( cfg, 'SYNTHETIC_DEMO_MANIFEST_NAME',
					DEFAULT_SYNTHETIC_MANIFEST_NAME )
			)
			self.zip_path = self.label_directory / str(
				getattr( cfg, 'SYNTHETIC_DEMO_ZIP_NAME', DEFAULT_SYNTHETIC_ZIP_NAME )
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = '__init__( self, project_root: str | Path | None = None ) -> None'
			Logger( ).write( error )
			self.project_root = Path.cwd( ).resolve( )
			self.prefix = DEFAULT_SYNTHETIC_PREFIX
			self.label_width = DEFAULT_SYNTHETIC_LABEL_WIDTH
			self.label_height = DEFAULT_SYNTHETIC_LABEL_HEIGHT
			self.label_extension = DEFAULT_SYNTHETIC_LABEL_EXTENSION
			self.samples_directory = self.project_root / 'samples'
			self.manifest_directory = self.samples_directory / 'manifests'
			self.label_directory = self.samples_directory / 'labels'
			self.manifest_path = self.manifest_directory / DEFAULT_SYNTHETIC_MANIFEST_NAME
			self.zip_path = self.label_directory / DEFAULT_SYNTHETIC_ZIP_NAME
	
	def ensure_demo_directories( self ) -> None:
		"""Create the synthetic demo samples directories when they are missing.

		Purpose:
			Create ``samples``, ``samples/manifests``, and ``samples/labels`` under the project
			root. Directory creation is limited to the configured samples path.

		Returns:
			None.
		"""
		try:
			self.samples_directory.mkdir( parents=True, exist_ok=True )
			self.manifest_directory.mkdir( parents=True, exist_ok=True )
			self.label_directory.mkdir( parents=True, exist_ok=True )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'ensure_demo_directories( self ) -> None'
			Logger( ).write( error )
			raise
	
	def get_safe_label_path( self, file_name: str ) -> Path:
		"""Return a safe generated label path under the label directory.

		Purpose:
			Validate a generated file name, ensure it uses the configured prefix, resolve the
			output path, and confirm the resulting path remains inside ``samples/labels``.

		Args:
			file_name (str): Generated label file name.

		Returns:
			Path: Safe resolved label path.
		"""
		try:
			throw_if( 'file_name', file_name )
			
			safe_name = Path( file_name ).name
			
			if not safe_name.startswith( f'{self.prefix}_' ):
				raise ValueError( 'Generated label file name must use the demo prefix.' )
			
			label_path = (self.label_directory / safe_name).resolve( )
			label_root = self.label_directory.resolve( )
			
			if label_root not in label_path.parents and label_path != label_root:
				raise ValueError( 'Generated label path must remain under samples/labels.' )
			
			return label_path
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_safe_label_path( self, file_name: str ) -> Path'
			Logger( ).write( error )
			raise
	
	def get_generated_file_paths( self ) -> List[ Path ]:
		"""Return existing generated demo files that match the configured demo pack.

		Purpose:
			Collect the generated manifest, generated ZIP archive, and generated label images that
			are safe for overwrite or cleanup operations.

		Returns:
			List[Path]: Existing generated demo file paths.
		"""
		try:
			files = [ ]
			
			if self.manifest_path.exists( ):
				files.append( self.manifest_path )
			
			if self.zip_path.exists( ):
				files.append( self.zip_path )
			
			if self.label_directory.exists( ):
				files.extend(
					sorted( self.label_directory.glob( f'{self.prefix}_*{self.label_extension}' ) )
				)
			
			return files
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_generated_file_paths( self ) -> List[Path]'
			Logger( ).write( error )
			return [ ]
	
	def get_file_name( self, index: int, scenario: str ) -> str:
		"""Create a deterministic synthetic label file name.

		Purpose:
			Build a generated file name using the configured prefix, a zero-padded index, a
			scenario identifier, and the configured label extension.

		Args:
			index (int): One-based record index.
			scenario (str): Scenario identifier.

		Returns:
			str: Generated label file name.
		"""
		try:
			throw_if( 'index', index )
			throw_if( 'scenario', scenario )
			
			return f'{self.prefix}_{index:03d}_{scenario}{self.label_extension}'
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_file_name( self, index: int, scenario: str ) -> str'
			Logger( ).write( error )
			return f'{DEFAULT_SYNTHETIC_PREFIX}_000_error{DEFAULT_SYNTHETIC_LABEL_EXTENSION}'
	
	def create_record( self, index: int, scenario: str, brand_name: str,
			class_type: str, alcohol_content: float, net_contents: str,
			producer_bottler: str, notes: str, label_brand_name: str = '',
			label_class_type: str = '', label_alcohol_content: Optional[ float ] = None,
			label_net_contents: Optional[ str ] = None, label_producer_bottler: str = '',
			label_government_warning: str = GOVERNMENT_WARNING_TEXT,
			imported: bool = False, importer: str = '',
			country_of_origin: str = '' ) -> SyntheticLabelRecord:
		"""Create one synthetic label record.

		Purpose:
			Centralize record construction so every scenario uses the same defaulting behavior,
			file naming convention, proof calculation, government warning value, fictional COLA
			identifier, and manifest schema.

		Args:
			index (int): One-based record index.
			scenario (str): Demonstration scenario identifier.
			brand_name (str): Expected manifest brand name.
			class_type (str): Expected manifest class or type.
			alcohol_content (float): Expected manifest ABV value.
			net_contents (str): Expected manifest net contents.
			producer_bottler (str): Expected manifest producer or bottler.
			notes (str): Scenario notes.
			label_brand_name (str): Brand name rendered on label. Defaults to manifest value.
			label_class_type (str): Class/type rendered on label. Defaults to manifest value.
			label_alcohol_content (Optional[float]): ABV rendered on label. Defaults to manifest
				value.
			label_net_contents (Optional[str]): Net contents rendered on label. ``None`` defaults
				to the manifest value; an empty string intentionally omits net contents.
			label_producer_bottler (str): Producer/bottler rendered on label. Defaults to
				manifest value.
			label_government_warning (str): Warning rendered on label.
			imported (bool): Indicates whether imported-product fields apply.
			importer (str): Importer name.
			country_of_origin (str): Country of origin.

		Returns:
			SyntheticLabelRecord: Fully populated synthetic label record.
		"""
		try:
			throw_if( 'index', index )
			throw_if( 'scenario', scenario )
			throw_if( 'brand_name', brand_name )
			throw_if( 'class_type', class_type )
			throw_if( 'alcohol_content', alcohol_content )
			throw_if( 'net_contents', net_contents )
			throw_if( 'producer_bottler', producer_bottler )
			
			file_name = self.get_file_name( index, scenario )
			proof = float( alcohol_content ) * 2.0
			rendered_abv = alcohol_content if label_alcohol_content is None else label_alcohol_content
			rendered_proof = rendered_abv * 2.0 if rendered_abv is not None else None
			rendered_net_contents = (
					net_contents if label_net_contents is None else label_net_contents
			)
			
			return SyntheticLabelRecord(
				index=index,
				scenario=scenario,
				file_name=file_name,
				brand_name=brand_name,
				label_brand_name=label_brand_name or brand_name,
				class_type=class_type,
				label_class_type=label_class_type or class_type,
				beverage_type=BEVERAGE_TYPE_DISTILLED_SPIRITS,
				alcohol_content=float( alcohol_content ),
				label_alcohol_content=rendered_abv,
				proof=proof,
				label_proof=rendered_proof,
				net_contents=net_contents,
				label_net_contents=rendered_net_contents,
				producer_bottler=producer_bottler,
				label_producer_bottler=label_producer_bottler or producer_bottler,
				imported=imported,
				importer=importer,
				country_of_origin=country_of_origin,
				government_warning=GOVERNMENT_WARNING_TEXT,
				label_government_warning=label_government_warning,
				cola_id=f'FIDDY-DEMO-{index:03d}',
				notes=notes
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_record( self, index: int, scenario: str, brand_name: str, class_type: str, alcohol_content: float, net_contents: str, producer_bottler: str, notes: str, label_brand_name: str, label_class_type: str, label_alcohol_content: Optional[float], label_net_contents: Optional[str], label_producer_bottler: str, label_government_warning: str, imported: bool, importer: str, country_of_origin: str ) -> SyntheticLabelRecord'
			Logger( ).write( error )
			return SyntheticLabelRecord( )
		
	def get_standard_records( self ) -> List[ SyntheticLabelRecord ]:
		"""Return the fixed standard demonstration records.

		Purpose:
			Create fifty deterministic synthetic scenarios used for the standard Fiddy demo pack.
			The records are fictional, stable across runs, and intentionally distributed across
			clean-pass, fuzzy-brand, ABV-mismatch, missing-warning, low-contrast, skewed-label,
			imported-product, and missing-net-contents scenarios. The fifty-record pack supports
			prototype batch validation within the stakeholder target of small-to-medium uploads.

		Returns:
			List[SyntheticLabelRecord]: Standard synthetic demo records.
		"""
		try:
			scenario_cycle = [
					SCENARIO_CLEAN_PASS,
					SCENARIO_FUZZY_BRAND,
					SCENARIO_ABV_MISMATCH,
					SCENARIO_MISSING_WARNING,
					SCENARIO_LOW_CONTRAST,
					SCENARIO_SKEWED_LABEL,
					SCENARIO_IMPORTED_PRODUCT,
					SCENARIO_MISSING_NET_CONTENTS
			]
			
			brand_roots = [
					'OLD TOM',
					'STONE THROW',
					'CROSSWIND',
					'RIVERSTONE',
					'PALE HARBOR',
					'IRON HILL',
					'NORTH COAST',
					'CANYON CREEK',
					'SILVER RIDGE',
					'COPPER FIELD',
					'BLUE OAK',
					'RED BARN',
					'WHITE PINE',
					'BLACK RIVER',
					'GOLDEN MILE',
					'CEDAR LANE',
					'BRIGHT FORK',
					'HOLLOW POINT',
					'MAPLE HOUSE',
					'SUMMIT ROAD',
					'LAKE COUNTY',
					'PRAIRIE STAR',
					'VALLEY STILL',
					'FOUR CORNERS',
					'BAY FRONT',
					'GRANITE PASS',
					'COLD SPRING',
					'HIGH PLAINS',
					'IRON GATE',
					'STONE BRIDGE',
					'CROWN POINT',
					'PINE BARREL',
					'OAK MEADOW',
					'COPPER RIDGE',
					'RIVER BEND',
					'FALLS ROAD',
					'BROWN CREEK',
					'LIBERTY STILL',
					'ORCHARD HILL',
					'BLUEGRASS',
					'CAPITOL RESERVE',
					'HARBOR LIGHT',
					'AMERICAN OAK',
					'FOUNDERS FIELD',
					'POTOMAC HOUSE',
					'RAIL YARD',
					'LONG TRAIL',
					'BEACON HILL',
					'FRONTIER LINE',
					'MARKET STREET'
			]
			
			class_types = [
					'Kentucky Straight Bourbon Whiskey',
					'Straight Rye Whiskey',
					'Vodka',
					'Blended Whiskey',
					'Distilled Gin',
					'Bourbon Whiskey',
					'Single Malt Irish Whiskey',
					'Tequila Blanco'
			]
			
			records = [ ]
			
			for index in range( 1, 51 ):
				scenario = scenario_cycle[ (index - 1) % len( scenario_cycle ) ]
				brand_root = brand_roots[ index - 1 ]
				class_type = class_types[ (index - 1) % len( class_types ) ]
				alcohol_content = 40.0 + float( (index % 8) )
				net_contents = '700 mL' if scenario == SCENARIO_IMPORTED_PRODUCT else '750 mL'
				producer_bottler = f'{brand_root} Beverage Company LLC, Washington, DC'
				brand_name = f'{brand_root} DISTILLING'
				label_brand_name = brand_name
				label_alcohol_content = None
				label_net_contents = None
				label_government_warning = GOVERNMENT_WARNING_TEXT
				imported = False
				importer = ''
				country_of_origin = ''
				notes = f'Deterministic synthetic scenario: {scenario}.'
				
				if scenario == SCENARIO_FUZZY_BRAND:
					brand_name = f"{brand_root}'S DISTILLING"
					label_brand_name = f'{brand_root}S DISTILLING'
					notes = 'Brand punctuation variation for fuzzy matching demonstration.'
				
				if scenario == SCENARIO_ABV_MISMATCH:
					label_alcohol_content = max( 35.0, alcohol_content - 5.0 )
					notes = 'Manifest ABV differs from label ABV.'
				
				if scenario == SCENARIO_MISSING_WARNING:
					label_government_warning = ''
					notes = 'Label omits the government warning text.'
				
				if scenario == SCENARIO_LOW_CONTRAST:
					notes = 'Lower-contrast artwork for image-quality diagnostics.'
				
				if scenario == SCENARIO_SKEWED_LABEL:
					notes = 'Slightly rotated artwork for skew diagnostics.'
				
				if scenario == SCENARIO_IMPORTED_PRODUCT:
					imported = True
					importer = 'Fiddy Imports LLC, Washington, DC'
					country_of_origin = 'Ireland'
					producer_bottler = f'{brand_root} Beverage Company, County Cork'
					notes = 'Imported product with importer and country-of-origin fields.'
				
				if scenario == SCENARIO_MISSING_NET_CONTENTS:
					label_net_contents = ''
					notes = 'Label omits net contents while manifest includes expected value.'
				
				records.append(
					self.create_record(
						index=index,
						scenario=scenario,
						brand_name=brand_name,
						label_brand_name=label_brand_name,
						class_type=class_type,
						alcohol_content=alcohol_content,
						label_alcohol_content=label_alcohol_content,
						net_contents=net_contents,
						label_net_contents=label_net_contents,
						producer_bottler=producer_bottler,
						label_government_warning=label_government_warning,
						imported=imported,
						importer=importer,
						country_of_origin=country_of_origin,
						notes=notes
					)
				)
			
			return records
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_standard_records( self ) -> List[SyntheticLabelRecord]'
			Logger( ).write( error )
			return [ ]
	
	def get_font( self, size: int, bold: bool = False ) -> ImageFont.ImageFont:
		"""Return a PIL font for label rendering.

		Purpose:
			Load a readable TrueType font when available and fall back to Pillow's default font
			when the runtime image does not provide common system fonts.

		Args:
			size (int): Requested font size.
			bold (bool): Indicates whether a bold font should be preferred.

		Returns:
			ImageFont.ImageFont: PIL font object.
		"""
		try:
			throw_if( 'size', size )
			
			font_names = [
					'arialbd.ttf' if bold else 'arial.ttf',
					'Arial Bold.ttf' if bold else 'Arial.ttf',
					'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf',
					'LiberationSans-Bold.ttf' if bold else 'LiberationSans-Regular.ttf'
			]
			
			for font_name in font_names:
				try:
					return ImageFont.truetype( font_name, size=size )
				except Exception:
					continue
			
			return ImageFont.load_default( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_font( self, size: int, bold: bool = False ) -> ImageFont.ImageFont'
			Logger( ).write( error )
			return ImageFont.load_default( )
	
	def get_text_width( self, draw: ImageDraw.ImageDraw, text: str,
			font: ImageFont.ImageFont ) -> int:
		"""Measure rendered text width.

		Purpose:
			Return a text width compatible with current and older Pillow versions.

		Args:
			draw (ImageDraw.ImageDraw): Active image drawing object.
			text (str): Text to measure.
			font (ImageFont.ImageFont): Font used for measurement.

		Returns:
			int: Approximate text width in pixels.
		"""
		try:
			throw_if( 'draw', draw )
			throw_if( 'text', text )
			throw_if( 'font', font )
			
			if hasattr( draw, 'textbbox' ):
				bounds = draw.textbbox( (0, 0), text, font=font )
				return int( bounds[ 2 ] - bounds[ 0 ] )
			
			return int( draw.textlength( text, font=font ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_text_width( self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont ) -> int'
			Logger( ).write( error )
			return len( text ) * 10
	
	def wrap_text( self, draw: ImageDraw.ImageDraw, text: str,
			font: ImageFont.ImageFont, max_width: int ) -> List[ str ]:
		"""Wrap text into lines that fit the available label width.

		Purpose:
			Split long label text into readable lines using word boundaries.

		Args:
			draw (ImageDraw.ImageDraw): Active image drawing object.
			text (str): Text to wrap.
			font (ImageFont.ImageFont): Font used for measurement.
			max_width (int): Maximum line width in pixels.

		Returns:
			List[str]: Wrapped text lines.
		"""
		try:
			throw_if( 'draw', draw )
			throw_if( 'text', text )
			throw_if( 'font', font )
			throw_if( 'max_width', max_width )
			
			words = str( text ).split( )
			lines = [ ]
			current_line = ''
			
			for word in words:
				candidate = word if not current_line else f'{current_line} {word}'
				
				if self.get_text_width( draw, candidate, font ) <= max_width:
					current_line = candidate
					continue
				
				if current_line:
					lines.append( current_line )
				
				current_line = word
			
			if current_line:
				lines.append( current_line )
			
			return lines
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'wrap_text( self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int ) -> List[str]'
			Logger( ).write( error )
			return [ str( text ) ]
	
	def draw_wrapped_line( self, draw: ImageDraw.ImageDraw, text: str,
			font: ImageFont.ImageFont, x: int, y: int, max_width: int,
			fill: tuple[ int, int, int ], line_spacing: int ) -> int:
		"""Draw wrapped text and return the next vertical position.

		Purpose:
			Draw one logical label line, wrapping it as needed to the available label width.

		Args:
			draw (ImageDraw.ImageDraw): Active image drawing object.
			text (str): Text to render.
			font (ImageFont.ImageFont): Font used to render text.
			x (int): Left x-coordinate.
			y (int): Starting y-coordinate.
			max_width (int): Maximum line width.
			fill (tuple[int, int, int]): RGB text color.
			line_spacing (int): Spacing between rendered lines.

		Returns:
			int: Next y-coordinate after drawing.
		"""
		try:
			throw_if( 'draw', draw )
			throw_if( 'text', text )
			throw_if( 'font', font )
			throw_if( 'x', x )
			throw_if( 'y', y )
			throw_if( 'max_width', max_width )
			
			lines = self.wrap_text( draw, text, font, max_width )
			
			for wrapped_line in lines:
				draw.text( (x, y), wrapped_line, font=font, fill=fill )
				y += line_spacing
			
			return y
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'draw_wrapped_line( self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, x: int, y: int, max_width: int, fill: tuple[int, int, int], line_spacing: int ) -> int'
			Logger( ).write( error )
			return y + line_spacing
	
	def create_label_image( self, record: SyntheticLabelRecord ) -> Image.Image:
		"""Create one OCR-friendly synthetic label image.

		Purpose:
			Render a simple fictional alcohol label optimized for Tesseract readability. The
			default design intentionally uses black text, a white background, large fonts, and
			simple line structure. Scenario-specific treatments are limited so the demonstration
			pack exercises Fiddy without making every synthetic image unreadable.

		Args:
			record (SyntheticLabelRecord): Synthetic label record to render.

		Returns:
			Image.Image: Rendered synthetic label image.
		"""
		try:
			throw_if( 'record', record )
			
			background = (255, 255, 255)
			text_color = (0, 0, 0)
			border_color = (0, 0, 0)
			
			if record.scenario == SCENARIO_LOW_CONTRAST:
				background = (245, 245, 245)
				text_color = (95, 95, 95)
				border_color = (130, 130, 130)
			
			image = Image.new( 'RGB', (self.label_width, self.label_height), background )
			draw = ImageDraw.Draw( image )
			title_font = self.get_font( 72, bold=True )
			subtitle_font = self.get_font( 46, bold=True )
			body_font = self.get_font( 40, bold=False )
			warning_font = self.get_font( 30, bold=True )
			margin = 80
			max_width = self.label_width - (margin * 2)
			y = 70
			
			draw.rectangle(
				[
						(margin // 2, margin // 2),
						(self.label_width - margin // 2, self.label_height - margin // 2)
				],
				outline=border_color,
				width=5
			)
			
			lines = record.to_label_lines( )
			
			if lines:
				y = self.draw_wrapped_line(
					draw=draw,
					text=lines[ 0 ],
					font=title_font,
					x=margin,
					y=y,
					max_width=max_width,
					fill=text_color,
					line_spacing=82
				)
			
			if len( lines ) > 1:
				y += 10
				y = self.draw_wrapped_line(
					draw=draw,
					text=lines[ 1 ],
					font=subtitle_font,
					x=margin,
					y=y,
					max_width=max_width,
					fill=text_color,
					line_spacing=58
				)
			
			y += 25
			
			for line in lines[ 2: ]:
				if line.startswith( 'GOVERNMENT WARNING' ):
					font = warning_font
					line_spacing = 38
				else:
					font = body_font
					line_spacing = 52
				
				y = self.draw_wrapped_line(
					draw=draw,
					text=line,
					font=font,
					x=margin,
					y=y,
					max_width=max_width,
					fill=text_color,
					line_spacing=line_spacing
				)
				y += 8
			
			if record.scenario == SCENARIO_SKEWED_LABEL:
				image = image.rotate(
					angle=3.0,
					resample=Image.Resampling.BICUBIC,
					expand=True,
					fillcolor=(255, 255, 255)
				)
			
			return image
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_label_image( self, record: SyntheticLabelRecord ) -> Image.Image'
			Logger( ).write( error )
			return Image.new( 'RGB', (self.label_width, self.label_height), 'white' )
	
	def write_manifest( self, records: List[ SyntheticLabelRecord ] ) -> Path:
		"""Write the synthetic manifest CSV.

		Purpose:
			Convert synthetic label records into manifest rows using the standard Fiddy manifest
			schema and write the resulting CSV to ``samples/manifests``.

		Args:
			records (List[SyntheticLabelRecord]): Synthetic records to write.

		Returns:
			Path: Generated manifest path.
		"""
		try:
			throw_if( 'records', records )
			
			self.ensure_demo_directories( )
			df_manifest = pd.DataFrame(
				[
						record.to_manifest_record( )
						for record in records
				],
				columns=MANIFEST_COLUMNS
			)
			df_manifest.to_csv( self.manifest_path, index=False, encoding='utf-8-sig' )
			
			return self.manifest_path
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'write_manifest( self, records: List[SyntheticLabelRecord] ) -> Path'
			Logger( ).write( error )
			raise
	
	def write_label_images( self, records: List[ SyntheticLabelRecord ] ) -> List[ Path ]:
		"""Write synthetic label artwork files.

		Purpose:
			Render and save one PNG image for each synthetic label record under ``samples/labels``.

		Args:
			records (List[SyntheticLabelRecord]): Synthetic records to render.

		Returns:
			List[Path]: Generated label image paths.
		"""
		try:
			throw_if( 'records', records )
			
			self.ensure_demo_directories( )
			file_paths = [ ]
			
			for record in records:
				label_path = self.get_safe_label_path( record.file_name )
				image = self.create_label_image( record )
				image.save( label_path, format='PNG' )
				file_paths.append( label_path )
			
			return file_paths
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'write_label_images( self, records: List[SyntheticLabelRecord] ) -> List[Path]'
			Logger( ).write( error )
			raise
	
	def write_label_zip( self, label_paths: List[ Path ] ) -> Path:
		"""Write a ZIP archive containing the generated synthetic label images.

		Purpose:
			Create one upload-friendly ZIP file containing all generated PNG labels. The ZIP
			archive simplifies demonstration because the reviewer can upload one manifest CSV and
			one label ZIP instead of selecting eight individual label files.

		Args:
			label_paths (List[Path]): Generated label image paths to include in the ZIP archive.

		Returns:
			Path: Generated ZIP archive path.
		"""
		try:
			throw_if( 'label_paths', label_paths )
			
			self.ensure_demo_directories( )
			
			if self.zip_path.exists( ):
				self.zip_path.unlink( )
			
			with zipfile.ZipFile( self.zip_path, mode='w',
					compression=zipfile.ZIP_DEFLATED ) as archive:
				for label_path in label_paths:
					resolved_path = Path( label_path ).resolve( )
					label_root = self.label_directory.resolve( )
					
					if label_root not in resolved_path.parents and resolved_path != label_root:
						continue
					
					if not resolved_path.name.startswith( f'{self.prefix}_' ):
						continue
					
					archive.write( resolved_path, arcname=resolved_path.name )
			
			return self.zip_path
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'write_label_zip( self, label_paths: List[Path] ) -> Path'
			Logger( ).write( error )
			raise
	
	def generate_standard_demo_pack( self, overwrite: bool = False ) -> SyntheticGenerationResult:
		"""Generate the standard deterministic Fiddy demo pack.

		Purpose:
			Create the standard fictional manifest, eight OCR-friendly label images, and one ZIP
			archive containing the generated label images. Existing generated files are preserved
			unless ``overwrite`` is ``True``.

		Args:
			overwrite (bool): Indicates whether existing generated demo files may be replaced.

		Returns:
			SyntheticGenerationResult: Generation outcome with paths, count, and status message.
		"""
		try:
			self.ensure_demo_directories( )
			existing_files = self.get_generated_file_paths( )
			
			if existing_files and not overwrite:
				return SyntheticGenerationResult(
					manifest_path=str( self.manifest_path ),
					label_directory=str( self.label_directory ),
					zip_path=str( self.zip_path ),
					generated_files=[
							str( path )
							for path in existing_files
					],
					deleted_files=[ ],
					record_count=0,
					success=False,
					message=(
							'Generated demo files already exist. Select overwrite to replace '
							'the standard demo pack.'
					)
				)
			
			if existing_files and overwrite:
				self.clear_demo_pack( )
			
			records = self.get_standard_records( )
			manifest_path = self.write_manifest( records )
			label_paths = self.write_label_images( records )
			zip_path = self.write_label_zip( label_paths )
			generated_files = [
					                  str( manifest_path ),
					                  str( zip_path )
			                  ] + [
					                  str( path )
					                  for path in label_paths
			                  ]
			
			return SyntheticGenerationResult(
				manifest_path=str( manifest_path ),
				label_directory=str( self.label_directory ),
				zip_path=str( zip_path ),
				generated_files=generated_files,
				deleted_files=[ ],
				record_count=len( records ),
				success=True,
				message='Standard Fiddy synthetic demo pack generated successfully.'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'generate_standard_demo_pack( self, overwrite: bool = False ) -> SyntheticGenerationResult'
			Logger( ).write( error )
			return SyntheticGenerationResult(
				manifest_path=str( self.manifest_path ),
				label_directory=str( self.label_directory ),
				zip_path=str( self.zip_path ),
				generated_files=[ ],
				deleted_files=[ ],
				record_count=0,
				success=False,
				message=f'Synthetic demo pack generation failed: {e}'
			)
	
	def clear_demo_pack( self ) -> SyntheticGenerationResult:
		"""Delete generated Fiddy demo pack files.

		Purpose:
			Delete only the configured synthetic manifest file, generated ZIP archive, and label
			files under ``samples/labels`` that begin with the configured demo prefix. No other
			files are deleted.

		Returns:
			SyntheticGenerationResult: Cleanup outcome with deleted file paths and status message.
		"""
		try:
			deleted_files = [ ]
			self.ensure_demo_directories( )
			
			if self.manifest_path.exists( ):
				self.manifest_path.unlink( )
				deleted_files.append( str( self.manifest_path ) )
			
			if self.zip_path.exists( ):
				self.zip_path.unlink( )
				deleted_files.append( str( self.zip_path ) )
			
			if self.label_directory.exists( ):
				for label_path in sorted(
						self.label_directory.glob( f'{self.prefix}_*{self.label_extension}' ) ):
					resolved_path = label_path.resolve( )
					label_root = self.label_directory.resolve( )
					
					if label_root not in resolved_path.parents and resolved_path != label_root:
						continue
					
					if not resolved_path.name.startswith( f'{self.prefix}_' ):
						continue
					
					resolved_path.unlink( )
					deleted_files.append( str( resolved_path ) )
			
			return SyntheticGenerationResult(
				manifest_path=str( self.manifest_path ),
				label_directory=str( self.label_directory ),
				zip_path=str( self.zip_path ),
				generated_files=[ ],
				deleted_files=deleted_files,
				record_count=0,
				success=True,
				message=f'Cleared {len( deleted_files )} generated Fiddy demo file(s).'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'clear_demo_pack( self ) -> SyntheticGenerationResult'
			Logger( ).write( error )
			return SyntheticGenerationResult(
				manifest_path=str( self.manifest_path ),
				label_directory=str( self.label_directory ),
				zip_path=str( self.zip_path ),
				generated_files=[ ],
				deleted_files=[ ],
				record_count=0,
				success=False,
				message=f'Synthetic demo pack cleanup failed: {e}'
			)

# ==========================================================================================
# Command-Line Entrypoint
# ==========================================================================================

def main( ) -> None:
	"""Generate the standard Fiddy synthetic demo pack from the command line.

	Purpose:
		Provide a simple local utility path for developers who want to generate the standard
		demo pack without opening the Streamlit interface.

	Returns:
		None.
	"""
	try:
		generator = SyntheticDataGenerator( )
		result = generator.generate_standard_demo_pack( overwrite=True )
		print( result.message )
		print( f'Manifest: {result.manifest_path}' )
		print( f'Labels: {result.label_directory}' )
		print( f'Label ZIP: {result.zip_path}' )
		print( f'Records: {result.record_count}' )
	except Exception as e:
		error = Error( e )
		error.cause = 'SyntheticDataGenerator'
		error.module = __name__
		error.method = 'main( ) -> None'
		Logger( ).write( error )
		print( f'Synthetic demo generation failed: {e}' )

if __name__ == '__main__':
	main( )