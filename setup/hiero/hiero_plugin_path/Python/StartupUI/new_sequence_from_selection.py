# Context Menu option to create new sequences from selected clips in the bin. If clips are Stereo left and right then one sequence will be created with left and right tagged tracks.

from hiero.core import *
from hiero.ui import *
from PySide.QtGui import *
from PySide.QtCore import *
import re
import os

class NewSequenceFromSelectionAction(QAction):

  class NewSequenceFromSelection(QDialog):

    def __init__(self,  trackItem,  parent=None):
      super(NewSequenceFromSelectionAction.NewSequenceFromSelection, self).__init__(parent)
      self.setWindowTitle("New Sequence")
      self.setSizeGripEnabled(False)
      self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
      self.setMinimumSize(350,174)
      self.setContentsMargins(15, 10, 10, 0)
      self.layout = QVBoxLayout()
      self.layout.setContentsMargins(20, 20, 20, 20)

      self.groupBox = QGroupBox()
      self.groupLayout = QFormLayout()
      self.groupBox.setLayout(self.groupLayout)

      self._radioSingle = QRadioButton("Single Sequence", self.groupBox)
      self._radioSingle.setToolTip("Create a single sequence with all selected items stacked.\nUseful for selecting multiple comp elements to export to Nuke with Collate Tracks.")
      self._radioSingle.setChecked(True)
      self._radioMultiple = QRadioButton("Multiple Sequences", self.groupBox)
      self._radioMultiple.setToolTip("Create multiple sequences for each selected item.")
      self.groupLayout.setWidget(0, QFormLayout.SpanningRole, self._radioSingle)
      self.groupLayout.setWidget(1, QFormLayout.SpanningRole, self._radioMultiple)

      self.spacerItem = QSpacerItem(15, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
      self.groupLayout.setItem(2, QFormLayout.LabelRole, self.spacerItem)

      self._sequenceLayers = QCheckBox("Sequential Layers", self.groupBox)
      self._sequenceLayers.setChecked(True)
      self._sequenceLayers.setToolTip("Place the selected items on one track back to back if Single Sequence is selected.\nOtherwise items are stacked on separate tracks.")
      self.groupLayout.setWidget(2, QFormLayout.FieldRole, self._sequenceLayers)

      self._includeAudio = QCheckBox("Include Audio", self.groupBox)
      self._includeAudio.setChecked(True)
      self._includeAudio.setToolTip("Include Audio Tracks from clips containing audio.")
      self.groupLayout.setWidget(3, QFormLayout.SpanningRole, self._includeAudio)

      self.horizontalLayout = QHBoxLayout()
      self.horizontalLayout.setSpacing(-1)
      self.horizontalLayout.setSizeConstraint(QLayout.SetDefaultConstraint)
      self.horizontalLayout.setObjectName("horizontalLayout")
      self.label = QLabel()
      self.label.setText("Format:")
      self.horizontalLayout.addWidget(self.label)
      self._formatChooser = hiero.ui.FormatChooser()
      self._formatChooser.setToolTip("Choose the format for a New Sequence created from Multiple Selections.")
      self._formatChooser.formatChanged.connect(self.formatChanged)
      self.horizontalLayout.addWidget(self._formatChooser)
      self.horizontalLayout.setStretch(1, 40)
      self.groupLayout.setLayout(4, QFormLayout.SpanningRole, self.horizontalLayout)



      # Add the standard ok/cancel buttons, default to ok.
      self._buttonbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
      self._buttonbox.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
      self._buttonbox.button(QDialogButtonBox.StandardButton.Ok).setDefault(True)
      self._buttonbox.accepted.connect(self.accept)
      self._buttonbox.rejected.connect(self.reject)
      self.groupLayout.addWidget(self._buttonbox)

      self.setLayout(self.groupLayout)
      self.layout.addWidget(self.groupBox)

      self._radioMultiple.clicked.connect(self.sequenceOptionChanged)
      self._radioSingle.clicked.connect(self.sequenceOptionChanged)

      firstclip = hiero.ui.activeView().selection()[0]
      try:
        format = firstclip.activeItem().format()
        self._formatChooser.setCurrentFormat(format)
      except:
        print "Could not set format"

    def formatChanged (self):
      format = self._formatChooser.currentFormat()

    def sequenceOptionChanged(self):
      if self._radioMultiple.isChecked():
        self._sequenceLayers.setEnabled(False)
        self._formatChooser.setEnabled(False)
        self.label.setEnabled(False)
      if self._radioSingle.isChecked():
        self._sequenceLayers.setEnabled(True)
        if self._formatChooser.count() > 0:
          self._formatChooser.setEnabled(True)
          self.label.setEnabled(True)


  def __init__(self):
      QAction.__init__(self, "Create Sequence from Selection...", None)
      self.triggered.connect(self.doit)
      hiero.core.events.registerInterest((hiero.core.events.EventType.kShowContextMenu, hiero.core.events.EventType.kBin), self.eventHandler)

  def trackExists(self, sequence, trackName):
    for track in sequence:
      if track.name() == trackName:
        return track
    return None

  # Create a stereo sequence with Left/Right tagged tracks. Eventually when full stereo support is implemented this can be changed.
  def newStereoSequence(self, leftClip, rightClip, baseName):

    bin = leftClip.binItem().parentBin()

    if leftClip.mediaSource().hasVideo():
      if leftClip.mediaSource().metadata()["foundry.source.framerate"]:
        fpsL = leftClip.mediaSource().metadata()["foundry.source.framerate"]
      else:
        fpsL = leftClip.framerate()

    if rightClip.mediaSource().hasVideo():
      if rightClip.mediaSource().metadata()["foundry.source.framerate"]:
        fpsR = rightClip.mediaSource().metadata()["foundry.source.framerate"]
      else:
        fpsR = rightClip.framerate()

    if fpsL != fpsR:
      QMessageBox.warning(None, "New Sequence", "Left and Right Stereo tracks must have the same framerate.", QMessageBox.Ok)
      return
    else:
      fps = fpsL

    if leftClip.mediaSource().duration() != rightClip.mediaSource().duration():
      QMessageBox.warning(None, "New Sequence", "Tracks %s and %s must have the same duration to create a Stereo Sequence." % (leftClip.name(), rightClip.name()), QMessageBox.Ok)
      return

    if leftClip.format().toString() != rightClip.format().toString():
      QMessageBox.warning(None, "New Sequence", "Clip %s resolution (%s) does not match Clip %s (%s)." % (leftClip.name(), leftClip.format(), rightClip.name(), rightClip.format()), QMessageBox.Ok)
      return

    sequence = Sequence(baseName)
    sequence.setFramerate(hiero.core.TimeBase.fromString(str(fps)))
    sequence.setFormat(leftClip.format())
    trackLeft = VideoTrack("Left")
    trackRight = VideoTrack("Right")
    sequence.addTrack(trackLeft)
    sequence.addTrack(trackRight)

    videoLeft = trackLeft.addTrackItem(leftClip, 0)
    videoRight = trackRight.addTrackItem(rightClip, 0)
    #videoLeft.link(videoRight)

    leftTag = hiero.core.projects(hiero.core.Project.kStartupProjects)[0].tagsBin().items()[0][0]
    rightTag = hiero.core.projects(hiero.core.Project.kStartupProjects)[0].tagsBin().items()[0][1]
    trackLeft.addTag(leftTag)
    trackRight.addTag(rightTag)

    bin.addItem(BinItem(sequence))


  def doit(self):
    selection = hiero.ui.activeView().selection()
    isStereo = False

    # if only one item is selected
    if len(selection) == 1:
      clip = selection[0].activeItem()
      bin = clip.binItem().parentBin()
      sequence = Sequence(selection[0].name())

      if clip.mediaSource().hasVideo():
        if clip.mediaSource().metadata()["foundry.source.framerate"]:
          fps = clip.mediaSource().metadata()["foundry.source.framerate"]
        else:
          fps = clip.framerate()
        sequence.setFramerate(hiero.core.TimeBase.fromString(str(fps)))
        sequence.setFormat(clip.format())

        for i in range(clip.numVideoTracks()):
          sequence.addTrack(hiero.core.VideoTrack("Video " + str(i+1)))
          try:
            videoClip = sequence.videoTrack(i).addTrackItem(clip, 0)
          except:
            print "Failed to add clip"
      else:
        videoClip = None

      if clip.mediaSource().hasAudio():
        linkItems = []
        for i in range(clip.numAudioTracks()):
          audioTrackName = "Audio " + str( i+1 )
          if self.trackExists(sequence, audioTrackName) is None:
            newAudioTrack = sequence.addTrack(hiero.core.AudioTrack(audioTrackName))
          else:
            newAudioTrack = self.trackExists(sequence, audioTrackName)
          audioClip = newAudioTrack.addTrackItem(clip, i, 0)
          linkItems.append(audioClip)
          if videoClip:
            audioClip.link(videoClip)
          else:
            if len(linkItems) > 0:
              audioClip.link(linkItems[0])

      bin.addItem(BinItem(sequence))

    # If exactly 2 items are selected we check to see if they are a stereo pair
    # If yes then create a stereo sequence. Otherwise treat them as 2 normal clips
    if len(selection) == 2:
      clip1 = selection[0].activeItem()
      clip2 = selection[1].activeItem()
      bin = clip1.binItem().parentBin()

      leftrx = re.compile("(.*)(_L(eft)?)$", re.IGNORECASE)
      rightrx = re.compile("(.*)(_R(ight)?)$", re.IGNORECASE)

      if leftrx.match(clip1.name()):
        leftmatch = leftrx.match(clip1.name()).groups()[1]
        leftClip = clip1
        leftName = leftrx.match(leftClip.name()).groups()[0]
      elif leftrx.match(clip2.name()):
        leftmatch = leftrx.match(clip2.name()).groups()[1]
        leftClip = clip2
        leftName = leftrx.match(leftClip.name()).groups()[0]
      else:
        leftClip = None

      if rightrx.match(clip1.name()):
        rightmatch = rightrx.match(clip1.name())
        rightClip = clip1
        rightName = rightrx.match(rightClip.name()).groups()[0]
      elif rightrx.match(clip2.name()):
        rightmatch = rightrx.match(clip2.name())
        rightClip = clip2
        rightName = rightrx.match(rightClip.name()).groups()[0]
      else:
        rightClip = None

      if leftClip != None and rightClip != None:
        if leftName == rightName:
          newName = leftName
          isStereo = True

      if isStereo == True:
        self.newStereoSequence(leftClip, rightClip, newName)

    # If multiple clips are selected and we want a Single Sequence
    if len(selection) > 1 and isStereo == False:
      dialog = self.NewSequenceFromSelection(selection)
      if dialog.exec_():
        if dialog._radioSingle.isChecked() == True:

          newFPS = selection[0].activeItem().framerate()
          newResolution = dialog._formatChooser.currentFormat()

          # If we want to stack clips on separate layers
          if dialog._sequenceLayers.isChecked() == False:
            clip = selection[0].activeItem()
            bin = clip.binItem().parentBin()
            sequence = Sequence(selection[0].name())

            if clip.mediaSource().hasVideo():
              if clip.mediaSource().metadata()["foundry.source.framerate"]:
                fps = clip.mediaSource().metadata()["foundry.source.framerate"]
              else:
                fps = clip.framerate()
              sequence.setFramerate(hiero.core.TimeBase.fromString(str(newFPS)))
              sequence.setFormat(newResolution)
            else:
              videoClip = None

            k = 0
            j = 0
            for item in selection:
              clip = item.activeItem()
              if clip.mediaSource().hasVideo():
                for i in range(clip.numVideoTracks()):
                  newVideoTrack = sequence.addTrack(hiero.core.VideoTrack("Video " + str(k+1)))
                  try:
                    videoClip = newVideoTrack.addTrackItem(clip, 0)
                  except:
                    print "Failed to add clip"
              else:
                videoClip = None
              k+=1

              if clip.mediaSource().hasAudio() and dialog._includeAudio.isChecked():
                linkedItems = []
                for i in range(clip.numAudioTracks()):
                  newAudioTrack = sequence.addTrack(hiero.core.AudioTrack("Audio " + str(j+i+1) ))
                  audioClip = newAudioTrack.addTrackItem(clip, i, 0)
                  linkedItems.append(audioClip)
                  if videoClip:
                    audioClip.link(videoClip)
                  else:
                    if len(linkedItems) > 0:
                      audioClip.link(linkedItems[0])
                  j+=1

            bin.addItem(BinItem(sequence))

          # Add the clips to the sequence back to back on one video layer
          if dialog._sequenceLayers.isChecked() == True:
            clip = selection[0].activeItem()
            bin = clip.binItem().parentBin()
            sequence = Sequence(selection[0].name())

            if clip.mediaSource().hasVideo():
              if clip.mediaSource().metadata()["foundry.source.framerate"]:
                fps = clip.mediaSource().metadata()["foundry.source.framerate"]
              else:
                fps = clip.framerate()
              sequence.setFramerate(hiero.core.TimeBase.fromString(str(newFPS)))
              sequence.setFormat(newResolution)
            else:
              videoClip = None
              fps = sequence.framerate()

            sequence.addTrack(hiero.core.VideoTrack("Video 1"))
            k = 0
            for item in selection:
              clip = item.activeItem()

              if clip.mediaSource().hasVideo():
                for i in range(clip.numVideoTracks()):
                  try:
                    videoClip = sequence.videoTrack(0).addTrackItem(clip, k)
                  except:
                    print "Failed to add clip"
                  outTime = clip.duration() - 1
              else:
                videoClip = None
                outTime = None

              if clip.mediaSource().hasAudio() and dialog._includeAudio.isChecked():
                linkedItems = []
                for i in range(clip.numAudioTracks()):
                  audioTrackName = "Audio " + str( i+1 )
                  if self.trackExists(sequence, audioTrackName) is None:
                    newAudioTrack = sequence.addTrack(hiero.core.AudioTrack(audioTrackName))
                  else:
                    newAudioTrack = self.trackExists(sequence, audioTrackName)

                  audioClip = newAudioTrack.addTrackItem(clip, i, k)
                  linkedItems.append(audioClip)
                  if videoClip:
                    audioClip.link(videoClip)
                  else:
                    if len(linkedItems) > 0:
                      audioClip.link(linkedItems[0])
                      # Audio only duration is currently returned in samples so we need to convert to frames
                      outTime = ( float(clip.duration() / 48000) * float(fps) ) - 1
              k+= (outTime + 1)

            bin.addItem(BinItem(sequence))

        # Multiple Sequences from selection
        if dialog._radioMultiple.isChecked():
          stereoPairs = []
          singleFiles = []
          leftrx = re.compile("(.*)(_L(eft)?)$", re.IGNORECASE)
          rightrx = re.compile("(.*)(_R(ight)?)$", re.IGNORECASE)

          for item in selection:
            clip = item.activeItem()

            if not leftrx.match(clip.name()) and not rightrx.match(clip.name()):
              singleFiles.append(clip)

            if leftrx.match(clip.name()):
              baseName = leftrx.match(clip.name()).groups()[0]
              if len(stereoPairs) == 0:
                stereoPairs.append([clip])
              else:
                for i in range(len(stereoPairs)):
                  pairMatch = True
                  for pair in stereoPairs[i]:
                    if baseName in pair.name():
                      stereoPairs[i].append(clip)
                      break
                    else:
                      pairMatch = False
                if pairMatch == False:
                  stereoPairs.append([clip])

            if rightrx.match(clip.name()):
              baseName = rightrx.match(clip.name()).groups()[0]
              if len(stereoPairs) == 0:
                stereoPairs.append([clip])
              else:
                for i in range(len(stereoPairs)):
                  pairMatch = True
                  for pair in stereoPairs[i]:
                    if baseName in pair.name():
                      stereoPairs[i].append(clip)
                      break
                    else:
                      pairMatch = False
                if pairMatch == False:
                  stereoPairs.append([clip])

          hiero.core.projects()[-1].beginUndo("Create Multiple Sequences")
          for pair in stereoPairs:

            if len(pair) == 1:
              singleFiles.append(pair[0])

            if len(pair) == 2:
              if leftrx.match(pair[0].name()):
                leftClip = pair[0]
              else:
                leftClip = pair[1]

              if rightrx.match(pair[0].name()):
                rightClip = pair[0]
              else:
                rightClip = pair[1]

              newName = leftrx.match(leftClip.name()).groups()[0]
              self.newStereoSequence(leftClip, rightClip, newName)

          for clip in singleFiles:
            bin = clip.binItem().parentBin()
            sequence = Sequence(clip.name())

            if clip.mediaSource().hasVideo():
              if clip.mediaSource().metadata()["foundry.source.framerate"]:
                fps = clip.mediaSource().metadata()["foundry.source.framerate"]
              else:
                fps = clip.framerate()
              sequence.setFramerate(hiero.core.TimeBase.fromString(str(fps)))
              sequence.setFormat(clip.format())

              for i in range(clip.numVideoTracks()):
                sequence.addTrack(hiero.core.VideoTrack("Video " + str(i+1)))
                try:
                  videoClip = sequence.videoTrack(i).addTrackItem(clip, 0)
                except:
                  print "Failed to add clip"
                  videoClip = None
            else:
              videoClip = None

            if clip.mediaSource().hasAudio() and dialog._includeAudio.isChecked():
              linkedItems = []
              for i in range(clip.numAudioTracks()):
                audioTrackName = "Audio " + str( i+1 )
                if self.trackExists(sequence, audioTrackName) is None:
                  newAudioTrack = sequence.addTrack(hiero.core.AudioTrack(audioTrackName))
                else:
                  newAudioTrack = self.trackExists(sequence, audioTrackName)
                audioClip = newAudioTrack.addTrackItem(clip, i, 0)
                linkedItems.append(audioClip)
                if videoClip:
                  audioClip.link(videoClip)
                else:
                  if len(linkedItems) > 0:
                    audioClip.link(linkedItems[0])

            bin.addItem(BinItem(sequence))
          hiero.core.projects()[-1].endUndo()

  def eventHandler(self, event):
    if not hasattr(event.sender, 'selection'):
      return

    # Disable if a sequence is selected or nothing is selected
    s = event.sender.selection()
    if s is None:
      s = ()

    if isinstance(s[0], hiero.core.Bin):
      s = ()

    if len(s) > 0:
      if isinstance(s[0], BinItem):
        if isinstance(s[0].activeItem(), Sequence):
          s = ()

      for selected in s:
        if type(selected.activeItem()) != Clip:
          s = ()

    title = "New Sequence from Selection"
    self.setText(title)
    self.setEnabled( len(s) > 0 )
    event.menu.addAction(self)

action = NewSequenceFromSelectionAction()