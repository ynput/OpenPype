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


/** 
 * Constructor to generate an $.oList type object. 
 * @constructor
 * @classdesc 
 * The base class for the $.oList.<br>
 * Provides a list of values similar to an array, but with simpler filtering and sorting functions provided.<br>
 * It can have any starting index and so can implement lists with a first index of 1 like the $.oColumn.frames returned value.   
 * @param   {object[]}                 initArray             An array to initialize the list.
 * @param   {int}                      [startIndex=0]        The first index exposed in the list.
 * @param   {int}                      [length=0]            The length of the list -- the max between this value and the initial array's length is used.
 * @param   {function}                 [getFunction=null]    The function used to initialize the list when accessing an uninitiated element in the list.<br>In form <i>function( listItem, index ){ return value; }</i>
 * @param   {function}                 [setFunction=null]    The function run when setting an entry in the list.<br>In form <i>function( listItem, index, value ){ return resolvedValue; }</i> -- must return a resolved value. 
 * @param   {function}                 [sizeFunction=null]   The function run when resizing the list.<br>In form <i>function( listItem, length ){ }</i>
 */
$.oList = function( initArray, startIndex, length, getFunction, setFunction, sizeFunction ){
  if(typeof initArray == 'undefined') var initArray = [];
  if(typeof startIndex == 'undefined') var startIndex = 0;
  if(typeof getFunction == 'undefined') var getFunction = false;
  if(typeof setFunction == 'undefined') var setFunction = false;
  if(typeof sizeFunction == 'undefined') var sizeFunction = false; 
  if(typeof length == 'undefined') var length = 0;
  
  //Extend the cache if the content has been provided initially.
  //Must be not enumerable. . .
  // this._initArray      = initArray;
  // this._cache          = [];
  
  // this._getFunction    = getFunction;
  // this._setFunction    = setFunction;  
  // this._sizeFunction   = sizeFunction;
  
  // this.startIndex    = startIndex;
  // this._length       = Math.max( initArray.length, startIndex+length );
  // this.currentIndex  = startIndex;
  
  Object.defineProperty( this, '_initArray', {
    enumerable : false, writable : true,
    value: initArray
  });

  Object.defineProperty( this, '_cache', {
    enumerable : false, writable : true,
    value: []
  });

  Object.defineProperty( this, '_getFunction', {
    enumerable : false, writable : true, configurable: false,
    value: getFunction
  });

  Object.defineProperty( this, '_setFunction', {
    enumerable : false, writable : true, configurable: false,
    value: setFunction
  });

  Object.defineProperty( this, '_sizeFunction', {
    enumerable : false, writable : true, configurable: false,
    value: sizeFunction
  });

  Object.defineProperty( this, 'currentIndex', {
    enumerable : false, writable : true, configurable: false,
    value: startIndex
  });

  Object.defineProperty( this, '_startIndex', {
    enumerable : false, writable : true, configurable: false,
    value: startIndex
  });

  Object.defineProperty( this, '_length', {
    enumerable : false, writable : true, configurable: false,
    value: Math.max( initArray.length, startIndex+length )
  });
  
  this.createGettersSetters();
}


Object.defineProperty( $.oList.prototype, '_type', {
  enumerable : false, writable : false, configurable: false,
  value: 'dynList'
});


/**
 * The next item in the list, undefined if reaching the end of the list.
 * @name $.oList#createGettersSetters
 * @private
 */
Object.defineProperty($.oList.prototype, 'createGettersSetters', {
  enumerable : false,
  value: function(){
    { 
      //Dynamic getter/setters.
      var func_get  =  function( listItem, index ){
                        if( index >= listItem._cache._length ) return null;
                        if( listItem._cache[index].cacheAvailable ){                  
                         return listItem._cache[index].value;                     
                        }                    
                        if( listItem._getFunction ){                     
                          listItem._cache[index].cacheAvailable = true;             
                          listItem._cache[index].value          = listItem._getFunction( listItem, index );          
                          return listItem._cache[ index ].value;                    
                        }
                        return null;
                      };
      
      //Either set the cache function directly, or run the setFunction to get a value and set it.
      var func_set  =  function( listItem, index, value ){
                        if( index >= listItem._cache._length ){
                          if( listItem._sizeFunction ){
                            listItem.length = index+1;
                          }else{
                            throw new ReferenceError( 'Index of out of range: '+index+ ' out of ' + listItem._cache._length )
                          }
                        }
                          
                        if( listItem._setFunction ){
                          listItem._cache[index].cacheAvailable = true;
                          try{
                            listItem._cache[index].value          = listItem._setFunction( listItem, index, value );
                          }catch(err){}
                        }else{
                          listItem._cache[index].cacheAvailable = true;
                          listItem._cache[index].value          = value;
                        }
                       };
    
      var setup_length           = Math.max( this._length, this._cache.length ); 
      if( this._cache.length < setup_length ){
        this._cache                = this._cache.concat( new Array( setup_length-this._cache.length ) );
      }
      
      for( var n=0;n<this._length;n++ ){
        if( !this._cache[n] ){
          var cacheAvail = n<this._initArray.length;
          this._cache[n] = { 
                        "cacheAvailable": cacheAvail,
                        "enumerable"    : false,
                        "value"         : cacheAvail ? this._initArray[n] : null,
                      };
        }
        
        var currentEnumerable = n>=this.startIndex && n< this.length;
        
        if( currentEnumerable && !this._cache[n].enumerable ){
          Object.defineProperty( this, n, {
            enumerable : true,
            configurable: true,
            set : eval( 'val = function(val){ return func_set( this, '+n+', val ); }' ),
            get : eval( 'val = function(){ return func_get( this, '+n+'); }' )
          });
          this._cache[n].enumerable = true;
        }else if( !currentEnumerable && this._cache[n].enumerable ){
          Object.defineProperty( this, n, {
            enumerable : false,
            configurable: true,
            value : null
          });
          this._cache[n].enumerable = false;
        }
      }
    }
  }
});


