#!/usr/bin/env python
#
# Copyright (C) 2015  Ryan Roden-Corrent <ryan@rcorre.net>
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

import os
from ycmd import utils
from ycmd import responses
from ycmd.utils import ToUtf8IfNeeded
from ycmd.completers.completer import Completer
import logging

SERVER_NOT_FOUND_MSG = ( 'DCD server binary not found at {0}. ' +
                         'Did you compile it? You can do so by running ' +
                         '"./install.sh --d-completer".' )
MIN_LINES_IN_FILE_TO_PARSE = 5
INVALID_FILE_MESSAGE = 'File is invalid.'
FILE_TOO_SHORT_MESSAGE = (
  'File is less than {0} lines long; not parsing.'.format(
    MIN_LINES_IN_FILE_TO_PARSE ) )
NO_DIAGNOSTIC_MESSAGE = 'No diagnostic for current line!'
PATH_TO_DCD_SERVER_BINARY = os.path.join(
  os.path.abspath( os.path.dirname( __file__ ) ),
  '../../../third_party/dcd/bin/dcd-server' )
PATH_TO_DCD_CLIENT_BINARY = os.path.join(
  os.path.abspath( os.path.dirname( __file__ ) ),
  '../../../third_party/dcd/bin/dcd-client' )

class DCDCompleter( Completer ):
  """
  A Completer that uses DCD (D Completion Daemon):
  https://github.com/Hackerpilot/DCD
  """

  def __init__( self, user_options ):
    super( DCDCompleter, self ).__init__( user_options )
    self._logger = logging.getLogger( __name__ )
    self._dcd_port = None
    self._dcd_phandle = None
  # subcommand handling -----------------------------------------
  # pattern of handling subcommands borrowed from CsharpCompleter

  subcommands = {
    'StartServer': ( lambda self, request_data: self._StartServer(
        request_data ) ),
    'StopServer': ( lambda self, request_data: self._StopServer() ),
    'RestartServer': ( lambda self, request_data: self._RestartServer(
        request_data ) ),
    'ServerRunning': ( lambda self, request_data: self._ServerRunning() ),
  }

  def DefinedSubcommands( self ):
    return DCDCompleter.subcommands.keys()

  def OnUserCommand( self, arguments, request_data ):
    if not arguments:
      raise ValueError( self.UserCommandsHelpMessage() )

    command = arguments[ 0 ]
    if command in DCDCompleter.subcommands:
      command_lamba = DCDCompleter.subcommands[ command ]
      return command_lamba( self, request_data )
    else:
      raise ValueError( self.UserCommandsHelpMessage() )

  # end subcommand handling -------------------------------------

  def SupportedFiletypes( self ):
    """ Just d """
    return [ 'd' ]

  def ShouldUseNow( self, request_data ):
    # TODO: probably shouldn't use this
    return True

  def ComputeCandidatesInner( self, request_data ):
    return [ responses.BuildCompletionData(
                ToUtf8IfNeeded( completion.name ),
                ToUtf8IfNeeded( completion.description ),
                ToUtf8IfNeeded( completion.docstring ) )
             for completion in self._GetDCDCompletions() ]

  def _GetDCDCompletions( self ):
    return [ DCDCompletion("fooable", "desc", "doc") ]

  # subcommand definitions --------------------------------------
  def _StartServer( self, request_data ):
    """ Start the DCD server """
    self._logger.info( 'starting DCD server' )

    #Note: detection could throw an exception if an extra_conf_store needs to be confirmed
    #TODO: find dub.json. use dutyl?
    #path_to_solutionfile = solutiondetection.FindSolutionPath( request_data[ 'filepath' ] )
    path_to_dubfile = 'dub.json'

    #if not path_to_solutionfile:
    #  raise RuntimeError( 'Autodetection of solution file failed.\n' )
    #self._logger.info( u'Loading solution file {0}'.format( path_to_solutionfile ) )

    self._ChooseDCDPort()

    # we need to pass the command to Popen as a string since we're passing
    # shell=True (as recommended by Python's doc)
    command = ' '.join( [ PATH_TO_DCD_SERVER_BINARY,
                         '--port',
                         str( self._dcd_port ) ] )
    # TODO: use -I to pass include paths (fetched from dutyl?)

    filename_format = os.path.join( utils.PathToTempDir(),
                                   u'dcd_{port}_{dub}_{std}.log' )

    dubfile = os.path.basename( path_to_dubfile )
    self._filename_stdout = filename_format.format(
        port = self._dcd_port, dub = dubfile, std = 'stdout' )
    self._filename_stderr = filename_format.format(
        port = self._dcd_port, dub = dubfile, std = 'stderr' )

    with open( self._filename_stderr, 'w' ) as fstderr:
      with open( self._filename_stdout, 'w' ) as fstdout:
        # shell=True is needed for Windows so DCD does not spawn
        # in a new visible window
        self._dcd_phandle = utils.SafePopen(
            command, stdout = fstdout, stderr = fstderr, shell = True )

    self._dub_path = path_to_dubfile

    self._logger.info( 'DCD server started on port %d' % self._dcd_port)

  def _StopServer( self ):
    """ Stop the DCD server """
    self._logger.info( 'stopping DCD server' )
    self._ClientCommand("--shutdown")
    self._dcd_phandle.wait()
    self._dcd_port = None
    self._dcd_phandle = None
    if ( not self.user_options[ 'server_keep_logfiles' ] ):
      os.unlink( self._filename_stdout );
      os.unlink( self._filename_stderr );
    self._logger.info( 'DCD server stopped' )

  def _RestartServer ( self, request_data ):
    self._logger.info( 'Restarting DCD server' )
    """ Restarts the DCD server """
    if self._IsServerRunning():
      self._StopServer()
    return self._StartServer( request_data )

  def _ServerRunning ( self ):
    if self._IsServerRunning():
      return responses.BuildDisplayMessageResponse("DCD server is UP")
    return responses.BuildDisplayMessageResponse("DCD server is DOWN")

  # end subcommand definitions ----------------------------------

  # helper functions --------------------------------------------

  def _ChooseDCDPort( self ):
    self._dcd_port = int( self.user_options.get( 'dcd_server_port', 0 ) )
    if not self._dcd_port:
        self._dcd_port = utils.GetUnusedLocalhostPort()
    self._logger.info( u'using port {0}'.format( self._dcd_port ) )

  def _ClientCommand( self, args ):
    command = "{binpath} -p{port} {args}".format(
      binpath = PATH_TO_DCD_CLIENT_BINARY,
      port = self._dcd_port,
      args = args)
    self._logger.info('client command: ' + command)
    with open( self._filename_stderr, 'w' ) as fstderr:
      with open( self._filename_stdout, 'w' ) as fstdout:
        # shell=True is needed for Windows so DCD does not spawn
        # in a new visible window
        client_proc = utils.SafePopen(
            command, stdout = fstdout, stderr = fstderr, shell = True )
        return client_proc.wait()
    #self._logger.info('client command complete')

  def _IsServerRunning( self ):
    """ Check if our DCD server is running (up and serving)."""
    try:
      return (self._dcd_port is not None)# and
             #(self._ClientCommand("--query") == 0)
    except:
      return False

  # end helper functions ----------------------------------------

class DCDCompletion:
  """
  A completion provided by DCD
  """

  def __init__( self, name, description, docstring ):
    self.name = name
    self.description = description
    self.docstring = docstring
