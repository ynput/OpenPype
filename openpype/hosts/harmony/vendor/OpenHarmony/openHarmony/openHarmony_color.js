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
//        $.oColorValue class       //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////

/**
 * This class holds a color value. It can be used to set color attributes to a specific value and to convert colors between different formats such as hex strings, RGBA decompositions, as well as HSL values.
 * @constructor
 * @classdesc  Constructor for the $.oColorValue Class.
 * @param   {string/object}            colorValue            Hex string value, or object in form {rgba}
 *
 * @property {int}                    r                      The int value of the red component.
 * @property {int}                    g                      The int value of the green component.
 * @property {int}                    b                      The int value of the blue component.
 * @property {int}                    a                      The int value of the alpha component.
 * @example
 * // initialise the class to start setting up attributes and making conversions by creating a new instance
 *
 * var myColor = new $.oColorValue("#336600ff");
 * $.log(myColor.r+" "+mycolor.g+" "+myColor.b+" "+myColor+a) // you can then access each component of the color
 *
 * var myBackdrop = $.scn.root.addBackdrop("Backdrop")
 * var myBackdrop.color = myColor                             // can be used to set the color of a backdrop
 *
 */
$.oColorValue = function( colorValue ){
    if (typeof colorValue === 'undefined') var colorValue = "#000000ff";

    this.r = 0;
    this.g = 0;
    this.b = 0;
    this.a = 255;

    //Special case in which RGBA values are defined directly.
    switch( arguments.length ){
      case 4:
        this.a = ( (typeof arguments[3]) == "number" ) ? arguments[3] : 0;
      case 3:
        this.r = ( (typeof arguments[0]) == "number" ) ? arguments[0] : 0;
        this.g = ( (typeof arguments[1]) == "number" ) ? arguments[1] : 0;
        this.b = ( (typeof arguments[2]) == "number" ) ? arguments[2] : 0;
        return;
      default:
    }

    if (typeof colorValue === 'string'){
      this.fromColorString(colorValue);
    }else{
      if (typeof colorValue.r === 'undefined') colorValue.r = 0;
      if (typeof colorValue.g === 'undefined') colorValue.g = 0;
      if (typeof colorValue.b === 'undefined') colorValue.b = 0;
      if (typeof colorValue.a === 'undefined') colorValue.a = 255;

      this.r = colorValue.r;
      this.g = colorValue.g;
      this.b = colorValue.b;
      this.a = colorValue.a;
    }
}


/**
 * Creates an int from the color value, as used for backdrop colors.
 * @return: {string}       ALPHA<<24  RED<<16  GREEN<<8  BLUE
 */
$.oColorValue.prototype.toInt = function (){
     return ((this.a & 0xff) << 24) | ((this.r & 0xff) << 16) | ((this.g & 0xff) << 8) | (this.b & 0xff);
}


/**
 * The colour value represented as a string.
 * @return: {string}       RGBA components in a string in format #RRGGBBAA
 */
$.oColorValue.prototype.toString = function (){
    var _hex = "#";

    var r = ("00"+this.r.toString(16)).slice(-2);
    var g = ("00"+this.g.toString(16)).slice(-2);
    var b = ("00"+this.b.toString(16)).slice(-2);
    var a = ("00"+this.a.toString(16)).slice(-2);

    _hex += r + g + b + a;

    return _hex;
}

/**
 * The colour value represented as a string.
 * @return: {string}       RGBA components in a string in format #RRGGBBAA
 */
$.oColorValue.prototype.toHex = function (){
  return this.toString();
}

/**
 * Ingest a hex string in form #RRGGBBAA to define the colour.
 * @param   {string}    hexString                The colour in form #RRGGBBAA
 */
$.oColorValue.prototype.fromColorString = function (hexString){
    hexString = hexString.replace("#","");
    if (hexString.length == 6) hexString += "ff";
    if (hexString.length != 8) throw new Error("incorrect color string format");

    this.$.debug( "HEX : " + hexString, this.$.DEBUG_LEVEL.LOG);

    this.r = parseInt(hexString.slice(0,2), 16);
    this.g = parseInt(hexString.slice(2,4), 16);
    this.b = parseInt(hexString.slice(4,6), 16);
    this.a = parseInt(hexString.slice(6,8), 16);
}


/**
 * Uses a color integer (used in backdrops) and parses the INT; applies the RGBA components of the INT to thos oColorValue
 * @param   { int }    colorInt                      24 bit-shifted integer containing RGBA values
 */
$.oColorValue.prototype.parseColorFromInt = function(colorInt){
	this.r = colorInt >> 16 & 0xFF;
	this.g = colorInt >> 8 & 0xFF;
	this.b = colorInt & 0xFF;
  this.a = colorInt >> 24 & 0xFF;
}


