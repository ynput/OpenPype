//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////
//
//                            openHarmony Library
//
//
//         Developped by Mathieu Chaptel, Chris Fourney
//
//
//   This library is an open source implementation of a Document Object Model
//   for Toonboom Harmony. It also implements patterns similar to JQuery
//   for traversing this DOM.
//
//   Its intended purpose is to simplify and streamline toonboom scripting to
//   empower users and be easy on newcomers, with default parameters values,
//   and by hiding the heavy lifting required by the official API.
//
//   This library is provided as is and is a work in progress. As such, not every
//   function has been implemented or is garanteed to work. Feel free to contribute
//   improvements to its official github. If you do make sure you follow the provided
//   template and naming conventions and document your new methods properly.
//
//   This library doesn't overwrite any of the objects and classes of the official
//   Toonboom API which must remains available.
//
//   This library is made available under the Mozilla Public license 2.0.
//   https://www.mozilla.org/en-US/MPL/2.0/
//
//   The repository for this library is available at the address:
//   https://github.com/cfourney/OpenHarmony/
//
//
//   For any requests feel free to contact m.chaptel@gmail.com
//
//
//
//
//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////

//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//          $.oFolder class         //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The $.oFolder helper class -- providing utilities for folder manipulation and access.
 * @constructor
 * @classdesc  $.oFolder Base Class
 * @param       {string}              path                      The path to the folder.
 *
 * @property    {string}             path                      The path to the folder.
 */
$.oFolder = function(path){
    this._type = "folder";
    this._path = fileMapper.toNativePath(path).split("\\").join("/");

    // fix lowercase drive letter
    var path_components = this._path.split("/");
    if (path_components[0] && about.isWindowsArch()){
      // local path that starts with a drive letter
      path_components[0] = path_components[0].toUpperCase()
      this._path = path_components.join("/");
    }
}


/**
 * The path of the folder.  Setting a path doesn't move the file, only changes where the file object is pointing.
 * @name $.oFolder#path
 * @type {string}
 */
Object.defineProperty($.oFolder.prototype, 'path', {
    get: function(){
      return this._path;
    },
    set: function( newPath ){
      this._path = fileMapper.toNativePath( newPath ).split("\\").join("/");
    }
});


/**
 * The path of the file encoded as a toonboom relative path.
 * @name $.oFile#toonboomPath
 * @readonly
 * @type {string}
 */
Object.defineProperty( $.oFolder.prototype, 'toonboomPath', {
  get: function(){
    var _path = this._path;
    if (!this.$.scene.online) return _path;
    if (_path.slice(0,2) != ("//")) return _path;

    var _pathComponents = _path.replace("//", "").split("/");
    var _drive = (_pathComponents[1]=="usadata000")?_pathComponents[1]:_pathComponents[1].toUpperCase();
    var _path = _pathComponents.slice(2);

    return ["",_drive].concat(_path).join("/");
  }
});


/**
 * The name of the folder.
 * @name $.oFolder#name
 * @type {string}
 */
Object.defineProperty($.oFolder.prototype, 'name', {
    get: function(){
        var _name = this.path.split("/");
        _name = _name.pop();
        return _name;
    },
    set: function(newName){
      this.rename(newName)
    }
});


/**
 * The parent folder.
 * @name $.oFolder#folder
 * @type {$.oFolder}
 */
Object.defineProperty($.oFolder.prototype, 'folder', {
    get: function(){
        var _folder = this.path.slice(0,this.path.lastIndexOf("/", this.path.length-2));
        return new this.$.oFolder(_folder);
    }
});


/**
 * The parent folder.
 * @name $.oFolder#exists
 * @type {string}
 */
Object.defineProperty($.oFolder.prototype, 'exists', {
    get: function(){
        var dir = new QDir;
        dir.setPath(this.path)
        return dir.exists();
    }
});


/**
 * The files in the folder.
 * @name $.oFolder#files
 * @type {$.oFile[]}
 * @deprecated use oFolder.getFiles() instead to specify filter
 */
