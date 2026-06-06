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
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd
from pydantic import BaseModel, Field

import config as cfg
from booger import Error, Logger
from config import throw_if

# ==========================================================================================
# Accessibility Constants
# ==========================================================================================

CHECK_STATUS_PASS: str = 'Pass'
CHECK_STATUS_FAIL: str = 'Fail'
CHECK_STATUS_NOT_TESTED: str = 'Not Tested'
CHECK_STATUS_NOT_APPLICABLE: str = 'Not Applicable'

CHECK_CATEGORY_KEYBOARD: str = 'Keyboard Navigation'
CHECK_CATEGORY_VISUAL: str = 'Visual Accessibility'
CHECK_CATEGORY_WORKFLOW: str = 'Workflow Accessibility'
CHECK_CATEGORY_RESULTS: str = 'Results Accessibility'
CHECK_CATEGORY_DOWNLOADS: str = 'Download Accessibility'

ACCESSIBILITY_STATUS_MET: str = 'Met'
ACCESSIBILITY_STATUS_PARTIAL: str = 'Partially Met'
ACCESSIBILITY_STATUS_NOT_MET: str = 'Not Met'
ACCESSIBILITY_STATUS_NOT_EVALUATED: str = 'Not Evaluated'

# ==========================================================================================
# Accessibility Models
# ==========================================================================================

