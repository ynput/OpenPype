/**
 *  Load the Open Harmony Library as needed.
 */
try{
  var oh_incl = preferences.getString( 'openHarmonyIncludeDebug', false );
  if( oh_incl=="false" ) oh_incl = preferences.getString( 'openHarmonyInclude', false );
  if( oh_incl=="false" ) oh_incl = "openHarmony.js";
  include(oh_incl);
}catch(err){
  MessageBox.information ("OpenHarmony is not installed. Get it here: \nhttps://github.com/cfourney/OpenHarmony")
}


/**
 *  Smart key button. Only adds a key if a column already exists. Maintains sections that are tweens and other sections that are stop-motion/holds.
 */
function oh_anim_smartKey(){
  System.println("");
  
  scene.beginUndoRedoAccum( "oh_anim_smartKey" );
  
  var timeline = $.scene.getTimeline();
  var layers   = timeline.selectedLayers;
  
  //--------------------------------------------------
  //--- The key function, used 
    
  var smart_key_item = function( attr ){
    var cfrm  = $.scene.currentFrame; 
    
    var frame = attr.frames[ cfrm ];

    
    if( attr.node.type == "READ" ){
      
      if( attr.column.type == "DRAWING" ){
        frame.isKeyFrame = true;
        return;
      }
      
      //DONT KEY THE OFFSETS IF ITS NOT ANIMATEABLE.
      var check_pos = {
                        "offset.x"        : true,
                        "offset.y"        : true,
                        "offset.z"        : true,
                        "skew"            : true,
                        "scale.x"         : true,
                        "scale.y"         : true,
                        "scale.z"         : true,
                        "rotation.anglez" : true
                      }
      if( !attr.node["can_animate"] ){
        return;
      }
    }
    
    if( !frame.isKeyFrame ){
      var lk    = frame.keyframeLeft;
      frame.isKeyFrame = true;
      
      if(!lk){
        //Consider this as static.
        frame.constant   = true;
      }else{
        if( lk.constant ){
          frame.constant   = true;
          // lk.constant      = true;   //UNNECESSARY, DEFAULT APPRAOCH TO isKeyFrame = true;
        }else{
          var rk    = frame.keyframeRight;
          
          if( rk ){
            //Something is to the right, keep the tween.
            frame.constant   = false;
            // lk.constant      = false;   //UNNECESSARY, DEFAULT APPRAOCH TO isKeyFrame = true;
          }else{
            frame.constant   = true;
            lk.constant      = true;
          }
        }
      }
    }
  }
  
  
  if( layers.length == 0 ){
    var layers = timeline.compositionLayers;
    
    var items = [];
    for( var n=0;n<layers.length;n++ ){
      var tlayer = layers[n];
      for( var attrname in tlayer.attributes ){
        var tattr = tlayer.attributes[ attrname ];
        if( tattr.column ){
          smart_key_item( tattr );
        }else{
          for( var tt=0;tt<tattr.subAttributes.length;tt++ ){
            var subattr = tattr.subAttributes[tt];
            if( subattr.column ){
              smart_key_item( subattr );
            }
          }
        }
      }
    }
  }else{
    //Selected layers are sufficient.
    for( var n=0;n<layers.length;n++ ){
      var tlayer = layers[n];
      if( tlayer.attribute ){
        if( tlayer.attribute.column ){  
          smart_key_item( tlayer.attribute );
        }
      }
    }
  }

  System.println( "END" );
  scene.endUndoRedoAccum( );
}