Object.defineProperty($.oFolder.prototype, 'files', {
    get: function(){
      var dir = new QDir;
      dir.setPath(this.path);
      dir.setFilter( QDir.Files );

      if (!dir.exists) throw new Error("can't get files from folder "+this.path+" because it doesn't exist");

      return dir.entryList().map(function(x){return new this.$.oFile(dir.path()+"/"+x)});
    }
});


/**
 * The folders within this folder.
 * @name $.oFolder#folders
 * @type {$.oFile[]}
 * @deprecated oFolder.folder is the containing parent folder, it can't also mean the children folders
 */
Object.defineProperty($.oFolder.prototype, 'folders', {
    get: function(){
      var _dir = new QDir;
      _dir.setPath(this.path);
      if (!_dir.exists) throw new Error("can't get files from folder "+this.path+" because it doesn't exist");
      _dir.setFilter(QDir.Dirs);
      var _folders = _dir.entryList();

      for (var i = _folders.length-1; i>=0; i--){
          if (_folders[i] == "." || _folders[i] == "..") _folders.splice(i,1);
      }

      return _folders.map(function(x){return new this.$.oFolder( _dir.path() + "/" + x )});
    }
});


/**
 * The content within the folder -- both folders and files.
 * @name $.oFolder#content
 * @type {$.oFile/$.oFolder[] }
 */
Object.defineProperty($.oFolder.prototype, 'content', {
    get: function(){
      var content = this.files;
          content = content.concat( this.folders );
      return content;
    }
});


/**
 * Lists the file names contained inside the folder.
 * @param   {string}   [filter]               Filter wildcards for the content of the folder.
 *
 * @returns {string[]}   The names of the files contained in the folder that match the filter.
 */
$.oFolder.prototype.listFiles = function(filter){
    if (typeof filter === 'undefined') var filter = "*";

    var _dir = new QDir;
    _dir.setPath(this.path);
    if (!_dir.exists) throw new Error("can't get files from folder "+this.path+" because it doesn't exist");
    _dir.setNameFilters([filter]);
    _dir.setFilter( QDir.Files);
    var _files = _dir.entryList();

    return _files;
}


/**
 * get the files from the folder
 * @param   {string}   [filter]     Filter wildcards for the content of the folder.
 *
 * @returns {$.oFile[]}   A list of files contained in the folder as oFile objects.
 */
$.oFolder.prototype.getFiles = function( filter ){
    if (typeof filter === 'undefined') var filter = "*";
    // returns the list of $.oFile in a directory that match a filter

    var _path = this.path;

    var _files = [];
    var _file_list = this.listFiles(filter);
    for( var i in _file_list){
      _files.push( new this.$.oFile( _path+'/'+_file_list[i] ) );
    }

    return _files;
}


/**
 * lists the folder names contained inside the folder.
 * @param   {string}   [filter="*.*"]    Filter wildcards for the content of the folder.
 *
 * @returns {string[]}  The names of the files contained in the folder that match the filter.
 */
$.oFolder.prototype.listFolders = function(filter){

    if (typeof filter === 'undefined') var filter = "*";

    var _dir = new QDir;
    _dir.setPath(this.path);

    if (!_dir.exists){
      this.$.debug("can't get files from folder "+this.path+" because it doesn't exist", this.$.DEBUG_LEVEL.ERROR);
      return [];
    }

    _dir.setNameFilters([filter]);
    _dir.setFilter(QDir.Dirs); //QDir.NoDotAndDotDot not supported?
    var _folders = _dir.entryList();

    _folders = _folders.filter(function(x){return x!= "." && x!= ".."})

    return _folders;
}


/**
 * gets the folders inside the oFolder
 * @param   {string}   [filter]              Filter wildcards for the content of the folder.
 *
 * @returns {$.oFolder[]}      A list of folders contained in the folder, as oFolder objects.
 */
$.oFolder.prototype.getFolders = function( filter ){
    if (typeof filter === 'undefined') var filter = "*";
    // returns the list of $.oFile in a directory that match a filter

    var _path = this.path;

    var _folders = [];
    var _folders_list = this.listFolders(filter);
    for( var i in _folders_list){
      _folders.push( new this.$.oFolder(_path+'/'+_folders_list[i]));
    }

    return _folders;
}


 /**
 * Creates the folder, if it doesn't already exist.
 * @returns { bool }      The existence of the newly created folder.
 */
