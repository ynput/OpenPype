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
//         $.oNodeLink class        //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * The base class for the oTimeline.
 * @constructor
 * @classdesc  oTimeline Base Class
 * @param   {oNode}                   outNode                   The source oNode of the link.
 * @param   {int}                     outPort                   The outport of the outNode that is connecting the link.
 * @param   {oNode}                   inNode                    The destination oNode of the link.
 * @param   {int}                     inPort                    The inport of the inNode that is connecting the link.
 *
 * @property   {bool}                    autoDisconnect         Whether to auto-disconnect links if they already exist. Defaults to true.
 * @example
 *  //Connect two pegs together.
 *  var peg1     = $.scene.getNodeByPath( "Top/Peg1" );
 *  var peg2     = $.scene.getNodeByPath( "Top/Peg2" );
 *
 *  //Create a new $.oNodeLink -- We'll connect two pegs with this new nodeLink.
 *  var link = new $.oNodeLink( peg1,     //Out Node
 *                              0,        //Out Port
 *                              peg2,     //In Node
 *                              0 );      //In Port
 *
 *  //The node link doesn't exist yet, but lets apply it.
 *  link.apply();
 *  //This connection between peg1 and peg2 now exists.
 *
 *  //We can also get the outlinks for the entire node and all of its outputs.
 *  var outLinks = peg2.outLinks;
 *
 *  //Lets connect peg3 to the chain with this existing outLink. This will use an existing link if its already there, or create a new one if none exists.
 *  var peg3     = $.scene.getNodeByPath( "Top/Peg3" );
 *  outLinks[0].linkIn( peg3, 0 );
 *
 *  //Uh oh! We need to connect a peg between 1 and 2.
 *  var peg4     = $.scene.getNodeByPath( "Top/Peg4" );
 *
 *  //The link we already created above can have a node inserted between it easily.
 *  link.insertNode(  peg4, 0, 0 ); //Peg to insert, in port, out port.
 *
 *  //Oh no! Peg 5 is in a group. Well, it still works!
 *  var peg5     = $.scene.getNodeByPath( "Top/Group/Peg5" );
 *  var newLink  = peg1.addOutLink( peg5 );
 */
$.oNodeLink = function( outNode, outPort, inNode, inPort, outlink ){

    //Public properties.
    this.autoDisconnect = true;
    this.path           = false;

    //Private properties.
    this._outNode = outNode;
    this._outPort = outPort;
    this._outLink = outlink;

    this._realOutNode = outNode;
    this._realOutPort = 0;

    this._inNode  = inNode;
    this._inPort  = inPort;

    this._stopUpdates        = false;
    this._newInNode     = null;
    this._newInPort     = null;
    this._newOutNode    = null;
    this._newOutPort    = null;
    this._exists        = false;
    this._validated     = false;

    //Assume validation when providing all details. This is done to speed up subsequent lookups.
    if( outNode &&
        inNode  &&
        typeof outPort === 'number' &&
        typeof inPort  === 'number' &&
        typeof outlink === 'number'
      ){

      //Skip validation in the event that we've beengiven all details -- this is to just speed up list generation.
      return;
    }

    this.validate();
}


/**
 * Whether the nodeLink exists in the provided state.
 * @name $.oNodeLink#exists
 * @type {bool}
 * @example
 *   //Connect two pegs together.
 *  var peg1     = $.scene.getNodeByPath( "Top/Peg1" );
 *  var peg2     = $.scene.getNodeByPath( "Top/NodeDoesntExist" );
 *  var link = new $.oNodeLink( peg1,     //Out Node
 *                              0,        //Out Port
 *                              peg2,     //In Node
 *                              0 );      //In Port
 *  link.exists == false;   //FALSE, This link doesnt exist in this context, because the node doesnt exist.
 */
Object.defineProperty($.oNodeLink.prototype, 'exists', {
    get : function(){
      if( !this._validated ){
        this.validate();
      }
      return this._exists;
    }
});


/**
 * The outnode of this $.oNodeLink. The outNode that is outputting the connection for this link on its outPort and outLink.
 * @name $.oNodeLink#outNode
 * @type {$.oNode}
 */
Object.defineProperty($.oNodeLink.prototype, 'outNode', {
    get : function(){
      return this._outNode;

    },
    set : function( val ){
      this._validated = false;
      this._newOutNode = val;

      if( this.stopUpdates ){
        return;
      }

      this.apply(); // do we really want to apply everytime we set?
    }
});


/**
 * The inNode of this $.oNodeLink. The inNode that is accepting this link on its inport.
 * @name $.oNodeLink#inNode
 * @type {$.oNode}
 */
Object.defineProperty($.oNodeLink.prototype, 'inNode', {
    get : function(){
      return this._inNode;
    },

    set : function( val ){
      //PATH FIND UP TO THE INNODE.
      this._validated = false;
      this._newInNode = val;

      if( this.stopUpdates ){
        return;
      }

      this.apply();  // do we really want to apply everytime we set?
    }
});


/**
 * The outport of this $.oNodeLink. The port that the outNode connected to for this link.
 * @name $.oNodeLink#outPort
 * @type {int}
 */
Object.defineProperty($.oNodeLink.prototype, 'outPort', {
    get : function(){
      return this._outPort;

    },

    set : function( val ){
      this._validated  = false;
      this._newOutPort = val;

      if( this.stopUpdates ){
        return;
      }

      this.apply();  // do we really want to apply everytime we set?
    }
});


/**
 * The outLink of this $.oNodeLink. The link index that the outNode connected to for this link.
 * @name $.oNodeLink#outLink
 * @type {int}
 */
Object.defineProperty($.oNodeLink.prototype, 'outLink', {
    get : function(){
      return this._outLink;
    }
});


/**
 * The inPort of this $.oNodeLink.
 * @name $.oNodeLink#inPort
 * @type {oNode[]}
 */
Object.defineProperty($.oNodeLink.prototype, 'inPort', {
    get : function(){
      return this._inPort;
    },
    set : function( val ){
      this._validated = false;
      this._newInPort = val;

      if( this.stopUpdates ){
        return;
      }

      this.apply();  // do we really want to apply everytime we set?
    }
});


/**
 * When enabled, changes to the link will no longer update -- the changes will then apply when no longer stopped.
 * @name $.oNodeLink#stopUpdates
 * @private
 * @type {bool}
 */
Object.defineProperty($.oNodeLink.prototype, 'stopUpdates', {
    get : function(){
      return this._stopUpdates;
    },
    set : function( val ){
      this._stopUpdates = val;

      if( !val ){
        this.apply();
      }
    }
});


/**
 * Dereferences up a node's chain, in order to find the exact node its actually attached to.
 * @private
 * @param   {oNode}                   onode                   The node to dereference the groups for.
 * @param   {int}                     port                    The port to dereference.
 * @param   {object[]}                path                    The array path to pass along recursively.<br>[ { "node": src_node, "port":srcNodeInfo.port, "link":srcNodeInfo.link } ]
 * @private
 * @return {object}                   Object in form { "node":oNode, "port":int, "link": int }
 */