/**
 * The startIndex of the list.
 * @name $.oList#startIndex
 * @type {int}
 */
Object.defineProperty( $.oList.prototype, 'startIndex', {
  enumerable : false,
  get: function(){
    return this._startIndex;
  },
  
  set: function( val ){
    this._startIndex = val;
    this.currentIndex = Math.max( this.currentIndex, val );
    
    this.createGettersSetters();
  }
});


/**
 * The length of the list.
 * @name $.oList#length
 * @function
 * @return {int}   The length of the list, considering the startIndex.
 */
Object.defineProperty($.oList.prototype, 'length', {
  enumerable : false,
  get: function(){
    return this._length;
  },
  
  set: function( val ){
    //Reset the size as needed.
    
    var new_val = val+this.startIndex;
    if( new_val != this._length ){
      this._length = new_val;
      this.createGettersSetters();
    }
     
    this._sizeFunction( this, this._length );
  }
});


/**
 * The first item in the list, resets the iterator to the first entry.
 * @name $.oList#first
 * @function
 * @return {object}   The first item in the list.
 */
Object.defineProperty($.oList.prototype, 'first', {
  enumerable : false,
  value: function(){
    this.currentIndex = this.startIndex;
    return this[ this.startIndex ];
  }
});

/**
 * The next item in the list, undefined if reaching the end of the list.
 * @name $.oList#next
 * @function
 * @return {object}     Grabs the next item using the property $.oList.currentIndex, and increase the iterator
 * @example
 * var myList = new $.oList([1,2,3], 1)
 *
 * var item = myList.first();  // 1
 *
 * while( item != undefined ){
 *   $.log(item)               // traces the whole array one item at a time : 1,2,3   
 *   item = myList.next();   
 * }
 */
Object.defineProperty($.oList.prototype, 'next', {
  enumerable : false,
  value: function(){
    this.currentIndex++;
    
    if( this.currentIndex >= this.length ){
      return;
    }
    if( !this.hasOwnProperty( this.currentIndex) ) return;  // we return undefined so we can check correctly in the case of list of boolean values

    return this[ this.currentIndex ];
  }
});


/**
 * The index of the last valid element of the list
 * @name $.oList#lastIndex
 * @type {int}
 */
Object.defineProperty($.oList.prototype, 'lastIndex', {
  enumerable : false,
  get: function(){
    return this.length - 1;
  }
});


/**
 * Similar to Array.push. Adds the value given as parameter to the end of the oList
 * @name $.oList#push
 * @function
 * @param   {various}     newElement                    The value to add at the end of the oList
 *
 * @return  {int}   Returns the new length of the oList.
 */
Object.defineProperty($.oList.prototype, 'push', {
  enumerable : false,
  value : function( newElement ){
    var origLength = this.length;
    this.length    = origLength+1;
    
    this[ origLength ] = newElement;
    return origLength+1;
  }
});

/**
 * Similar to Array.pop. Removes the last value from the array and returns it. It is then removed from the array.
 * @name $.oList#pop
 * @function
 * @return  {int}   The item popped from the back of the array.
 */
Object.defineProperty($.oList.prototype, 'pop', {
  enumerable : false,
  value : function( ){

    var origLength = this.length;
    if( !this.hasOwnProperty( origLength-1 ) ){
      return;
    }
    
    var cache = this._cache.pop();
  
    this.length    = origLength-1;
    
    return cache.value;
  }
});


