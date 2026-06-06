'''******************************************************************************************
      Assembly:                Fiddy
      Filename:                booger.py
      Author:                  Terry D. Eppler
      Created:                 06-05-2026

      Last Modified By:        Terry D. Eppler
      Last Modified On:        06-05-2026
    ******************************************************************************************
    <copyright file="booger.py" company="Terry D. Eppler">

         booger.py
         Copyright © 2026 Terry Eppler

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

     You can contact me at: terryeppler@gmail.com

    </copyright>
    <summary>
        Provides structured exception wrapping and local SQLite error logging for Fiddy.

        This module defines the Error wrapper used by guarded execution paths and the Logger
        class used to persist exception metadata to the configured local error database and
        table. It also provides a convenience function for wrapping and writing exceptions in
        one call.
    </summary>
    ******************************************************************************************
'''
from __future__ import annotations

import re
import sqlite3
import traceback
from pathlib import Path
from sys import exc_info
from typing import List, Optional

import config as cfg

class Error( Exception ):
	"""Wrap a Python exception with structured metadata for logging.

	The ``Error`` class extends ``Exception`` and stores the original exception together with
	context fields used by Fiddy logging and diagnostics. The wrapper captures the source
	exception message, exception type, formatted traceback, component or class cause, module
	name, method or function signature, and optional heading.

	The object is intentionally lightweight. Callers generally create an ``Error`` inside an
	``except`` block, assign stable metadata fields such as ``cause``, ``module``, and
	``method``, and then pass the object to ``Logger.write`` for local persistence.

	Attributes:
		error (Optional[Exception]): Source exception being wrapped.
		heading (Optional[str]): Optional user-facing heading or category.
		cause (Optional[str]): Component, class, or module purpose associated with the failure.
		method (Optional[str]): Stable method or function signature associated with the failure.
		module (Optional[str]): Module name associated with the failure.
		type (Optional[type]): Exception type captured from ``sys.exc_info``.
		trace (Optional[str]): Formatted traceback captured at wrapper creation time.
		info (Optional[str]): Combined exception type and traceback information.
		message (Optional[str]): String representation of the source exception.
	"""
	
	error: Optional[ Exception ]
	heading: Optional[ str ]
	cause: Optional[ str ]
	method: Optional[ str ]
	module: Optional[ str ]
	type: Optional[ type ]
	trace: Optional[ str ]
	info: Optional[ str ]
	message: Optional[ str ]
	
	def __init__( self, error: Exception, heading: str = None, cause: str = None,
			method: str = None, module: str = None ) -> None:
		"""Initialize an error wrapper from a caught exception.

		The constructor stores the original exception and optional context values, initializes
		the base ``Exception`` with the exception message, captures the current exception type
		from ``exc_info``, captures the formatted traceback, and builds a combined information
		string suitable for database logging.

		Args:
			error (Exception): Source exception being wrapped.
			heading (str): Optional user-facing heading.
			cause (str): Optional component, class, or module purpose that caused the error.
			method (str): Optional stable method or function signature where the error occurred.
			module (str): Optional module where the error occurred.

		Returns:
			None.
		"""
		super( ).__init__( str( error ) if error else '' )
		
		self.error = error
		self.heading = heading
		self.cause = cause
		self.method = method
		self.module = module
		self.type = exc_info( )[ 0 ]
		self.message = str( error ) if error else ''
		self.trace = traceback.format_exc( )
		self.info = f'{str( self.type )}: \r\n \r\n{self.trace}'
	
	def __str__( self ) -> str:
		"""Return a string representation of the wrapped error.

		The information string is preferred because it includes the captured exception type and
		traceback. When that value is unavailable, the source exception message is returned. If
		neither value is available, an empty string is returned.

		Returns:
			str: Error information string.
		"""
		return self.info or self.message or ''
	
	def __dir__( self ) -> List[ str ]:
		"""Return public member names used by callers and display surfaces.

		The returned list intentionally exposes the primary fields that are useful for logging,
		diagnostics, and reviewer-safe display. It omits implementation details and inherited
		exception internals.

		Returns:
			List[str]: Public error member names.
		"""
		return [
				'message',
				'cause',
				'error',
				'method',
				'module',
				'trace',
				'info'
		]

