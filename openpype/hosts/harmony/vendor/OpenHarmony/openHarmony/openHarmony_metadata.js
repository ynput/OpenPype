//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////
//
//                            openHarmony Library v0.01
//
//
//         Developped by Mathieu Chaptel, Chris Fourney...
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
//   This library is made available under the MIT license.
//   https://opensource.org/licenses/mit
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
//        $.oMetadata class         //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.oMetadata class.
 * @classdesc  Provides access to getting/setting metadata as an object interface.<br>Given a node as a source, will use provide the metadata associated to that node, 
 * otherwise provides metadata for the scene.
 * @param   {$.oNode}                 source            A node as the source of the metadata-- otherwise provides the scene metadata.
 * @todo Need to extend this to allow node metadata.
 * @constructor
 * @example
 * var metadata = $.scene.getMetadata();
 * metadata.create( "mySceneMetadataName", {"ref":"thisReferenceValue"} );
 * metadata["mySceneMetadataName"]; //Provides: {"ref":"thisReferenceValue"}
 */
$.oMetadata = function( source ){
  this._type             = "metadata";
  if( !source ){ source = 'scene'; }
  this.source = source;
  
  this._metadatas = {};
  
  this.refresh();
}


/**
 * Refreshes the preferences by re-reading the preference file and ingesting their values appropriately. They are then available as properties of this class.<br>
 * <b>Note, any new preferences will not be available as properties until Harmony saves the preference file at exit. In order to reference new preferences, use the get function.
 * @name $.oMetadata#refresh
 * @function
 */
$.oMetadata.prototype.refresh = function(){
  
  //----------------------------
  //GETTER/SETTERS
  var set_val = function( meta, name, val ){
    var metadata = meta._metadatas[ name ];
    
    var valtype = false;
    var jsonify = false;
    switch( typeof val ){
      case 'string':
        valtype = 'string';
        break;
      case 'number':
        if( val%1.0==0.0 ){
          valtype = 'int';
        }else{
          valtype = 'double';
        }
        break
      case 'boolean':
      case 'undefined':
      case 'null':
        valtype = 'bool';
        break
      case 'object':
      default:
        valtype = 'string';
        jsonify = true;
        break
    }
    
    if(jsonify){
      val = 'json('+JSON.stringify( val )+')';
    }
    
    if( meta.source == "scene" ){
      var type = false;
      scene.setMetadata( {
                           "name"       : name,
                           "type"       : valtype,
                           "creator"    : "OpenHarmony",
                           "version"    : "1.0",
                           "value"      : val
                         }
                       );
    }else{
      var metaAttr = this.source.attributes["meta"];
      if( metaAttr ){
        metaAttr[ name ] = val;
      }
    }
    
    meta.refresh();
  }
  
  var get_val = function( meta, name ){
    return meta._metadatas[name].value;
  }
  
  //Definition of properties.
  var getterSetter_create = function( targ, id, type, value ){
  
    if( type == "string" ){
      if( value.slice( 0, 5 ) == "json(" ){
          var obj = value.slice( 5, value.length-1 );
          value = JSON.parse( obj );
      }
    }
    targ._metadatas[ id ] = { "value": value, "type":type };
   
    //Create a getter/setter for it!
    Object.defineProperty( targ, id, {
      enumerable : true,
      configurable: true,
      set : eval( 'val = function(val){ set_val( targ, "'+id+'", val ); }' ),
      get : eval( 'val = function(){ return get_val( targ, "'+id+'"); }' )
    });
  }
  
  
  //Clear this objects previous getter/setters to make room for new ones.
  if( this._metadatas ){
    for( n in this._metadatas ){ //Remove them if they've disappeared.
        Object.defineProperty( this, n, {
          enumerable : false,
          configurable: true,
          set : function(){},
          get : function(){}
        });
    }
  }
  this._metadatas = {};

  if( this.source == "scene" ){
    var metadatas = scene.metadatas();
    
    for( var n=0;n<metadatas.length;n++ ){
      var metadata = metadatas[n];
      getterSetter_create( this, metadata.name.toLowerCase(), metadata.type, metadata.value );
    }
  }else{
    //createDynamicAttr (String node, String type, String attrName, String displayName, bool linkable)
    //var alist = node.getAttrList( this.source.name, 1, 'meta' );
    var metaAttr = this.source.attributes["meta"];
    if( metaAttr ){
      var subAttrs = metaAttr.subAttributes;
      if( subAttrs.length>0 ){
        for( var i=0;i<subAttrs.length;i++ ){
          getterSetter_create( this, subAttrs[i].shortKeyword.toLowerCase(), subAttrs[i].type, subAttrs[i].getValue(1) );
        }
      }
    }
    
  }
}


/**
 * Creates a new metadata based on name and value.<br>The metadata is created on the source to which this metadata object references.
 * @name $.oMetadata#create
 * @param   {string}                 name            The name of the new metadata to create.
 * @param   {object}                 val             The value of the new metadata created.
 */
$.oMetadata.prototype.create = function( name, val ){
  var name = name.toLowerCase();

  if( this[ name ] ){
    throw ReferenceError( "Metadata already exists by name: " + name );
  }
  
  var valtype = false;
  var jsonify = false;
  switch( typeof val ){
    case 'string':
      valtype = 'string';
      break;
    case 'number':
      if( val%1.0==0.0 ){
        valtype = 'int';
      }else{
        valtype = 'double';
      }
      break
    case 'boolean':
    case 'undefined':
    case 'null':
      valtype = 'bool';
      break
    case 'object':
    default:
      valtype = 'string';
      jsonify = true;
      break
  }
  
  if(jsonify){
    val = 'json('+JSON.stringify( val )+')';
  }
  
  if( this.source == "scene" ){
    scene.setMetadata( {
                         "name"       : name,
                         "type"       : valtype,
                         "creator"    : "OpenHarmony",
                         "version"    : "1.0",
                         "value"      : val
                       }
                     );
  }else{
    var attr = this.source.createAttribute( "meta."+name, valtype, valtype, false );
    if( attr ){ 
      attr.setValue( val, 1 ); 
    }
  }
  this.refresh();
}

/**
 * Removes a new metadata based on name and value.<br>The metadata is removed from the source to which this metadata object references.
 * @name $.oMetadata#remove
 * @param   {string}                 name            The name of the metadata to remove.
 */
$.oMetadata.prototype.remove = function( name ){
  var name = name.toLowerCase();
  if( !this.hasOwnProperty( name ) ){ return true; }
  
  var res = false;
  if( this.source == "scene" ){
    if( !scene.removeMetadata ){
      res = scene.removeMetadata( scene.metadata(name), this._metadatas[ name ].type );
    }else{
      throw ReferenceError( "This is supposed to exist, but doesn't seem to be available." );
    }
  }else{
    res = this.source.removeAttribute( "meta."+name );
  }
  
  this.refresh();
  return res;
}