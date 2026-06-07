'''
    ******************************************************************************************
      Assembly:                Fiddy
      Filename:                accessibility_checklist.py
      Author:                  Terry D. Eppler
      Created:                 06-06-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-06-2026
    ******************************************************************************************
    <copyright file="accessibility_checklist.py" company="Terry D. Eppler">

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
        Provides a reusable accessibility checklist model and evaluator for the Fiddy
        prototype.

        This module creates structured checklist items for validating high-contrast mode, large
        text mode, visible keyboard focus, keyboard navigation, keyboard activation, file upload
        reachability, result review, download reachability, and non-hover mismatch guidance.
        The checklist is intentionally designed for manual validation because keyboard
        navigation and focus order must be verified in the browser where Streamlit renders the
        final user interface.

        The module produces tabular, JSON, Markdown, and summary outputs that can be displayed
        in Streamlit, exported with the acceptance evidence package, or consumed by the
        acceptance checker.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field

import config as cfg
from booger import Error, Logger
from config import throw_if

CHECK_STATUS_PASS: str = 'Pass'
CHECK_STATUS_FAIL: str = 'Fail'
CHECK_STATUS_NOT_TESTED: str = 'Not Tested'
CHECK_STATUS_NOT_APPLICABLE: str = 'Not Applicable'

CHECK_CATEGORY_KEYBOARD: str = 'Keyboard Navigation'
CHECK_CATEGORY_VISUAL: str = 'Visual Accessibility'
CHECK_CATEGORY_WORKFLOW: str = 'Workflow Accessibility'
CHECK_CATEGORY_RESULTS: str = 'Results Accessibility'
CHECK_CATEGORY_DOWNLOADS: str = 'Download Accessibility'
CHECK_CATEGORY_FEEDBACK: str = 'Mismatch Feedback'
CHECK_CATEGORY_ACCEPTANCE: str = 'Acceptance Evidence'

ACCESSIBILITY_STATUS_MET: str = 'Met'
ACCESSIBILITY_STATUS_PARTIAL: str = 'Partially Met'
ACCESSIBILITY_STATUS_NOT_MET: str = 'Not Met'
ACCESSIBILITY_STATUS_NOT_EVALUATED: str = 'Not Evaluated'

class AccessibilityChecklistItem( BaseModel ):
	"""Represent one accessibility validation checklist item.

	Purpose:
		Store one browser-validation item used to confirm that Fiddy can be operated with
		keyboard and visual accessibility support. Each item includes a stable identifier,
		category, plain-language test name, test procedure, expected result, current status,
		tester notes, and evaluation timestamp.

	Attributes:
		item_id (str): Stable checklist item identifier.
		category (str): Accessibility category.
		name (str): Plain-language checklist item name.
		procedure (str): Manual test procedure.
		expected_result (str): Expected result for a passing test.
		status (str): Item status such as ``Pass``, ``Fail``, ``Not Tested``, or
			``Not Applicable``.
		notes (str): Optional tester notes.
		evaluated_on (str): UTC timestamp when the item status was last set.
	"""
	
	item_id: str = Field( default='' )
	category: str = Field( default='' )
	name: str = Field( default='' )
	procedure: str = Field( default='' )
	expected_result: str = Field( default='' )
	status: str = Field( default=CHECK_STATUS_NOT_TESTED )
	notes: str = Field( default='' )
	evaluated_on: str = Field(
		default_factory=lambda: datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
	)
	
	def mark_passed( self, notes: str = '' ) -> None:
		"""Mark the checklist item as passed.

		Purpose:
			Update the item status to ``Pass``, store optional tester notes, and refresh the
			evaluation timestamp.

		Args:
			notes (str): Optional tester notes.

		Returns:
			None.
		"""
		try:
			self.status = CHECK_STATUS_PASS
			self.notes = notes
			self.evaluated_on = datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'mark_passed( self, notes: str = "" ) -> None'
			Logger( ).write( error )
			return None
	
	def mark_failed( self, notes: str = '' ) -> None:
		"""Mark the checklist item as failed.

		Purpose:
			Update the item status to ``Fail``, store optional tester notes, and refresh the
			evaluation timestamp.

		Args:
			notes (str): Optional tester notes.

		Returns:
			None.
		"""
		try:
			self.status = CHECK_STATUS_FAIL
			self.notes = notes
			self.evaluated_on = datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'mark_failed( self, notes: str = "" ) -> None'
			Logger( ).write( error )
			return None
	
	def mark_not_tested( self, notes: str = '' ) -> None:
		"""Mark the checklist item as not tested.

		Purpose:
			Update the item status to ``Not Tested``, store optional tester notes, and refresh
			the evaluation timestamp.

		Args:
			notes (str): Optional tester notes.

		Returns:
			None.
		"""
		try:
			self.status = CHECK_STATUS_NOT_TESTED
			self.notes = notes
			self.evaluated_on = datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'mark_not_tested( self, notes: str = "" ) -> None'
			Logger( ).write( error )
			return None
	
	def mark_not_applicable( self, notes: str = '' ) -> None:
		"""Mark the checklist item as not applicable.

		Purpose:
			Update the item status to ``Not Applicable``, store optional tester notes, and
			refresh the evaluation timestamp.

		Args:
			notes (str): Optional tester notes.

		Returns:
			None.
		"""
		try:
			self.status = CHECK_STATUS_NOT_APPLICABLE
			self.notes = notes
			self.evaluated_on = datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'mark_not_applicable( self, notes: str = "" ) -> None'
			Logger( ).write( error )
			return None
	
	def update_status( self, status: str, notes: str = '' ) -> None:
		"""Update the checklist item using a supplied status value.

		Purpose:
			Apply one of the recognized checklist statuses to the item and refresh the evaluation
			timestamp. This supports UI-driven edits, imported checklist results, and test-harness
			status maps.

		Args:
			status (str): Status value to apply.
			notes (str): Optional tester notes.

		Returns:
			None.
		"""
		try:
			throw_if( 'status', status )
			
			if status == CHECK_STATUS_PASS:
				self.mark_passed( notes )
			elif status == CHECK_STATUS_FAIL:
				self.mark_failed( notes )
			elif status == CHECK_STATUS_NOT_APPLICABLE:
				self.mark_not_applicable( notes )
			elif status == CHECK_STATUS_NOT_TESTED:
				self.mark_not_tested( notes )
			else:
				raise ValueError( f'Unsupported accessibility status: {status}' )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'update_status( self, *args ) -> None'
			Logger( ).write( error )
			return None
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert the checklist item into a flat display/export record.

		Purpose:
			Return a dictionary suitable for Streamlit display, CSV export, JSON export,
			Markdown reporting, or test-result archiving.

		Returns:
			Dict[str, object]: Flat checklist item record.
		"""
		try:
			return {
					'Item ID': self.item_id,
					'Category': self.category,
					'Name': self.name,
					'Procedure': self.procedure,
					'Expected Result': self.expected_result,
					'Status': self.status,
					'Notes': self.notes,
					'Evaluated On': self.evaluated_on
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Item ID': self.item_id,
					'Category': self.category,
					'Name': self.name,
					'Procedure': '',
					'Expected Result': '',
					'Status': CHECK_STATUS_NOT_TESTED,
					'Notes': 'Checklist item could not be rendered.',
					'Evaluated On': ''
			}

class AccessibilityChecklistResult( BaseModel ):
	"""Represent the complete Fiddy accessibility checklist outcome.

	Purpose:
		Store all checklist items and calculated accessibility status values. The result reports
		whether high-contrast mode is available, whether large-text mode is available, whether
		keyboard validation is required, which items passed, which items failed, which items
		remain untested, and the overall accessibility status.

	Attributes:
		high_contrast_available (bool): Indicates whether high-contrast mode is configured.
		large_text_available (bool): Indicates whether large-text mode is configured.
		keyboard_check_required (bool): Indicates whether manual keyboard validation is required.
		items (List[AccessibilityChecklistItem]): Accessibility checklist items.
		passed_items (List[str]): Names of checklist items marked ``Pass``.
		failed_items (List[str]): Names of checklist items marked ``Fail``.
		untested_items (List[str]): Names of checklist items marked ``Not Tested``.
		not_applicable_items (List[str]): Names of checklist items marked ``Not Applicable``.
		status (str): Overall accessibility checklist status.
		message (str): Plain-language summary message.
		created_on (str): UTC timestamp when the result was created.
	"""
	
	high_contrast_available: bool = Field( default=False )
	large_text_available: bool = Field( default=False )
	keyboard_check_required: bool = Field( default=True )
	items: List[ AccessibilityChecklistItem ] = Field( default_factory=list )
	passed_items: List[ str ] = Field( default_factory=list )
	failed_items: List[ str ] = Field( default_factory=list )
	untested_items: List[ str ] = Field( default_factory=list )
	not_applicable_items: List[ str ] = Field( default_factory=list )
	status: str = Field( default=ACCESSIBILITY_STATUS_NOT_EVALUATED )
	message: str = Field( default='' )
	created_on: str = Field(
		default_factory=lambda: datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
	)
	
	def status_counts( self ) -> Dict[ str, int ]:
		"""Return counts of checklist item statuses.

		Purpose:
			Count checklist items by status for dashboard metrics, summary records, Markdown
			output, JSON output, and acceptance evidence.

		Returns:
			Dict[str, int]: Status counts keyed by checklist status text.
		"""
		try:
			counts = {
					CHECK_STATUS_PASS: 0,
					CHECK_STATUS_FAIL: 0,
					CHECK_STATUS_NOT_TESTED: 0,
					CHECK_STATUS_NOT_APPLICABLE: 0
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
					CHECK_STATUS_PASS: 0,
					CHECK_STATUS_FAIL: 0,
					CHECK_STATUS_NOT_TESTED: 0,
					CHECK_STATUS_NOT_APPLICABLE: 0
			}
	
	def refresh_status( self ) -> None:
		"""Recalculate derived accessibility status fields.

		Purpose:
			Rebuild passed, failed, untested, and not-applicable item lists, then calculate the
			overall accessibility status and message. High-contrast and large-text support are
			treated as required visual accessibility capabilities. Keyboard checks remain manual
			when configured as required.

		Returns:
			None.
		"""
		try:
			self.passed_items = [
					item.name
					for item in self.items
					if item.status == CHECK_STATUS_PASS
			]
			self.failed_items = [
					item.name
					for item in self.items
					if item.status == CHECK_STATUS_FAIL
			]
			self.untested_items = [
					item.name
					for item in self.items
					if item.status == CHECK_STATUS_NOT_TESTED
			]
			self.not_applicable_items = [
					item.name
					for item in self.items
					if item.status == CHECK_STATUS_NOT_APPLICABLE
			]
			
			if not self.items:
				self.status = ACCESSIBILITY_STATUS_NOT_EVALUATED
				self.message = 'No accessibility checklist items are available.'
			elif self.failed_items:
				self.status = ACCESSIBILITY_STATUS_NOT_MET
				self.message = (
						f'{len( self.failed_items )} accessibility checklist item(s) failed and '
						'require remediation before acceptance.'
				)
			elif self.untested_items and self.keyboard_check_required:
				self.status = ACCESSIBILITY_STATUS_PARTIAL
				self.message = (
						f'{len( self.untested_items )} accessibility checklist item(s) remain '
						'untested. Manual browser validation is required.'
				)
			elif not self.high_contrast_available or not self.large_text_available:
				self.status = ACCESSIBILITY_STATUS_PARTIAL
				self.message = (
						'Checklist items are complete, but high-contrast or large-text availability '
						'was not confirmed.'
				)
			else:
				self.status = ACCESSIBILITY_STATUS_MET
				self.message = 'All applicable accessibility checklist items passed.'
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'refresh_status( self ) -> None'
			Logger( ).write( error )
			self.status = ACCESSIBILITY_STATUS_NOT_EVALUATED
			self.message = 'Accessibility status could not be refreshed.'
	
	def to_records( self ) -> List[ Dict[ str, object ] ]:
		"""Convert checklist items into flat records.

		Purpose:
			Convert each accessibility checklist item into a dictionary suitable for DataFrame
			display, CSV export, JSON export, or Markdown reporting.

		Returns:
			List[Dict[str, object]]: Flat checklist item records.
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
		"""Convert checklist results into a pandas DataFrame.

		Purpose:
			Create a tabular representation of checklist items for Streamlit display, CSV export,
			or acceptance evidence.

		Returns:
			pd.DataFrame: Accessibility checklist DataFrame.
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
		"""Convert the checklist result into a one-row summary record.

		Purpose:
			Return high-level accessibility status, configuration flags, item counts, and message
			values for dashboards and acceptance reports.

		Returns:
			Dict[str, object]: Flat accessibility checklist summary record.
		"""
		try:
			counts = self.status_counts( )
			
			return {
					'Accessibility Status': self.status,
					'Accessibility Message': self.message,
					'High Contrast Available': self.high_contrast_available,
					'Large Text Available': self.large_text_available,
					'Keyboard Check Required': self.keyboard_check_required,
					'Passed Items': counts.get( CHECK_STATUS_PASS, 0 ),
					'Failed Items': counts.get( CHECK_STATUS_FAIL, 0 ),
					'Untested Items': counts.get( CHECK_STATUS_NOT_TESTED, 0 ),
					'Not Applicable Items': counts.get( CHECK_STATUS_NOT_APPLICABLE, 0 ),
					'Created On': self.created_on
			}
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_summary_record( self ) -> Dict[str, object]'
			Logger( ).write( error )
			return {
					'Accessibility Status': ACCESSIBILITY_STATUS_NOT_EVALUATED,
					'Accessibility Message': 'Accessibility summary could not be rendered.',
					'High Contrast Available': False,
					'Large Text Available': False,
					'Keyboard Check Required': True,
					'Passed Items': 0,
					'Failed Items': 0,
					'Untested Items': 0,
					'Not Applicable Items': 0,
					'Created On': ''
			}
	
	def to_json( self ) -> str:
		"""Serialize the accessibility result as formatted JSON.

		Purpose:
			Create a JSON representation of the accessibility checklist result containing the
			summary record and every checklist item. The output is suitable for evidence packages,
			test harnesses, and stakeholder records.

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
		"""Render the accessibility result as Markdown.

		Purpose:
			Create a stakeholder-readable Markdown report containing the overall accessibility
			status, summary metrics, and every checklist item with procedure, expected result,
			status, and tester notes.

		Returns:
			str: Markdown accessibility report. If rendering fails, returns a fallback report.
		"""
		try:
			summary = self.to_summary_record( )
			lines = [
					'# Fiddy Accessibility Checklist',
					'',
					f'Created On: {self.created_on}',
					f'Accessibility Status: {summary.get( "Accessibility Status", "" )}',
					f'Message: {summary.get( "Accessibility Message", "" )}',
					'',
					'## Summary',
					'',
					f'- High Contrast Available: {self.high_contrast_available}',
					f'- Large Text Available: {self.large_text_available}',
					f'- Keyboard Check Required: {self.keyboard_check_required}',
					f'- Passed Items: {summary.get( "Passed Items", 0 )}',
					f'- Failed Items: {summary.get( "Failed Items", 0 )}',
					f'- Untested Items: {summary.get( "Untested Items", 0 )}',
					f'- Not Applicable Items: {summary.get( "Not Applicable Items", 0 )}',
					'',
					'## Checklist Items',
					''
			]
			
			for item in self.items:
				lines.extend(
					[
							f'### {item.item_id} - {item.name}',
							'',
							f'- Category: {item.category}',
							f'- Status: {item.status}',
							f'- Procedure: {item.procedure}',
							f'- Expected Result: {item.expected_result}',
							f'- Notes: {item.notes}',
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
			return '# Fiddy Accessibility Checklist\n\nAccessibility report could not be rendered.'

class AccessibilityChecklist( ):
	"""Build and evaluate Fiddy's manual accessibility checklist.

	Purpose:
		Create the canonical checklist used to validate the Fiddy prototype in a browser. The
		checks are intentionally manual because Streamlit renders interactive controls in the
		browser, and focus order, keyboard activation, file upload reachability, download
		reachability, visible focus, and non-hover guidance must be observed in the actual UI.

	Attributes:
		_items (List[AccessibilityChecklistItem]): Canonical checklist items.
	"""
	
	_items: List[ AccessibilityChecklistItem ]
	
	def __init__( self ) -> None:
		"""Initialize the checklist with canonical accessibility items.

		Purpose:
			Build the default checklist items used for high-contrast, large-text, keyboard
			navigation, keyboard activation, workflow, result review, download validation, and
			non-hover mismatch guidance.

		Returns:
			None.
		"""
		self._items = self.create_default_items( )
	
	@property
	def items( self ) -> List[ AccessibilityChecklistItem ]:
		"""Return the checklist items.

		Purpose:
			Expose the current checklist item list to callers that need to display, update, or
			export manual validation records.

		Returns:
			List[AccessibilityChecklistItem]: Checklist items.
		"""
		return self._items
	
	def create_item( self, item_id: str, category: str, name: str, procedure: str,
			expected_result: str ) -> AccessibilityChecklistItem:
		"""Create one accessibility checklist item.

		Purpose:
			Centralize construction of checklist item records. Required values are validated
			before the item is created.

		Args:
			item_id (str): Stable checklist item identifier.
			category (str): Accessibility category.
			name (str): Plain-language checklist item name.
			procedure (str): Manual test procedure.
			expected_result (str): Expected passing result.

		Returns:
			AccessibilityChecklistItem: Checklist item.
		"""
		try:
			throw_if( 'item_id', item_id )
			throw_if( 'category', category )
			throw_if( 'name', name )
			throw_if( 'procedure', procedure )
			throw_if( 'expected_result', expected_result )
			
			return AccessibilityChecklistItem(
				item_id=item_id,
				category=category,
				name=name,
				procedure=procedure,
				expected_result=expected_result
			)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_item( self, *args ) -> AccessibilityChecklistItem'
			Logger( ).write( error )
			return AccessibilityChecklistItem(
				item_id=item_id or '',
				category=category or '',
				name=name or '',
				procedure=procedure or '',
				expected_result=expected_result or ''
			)
	
	def create_default_items( self ) -> List[ AccessibilityChecklistItem ]:
		"""Create the canonical Fiddy accessibility checklist.

		Purpose:
			Return checklist items that cover the stakeholder accessibility requirements and the
			specific UI evidence needed for Fiddy acceptance. The checklist includes high contrast,
			large text, visible focus, keyboard navigation, keyboard activation, file upload
			reachability, result review, download reachability, and mismatch explanations that do
			not depend on hover-only behavior.

		Returns:
			List[AccessibilityChecklistItem]: Canonical accessibility checklist items.
		"""
		try:
			return [
					self.create_item(
						item_id='A11Y-001',
						category=CHECK_CATEGORY_VISUAL,
						name='High Contrast Mode Available',
						procedure='Enable High Contrast in the sidebar and inspect the main workflow, buttons, upload controls, result tables, and download buttons.',
						expected_result='High Contrast mode increases contrast across controls, panels, text, buttons, and tables without hiding workflow content.'
					),
					self.create_item(
						item_id='A11Y-002',
						category=CHECK_CATEGORY_VISUAL,
						name='Large Text Mode Available',
						procedure='Enable Large Text in the sidebar and inspect headers, panels, input fields, buttons, tables, and guidance notes.',
						expected_result='Large Text mode increases readability without clipping labels, hiding controls, or breaking the upload-run-review workflow.'
					),
					self.create_item(
						item_id='A11Y-003',
						category=CHECK_CATEGORY_KEYBOARD,
						name='Visible Keyboard Focus',
						procedure='Use Tab and Shift+Tab through the app controls and observe visible focus indicators.',
						expected_result='Keyboard focus is visible on buttons, upload controls, input fields, selectors, expanders, and download controls.'
					),
					self.create_item(
						item_id='A11Y-004',
						category=CHECK_CATEGORY_KEYBOARD,
						name='Keyboard Navigation Order',
						procedure='Use only the keyboard to move from sidebar reviewer controls through upload controls, processing controls, results, and downloads.',
						expected_result='Focus order follows the visual workflow and does not trap the reviewer or skip required controls.'
					),
					self.create_item(
						item_id='A11Y-005',
						category=CHECK_CATEGORY_KEYBOARD,
						name='Keyboard Activation',
						procedure='Use Enter or Space to activate buttons, toggles, expanders, and download controls.',
						expected_result='All primary workflow controls can be activated without using a mouse.'
					),
					self.create_item(
						item_id='A11Y-006',
						category=CHECK_CATEGORY_WORKFLOW,
						name='File Upload Reachability',
						procedure='Reach the manifest upload and label-artwork upload controls using keyboard navigation.',
						expected_result='Upload controls are reachable, labeled, and usable in the rendered browser UI.'
					),
					self.create_item(
						item_id='A11Y-007',
						category=CHECK_CATEGORY_WORKFLOW,
						name='Simple Workflow Operable',
						procedure='Complete the Simple Mode upload-run-review path using the rendered controls.',
						expected_result='A reviewer can complete the core workflow without hunting through technical controls.'
					),
					self.create_item(
						item_id='A11Y-008',
						category=CHECK_CATEGORY_RESULTS,
						name='Results Review Reachability',
						procedure='After verification, use keyboard navigation to reach the dashboard, results viewer, comparison table, and acceptance evidence.',
						expected_result='Results are reachable and readable without requiring pointer-only interaction.'
					),
					self.create_item(
						item_id='A11Y-009',
						category=CHECK_CATEGORY_DOWNLOADS,
						name='Download Controls Reachable',
						procedure='Use keyboard navigation to reach and activate each enabled download button.',
						expected_result='Summary, comparison, detail, performance, acceptance, JSON, and Markdown downloads are keyboard reachable when enabled.'
					),
					self.create_item(
						item_id='A11Y-010',
						category=CHECK_CATEGORY_FEEDBACK,
						name='Mismatch Guidance Does Not Require Hover',
						procedure='Inspect mismatch, warning, fail, and review rows in the results and comparison outputs.',
						expected_result='Mismatch explanations and reviewer actions are visible as text or table content and do not depend only on hover tooltips.'
					),
					self.create_item(
						item_id='A11Y-011',
						category=CHECK_CATEGORY_FEEDBACK,
						name='Confidence and Severity Are Visible',
						procedure='Inspect result tables and summaries after verification.',
						expected_result='Confidence values and severity indicators are visible in text or table form.'
					),
					self.create_item(
						item_id='A11Y-012',
						category=CHECK_CATEGORY_ACCEPTANCE,
						name='Accessibility Evidence Exportable',
						procedure='Generate the accessibility checklist DataFrame, CSV, JSON, or Markdown output.',
						expected_result='Accessibility evidence can be exported and included in the stakeholder acceptance package.'
					)
			]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_default_items( self ) -> List[AccessibilityChecklistItem]'
			Logger( ).write( error )
			return [ ]
	
	def get_item( self, item_id: str ) -> Optional[ AccessibilityChecklistItem ]:
		"""Return one checklist item by identifier.

		Purpose:
			Find one checklist item using its stable item identifier. This supports UI forms,
			status imports, and targeted updates.

		Args:
			item_id (str): Checklist item identifier.

		Returns:
			Optional[AccessibilityChecklistItem]: Matching checklist item, or ``None`` when no
			item is found.
		"""
		try:
			throw_if( 'item_id', item_id )
			
			for item in self._items:
				if item.item_id == item_id:
					return item
			
			return None
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'get_item( self, item_id: str ) -> Optional[AccessibilityChecklistItem]'
			Logger( ).write( error )
			return None
	
	def update_item_status( self, item_id: str, status: str, notes: str = '' ) -> None:
		"""Update one checklist item status.

		Purpose:
			Apply a status and optional notes to one checklist item using its stable identifier.
			The method supports manual UI updates, imported checklist status maps, and acceptance
			test harness updates.

		Args:
			item_id (str): Checklist item identifier.
			status (str): New checklist status.
			notes (str): Optional tester notes.

		Returns:
			None.
		"""
		try:
			throw_if( 'item_id', item_id )
			throw_if( 'status', status )
			
			item = self.get_item( item_id )
			
			if not item:
				raise ValueError( f'Checklist item was not found: {item_id}' )
			
			item.update_status( status, notes )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'update_item_status( self, *args ) -> None'
			Logger( ).write( error )
			return None
	
	def apply_status_map( self, status_map: Dict[ str, str ],
			notes_map: Optional[ Dict[ str, str ] ] = None ) -> None:
		"""Apply a mapping of item statuses to the checklist.

		Purpose:
			Update multiple checklist items from dictionaries. This supports future UI forms, CSV
			imports, JSON imports, or tests that collect manual accessibility results outside the
			class.

		Args:
			status_map (Dict[str, str]): Mapping from item identifier to status.
			notes_map (Optional[Dict[str, str]]): Optional mapping from item identifier to notes.

		Returns:
			None.
		"""
		try:
			throw_if( 'status_map', status_map )
			
			notes = notes_map or { }
			
			for item_id, status in status_map.items( ):
				self.update_item_status(
					item_id=item_id,
					status=status,
					notes=notes.get( item_id, '' )
				)
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'apply_status_map( self, *args ) -> None'
			Logger( ).write( error )
			return None
	
	def mark_all_manual_checks_passed( self, notes: str = '' ) -> None:
		"""Mark every checklist item as passed.

		Purpose:
			Support acceptance testing after a reviewer has manually validated the rendered
			browser UI. This method should only be used when the reviewer or test harness has
			actually performed the browser checks and wants to record the completed evidence.

		Args:
			notes (str): Optional note applied to every checklist item.

		Returns:
			None.
		"""
		try:
			for item in self._items:
				item.mark_passed( notes )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'mark_all_manual_checks_passed( self, notes: str = "" ) -> None'
			Logger( ).write( error )
			return None
	
	def mark_all_manual_checks_not_tested( self, notes: str = '' ) -> None:
		"""Mark every checklist item as not tested.

		Purpose:
			Reset checklist evidence to a not-tested state while preserving the canonical item
			list. This is useful before rerunning accessibility validation or when clearing prior
			manual evidence.

		Args:
			notes (str): Optional note applied to every checklist item.

		Returns:
			None.
		"""
		try:
			for item in self._items:
				item.mark_not_tested( notes )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'mark_all_manual_checks_not_tested( self, notes: str = "" ) -> None'
			Logger( ).write( error )
			return None
	
	def evaluate( self ) -> AccessibilityChecklistResult:
		"""Evaluate the current checklist status.

		Purpose:
			Create an ``AccessibilityChecklistResult`` using current checklist items and
			configuration flags. The result recalculates passed, failed, not-tested, and
			not-applicable items before returning.

		Returns:
			AccessibilityChecklistResult: Current accessibility checklist result.
		"""
		try:
			result = AccessibilityChecklistResult(
				high_contrast_available=bool(
					getattr( cfg, 'DEFAULT_HIGH_CONTRAST_MODE', False )
					or getattr( cfg, 'HIGH_CONTRAST_AVAILABLE', True )
				),
				large_text_available=bool(
					getattr( cfg, 'DEFAULT_LARGE_TEXT_MODE', False )
					or getattr( cfg, 'LARGE_TEXT_AVAILABLE', True )
				),
				keyboard_check_required=bool(
					getattr( cfg, 'REQUIRE_KEYBOARD_ACCESSIBILITY_CHECK', True )
				),
				items=self._items
			)
			
			result.refresh_status( )
			return result
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'evaluate( self ) -> AccessibilityChecklistResult'
			Logger( ).write( error )
			return AccessibilityChecklistResult(
				high_contrast_available=False,
				large_text_available=False,
				keyboard_check_required=True,
				items=[ ],
				status=ACCESSIBILITY_STATUS_NOT_EVALUATED,
				message='Accessibility checklist could not be evaluated.'
			)
	
	def to_dataframe( self ) -> pd.DataFrame:
		"""Convert the current checklist into a pandas DataFrame.

		Purpose:
			Return checklist items as tabular records before or after manual validation. This is
			useful for Streamlit display, CSV export, and acceptance documentation.

		Returns:
			pd.DataFrame: Checklist item DataFrame.
		"""
		try:
			result = self.evaluate( )
			return result.to_dataframe( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_dataframe( self ) -> pd.DataFrame'
			Logger( ).write( error )
			return pd.DataFrame( )
	
	def to_summary_dataframe( self ) -> pd.DataFrame:
		"""Convert the current checklist summary into a one-row DataFrame.

		Purpose:
			Return high-level accessibility status as a DataFrame for dashboard display,
			acceptance reports, or CSV export.

		Returns:
			pd.DataFrame: One-row accessibility summary DataFrame.
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
		"""Serialize the current checklist result as formatted JSON.

		Purpose:
			Evaluate the current checklist and return its JSON representation for evidence
			packages, downloads, test harnesses, or stakeholder records.

		Returns:
			str: Formatted JSON string.
		"""
		try:
			result = self.evaluate( )
			return result.to_json( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_json( self ) -> str'
			Logger( ).write( error )
			return '{}'
	
	def to_markdown( self ) -> str:
		"""Render the current checklist result as Markdown.

		Purpose:
			Evaluate the current checklist and return a stakeholder-readable Markdown report.

		Returns:
			str: Markdown accessibility checklist report.
		"""
		try:
			result = self.evaluate( )
			return result.to_markdown( )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'to_markdown( self ) -> str'
			Logger( ).write( error )
			return '# Fiddy Accessibility Checklist\n\nAccessibility report could not be rendered.'