class Logger( ):
	"""Persist ``Error`` objects to the configured local SQLite database.

	The ``Logger`` class resolves the configured log database path and table name, creates the
	database table when needed, truncates values to fit the configured schema, and writes one
	row per error. The logger is intentionally defensive: logger failures return conservative
	fallback values rather than raising additional exceptions into application workflows.

	The class reads ``cfg.LOG_PATH`` for the database location and ``cfg.LOG_FILE`` for the table
	name. Relative database paths are resolved beneath ``cfg.ROOT_DIR`` when available through
	the uploaded configuration module.

	Attributes:
		path (Path): Resolved SQLite database path.
		table_name (str): Safe SQLite table name used for inserts.
	"""
	path: Path
	table_name: str
	
	def __init__( self ) -> None:
		"""Initialize the logger from configured database and table settings.

		The constructor resolves the SQLite database path through ``get_database_path`` and the
		table name through ``get_table_name``. No database connection is opened until
		``ensure_database`` or ``write`` is called.

		Returns:
			None.
		"""
		self.path = self.get_database_path( )
		self.table_name = self.get_table_name( )
	
	def get_database_path( self ) -> Path:
		"""Return the configured SQLite database path.

		This method reads ``cfg.LOG_PATH`` and resolves it to an absolute ``Path``. Relative log
		paths are resolved under ``cfg.ROOT_DIR``. If path resolution fails, the original fallback
		path ``logging/Exceptions.db`` is resolved relative to the current working directory.

		Returns:
			Path: Resolved SQLite database path.
		"""
		try:
			value = getattr( cfg, 'LOG_PATH', 'logging/Exceptions.db' )
			path = Path( value )
			if not path.is_absolute( ):
				path = cfg.ROOT_DIR / path
			
			return path.resolve( )
		except Exception:
			return Path( 'logging/Exceptions.db' ).resolve( )
	
	def get_table_name( self ) -> str:
		"""Return a safe SQLite table name.

		This method reads ``cfg.LOG_FILE`` and accepts it only when it matches a conservative
		SQLite identifier pattern beginning with a letter or underscore and containing only
		letters, digits, and underscores. Unsafe or unavailable values fall back to ``Errors``.

		Returns:
			str: Safe SQLite table name.
		"""
		try:
			value = str( getattr( cfg, 'LOG_FILE', 'Errors' ) ).strip( )
			
			if re.fullmatch( r'[A-Za-z_][A-Za-z0-9_]*', value ):
				return value
			
			return 'Errors'
		except Exception:
			return 'Errors'
	
	def truncate( self, value: object, length: int ) -> str:
		"""Convert a value to text and truncate it to a maximum length.

		This helper standardizes values before database insertion. ``None`` values become empty
		strings, all other values are converted to text, and the text is sliced to the requested
		length so it fits the configured logging schema.

		Args:
			value (object): Source value to convert and truncate.
			length (int): Maximum string length.

		Returns:
			str: Truncated string, or an empty string when conversion fails.
		"""
		try:
			if value is None:
				return ''
			
			text = str( value )
			return text[ :length ]
		except Exception:
			return ''
	
	def ensure_database( self ) -> None:
		"""Create the log directory and configured error table when needed.

		This method creates the parent directory for the configured SQLite database path and then
		creates the configured table if it does not already exist. The table stores cause,
		module, method, message, info, and trace values, with an autoincrementing primary key.

		The method is defensive by design. If database creation fails, the failure is swallowed
		so application error handling does not raise secondary logger exceptions.

		Returns:
			None.
		"""
		try:
			self.path.parent.mkdir( parents=True, exist_ok=True )
			sql = f'''
			CREATE TABLE IF NOT EXISTS "{self.table_name}" (
				"ID" INTEGER NOT NULL UNIQUE,
				"cause" TEXT(80),
				"module" TEXT(80),
				"method" TEXT(80),
				"message" TEXT(80),
				"info" TEXT(255),
				"trace" TEXT(255),
				PRIMARY KEY("ID" AUTOINCREMENT)
			)
			'''
			
			with sqlite3.connect( self.path ) as connection:
				connection.execute( sql )
				connection.commit( )
		except Exception:
			return None
	
	def write( self, error: Error ) -> int:
		"""Write one ``Error`` object to the configured SQLite error table.

		This method ensures the database exists, builds a parameterized insert statement, truncates
		error fields to the configured schema lengths, writes the row, commits the transaction,
		and returns the inserted row identifier. The table name is quoted and validated by
		``get_table_name`` to reduce unsafe identifier risk.

		Args:
			error (Error): Error object to persist.

		Returns:
			int: Inserted row identifier, or ``0`` when the error is missing or logging fails.
		"""
		try:
			if not error:
				return 0
			self.ensure_database( )
			sql = f'''
			INSERT INTO "{self.table_name}"
			(
				"cause",
				"module",
				"method",
				"message",
				"info",
				"trace"
			)
			VALUES
			(
				?,
				?,
				?,
				?,
				?,
				?
			)
			'''
			
			values = (self.truncate( error.cause, 80 ),
			          self.truncate( error.module, 80 ),
			          self.truncate( error.method, 80 ),
			          self.truncate( error.message, 80 ),
			          self.truncate( error.info, 255 ),
			          self.truncate( error.trace, 255 ))
			
			with sqlite3.connect( self.path ) as connection:
				cursor = connection.execute( sql, values )
				connection.commit( )
				return int( cursor.lastrowid or 0 )
		except Exception:
			return 0

def log_error( error: Exception, heading: str = None, cause: str = None,
		method: str = None, module: str = None ) -> Error:
	"""Wrap and log an exception using the configured Fiddy error database.

	This function is a convenience wrapper for callers that want to create an ``Error`` object
	and persist it in one step. It preserves the wrapped error object as the return value so
	callers can continue to inspect or display the structured metadata after logging.

	Args:
		error (Exception): Source exception being wrapped and logged.
		heading (str): Optional user-facing heading.
		cause (str): Optional component, class, or module purpose that caused the error.
		method (str): Optional stable method or function signature where the error occurred.
		module (str): Optional module where the error occurred.

	Returns:
		Error: Wrapped error object.
	"""
	exception = Error( error=error, heading=heading, cause=cause,
		method=method, module=module )
	
	Logger( ).write( exception )
	return exception