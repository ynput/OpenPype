/*jslint vars: true, plusplus: true, devel: true, nomen: true, regexp: true,
indent: 4, maxerr: 50 */
/*global $, Folder*/
#include "../js/libs/json.js";

/* All public API function should return JSON! */

app.preferences.savePrefAsBool("General Section", "Show Welcome Screen", false) ;

if(!Array.prototype.indexOf) {
    Array.prototype.indexOf = function ( item ) {
        var index = 0, length = this.length;
        for ( ; index < length; index++ ) {
                  if ( this[index] === item )
                        return index;
        }
        return -1;
        };
}

function sayHello(){
    alert("hello from ExtendScript");
}

function getEnv(variable){
    return $.getenv(variable);
}

function getMetadata(){
    /**
     *  Returns payload in 'Label' field of project's metadata
     * 
     **/
    if (ExternalObject.AdobeXMPScript === undefined){
        ExternalObject.AdobeXMPScript =
            new ExternalObject('lib:AdobeXMPScript');
    }
    
    var proj = app.project;
    var meta = new XMPMeta(app.project.xmpPacket);
    var schemaNS = XMPMeta.getNamespaceURI("xmp");
    var label = "xmp:Label";

    if (meta.doesPropertyExist(schemaNS, label)){
        var prop = meta.getProperty(schemaNS, label);
        return prop.value;
    }

    return _prepareSingleValue([]);

}

function imprint(payload){
    /**
     * Stores payload in 'Label' field of project's metadata
     * 
     * Args:
     *     payload (string): json content
     */
    if (ExternalObject.AdobeXMPScript === undefined){
        ExternalObject.AdobeXMPScript =
            new ExternalObject('lib:AdobeXMPScript');
    }
    
    var proj = app.project;
    var meta = new XMPMeta(app.project.xmpPacket);
    var schemaNS = XMPMeta.getNamespaceURI("xmp");
    var label = "xmp:Label";

    meta.setProperty(schemaNS, label, payload);
    
    app.project.xmpPacket = meta.serialize();

}


function fileOpen(path){
    /**
     * Opens (project) file on 'path'
     */
    fp = new File(path);
    return _prepareSingleValue(app.open(fp))
}

function getActiveDocumentName(){
    /**
     *   Returns file name of active document
     * */
    var file = app.project.file;

    if (file){
        return _prepareSingleValue(file.name)
    }

    return _prepareError("No file open currently");
}

function getActiveDocumentFullName(){
    /**
     *   Returns absolute path to current project
     * */
    var file = app.project.file;

    if (file){
        var f = new File(file.fullName);
        var path = f.fsName;
        f.close();

        return _prepareSingleValue(path)
    }

    return _prepareError("No file open currently");
}

function getItems(comps, folders, footages){
    /**
     * Returns JSON representation of compositions and
     * if 'collectLayers' then layers in comps too.
     * 
     * Args:
     *     comps (bool): return selected compositions
     *     folders (bool): return folders
     *     footages (bool): return FootageItem
     * Returns:
     *     (list) of JSON items
     */    
    var items = []
    for (i = 1; i <= app.project.items.length; ++i){
        var item = app.project.items[i];
        if (!item){
            continue;
        }
        var ret = _getItem(item, comps, folders, footages);
        if (ret){
            items.push(ret);
        }
    }
    return '[' + items.join() + ']';

}

function getSelectedItems(comps, folders, footages){
    /**
     * Returns list of selected items from Project menu
     * 
     * Args:
     *     comps (bool): return selected compositions
     *     folders (bool): return folders
     *     footages (bool): return FootageItem
     * Returns:
     *     (list) of JSON items
     */    
    var items = []
    for (i = 0; i < app.project.selection.length; ++i){
        var item = app.project.selection[i];
        if (!item){
            continue;
        }
        var ret = _getItem(item, comps, folders, footages);
        if (ret){
            items.push(ret);
        }
    }
    return '[' + items.join() + ']';
}