$.oNodeLink.prototype.findInputPath = function( onode, port, path ) {
  var srcNodeInfo = node.srcNodeInfo( onode.path, port );
  if( !srcNodeInfo ){
    return path;
  }

  var src_node = this.$.scene.getNodeByPath( srcNodeInfo.node );
  if( !src_node ){
    return path;
  }

  if( src_node.type == "MULTIPORT_IN" ){
    //Continue to dereference until we find something other than a group/multiport in.
    var ret = { "node": src_node, "port":srcNodeInfo.port, "link":srcNodeInfo.link };
    path.push( ret );

    var src_node = src_node.group;

    var ret = { "node": src_node, "port":srcNodeInfo.port, "link":srcNodeInfo.link };
    path.push( ret );
  }else if( src_node.type == "GROUP" ){
    //Continue to dereference until we find something other than a group/multiport out.
    var ret = { "node": src_node, "port":srcNodeInfo.port, "link":srcNodeInfo.link };
    path.push( ret );

    var src_node =  src_node.multiportOut;

    var ret = { "node": src_node, "port":srcNodeInfo.port, "link":srcNodeInfo.link };
    path.push( ret );
  }else{
    var ret = { "node": src_node, "port":srcNodeInfo.port, "link":srcNodeInfo.link };
    path.push( ret );
    return path;
  }

  return this.findInputPath( src_node, srcNodeInfo.port, path );
}


/**
 * Changes both the in-node and in-port at once.
 * @param   {oNode}                   onode                   The node to link on the input.
 * @param   {int}                     port                    The port to link on the input.
 * @example
 *  //Connect two pegs together.
 *  var peg1     = $.scene.getNodeByPath( "Top/Peg1" );
 *  var peg2     = $.scene.getNodeByPath( "Top/Peg2" );
 *
 *  var outLinks  = peg1.outLinks;
 *  outLinks[0].linkIn( peg2, 0 ); //Links the input of peg2, port 0 -- to this link, connecting its outNode [peg1] and outPort [0] and outLink [arbitrary].
 */
$.oNodeLink.prototype.linkIn = function( onode, port ) {
  this._validated = false;
  var stopUpdates_val = this.stopUpdates;
  this.stopUpdates = true;

  this.inNode = onode;
  this.inPort = port;

  this.stopUpdates = stopUpdates_val;
}


/**
 * Changes both the out-node and out-port at once.
 * @param   {oNode}                   onode                   The node to link on the output.
 * @param   {int}                     port                    The port to link on the output.
 * @example
 *  //Connect two pegs together.
 *  var peg1     = $.scene.getNodeByPath( "Top/Peg1" );
 *  var peg2     = $.scene.getNodeByPath( "Top/Peg2" );
 *
 *  var inLinks  = peg1.inLinks;
 *  inLinks[0].linkOut( peg2, 0 ); //Links the output of peg2, port 0 -- to this link, connecting its inNode [peg1] and inPort [0].
 */
$.oNodeLink.prototype.linkOut = function( onode, port ) {
  this._validated = false;

  var stopUpdates_val = this.stopUpdates;
  this.stopUpdates = true;

  this.outNode = onode;
  this.outPort = port;

  this.stopUpdates = stopUpdates_val;
}


/**
 * Insert a node in the middle of the link chain.
 * @param   {oNode}                   nodeToInsert            The node to link on the output.
 * @param   {int}                     inPort                  The port to link on the output.
 * @param   {int}                     outPort                 The port to link on the output.
 * @example
 *  //Connect two pegs together.
 *  var peg1     = $.scene.getNodeByPath( "Top/Peg1" );
 *  var peg2     = $.scene.getNodeByPath( "Top/Peg2" );
 *
 *  //Create a new $.oNodeLink -- We'll connect two pegs with this new nodeLink.
 *  var link = new $.oNodeLink( peg1,     //Out Node
 *                              0,        //Out Port
 *                              peg2,     //In Node
 *                              0 );      //In Port
 *
 *  //The link we already created above can have a node inserted between it easily.
 *  var peg4     = $.scene.getNodeByPath( "Top/Peg4" );
 *  link.insertNode(  peg4, 0, 0 ); //Peg to insert, in port, out port.
 */
$.oNodeLink.prototype.insertNode = function( nodeToInsert, inPort, outPort ) {
  this.stopUpdates = true;

  var inNode = this.inNode;
  var inPort = this.inPort;

  this.inNode = nodeToInsert;
  this.inport = inPort;

  this.stopUpdates = false;

  var new_link = new this.$.oNodeLink( nodeToInsert, outPort, inNode, inPort, 0 );
  new_link.apply( true );
}

/**
 * Apply the links as needed after unfreezing the oNodeLink
 * @param   {bool}                   force                   Forcefully reconnect/disconnect the note given the current settings of this nodelink.
 * @example
 *  //Connect two pegs together.
 *  var peg1     = $.scene.getNodeByPath( "Top/Peg1" );
 *  var peg2     = $.scene.getNodeByPath( "Top/Peg2" );
 *
 *  //Create a new $.oNodeLink -- We'll connect two pegs with this new nodeLink.
 *  var link = new $.oNodeLink( peg1,     //Out Node
 *                              0,        //Out Port
 *                              peg2,     //In Node
 *                              0 );      //In Port
 *
 *  //The node link doesn't exist yet, but lets apply it.
 *  link.apply();
 */