/**
 * Gets the color's HUE value.
 * @name $.oColorValue#h
 * @type {float}
 */
Object.defineProperty($.oColorValue.prototype, 'h', {
    get : function(){
        var r = this.r;
        var g = this.g;
        var b = this.b;

        var cmin = Math.min(r,g,b);
        var cmax = Math.max(r,g,b);
        var delta = cmax - cmin;
        var h = 0;
        var s = 0;
        var l = 0;

        if (delta == 0){
          h = 0.0;
        // Red is max
        }else if (cmax == r){
          h = ((g - b) / delta) % 6.0;
        // Green is max
        }else if (cmax == g){
          h = (b - r) / delta + 2.0;
        // Blue is max
        }else{
          h = (r - g) / delta + 4.0;
        }

        h = Math.round(h * 60.0);

        //WRAP IN 360.
        if (h < 0){
            h += 360.0;
        }

        // // Calculate lightness
        // l = (cmax + cmin) / 2.0;

        // // Calculate saturation
        // s = delta == 0 ? 0 : delta / (1.0 - Math.abs(2.0 * l - 1.0));

        // s = Math.min( Math.abs(s)*100.0, 100.0 );
        // l = (Math.abs(l)/255.0)*100.0;

        return h;
    },

    set : function( new_h ){
      var h = Math.min( new_h, 360.0 );
      var s = Math.min( this.s, 100.0 )/100.0;
      var l = Math.min( this.l, 100.0 )/100.0;

      var c = (1.0 - Math.abs(2.0 * l - 1.0)) * s;
      var x = c * (1 - Math.abs((h / 60.0) % 2.0 - 1.0));
      var m = l - c/2.0;
      var r = 0.0;
      var g = 0.0;
      var b = 0.0;

      if (0.0 <= h && h < 60.0) {
        r = c; g = x; b = 0;
      } else if (60.0 <= h && h < 120.0) {
        r = x; g = c; b = 0;
      } else if (120.0 <= h && h < 180.0) {
        r = 0; g = c; b = x;
      } else if (180.0 <= h && h < 240.0) {
        r = 0; g = x; b = c;
      } else if (240.0 <= h && h < 300.0) {
        r = x; g = 0; b = c;
      } else if (300.0 <= h && h < 360.0) {
        r = c; g = 0; b = x;
      }

      this.r = (r + m) * 255.0;
      this.g = (g + m) * 255.0;
      this.b = (b + m) * 255.0;
    }
});

/**
 * Gets the color's SATURATION value.
 * @name $.oColorValue#s
 * @type {float}
 */
Object.defineProperty($.oColorValue.prototype, 's', {
    get : function(){
        var r = this.r;
        var g = this.g;
        var b = this.b;

        var cmin = Math.min(r,g,b);
        var cmax = Math.max(r,g,b);
        var delta = cmax - cmin;
        var s = 0;
        var l = 0;

        // Calculate lightness
        l = (cmax + cmin) / 2.0;
        s = delta == 0 ? 0 : delta / (1.0 - Math.abs(2.0 * l - 1.0));

        // Calculate saturation
        s = Math.min( Math.abs(s)*100.0, 100.0 );

        return s;
    },

    set : function( new_s ){
      var h = Math.min( this.h, 360.0 );
      var s = Math.min( new_s, 100.0 )/100.0;
      var l = Math.min( this.l, 100.0 )/100.0;

      var c = (1.0 - Math.abs(2.0 * l - 1.0)) * s;
      var x = c * (1 - Math.abs((h / 60.0) % 2.0 - 1.0));
      var m = l - c/2.0;
      var r = 0.0;
      var g = 0.0;
      var b = 0.0;

      if (0.0 <= h && h < 60.0) {
        r = c; g = x; b = 0;
      } else if (60.0 <= h && h < 120.0) {
        r = x; g = c; b = 0;
      } else if (120.0 <= h && h < 180.0) {
        r = 0; g = c; b = x;
      } else if (180.0 <= h && h < 240.0) {
        r = 0; g = x; b = c;
      } else if (240.0 <= h && h < 300.0) {
        r = x; g = 0; b = c;
      } else if (300.0 <= h && h < 360.0) {
        r = c; g = 0; b = x;
      }

      this.r = (r + m) * 255.0;
      this.g = (g + m) * 255.0;
      this.b = (b + m) * 255.0;
    }
});

/**
 * Gets the color's LIGHTNESS value.
 * @name $.oColorValue#l
 * @type {float}
 */
