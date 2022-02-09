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
//      $.oPreferences class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The constructor for the $.preferences class.
 * @classdesc  Provides access to getting/setting preferenes as an object interface.<br>All preferences that have been written to the file are accessible as properties of this class.<br>
 * Alternatively, new preferences can be retrieved with the .get function.
 * @constructor
 * @example
 * var pref = $.getPreferences();
 * pref.create( "MyNewPreferenceName", "MyPreferenceValue" );
 * pref["MyNewPreferenceName"];     // Provides: MyPreferenceValue
 * pref.get("MyNewPreferenceName"); // Provides: MyPreferenceValue
 */
$.oPreferences = function( ){
  this._type             = "preferences";
  this._addedPreferences = []

  this.refresh();
}


/**
 * Refreshes the preferences by re-reading the preference file and ingesting their values appropriately. They are then available as properties of this class.<br>
 * <b>Note, any new preferences will not be available as properties until Harmony saves the preference file at exit. In order to reference new preferences, use the get function.
 * @name $.oPreferences#refresh
 * @function
 */
$.oPreferences.prototype.refresh = function(){
  var fl = specialFolders.userConfig + "/Harmony Premium-pref.xml";
  var nfl = new this.$.oFile( fl );
  if( !nfl.exists ){
    System.println( "Unable to find preference file: " + fl );
    this.$.debug( "Unable to find preference file: " + fl, this.$.DEBUG_LEVEL.ERROR );
    return;
  }

  var xmlDom = new QDomDocument();
      xmlDom.setContent( nfl.read() );

  if( !xmlDom ){
    return;
  }

  var prefXML = xmlDom.elementsByTagName( "preferences" );
  if( prefXML.length() == 0 ){
    this.$.debug( "Unable to find preferences in file: " + fl, this.$.DEBUG_LEVEL.ERROR );
    return;
  }

  var XMLpreferences = prefXML.at(0);

  //Clear this objects previous getter/setters to make room for new ones.
  if( this._preferences ){
    for( n in this._preferences ){ //Remove them if they've disappeared.
        Object.defineProperty( this, n, {
          enumerable : false,
          configurable: true,
          set : function(){},
          get : function(){}
        });
    }
  }
  this._preferences = {};

  if( !XMLpreferences.hasChildNodes() ){
    this.$.debug( "Unable to find preferences in file: " + fl, this.$.DEBUG_LEVEL.ERROR );
    return;
  }

  //THE DEFAULT SETTER
  var set_val = function( pref, name, val ){
    var prefObj = pref._preferences[name];

    //Check against types, unable to set types differently.
    switch( typeof val ){
      case 'string':
        if( prefObj["type"] != "string" ){
          throw ReferenceError( "Harmony does not support preference type-changes. Preference must remain " + prefObj["type"] );
        }
        preferences.setString( name, val );
        break;
      case 'number':
        if( prefObj["type"] == "int" ){
          val = Math.floor( val );
          preferences.setInt( name, val );
        }else if( prefObj["type"] == "double" ){
          //This is fine.
          preferences.setDouble( name, val );
        }else{
          throw ReferenceError( "Harmony does not support preference type-changes. Preference must remain " + prefObj["type"] );
        }
        break
      case 'boolean':
      case 'undefined':
      case 'null':
        if( prefObj["type"] != "bool" ){
          throw ReferenceError( "Harmony does not support preference type-changes. Preference must remain " + prefObj["type"] );
        }
        preferences.setBool( name, val ? true:false );
        break
      case 'object':
      default:
        var set = false;
        try{
          if( val.r && val.g && val.b && val.a ){
            if( prefObj["type"] != "color" ){
              throw ReferenceError( "Harmony does not support preference type-changes. Preference must remain " + prefObj["type"] );
            }

            value = preferences.setColor( name, new ColorRGBA( val.r, val.g, val.b, val.a ) );
            set = true;
          }
        }catch(err){
        }

        if(!set){
          if( prefObj["type"] != "string" ){
            throw ReferenceError( "Harmony does not support preference type-changes. Preference must remain " + prefObj["type"] );
          }
          var json_val = 'json('+JSON.stringify( val )+')';
          preferences.setString( name, json_val );
        }
        break
    }

    {
      pref._preferences[name].value = val;
    }
  }

  //THE DEFAULT GETTER
  var get_val = function( pref, name ){
    return pref._preferences[name].value;
  }


  var getterSetter_create = function( targ, id, type ){
      switch( type ){
      case 'color':
        var tempVal = preferences.getColor( id, new ColorRGBA () );
        value = new $.oColorValue( tempVal.r, tempVal.g, tempVal.b, tempVal.a );
        break;
      case 'int':
        value = preferences.getInt( id, 0 );
        break
      case 'double':
        value = preferences.getDouble( id, 0.0 );
        break
      case 'bool':
        value = preferences.getBool( id, false );
        break
      case 'string':
        value = preferences.getString( id, "unknown" );
        if( value.slice( 0, 5 ) == "json(" ){
          var obj = value.slice( 5, value.length-1 );
          value = JSON.parse( obj );
        }
        break
      default:
        break;
    }
    if( value === null ) return;

    targ._preferences[ id ] = { "value": value, "type":type };

    //Create a getter/setter for it!
    Object.defineProperty( targ, id, {
      enumerable : true,
      configurable: true,
      set : eval( 'val = function(val){ set_val( targ, "'+id+'", val ); }' ),
      get : eval( 'val = function(){ return get_val( targ, "'+id+'"); }' )
    });
  }


  //Get all the children preferences.
  var childNodes = XMLpreferences.childNodes();
  for( var cn=0;cn<childNodes.length();cn++ ){
    try{
      var thisChild = childNodes.at( cn );
      if (thisChild.isElement()){
        var e = thisChild.toElement();
        var type = e.tagName();
        var id   = e.attribute( "id", "null" );

        if( id == "null" ){ continue; }

        var value = null;

        getterSetter_create( this, id, type );
      }
    }catch( err ){
      //Internal error, skip it.
      System.println( err );
    }
  }

  for( var n=0;n<this._addedPreferences.length;n++ ){
    var pref = this._addedPreferences[n];
    var id   = pref["name"];
    var type = pref["type"];

    getterSetter_create( this, id, type );
  }

}


