'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                deployment_evidence.py
      Author:                  Terry D. Eppler
      Created:                 06-06-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-06-2026
    ******************************************************************************************
    <copyright file="deployment_evidence.py" company="Terry D. Eppler">

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
        Provides deployment, security, integration, and data-handling evidence for the Fiddy
        prototype.

        This module inspects project files and configuration flags to determine whether the
        prototype has evidence of Azure-ready packaging, local OCR operation, disabled external
        machine-learning endpoints, disabled COLA integration, temporary-file cleanup posture,
        and no long-term storage of uploaded label artwork or extracted OCR text.

        The module does not deploy infrastructure, start Azure services, call external
        endpoints, persist uploaded data, or alter configuration. It only produces structured
        evidence records for Streamlit display, CSV export, JSON export, Markdown reporting, and
        stakeholder acceptance review.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field

import config as cfg
from booger import Error, Logger
from config import throw_if

EVIDENCE_STATUS_MET: str = 'Met'
EVIDENCE_STATUS_PARTIAL: str = 'Partially Met'
EVIDENCE_STATUS_NOT_MET: str = 'Not Met'
EVIDENCE_STATUS_NOT_EVALUATED: str = 'Not Evaluated'

CHECK_DOCKERFILE_PRESENT: str = 'DEPLOY-001'
CHECK_AZURE_ARTIFACT_PRESENT: str = 'DEPLOY-002'
CHECK_LOCAL_OCR_REQUIRED: str = 'DEPLOY-003'
CHECK_EXTERNAL_ML_DISABLED: str = 'DEPLOY-004'
CHECK_COLA_DISABLED: str = 'DEPLOY-005'
CHECK_UPLOAD_PERSISTENCE_DISABLED: str = 'DEPLOY-006'
CHECK_RAW_TEXT_LOGGING_DISABLED: str = 'DEPLOY-007'
CHECK_TEMP_CLEANUP_CONFIGURED: str = 'DEPLOY-008'
CHECK_AZURE_SMOKE_TEST: str = 'DEPLOY-009'

AZURE_ARTIFACT_NAMES: List[ str ] = [
		'azure.yaml',
		'containerapp.yaml',
		'container-app.yaml',
		'webapp.yaml',
		'azure-pipelines.yml',
		'.github/workflows/azure.yml',
		'.github/workflows/deploy.yml'
]

DOCKERFILE_NAMES: List[ str ] = [
		'Dockerfile',
		'dockerfile'
]