$.oNodeLink.prototype.apply = function( force ) {
  this._stopUpdates = false;
  this._validated = false; // ? Shouldn't we use this to bypass application if it's already been validated?

  var disconnect_in = false;
  var disconnect_out = false;
  var inports_removed  = {};
  var outports_removed = {};

  if( force || !this._exists ){    //Apply this.
    this._newInNode     = this._newInNode ? this._newInNode : this._inNode;
    this._newOutNode    = this._newOutNode ? this._newOutNode : this._outNode;
    this._newOutPort    = ( this._newOutPort === null ) ? this._outPort : this._newOutPort;
    this._newInPort     = ( this._newInPort  === null ) ? this._inPort  : this._newInPort;

    var force = true;

    disconnect_in = true;
    disconnect_out = true;
  }else{

    //Force a reconnect -- track content as needed.
    //Check and validate in ports.
    var target_port = this._inPort;
    if( this._newInPort !== null ){
      if( this._newInPort != this._inPort ){
        target_port = this._newInPort;
        disconnect_in = true;
      }
    }

    var old_inPortCount = false;    //Used to track if the inport count has changed upon its removal.
    if( this._newInNode !== null ){
      if( this._newInNode ){
        if( !this._inNode || ( this._inNode.path != this._newInNode.path ) ){
          disconnect_in = true;
        }
      }else if( this._inNode ){
        disconnect_in = true;
      }
    }

    //Check and validate out ports.
    if( this._newOutPort !== null ){
      if( ( this._newOutPort !== this._outPort ) ){
        disconnect_out = true;
      }
    }

    if( this._newOutNode !== null ){
      if( this._newOutNode ){
        if( !this._outNode || ( this._outNode.path != this._newOutNode.path ) ){
          disconnect_out = true;
        }
      }else if( this._outNode ){
        disconnect_out = true;
      }
    }
  }

  if( !disconnect_in && !disconnect_out ){
    //Nothing happened.
    // System.println( "NOTHING TO DO" );
    return;
  }

  if( this._newInNode ){
    // if( this._newInNode.inNodes.length > target_port ){
    if( this._newInNode.inPorts > target_port ){
      // if( this._newInNode.inNodes[ target_port ] ){
      if( node.isLinked(this._newInNode.path, target_port) ){
        //-- Theres already a connection here-- lets remove it.
        if( this.autoDisconnect ){
          node.unlink (this._newInNode.path, target_port)
          // this._newInNode.unlinkInPort( target_port );
          inports_removed[ this._newInNode.path ] = target_port;
        }else{
          throw "Unable to link "+this._outNode+" to "+this._newInNode+", port "+target_port+" is already occupied.";
        }
      }
    }
  }

  //We'll work with the new values -- pretend any new connection is a new one.
  this._newInNode  = this._newInNode ? this._newInNode : this._inNode;
  this._newOutNode = this._newOutNode ? this._newOutNode : this._outNode;
  this._newOutPort = ( this._newOutPort === null ) ? this._outPort : this._newOutPort;
  this._newInPort  = ( this._newInPort === null ) ? this._inPort : this._newInPort;


  if( !this._newInNode || !this._newOutNode ){
    //Nothing to attach.
    this._inNode  = this._newInNode;
    this._inPort  = this._newInPort;
    this._outNode = this._newOutNode;
    this._outPort = this._newOutPort;

    return;
  }

  if( !this._newInNode.exists || !this._newOutNode.exists ){
    this._inNode  = this._newInNode;
    this._inPort  = this._newInPort;
    this._outNode = this._newOutNode;
    this._outPort = this._newOutPort;

    return;
  }


  //Kill and rebuild the current connection - but first, calculate existing port indices so they can be reconnected contextually.
  // var newInPortCount   = this._newInNode ? this._newInNode.inNodes.length : 0;
  var newInPortCount   = this._newInNode ? this._newInNode.inPorts : 0;
  // var newOutPortCount  = this._newOutNode ? this._newOutNode.outNodes.length : 0;
  var newOutPortCount  = this._newOutNode ? this._newOutNode.outPorts : 0;

  //Unlink it anyway! Dont worry, we'll reattach that after.
  if( this._inNode ){
    // this._inNode.unlinkInPort( this._inPort );
    node.unlink (this._inNode.path, this._inPort)
    if( this._outNode ) outports_removed[ this._outNode.path ] = this._outPort;
    inports_removed[ this._inNode.path ] = this._inPort;
  }

  //Cant connect without a valid port.
  if( ( this._newOutPort === null ) || ( this._newOutPort === false ) ){
    this._inNode  = this._newInNode;
    this._inPort  = this._newInPort;
    this._outNode = this._newOutNode;
    this._outPort = this._newOutPort;

    return;
  }
  if( ( this._newInPort === null ) || ( this._newInPort === false ) ){
    this._inNode  = this._newInNode;
    this._inPort  = this._newInPort;
    this._outNode = this._newOutNode;
    this._outPort = this._newOutPort;

    return;
  }

  //Check to see if any of the port values have changed.
  var newInPortCount_result   = this._newInNode ? this._newInNode.inNodes.length : 0;
  var newOutPortCount_result  = this._newOutNode ? this._newOutNode.outNodes.length : 0;

  if( newOutPortCount_result != newOutPortCount ){
    //Outport might have changed. React appropriately.
    if( this._newOutNode.path in outports_removed ){
      if( this._newOutPort > outports_removed[ this._newOutNode.path ] ){
        this._newOutPort-=1;
      }
    }
  }

  if( newInPortCount_result != newInPortCount ){
    //Outport might have changed. React appropriately.
    if( this._newInNode.path in inports_removed ){
      if( this._newInPort > inports_removed[ this._newInNode.path ] ){
        this._newInPort-=1;
      }
    }
  }

  var new_inGroup  = this._newInNode.group;
  var new_outGroup = this._newOutNode.group;
  if( new_inGroup.path == new_outGroup.path ){
    //Simple direct connection within the same group.
    node.link( _newOutNode.path, this._newInPort, this._newInNode.path, this._newOutPort);
    //this._newOutNode.linkOutNode( this._newInNode, this._newInPort, this._newOutPort ); MCNote: use the API so we can replace stuff into it later

  }else{
    //Look for an access route.

    var common_path = [];
    var split_in  = new_inGroup.path.split( "/" );
    var split_out = new_outGroup.path.split( "/" );

    //Find the common top path.
    for( var n=0;n<Math.min(split_in.length, split_out.length);n++ ){
      if( split_in[n] != split_out[n] ) break;

      common_path.push( split_out[n] );
    }

    //The common path is the place we need to attach; find a common link.
    //Work forward from in, backwards from out.

    var common_path = common_path.join( "/" );

    //Outward Path finding.
    // var outward_path = find_outward( this._newOutNode, this._newOutPort, common_path, [] );
    var outward_search = new this.$.oNodeLink(this._newOutNode, this._newOutPort, new this.$.oNode(common_path), 0)
    var outward_path = outward_search.findOutwardPath();

    var common_from = outward_path[outward_path.length-1].from;
    var common_port = outward_path[outward_path.length-1].fromport;

    var targ_path = this._newInNode.path;
    targ_path_split = targ_path.split( "/" );

    // Find forward from the common junction.
    var inward_search = new this.$.oNodeLink(common_from, common_port, this._newInNode, this._newInPort)
    var inward_path = inward_search.findInwardPath( true );

    var cleanPath = [];
    for( var n = 0; n < outward_path.length; n++ ){
      var t_path = outward_path[n];
      if( !t_path.exists && t_path.to ){
        // t_path.from.linkOutNode( t_path.to, t_path.fromport, t_path.toport, true );
        node.link(t_path.from.path, t_path.fromport, t_path.to.path, t_path.toport, true , true);
        // System.println( "RESULT OUT: " + t_path.from + " : " + t_path.fromport + " -- " + t_path.to + " : " + t_path.toport );
      }
    }

    for( var n = inward_path.length-1; n >= 0; n-- ){
      var t_path = inward_path[n];
      if( !t_path.exists ){
        // t_path.from.linkOutNode( t_path.to, t_path.fromport, t_path.toport, t_path.createPort );
        node.link(t_path.from.path, t_path.fromport, t_path.to.path, t_path.toport, t_path.createPort, t_path.createPort);
        // System.println( "RESULT IN: " + t_path.from + " : " + t_path.fromport + " -- " + t_path.to + " : " + t_path.toport + "  " + t_path.createPort );
      }
    }
  }

  this._inNode  = this._newInNode;
  this._inPort  = this._newInPort;
  this._outNode = this._newOutNode;
  this._outPort = this._newOutPort;

  this._newInNode     = null;
  this._newInPort     = null;
  this._newOutNode    = null;
  this._newOutPort    = null;

  if( !this.validate() ){
    throw ReferenceError( "Failed to connect the targets appropriately." );
  }
}