/**
 * Returns an oList object containing only the elements that passed the provided filter function.
 * @name $.oList#filterByFunction
 * @function
 * @param   {function}     func                    A function that is used to filter, returns true if it is to be kept in the list.
 *
 * @return  {$.oList}   The list represented as an array, filtered given the function.
 */
Object.defineProperty($.oList.prototype, 'filterByFunction', {
  enumerable : false,
  value : function( func ){
    var _results = [];
    for (var i in this){
      if ( func(this[i]) ){
        _results.push( this[i] );
      }
    }

    return new this.$.oList( _results );
  }
});


/**
 * Returns an oList object containing only the elements that have the same property value as provided.
 * @name $.oList#filterByProperty
 * @function
 * @param   {string}    property                    The property to find.
 * @param   {string}    search                      The value to search for in the property.
 *
 * @return  {$.oList}   The list represented as an array, filtered given its properties.
 * @example
 * var doc = $.s // grab the scene object
 * var nodeList = new $.oList(doc.nodes, 1) // get a list of all the nodes, with a first index of 1
 * 
 * $.log(nodeList) // outputs the list of all the node paths
 * 
 * var readNodes = nodeList.filterByProperty("type", "READ") // get a new list of only the nodes of type 'READ'
 * 
 * $.log(readNodes.extractProperty("name"))  // prints the names of the result
 *
 */
Object.defineProperty($.oList.prototype, 'filterByProperty', {
  enumerable : false,
  value : function(property, search){
    var _results = []
    var _lastIndex = this.lastIndex;
    for (var i=this.startIndex; i < _lastIndex; i++){
      // this.$.log(i+" "+(property in this[i])+" "+(this[i][property] == search)+_lastIndex)
      if ((property in this[i]) && (this[i][property] == search)) _results.push(this[i])
    }
    // this.$.log(_results)
    return new this.$.oList(_results)
  }
});


/**
 * Returns an oList object containing only the values of the specified property.
 * @name $.oList#extractProperty
 * @function
 * @param   {string}     property                    The property to find.
 *
 * @return  {$.oList}   The newly created oList object containing the property values.
 */
Object.defineProperty($.oList.prototype, 'extractProperty', {
  enumerable : false,
  value : function(property){
    var _results = []
    var _lastIndex = this.lastIndex;
    for (var i=this.startIndex; i < _lastIndex; i++){
      _results.push(this[i][property])
    }
    return new this.$.oList(_results)
  }
});


/**
 * Returns an oList object sorted according to the values of the specified property.
 * @name $.oList#sortByProperty
 * @function
 * @param   {string}    property                    The property to find.
 * @param   {bool}      [ascending=true]            Whether the sort is ascending/descending.
 *
 * @return  {$.oList}   The sorted $oList.
 */
Object.defineProperty($.oList.prototype, 'sortByProperty', {
  enumerable : false,
  value : function( property, ascending ){
    if (typeof ascending === 'undefined') var ascending = true;

    var _array = this.toArray();
    if (ascending){
      var results = _array.sort(function (a,b){return a[property] - b[property]});
    }else{
      var results = _array.sort(function (a,b){return b[property] - a[property]});
    }

    // Sort in place or return a copy?
    return new this.$.oList( results, this.startIndex );
  }
});


/**
 * Returns an oList object sorted according to the sorting function provided.
 * @name $.oList#sortByFunction
 * @function
 * @param   {function}   func                    A function that is used to sort, in form function (a,b){return a - b}. (A positive a-b value will put the element b before a)
 *
 * @return  {$.oList}   The sorted $oList.
 */
Object.defineProperty($.oList.prototype, 'sortByFunction', {
  enumerable : false,
  value : function( func ){
    var _array = this.toArray();
    var results = _array.sort( func );

    // Sort in place or return a copy?
    return new this.$.oList( results, this.startIndex );
  }
});


// Methods must be declared as unenumerable properties this way
/**
 * Converts the oList to an array
 * @name $.oList#toArray
 * @function
 * @return  {object[]}   The list represented as an array.
 */
Object.defineProperty($.oList.prototype, 'toArray', {
  enumerable : false,
  value : function(){
    var _array = [];
    for (var i=0; i<this.startIndex+this.length; i++){
      if( i<this.startIndex ){
        _array.push( null );
      }else{
        _array.push( this[i] );
      }
    }
    return _array;
  }
});

/**
 * outputs the list to a string for easy logging
 * @name $.oList#toString
 * @function 
 * @type {string}
 */
Object.defineProperty($.oList.prototype, 'toString', {
  enumerable : false,
  value: function(){
    return this.toArray().join(",");
  }
});




//Needs all filtering, limiting. mapping, pop,  concat, join, ect
//Speed up by finessing the way it extends and tracks the enumerable properties.