class DeploymentEvidenceItem( BaseModel ):
	"""Represent one deployment or security evidence check.

	Purpose:
		Store one evidence check used to support stakeholder acceptance. Each item contains a
		stable check identifier, category, display name, status, evidence statement,
		recommendation, optional path, and evaluation timestamp. The model is intentionally flat
		so it can be displayed in Streamlit, exported as CSV, serialized as JSON, or included in a
		Markdown acceptance package.

	Attributes:
		check_id (str): Stable evidence check identifier.
		category (str): Evidence category such as deployment, security, integration, or data
			handling.
		name (str): Human-readable evidence check name.
		status (str): Check status such as ``Met``, ``Partially Met``, ``Not Met``, or
			``Not Evaluated``.
		evidence (str): Plain-language evidence statement.
		recommendation (str): Recommended action to improve or preserve the posture.
		path (str): Optional file-system path supporting the evidence.
		evaluated_on (str): UTC timestamp when the evidence item was created.
	"""
	
	check_id: str = Field( default='' )
	category: str = Field( default='' )
	name: str = Field( default='' )
	status: str = Field( default=EVIDENCE_STATUS_NOT_EVALUATED )
	evidence: str = Field( default='' )
	recommendation: str = Field( default='' )
	path: str = Field( default='' )
	evaluated_on: str = Field(
		default_factory=lambda: datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
	)
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert the evidence item into a flat display/export record.

		Purpose:
			Return a dictionary suitable for DataFrame construction, Streamlit display, CSV
			export, JSON serialization, Markdown reporting, and stakeholder evidence review.

		Returns:
			Dict[str, object]: Flat evidence item record. If conversion fails, returns a
			conservative fallback record.
		"""
		try:
			return {
					'Check ID': self.check_id,
					'Category': self.category,
					'Name': self.name,
					'Status': self.status,
					'Evidence': self.evidence,
					'Recommendation': self.recommendation,
					'Path': self.path,
					'Evaluated On': self.evaluated_on
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Check ID': self.check_id,
					'Category': self.category,
					'Name': self.name,
					'Status': EVIDENCE_STATUS_NOT_EVALUATED,
					'Evidence': 'Deployment evidence item could not be rendered.',
					'Recommendation': 'Inspect the deployment evidence error log.',
					'Path': '',
					'Evaluated On': ''
			}

class DeploymentEvidence( BaseModel ):
	"""Represent the complete deployment and security evidence result.

	Purpose:
		Aggregate deployment, security, integration, and data-handling evidence checks into one
		exportable result. The model provides status counts, summary status, DataFrame
		conversion, JSON serialization, Markdown rendering, and acceptance-checker evidence flags.

	Attributes:
		items (List[DeploymentEvidenceItem]): Individual deployment evidence checks.
		created_on (str): UTC timestamp when the result was created.
	"""
	
	items: List[ DeploymentEvidenceItem ] = Field( default_factory=list )
	created_on: str = Field(
		default_factory=lambda: datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
	)
	
	def status_counts( self ) -> Dict[ str, int ]:
		"""Count evidence items by status.

		Purpose:
			Produce status counts for dashboard metrics, summary records, JSON output, and
			Markdown reports.

		Returns:
			Dict[str, int]: Status counts keyed by evidence status text.
		"""
		try:
			counts = {
					EVIDENCE_STATUS_MET: 0,
					EVIDENCE_STATUS_PARTIAL: 0,
					EVIDENCE_STATUS_NOT_MET: 0,
					EVIDENCE_STATUS_NOT_EVALUATED: 0
			}
			
			for item in self.items:
				counts[ item.status ] = counts.get( item.status, 0 ) + 1
			
			return counts
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'status_counts( self ) -> Dict[str, int]'
			Logger( ).write( error )
			return {
					EVIDENCE_STATUS_MET: 0,
					EVIDENCE_STATUS_PARTIAL: 0,
					EVIDENCE_STATUS_NOT_MET: 0,
					EVIDENCE_STATUS_NOT_EVALUATED: 0
			}
	
	def overall_status( self ) -> str:
		"""Calculate the overall deployment evidence status.

		Purpose:
			Return an aggregate status for the evidence result. Any failed item makes the overall
			status ``Not Met``. Any partial or not-evaluated item makes the overall status
			``Partially Met`` unless a failure exists. All met items produce ``Met``.

		Returns:
			str: Aggregate evidence status.
		"""
		try:
			if not self.items:
				return EVIDENCE_STATUS_NOT_EVALUATED
			
			counts = self.status_counts( )
			
			if counts.get( EVIDENCE_STATUS_NOT_MET, 0 ) > 0:
				return EVIDENCE_STATUS_NOT_MET
			
			if counts.get( EVIDENCE_STATUS_PARTIAL, 0 ) > 0:
				return EVIDENCE_STATUS_PARTIAL
			
			if counts.get( EVIDENCE_STATUS_NOT_EVALUATED, 0 ) > 0:
				return EVIDENCE_STATUS_PARTIAL
			
			return EVIDENCE_STATUS_MET
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'overall_status( self ) -> str'
			Logger( ).write( error )
			return EVIDENCE_STATUS_NOT_EVALUATED
	
	def to_records( self ) -> List[ Dict[ str, object ] ]:
		"""Convert all evidence items into flat records.

		Purpose:
			Convert each deployment evidence item into a dictionary for DataFrame display, CSV
			export, JSON export, and Markdown reporting.

		Returns:
			List[Dict[str, object]]: Flat evidence item records.
		"""
		try:
			return [
					item.to_record( )
					for item in self.items
			]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_records( self ) -> List[Dict[str, object]]'
			Logger( ).write( error )
			return [ ]
	
	def to_dataframe( self ) -> pd.DataFrame:
		"""Convert deployment evidence into a pandas DataFrame.

		Purpose:
			Create a DataFrame from all evidence item records for Streamlit display, CSV export,
			and acceptance evidence packaging.

		Returns:
			pd.DataFrame: Deployment evidence DataFrame.
		"""
		try:
			return pd.DataFrame( self.to_records( ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_dataframe( self ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def to_summary_record( self ) -> Dict[ str, object ]:
		"""Convert deployment evidence into a one-row summary record.

		Purpose:
			Provide high-level evidence status and counts for dashboards, acceptance summaries,
			and export packages.

		Returns:
			Dict[str, object]: Flat deployment evidence summary record.
		"""
		try:
			counts = self.status_counts( )
			
			return {
					'Deployment Evidence Status': self.overall_status( ),
					'Met': counts.get( EVIDENCE_STATUS_MET, 0 ),
					'Partially Met': counts.get( EVIDENCE_STATUS_PARTIAL, 0 ),
					'Not Met': counts.get( EVIDENCE_STATUS_NOT_MET, 0 ),
					'Not Evaluated': counts.get( EVIDENCE_STATUS_NOT_EVALUATED, 0 ),
					'Created On': self.created_on
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_summary_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Deployment Evidence Status': EVIDENCE_STATUS_NOT_EVALUATED,
					'Met': 0,
					'Partially Met': 0,
					'Not Met': 0,
					'Not Evaluated': 0,
					'Created On': ''
			}
	
	def to_json( self ) -> str:
		"""Serialize deployment evidence as formatted JSON.

		Purpose:
			Create a JSON evidence payload containing summary status and every evidence check.
			The output is intended for evidence packages, test harnesses, downloads, and
			stakeholder records.

		Returns:
			str: Formatted JSON string. If serialization fails, returns an empty JSON object.
		"""
		try:
			payload = {
					'summary': self.to_summary_record( ),
					'items': self.to_records( )
			}
			return json.dumps( payload, indent=2, default=str )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_json( self ) -> str'
			Logger( ).write( error )
			return '{}'
	
	def to_markdown( self ) -> str:
		"""Render deployment evidence as Markdown.

		Purpose:
			Create a stakeholder-readable Markdown report containing the overall evidence status,
			status counts, and each deployment evidence item with evidence and recommendation.

		Returns:
			str: Markdown deployment evidence report.
		"""
		try:
			summary = self.to_summary_record( )
			lines = [
					'# Fiddy Deployment Evidence',
					'',
					f'Created On: {self.created_on}',
					f'Overall Status: {summary.get( "Deployment Evidence Status", "" )}',
					'',
					'## Status Counts',
					'',
					f'- Met: {summary.get( "Met", 0 )}',
					f'- Partially Met: {summary.get( "Partially Met", 0 )}',
					f'- Not Met: {summary.get( "Not Met", 0 )}',
					f'- Not Evaluated: {summary.get( "Not Evaluated", 0 )}',
					'',
					'## Evidence Checks',
					''
			]
			
			for item in self.items:
				lines.extend(
					[
							f'### {item.check_id} - {item.name}',
							'',
							f'- Category: {item.category}',
							f'- Status: {item.status}',
							f'- Evidence: {item.evidence}',
							f'- Recommendation: {item.recommendation}',
							f'- Path: {item.path}',
							f'- Evaluated On: {item.evaluated_on}',
							''
					]
				)
			
			return '\n'.join( lines )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_markdown( self ) -> str'
			Logger( ).write( error )
			return '# Fiddy Deployment Evidence\n\nDeployment evidence could not be rendered.'
	
	def to_acceptance_evidence( self ) -> Dict[ str, object ]:
		"""Convert deployment checks into acceptance-checker evidence flags.

		Purpose:
			Produce supplemental evidence keys consumed by ``AcceptanceChecker``. This bridges the
			deployment evidence module into requirement-level acceptance evaluation without
			coupling the acceptance checker to file-system inspection logic.

		Returns:
			Dict[str, object]: Evidence flags suitable for ``AcceptanceChecker``.
		"""
		try:
			item_map = {
					item.check_id: item
					for item in self.items
			}
			
			def is_met( check_id: str ) -> bool:
				return item_map.get(
					check_id,
					DeploymentEvidenceItem( )
				).status == EVIDENCE_STATUS_MET
			
			def is_partial_or_met( check_id: str ) -> bool:
				return item_map.get(
					check_id,
					DeploymentEvidenceItem( )
				).status in (EVIDENCE_STATUS_MET, EVIDENCE_STATUS_PARTIAL)
			
			return {
					'AZURE_READY_ARTIFACTS_PRESENT': is_partial_or_met(
						CHECK_AZURE_ARTIFACT_PRESENT ),
					'AZURE_SMOKE_TEST_PASSED': is_met( CHECK_AZURE_SMOKE_TEST ),
					'REQUIRE_LOCAL_OCR': is_met( CHECK_LOCAL_OCR_REQUIRED ),
					'ALLOW_EXTERNAL_ML_ENDPOINTS': not is_met( CHECK_EXTERNAL_ML_DISABLED ),
					'COLA_INTEGRATION_ENABLED': not is_met( CHECK_COLA_DISABLED ),
					'ENABLE_UPLOAD_PERSISTENCE': not is_met( CHECK_UPLOAD_PERSISTENCE_DISABLED ),
					'ENABLE_RAW_TEXT_LOGGING': not is_met( CHECK_RAW_TEXT_LOGGING_DISABLED ),
					'LONG_TERM_STORAGE_DISABLED': is_met( CHECK_UPLOAD_PERSISTENCE_DISABLED ),
					'DEPLOYMENT_TARGET': str( getattr( cfg, 'DEPLOYMENT_TARGET', 'local' ) )
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_acceptance_evidence( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'REQUIRE_LOCAL_OCR': True,
					'ALLOW_EXTERNAL_ML_ENDPOINTS': False,
					'COLA_INTEGRATION_ENABLED': False,
					'LONG_TERM_STORAGE_DISABLED': True,
					'DEPLOYMENT_TARGET': 'local'
			}

class DeploymentEvidenceChecker( ):
	"""Inspect project and configuration posture for deployment evidence.

	Purpose:
		Check whether the project has evidence of Docker packaging, Azure-ready artifacts,
		local-OCR configuration, disabled external ML endpoints, disabled COLA integration,
		disabled persistent upload storage, disabled raw OCR text logging, configured temporary
		cleanup, and Azure smoke-test evidence.

		The checker performs read-only inspection. It does not deploy infrastructure, call Azure,
		create files, delete files, modify configuration, or start external services.

	Attributes:
		_project_root (Path): Project root path used for file checks.
		_items (List[DeploymentEvidenceItem]): Evidence items created during evaluation.
	"""
	
	_project_root: Path
	_items: List[ DeploymentEvidenceItem ]
	
	def __init__( self, project_root: str | Path | None = None ) -> None:
		"""Initialize the deployment evidence checker.

		Purpose:
			Store the project root used for file-system evidence checks. When no project root is
			supplied, the current working directory is used.

		Args:
			project_root (str | Path | None): Optional project root path.

		Returns:
			None.
		"""
		try:
			if project_root is None:
				self._project_root = Path.cwd( )
			else:
				self._project_root = Path( project_root )
			
			self._items = [ ]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = '__init__( self, project_root: str | Path | None = None ) -> None'
			Logger( ).write( error )
			self._project_root = Path.cwd( )
			self._items = [ ]
	
	@property
	def project_root( self ) -> Path:
		"""Return the configured project root.

		Purpose:
			Expose the project root used for read-only file-system evidence checks.

		Returns:
			Path: Project root path.
		"""
		return self._project_root
	
	def create_item( self, check_id: str, category: str, name: str, status: str,
			evidence: str, recommendation: str = '', path: str = '' ) -> DeploymentEvidenceItem:
		"""Create one deployment evidence item.

		Purpose:
			Centralize construction of deployment evidence records. Required values are validated
			before the item is created. If creation fails, a conservative fallback item is
			returned.

		Args:
			check_id (str): Stable evidence check identifier.
			category (str): Evidence category.
			name (str): Human-readable evidence check name.
			status (str): Evidence status.
			evidence (str): Plain-language evidence statement.
			recommendation (str): Recommended action.
			path (str): Optional supporting path.

		Returns:
			DeploymentEvidenceItem: Evidence item.
		"""
		try:
			throw_if( 'check_id', check_id )
			throw_if( 'category', category )
			throw_if( 'name', name )
			throw_if( 'status', status )
			throw_if( 'evidence', evidence )
			
			return DeploymentEvidenceItem(
				check_id=check_id,
				category=category,
				name=name,
				status=status,
				evidence=evidence,
				recommendation=recommendation,
				path=path
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_item( self, *args ) -> DeploymentEvidenceItem'
			Logger( ).write( error )
			return DeploymentEvidenceItem(
				check_id=check_id or '',
				category=category or '',
				name=name or '',
				status=EVIDENCE_STATUS_NOT_EVALUATED,
				evidence='Deployment evidence item could not be created.',
				recommendation='Inspect the deployment evidence error log.',
				path=path or ''
			)
	
	def find_existing_path( self, candidate_names: List[ str ] ) -> Optional[ Path ]:
		"""Return the first existing project-relative path from candidates.

		Purpose:
			Search for the first candidate file under the configured project root and return the
			matching path. This helper supports Docker and Azure artifact checks without hard
			coding a single expected layout.

		Args:
			candidate_names (List[str]): Project-relative candidate file names.

		Returns:
			Optional[Path]: Matching path when found; otherwise, ``None``.
		"""
		try:
			throw_if( 'candidate_names', candidate_names )
			
			for candidate in candidate_names:
				path = self._project_root / candidate
				
				if path.exists( ):
					return path
			
			return None
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'find_existing_path( self, candidate_names: List[str] ) -> Optional[Path]'
			Logger( ).write( error )
			return None
	
	def get_config_bool( self, name: str, default: bool ) -> bool:
		"""Return a Boolean configuration value.

		Purpose:
			Safely read optional Boolean posture flags from the configuration module. Missing,
			invalid, or unavailable values return the supplied default.

		Args:
			name (str): Configuration attribute name.
			default (bool): Default value.

		Returns:
			bool: Resolved configuration value.
		"""
		try:
			throw_if( 'name', name )
			return bool( getattr( cfg, name, default ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_config_bool( self, name: str, default: bool ) -> bool'
			Logger( ).write( error )
			return default
	
	def get_config_text( self, name: str, default: str ) -> str:
		"""Return a text configuration value.

		Purpose:
			Safely read optional text posture flags from the configuration module. Missing,
			invalid, or unavailable values return the supplied default.

		Args:
			name (str): Configuration attribute name.
			default (str): Default value.

		Returns:
			str: Resolved configuration text.
		"""
		try:
			throw_if( 'name', name )
			return str( getattr( cfg, name, default ) )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_config_text( self, name: str, default: str ) -> str'
			Logger( ).write( error )
			return default
	
	def check_dockerfile_present( self ) -> DeploymentEvidenceItem:
		"""Check whether a Dockerfile exists.

		Purpose:
			Determine whether the project contains a Dockerfile or dockerfile at the project root.
			A Dockerfile is treated as evidence of container packaging readiness.

		Returns:
			DeploymentEvidenceItem: Dockerfile evidence item.
		"""
		try:
			path = self.find_existing_path( DOCKERFILE_NAMES )
			
			if path:
				return self.create_item(
					check_id=CHECK_DOCKERFILE_PRESENT,
					category='Deployment',
					name='Dockerfile Present',
					status=EVIDENCE_STATUS_MET,
					evidence='A Dockerfile was found for container packaging.',
					recommendation='Retain the Dockerfile and validate container build during acceptance testing.',
					path=str( path )
				)
			
			return self.create_item(
				check_id=CHECK_DOCKERFILE_PRESENT,
				category='Deployment',
				name='Dockerfile Present',
				status=EVIDENCE_STATUS_NOT_MET,
				evidence='No Dockerfile was found at the project root.',
				recommendation='Add a Dockerfile to support Azure container deployment evidence.'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'check_dockerfile_present( self ) -> DeploymentEvidenceItem'
			Logger( ).write( error )
			return self.create_item(
				check_id=CHECK_DOCKERFILE_PRESENT,
				category='Deployment',
				name='Dockerfile Present',
				status=EVIDENCE_STATUS_NOT_EVALUATED,
				evidence='Dockerfile evidence could not be evaluated.',
				recommendation='Inspect deployment evidence error logs.'
			)
	
	def check_azure_artifact_present( self ) -> DeploymentEvidenceItem:
		"""Check whether Azure deployment artifacts exist.

		Purpose:
			Determine whether the project contains a recognized Azure deployment artifact such as
			``azure.yaml``, container app YAML, web app YAML, Azure pipeline YAML, or a GitHub
			workflow used for Azure deployment.

		Returns:
			DeploymentEvidenceItem: Azure artifact evidence item.
		"""
		try:
			path = self.find_existing_path( AZURE_ARTIFACT_NAMES )
			config_flag = self.get_config_bool( 'AZURE_READY_ARTIFACTS_PRESENT', False )
			
			if path:
				return self.create_item(
					check_id=CHECK_AZURE_ARTIFACT_PRESENT,
					category='Deployment',
					name='Azure Deployment Artifact Present',
					status=EVIDENCE_STATUS_MET,
					evidence='An Azure deployment artifact was found.',
					recommendation='Run an Azure-hosted smoke test and retain the result.',
					path=str( path )
				)
			
			if config_flag:
				return self.create_item(
					check_id=CHECK_AZURE_ARTIFACT_PRESENT,
					category='Deployment',
					name='Azure Deployment Artifact Present',
					status=EVIDENCE_STATUS_PARTIAL,
					evidence='Configuration indicates Azure-ready artifacts are present, but no recognized artifact was found from this project root.',
					recommendation='Confirm project root or add a recognized Azure artifact path.'
				)
			
			return self.create_item(
				check_id=CHECK_AZURE_ARTIFACT_PRESENT,
				category='Deployment',
				name='Azure Deployment Artifact Present',
				status=EVIDENCE_STATUS_NOT_MET,
				evidence='No recognized Azure deployment artifact was found.',
				recommendation='Add Azure deployment artifacts and run an Azure smoke test.'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'check_azure_artifact_present( self ) -> DeploymentEvidenceItem'
			Logger( ).write( error )
			return self.create_item(
				check_id=CHECK_AZURE_ARTIFACT_PRESENT,
				category='Deployment',
				name='Azure Deployment Artifact Present',
				status=EVIDENCE_STATUS_NOT_EVALUATED,
				evidence='Azure artifact evidence could not be evaluated.',
				recommendation='Inspect deployment evidence error logs.'
			)
	
	def check_local_ocr_required( self ) -> DeploymentEvidenceItem:
		"""Check whether local OCR is required.

		Purpose:
			Determine whether configuration requires local OCR operation. This supports the
			firewall-safe prototype requirement because OCR should not depend on external
			machine-learning endpoints.

		Returns:
			DeploymentEvidenceItem: Local OCR evidence item.
		"""
		try:
			require_local_ocr = self.get_config_bool( 'REQUIRE_LOCAL_OCR', True )
			
			if require_local_ocr:
				return self.create_item(
					check_id=CHECK_LOCAL_OCR_REQUIRED,
					category='Security',
					name='Local OCR Required',
					status=EVIDENCE_STATUS_MET,
					evidence='Configuration requires local OCR operation.',
					recommendation='Keep local OCR required unless procurement scope changes.'
				)
			
			return self.create_item(
				check_id=CHECK_LOCAL_OCR_REQUIRED,
				category='Security',
				name='Local OCR Required',
				status=EVIDENCE_STATUS_NOT_MET,
				evidence='Configuration does not require local OCR operation.',
				recommendation='Set REQUIRE_LOCAL_OCR to True.'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'check_local_ocr_required( self ) -> DeploymentEvidenceItem'
			Logger( ).write( error )
			return self.create_item(
				check_id=CHECK_LOCAL_OCR_REQUIRED,
				category='Security',
				name='Local OCR Required',
				status=EVIDENCE_STATUS_NOT_EVALUATED,
				evidence='Local OCR evidence could not be evaluated.',
				recommendation='Inspect configuration and deployment evidence logs.'
			)
	
	def check_external_ml_disabled( self ) -> DeploymentEvidenceItem:
		"""Check whether external machine-learning endpoints are disabled.

		Purpose:
			Determine whether configuration prevents use of external ML endpoints. The prototype
			should remain local-first and firewall-safe unless a future scope explicitly changes
			that posture.

		Returns:
			DeploymentEvidenceItem: External endpoint evidence item.
		"""
		try:
			allow_external_ml = self.get_config_bool( 'ALLOW_EXTERNAL_ML_ENDPOINTS', False )
			
			if not allow_external_ml:
				return self.create_item(
					check_id=CHECK_EXTERNAL_ML_DISABLED,
					category='Security',
					name='External ML Endpoints Disabled',
					status=EVIDENCE_STATUS_MET,
					evidence='Configuration disables external machine-learning endpoints.',
					recommendation='Keep external ML endpoints disabled for the prototype.'
				)
			
			return self.create_item(
				check_id=CHECK_EXTERNAL_ML_DISABLED,
				category='Security',
				name='External ML Endpoints Disabled',
				status=EVIDENCE_STATUS_NOT_MET,
				evidence='Configuration allows external machine-learning endpoints.',
				recommendation='Set ALLOW_EXTERNAL_ML_ENDPOINTS to False.'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'check_external_ml_disabled( self ) -> DeploymentEvidenceItem'
			Logger( ).write( error )
			return self.create_item(
				check_id=CHECK_EXTERNAL_ML_DISABLED,
				category='Security',
				name='External ML Endpoints Disabled',
				status=EVIDENCE_STATUS_NOT_EVALUATED,
				evidence='External ML endpoint evidence could not be evaluated.',
				recommendation='Inspect configuration and deployment evidence logs.'
			)
	
	def check_cola_disabled( self ) -> DeploymentEvidenceItem:
		"""Check whether direct COLA integration is disabled.

		Purpose:
			Determine whether configuration indicates direct COLA integration is disabled. The
			prototype should rely on reviewer-provided application data rather than direct COLA
			system integration.

		Returns:
			DeploymentEvidenceItem: COLA integration evidence item.
		"""
		try:
			cola_enabled = self.get_config_bool( 'COLA_INTEGRATION_ENABLED', False )
			
			if not cola_enabled:
				return self.create_item(
					check_id=CHECK_COLA_DISABLED,
					category='Integration',
					name='Direct COLA Integration Disabled',
					status=EVIDENCE_STATUS_MET,
					evidence='Configuration indicates direct COLA integration is disabled.',
					recommendation='Keep direct COLA integration disabled for the prototype scope.'
				)
			
			return self.create_item(
				check_id=CHECK_COLA_DISABLED,
				category='Integration',
				name='Direct COLA Integration Disabled',
				status=EVIDENCE_STATUS_NOT_MET,
				evidence='Configuration indicates direct COLA integration is enabled.',
				recommendation='Set COLA_INTEGRATION_ENABLED to False unless scope changes.'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'check_cola_disabled( self ) -> DeploymentEvidenceItem'
			Logger( ).write( error )
			return self.create_item(
				check_id=CHECK_COLA_DISABLED,
				category='Integration',
				name='Direct COLA Integration Disabled',
				status=EVIDENCE_STATUS_NOT_EVALUATED,
				evidence='COLA integration evidence could not be evaluated.',
				recommendation='Inspect configuration and deployment evidence logs.'
			)
	
	def check_upload_persistence_disabled( self ) -> DeploymentEvidenceItem:
		"""Check whether persistent upload storage is disabled.

		Purpose:
			Determine whether uploaded label images are configured for temporary processing rather
			than persistent long-term storage.

		Returns:
			DeploymentEvidenceItem: Upload persistence evidence item.
		"""
		try:
			persistence_enabled = self.get_config_bool( 'ENABLE_UPLOAD_PERSISTENCE', False )
			long_term_storage_disabled = self.get_config_bool( 'LONG_TERM_STORAGE_DISABLED', True )
			
			if not persistence_enabled and long_term_storage_disabled:
				return self.create_item(
					check_id=CHECK_UPLOAD_PERSISTENCE_DISABLED,
					category='Data Handling',
					name='Persistent Upload Storage Disabled',
					status=EVIDENCE_STATUS_MET,
					evidence='Configuration disables persistent uploads and indicates long-term storage is disabled.',
					recommendation='Retain temporary-file cleanup and avoid persistent uploaded-image storage.'
				)
			
			return self.create_item(
				check_id=CHECK_UPLOAD_PERSISTENCE_DISABLED,
				category='Data Handling',
				name='Persistent Upload Storage Disabled',
				status=EVIDENCE_STATUS_NOT_MET,
				evidence=(
						f'Upload persistence enabled: {persistence_enabled}; long-term storage disabled: '
						f'{long_term_storage_disabled}.'
				),
				recommendation='Disable persistent upload storage and ensure long-term storage remains disabled.'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'check_upload_persistence_disabled( self ) -> DeploymentEvidenceItem'
			Logger( ).write( error )
			return self.create_item(
				check_id=CHECK_UPLOAD_PERSISTENCE_DISABLED,
				category='Data Handling',
				name='Persistent Upload Storage Disabled',
				status=EVIDENCE_STATUS_NOT_EVALUATED,
				evidence='Upload persistence evidence could not be evaluated.',
				recommendation='Inspect configuration and deployment evidence logs.'
			)
	
	def check_raw_text_logging_disabled( self ) -> DeploymentEvidenceItem:
		"""Check whether raw OCR text logging is disabled.

		Purpose:
			Determine whether raw OCR text logging is disabled. This supports privacy and
			no-long-term-storage expectations by avoiding unnecessary persistence of extracted
			label text.

		Returns:
			DeploymentEvidenceItem: Raw text logging evidence item.
		"""
		try:
			raw_text_logging = self.get_config_bool( 'ENABLE_RAW_TEXT_LOGGING', False )
			
			if not raw_text_logging:
				return self.create_item(
					check_id=CHECK_RAW_TEXT_LOGGING_DISABLED,
					category='Data Handling',
					name='Raw OCR Text Logging Disabled',
					status=EVIDENCE_STATUS_MET,
					evidence='Configuration disables raw OCR text logging.',
					recommendation='Keep raw OCR text out of logs and use sanitized diagnostics only.'
				)
			
			return self.create_item(
				check_id=CHECK_RAW_TEXT_LOGGING_DISABLED,
				category='Data Handling',
				name='Raw OCR Text Logging Disabled',
				status=EVIDENCE_STATUS_NOT_MET,
				evidence='Configuration enables raw OCR text logging.',
				recommendation='Set ENABLE_RAW_TEXT_LOGGING to False.'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'check_raw_text_logging_disabled( self ) -> DeploymentEvidenceItem'
			Logger( ).write( error )
			return self.create_item(
				check_id=CHECK_RAW_TEXT_LOGGING_DISABLED,
				category='Data Handling',
				name='Raw OCR Text Logging Disabled',
				status=EVIDENCE_STATUS_NOT_EVALUATED,
				evidence='Raw OCR text logging evidence could not be evaluated.',
				recommendation='Inspect configuration and deployment evidence logs.'
			)
	
	def check_temp_cleanup_configured( self ) -> DeploymentEvidenceItem:
		"""Check whether temporary cleanup posture is configured.

		Purpose:
			Determine whether configuration contains evidence that temporary upload/output data
			should be cleaned up. This check supports the no-long-term-storage requirement.

		Returns:
			DeploymentEvidenceItem: Temporary cleanup evidence item.
		"""
		try:
			cleanup_enabled = self.get_config_bool( 'ENABLE_TEMP_CLEANUP', True )
			retention_days = int( getattr( cfg, 'LOG_RETENTION_DAYS', 14 ) )
			
			if cleanup_enabled:
				return self.create_item(
					check_id=CHECK_TEMP_CLEANUP_CONFIGURED,
					category='Data Handling',
					name='Temporary Cleanup Configured',
					status=EVIDENCE_STATUS_MET,
					evidence=(
							f'Temporary cleanup is configured. Log retention days: {retention_days}.'
					),
					recommendation='Retain cleanup configuration and document runtime cleanup behavior.'
				)
			
			return self.create_item(
				check_id=CHECK_TEMP_CLEANUP_CONFIGURED,
				category='Data Handling',
				name='Temporary Cleanup Configured',
				status=EVIDENCE_STATUS_PARTIAL,
				evidence='Temporary cleanup is not explicitly enabled in configuration.',
				recommendation='Add ENABLE_TEMP_CLEANUP=True or document equivalent runtime cleanup.'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'check_temp_cleanup_configured( self ) -> DeploymentEvidenceItem'
			Logger( ).write( error )
			return self.create_item(
				check_id=CHECK_TEMP_CLEANUP_CONFIGURED,
				category='Data Handling',
				name='Temporary Cleanup Configured',
				status=EVIDENCE_STATUS_NOT_EVALUATED,
				evidence='Temporary cleanup evidence could not be evaluated.',
				recommendation='Inspect configuration and deployment evidence logs.'
			)
	
	def check_azure_smoke_test( self ) -> DeploymentEvidenceItem:
		"""Check whether Azure smoke-test evidence is configured.

		Purpose:
			Determine whether the project has evidence that an Azure-hosted smoke test passed.
			This check distinguishes Azure-ready posture from actual Azure runtime proof.

		Returns:
			DeploymentEvidenceItem: Azure smoke-test evidence item.
		"""
		try:
			smoke_test_passed = self.get_config_bool( 'AZURE_SMOKE_TEST_PASSED', False )
			deployment_target = self.get_config_text( 'DEPLOYMENT_TARGET', 'local' )
			
			if smoke_test_passed:
				return self.create_item(
					check_id=CHECK_AZURE_SMOKE_TEST,
					category='Deployment',
					name='Azure Smoke Test Passed',
					status=EVIDENCE_STATUS_MET,
					evidence='Configuration indicates an Azure-hosted smoke test passed.',
					recommendation='Retain Azure smoke-test screenshots, logs, and acceptance output package.'
				)
			
			if deployment_target.lower( ) == 'azure':
				return self.create_item(
					check_id=CHECK_AZURE_SMOKE_TEST,
					category='Deployment',
					name='Azure Smoke Test Passed',
					status=EVIDENCE_STATUS_PARTIAL,
					evidence='Deployment target is Azure, but smoke-test pass evidence is not configured.',
					recommendation='Run the Azure-hosted application and set AZURE_SMOKE_TEST_PASSED after validation.'
				)
			
			return self.create_item(
				check_id=CHECK_AZURE_SMOKE_TEST,
				category='Deployment',
				name='Azure Smoke Test Passed',
				status=EVIDENCE_STATUS_NOT_EVALUATED,
				evidence='No Azure smoke-test evidence is configured.',
				recommendation='Run an Azure-hosted smoke test when deployment artifacts are ready.'
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'check_azure_smoke_test( self ) -> DeploymentEvidenceItem'
			Logger( ).write( error )
			return self.create_item(
				check_id=CHECK_AZURE_SMOKE_TEST,
				category='Deployment',
				name='Azure Smoke Test Passed',
				status=EVIDENCE_STATUS_NOT_EVALUATED,
				evidence='Azure smoke-test evidence could not be evaluated.',
				recommendation='Inspect configuration and deployment evidence logs.'
			)
	
	def evaluate( self ) -> DeploymentEvidence:
		"""Evaluate all deployment, security, integration, and data-handling evidence.

		Purpose:
			Run all evidence checks and return a complete ``DeploymentEvidence`` result. The
			result can be displayed in the app, exported as CSV, serialized as JSON, rendered as
			Markdown, or converted into acceptance-checker evidence flags.

		Returns:
			DeploymentEvidence: Complete deployment evidence result.
		"""
		try:
			self._items = [
					self.check_dockerfile_present( ),
					self.check_azure_artifact_present( ),
					self.check_local_ocr_required( ),
					self.check_external_ml_disabled( ),
					self.check_cola_disabled( ),
					self.check_upload_persistence_disabled( ),
					self.check_raw_text_logging_disabled( ),
					self.check_temp_cleanup_configured( ),
					self.check_azure_smoke_test( )
			]
			
			return DeploymentEvidence( items=self._items )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate( self ) -> DeploymentEvidence'
			Logger( ).write( error )
			return DeploymentEvidence(
				items=[
						self.create_item(
							check_id='DEPLOYMENT-EVALUATION',
							category='Deployment',
							name='Deployment Evidence Evaluation',
							status=EVIDENCE_STATUS_NOT_EVALUATED,
							evidence='Deployment evidence evaluation failed.',
							recommendation='Inspect deployment evidence error logs.'
						)
				]
			)
	
	def to_dataframe( self ) -> pd.DataFrame:
		"""Evaluate deployment evidence and return a DataFrame.

		Purpose:
			Run all deployment evidence checks and convert the result into a DataFrame for
			Streamlit display, CSV export, and acceptance package creation.

		Returns:
			pd.DataFrame: Deployment evidence DataFrame.
		"""
		try:
			return self.evaluate( ).to_dataframe( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_dataframe( self ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def to_summary_dataframe( self ) -> pd.DataFrame:
		"""Evaluate deployment evidence and return a one-row summary DataFrame.

		Purpose:
			Run all deployment evidence checks and convert the aggregate summary into a one-row
			DataFrame for dashboard display and export.

		Returns:
			pd.DataFrame: Deployment evidence summary DataFrame.
		"""
		try:
			result = self.evaluate( )
			return pd.DataFrame( [ result.to_summary_record( ) ] )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_summary_dataframe( self ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def to_json( self ) -> str:
		"""Evaluate deployment evidence and return JSON.

		Purpose:
			Run all deployment evidence checks and serialize the result as formatted JSON.

		Returns:
			str: Formatted deployment evidence JSON.
		"""
		try:
			return self.evaluate( ).to_json( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_json( self ) -> str'
			Logger( ).write( error )
			return '{}'
	
	def to_markdown( self ) -> str:
		"""Evaluate deployment evidence and return Markdown.

		Purpose:
			Run all deployment evidence checks and render the result as stakeholder-readable
			Markdown.

		Returns:
			str: Deployment evidence Markdown report.
		"""
		try:
			return self.evaluate( ).to_markdown( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_markdown( self ) -> str'
			Logger( ).write( error )
			return '# Fiddy Deployment Evidence\n\nDeployment evidence could not be rendered.'
	
	def to_acceptance_evidence( self ) -> Dict[ str, object ]:
		"""Evaluate deployment evidence and return acceptance-checker flags.

		Purpose:
			Run all deployment evidence checks and convert them into supplemental evidence flags
			consumed by the acceptance checker.

		Returns:
			Dict[str, object]: Acceptance-checker evidence flags.
		"""
		try:
			return self.evaluate( ).to_acceptance_evidence( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_acceptance_evidence( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'REQUIRE_LOCAL_OCR': True,
					'ALLOW_EXTERNAL_ML_ENDPOINTS': False,
					'COLA_INTEGRATION_ENABLED': False,
					'LONG_TERM_STORAGE_DISABLED': True,
					'DEPLOYMENT_TARGET': 'local'
			}