/**
 * findInwardPath. Used internally when applying link.
 * finds the sequence of groups to go into to find the node to connect from a higher level
 * @private
 * @return {path}      an array of path node objects : { "end" : bool,
 *                                                       "exists" : bool,
 *                                                       "from" : oNode,
 *                                                       "fromport" : int,
 *                                                       "to" : oNode,
 *                                                       "toport" : int,
 *                                                       "createPort" : bool
 *                                                      }
 */
$.oNodeLink.prototype.findInwardPath = function( createPort ){
  var from_node = this._outNode;
  var from_port = this._outPort;
  var targ_node = this._inNode;
  var targ_port = this._inPort;
  var path = [];

  var length_parent = from_node.group.path.split("/").length;
  var targ_grp = targ_path_split.slice( 0, length_parent+1 ).join("/");

  if( targ_grp == targ_path ){
    //Should it create the port?

    path.push( { "end": true, "exists":false, "from":from_node, "fromport":from_port, "to":targ_node, "toport":targ_port, "createPort":createPort } );
    return path;
  }

  //Find a common link from this target to the next.
  var grp = this.$.scene.getNodeByPath( targ_grp );
  var mport = grp.multiportIn;
  // var followPort = mport.outNodes.length;
  var followPort = mport.outPorts;

  //Find if the outnodes of from, at the given outNode, connects to the multiportOut already.
  try{
    var found_existing = false;
    var createPortForward = true;
    // if( from_node.outNodes.length>from_port ){
    if( from_node.outPorts > from_port){
      // var ops = from_node.outNodes[from_port];
      var ops = from_node.getOutLinksNumber(from_port);
      // for( var n=0; n<ops.length; n++ ){
      for( var n=0; n<ops; n++ ){
        // if( ops[n].path == targ_grp ){
        if( node.linkedNode(from_node.path, from_port, n) == targ_grp){
          //Dont add it as a new connection, add it as an existing one.
          var info = node.dstNodeInfo( from_node.path, from_port, n );
          if( info ){
            found_existing = true;
            followPort = info.port;
            createPortForward = false;
            break;
          }
       }
      }
      if(!found_existing){
        // var grprIns = grp.inNodes;
        var grprIns = grp.inPorts;
        // var mpOuts  = mport.outNodes;
        var mpOuts = mport.outPorts;

        //It can either be acceptable, if the connection is not connected at grpin and not connected at mpout,
        //or if grpin is not connected, and mpout is connected where we want it to be.
        var targ_internal = targ_path_split.slice( 0, length_parent+2 ).join("/");
        for( var n=0; n < grprIns; n++ ){
          var grprLinks = grp.getInLinksNumber(n);
          var mpLinks = mport.getOutLinksNumber(n);

          // if( !grprIns[n] ){
          if( grprLinks == 0 ){
            // if( mpOuts[n].length == 0 ){
            if( mpLinks == 0 ){
              //Its not being used.
              followPort = n;
              createPortForward = false;

              break;
            // }else if( mpOuts[n].length == 1 ){
            }else if( mpLinks == 1 ){
              // Its being used, check if its just passing through to another group.
              // if( mpOuts[n][0].path == targ_internal ){
              if( node.linkedNode(mport.path, n, 0) == grp.multiportOut.path ){
                followPort = n;
                createPortForward = false;
                break;
              }
            }
          }
        }
      }
    }

    path.push( { "end" : false, "exists":found_existing, "from":from_node, "fromport":from_port, "to":grp, "toport":followPort, "createPort":createPort } );
    // path = find_inward( mport, followPort, targ_node, targ_port, path, createPortForward );
    var checkLink = new this.$.oNodeLink(mport, followPort, targ_node, targ_port)
    path = path.concat(checkLink.find_inward( createPortForward ));

  }catch(err){
    this.$.debug( "ERR: " + err.message + "  " + err.lineNumber + " : " + err.fileName, this.$.DEBUG_LEVEL.ERROR );
  }

  return path;
}


/**
 * findOutwardPath. Used internally when applying link.
 * finds the sequence of links to go to the highest level of group needed to connect
 * @private
 * @return {path}      an array of path node objects : { "end" : bool,
 *                                                       "exists" : bool,
 *                                                       "from" : oNode,
 *                                                       "fromport" : int,
 *                                                       "to" : oNode,
 *                                                       "toport" : int,
 *                                                       "createPort" : bool
 *                                                      }
 */
$.oNodeLink.prototype.findOutwardPath = function(){
  var from_node = this._outNode;
  var port = this._outPort;
  var targ = this._inNode;

  // if( from_node.group.path != targ ){
  if( from_node.group.path != targ.path ){
    //Attach to a group one higher.
    //multiportIn
    var grp   = from_node.group;
    var mport = grp.multiportOut;
    var followPort = mport.inPorts;
    //Find if the outnodes of from, at the given outNode, connects to the multiportOut already.
    try{
      var found_existing = false;
      // if( from_node.outNodes.length>port ){
      if( from_node.outPorts > port ){
        for( var n = 0; n < from_node.outPorts; n++ ){
          // if( from_node.outNodes[port][n].path == mport.path ){
          if( node.dstNode(from_node.path, port, n) == mport.path ){
            //Dont add it as a new connection, add it as an existing one.
            var info = node.dstNodeInfo( from_node.path, port, n );
            if( info ){
              found_existing = true;
              followPort = info.port;
              break;
            }
          }
        }
      }

      path.push( { "end" : false, "exists":found_existing, "from":from_node, "fromport":port, "to":mport, "toport":followPort  } );
      // path = find_outward( grp, followPort, targ, path );
      var checkLink = new this.$.oNodeLink(grp, followPort, this._inNode)
      path = path.concat( checkLink.findOutwardPath());
    }catch(err){
      this.$.debug( "ERR: " + err.message + "  " + err.lineNumber + " : " + err.fileName , this.$.DEBUG_LEVEL.ERROR);
    }

  }else{
    path.push( { "end": true, "exists":true, "from":from_node, "fromport":port, "to":false, "toport":false  } );
  }

  return path;
}


/**
 * Validates the details of a given connection. Used internally when details change.
 * @private
 * @return {bool}      Whether the connection is a valid connection that exists currently in the node system.
 */