$.oFolder.prototype.create = function(){
  if( this.exists ){
    this.$.debug("folder "+this.path+" already exists and will not be created", this.$.DEBUG_LEVEL.WARNING)
    return true;
  }

  var dir = new QDir(this.path);

  dir.mkpath(this.path);
  if (!this.exists) throw new Error ("folder " + this.path + " could not be created.")
}


/**
 * Copy the folder and its contents to another path.
 * @param   {string}   folderPath          The path to an existing folder in which to copy this folder. (Can provide an oFolder)
 * @param   {string}   [copyName]          Optionally, a name for the folder copy, if different from the original
 * @param   {bool}     [overwrite=false]   Whether to overwrite the files that are already present at the copy location.
 * @returns {$.oFolder} the oFolder describing the newly created copy.
 */
$.oFolder.prototype.copy = function( folderPath, copyName, overwrite ){
  // TODO: it should propagate errors from the recursive copy and throw them before ending?
  if (typeof overwrite === 'undefined') var overwrite = false;
  if (typeof copyName === 'undefined' || !copyName) var copyName = this.name;
  if (!(folderPath instanceof this.$.oFolder)) folderPath = new $.oFolder(folderPath);
  if (this.name == copyName && folderPath == this.folder.path) copyName += "_copy";

  if (!folderPath.exists) throw new Error("Target folder " + folderPath +" doesn't exist. Can't copy folder "+this.path)

  var nextFolder = new $.oFolder(folderPath.path + "/" + copyName);
  nextFolder.create();
  var files = this.getFiles();
  for (var i in files){
    var _file = files[i];
    var targetFile = new $.oFile(nextFolder.path + "/" + _file.fullName);

    // deal with overwriting
    if (targetFile.exists && !overwrite){
      this.$.debug("File " + targetFile + " already exists, skipping copy of "+ _file, this.$.DEBUG_LEVEL.ERROR);
      continue;
    }

    _file.copy(nextFolder, undefined, overwrite);
  }
  var folders = this.getFolders();
  for (var i in folders){
    folders[i].copy(nextFolder, undefined, overwrite);
  }

  return nextFolder;
}


/**
 * Move this folder to the specified path.
 * @param   {string}   destFolderPath           The new complete path of the folder after the move
 * @param   {bool}     [overwrite=false]        Whether to overwrite the target.
 *
 * @return { bool }                            The result of the move.
 * @todo implement with Robocopy
 */
$.oFolder.prototype.move = function( destFolderPath, overwrite ){
    if (typeof overwrite === 'undefined') var overwrite = false;

    if (destFolderPath instanceof this.$.oFolder) destFolderPath = destFolderPath.path;

    var dir = new Dir;
    dir.path = destFolderPath;

    if (dir.exists && !overwrite)
        throw new Error("destination file "+dir.path+" exists and will not be overwritten. Can't move folder.");

    var path = fileMapper.toNativePath(this.path);
    var destPath = fileMapper.toNativePath(dir.path+"/");

    var destDir = new Dir;
    try {
        destDir.rename( path, destPath );
        this._path = destPath;

        return true;
    }catch (err){
        throw new Error ("Couldn't move folder "+this.path+" to new address "+destPath + ": " + err);
    }
}


/**
 * Move this folder to a different parent folder, while retaining its content and base name.
 * @param   {string}   destFolderPath           The path of the destination to copy the folder into.
 * @param   {bool}     [overwrite=false]        Whether to overwrite the target. Default is false.
 *
 * @return: { bool }                            The result of the move.
 */
$.oFolder.prototype.moveToFolder = function( destFolderPath, overwrite ){
  destFolderPath = (destFolderPath instanceof this.$.oFolder)?destFolderPath:new this.$.oFolder(destFolderPath)

  var folder = destFolderPath.path;
  var name = this.name;

  this.move(folder+"/"+name, overwrite);
}


/**
 * Renames the folder
 * @param {string} newName
 */