function _getItem(item, comps, folders, footages){
    /**
     * Auxiliary function as project items and selections 
     * are indexed in different way :/
     * Refactor 
     */
    var item_type = '';
    if (item instanceof FolderItem){
        item_type = 'folder';
        if (!folders){
            return "{}";
        }
    }
    if (item instanceof FootageItem){
        item_type = 'footage';
        if (!footages){
            return "{}";
        }
    }
    if (item instanceof CompItem){
        item_type = 'comp';
        if (!comps){
            return "{}";
        }
    }
        
    var item = {"name": item.name,
                "id": item.id,
                "type": item_type};
    return JSON.stringify(item);
}

function importFile(path, item_name, import_options){
    /**
     * Imports file (image tested for now) as a FootageItem.
     * Creates new composition
     * 
     * Args:
     *    path (string): absolute path to image file
     *    item_name (string): label for composition
     * Returns:
     *    JSON {name, id}
     */
    var comp;
    var ret = {};
    try{
        import_options = JSON.parse(import_options);
    } catch (e){
        return _prepareError("Couldn't parse import options " + import_options);
    }

    app.beginUndoGroup("Import File");
    fp = new File(path);
    if (fp.exists){
        try { 
            im_opt = new ImportOptions(fp);
            importAsType = import_options["ImportAsType"];

            if ('ImportAsType' in import_options){ // refactor
                if (importAsType.indexOf('COMP') > 0){
                    im_opt.importAs = ImportAsType.COMP;
                }
                if (importAsType.indexOf('FOOTAGE') > 0){
                    im_opt.importAs = ImportAsType.FOOTAGE;
                }
                if (importAsType.indexOf('COMP_CROPPED_LAYERS') > 0){
                    im_opt.importAs = ImportAsType.COMP_CROPPED_LAYERS;
                }
                if (importAsType.indexOf('PROJECT') > 0){
                    im_opt.importAs = ImportAsType.PROJECT;
                }  
                             
            }
            if ('sequence' in import_options){
                im_opt.sequence = true;
            }
            
            comp = app.project.importFile(im_opt);

            if (app.project.selection.length == 2 &&
                app.project.selection[0] instanceof FolderItem){
                 comp.parentFolder = app.project.selection[0]   
            }
        } catch (error) {
            return _prepareError(error.toString() + importOptions.file.fsName);
        } finally {
            fp.close();
        }
    }else{
	    return _prepareError("File " + path + " not found.");
    }
    if (comp){
        comp.name = item_name;
        comp.label = 9; // Green
        ret = {"name": comp.name, "id": comp.id}
    }
    app.endUndoGroup();

    return JSON.stringify(ret);
}

function setLabelColor(comp_id, color_idx){
    /**
     * Set item_id label to 'color_idx' color
     * Args:
     *     item_id (int): item id
     *     color_idx (int): 0-16 index from Label
     */
    var item = app.project.itemByID(comp_id);
    if (item){
        item.label = color_idx;
    }else{
        return _prepareError("There is no composition with "+ comp_id);
    }
}

function replaceItem(comp_id, path, item_name){
    /**
     * Replaces loaded file with new file and updates name
     * 
     * Args:
     *    comp_id (int): id of composition, not a index!
     *    path (string): absolute path to new file
     *    item_name (string): new composition name
     */
    app.beginUndoGroup("Replace File");
    
    fp = new File(path);
    if (!fp.exists){
        return _prepareError("File " + path + " not found.");
    }
    var item = app.project.itemByID(comp_id);
    if (item){
        try{
            if (isFileSequence(item)) {
                item.replaceWithSequence(fp, false);
            }else{
                item.replace(fp);
            }
            
            item.name = item_name;
        } catch (error) {
            return _prepareError(error.toString() + path);
        } finally {
            fp.close();
        }
    }else{
        return _prepareError("There is no composition with "+ comp_id);
    }
    app.endUndoGroup();
}

