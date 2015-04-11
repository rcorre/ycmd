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

from ycmd.utils import ToUtf8IfNeeded
from ycmd.completers.completer import Completer
from ycmd import responses

class DCDCompleter( Completer ):
  """
  A Completer that uses DCD (D Completion Daemon):
  https://github.com/Hackerpilot/DCD
  """

  def __init__( self, user_options ):
    super( DCDCompleter, self ).__init__( user_options )


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

class DCDCompletion:
  def __init__( self, name, description, docstring ):
    self.name = name
    self.description = description
    self.docstring = docstring