/**
 * Creates a new preferences based on name and value.<br><b>Note- A new preference isn't actively written into the Harmony's preference file until created and the application closed. Use preference.get for newly created preferences.</b>
 * @name $.oPreferences#create
 * @param   {string}                 name            The name of the new preference to create.
 * @param   {object}                 val             The value of the new preference created.
 */
$.oPreferences.prototype.create = function( name, val ){
  if( this[ name ] ){
    throw ReferenceError( "Preference already exists by name: " + name );
  }

  var type = '';
  //Check against types, unable to set types differently.
  switch( typeof val ){
    case 'string':
      type = 'string';
      preferences.setString( name, val );
      break;
    case 'number':
      type = 'double';
      preferences.setDouble( name, val );
      break
    case 'boolean':
    case 'undefined':
    case 'null':
      type = 'bool';
      preferences.setBool( name, val ? true:false );
      break
    case 'object':
    default:
      var set = false;
      try{
        if( val.r && val.g && val.b && val.a ){
          type = 'color';
          value = preferences.setColor( name, new ColorRGBA( val.r, val.g, val.b, val.a ) );
          set = true;
        }
      }catch(err){
      }

      if(!set){
        type = 'string';
        var json_val = 'json('+JSON.stringify( val )+')';
        preferences.setString( name, json_val );
      }
      break
  }

  this._addedPreferences.push( {"type":type, "name":name } );
  this.refresh();
}


/**
 * Retrieves a preference and attempts to identify its type automatically.<br>This is generally useful for accessing newly created preferences that have not been written to disk.
 * @name $.oPreferences#get
 * @param   {string}                 name            The name of the preference to retrieve.
 * @example
 * var pref = $.getPreferences();
 * pref.create( "MyNewPreferenceName", "MyPreferenceValue" );
 * //This new preference won't be available in the file until Harmony closes.
 * //So if preferences are reinstantiated, it won't be readily available -- but it can still be retrieved with get.
 *
 * var pref2 = $.getPreferences();
 * pref["MyNewPreferenceName"];     // Provides: undefined -- its not in the Harmony preference file.
 * pref.get("MyNewPreferenceName"); // Provides: MyPreferenceValue, its still available
 */
$.oPreferences.prototype.get = function( name ){
  if( this[name] ){
    return this[name];
  }

  var testTime   = (new Date()).getTime();
  var doubleExist = preferences.getDouble( name, testTime );
  if( doubleExist!= testTime ){
    this._addedPreferences.push( {"type":'double', "name":name } );
    this.refresh();

    return doubleExist;
  }

  var intExist = preferences.getInt( name, testTime );
  if( intExist!= testTime ){
    this._addedPreferences.push( {"type":'int', "name":name } );
    this.refresh();

    return intExist;
  }


  var colorExist = preferences.getColor( name, new ColorRGBA(1,2,3,4) );
  if( !( (colorExist.r==1) && (colorExist.g==2) && (colorExist.b==3) && (colorExist.a==4) ) ){
    this._addedPreferences.push( {"type":'color', "name":name } );
    this.refresh();

    return colorExist;
  }

  var stringExist = preferences.getString( name, "doesntExist" );
  if( stringExist != "doesntExist" ){
    this._addedPreferences.push( {"type":'color', "name":name } );
    this.refresh();

    return this[name];
  }

  return preferences.getBool( name, false );
}