function renameItem(item_id, new_name){
    /**
     * Renames item with 'item_id' to 'new_name'
     * 
     * Args:
     *    item_id (int): id to search item
     *    new_name (str)
     */
    var item = app.project.itemByID(item_id);
    if (item){
        item.name = new_name;
    }else{
        return _prepareError("There is no composition with "+ comp_id);
    }
}

function deleteItem(item_id){
    /**
     *  Delete any 'item_id'
     * 
     *  Not restricted only to comp, it could delete
     *  any item with 'id'
     */
    var item = app.project.itemByID(item_id);
    if (item){
        item.remove();
    }else{
        return _prepareError("There is no composition with "+ comp_id);
    }
}

function getWorkArea(comp_id){
    /**
     * Returns information about workarea - are that will be
     * rendered. All calculation will be done in OpenPype,
     * easier to modify without redeploy of extension.
     * 
     * Returns
     *     (dict)
     */
    var item = app.project.itemByID(comp_id);
    if (item){
        return JSON.stringify({
            "workAreaStart": item.displayStartFrame, 
            "workAreaDuration": item.duration,
            "frameRate": item.frameRate});
    }else{
        return _prepareError("There is no composition with "+ comp_id);
    }
}

function setWorkArea(comp_id, workAreaStart, workAreaDuration, frameRate){
    /**
     * Sets work area info from outside (from Ftrack via OpenPype)
     */
    var item = app.project.itemByID(comp_id);
    if (item){
        item.displayStartTime = workAreaStart;
        item.duration = workAreaDuration;
        item.frameRate = frameRate;
    }else{
        return _prepareError("There is no composition with "+ comp_id);
    }
}

function save(){
    /**
     * Saves current project
     */
    app.project.save();  //TODO path is wrong, File instead
}

function saveAs(path){
    /**
     *   Saves current project as 'path'
     * */
    app.project.save(fp = new File(path));
}

function getRenderInfo(){
    /***
        Get info from render queue.
        Currently pulls only file name to parse extension and 
        if it is sequence in Python
    **/
    try{
        var render_item = app.project.renderQueue.item(1);
        if (render_item.status == RQItemStatus.DONE){
            render_item.duplicate();  // create new, cannot change status if DONE
            render_item.remove();  // remove existing to limit duplications
            render_item = app.project.renderQueue.item(1);
        }

        render_item.render = true; // always set render queue to render
        var item = render_item.outputModule(1);
    } catch (error) {
        return _prepareError("There is no render queue, create one");
    }
    var file_url = item.file.toString();

    return JSON.stringify({
        "file_name": file_url            
    })
}

function getAudioUrlForComp(comp_id){
    /**
     * Searches composition for audio layer
     * 
     * Only single AVLayer is expected!
     * Used for collecting Audio
     * 
     * Args:
     *    comp_id (int): id of composition
     * Return:
     *    (str) with url to audio content
     */
    var item = app.project.itemByID(comp_id);
    if (item){
        for (i = 1; i <= item.numLayers; ++i){
            var layer = item.layers[i];
            if (layer instanceof AVLayer){
                if (layer.hasAudio){
                    source_url = layer.source.file.fsName.toString()
                    return _prepareSingleValue(source_url);
                }
            }

        }
    }else{
        return _prepareError("There is no composition with "+ comp_id);
    }

}

function addItemAsLayerToComp(comp_id, item_id, found_comp){
    /**
     * Adds already imported FootageItem ('item_id') as a new
     * layer to composition ('comp_id').
     * 
     * Args:
     *  comp_id (int): id of target composition
     *  item_id (int): FootageItem.id
     *  found_comp (CompItem, optional): to limit quering if
     *      comp already found previously
     */
    var comp = found_comp || app.project.itemByID(comp_id);
    if (comp){
        item = app.project.itemByID(item_id);
        if (item){
            comp.layers.add(item);
        }else{
            return _prepareError("There is no item with " + item_id);
        }
    }else{
        return _prepareError("There is no composition with "+ comp_id);
    }
}

