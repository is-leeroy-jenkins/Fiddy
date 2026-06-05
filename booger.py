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
        booger.py
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

# ==========================================================================================
# Error Wrapper
# ==========================================================================================

class Error( Exception ):
	"""
		Purpose:
		--------
		Wrap a Python exception with structured metadata used for display and persistent logging.
	
		Parameters:
		-----------
		error (Exception): Source exception being wrapped.
		heading (str): Optional user-facing heading.
		cause (str): Optional component or class that caused the error.
		method (str): Optional method or function name where the error occurred.
		module (str): Optional module where the error occurred.
	
		Returns:
		--------
		None
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
		"""
		
			Purpose:
			--------
			Initialize an Error wrapper from a caught exception and optional execution context.
	
			Parameters:
			-----------
			error (Exception): Source exception being wrapped.
			heading (str): Optional user-facing heading.
			cause (str): Optional component or class that caused the error.
			method (str): Optional method or function name where the error occurred.
			module (str): Optional module where the error occurred.
	
			Returns:
			--------
			None
			
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
		"""
			Purpose:
			--------
			Return a string representation of the wrapped error.
	
			Parameters:
			-----------
			None
	
			Returns:
			--------
			str: Error information string.
		"""
		return self.info or self.message or ''
	
	def __dir__( self ) -> List[ str ]:
		"""
			
			Purpose:
			--------
			Return public member names used by callers and display surfaces.
	
			Parameters:
			-----------
			None
	
			Returns:
			--------
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
	"""
	
		Purpose:
		--------
		Log Error objects to the configured local SQLite database and configured error table.
	
		Parameters:
		-----------
		None
	
		Returns:
		--------
		None
		
	"""
	path: Path
	table_name: str
	
	def __init__( self ) -> None:
		"""
		
			Purpose:
			--------
			Initialize the logger from cfg.LOG_PATH and cfg.LOG_FILE.
	
			Parameters:
			-----------
			None
	
			Returns:
			--------
			None
			
		"""
		self.path = self.get_database_path( )
		self.table_name = self.get_table_name( )
	
	def get_database_path( self ) -> Path:
		"""
		
			Purpose:
			--------
			Return the SQLite database path configured by cfg.LOG_PATH.
	
			Parameters:
			-----------
			None
	
			Returns:
			--------
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
		"""
		
			Purpose:
			--------
			Return a safe SQLite table name configured by cfg.LOG_FILE.
	
			Parameters:
			-----------
			None
	
			Returns:
			--------
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
		"""
		
			Purpose:
			--------
			Convert a value to text and truncate it to the configured database field length.
	
			Parameters:
			-----------
			value (object): Source value.
			length (int): Maximum string length.
	
			Returns:
			--------
			str: Truncated string.
			
		"""
		try:
			if value is None:
				return ''
			
			text = str( value )
			return text[ :length ]
		except Exception:
			return ''
	
	def ensure_database( self ) -> None:
		"""
		
			Purpose:
			--------
			Create the log database directory and configured error table when they do not exist.
	
			Parameters:
			-----------
			None
	
			Returns:
			--------
			None
			
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
		"""
		
			Purpose:
			--------
			Write one Error object to the configured SQLite error table.
	
			Parameters:
			-----------
			error (Error): Error object to persist.
	
			Returns:
			--------
			int: Inserted row ID, or 0 when logging fails.
			
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
			
			values = ( self.truncate( error.cause, 80 ),
					self.truncate( error.module, 80 ),
					self.truncate( error.method, 80 ),
					self.truncate( error.message, 80 ),
					self.truncate( error.info, 255 ),
					self.truncate( error.trace, 255 ) )
			
			with sqlite3.connect( self.path ) as connection:
				cursor = connection.execute( sql, values )
				connection.commit( )
				return int( cursor.lastrowid or 0 )
		except Exception:
			return 0

def log_error( error: Exception, heading: str = None, cause: str = None,
		method: str = None, module: str = None ) -> Error:
	"""
		Purpose:
		--------
		Wrap and log an exception using the configured Fiddy error database.
	
		Parameters:
		-----------
		error (Exception): Source exception being wrapped and logged.
		heading (str): Optional user-facing heading.
		cause (str): Optional component or class that caused the error.
		method (str): Optional method or function name where the error occurred.
		module (str): Optional module where the error occurred.
	
		Returns:
		--------
		Error: Wrapped error object.
	"""
	exception = Error( error=error, heading=heading, cause=cause,
		method=method, module=module )
	
	Logger( ).write( exception )
	return exception