$.oNodeLink.prototype.validate = function ( ) {
    //Initialize the connection and get the information.
    //First check to see if the path is valid.
    this._exists    = false;
    this._validated = true;

    var inportProvided  = !(!this._inPort && this._inPort!== 0);
    var outportProvided = !(!this._outPort && this._outPort!== 0);

    if( !inportProvided && !outportProvided ){
      //inport is the safest to determine contextually.
      //If either has 1 input.
      if( this._inNode && this._inNode.inNodes.length == 1 ){
        this._inPort = 0;
        inportProvided = true;
      }
    }

    if( !this._outNode && !this._inNode ){
      //Unable to comply, need at least the nodes.
      this._exists = false;
      return false;
    }else if( !this._outNode ){
      //No outnode. Just look for one above it given the inport.
      //Lets derive up the chain.
      if( inportProvided ){
        this.validateUpwards( this._inPort );

        if( !this.path || this.path.length==0 ){
          return false;
        }

        this._outNode     = this.path[ this.path.length-1 ].node;
        this._outPort     = this.path[ this.path.length-1 ].port;
        this._outLink     = this.path[ this.path.length-1 ].link;

        this._realOutNode = this.path[ 0 ].node;
        this._realOutPort = this.path[ 0 ].port;
        this._realOutLink = this.path[ 0 ].link;

        this._exists = true;
        return true;
      }
    }else if( !this._inNode ){
      //There can be multiple links. This is very difficult and only possible if theres only a singular path, we'll have to derive them all downwards.
      //This is just hopeful thinking that there is only one valid path.

      this._outLink = this._outLink ? this._outLink : 0;

      var huntInNode = function( currentNode, port, link ){
        try{
          // var on = currentNode.outNodes[port];
          var numOutLinks = currentNode.getOutLinksNumber(port);

          // if( on.length != 1 ){
          if( numOutLinks != 1 ){
            return false;
          }

          var dstNodeInfo = node.dstNodeInfo( currentNode.path, port, link );
          if( !dstNodeInfo ){
            return false;
          }

          var outNode = this.$.scene.getNodeByPath(node.dstNode( currentNode.path, port, 0 ))

          // if( on[0].type == "MULTIPORT_OUT" ){
          if( outNode.type == "MULTIPORT_OUT" ){
            return huntInNode( currentNode.grp, dstNodeInfo.port );
          // }else if( on[0].type == "GROUP" ){
          }else if( outNode.type == "GROUP" ){
            return huntInNode( outNode.multiportIn, dstNodeInfo.port, dstNodeInfo.link );
          }else{
            // var ret = { "node": on[0], "port":dstNodeInfo.port };
            var ret = { "node": outNode, "port":dstNodeInfo.port };
            return ret;
          }
        }catch(err){
          this.$.debug( err , this.$.DEBUG_LEVEL.ERROR);
          return false;
        }
      }

      //Find the in node recursively.
      var res = huntInNode( this._outNode, this._outPort, this._outLink );
      if( !res ){
        this._exists = false;
        return false;
      }

      if( inportProvided ){
        if( res.port != this._inPort ){
          this._exists = false;
          return false;
        }
      }

      this._inNode = res.node;
      this._inPort = res.port;
      inportProvided = true;
    }

    if( !this._outNode || !this._inNode ){
        this._exists = false;
        return false;
    }

    if( !inportProvided && !outportProvided ){
      //Still no ports provided.
      //Just simply assume the 0 port on the input.
      this._inPort = 0;
      inportProvided = true;
    }

    if( !inportProvided ){
      //Derive upwards for each input, if its valid, keep it.
      var inNodes = this._inNode.inNodes;
      for( var n=0;n<inNodes.length;n++ ){
        if( this.validateUpwards( n, outportProvided ) ){
          this._inPort = n;
          return true;
        }
      }
      return false;
    }

    return this.validateUpwards( this._inPort, outportProvided );
}


/**
 * Validates the a node upwards until it hits the target. Given an inport argument to scan.
 * @static
 * @private
 * @param   {int}                   inport                   The inport to scan.
 * @param   {bool}                  outportProvided          Was an outport provided.
 * @return {bool}      Whether the connection is a valid connection that exists currently in the node system.
 */
$.oNodeLink.prototype.validateUpwards = function( inport, outportProvided ) {
  //IN THE EVENT OUTNODE WASNT PROVIDED.
  this.path = this.findInputPath( this._inNode, inport, [] );
  if( !this.path || this.path.length == 0 ){
    return false;
  }

  var valid = false;
  for( var n=0;n<this.path.length;n++ ){
    if( this.path[n].node.path == this._outNode.path ){

      if( !outportProvided ){
        valid = this.path[n];
        break;
      }

      if( this.path[n].port == this._outPort ){
        valid = this.path[n];
        break;
      }
    }
  }

  if( !valid ){
    return false;
  }

  this._exists = true;
  this._outLink = valid.link;
  this._realOutNode = this.path[ 0 ].node;
  this._realOutPort = this.path[ 0 ].port;
  this._realOutLink = this.path[ 0 ].link;

  return true;
}



/**
 * Converts the node link to a string.
 */
$.oNodeLink.prototype.toString = function( ) {
  return '{"inNode":"'+this.inNode+'", "inPort":"'+this.inPort+'", "outNode":"'+this.outNode+'", "outPort":"'+this.outPort+'", "outLink":"'+this.outLink+'" }';
}





//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//           $.oLink class          //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * Constructor for $.oLink class
 * @classdesc
 * The $.oLink class models a connection between two nodes.<br>
 * A $.oLink object is always describing just one connection between two nodes in the same group. For distant nodes in separate groups, use $.oLinkPath.
 * @constructor
 * @param   {$.oNode}        outNode                         The node from which the link is coming out.
 * @param   {$.oNode}        inNode                          The node into which the link is connected.
 * @param   {oScene}         [outPortNum]                    The out-port of the outNode used by this link.
 * @param   {oScene}         [inPortNum]                     The in-port of the inNode used by this link.
 * @param   {oScene}         [outLinkNum]                    The link index coming out of the out-port.
 * @param   {bool}           [isValid=false]                 Bypass checks and assume this link is connected.
 * @example
 * // find out if two nodes are linked, and through which ports
 * var doc = $.scn;
 * var myNode = doc.root.$node("Drawing");
 * var sceneComp = doc.root.$node("Composite");
 *
 * var myLink = new $.oLink(myNode, sceneComp);
 *
 * log(myLink.linked+" "+myLink.inPort+" "+myLink.outPort+" "+myLink.outLink); // trace the details of the connection.
 *
 * // activate/deactivate connections simply:
 * myLink.connect();
 * log (myLink.linked)  // true
 *
 * myLink.disconnect();
 * log (myLink.linked)  // false
 *
 * // it is also possible to set the linked status directly on the linked property:
 * myLink.linked = true;
 *
 * // however, changing the ports of the link object don't physically change the connection
 *
 * myLink.inPort = 2    // the connection didn't change, the link object simply represents now a different connection possible.
 * log (myLink.linked)  // false
 *
 * myLink.connect()     // this will connect the nodes once more, with different ports. A new connection is created.
 */
$.oLink = function(outNode, inNode, outPortNum, inPortNum, outLinkNum, isValid){
  this._outNode = outNode;
  this._inNode = inNode;
  this._outPort = (typeof outPortNum !== 'undefined')? outPortNum:undefined;
  this._outLink = (typeof outLinkNum !== 'undefined')? outLinkNum:undefined;
  this._inPort = (typeof inPortNum !== 'undefined')? inPortNum:undefined;
  this._linked = (typeof isValid !== 'undefined')? isValid:false;
}