class AccessibilityChecklistItem( BaseModel ):
	"""Represent one accessibility validation checklist item.

	The ``AccessibilityChecklistItem`` model stores one browser-validation item used to confirm
	that Fiddy can be operated with keyboard and visual accessibility support. Each item includes
	a stable identifier, category, plain-language test name, procedure, expected result, current
	status, tester notes, and evaluation timestamp.

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
		default_factory=lambda: datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' ) )
	
	def mark_passed( self, notes: str = '' ) -> None:
		"""Mark the checklist item as passed.

		Purpose:
			Update the item status to ``Pass``, store optional tester notes, and refresh the
			evaluation timestamp.

		Parameters:
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

		Parameters:
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
	
	def mark_not_applicable( self, notes: str = '' ) -> None:
		"""Mark the checklist item as not applicable.

		Purpose:
			Update the item status to ``Not Applicable``, store optional tester notes, and refresh
			the evaluation timestamp.

		Parameters:
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
	
	def to_record( self ) -> Dict[ str, object ]:
		"""Convert the checklist item into a flat display/export record.

		Purpose:
			Return a dictionary suitable for Streamlit display, CSV export, JSON export, Markdown
			reporting, or test-result archiving.

		Parameters:
			None.

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

	The ``AccessibilityChecklistResult`` model stores all checklist items and calculated
	accessibility status values. It reports whether high-contrast mode is available, whether
	large-text mode is available, whether keyboard navigation checks are required, which items
	passed, which items failed, which items remain untested, and the overall status.

	Attributes:
		high_contrast_available (bool): Indicates whether high-contrast mode is configured.
		large_text_available (bool): Indicates whether large-text mode is configured.
		keyboard_check_required (bool): Indicates whether manual keyboard validation is required.
		items (List[AccessibilityChecklistItem]): Accessibility checklist items.
		passed_items (List[str]): Names of checklist items marked ``Pass``.
		failed_items (List[str]): Names of checklist items marked ``Fail``.
		untested_items (List[str]): Names of checklist items marked ``Not Tested``.
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
	status: str = Field( default=ACCESSIBILITY_STATUS_NOT_EVALUATED )
	message: str = Field( default='' )
	created_on: str = Field(
		default_factory=lambda: datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' ) )
	
	def refresh_status( self ) -> None:
		"""Refresh item lists and overall accessibility status.

		Purpose:
			Recalculate passed, failed, and untested item lists from the current checklist items.
			The overall status is ``Met`` when every applicable item passes, ``Not Met`` when one or
			more items fail, ``Partially Met`` when some items pass but others remain untested, and
			``Not Evaluated`` when no applicable item has been tested.

		Parameters:
			None.

		Returns:
			None.
		"""
		try:
			applicable_items = [
					item
					for item in self.items
					if item.status != CHECK_STATUS_NOT_APPLICABLE
			]
			
			self.passed_items = [
					item.name
					for item in applicable_items
					if item.status == CHECK_STATUS_PASS
			]
			
			self.failed_items = [
					item.name
					for item in applicable_items
					if item.status == CHECK_STATUS_FAIL
			]
			
			self.untested_items = [
					item.name
					for item in applicable_items
					if item.status == CHECK_STATUS_NOT_TESTED
			]
			
			if not applicable_items:
				self.status = ACCESSIBILITY_STATUS_NOT_EVALUATED
				self.message = 'No applicable accessibility checklist items were available.'
			elif self.failed_items:
				self.status = ACCESSIBILITY_STATUS_NOT_MET
				self.message = (
						f'{len( self.failed_items )} accessibility item(s) failed validation.'
				)
			elif len( self.passed_items ) == len( applicable_items ):
				self.status = ACCESSIBILITY_STATUS_MET
				self.message = 'All applicable accessibility checklist items passed validation.'
			elif self.passed_items:
				self.status = ACCESSIBILITY_STATUS_PARTIAL
				self.message = (
						f'{len( self.passed_items )} item(s) passed and '
						f'{len( self.untested_items )} item(s) remain untested.'
				)
			else:
				self.status = ACCESSIBILITY_STATUS_NOT_EVALUATED
				self.message = 'Accessibility checklist has not been manually tested.'
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'refresh_status( self ) -> None'
			Logger( ).write( error )
			self.status = ACCESSIBILITY_STATUS_NOT_EVALUATED
			self.message = 'Accessibility checklist status could not be calculated.'
	
	def status_counts( self ) -> Dict[ str, int ]:
		"""Return counts of checklist item statuses.

		Purpose:
			Count checklist items by status for dashboards, summaries, and exports.

		Parameters:
			None.

		Returns:
			Dict[str, int]: Counts keyed by checklist status value.
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
	
	def to_records( self ) -> List[ Dict[ str, object ] ]:
		"""Convert all checklist items into flat records.

		Purpose:
			Return one dictionary per checklist item for display and export.

		Parameters:
			None.

		Returns:
			List[Dict[str, object]]: Flat checklist records.
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
		"""Convert the checklist result into a pandas DataFrame.

		Purpose:
			Create a tabular representation of checklist items for Streamlit display, CSV export,
			or acceptance evidence.

		Parameters:
			None.

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

		Parameters:
			None.

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

# ==========================================================================================
# Accessibility Checklist Builder
# ==========================================================================================

class AccessibilityChecklist( ):
	"""Build and evaluate Fiddy's manual accessibility checklist.

	The ``AccessibilityChecklist`` class creates the canonical checklist used to validate the
	Fiddy prototype in a browser. The checks are intentionally manual because Streamlit renders
	interactive controls in the browser, and focus order, keyboard activation, and visible focus
	must be observed in the actual UI.

	Attributes:
		_items (List[AccessibilityChecklistItem]): Canonical checklist items.
	"""
	
	_items: List[ AccessibilityChecklistItem ]
	
	def __init__( self ) -> None:
		"""Initialize the checklist with canonical accessibility items.

		Purpose:
			Build the default checklist items used for high-contrast, large-text, keyboard
			navigation, workflow, result-review, and download validation.

		Parameters:
			None.

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

		Parameters:
			None.

		Returns:
			List[AccessibilityChecklistItem]: Checklist items.
		"""
		return self._items
	
	def create_item( self, item_id: str, category: str, name: str, procedure: str,
			expected_result: str ) -> AccessibilityChecklistItem:
		"""Create one accessibility checklist item.

		Purpose:
			Centralize construction of checklist item records. Required values are validated before
			the item is created.

		Parameters:
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
			error.method = 'create_item( self, item_id: str, category: str, name: str, procedure: str, expected_result: str ) -> AccessibilityChecklistItem'
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
			Return the standard set of manual browser checks needed to support the stakeholder
			requirement for high-contrast mode, large text, and keyboard navigation. The checklist
			also verifies that reviewers are not forced to rely on mouse-only hover behavior.

		Parameters:
			None.

		Returns:
			List[AccessibilityChecklistItem]: Canonical checklist items.
		"""
		try:
			return [
					self.create_item(
						'A11Y-001',
						CHECK_CATEGORY_VISUAL,
						'High Contrast Mode Available',
						'Open the sidebar, enable High Contrast, and inspect upload controls, buttons, tables, and result panels.',
						'Controls and text remain readable with strong contrast.'
					),
					self.create_item(
						'A11Y-002',
						CHECK_CATEGORY_VISUAL,
						'Large Text Mode Available',
						'Open the sidebar, enable Large Text, and inspect upload controls, buttons, tables, result panels, and downloads.',
						'Text and controls are larger without hiding required workflow controls.'
					),
					self.create_item(
						'A11Y-003',
						CHECK_CATEGORY_KEYBOARD,
						'Keyboard Focus Visible',
						'Press Tab through the interface and watch the active control.',
						'A visible focus outline appears on active controls.'
					),
					self.create_item(
						'A11Y-004',
						CHECK_CATEGORY_KEYBOARD,
						'Upload Controls Reachable by Keyboard',
						'Press Tab until the manifest and artwork upload controls receive focus.',
						'Both upload controls can be reached without a mouse.'
					),
					self.create_item(
						'A11Y-005',
						CHECK_CATEGORY_KEYBOARD,
						'Run Verification Button Reachable by Keyboard',
						'Press Tab until Run Verification receives focus.',
						'Run Verification can be reached without a mouse.'
					),
					self.create_item(
						'A11Y-006',
						CHECK_CATEGORY_KEYBOARD,
						'Run Verification Button Activates by Keyboard',
						'With Run Verification focused and valid inputs loaded, press Enter or Space.',
						'Verification starts without requiring mouse click.'
					),
					self.create_item(
						'A11Y-007',
						CHECK_CATEGORY_KEYBOARD,
						'Backward Keyboard Navigation Works',
						'Press Shift + Tab from the Run Verification area.',
						'Focus moves backward through prior controls.'
					),
					self.create_item(
						'A11Y-008',
						CHECK_CATEGORY_WORKFLOW,
						'Simple Mode Uses Short Workflow',
						'Enable Simple Mode and complete a review from upload to results.',
						'The reviewer can complete the workflow as upload, run, review/download.'
					),
					self.create_item(
						'A11Y-009',
						CHECK_CATEGORY_WORKFLOW,
						'Simple Mode Hides Technical Controls',
						'Enable Simple Mode and inspect the processing area.',
						'Worker count and SLA tuning controls are not visible.'
					),
					self.create_item(
						'A11Y-010',
						CHECK_CATEGORY_RESULTS,
						'Result Selector Reachable by Keyboard',
						'After verification, press Tab until the flagged-label selector receives focus.',
						'The selected result can be changed without a mouse.'
					),
					self.create_item(
						'A11Y-011',
						CHECK_CATEGORY_RESULTS,
						'Mismatch Guidance Does Not Require Hover',
						'Inspect comparison results using keyboard navigation only.',
						'Mismatch explanation and reviewer action text are visible without mouse-only hover.'
					),
					self.create_item(
						'A11Y-012',
						CHECK_CATEGORY_RESULTS,
						'Comparison Table Readable',
						'Inspect the side-by-side comparison table in normal, high-contrast, and large-text modes.',
						'Application value, extracted value, status, severity, confidence, explanation, and reviewer action remain readable.'
					),
					self.create_item(
						'A11Y-013',
						CHECK_CATEGORY_DOWNLOADS,
						'Download Buttons Reachable by Keyboard',
						'After verification, press Tab until each download button receives focus.',
						'Summary, comparison, detail, performance, JSON, and Markdown download controls are reachable without a mouse.'
					),
					self.create_item(
						'A11Y-014',
						CHECK_CATEGORY_DOWNLOADS,
						'Download Buttons Activate by Keyboard',
						'With a download button focused, press Enter or Space.',
						'The browser starts the download action without requiring a mouse.'
					)
			]
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'create_default_items( self ) -> List[AccessibilityChecklistItem]'
			Logger( ).write( error )
			return [ ]
	
	def update_item_status( self, item_id: str, status: str, notes: str = '' ) -> None:
		"""Update one checklist item status.

		Purpose:
			Find an item by identifier and update its status and notes. Accepted status values are
			``Pass``, ``Fail``, ``Not Tested``, and ``Not Applicable``.

		Parameters:
			item_id (str): Checklist item identifier.
			status (str): New item status.
			notes (str): Optional tester notes.

		Returns:
			None.
		"""
		try:
			throw_if( 'item_id', item_id )
			throw_if( 'status', status )
			
			valid_statuses = {
					CHECK_STATUS_PASS,
					CHECK_STATUS_FAIL,
					CHECK_STATUS_NOT_TESTED,
					CHECK_STATUS_NOT_APPLICABLE
			}
			
			if status not in valid_statuses:
				raise ValueError( f'Invalid checklist status: {status}' )
			
			for item in self._items:
				if item.item_id == item_id:
					item.status = status
					item.notes = notes
					item.evaluated_on = datetime.utcnow( ).strftime( '%Y-%m-%d %H:%M:%S' )
					return None
			
			raise ValueError( f'Checklist item was not found: {item_id}' )
		except Exception as e:
			error = Error( e )
			error.cause = self.__class__.__name__
			error.module = __name__
			error.method = 'update_item_status( self, item_id: str, status: str, notes: str = "" ) -> None'
			Logger( ).write( error )
			return None
	
	def apply_status_map( self, status_map: Dict[ str, str ],
			notes_map: Dict[ str, str ] = None ) -> None:
		"""Apply a mapping of item statuses to the checklist.

		Purpose:
			Update multiple checklist items from dictionaries. This supports future UI forms, CSV
			imports, JSON imports, or tests that collect manual accessibility results outside the
			class.

		Parameters:
			status_map (Dict[str, str]): Mapping from item identifier to status.
			notes_map (Dict[str, str]): Optional mapping from item identifier to notes.

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
	
	def evaluate( self ) -> AccessibilityChecklistResult:
		"""Evaluate the current checklist status.

		Purpose:
			Create an ``AccessibilityChecklistResult`` using current checklist items and
			configuration flags. The result recalculates passed, failed, and untested items before
			returning.

		Parameters:
			None.

		Returns:
			AccessibilityChecklistResult: Current accessibility checklist result.
		"""
		try:
			result = AccessibilityChecklistResult(
				high_contrast_available=True,
				large_text_available=True,
				keyboard_check_required=bool(
					getattr( cfg, 'REQUIRE_KEYBOARD_ACCESSIBILITY_CHECK', True ) ),
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
			useful for display, export, and acceptance documentation.

		Parameters:
			None.

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