function importBackground(comp_id, composition_name, files_to_import){
    /**
     * Imports backgrounds images to existing or new composition.
     * 
     * If comp_id is not provided, new composition is created, basic
     * values (width, heights, frameRatio) takes from first imported
     * image.
     * 
     * Args:
     *   comp_id (int): id of existing composition (null if new)
     *   composition_name (str): used when new composition 
     *   files_to_import (list): list of absolute paths to import and
     *      add as layers
     * 
     * Returns:
     *  (str): json representation (id, name, members)
     */
    var comp;
    var folder;
    var imported_ids = [];
    if (comp_id){
        comp = app.project.itemByID(comp_id);
        folder = comp.parentFolder;
    }else{
        if (app.project.selection.length > 1){
            return _prepareError(
                "Too many items selected, select only target composition!");
        }else{
            selected_item = app.project.activeItem;
            if (selected_item instanceof Folder){
                comp = selected_item;
                folder = selected_item;
            }
        }
    }
       
    if (files_to_import){
        for (i = 0; i < files_to_import.length; ++i){
            item = _importItem(files_to_import[i]);
            if (!item){
                return _prepareError(
                    "No item for " + item_json["id"] +
                    ". Import background failed.")
            }
            if (!comp){
                folder = app.project.items.addFolder(composition_name);
                imported_ids.push(folder.id);
                comp = app.project.items.addComp(composition_name, item.width, 
                    item.height, item.pixelAspect, 
                    1, 26.7);  // hardcode defaults
                imported_ids.push(comp.id);
                comp.parentFolder = folder;
            }
            imported_ids.push(item.id)
            item.parentFolder = folder;

            addItemAsLayerToComp(comp.id, item.id, comp);
        }       
    }
    var item = {"name": comp.name,
                "id": folder.id,
                "members": imported_ids};
    return JSON.stringify(item);
}

function reloadBackground(comp_id, composition_name, files_to_import){
    /**
     * Reloads existing composition.
     * 
     * It deletes complete composition with encompassing folder, recreates
     * from scratch via 'importBackground' functionality.
     * 
     * Args:
     *   comp_id (int): id of existing composition (null if new)
     *   composition_name (str): used when new composition 
     *   files_to_import (list): list of absolute paths to import and
     *      add as layers
     * 
     * Returns:
     *  (str): json representation (id, name, members)
     * 
     */
    var imported_ids = []; // keep track of members of composition
    comp = app.project.itemByID(comp_id);
    folder = comp.parentFolder;
    if (folder){
        renameItem(folder.id, composition_name);
        imported_ids.push(folder.id);
    }
    if (comp){
        renameItem(comp.id, composition_name);
        imported_ids.push(comp.id);
    }

    var existing_layer_names = [];
    var existing_layer_ids = []; // because ExtendedScript doesnt have keys()
    for (i = 1; i <= folder.items.length; ++i){
        layer = folder.items[i];
        //because comp.layers[i] doesnt have 'id' accessible
        if (layer instanceof CompItem){
            continue;
        }
        existing_layer_names.push(layer.name);
        existing_layer_ids.push(layer.id);
    }

    var new_filenames = [];
    if (files_to_import){
        for (i = 0; i < files_to_import.length; ++i){
            file_name = _get_file_name(files_to_import[i]);
            new_filenames.push(file_name);

            idx = existing_layer_names.indexOf(file_name);
            if (idx >= 0){  // update
                var layer_id = existing_layer_ids[idx];
                replaceItem(layer_id, files_to_import[i], file_name);
                imported_ids.push(layer_id);
            }else{ // new layer
                item = _importItem(files_to_import[i]);
                if (!item){
                    return _prepareError(
                        "No item for " + files_to_import[i] +
                        ". Reload background failed.");
                }
                imported_ids.push(item.id);
                item.parentFolder = folder;
                addItemAsLayerToComp(comp.id, item.id, comp);
            }
        }
    }

    _delete_obsolete_items(folder, new_filenames);

    var item = {"name": comp.name,
                "id": folder.id,
                "members": imported_ids};

    return JSON.stringify(item);
}