/**
 * The node that the link is coming out of. Changing this value doesn't reconnect the link, just changes the connection described by the link object.
 * @name $.oLink#outNode
 * @type {$.oNode}
 */Object.defineProperty($.oLink.prototype, 'outNode', {
  get : function(){
    return this._outNode;
  },

  set : function(newOutNode){
    this._outNode = newOutNode;
    this._linked = false;
  }
});


/**
 * The node that the link is connected into. Changing this value doesn't reconnect the link, just changes the connection described by the link object.
 * @name $.oLink#inNode
 * @type {$.oNode}
 */
Object.defineProperty($.oLink.prototype, 'inNode', {
  get : function(){
    return this._inNode;
  },

  set: function(newInNode){
    this._inNode = newInNode;
    this._linked = false;
  }
});


/**
 * The in-port used by the link. Changing this value doesn't reconnect the link, just changes the connection described by the link object.
 * <br>In the event this value wasn't known by the link object but the link is actually connected, the correct value will be found.
 * @name $.oLink#inPort
 * @type {int}
 */
Object.defineProperty($.oLink.prototype, 'inPort', {
  get : function(){
    if (this.linked) return this._inPort;  // cached value was correct

    var _found = this.findPorts();
    if (_found) return this._inPort;

    // nodes are not connected
    return null;
  },

  set : function(newInPort){
    this._inPort = newInPort;
    this._linked = false;
  }
});


/**
 * The out-port used by the link. Changing this value doesn't reconnect the link, just changes the connection described by the link object.
 * <br>In the event this value wasn't known by the link object but the link is actually connected, the correct value will be found.
 * @name $.oLink#outPort
 * @type {int}
 */
Object.defineProperty($.oLink.prototype, 'outPort', {
  get : function(){
    if (this.linked) return this._outPort;  // cached value was correct

    var _found = this.findPorts();
    if (_found) return this._outPort;

    // nodes are not connected
    return null;
  },

  set : function(newOutPort){
    this._outPort = newOutPort;
    this._linked = false;
  }
});


/**
 * The index of the link comming out of the out-port.
 * <br>In the event this value wasn't known by the link object but the link is actually connected, the correct value will be found.
 * @name $.oLink#outLink
 * @readonly
 * @type {int}
 */
Object.defineProperty($.oLink.prototype, 'outLink', {
  get : function(){
    if (this.linked) return this._outLink;

    var _found = this.findPorts();
    if (_found) return this._outLink;

    // nodes are not connected
    return null;
  }
});


/**
 * Get and set the linked status of a link
 * @name $.oLink#linked
 * @type {bool}
 */
Object.defineProperty($.oLink.prototype, 'linked', {
  get : function(){
    if (this._linked) return this._linked;

    // first check if node object refers to two valid nodes
    if (this.outNode === undefined || this.inNode === undefined){
      this.$.debug("checking 'linked' for invalid link: "+this.outNode+">"+this.inNode, this.$.DEBUG_LEVEL.ERROR)
      return false;
    }

    // if ports/links unknown, get a valid link we can check
    if (this._outPort === undefined || this._inPort === undefined || this._outLink === undefined){
      if (!this.findPorts()){
        return false;
      }
    }

    // if ports/links are specified, we check the if the nodes connected to each port correspond with the link values
    var _linkedOutNode = this.outNode.getLinkedOutNode(this._outPort, this._outLink);
    var _linkedInNode = this.inNode.getLinkedInNode(this._inPort);

    if (_linkedOutNode == null || _linkedInNode == null) return false;

    var validOutLink = (_linkedOutNode.path == this.inNode.path);
    var validInLink = (_linkedInNode.path == this.outNode.path);

    if (validOutLink && validInLink){
      this._linked = true;
      return true;
    }
    return false;
  },

  set : function(newLinkedStatus){
    if (newLinkedStatus){
      this.connect();
    }else{
      this.disconnect();
    }
  }
});


/**
 * Compares the start and end nodes groups to see if the path traverses several groups or not.
 * @name $.oLink#isMultiLevel
 * @readonly
 * @type {bool}
 */
Object.defineProperty($.oLink.prototype, 'isMultiLevel', {
  get : function(){
    //this.$.debug("isMultiLevel? "+this.outNode +" "+this.inNode, this.$.DEBUG_LEVEL.LOG);
    if (!this.outNode || !this.outNode.group || !this.inNode || !this.inNode.group) return false;
    return this.outNode.group.path != this.inNode.group.path;
  }
});


/**
 * Compares the start and end nodes groups to see if the path traverses several groups or not.
 * @name $.oLink#isMultiLevel
 * @readonly
 * @type {bool}
 */
Object.defineProperty($.oLink.prototype, 'waypoints', {
  get : function(){
    if (!this.linked) return []
    var _waypoints = waypoint.getAllWaypointsAbove (this.inNode, this.inPort)
    return _waypoints;
  }
});


/**
 * Get a link that can be connected by working out ports that can be used. If a link already exists, it will be returned.
 * @return {$.oLink} A separate $.oLink object that can be connected. Null if none could be constructed.
 */
$.oLink.prototype.getValidLink = function(createOutPorts, createInPorts){
  if (typeof createOutPorts === 'undefined') var createOutPorts = false;
  if (typeof createInPorts === 'undefined') var createInPorts = true;
  var start = this.outNode;
  var end = this.inNode;
  var outPort = this._outPort;
  var inPort = this._inPort;

  if (!start || !end) {
    $.debug("A valid link can't be found: node missing in link "+this.toString(), this.$.DEBUG_LEVEL.ERROR)
    return null;
  }

  if (this.isMultiLevel) return null;

  var _link = new this.$.oLink(start, end, outPort, inPort);
  _link.findPorts();

  // if can't be found, choose a new non existent link
  if (!_link.linked){
    if (typeof outPort === 'undefined' || outPort === undefined){
      _link._outPort = start.getFreeOutPort(createOutPorts);
      // if (_link._outPort == null) _link._outPort = 0; // just use a current port and add a link
    }

    _link._outLink = start.getOutLinksNumber(_link._outPort);

    if (typeof inPort === 'undefined' || inPort === undefined){
      _link._inPort = end.getFreeInPort(createInPorts);
      if (_link._inPort == null){
        this.$.debug("can't create link because the node "+end+" can't create a free inPort", this.$.DEBUG_LEVEL.ERROR);
        return null; // can't create a valid link.
      }

    }else{
      _link._inPort = inPort;

      if (end.getInLinksNumber(inPort)!= 0 && !end.canCreateInPorts){
        this.$.debug("can't create link because the requested port "+_link._inPort+" of node "+end+" isn't free", this.$.DEBUG_LEVEL.ERROR);
        return null;
      }
    }
  }

  return _link;
}


/**
 * Attemps to connect a link. Will guess the ports if not provided.
 * @return {bool}
 */
