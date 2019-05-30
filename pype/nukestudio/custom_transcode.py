# Example of a custom transcoder

import sys
import os.path
import tempfile
import re

import hiero.core
import hiero.core.nuke as nuke

from hiero.exporters import FnTranscodeExporter, FnTranscodeExporterUI

import wave
import shutil


class CustomTranscode(FnTranscodeExporter.TranscodeExporter):
  def __init__(self, initDict):
    """Initialize"""
    FnTranscodeExporter.TranscodeExporter.__init__( self, initDict )
        
  def startTask(self):   
    # Call parent startTask
    FnTranscodeExporter.TranscodeExporter.startTask(self)
    
    # This only works if the export item is a Sequence
    if isinstance(self._item, hiero.core.Sequence):
      
      sequence = self._item
      
      isQuicktime = self._preset.properties()["file_type"] == "mov"
      platformUsesQuicktime = sys.platform.startswith("win32") or sys.platform.startswith("darwin")
      includeAudio = self._preset.properties()["insertAudio"]      
      
      # Only the quicktime write node has the audio file knob
      if includeAudio and isQuicktime and platformUsesQuicktime:        
        
        # Get audiotracks
        audioTracks = sequence.audioTracks()
        if audioTracks:
        
          # Grab first audio track
          audioTrack = audioTracks[0]
          
          # Get list of items on track
          audioTrackItems = audioTrack.items()
          
          if audioTrackItems:
                      
            # Get first item on Track
            firstAudioTrackItem = audioTrackItems[0]
            
            firstSrcFile, firstSrcExt = self.sourceFileFromTrackItem(firstAudioTrackItem)
            
            offset = firstAudioTrackItem.timelineIn() - firstAudioTrackItem.sourceIn()
            
            # The first audio track item is a QuickTime
            if firstSrcExt == ".mov":
              # TODO
              pass
            else:
              # Otherwise, perhaps we can stitch them together TODO
              pass
            
            for node in self._script._nodes:
              if node.type() == "Write":              
                node.setKnob("audiofile", firstSrcFile)
                node.setKnob("units", 'Frames')
                node.setKnob("audio_offset",  offset)
            
      else:
        print "Error: Cannot add audio to non-quicktime format"  
        
        # Set error will end execution of task and show an error in the export queue
        # self.setError("Error: Cannot add audio to non-quicktime format")
      

  def taskStep(self):
    # The parent implimentation of taskstep
    #  - Calls self.writeScript() which writes the script to the path in self._scriptfile
    #  - Executes script in Nuke with either HieroNuke or local Nuke as defined in preferences
    #  - Parses the output ever frame until complete
    
    return FnTranscodeExporter.TranscodeExporter.taskStep(self)    
    
    ###############################################
    # Alternative impliementation for a render farm
    
    # Instead write out the script
    self.writeScript()
    
    # Copy the script somewhere
    shutil.copyfile(self._scriptfile, "/mnt/somewhere/over/the/rainbow/")
    
    # TODO Poll for completion
    
    # Return True whilst incomplete
    # Return False when no more updates required
    return False
    
  def forcedAbort (self):
    # Parent impliementation terminates nuke process
    FnTranscodeExporter.TranscodeExporter.forcedAbort(self)    
    return
    
    # Cancel render farm job
    
    return
  
  def finishTask (self):  
    FnTranscodeExporter.TranscodeExporter.finishTask(self)

    # Called when task step signals completion
    
    return
    
  def progress(self):
    # Parent implimentation returns a float between 0.0-1.0 representing progress
    # Progress is monitored by parsing frame progress in stdout from Nuke 
    
    # Ensure return type is float or shiboken will throw an error
    return float(FnTranscodeExporter.TranscodeExporter.progress(self))
    
    
    


  def sourceFileFromTrackItem( self, trackItem ):
    
    # Get Clip
    clip = trackItem.source()
    
    # Get Clip Source
    source = clip.mediaSource()
    
    # Get Source Filename
    filename = source.firstpath()
    
    # Split off the extension
    base, extension = os.path.splitext(filename)
    
    # Return filenamea and Extension
    return filename, extension.lower()

  
  
class CustomTranscodePreset(FnTranscodeExporter.TranscodePreset):
  def __init__(self, name, properties):
    FnTranscodeExporter.TranscodePreset.__init__(self, name, properties)
    self._parentType = CustomTranscode
    
    # Set default values
    self._properties["insertAudio"] = True
    
    # Update properties dictionary with data from file
    self._properties.update(properties)
    
  # Override supported types to be Sequences only
  def supportedItems(self):
    return hiero.core.TaskPresetBase.kSequence

    
# Register this CustomTask and its associated Preset
hiero.core.taskRegistry.registerTask(CustomTranscodePreset, CustomTranscode)