Object.defineProperty($.oColorValue.prototype, 'l', {
    get : function(){
        var r = this.r;
        var g = this.g;
        var b = this.b;

        var cmin = Math.min(r,g,b);
        var cmax = Math.max(r,g,b);
        var delta = cmax - cmin;
        var s = 0;
        var l = 0;


        // Calculate lightness
        l = (cmax + cmin) / 2.0;
        l = (Math.abs(l)/255.0)*100.0;
        return l;
    },

    set : function( new_l ){
      var h = Math.min( this.h, 360.0 );
      var s = Math.min( this.s, 100.0 )/100.0;
      var l = Math.min( new_l, 100.0 )/100.0;

      var c = (1.0 - Math.abs(2.0 * l - 1.0)) * s;
      var x = c * (1 - Math.abs((h / 60.0) % 2.0 - 1.0));
      var m = l - c/2.0;
      var r = 0.0;
      var g = 0.0;
      var b = 0.0;

      if (0.0 <= h && h < 60.0) {
        r = c; g = x; b = 0;
      } else if (60.0 <= h && h < 120.0) {
        r = x; g = c; b = 0;
      } else if (120.0 <= h && h < 180.0) {
        r = 0; g = c; b = x;
      } else if (180.0 <= h && h < 240.0) {
        r = 0; g = x; b = c;
      } else if (240.0 <= h && h < 300.0) {
        r = x; g = 0; b = c;
      } else if (300.0 <= h && h < 360.0) {
        r = c; g = 0; b = x;
      }

      this.r = (r + m) * 255.0;
      this.g = (g + m) * 255.0;
      this.b = (b + m) * 255.0;
    }
});




//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//           $.oColor class         //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


// oPalette constructor

/**
 * The base class for the $.oColor.
 * @constructor
 * @classdesc  $.oColor Base Class
 * @param   {$.oPalette}             oPaletteObject             The palette to which the color belongs.
 * @param   {int}                    attributeObject            The index of the color in the palette.
 *
 * @property {$.oPalette}            palette                    The palette to which the color belongs.
 */
$.oColor = function( oPaletteObject, index ){
  // We don't use id in the constructor as multiple colors with the same id can exist in the same palette.
  this._type = "color";

  this.palette = oPaletteObject;
  this._index = index;
}

// $.oColor Object Properties

/**
 * The Harmony color object.
 * @name $.oColor#colorObject
 * @type {BaseColor}
 */
Object.defineProperty($.oColor.prototype, 'colorObject', {
    get : function(){
        return this.palette.paletteObject.getColorByIndex(this._index);
    }
});



/**
 * The name of the color.
 * @name $.oColor#name
 * @type {string}
 */
Object.defineProperty($.oColor.prototype, 'name', {
    get : function(){
        var _color = this.colorObject;
        return _color.name;
    },

    set : function(newName){
        var _color = this.colorObject;
        _color.setName(newName);
    }
});


/**
 * The id of the color.
 * @name $.oColor#id
 * @type {string}
 */
Object.defineProperty($.oColor.prototype, 'id', {
    get : function(){
        var _color = this.colorObject;
        return _color.id
    },

    set : function(newId){
        // TODO: figure out a way to change id? Create a new color with specific id in the palette?
        throw new Error("setting oColor.id Not yet implemented");
    }
});


/**
 * The index of the color.
 * @name $.oColor#index
 * @type {int}
 */
Object.defineProperty($.oColor.prototype, 'index', {
    get : function(){
        return this._index;
    },

    set : function(newIndex){
        var _color = this.palette.paletteObject.moveColor(this._index, newIndex);
        this._index = newIndex;
    }
});


/**
 * The type of the color.
 * @name $.oColor#type
 * @type {int}
 */
Object.defineProperty($.oColor.prototype, 'type', {
    set : function(){
      throw new Error("setting oColor.type Not yet implemented.");
    },

    get : function(){
        var _color = this.colorObject;
        if (_color.isTexture) return "texture";

        switch (_color.colorType) {
            case PaletteObjectManager.Constants.ColorType.SOLID_COLOR:
                return "solid";
            case PaletteObjectManager.Constants.ColorType.LINEAR_GRADIENT :
                return "gradient";
            case PaletteObjectManager.Constants.ColorType.RADIAL_GRADIENT:
                return "radial gradient";
            default:
        }
    }
});


/**
 * Whether the color is selected.
 * @name $.oColor#selected
 * @type {bool}
 */
Object.defineProperty($.oColor.prototype, 'selected', {
    get : function(){
        var _currentId = PaletteManager.getCurrentColorId()
        var _colors = this.palette.colors;
        var _ids = _colors.map(function(x){return x.id})
        return this._index == _ids.indexOf(_currentId);
    },

    set : function(isSelected){
        // TODO: find a way to work with index as more than one color can have the same id, also, can there be no selected color when removing selection?
        if (isSelected){
            var _id = this.id;
            PaletteManager.setCurrentColorById(_id);
        }
    }
});