function _get_file_name(file_url){
    /**
     * Returns file name without extension from 'file_url'
     * 
     * Args:
     *    file_url (str): full absolute url
     * Returns:
     *    (str)
     */
    fp = new File(file_url);
    file_name = fp.name.substring(0, fp.name.lastIndexOf("."));
    return file_name;
}

function _delete_obsolete_items(folder, new_filenames){
    /***
     * Goes through 'folder' and removes layers not in new
     * background
     * 
     * Args:
     *   folder (FolderItem)
     *   new_filenames (array): list of layer names in new bg
     */
    // remove items in old, but not in new
    delete_ids = []
    for (i = 1; i <= folder.items.length; ++i){
        layer = folder.items[i];
        //because comp.layers[i] doesnt have 'id' accessible
        if (layer instanceof CompItem){
            continue;
        }
        if (new_filenames.indexOf(layer.name) < 0){
            delete_ids.push(layer.id);
        }
    }
    for (i = 0; i < delete_ids.length; ++i){
        deleteItem(delete_ids[i]);
    }
}

function _importItem(file_url){
    /**
     * Imports 'file_url' as new FootageItem
     * 
     * Args:
     *    file_url (str): file url with content
     * Returns:
     *    (FootageItem)
     */
    file_name = _get_file_name(file_url);
    
    //importFile prepared previously to return json
    item_json = importFile(file_url, file_name, JSON.stringify({"ImportAsType":"FOOTAGE"}));
    item_json = JSON.parse(item_json);
    item = app.project.itemByID(item_json["id"]);

    return item;
}

function isFileSequence (item){
    /**
     * Check that item is a recognizable sequence
     */
    if (item instanceof FootageItem && item.mainSource instanceof FileSource && !(item.mainSource.isStill) && item.hasVideo){
        var extname = item.mainSource.file.fsName.split('.').pop();

        return extname.match(new RegExp("(ai|bmp|bw|cin|cr2|crw|dcr|dng|dib|dpx|eps|erf|exr|gif|hdr|ico|icb|iff|jpe|jpeg|jpg|mos|mrw|nef|orf|pbm|pef|pct|pcx|pdf|pic|pict|png|ps|psd|pxr|raf|raw|rgb|rgbe|rla|rle|rpf|sgi|srf|tdi|tga|tif|tiff|vda|vst|x3f|xyze)", "i")) !== null;
    }

    return false;
}

function render(target_folder){
    var out_dir = new Folder(target_folder);
    var out_dir = out_dir.fsName;
    for (i = 1; i <= app.project.renderQueue.numItems; ++i){
        var render_item = app.project.renderQueue.item(i);
        var om1 = app.project.renderQueue.item(i).outputModule(1);
        var file_name = File.decode( om1.file.name ).replace('℗', ''); // Name contains special character, space?
        
        var omItem1_settable_str = app.project.renderQueue.item(i).outputModule(1).getSettings( GetSettingsFormat.STRING_SETTABLE );

        if (render_item.status == RQItemStatus.DONE){
            render_item.duplicate();
            render_item.remove();
            continue;
        }

        var targetFolder = new Folder(target_folder);
        if (!targetFolder.exists) {
          targetFolder.create();
        }

        om1.file = new File(targetFolder.fsName + '/' + file_name);
    }
    app.project.renderQueue.render();
}

function close(){
    app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
    app.quit();
}

function getAppVersion(){
    return _prepareSingleValue(app.version);
}

function _prepareSingleValue(value){
    return JSON.stringify({"result": value})
}
function _prepareError(error_msg){
    return JSON.stringify({"error": error_msg})
}