$.oLink.prototype.connect = function(){
  if (this._linked){
    return true;
  }

  // do we want to just always get a valid link here or do we want it to fail if not set properly?
  if (!this.findPorts()){
    var _validLink = this.getValidLink(this.outNode.canCreateInPorts, this.inNode.canCreateInPorts);
    if (!_validLink) return false;
    this.inPort = _validLink.inPort;
    this.outPort = _validLink.outPort;
    this.outLink = _validLink.outLink;
  };

  if (this.inNode.getInLinksNumber(this._inPort) > 0 && !this.inNode.canCreateInPorts) return false; // can't connect if the in-port is already connected

  var createOutPorts = (this.outNode.outPorts <= this._outPort && this.outNode.canCreateOutPorts);
  var createInPorts = ((this.inNode.inPorts <= this._inPort || this.inNode.getInLinksNumber(this._inPort)>0) && this.inNode.canCreateInPorts);

  if (this._outNode.type == "GROUP" && createOutPorts) this._outNode.addOutPort(this._outPort);
  if (this._inNode.type == "GROUP" && createInPorts) this._inNode.addInPort(this._inPort);

  try{
    this.$.debug("linking nodes "+this._outNode+" to "+this._inNode+" through outPort: "+this._outPort+", inPort: "+this._inPort+" and create ports: "+createOutPorts+" "+createInPorts, this.$.DEBUG_LEVEL.LOG);

    var success = node.link(this._outNode, this._outPort, this._inNode, this._inPort, createOutPorts, createInPorts);
    this._linked = success;

    if (!success) throw new Error();
    return success;

  }catch(err){
    this.$.debug("linking nodes "+this._outNode+" to "+this._inNode+" through outPort: "+this._outPort+", inPort: "+this._inPort+", create outports: "+createOutPorts+", create inports:"+createInPorts, this.$.DEBUG_LEVEL.ERROR);
    this.$.debug("Error linking nodes: " +err, this.$.DEBUG_LEVEL.ERROR);
    return false;
  }
}


/**
 * Disconnects a link.
 * @return {bool} Whether disconnecting was successful;
 */
$.oLink.prototype.disconnect = function(){
  if (!this._linked) return true;

  if (!this.findPorts()) return false;

  node.unlink(this._inNode, this._inPort);
  this._linked = false;
  return true;
}


/**
 * Finds ports missing or undefined ports in the link object if it is linked, and update the object accordingly. <br>
 * This will not update ports if the link isn't connected. Use getValidLink to get a connectable unconnected link.
 * @private
 * @return {bool} Whether finding ports was successful.
 */
$.oLink.prototype.findPorts = function(){
  // Unless some ports are specified, this will always find the first link and stop there. Provide more info in case of multiple links

  if (!this.outNode|| !this.inNode) {
    this.$.debug("calling 'findPorts' for invalid link: "+this.outNode+" > "+this.inNode, this.$.DEBUG_LEVEL.ERROR);
    return false;
  }

  if (this._inPort !== undefined && this._outPort!== undefined && this._outLink!== undefined) return true; // ports already are valid, even if link might not be linked

  var _inNodePath = this.inNode.path;
  var _outNodePath = this.outNode.path;

  // Try to find outPort based on inPort
  // most likely to be missing is outLink, and this is the quickest way to find it.
  if (this._inPort != undefined){
    var _nodeInfo = node.srcNodeInfo(_inNodePath, this._inPort);
    if (_nodeInfo && _nodeInfo.node == _outNodePath && (this._outPort == undefined || this._outPort == _nodeInfo.port)){
      this._outPort = _nodeInfo.port;
      this._outLink = _nodeInfo.link;
      this._linked = true;

      // this.$.log("found ports through provided inPort: "+ this._inPort)
      return true;
    }
  }

  // Try to find ports based on outLink/outPort
  if (this._outPort !== undefined && this._outLink !== undefined){
    var _nodeInfo = node.dstNodeInfo(_outNodePath, this._outPort, this._outLink);
    if (_nodeInfo && _nodeInfo.node == _inNodePath){
      this._inPort = _nodeInfo.port;
      this._linked = true;

      // this.$.log("found ports through provided outPort/outLink: "+this._outPort+" "+this._outLink)
      return true;
    }
  }

  // Find the ports if we are missing all of them, looking at in-ports to avoid messing with outLinks
  var _inPorts = this.inNode.inPorts;
  for (var i = 0; i<_inPorts; i++){
    var _nodeInfo = node.srcNodeInfo(_inNodePath, i);
    if (_nodeInfo && _nodeInfo.node == _outNodePath){
      if (this._outPort !== undefined && this._outPort !== _nodeInfo.port) continue;

      this._inPort = i;
      this._outPort = _nodeInfo.port;
      this._outLink = _nodeInfo.link;

      // this.$.log("found ports through iterations")
      this._linked = true;

      return true;
    }
  }

  // The nodes are not linked
  this._linked = false;
  return false;
}


/**
 * Connects the given node in the middle of the link. The link must be connected.
 * @param {$.oNode} oNode          The node to insert in the link
 * @param {int} [nodeInPort = 0]   The inPort to use on the inserted node
 * @param {int} [nodeOutPort = 0]  The outPort to use on the inserted node
 * @param {int} [nodeOutLink = 0]  The outLink to use on the inserted node
 * @return {$.oLink[]}   an Array of two oLink objects that describe the new connections.
 * @example
 * include("openHarmony.js")
 * doc = $.scn
 * var node1 = doc.$node("Top/Drawing")
 * var node2 = doc.$node("Top/Composite")
 * var node3 = doc.$node("Top/Transparency")
 *
 * var link = new $.oLink(node1, node2)
 * link.insertNode(node3) // insert the Transparency node between the Drawing and Composite
 */
$.oLink.prototype.insertNode = function(oNode, nodeInPort, nodeOutPort, nodeOutLink){
  if (!this.linked) return    // can't insert a node if the link isn't connected

  this.$.beginUndo("oh_insertNode")

  var _inNode = this.inNode
  var _outNode = this.outNode
  var _inPort = this.inPort
  var _outPort = this.outPort
  var _outLink = this.outLink

  var _topLink = new this.$.oLink(_outNode, oNode, _outPort, nodeInPort, _outLink)
  var _lowerLink = new this.$.oLink(oNode, _inNode, nodeOutPort, _inPort, nodeOutLink)

  this.linked = false;
  var success = (_topLink.connect() && _lowerLink.connect());

  this.$.endUndo()

  if (success) {
    return [_topLink, _lowerLink]
  } else{
    // we restore the links to default state and return false
    this.$.debug("failed to insert node "+oNode+" into link "+this)
    this.$.undo()
    return false
  }
}

/**
 * Converts the node link to a string.
 * @private
 */
$.oLink.prototype.toString = function( ) {
  return ('link: {"'+this._outNode+'" ['+this._outPort+', '+this._outLink+'] -> "'+this._inNode+'" ['+this._inPort+']} linked:'+this._linked);
  // return '{outNode:'+this.outNode+' inNode:'+this.inNode+' }';
}