$.oFolder.prototype.rename = function(newName){
  var destFolderPath = this.folder.path+"/"+newName
  if ((new this.$.oFolder(destFolderPath)).exists) throw new Error("Can't rename folder "+this.path + " to "+newName+", a folder already exists at this location")

  this.move(destFolderPath)
}


/**
 * Deletes the folder.
 * @param   {bool}    removeContents            Whether to check if the folder contains files before deleting.
 */
$.oFolder.prototype.remove = function (removeContents){
  if (typeof removeContents === 'undefined') var removeContents = false;

  if (this.listFiles.length > 0 && this.listFolders.length > 0 && !removeContents) throw new Error("Can't remove folder "+this.path+", it is not empty.")
  var _folder = new Dir(this.path);
  _folder.rmdirs();
}


/**
 * Get the sub folder or file by name.
 * @param   {string}   name                     The sub name of a folder or file within a directory.
 * @return: {$.oFolder/$.oFile}                 The resulting oFile or oFolder.
 */
$.oFolder.prototype.get = function( destName ){
  var new_path = this.path + "/" + destName;
  var new_folder = new $.oFolder( new_path );
  if( new_folder.exists ){
    return new_folder;
  }

  var new_file = new $.oFile( new_path );
  if( new_file.exists ){
    return new_file;
  }

  return false;
}


 /**
 * Used in converting the folder to a string value, provides the string-path.
 * @return  {string}   The folder path's as a string.
 */
