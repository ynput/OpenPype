// ***************************************************************************
// *                        ImageSequenceLoader                              *
// ***************************************************************************


// check if PypeHarmony is defined and if not, load it.
if (typeof PypeHarmony !== 'undefined') {
  var PYPE_HARMONY_JS = System.getenv('PYPE_HARMONY_JS');
  include(PYPE_HARMONY_JS + '/pype_harmony.js');
}


/**
 * @namespace
 * @classdesc Image Sequence loader JS code.
 * @property  {Object}  loaders   Namespace for Loaders JS code.
 * @property  {Object}  Creators  Namespace for Creators JS code.
 * @property  {Object}  Publish   Namespace for Publish plugins JS code.
 */
ImageSequenceLoader = function() {
  this.PNGTransparencyMode = 0; // Premultiplied wih Black
  this.TGATransparencyMode = 0; // Premultiplied wih Black
  this.SGITransparencyMode = 0; // Premultiplied wih Black
  this.LayeredPSDTransparencyMode = 1; // Straight
  this.FlatPSDTransparencyMode = 2; // Premultiplied wih White
};


/**
 * Get unique column name.
 * @function
 * @param  {string}  columnPrefix Column name.
 * @return {string}  Unique column name.
 */
ImageSequenceLoader.prototype.getUniqueColumnName = function(columnPrefix) {
  var suffix = 0;
  // finds if unique name for a column
  var columnName = columnPrefix;
  while (suffix < 2000) {
    if (!column.type(columnName)) {
      break;
    }

    suffix = suffix + 1;
    columnName = columnPrefix + '_' + suffix;
  }
  return columnName;
};


/**
 * Import file sequences into Harmony.
 * @function
 * @param  {object}  args  Arguments for import, see Example.
 * @return {string}  Read node name
 *
 * @example
 * // Agrguments are in following order:
 * var args = [
 *    root, // Harmony root
 *    files, // Files in file sequences
 *    name, // Node name
 *    startFrame // Sequence starting frame
 * ];
 */
ImageSequenceLoader.prototype.importFiles = function(args) {
  var root = args[0];
  var files = args[1];
  var name = args[2];
  var startFrame = args[3];
  var vectorFormat = null;
  var extension = null;
  var filename = files[0];
  var pos = filename.lastIndexOf('.');
  if (pos < 0) {
    return null;
  }

  extension = filename.substr(pos+1).toLowerCase();
  if (extension == 'jpeg') {
    extension = 'jpg';
  }

  if (extension == 'tvg') {
    vectorFormat = 'TVG';
    extension ='SCAN'; // element.add() will use this.
  }

  var elemId = element.add(
      name,
      'BW',
      scene.numberOfUnitsZ(),
      extension.toUpperCase(),
      vectorFormat
  );

  if (elemId == -1) {
    // hum, unknown file type most likely -- let's skip it.
    return null; // no read to add.
  }

  var uniqueColumnName = this.getUniqueColumnName(name);
  column.add(uniqueColumnName, 'DRAWING');
  column.setElementIdOfDrawing(uniqueColumnName, elemId);
  var read = node.add(root, name, 'READ', 0, 0, 0);
  var transparencyAttr = node.getAttr(
      read, frame.current(), 'READ_TRANSPARENCY'
  );
  var opacityAttr = node.getAttr(read, frame.current(), 'OPACITY');
  transparencyAttr.setValue(true);
  opacityAttr.setValue(true);
  var alignmentAttr = node.getAttr(read, frame.current(), 'ALIGNMENT_RULE');
  alignmentAttr.setValue('ASIS');
  var transparencyModeAttr = node.getAttr(
      read, frame.current(), 'applyMatteToColor'
  );
  if (extension === 'png') {
    transparencyModeAttr.setValue(this.PNGTransparencyMode);
  }
  if (extension === 'tga') {
    transparencyModeAttr.setValue(this.TGATransparencyMode);
  }
  if (extension === 'sgi') {
    transparencyModeAttr.setValue(this.SGITransparencyMode);
  }
  if (extension === 'psd') {
    transparencyModeAttr.setValue(this.FlatPSDTransparencyMode);
  }
  if (extension === 'jpg') {
    transparencyModeAttr.setValue(this.LayeredPSDTransparencyMode);
  }

  node.linkAttr(read, 'DRAWING.ELEMENT', uniqueColumnName);
  if (files.length === 1) {
    // Create a drawing drawing, 'true' indicate that the file exists.
    Drawing.create(elemId, 1, true);
    // Get the actual path, in tmp folder.
    var drawingFilePath = Drawing.filename(elemId, '1');
    PypeHarmony.copyFile(files[0], drawingFilePath);
    // Expose the image for the entire frame range.
    for (var i =0; i <= frame.numberOf() - 1; ++i) {
      timing = startFrame + i;
      column.setEntry(uniqueColumnName, 1, timing, '1');
    }
  } else {
    // Create a drawing for each file.
    for (var i =0; i <= files.length - 1; ++i) {
      timing = startFrame + i;
      // Create a drawing drawing, 'true' indicate that the file exists.
      Drawing.create(elemId, timing, true);
      // Get the actual path, in tmp folder.
      var drawingFilePath = Drawing.filename(elemId, timing.toString());
      PypeHarmony.copyFile(files[i], drawingFilePath);
      column.setEntry(uniqueColumnName, 1, timing, timing.toString());
    }
  }
  var greenColor = new ColorRGBA(0, 255, 0, 255);
  node.setColor(read, greenColor);
  return read;
};