//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//       $.oPreference class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * The constructor for the oPreference Class.
 * @classdesc
 * The oPreference class wraps a single preference item.
 * @constructor
 * @param {string} category             The category of the preference
 * @param {string} keyword              The keyword used by the preference
 * @param {string} type                 The type of value held by the preference
 * @param {string} description          A short string of description
 * @param {string} descriptionText      The complete tooltip text for the preference
 * @example
 * // To access the preferences of Harmony, grab the preference object in the $.oApp class:
 * var prefs = $.app.preferences;
 *
 * // It's then possible to access all available preferences of the software:
 * for (var i in prefs){
 *   log (i+" "+prefs[i]);
 * }
 *
 * // accessing the preference value can be done directly by using the dot notation:
 * prefs.USE_OVERLAY_UNDERLAY_ART = true;
 * log (prefs.USE_OVERLAY_UNDERLAY_ART);
 *
 * //the details objects of the preferences object allows access to more information about each preference
 * var details = prefs.details
 * log(details.USE_OVERLAY_UNDERLAY_ART.category+" "+details.USE_OVERLAY_UNDERLAY_ART.id+" "+details.USE_OVERLAY_UNDERLAY_ART.type);
 *
 * for (var i in details){
 *   log(i+" "+JSON.stringify(details[i]))       // each object inside detail is a complete oPreference instance
 * }
 *
 * // the preference object also holds a categories array with the list of all categories
 * log (prefs.categories)
 */
$.oPreference = function(category, keyword, type, value, description, descriptionText){
  this.category = category;
  this.keyword = keyword;
  this.type = type;
  this.description = description;
  this.descriptionText = descriptionText;
  this.defaultValue = value;
}


/**
 * get and set a preference value
 * @name $.oPreference#value
 */
Object.defineProperty ($.oPreference.prototype, 'value', {
  get: function(){
    try{
      switch(this.type){
        case "bool":
          var _value = preferences.getBool(this.keyword, this.defaultValue);
          break
        case "int":
          var _value = preferences.getInt(this.keyword, this.defaultValue);
          break;
        case "double":
          var _value = preferences.getDouble(this.keyword, this.defaultValue);
          break;
        case "color":
          var _value = preferences.getColor(this.keyword, this.defaultValue);
          _value = new this.$.oColorValue(_value.r, _value.g, _value.b, _value.a)
          break;
        default:
          var _value = preferences.getString(this.keyword, this.defaultValue);
      }
    }catch(err){
      this.$.debug(err, this.$.DEBUG_LEVEL.ERROR)
    }
    this.$.debug("Getting value of Preference "+this.keyword+" : "+_value, this.$.DEBUG_LEVEL.LOG)
    return _value;
  },

  set : function(newValue){
    switch(this.type){
      case "bool":
        preferences.setBool(this.keyword, newValue);
        break
      case "int":
        preferences.setInt(this.keyword, newValue);
        break;
      case "double":
        preferences.setDouble(this.keyword, newValue);
        break;
      case "color":
        if (typeof newValue == String) newValue = (new oColorValue()).fromColorString(newValue);
        preferences.setColor(this.keyword, new ColorRGBA(newValue.r, newValue.g, newValue.b, newValue.a));
        break;
      default:
        preferences.setString(this.keyword, newValue);
    }
    this.$.debug("Preference "+this.keyword+" was set to : "+newValue, this.$.DEBUG_LEVEL.LOG)
  }
})


/**
 * Creates getter setters on a simple object for the preference described by the params
 * @private
 * @param {string} category             The category of the preference
 * @param {string} keyword              The keyword used by the preference
 * @param {string} type                 The type of value held by the preference
 * @param {string} description          A short string of description
 * @param {string} descriptionText      The complete tooltip text for the preference
 * @param {Object} prefObject           The preference object that will receive the getter setter property (usually $.oApp._prefObject)
 */
$.oPreference.createPreference = function(category, keyword, type, value, description, descriptionText, prefObject){
  if (!prefObject.details.hasOwnProperty(keyword)){
    var pref = new $.oPreference(category, keyword, type, value, description, descriptionText);
    Object.defineProperty(prefObject, keyword,{
      enumerable: true,
      get : function(){
        return pref.value;
      },
      set : function(newValue){
        pref.value = newValue;
      }
    })
  }else{
    var pref = prefObject.details[keyword]
  }

  return pref;
}