$.oFolder.prototype.toString = function(){
    return this.path;
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//           $.oFile class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The $.oFile helper class -- providing utilities for file manipulation and access.
 * @constructor
 * @classdesc  $.oFile Base Class
 * @param      {string}              path                     The path to the file.
 *
 * @property    {string}             path                     The path to the file.
 */
$.oFile = function(path){
  this._type = "file";
  this._path = fileMapper.toNativePath(path).split('\\').join('/');

  // fix lowercase drive letter
  var path_components = this._path.split("/");
  if (path_components[0] && about.isWindowsArch()){
    // local path that starts with a drive letter
    path_components[0] = path_components[0].toUpperCase()
    this._path = path_components.join("/");
  }
}


/**
 * The name of the file with extension.
 * @name $.oFile#fullName
 * @type {string}
 */
Object.defineProperty($.oFile.prototype, 'fullName', {
    get: function(){
        var _name = this.path.slice( this.path.lastIndexOf("/")+1 );
        return _name;
    }
});


/**
 * The name of the file without extenstion.
 * @name $.oFile#name
 * @type {string}
 */
Object.defineProperty($.oFile.prototype, 'name', {
    get: function(){
      var _fullName = this.fullName;
      if (_fullName.indexOf(".") == -1) return _fullName;

      var _name = _fullName.slice(0, _fullName.lastIndexOf("."));
      return _name;
    },
    set: function(newName){
      this.rename(newName)
    }
});


/**
 * The extension of the file.
 * @name $.oFile#extension
 * @type {string}
 */
Object.defineProperty($.oFile.prototype, 'extension', {
    get: function(){
      var _fullName = this.fullName;
      if (_fullName.indexOf(".") == -1) return "";

      var _extension = _fullName.slice(_fullName.lastIndexOf(".")+1);
      return _extension;
    }
});


/**
 * The folder containing the file.
 * @name $.oFile#folder
 * @type {$.oFolder}
 */
Object.defineProperty($.oFile.prototype, 'folder', {
    get: function(){
        var _folder = this.path.slice(0,this.path.lastIndexOf("/"));
        return new this.$.oFolder(_folder);
    }
});


/**
 * Whether the file exists already.
 * @name $.oFile#exists
 * @type {bool}
 */
Object.defineProperty($.oFile.prototype, 'exists', {
    get: function(){
        var _file = new File( this.path );
        return _file.exists;
    }
})


/**
 * The path of the file. Setting a path doesn't move the file, only changes where the file object is pointing.
 * @name $.oFile#path
 * @type {string}
 */
Object.defineProperty( $.oFile.prototype, 'path', {
  get: function(){
    return this._path;
  },

  set: function( newPath ){
    this._path = fileMapper.toNativePath( newPath ).split("\\").join("/");
  }
});


/**
 * The path of the file encoded as a toonboom relative path.
 * @name $.oFile#toonboomPath
 * @readonly
 * @type {string}
 */
Object.defineProperty( $.oFile.prototype, 'toonboomPath', {
  get: function(){
    var _path = this._path;
    if (!this.$.scene.online) return _path;
    if (_path.slice(0,2) != ("//")) return _path;

    var _pathComponents = _path.replace("//", "").split("/");
    var _drive = (_pathComponents[1]=="usadata000")?_pathComponents[1]:_pathComponents[1].toUpperCase();
    var _path = _pathComponents.slice(2);

    return ["",_drive].concat(_path).join("/");
  }
});


//Todo, Size, Date Created, Date Modified


/**
 * Reads the content of the file.
 *
 * @return: { string }                      The contents of the file.
 */
$.oFile.prototype.read = function() {
  var file = new File(this.path);

  try {
    if (file.exists) {
      file.open(FileAccess.ReadOnly);
      var string = file.read();
      file.close();
      return string;
    }
  } catch (err) {
    this.$.debug(err, this.DEBUG_LEVEL.ERROR)
    return null
  }
}


/**
 * Writes to the file.
 * @param   {string}   content               Content to write to the file.
 * @param   {bool}     [append=false]        Whether to append to the file.
 */
$.oFile.prototype.write = function(content, append){
    if (typeof append === 'undefined') var append = false

    var file = new File(this.path);
    try {
        if (append){
            file.open(FileAccess.Append);
        }else{
            file.open(FileAccess.WriteOnly);
        }
        file.write(content);
        file.close();
        return true
    } catch (err) {return false;}
}


/**
 * Moves the file to the specified path.
 * @param   {string}   folder                  destination folder for the file.
 * @param   {bool}     [overwrite=false]       Whether to overwrite the file.
 *
 * @return: { bool }                           The result of the move.
 */
$.oFile.prototype.move = function( newPath, overwrite ){
  if (typeof overwrite === 'undefined') var overwrite = false;

  if(newPath instanceof this.$.oFile) newPath = newPath.path;

  var _file = new PermanentFile(this.path);
  var _dest = new PermanentFile(newPath);
  // this.$.alert("moving "+_file.path()+" to "+_dest.path()+" exists?"+_dest.exists())

  if (_dest.exists()){
    if (!overwrite){
      this.$.debug("destination file "+newPath+" exists and will not be overwritten. Can't move file.", this.$.DEBUG_LEVEL.ERROR);
      return false;
    }else{
      _dest.remove()
    }
  }

  var success = _file.move(_dest);
  // this.$.alert(success)
  if (success) {
    this.path = _dest.path()
    return this;
  }
  return false;
}


 /**
 * Moves the file to the folder.
 * @param   {string}   folder                  destination folder for the file.
 * @param   {bool}     [overwrite=false]       Whether to overwrite the file.
 *
 * @return: { bool }                           The result of the move.
 */
$.oFile.prototype.moveToFolder = function( folder, overwrite ){
  if (folder instanceof this.$.oFolder) folder = folder.path;
  var _fileName = this.fullName;

  return this.move(folder+"/"+_fileName, overwrite)
}


 /**
 * Renames the file.
 * @param   {string}   newName                 the new name for the file, without the extension.
 * @param   {bool}     [overwrite=false]       Whether to replace a file of the same name if it exists in the folder.
 *
 * @return: { bool }                           The result of the renaming.
 */
$.oFile.prototype.rename = function( newName, overwrite){
  if (newName == this.name) return true;
  if (this.extension != "") newName += "."+this.extension;
  return this.move(this.folder.path+"/"+newName, overwrite);
}



/**
 * Copies the file to the folder.
 * @param   {string}   [folder]                Content to write to the file.
 * @param   {string}   [copyName]              Name of the copied file without the extension. If not specified, the copy will keep its name unless another file is present in which case it will be called "_copy"
 * @param   {bool}     [overwrite=false]       Whether to overwrite the file.
 *
 * @return: { bool }                           The result of the copy.
 */
$.oFile.prototype.copy = function( destfolder, copyName, overwrite){
    if (typeof overwrite === 'undefined') var overwrite = false;
    if (typeof copyName === 'undefined') var copyName = this.name;
    if (typeof destfolder === 'undefined') var destfolder = this.folder.path;

    var _fileName = this.fullName;
    if(destfolder instanceof this.$.oFolder) destfolder = destfolder.path;

    // remove extension from name in case user added it to the param
    copyName.replace ("."+this.extension, "");
    if (this.name == copyName && destfolder == this.folder.path) copyName += "_copy";

    var _fileName = copyName+((this.extension.length>0)?"."+this.extension:"");

    var _file = new PermanentFile(this.path);
    var _dest = new PermanentFile(destfolder+"/"+_fileName);

    if (_dest.exists() && !overwrite){
        throw new Error("Destination file "+destfolder+"/"+_fileName+" exists and will not be overwritten. Can't copy file.", this.DEBUG_LEVEL.ERROR);
    }

    this.$.debug("copying "+_file.path()+" to "+_dest.path(), this.$.DEBUG_LEVEL.LOG)

    var success = _file.copy(_dest);
    if (!success) throw new Error ("Copy of file "+_file.path()+" to location "+_dest.path()+" has failed.", this.$.DEBUG_LEVEL.ERROR)

    return new this.$.oFile(_dest.path());
}


/**
 * Removes the file.
 * @return: { bool }                           The result of the removal.
 */
$.oFile.prototype.remove = function(){
    var _file = new PermanentFile(this.path)
    if (_file.exists()) return _file.remove()
}



/**
 * Parses the file as a XML and returns an object containing the values.
 * @example
 * // parses the xml file as an object with imbricated hierarchy.
 * // each xml node is represented by a simple object with a "children" property containing the children nodes,
 * // and a objectName property representing the name of the node.
 * // If the node has attributes, those are set as properties on the object. All values are set as strings.
 *
 * // example: parsing the shortcuts file
 *
 * var shortcutsFile = (new $.oFile(specialFolders.userConfig+"/shortcuts.xml")).parseAsXml();
 *
 * // The returned object will always be a simple document object with a single "children" property containing the document nodes.
 *
 * var shortcuts = shortcuts.children[0].children     // children[0] is the "shortcuts" parent node, we want the nodes contained within
 *
 * for (var i in shortcuts){
 *   log (shortcuts[i].id)
 * }
 */
$.oFile.prototype.parseAsXml = function(){
  if (this.extension.toLowerCase() != "xml") return

  // build an object model representation of the contents of the XML by parsing it character by character
  var xml = this.read();
  var xmlDocument = new this.$.oXml(xml);
  return xmlDocument;
}


 /**
 * Used in converting the file to a string value, provides the string-path.
 * @return  {string}   The file path's as a string.
 */
$.oFile.prototype.toString = function(){
    return this.path;
}




//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//           $.oXml class           //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oXml class.
 * @classdesc
 * The $.oXml class can be used to create an object from a xml string. It will contain a "children" property which is an array that holds all the children node from the main document.
 * @constructor
 * @param {string}     xmlString           the string to parse for xml content
 * @param {string}     objectName          "xmlDocument" for the top node, otherwise, the string description of the xml node (ex: <objectName> <property = "value"/> </objectName>)
 * @property {string}  objectName
 * @property {$.oXml[]}  children
 */
$.oXml = function (xmlString, objectName){
  if (typeof objectName === 'undefined') var objectName = "xmlDocument";
  this.objectName = objectName;
  this.children = [];

  var string = xmlString+"";

  // matches children xml nodes, multiline or single line, and provides one group for the objectName and one for the insides to parse again.
  var objectRE = /<(\w+)[ >?]([\S\s]+?\/\1|[^<]+?\/)>/igm
  var match;
  while (match = objectRE.exec(xmlString)){
    this.children.push(new this.$.oXml(match[2], match[1]));
    // remove the match from the string to parse the rest as properties
    string = string.replace(match[0], "");
  }

  // matches a line with name="property"
  var propertyRE = /(\w+)="([^\=\<\>]+?)"/igm
  var match;
  while (match = propertyRE.exec(string)){
    // set the property on the object
    this[match[1]] = match[2];
  }
}