/**
 * Takes a string or array of strings for gradients and filename for textures. Instead of passing rgba objects, it accepts "#rrggbbaa" hex strings for convenience.<br>set gradients, provide an object with keys from 0 to 1 for the position of each color.<br>(ex: {0: new $.oColorValue("000000ff"), 1:new $.oColorValue("ffffffff")}).
 * @name $.oColor#value
 * @type {$.oColorValue}
 */
Object.defineProperty($.oColor.prototype, 'value', {
  get : function(){
    var _color = this.colorObject;

    switch(this.type){
      case "solid":
        return new this.$.oColorValue(_color.colorData);
      case "texture":
        return this.palette.path.parent.path + this.palette.name+"_textures/" + this.id + ".tga";
      case "gradient":
      case "radial gradient":
        var _gradientArray = _color.colorData;
        var _value = {};
        for (var i in _gradientArray){
          var _data = _gradientArray[i];
          _value[_gradientArray[i].t] = new this.$.oColorValue(_data.r, _data.g, _data.b, _data.a);
        }
        return _value;
      default:
    }
  },

  set : function(newValue){
    var _color = this.colorObject;

    switch(this.type){
      case "solid":
        _value = new $.oColorValue(newValue);
        _color.setColorData(_value);
        break;
      case "texture":
        // TODO: need to copy the file into the folder first?
        _color.setTextureFile(newValue);
        break;
      case "gradient":
      case "radial gradient":
        var _value = [];
        var _gradient = newValue;
        for (var i  in _gradient){
          var _color = _gradient[i];
          var _tack = {r:_color.r, g:_color.g, b:_color.b, a:_color.a, t:parseFloat(i, 10)}
          _value.push(_tack);
        }
        _color.setColorData(_value);
        break;
      default:
    };
  }
});


// Methods

/**
 * Moves the palette to another Palette Object (CFNote: perhaps have it push to paletteObject, instead of being done at the color level)
 * @param   {$.oPalette}         oPaletteObject              The paletteObject to move this color into.
 * @param   {int}                index                       Need clarification from mchap
 *
 * @return: {$.oColor}           The new resulting $.oColor object.
 */
$.oColor.prototype.moveToPalette = function (oPaletteObject, index){
    if (typeof index === 'undefined') var index = oPaletteObject.paletteObject.nColors;
    var _duplicate = this.copyToPalette(oPaletteObject, index)
    this.remove()

    return _duplicate;
}


/**
 * Copies the palette to another Palette Object (CFNote: perhaps have it push to paletteObject, instead of being done at the color level)
 * @param   {$.oPalette}         oPaletteObject              The paletteObject to move this color into.
 * @param   {int}                index                       Need clarification from mchap
 *
 * @return: {$.oColor}           The new resulting $.oColor object.
 */
$.oColor.prototype.copyToPalette = function (oPaletteObject, index){
    var _color = this.colorObject;

    oPaletteObject.paletteObject.cloneColor(_color);
    var _colors = oPaletteObject.colors;
    var _duplicate = _colors.pop();

    if (typeof index !== 'undefined')  _duplicate.index = index;

    return _duplicate;
}


/**
 * Removes the color from the palette it belongs to.
 */
$.oColor.prototype.remove = function (){
    // TODO: find a way to work with index as more than one color can have the same id
    this.palette.paletteObject.removeColor(this.id);
}


/**
 * Static helper function to convert from {r:int, g:int, b:int, a:int} to a hex string in format #FFFFFFFF <br>
 *          Consider moving this to a helper function.
 * @param   { obj }       rgbaObject                       RGB object
 * @static
 * @return: { string }    Hex color string in format #FFFFFFFF.
 */
$.oColor.prototype.rgbaToHex = function (rgbaObject){
    var _hex = "#";
    _hex += rvbObject.r.toString(16)
    _hex += rvbObject.g.toString(16)
    _hex += rvbObject.b.toString(16)
    _hex += rvbObject.a.toString(16)

    return _hex;
}


/**
 *  Static helper function to convert from hex string in format #FFFFFFFF to {r:int, g:int, b:int, a:int} <br>
 *          Consider moving this to a helper function.
 * @param   { string }    hexString                       RGB object
 * @static
 * @return: { obj }    The hex object returned { r:int, g:int, b:int, a:int }
 */
$.oColor.prototype.hexToRgba = function (hexString){
    var _rgba = {};
    //Needs a better fail state.

    _rgba.r = parseInt(hexString.slice(1,3), 16)
    _rgba.g = parseInt(hexString.slice(3,5), 16)
    _rgba.b = parseInt(hexString.slice(5,7), 16)
    _rgba.a = parseInt(hexString.slice(7,9), 16)

    return _rgba;
}