//////////////////////////////////////
//////////////////////////////////////
//                                  //
//                                  //
//        $.oLinkPath class         //
//                                  //
//                                  //
//////////////////////////////////////
//////////////////////////////////////


/**
 * Constructor for $.oLinkPath class
 * @classdesc
 * The $.oLinkPath class allows to figure out paths as a series of links between distant nodes.<br>
 * It can either look for existing paths and check that two distant nodes are connected or create new ones that can then be connected.
 * @constructor
 * @param   {$.oNode}        startNode                       The first node from which the link is coming out.
 * @param   {$.oNode}        endNode                         The last node into which the link is connected.
 * @param   {oScene}         [outPortNum]                    The out-port of the startNode.
 * @param   {oScene}         [inPortNum]                     The in-port of the endNode.
 * @param   {oScene}         [outLinkNum]                    The link index coming out of the out-port of the startNode.
 * @see NodeType
 */
$.oLinkPath = function( startNode, endNode, outPort, inPort, outLink){
  this.startNode = startNode;
  this.endNode = endNode;
  this.outPort = (typeof outPort !== 'undefined')? outPort:undefined;
  this.inPort = (typeof inPort !== 'undefined')? inPort:undefined;
  this.outLink = (typeof outLink !== 'undefined')? outLink:undefined;
}


/**
 * Compares the start and end nodes groups to see if the path traverses several groups or not.
 * @name $.oLinkPath#isMultiLevel
 * @readonly
 * @type {bool}
 */
Object.defineProperty($.oLinkPath.prototype, 'isMultiLevel', {
  get : function(){
    //this.$.log(this.startNode+" "+this.endNode)
    return this.startNode.group.path != this.endNode.group.path;
  }
});


/**
 * Identifies the group in which the two nodes will connect if they are at different levels of depth.
 * @name $.oLinkPath#lowestCommonGroup
 * @readonly
 * @type {$.oGroupNode}
 */
Object.defineProperty($.oLinkPath.prototype, 'lowestCommonGroup', {
  get : function(){
    var startPath = this.startNode.group.path.split("/");
    var endPath = this.endNode.group.path.split("/");

    var commonPath = [];
    for (var i=0; i<startPath.length; i++){
      if (startPath[i] != endPath[i]) break;
      commonPath.push(startPath[i]);
    }

    return this.$.scene.getNodeByPath(commonPath.join("/"));
  }
});


/**
 * Finds an existing path if one exists between two distant nodes.
 *
 * @return {$.oLink[]} The list of successive $.oLink objects describing the path. Returns null if no such path could be found.
 */
$.oLinkPath.prototype.findExistingPath = function(){
  // looking for the startNode from the endNode going up since the hierarchy is usually simpler this direction
  // if inPort is provided, we assume it's correct or a search filter, otherwise look up all inLinks
  var _searchPorts = (this.inPort !== undefined)?[this.inPort]:Array.apply(null, new Array(this.endNode.inPorts)).map(function (x, i) {return i;});

  for (var i = 0; i<_searchPorts.length; i++){
    var _inLink = this.endNode.getInLink(_searchPorts[i]);
    if (_inLink == null) continue; // if no node is connected, this branch is a dead end;

    var _connectedInNode = _inLink.outNode;

    // start looking again from the corresponding node
    if(_connectedInNode.path == this.startNode.path){
      // check that we have the valid outPort/outLink if provided as search filter
      if (this.outPort !== undefined && _inLink.outPort != this.outPort) return null;
      if (this.outLink !== undefined && _inLink.outLink != this.outLink) return null;

      return [_inLink]; // we found the node
    }else if (_connectedInNode.type == "MULTIPORT_IN"){
      _connectedInNode = _connectedInNode.group;
    }else if (_connectedInNode.type == "GROUP"){
      _connectedInNode = _connectedInNode.multiportOut;
    }else{
      // stop looking? any other nodes we want to traverse? Composites?
      continue;
    }

    var _searchLink = new this.$.oLinkPath(this.startNode, _connectedInNode, this.outPort, _inLink.outPort, this.outLink);
    var _path = _searchLink.findExistingPath();

    if (_path == null) return null; // this branch is a dead end

    _path.push(_inLink);
    return _path;
  }

  // we couldn't find a path
  return null
}


/**
 * Gets a link object from two nodes that can be succesfully connected. Provide port numbers if there are specific requirements to match. If a link already exists, it will be returned.
 * @param  {$.oNode}         start          The node from which the link originates.
 * @param  {$.oNode}         end            The node at which the link ends.
 * @param  {int}             [outPort]      A prefered out-port for the link to use.
 * @param  {int}             [inPort]       A prefered in-port for the link to use.
 *
 * @return {$.oLink} the valid $.oLink object.  Returns null if no such link could be created (for example if the node's in-port is already linked)
 */
$.oLinkPath.prototype.getValidLink = function(start, end, outPort, inPort){
  var _link = new $.oLink(start, end, outPort, inPort)
  return _link.getValidLink();
}


/**
 * Finds a valid path between two distant nodes, even if one doesn't currently exist.
 *
 * @return {$.oLink[]}     The list of links needed for the path. Some can already be connected.
 */
$.oLinkPath.prototype.findNewPath = function(){
  // look for the lowest common group we will have to reach first
  subLinks = [];
  var commonGroup = this.lowestCommonGroup;

  //get links out of the start group until the common group
  var _startPath = [];
  var _node = this.startNode;
  var _preferedOutPort = this.outPort;

  while (_node.group.path != commonGroup.path){
    var _linkOutNode = _node;
    var _linkInNode = _node.group.multiportOut;

    // look for an existing link to reuse
    var _link = this.getValidLink(_linkOutNode, _linkInNode, _preferedOutPort);
    _startPath.push(_link);

    // prepare for next step
    _node = _node.group
    _preferedOutPort = _link.inPort;
  }
  var startGroup = _node;


  // get links out of the end group until the common group
  var _endPath = []
  _node = this.endNode;
  var _preferedInPort = this.inPort;

  while (_node.group.path != commonGroup.path){
    var _linkOutNode = _node.group.multiportIn;
    var _linkInNode = _node;

    // look for an existing link to reuse
    var _link = this.getValidLink(_linkOutNode, _linkInNode, undefined, _preferedInPort);
    _endPath.unshift(_link);

    // prepare for next step
    _node = _node.group;
    _preferedInPort = _link.OutPort;
  }

  var endGroup = _node;

  var _link = this.getValidLink(startGroup, endGroup, _preferedOutPort, _preferedInPort);
  _startPath.push(_link)

  var _path = _startPath.concat(_endPath)
  this.$.log(_path.join("\n"))

  return _path
}


/**
 * Connects all the unconnected links between two distant nodes
 * @return {$.oLink[]} return the list of links present in the created path
 */

$.oLinkPath.prototype.connectPath = function(){
  var newPath = this.findNewPath();

  for (var i in newPath){
    newPath[i].connect();
  }

  return newPath;
}