/**
 * Replace files sequences in Harmony.
 * @function
 * @param  {object}  args  Arguments for import, see Example.
 * @return {string}  Read node name
 *
 * @example
 * // Agrguments are in following order:
 * var args = [
 *    files, // Files in file sequences
 *    name, // Node name
 *    startFrame // Sequence starting frame
 * ];
 */
ImageSequenceLoader.prototype.replaceFiles = function(args) {
  var files = args[0];
  MessageLog.trace(files);
  MessageLog.trace(files.length);
  var _node = args[1];
  var startFrame = args[2];
  var _column = node.linkedColumn(_node, 'DRAWING.ELEMENT');
  var elemId = column.getElementIdOfDrawing(_column);
  // Delete existing drawings.
  var timings = column.getDrawingTimings(_column);
  for ( var i =0; i <= timings.length - 1; ++i) {
    column.deleteDrawingAt(_column, parseInt(timings[i]));
  }
  var filename = files[0];
  var pos = filename.lastIndexOf('.');
  if (pos < 0) {
    return null;
  }
  var extension = filename.substr(pos+1).toLowerCase();
  if (extension === 'jpeg') {
    extension = 'jpg';
  }

  var transparencyModeAttr = node.getAttr(
      _node, frame.current(), 'applyMatteToColor'
  );
  if (extension === 'png') {
    transparencyModeAttr.setValue(this.PNGTransparencyMode);
  }
  if (extension === 'tga') {
    transparencyModeAttr.setValue(this.TGATransparencyMode);
  }
  if (extension === 'sgi') {
    transparencyModeAttr.setValue(this.SGITransparencyMode);
  }
  if (extension == 'psd') {
    transparencyModeAttr.setValue(this.FlatPSDTransparencyMode);
  }
  if (extension === 'jpg') {
    transparencyModeAttr.setValue(this.LayeredPSDTransparencyMode);
  }

  if (files.length == 1) {
    // Create a drawing drawing, 'true' indicate that the file exists.
    Drawing.create(elemId, 1, true);
    // Get the actual path, in tmp folder.
    var drawingFilePath = Drawing.filename(elemId, '1');
    PypeHarmony.copyFile(files[0], drawingFilePath);
    MessageLog.trace(files[0]);
    MessageLog.trace(drawingFilePath);
    // Expose the image for the entire frame range.
    for (var i =0; i <= frame.numberOf() - 1; ++i) {
      timing = startFrame + i;
      column.setEntry(_column, 1, timing, '1');
    }
  } else {
    // Create a drawing for each file.
    for (var i =0; i <= files.length - 1; ++i) {
      timing = startFrame + i;
      // Create a drawing drawing, 'true' indicate that the file exists.
      Drawing.create(elemId, timing, true);
      // Get the actual path, in tmp folder.
      var drawingFilePath = Drawing.filename(elemId, timing.toString());
      PypeHarmony.copyFile( files[i], drawingFilePath );
      column.setEntry(_column, 1, timing, timing.toString());
    }
  }
  var greenColor = new ColorRGBA(0, 255, 0, 255);
  node.setColor(_node, greenColor);
};

// add self to Pype Loaders
PypeHarmony.Loaders.ImageSequenceLoader = new ImageSequenceLoader();
