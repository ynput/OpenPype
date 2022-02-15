var docstringStart = "/**"
var docstringEnd = "*/"
/*
// values outputted by following script:
function traceAll(){
  var globalMessage = [docstringStart+"\n * Attributes associated to Node types\n * @class NodeTypes \n "+docstringEnd];
  var nodes = selection.selectedNodes()

  for (var i in nodes){
    var message = [
      "Attributes present in the node : " + node.getName(nodes[i]),
      "@name  NodeTypes#"+ node.type(nodes[i])
    ]
    message = message.concat(node.getAttrList( nodes[i], 1).map(function(x){return traceAttributes(x, nodes[i]));
    message = ("\n "+docstringStart+"\n * ")+message.join("\n * ")+("\n "+docstringEnd+"\n");
    globalMessage.push(message);
  }

  MessageLog.trace(globalMessage.join("\n"));
}

function traceAttributes(attribute, theNode){
  var message = [formatAttribute(attribute, theNode)];
  if (attribute.hasSubAttributes()){
    var subattributes = attribute.getSubAttributes();
    for (var i in subattributes){
      message = message.concat(traceAttributes(subattributes[i], theNode));
    }
  }
  return message
}

function formatAttribute(attr, theNode){
  var keyword = attr.fullKeyword();
  var type = attr.typeName().toLowerCase();
  var name = attr.name();
  var defaultValue = node.getTextAttr(theNode, 1, keyword).split(" ").join("_").replace(".0000", "");
  if (defaultValue == "N") defaultValue = "false";
  if (defaultValue == "Y") defaultValue = "true";
  var message = "@property {"+type+"}  "+keyword.toLowerCase()+((defaultValue)?"="+defaultValue:"")+"   - "+name+"."
  return message;
}
*/

/**
 * Attributes associated to Node types.<br>These are the types to specify when creating a node, and the corresponding usual node name when creating directly through Harmony's interface. The attributes displayed here can be set and manipulated by calling the displayed names.
 * @class NodeTypes
 * @hideconstructor
 * @namespace
 * @example
 * // This is how to use this page:
 *
 * var myNode = $.scn.root.addNode("READ");        // This is the node type as specified for each node under the default display name.
 * $.log(myNode.type)                              // This is how to find out the type
 *
 * myNode.drawing.element = "1"                    // Sets the drawing.element attribute to display drawing "1"
 *
 * myNode.drawing.element = {frameNumber: 5, "2"}  // If the attribute can be animated, pass a {frameNumber, value} object to set a specific frame;
 *
 * myNode.attributes.drawing.element.setValue ("2", 5)   // also possible to set the attribute directly.
 *
 * // refer to the node type on this page to find out what properties can be set with what synthax for each Node Type.
 */

/**
 * Attributes present in the node of type: 'MasterController'
 * @name  NodeTypes#MasterController
 * @property {string}  [specs_editor="<specs>
  <ports>
    <in type="IMAGE"/>
    <out type="IMAGE"/>
  </ports>
  <attributes>
  </attributes>
</specs>
"]   - Specifications.
 * @property {file_editor}  script_editor   - .
 * @property {file_editor}  init_script   - .
 * @property {file_editor}  cleanup_script   - .
 * @property {file_editor}  ui_script   - .
 * @property {string}  ui_data   - .
 * @property {file_library}  files   - .
 * @property {generic_enum}  [show_controls_mode="Normal"]   - Show Controls Mode.
 */


/**
 * Attributes present in the node of type: 'ShapeCurve'
 * @name  NodeTypes#Shape-Curve
 * @property {bool}  flattenz=true   - Flatten Z.
 * @property {position_3d}  position1   - Position 1.
 * @property {bool}  position1.separate=On   - Separate.
 * @property {double}  position1.x=0   - Pos x.
 * @property {double}  position1.y=0   - Pos y.
 * @property {double}  position1.z=0   - Pos z.
 * @property {path_3d}  position1.3dpath   - Path.
 * @property {position_3d}  position2   - Left Handle Offset.
 * @property {bool}  position2.separate=On   - Separate.
 * @property {double}  position2.x=0   - Pos x.
 * @property {double}  position2.y=-1   - Pos y.
 * @property {double}  position2.z=0   - Pos z.
 * @property {path_3d}  position2.3dpath   - Path.
 * @property {position_3d}  position3   - Right Handle Offset.
 * @property {bool}  position3.separate=On   - Separate.
 * @property {double}  position3.x=0   - Pos x.
 * @property {double}  position3.y=1   - Pos y.
 * @property {double}  position3.z=0   - Pos z.
 * @property {path_3d}  position3.3dpath   - Path.
 * @property {bool}  closeshape=false   - Close Shape Contour.
 */


/**
 * Attributes present in the node of type: 'SubNodeAnimation'
 * @name  NodeTypes#Subnode-Animation
 */


/**
 * Attributes present in the node of type: 'BoneModule'
 * @name  NodeTypes#Stick
 * @property {generic_enum}  [influencetype="Infinite"]   - Influence Type.
 * @property {double}  influencefade=0.5000   - Influence Fade Radius.
 * @property {bool}  symmetric=true   - Symmetric Ellipse of Influence.
 * @property {double}  transversalradius=1   - Transversal Influence Radius Left.
 * @property {double}  transversalradiusright=1   - Transversal Influence Radius Right.
 * @property {double}  longitudinalradiusbegin=1   - Longitudinal Influence Radius Begin.
 * @property {double}  longitudinalradius=1   - Longitudinal Influence Radius End.
 * @property {double}  restlength=3   - Rest Length.
 * @property {double}  length=3   - Length.
 */


/**
 * Attributes present in the node of type: 'CurveModule'
 * @name  NodeTypes#Curve
 * @property {bool}  localreferential=true   - Apply Parent Transformation.
 * @property {generic_enum}  [influencetype="Infinite"]   - Influence Type.
 * @property {double}  influencefade=0.5000   - Influence Fade Radius.
 * @property {bool}  symmetric=true   - Symmetric Ellipse of Influence.
 * @property {double}  transversalradius=1   - Transversal Influence Radius Left.
 * @property {double}  transversalradiusright=1   - Transversal Influence Radius Right.
 * @property {double}  longitudinalradiusbegin=1   - Longitudinal Influence Radius Begin.
 * @property {double}  longitudinalradius=1   - Longitudinal Influence Radius End.
 * @property {bool}  closepath=false   - Close Contour.
 * @property {double}  restlength0=2   - Rest Length 0.
 * @property {double}  restingorientation0=0   - Resting Orientation 0.
 * @property {position_2d}  restingoffset   - Resting Offset.
 * @property {bool}  restingoffset.separate=On   - Separate.
 * @property {double}  restingoffset.x=6   - Pos x.
 * @property {double}  restingoffset.y=0   - Pos y.
 * @property {double}  restlength1=2   - Rest Length 1.
 * @property {double}  restingorientation1=0   - Resting Orientation 1.
 * @property {double}  length0=2   - Length 0.
 * @property {double}  orientation0=0   - Orientation 0.
 * @property {position_2d}  offset   - Offset.
 * @property {bool}  offset.separate=On   - Separate.
 * @property {double}  offset.x=6   - Pos x.
 * @property {double}  offset.y=0   - Pos y.
 * @property {point_2d}  offset.2dpoint   - Point.
 * @property {double}  length1=2   - Length 1.
 * @property {double}  orientation1=0   - Orientation 1.
 */


/**
 * Attributes present in the node of type: 'BendyBoneModule'
 * @name  NodeTypes#Bone
 * @property {generic_enum}  [influencetype="Infinite"]   - Influence Type.
 * @property {double}  influencefade=0.5000   - Influence Fade Radius.
 * @property {bool}  symmetric=true   - Symmetric Ellipse of Influence.
 * @property {double}  transversalradius=1   - Transversal Influence Radius Left.
 * @property {double}  transversalradiusright=1   - Transversal Influence Radius Right.
 * @property {double}  longitudinalradiusbegin=1   - Longitudinal Influence Radius Begin.
 * @property {double}  longitudinalradius=1   - Longitudinal Influence Radius End.
 * @property {position_2d}  restoffset   - Rest Offset.
 * @property {bool}  restoffset.separate=On   - Separate.
 * @property {double}  restoffset.x=0   - Pos x.
 * @property {double}  restoffset.y=0   - Pos y.
 * @property {double}  restorientation=0   - Rest Orientation.
 * @property {double}  restradius=0.5000   - Rest Radius.
 * @property {double}  restbias=0.4500   - Rest Bias.
 * @property {double}  restlength=3   - Rest Length.
 * @property {position_2d}  offset   - Offset.
 * @property {bool}  offset.separate=On   - Separate.
 * @property {double}  offset.x=0   - Pos x.
 * @property {double}  offset.y=0   - Pos y.
 * @property {point_2d}  offset.2dpoint   - Point.
 * @property {double}  orientation=0   - Orientation.
 * @property {double}  radius=0.5000   - Radius.
 * @property {double}  bias=0.4500   - Bias.
 * @property {double}  length=3   - Length.
 */


/**
 * Attributes present in the node of type: 'ShapeRender'
 * @name  NodeTypes#Shape-Render
 * @property {generic_enum}  [edgetype="Hard Edge"]   - Edge Type.
 * @property {double}  scale=25   - Scale.
 * @property {double}  discretizationscale=5   - Discretization Scale.
 * @property {double}  preblur=0   - Pre-Blur.
 * @property {double}  postblur=0   - Post-Blur.
 */


/**
 * Attributes present in the node of type: 'NormalFloat'
 * @name  NodeTypes#Normal-Map-Converter
 * @property {generic_enum}  [conversiontype="Genarts"]   - Conversion Type.
 * @property {double}  offset=0   - Offset.
 * @property {double}  length=1   - Length.
 * @property {bool}  invertred=false   - Invert Red.
 * @property {bool}  invertgreen=false   - Invert Green.
 * @property {bool}  invertblue=false   - Invert Blue.
 */


/**
 * Attributes present in the node of type: 'GameBoneModule'
 * @name  NodeTypes#Game-Bone
 * @property {position_2d}  restoffset   - Rest Offset.
 * @property {bool}  restoffset.separate=On   - Separate.
 * @property {double}  restoffset.x=0   - Pos x.
 * @property {double}  restoffset.y=0   - Pos y.
 * @property {double}  restorientation=0   - Rest Orientation.
 * @property {double}  restradius=0.5000   - Rest Radius.
 * @property {double}  restbias=0.4500   - Rest Bias.
 * @property {double}  restlength=3   - Rest Length.
 * @property {position_2d}  offset   - Offset.
 * @property {bool}  offset.separate=On   - Separate.
 * @property {double}  offset.x=0   - Pos x.
 * @property {double}  offset.y=0   - Pos y.
 * @property {point_2d}  offset.2dpoint   - Point.
 * @property {double}  orientation=0   - Orientation.
 * @property {double}  radius=0.5000   - Radius.
 * @property {double}  bias=0.4500   - Bias.
 * @property {double}  length=3   - Length.
 */


/**
 * Attributes present in the node of type: 'OffsetModule'
 * @name  NodeTypes#Offset
 * @property {bool}  localreferential=true   - Apply Parent Transformation.
 * @property {position_2d}  restingoffset   - Resting Offset.
 * @property {bool}  restingoffset.separate=On   - Separate.
 * @property {double}  restingoffset.x=1   - Pos x.
 * @property {double}  restingoffset.y=0   - Pos y.
 * @property {double}  restingorientation=0   - Resting Orientation.
 * @property {position_2d}  offset   - Offset.
 * @property {bool}  offset.separate=On   - Separate.
 * @property {double}  offset.x=1   - Pos x.
 * @property {double}  offset.y=0   - Pos y.
 * @property {point_2d}  offset.2dpoint   - Point.
 * @property {double}  orientation=0   - Orientation.
 */


/**
 * Attributes present in the node of type: 'ArticulationModule'
 * @name  NodeTypes#Articulation
 * @property {generic_enum}  [influencetype="Infinite"]   - Influence Type.
 * @property {double}  influencefade=0.5000   - Influence Fade Radius.
 * @property {bool}  symmetric=true   - Symmetric Ellipse of Influence.
 * @property {double}  transversalradius=1   - Transversal Influence Radius Left.
 * @property {double}  transversalradiusright=1   - Transversal Influence Radius Right.
 * @property {double}  longitudinalradiusbegin=1   - Longitudinal Influence Radius Begin.
 * @property {double}  longitudinalradius=1   - Longitudinal Influence Radius End.
 * @property {double}  restradius=0.5000   - Rest Radius.
 * @property {double}  restingorientation=0   - Resting Orientation.
 * @property {double}  restbias=0.4500   - Rest Bias.
 * @property {double}  radius=0.5000   - Radius.
 * @property {double}  orientation=0   - Orientation.
 * @property {double}  bias=0.4500   - Bias.
 */


/**
 * Attributes present in the node of type: 'TransformGate'
 * @name  NodeTypes#Transformation-Gate
 * @property {double}  active=100   - ACTIVE.
 * @property {int}  target_gate=1   - LOCAL TARGET GATE.
 * @property {int}  default_gate=0   - DEFAULT GATE.
 */


/**
 * Attributes present in the node of type: 'ParticleBaker'
 * @name  NodeTypes#Particle-Baker
 * @property {int}  maxnumparticles=10000   - Maximum Number of Particles.
 * @property {generic_enum}  [simulationquality="Normal"]   - Simulation Quality.
 * @property {int}  seed=0   - Seed.
 * @property {int}  transientframes=0   - Number of Pre-roll Frames.
 * @property {bool}  moveage=false   - Age Particles.
 * @property {bool}  moveposition=true   - Move Position.
 * @property {bool}  moveangle=false   - Move Angle.
 * @property {bool}  roundage=false   - Round Particle Age.
 */


/**
 * Attributes present in the node of type: 'KinematicOutputModule'
 * @name  NodeTypes#Kinematic-Output
 */


/**
 * Attributes present in the node of type: 'ParticleVisualizer'
 * @name  NodeTypes#Particle-Visualizer
 * @property {bool}  forcedots=false   - Force to Render as Dots.
 * @property {generic_enum}  [sortingstrategy="Back to Front"]   - Rendering Order.
 * @property {bool}  fixalpha=true   - Fix Output Alpha.
 * @property {bool}  useviewscaling=true   - Scale Particle System Using Parent Peg.
 * @property {double}  globalsize=1   - Global Scaling Factor.
 */


/**
 * Attributes present in the node of type: 'FreeFormDeformation'
 * @name  NodeTypes#Free-Form-Deformer
 * @property {generic_enum}  [deformationquality="Very High"]   - Deformation Quality.
 */


/**
 * Attributes present in the node of type: 'ComputeNormals'
 * @name  NodeTypes#Normal-Map
 * @property {string}  objectlist   - Volume Creation.
 * @property {bool}  depthinblue=false   - Output Elevation in Blue Channel.
 * @property {double}  blurscale=1   - Bevel Multiplier.
 * @property {bool}  clipblurredwithgeometry=true   - Clip Blurred Image with Geometry.
 * @property {double}  elevationscale=1   - Elevation Multiplier.
 * @property {double}  elevationsmoothness=1   - Elevation Smoothness Multiplier.
 * @property {bool}  generatenormals=true   - Generate Normals.
 * @property {generic_enum}  [normalquality="Low"]   - Normal Map Quality.
 * @property {bool}  usetruckfactor=false   - Consider Truck Factor.
 * @property {string}  colorinformation   - Colour Information.
 */


/**
 * Attributes present in the node of type: 'PointConstraint3'
 * @name  NodeTypes#Three-Points-Constraints
 * @property {double}  active=100   - Active.
 * @property {generic_enum}  [flattentype="Allow 3D Transform"]   - Flatten Type.
 * @property {generic_enum}  [transformtype="Translate"]   - Transform Type.
 * @property {generic_enum}  [primaryport="Right"]   - Primary Port.
 */


/**
 * Attributes present in the node of type: 'GROUP'
 * @name  NodeTypes#Group
 * @property {string}  [editor="<editor dockable="true" title="Script" winPreferred="640x460" linuxPreferred="640x480">
  <tab title="Editor" expand="true">
    <attr name="EDITOR"/>
  </tab>
  <tab title="Options">
    <attr name="TARGET_COMPOSITE"/>
    <attr name="TIMELINE_MODULE"/>
  </tab>
  <tab title="Extern Attributes">
    <!-- <attr name="GroupA/GroupB/Module:Attr1/SubAttr"/> -->
    <!-- <attr module="GroupA/GroupB/Module" name="Attr1/SubAttr"/> -->
  </tab>
</editor>

"]   - .
 * @property {string}  target_composite   - Target Composite.
 * @property {string}  timeline_module   - Substitute Node in Timeline.
 * @property {bool}  mask=false   - Mask Flag.
 * @property {bool}  publish_to_parents=true   - Publish to Parent Groups.
 */


/**
 * Attributes present in the node of type: 'ComputeWorld'
 * @name  NodeTypes#Surface-Map
 * @property {string}  objectlist   - Volume Creation.
 * @property {double}  blurscale=1   - Bevel Multiplier.
 * @property {bool}  clipblurredwithgeometry=true   - Clip Blurred Image with Geometry.
 * @property {double}  elevationscale=1   - Elevation Multiplier.
 * @property {double}  elevationsmoothness=1   - Elevation Smoothness Multiplier.
 * @property {bool}  usetruckfactor=false   - Consider Truck Factor.
 * @property {string}  colorinformation   - Colour Information.
 */


/**
 * Attributes present in the node of type: 'FOCUS_SET'
 * @name  NodeTypes#Focus
 * @property {bool}  mirror=true   - Mirror.
 * @property {double}  ratio=2   - Mirror Front/Back Ratio.
 * @property {simple_bezier}  radius=(Curve)   - Radius.
 * @property {generic_enum}  [quality="High"]   - Quality.
 */


/**
 * Attributes present in the node of type: 'SCRIPT_MODULE'
 * @name  NodeTypes#ScriptModule
 * @property {string}  [specs_editor="<specs>
  <ports>
    <in type="IMAGE"/>
    <out type="IMAGE"/>
  </ports>
  <attributes>
  </attributes>
</specs>
"]   - Specifications.
 * @property {file_editor}  script_editor   - .
 * @property {file_editor}  init_script   - .
 * @property {file_editor}  cleanup_script   - .
 * @property {file_editor}  ui_script   - .
 * @property {string}  ui_data   - .
 * @property {file_library}  files   - .
 */


/**
 * Attributes present in the node of type: 'StaticConstraint'
 * @name  NodeTypes#Static-Transformation
 * @property {push_button}  bakeattr   - Bake Immediate Parent's Transformation.
 * @property {push_button}  bakeattr_all   - Bake All Incoming Transformations.
 * @property {bool}  active=false   - Active.
 * @property {position_3d}  translate   - Translate.
 * @property {bool}  translate.separate=On   - Separate.
 * @property {double}  translate.x=0   - Pos x.
 * @property {double}  translate.y=0   - Pos y.
 * @property {double}  translate.z=0   - Pos z.
 * @property {scale_3d}  scale   - Skew.
 * @property {bool}  scale.separate=On   - Separate.
 * @property {bool}  scale.in_fields=Off   - In fields.
 * @property {doublevb}  scale.xy=1   - Scale.
 * @property {doublevb}  scale.x=1   - Scale x.
 * @property {doublevb}  scale.y=1   - Scale y.
 * @property {doublevb}  scale.z=1   - Scale z.
 * @property {rotation_3d}  rotate   - Rotate.
 * @property {bool}  rotate.separate=On   - Separate.
 * @property {doublevb}  rotate.anglex=0   - Angle_x.
 * @property {doublevb}  rotate.angley=0   - Angle_y.
 * @property {doublevb}  rotate.anglez=0   - Angle_z.
 * @property {double}  skewx=0   - Skew X.
 * @property {double}  skewy=0   - Skew Y.
 * @property {double}  skewz=0   - Skew Z.
 * @property {bool}  inverted=false   - Invert Transformation.
 */


/**
 * Attributes present in the node of type: 'GLCacheLock'
 * @name  NodeTypes#OpenGL-Cache-Lock
 * @property {bool}  composite_3d=false   - 3D.
 */


/**
 * Attributes present in the node of type: 'PLUGIN'
 * @name  NodeTypes#Brightness-Contrast
 * @property {double}  b=0   - Brightness.
 * @property {double}  c=0   - Contrast.
 */


/**
 * Attributes present in the node of type: 'PLUGIN'
 * @name  NodeTypes#Sparkle
 * @property {double}  angle=0   - Start angle.
 * @property {double}  scale=1   - Scale.
 * @property {double}  factor=0.7500   - Factor.
 * @property {double}  density=50   - Density.
 * @property {int}  n_points=8   - Number of Points.
 * @property {double}  prob_app=100   - Probability of Appearing.
 * @property {double}  point_noise=0   - Point Noise.
 * @property {double}  center_noise=0   - Center Noise.
 * @property {double}  angle_noise=0   - Angle Noise.
 * @property {int}  seed=0   - Random Seed.
 * @property {bool}  use_drawing_color=true   - Use Drawing Colours.
 * @property {bool}  flatten_sparkles_of_same_color=true   - Flatten Sparkles of Same Colour.
 * @property {color}  sparkle_color=80ffffff   - Sparkles' Colour.
 * @property {int}  sparkle_color.red=255   - Red.
 * @property {int}  sparkle_color.green=255   - Green.
 * @property {int}  sparkle_color.blue=255   - Blue.
 * @property {int}  sparkle_color.alpha=128   - Alpha.
 * @property {generic_enum}  [sparkle_color.preferred_ui="Separate"]   - Preferred Editor.
 */


/**
 * Attributes present in the node of type: 'WeightedDeform'
 * @name  NodeTypes#Weighted-Deform
 * @property {double}  blend=0   - Pre-Blend Amount.
 * @property {double}  postblend=0   - Post-Blend Amount.
 * @property {generic_enum}  [deformationquality="Very High"]   - Deformation Quality.
 */


/**
 * Attributes present in the node of type: 'BurnIn'
 * @name  NodeTypes#Burn-In
 * @property {bool}  drawbackgroundbox=false   - Add background box.
 * @property {color}  textcolor=ffffffff   - Text colour.
 * @property {int}  textcolor.red=255   - Red.
 * @property {int}  textcolor.green=255   - Green.
 * @property {int}  textcolor.blue=255   - Blue.
 * @property {int}  textcolor.alpha=255   - Alpha.
 * @property {generic_enum}  [textcolor.preferred_ui="Separate"]   - Preferred Editor.
 * @property {color}  backgroundcolor=ff000000   - Background colour.
 * @property {int}  backgroundcolor.red=0   - Red.
 * @property {int}  backgroundcolor.green=0   - Green.
 * @property {int}  backgroundcolor.blue=0   - Blue.
 * @property {int}  backgroundcolor.alpha=255   - Alpha.
 * @property {generic_enum}  [backgroundcolor.preferred_ui="Separate"]   - Preferred Editor.
 * @property {int}  size=36   - Size.
 * @property {int}  frameoffset=0   - Frame Offset.
 * @property {bool}  drawframenumber=true   - Frame Number.
 * @property {bool}  drawtimecode=true   - Time code.
 * @property {string}  [printinfo="Environment %e Job %j Scene %s"]   - Scene Name.
 * @property {generic_enum}  [alignment="Left"]   - Alignment.
 * @property {int}  font=Arial   - Font.
 */


/**
 * Attributes present in the node of type: 'TransformLimit'
 * @name  NodeTypes#Transformation-Limit
 * @property {double}  active=100   - Active.
 * @property {generic_enum}  [switchtype="Active Value"]   - Switch Effects.
 * @property {double}  tx=100   - Translate X.
 * @property {double}  ty=100   - Translate Y.
 * @property {double}  tz=100   - Translate Z.
 * @property {double}  rot=100   - Rotate.
 * @property {double}  skew=100   - Skew.
 * @property {double}  sx=100   - Scale X.
 * @property {double}  sy=100   - Scale Y.
 * @property {bool}  allowflip=true   - Allow Flipping.
 * @property {bool}  uniformscale=false   - Uniform Scale.
 * @property {double}  pignore=0   - Ignore Parents.
 * @property {string}  parentname   - Parent's Name.
 * @property {generic_enum}  [flattentype="Allow 3D Translate"]   - Flatten Type.
 * @property {generic_enum}  [skewtype="Skew Optimized for Rotation"]   - Skew Type.
 * @property {generic_enum}  [flipaxis="Allow Flip on X-Axis"]   - Flip Axis.
 * @property {position_2d}  pos   - Control Position.
 * @property {bool}  pos.separate=On   - Separate.
 * @property {double}  pos.x=0   - Pos x.
 * @property {double}  pos.y=0   - Pos y.
 * @property {point_2d}  pos.2dpoint   - Point.
 */


/**
 * Attributes present in the node of type: 'SCRIPT_MODULE'
 * @name  NodeTypes#Maya-Batch-Render
 * @property {string}  [specs_editor="
<specs>
  <ports>
    <in type="IMAGE"/>
    <out type="IMAGE"/>
  </ports>
  <attributes>
    <attr type="string" name="renderer" value="" tooltip="If this attribute is not set, then the MayaBatchRender node will use the default renderer specified in the Maya file. If this attribute is set, then it forces the use of a specific renderer other than the default. The following renderers are currently supported: 'renderMan' (renderMan version 22.0 or higher), 'renderManRIS' or 'RIS' (renderMan version 21.x or earlier), 'renderManReyes' or 'reyes' (renderMan version 20.x or earlier), 'arnold', 'mentalRay', 'mayaSoftware' or 'maya'. Note that those values are case insensitive."/>
  </attributes>
</specs>
"]   - Specifications.
 * @property {file_editor}  script_editor   - .
 * @property {file_editor}  init_script   - .
 * @property {file_editor}  cleanup_script   - .
 * @property {file_editor}  ui_script   - .
 * @property {string}  ui_data   - .
 * @property {file_library}  files   - .
 * @property {string}  renderer   - renderer.
 */


/**
 * Attributes present in the node of type: 'FIELD_CHART'
 * @name  NodeTypes#Field-Chart
 * @property {bool}  enable_3d=false   - Enable 3D.
 * @property {bool}  face_camera=false   - Face Camera.
 * @property {generic_enum}  [camera_alignment="None"]   - Camera Alignment.
 * @property {position_3d}  offset   - Position.
 * @property {bool}  offset.separate=On   - Separate.
 * @property {double}  offset.x=0   - Pos x.
 * @property {double}  offset.y=0   - Pos y.
 * @property {double}  offset.z=0   - Pos z.
 * @property {path_3d}  offset.3dpath   - Path.
 * @property {scale_3d}  scale   - Scale.
 * @property {bool}  scale.separate=On   - Separate.
 * @property {bool}  scale.in_fields=Off   - In fields.
 * @property {doublevb}  scale.xy=1   - Scale.
 * @property {doublevb}  scale.x=1   - Scale x.
 * @property {doublevb}  scale.y=1   - Scale y.
 * @property {doublevb}  scale.z=1   - Scale z.
 * @property {rotation_3d}  rotation   - Rotation.
 * @property {bool}  rotation.separate=Off   - Separate.
 * @property {doublevb}  rotation.anglex=0   - Angle_x.
 * @property {doublevb}  rotation.angley=0   - Angle_y.
 * @property {doublevb}  rotation.anglez=0   - Angle_z.
 * @property {quaternion_path}  rotation.quaternionpath   - Quaternion.
 * @property {alias}  angle=0   - Angle.
 * @property {double}  skew=0   - Skew.
 * @property {position_3d}  pivot   - Pivot.
 * @property {bool}  pivot.separate=On   - Separate.
 * @property {double}  pivot.x=0   - Pos x.
 * @property {double}  pivot.y=0   - Pos y.
 * @property {double}  pivot.z=0   - Pos z.
 * @property {position_3d}  spline_offset   - Spline Offset.
 * @property {bool}  spline_offset.separate=On   - Separate.
 * @property {double}  spline_offset.x=0   - Pos x.
 * @property {double}  spline_offset.y=0   - Pos y.
 * @property {double}  spline_offset.z=0   - Pos z.
 * @property {bool}  ignore_parent_peg_scaling=false   - Ignore Parent Scaling.
 * @property {bool}  disable_field_rendering=false   - Disable Field Rendering.
 * @property {int}  depth=0   - Depth.
 * @property {bool}  enable_min_max_angle=false   - Enable Min/Max Angle.
 * @property {double}  min_angle=-360   - Min Angle.
 * @property {double}  max_angle=360   - Max Angle.
 * @property {bool}  nail_for_children=false   - Nail for Children.
 * @property {bool}  ik_hold_orientation=false   - Hold Orientation in IK.
 * @property {bool}  ik_hold_x=false   - Hold X in IK.
 * @property {bool}  ik_hold_y=false   - Hold Y in IK.
 * @property {bool}  ik_excluded=false   - Is Excluded from IK.
 * @property {bool}  ik_can_rotate=true   - Can Rotate during IK.
 * @property {bool}  ik_can_translate_x=false   - Can Translate in X during IK.
 * @property {bool}  ik_can_translate_y=false   - Can Translate in Y during IK.
 * @property {double}  ik_bone_x=0.2000   - X Direction of Bone.
 * @property {double}  ik_bone_y=0   - Y Direction of Bone.
 * @property {double}  ik_stiffness=1   - Stiffness of Bone.
 * @property {drawing}  drawing   - Drawing.
 * @property {bool}  drawing.element_mode=On   - Element Mode.
 * @property {element}  drawing.element=unknown   - Element.
 * @property {string}  drawing.element.layer   - Layer.
 * @property {custom_name}  drawing.custom_name   - Custom Name.
 * @property {string}  drawing.custom_name.name   - Local Name.
 * @property {timing}  drawing.custom_name.timing   - Timing.
 * @property {string}  drawing.custom_name.extension=tga   - Extension.
 * @property {double}  drawing.custom_name.field_chart=12   - FieldChart.
 * @property {bool}  read_overlay=true   - Overlay Art Enabled.
 * @property {bool}  read_line_art=true   - Line Art Enabled.
 * @property {bool}  read_color_art=true   - Colour Art Enabled.
 * @property {bool}  read_underlay=true   - Underlay Art Enabled.
 * @property {generic_enum}  [overlay_art_drawing_mode="Vector"]   - Overlay Art Type.
 * @property {generic_enum}  [line_art_drawing_mode="Vector"]   - Line Art Type.
 * @property {generic_enum}  [color_art_drawing_mode="Vector"]   - Colour Art Type.
 * @property {generic_enum}  [underlay_art_drawing_mode="Vector"]   - Underlay Art Type.
 * @property {bool}  pencil_line_deformation_preserve_thickness=false   - Preserve Line Thickness.
 * @property {generic_enum}  [pencil_line_deformation_quality="Low"]   - Pencil Lines Quality.
 * @property {int}  pencil_line_deformation_smooth=1   - Pencil Lines Smoothing.
 * @property {double}  pencil_line_deformation_fit_error=3   - Fit Error.
 * @property {bool}  read_color=true   - Colour.
 * @property {bool}  read_transparency=true   - Transparency.
 * @property {generic_enum}  [color_transformation="Linear"]   - Colour Space.
 * @property {string}  color_space   - Colour Space.
 * @property {generic_enum}  [apply_matte_to_color="Premultiplied with Black"]   - Transparency Type.
 * @property {bool}  enable_line_texture=true   - Enable Line Texture.
 * @property {generic_enum}  [antialiasing_quality="Medium"]   - Antialiasing Quality.
 * @property {double}  antialiasing_exponent=1   - Antialiasing Exponent.
 * @property {double}  opacity=100   - Opacity.
 * @property {generic_enum}  [texture_filter="Nearest (Filtered)"]   - Texture Filter.
 * @property {bool}  adjust_pencil_thickness=false   - Adjust Pencil Lines Thickness.
 * @property {bool}  normal_line_art_thickness=true   - Normal Thickness.
 * @property {generic_enum}  [zoom_independent_line_art_thickness="Scale Independent"]   - Scale Independent.
 * @property {double}  mult_line_art_thickness=1   - Proportional.
 * @property {double}  add_line_art_thickness=0   - Constant.
 * @property {double}  min_line_art_thickness=0   - Minimum.
 * @property {double}  max_line_art_thickness=0   - Maximum.
 * @property {generic_enum}  [use_drawing_pivot="Apply Embedded Pivot on Drawing Layer"]   - Use Embedded Pivots.
 * @property {bool}  flip_hor=false   - Flip Horizontal.
 * @property {bool}  flip_vert=false   - Flip Vertical.
 * @property {bool}  turn_before_alignment=false   - Turn Before Alignment.
 * @property {bool}  no_clipping=false   - No Clipping.
 * @property {int}  x_clip_factor=0   - Clipping Factor (x).
 * @property {int}  y_clip_factor=0   - Clipping Factor (y).
 * @property {generic_enum}  [alignment_rule="Center First Page"]   - Alignment Rule.
 * @property {double}  morphing_velo=0   - Morphing Velocity.
 * @property {bool}  can_animate=true   - Animate Using Animation Tools.
 * @property {bool}  tile_horizontal=false   - Tile Horizontally.
 * @property {bool}  tile_vertical=false   - Tile Vertically.
 * @property {generic_enum}  [size="12"]   - Size.
 * @property {bool}  opaque=false   - Opaque.
 */


/**
 * Attributes present in the node of type: 'READ'
 * @name  NodeTypes#Drawing
 * @property {bool}  enable_3d=false   - Enable 3D.
 * @property {bool}  face_camera=false   - Face Camera.
 * @property {generic_enum}  [camera_alignment="None"]   - Camera Alignment.
 * @property {position_3d}  offset   - Position.
 * @property {bool}  offset.separate=On   - Separate.
 * @property {double}  offset.x=0   - Pos x.
 * @property {double}  offset.y=0   - Pos y.
 * @property {double}  offset.z=0   - Pos z.
 * @property {path_3d}  offset.3dpath   - Path.
 * @property {scale_3d}  scale   - Scale.
 * @property {bool}  scale.separate=On   - Separate.
 * @property {bool}  scale.in_fields=Off   - In fields.
 * @property {doublevb}  scale.xy=1   - Scale.
 * @property {doublevb}  scale.x=1   - Scale x.
 * @property {doublevb}  scale.y=1   - Scale y.
 * @property {doublevb}  scale.z=1   - Scale z.
 * @property {rotation_3d}  rotation   - Rotation.
 * @property {bool}  rotation.separate=Off   - Separate.
 * @property {doublevb}  rotation.anglex=0   - Angle_x.
 * @property {doublevb}  rotation.angley=0   - Angle_y.
 * @property {doublevb}  rotation.anglez=0   - Angle_z.
 * @property {quaternion_path}  rotation.quaternionpath   - Quaternion.
 * @property {alias}  angle=0   - Angle.
 * @property {double}  skew=0   - Skew.
 * @property {position_3d}  pivot   - Pivot.
 * @property {bool}  pivot.separate=On   - Separate.
 * @property {double}  pivot.x=0   - Pos x.
 * @property {double}  pivot.y=0   - Pos y.
 * @property {double}  pivot.z=0   - Pos z.
 * @property {position_3d}  spline_offset   - Spline Offset.
 * @property {bool}  spline_offset.separate=On   - Separate.
 * @property {double}  spline_offset.x=0   - Pos x.
 * @property {double}  spline_offset.y=0   - Pos y.
 * @property {double}  spline_offset.z=0   - Pos z.
 * @property {bool}  ignore_parent_peg_scaling=false   - Ignore Parent Scaling.
 * @property {bool}  disable_field_rendering=false   - Disable Field Rendering.
 * @property {int}  depth=0   - Depth.
 * @property {bool}  enable_min_max_angle=false   - Enable Min/Max Angle.
 * @property {double}  min_angle=-360   - Min Angle.
 * @property {double}  max_angle=360   - Max Angle.
 * @property {bool}  nail_for_children=false   - Nail for Children.
 * @property {bool}  ik_hold_orientation=false   - Hold Orientation in IK.
 * @property {bool}  ik_hold_x=false   - Hold X in IK.
 * @property {bool}  ik_hold_y=false   - Hold Y in IK.
 * @property {bool}  ik_excluded=false   - Is Excluded from IK.
 * @property {bool}  ik_can_rotate=true   - Can Rotate during IK.
 * @property {bool}  ik_can_translate_x=false   - Can Translate in X during IK.
 * @property {bool}  ik_can_translate_y=false   - Can Translate in Y during IK.
 * @property {double}  ik_bone_x=0.2000   - X Direction of Bone.
 * @property {double}  ik_bone_y=0   - Y Direction of Bone.
 * @property {double}  ik_stiffness=1   - Stiffness of Bone.
 * @property {drawing}  drawing=C:/Users/mathieuc/Documents/NewScene/elements/Drawing/Drawing-1.tvg   - Drawing.
 * @property {bool}  drawing.element_mode=On   - Element Mode.
 * @property {element}  drawing.element=unknown   - Element.
 * @property {string}  drawing.element.layer   - Layer.
 * @property {custom_name}  drawing.custom_name   - Custom Name.
 * @property {string}  drawing.custom_name.name   - Local Name.
 * @property {timing}  drawing.custom_name.timing   - Timing.
 * @property {string}  drawing.custom_name.extension=tga   - Extension.
 * @property {double}  drawing.custom_name.field_chart=12   - FieldChart.
 * @property {bool}  read_overlay=true   - Overlay Art Enabled.
 * @property {bool}  read_line_art=true   - Line Art Enabled.
 * @property {bool}  read_color_art=true   - Colour Art Enabled.
 * @property {bool}  read_underlay=true   - Underlay Art Enabled.
 * @property {generic_enum}  [overlay_art_drawing_mode="Vector"]   - Overlay Art Type.
 * @property {generic_enum}  [line_art_drawing_mode="Vector"]   - Line Art Type.
 * @property {generic_enum}  [color_art_drawing_mode="Vector"]   - Colour Art Type.
 * @property {generic_enum}  [underlay_art_drawing_mode="Vector"]   - Underlay Art Type.
 * @property {bool}  pencil_line_deformation_preserve_thickness=false   - Preserve Line Thickness.
 * @property {generic_enum}  [pencil_line_deformation_quality="Low"]   - Pencil Lines Quality.
 * @property {int}  pencil_line_deformation_smooth=1   - Pencil Lines Smoothing.
 * @property {double}  pencil_line_deformation_fit_error=3   - Fit Error.
 * @property {bool}  read_color=true   - Colour.
 * @property {bool}  read_transparency=true   - Transparency.
 * @property {generic_enum}  [color_transformation="Linear"]   - Colour Space.
 * @property {string}  color_space   - Colour Space.
 * @property {generic_enum}  [apply_matte_to_color="Premultiplied with Black"]   - Transparency Type.
 * @property {bool}  enable_line_texture=true   - Enable Line Texture.
 * @property {generic_enum}  [antialiasing_quality="High"]   - Antialiasing Quality.
 * @property {double}  antialiasing_exponent=1   - Antialiasing Exponent.
 * @property {double}  opacity=100   - Opacity.
 * @property {generic_enum}  [texture_filter="Nearest (Filtered)"]   - Texture Filter.
 * @property {bool}  adjust_pencil_thickness=false   - Adjust Pencil Lines Thickness.
 * @property {bool}  normal_line_art_thickness=true   - Normal Thickness.
 * @property {generic_enum}  [zoom_independent_line_art_thickness="Scale Independent"]   - Scale Independent.
 * @property {double}  mult_line_art_thickness=1   - Proportional.
 * @property {double}  add_line_art_thickness=0   - Constant.
 * @property {double}  min_line_art_thickness=0   - Minimum.
 * @property {double}  max_line_art_thickness=0   - Maximum.
 * @property {generic_enum}  [use_drawing_pivot="Apply Embedded Pivot on Drawing Layer"]   - Use Embedded Pivots.
 * @property {bool}  flip_hor=false   - Flip Horizontal.
 * @property {bool}  flip_vert=false   - Flip Vertical.
 * @property {bool}  turn_before_alignment=false   - Turn Before Alignment.
 * @property {bool}  no_clipping=false   - No Clipping.
 * @property {int}  x_clip_factor=0   - Clipping Factor (x).
 * @property {int}  y_clip_factor=0   - Clipping Factor (y).
 * @property {generic_enum}  [alignment_rule="Center First Page"]   - Alignment Rule.
 * @property {double}  morphing_velo=0   - Morphing Velocity.
 * @property {bool}  can_animate=false   - Animate Using Animation Tools.
 * @property {bool}  tile_horizontal=false   - Tile Horizontally.
 * @property {bool}  tile_vertical=false   - Tile Vertically.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'Shake'
 * @name  NodeTypes#Shake
 * @property {double}  frequency=0.3000   - Frequency.
 * @property {int}  octaves=2   - Octaves.
 * @property {double}  multiplier=0.5000   - Multiplier.
 * @property {double}  positionx=1   - Position X.
 * @property {double}  positiony=1.3300   - Position Y.
 * @property {double}  positionz=0.1000   - Position Z.
 * @property {double}  rotationx=0   - Rotation X.
 * @property {double}  rotationy=0   - Rotation Y.
 * @property {double}  rotationz=1   - Rotation Z.
 * @property {double}  pivotx=0   - Pivot X.
 * @property {double}  pivoty=0   - Pivot Y.
 * @property {double}  pivotz=0   - Pivot Z.
 * @property {int}  steps=1   - Steps.
 * @property {int}  seed=0   - Random Seed.
 */


/**
 * Attributes present in the node of type: 'QUADMAP'
 * @name  NodeTypes#Quadmap
 * @property {position_2d}  src_point_1   - Source Point 1.
 * @property {bool}  src_point_1.separate=On   - Separate.
 * @property {double}  src_point_1.x=-12   - Pos x.
 * @property {double}  src_point_1.y=12   - Pos y.
 * @property {point_2d}  src_point_1.2dpoint   - Point.
 * @property {position_2d}  src_point_2   - Source Point 2.
 * @property {bool}  src_point_2.separate=On   - Separate.
 * @property {double}  src_point_2.x=12   - Pos x.
 * @property {double}  src_point_2.y=12   - Pos y.
 * @property {point_2d}  src_point_2.2dpoint   - Point.
 * @property {position_2d}  src_point_3   - Source Point 3.
 * @property {bool}  src_point_3.separate=On   - Separate.
 * @property {double}  src_point_3.x=-12   - Pos x.
 * @property {double}  src_point_3.y=-12   - Pos y.
 * @property {point_2d}  src_point_3.2dpoint   - Point.
 * @property {position_2d}  src_point_4   - Source Point 4.
 * @property {bool}  src_point_4.separate=On   - Separate.
 * @property {double}  src_point_4.x=12   - Pos x.
 * @property {double}  src_point_4.y=-12   - Pos y.
 * @property {point_2d}  src_point_4.2dpoint   - Point.
 * @property {position_2d}  point_1   - Destination Point 1.
 * @property {bool}  point_1.separate=On   - Separate.
 * @property {double}  point_1.x=-12   - Pos x.
 * @property {double}  point_1.y=12   - Pos y.
 * @property {point_2d}  point_1.2dpoint   - Point.
 * @property {position_2d}  point_2   - Destination Point 2.
 * @property {bool}  point_2.separate=On   - Separate.
 * @property {double}  point_2.x=12   - Pos x.
 * @property {double}  point_2.y=12   - Pos y.
 * @property {point_2d}  point_2.2dpoint   - Point.
 * @property {position_2d}  point_3   - Destination Point 3.
 * @property {bool}  point_3.separate=On   - Separate.
 * @property {double}  point_3.x=-12   - Pos x.
 * @property {double}  point_3.y=-12   - Pos y.
 * @property {point_2d}  point_3.2dpoint   - Point.
 * @property {position_2d}  point_4   - Destination Point 4.
 * @property {bool}  point_4.separate=On   - Separate.
 * @property {double}  point_4.x=12   - Pos x.
 * @property {double}  point_4.y=-12   - Pos y.
 * @property {point_2d}  point_4.2dpoint   - Point.
 * @property {position_2d}  pivot   - Pivot.
 * @property {bool}  pivot.separate=On   - Separate.
 * @property {double}  pivot.x=0   - Pos x.
 * @property {double}  pivot.y=0   - Pos y.
 */


/**
 * Attributes present in the node of type: 'RADIALBLUR-PLUGIN'
 * @name  NodeTypes#Blur-Radial-Zoom
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {bool}  truck_factor=true   - Truck Factor.
 * @property {bool}  bidirectional=true   - Bidirectional.
 * @property {generic_enum}  [precision="Medium 8"]   - Precision.
 * @property {double}  blurriness=0   - Blurriness.
 * @property {double}  fall_off=0   - Fall Off.
 * @property {double}  spiral=0   - Custom.
 * @property {position_2d}  focus   - Focus.
 * @property {bool}  focus.separate=On   - Separate.
 * @property {double}  focus.x=0   - Pos x.
 * @property {double}  focus.y=0   - Pos y.
 * @property {point_2d}  focus.2dpoint   - Point.
 * @property {generic_enum}  [smoothness="Quadratic"]   - Variation.
 * @property {double}  quality=1   - Quality.
 * @property {bool}  legacy=false   - Legacy.
 */


/**
 * Attributes present in the node of type: 'CAMERA'
 * @name  NodeTypes#Camera
 * @property {position_3d}  offset   - Offset.
 * @property {bool}  offset.separate=On   - Separate.
 * @property {double}  offset.x=0   - Pos x.
 * @property {double}  offset.y=0   - Pos y.
 * @property {double}  offset.z=12   - Pos z.
 * @property {position_2d}  pivot   - Pivot.
 * @property {bool}  pivot.separate=On   - Separate.
 * @property {double}  pivot.x=0   - Pos x.
 * @property {double}  pivot.y=0   - Pos y.
 * @property {doublevb}  angle=0   - Angle.
 * @property {bool}  override_scene_fov=false   - Override Scene Fov.
 * @property {doublevb}  fov=41.1121   - FOV.
 * @property {double}  near_plane=0.1000   - Near Plane.
 * @property {double}  far_plane=1000   - Far Plane.
 */


/**
 * Attributes present in the node of type: 'COMPOSITE'
 * @name  NodeTypes#Composite
 * @property {generic_enum}  [composite_mode="Pass Through"]   - Mode.
 * @property {bool}  flatten_output=false   - Flatten Output.
 * @property {bool}  flatten_vector=false   - Vector Flatten Output.
 * @property {bool}  composite_2d=false   - 2D.
 * @property {bool}  composite_3d=false   - 3D.
 * @property {generic_enum}  [output_z="Leftmost"]   - Output Z.
 * @property {int}  output_z_input_port=1   - Port For Output Z.
 * @property {bool}  apply_focus=true   - Apply Focus.
 * @property {double}  multiplier=1   - Focus Multiplier.
 * @property {string}  tvg_palette=compositedPalette   - Palette Name.
 * @property {bool}  merge_vector=false   - Flatten.
 */


/**
 * Attributes present in the node of type: 'CastShadow'
 * @name  NodeTypes#Cast-Shadow
 * @property {generic_enum}  [lighttype="Point"]   - Light Type.
 * @property {generic_enum}  [shadetype="Smooth"]   - Shading Type.
 * @property {double}  anglebias=0   - Angle Bias.
 * @property {double}  shadowdarkness=100   - Shadow Darkness.
 * @property {double}  shadowlength=0   - Shadow Length.
 * @property {double}  shadowbias=0   - Shadow Bias.
 * @property {int}  samplecount=1   - Sample Count.
 * @property {double}  samplesize=0.5000   - Sample Size.
 * @property {int}  softcount=1   - Soft Shadow Sample Count.
 * @property {double}  softsize=1   - Soft Shadow Sample Size.
 * @property {double}  softweight=1   - Soft Shadow Weight.
 * @property {double}  postblur=0   - Final Blur.
 * @property {double}  postblurthreshold=0   - Final Blur Threshold.
 * @property {double}  shadownoise=0   - Shadow Noise.
 * @property {int}  expandsource=0   - Expand Render Source.
 * @property {double}  shadowgamma=1   - Shadow Gamma.
 * @property {int}  antialiasbias=1   - Anti-Alias Bias.
 * @property {int}  antialiasblend=1   - Anti-Alias Blend.
 * @property {int}  antialiasblur=1   - Anti-Alias Blur.
 * @property {double}  exponent=2   - Abruptness.
 * @property {color}  color=ff000000   - Light Colour.
 * @property {int}  color.red=0   - Red.
 * @property {int}  color.green=0   - Green.
 * @property {int}  color.blue=0   - Blue.
 * @property {int}  color.alpha=255   - Alpha.
 * @property {generic_enum}  [color.preferred_ui="Separate"]   - Preferred Editor.
 * @property {bool}  useimagecolor=false   - Use Image Colour.
 * @property {double}  imagecolorweight=50   - Image Colour Intensity.
 * @property {bool}  usetruckfactor=true   - Consider Truck Factor.
 * @property {bool}  polarmethod=false   - Use Polar Method.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'PRECOMP'
 * @name  NodeTypes#Pre-render-Cache
 * @property {generic_enum}  [composite_mode="As Bitmap"]   - Mode.
 * @property {bool}  flatten_output=true   - Flatten Output.
 * @property {bool}  flatten_vector=false   - Vector Flatten Output.
 * @property {bool}  composite_2d=false   - 2D.
 * @property {bool}  composite_3d=false   - 3D.
 * @property {generic_enum}  [output_z="Leftmost"]   - Output Z.
 * @property {int}  output_z_input_port=1   - Port For Output Z.
 * @property {bool}  apply_focus=true   - Apply Focus.
 * @property {double}  multiplier=1   - Focus Multiplier.
 * @property {string}  tvg_palette=compositedPalette   - Palette Name.
 * @property {bool}  merge_vector=false   - Flatten.
 * @property {bool}  prerender_current_frame=false   - Current Frame.
 * @property {bool}  prerender_selected_frames=false   - Selected Frames.
 * @property {int}  prerender_frames_from=1   - From.
 * @property {int}  prerender_frames_to=1   - To.
 * @property {push_button}  render_prerender_cache   - Render.
 * @property {push_button}  clear_prerender_cache   - Clear.
 */


/**
 * Attributes present in the node of type: 'MATTE_COMPOSITE'
 * @name  NodeTypes#Matte-Composite
 */


/**
 * Attributes present in the node of type: 'TransformationSwitch'
 * @name  NodeTypes#Transformation-Switch
 * @property {drawing}  drawing   - Drawing.
 * @property {bool}  drawing.element_mode=On   - Element Mode.
 * @property {element}  drawing.element=unknown   - Element.
 * @property {string}  drawing.element.layer   - Layer.
 * @property {custom_name}  drawing.custom_name   - Custom Name.
 * @property {string}  drawing.custom_name.name   - Local Name.
 * @property {timing}  drawing.custom_name.timing   - Timing.
 * @property {string}  drawing.custom_name.extension=tga   - Extension.
 * @property {double}  drawing.custom_name.field_chart=12   - FieldChart.
 * @property {array_string}  transformationnames=2;;   - Transformation Names.
 * @property {int}  transformationnames.size=2   - Size.
 * @property {string}  transformationnames.transformation_1   - Transformation 1.
 * @property {string}  transformationnames.transformation_2   - Transformation 2.
 */


/**
 * Attributes present in the node of type: 'MOTION_BLUR'
 * @name  NodeTypes#Motion-Blur-Legacy
 * @property {double}  nb_frames_trail=10   - Number of Frames in the Trail.
 * @property {double}  samples=200   - Number of Samples.
 * @property {double}  falloff=2   - Fall-off Rate.
 * @property {double}  intensity=1   - Intensity.
 * @property {bool}  mirror=false   - Use Mirror on Edges.
 */


/**
 * Attributes present in the node of type: 'BLUR_VARIABLE'
 * @name  NodeTypes#Blur-Variable
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {double}  black_radius=0   - Black radius.
 * @property {double}  white_radius=0   - White radius.
 * @property {generic_enum}  [quality="High"]   - Quality.
 * @property {bool}  keep_inside_source_image=false   - Keep inside source image.
 */


/**
 * Attributes present in the node of type: 'LAYER_SELECTOR'
 * @name  NodeTypes#Layer-Selector
 * @property {bool}  flatten=false   - Flatten.
 * @property {bool}  apply_to_matte_ports=false   - Apply to Matte Ports on Input Effects.
 * @property {generic_enum}  [antialiasing_quality="Ignore"]   - Antialiasing Quality.
 * @property {double}  antialiasing_exponent=1   - Antialiasing Exponent.
 * @property {bool}  read_overlay=false   - Read Overlay.
 * @property {bool}  read_lineart=true   - Read LineArt.
 * @property {bool}  read_colourart=true   - Read ColourArt.
 * @property {bool}  read_underlay=false   - Read Underlay.
 */


/**
 * Attributes present in the node of type: 'MOTIONBLUR-PLUGIN'
 * @name  NodeTypes#Motion-Blur
 * @property {double}  nb_frames_trail=1   - Duration (Number of Frames).
 * @property {int}  samples=30   - Samples per Frame.
 * @property {double}  falloff=0   - Fall-off Rate.
 * @property {bool}  use_camera_transformation=false   - Use Camera Motion.
 * @property {bool}  preroll_motion=true   - Preroll Motion.
 */


/**
 * Attributes present in the node of type: 'COLOR_CARD'
 * @name  NodeTypes#Colour-Card
 * @property {int}  depth=0   - Depth.
 * @property {double}  offset_z=-12   - Offset Z.
 * @property {color}  color=ffffffff   - Color.
 * @property {int}  color.red=255   - Red.
 * @property {int}  color.green=255   - Green.
 * @property {int}  color.blue=255   - Blue.
 * @property {int}  color.alpha=255   - Alpha.
 * @property {generic_enum}  [color.preferred_ui="Separate"]   - Preferred Editor.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'TransformLoop'
 * @name  NodeTypes#Transform-Loop
 * @property {bool}  autorange=true   - Automatic Range Detection.
 * @property {int}  rangestart=1   -     Start.
 * @property {int}  rangeend=1   -     End.
 * @property {generic_enum}  [looptype="Repeat"]   - Loop Type.
 */


/**
 * Attributes present in the node of type: 'COLOR_MASK'
 * @name  NodeTypes#Channel-Selector
 * @property {bool}  red=true   - Red.
 * @property {bool}  green=true   - Green.
 * @property {bool}  blue=true   - Blue.
 * @property {bool}  alpha=true   - Alpha.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'SCALE'
 * @name  NodeTypes#Scale-Output
 * @property {bool}  by_value=true   - Custom Resolution.
 * @property {string}  resolution_name   - Resolution Name.
 * @property {int}  res_x=720   - Width.
 * @property {int}  res_y=540   - Height.
 */


/**
 * Attributes present in the node of type: 'COLOR_LEVELS'
 * @name  NodeTypes#Colour-Levels
 * @property {levels-channel-params-attribute}  rgb   - RGB.
 * @property {double}  rgb.input_black=0   - Input Black.
 * @property {double}  rgb.input_white=1   - Input White.
 * @property {double}  rgb.gamma=1   - Gamma.
 * @property {double}  rgb.output_black=0   - Output Black.
 * @property {double}  rgb.output_white=1   - Output White.
 * @property {levels-channel-params-attribute}  red   - Red.
 * @property {double}  red.input_black=0   - Input Black.
 * @property {double}  red.input_white=1   - Input White.
 * @property {double}  red.gamma=1   - Gamma.
 * @property {double}  red.output_black=0   - Output Black.
 * @property {double}  red.output_white=1   - Output White.
 * @property {levels-channel-params-attribute}  green   - Green.
 * @property {double}  green.input_black=0   - Input Black.
 * @property {double}  green.input_white=1   - Input White.
 * @property {double}  green.gamma=1   - Gamma.
 * @property {double}  green.output_black=0   - Output Black.
 * @property {double}  green.output_white=1   - Output White.
 * @property {levels-channel-params-attribute}  blue   - Blue.
 * @property {double}  blue.input_black=0   - Input Black.
 * @property {double}  blue.input_white=1   - Input White.
 * @property {double}  blue.gamma=1   - Gamma.
 * @property {double}  blue.output_black=0   - Output Black.
 * @property {double}  blue.output_white=1   - Output White.
 * @property {levels-channel-params-attribute}  alpha   - Alpha.
 * @property {double}  alpha.input_black=0   - Input Black.
 * @property {double}  alpha.input_white=1   - Input White.
 * @property {double}  alpha.gamma=1   - Gamma.
 * @property {double}  alpha.output_black=0   - Output Black.
 * @property {double}  alpha.output_white=1   - Output White.
 */


/**
 * Attributes present in the node of type: 'COLOR_FADE'
 * @name  NodeTypes#Colour-Fade
 * @property {double}  fadefactor=100   - Fade.
 * @property {generic_enum}  [colorspace="RGB"]   - Colour Interpolation.
 * @property {generic_enum}  [hueinterpolation="Linear"]   - Hue Interpolation.
 */


/**
 * Attributes present in the node of type: 'Gamma'
 * @name  NodeTypes#Gamma
 * @property {double}  rgb_gamma=1   - RGB Gamma.
 * @property {double}  red_gamma=1   - Red Gamma.
 * @property {double}  green_gamma=1   - Green Gamma.
 * @property {double}  blue_gamma=1   - Blue Gamma.
 * @property {double}  alpha_gamma=1   - Alpha Gamma.
 */


/**
 * Attributes present in the node of type: 'DITHER'
 * @name  NodeTypes#Dither
 * @property {double}  magnitude=1   - Magnitude.
 * @property {bool}  correlate=false   - Correlate.
 * @property {bool}  random=true   - Random.
 */


/**
 * Attributes present in the node of type: 'GRAIN'
 * @name  NodeTypes#Grain
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {double}  noise=0.3000   - Noise.
 * @property {double}  smooth=0   - Smooth.
 * @property {bool}  random=true   - Random At Each Frame.
 * @property {int}  seed=0   - Seed Value.
 */


/**
 * Attributes present in the node of type: 'ShapeLine'
 * @name  NodeTypes#Shape-Line
 * @property {bool}  flattenz=true   - Flatten Z.
 * @property {position_3d}  position1   - Position 1.
 * @property {bool}  position1.separate=On   - Separate.
 * @property {double}  position1.x=0   - Pos x.
 * @property {double}  position1.y=0   - Pos y.
 * @property {double}  position1.z=0   - Pos z.
 * @property {path_3d}  position1.3dpath   - Path.
 * @property {bool}  closeshape=false   - Close Shape Contour.
 */


/**
 * Attributes present in the node of type: 'COMPOSITE_GENERIC'
 * @name  NodeTypes#Composite-Generic
 * @property {generic_enum}  [color_operation="Apply With Alpha"]   - Colour Operation.
 * @property {double}  intensity_color_red=1   - Intensity Red.
 * @property {double}  intensity_color_blue=1   - Intensity Blue.
 * @property {double}  intensity_color_green=1   - Intensity Green.
 * @property {double}  opacity=100   - Opacity.
 * @property {generic_enum}  [alpha_operation="Apply"]   - Alpha Operation.
 * @property {generic_enum}  [output_z="Leftmost"]   - Output Z.
 * @property {int}  output_z_input_port=1   - Port For Output Z.
 */


/**
 * Attributes present in the node of type: 'COLOR_ART'
 * @name  NodeTypes#Colour-Art
 * @property {bool}  flatten=false   - Flatten.
 * @property {bool}  apply_to_matte_ports=false   - Apply to Matte Ports on Input Effects.
 * @property {generic_enum}  [antialiasing_quality="Ignore"]   - Antialiasing Quality.
 * @property {double}  antialiasing_exponent=1   - Antialiasing Exponent.
 */


/**
 * Attributes present in the node of type: 'UNDERLAY'
 * @name  NodeTypes#Underlay-Layer
 * @property {bool}  flatten=false   - Flatten.
 * @property {bool}  apply_to_matte_ports=false   - Apply to Matte Ports on Input Effects.
 * @property {generic_enum}  [antialiasing_quality="Ignore"]   - Antialiasing Quality.
 * @property {double}  antialiasing_exponent=1   - Antialiasing Exponent.
 */


/**
 * Attributes present in the node of type: 'CUTTER'
 * @name  NodeTypes#Cutter
 * @property {bool}  inverted=false   - Inverted.
 */


/**
 * Attributes present in the node of type: 'FOCUS_APPLY'
 * @name  NodeTypes#Focus-Multiplier
 * @property {double}  multiplier=1   - Multiplier.
 */


/**
 * Attributes present in the node of type: 'PEG_APPLY3'
 * @name  NodeTypes#Apply-Image-Transformation
 */


/**
 * Attributes present in the node of type: 'PEG_APPLY3_V2'
 * @name  NodeTypes#Apply-Peg-Transformation
 */


/**
 * Attributes present in the node of type: 'LINE_ART'
 * @name  NodeTypes#Line-Art
 * @property {bool}  flatten=false   - Flatten.
 * @property {bool}  apply_to_matte_ports=false   - Apply to Matte Ports on Input Effects.
 * @property {generic_enum}  [antialiasing_quality="Ignore"]   - Antialiasing Quality.
 * @property {double}  antialiasing_exponent=1   - Antialiasing Exponent.
 */


/**
 * Attributes present in the node of type: 'OVERLAY'
 * @name  NodeTypes#Overlay-Layer
 * @property {bool}  flatten=false   - Flatten.
 * @property {bool}  apply_to_matte_ports=false   - Apply to Matte Ports on Input Effects.
 * @property {generic_enum}  [antialiasing_quality="Ignore"]   - Antialiasing Quality.
 * @property {double}  antialiasing_exponent=1   - Antialiasing Exponent.
 */


/**
 * Attributes present in the node of type: 'AutoPatchModule'
 * @name  NodeTypes#Auto-Patch
 */


/**
 * Attributes present in the node of type: 'SubNodeAnimationFilter'
 * @name  NodeTypes#3D-Kinematic-Output
 * @property {string}  sub_node_name   - Subnode Name.
 */


/**
 * Attributes present in the node of type: 'BOXBLUR-PLUGIN'
 * @name  NodeTypes#Blur-Box
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {bool}  truck_factor=true   - Truck Factor.
 * @property {bool}  bidirectional=true   - Bidirectional.
 * @property {generic_enum}  [precision="Medium 8"]   - Precision.
 * @property {bool}  repeat_edge_pixels=false   - Repeat Edge Pixels.
 * @property {bool}  directional=false   - Directional.
 * @property {double}  angle=0   - Angle.
 * @property {int}  iterations=1   - Number of Iterations.
 * @property {double}  radius=0   - Radius.
 * @property {double}  width=0   - Width.
 * @property {double}  length=0   - Length.
 * @property {double}  fall_off=0   - Fall Off.
 */


/**
 * Attributes present in the node of type: 'RGB_DIFFERENCE_KEYER'
 * @name  NodeTypes#RGB-Difference-Keyer
 * @property {color}  color=ff000000   - Colour.
 * @property {int}  color.red=0   - Red.
 * @property {int}  color.green=0   - Green.
 * @property {int}  color.blue=0   - Blue.
 * @property {int}  color.alpha=255   - Alpha.
 * @property {generic_enum}  [color.preferred_ui="Separate"]   - Preferred Editor.
 * @property {bool}  pre_multiplied_alpha=true   - Pre-multiplied Alpha.
 * @property {double}  key_difference_weighting=50   - Key Weight.
 * @property {double}  edge_key_threshold=0   - Background Bias.
 * @property {double}  key_primary_spill_reduction=0   - Spill Reduction.
 * @property {double}  key_low_intensity_scaled_thresh=100   - Low Intensity Threshold.
 * @property {bool}  blend_input_alpha=true   - Blend Input Alpha.
 * @property {bool}  despill_matte=true   - Despill Matte.
 * @property {color}  spill_color=ff000000   - Spill Replace Colour.
 * @property {int}  spill_color.red=0   - Red.
 * @property {int}  spill_color.green=0   - Green.
 * @property {int}  spill_color.blue=0   - Blue.
 * @property {int}  spill_color.alpha=255   - Alpha.
 * @property {generic_enum}  [spill_color.preferred_ui="Separate"]   - Preferred Editor.
 * @property {double}  matte_clip_black=0   - Clip Black.
 * @property {double}  matte_clip_white=100   - Clip White.
 * @property {bool}  invert_matte=false   - Invert Output Matte.
 */


/**
 * Attributes present in the node of type: 'CHANNEL_SWAP'
 * @name  NodeTypes#Channel-Swap
 * @property {generic_enum}  [redchannelselection="Red"]   - Red Channel From.
 * @property {generic_enum}  [greenchannelselection="Green"]   - Green Channel From.
 * @property {generic_enum}  [bluechannelselection="Blue"]   - Blue Channel From.
 * @property {generic_enum}  [alphachannelselection="Alpha"]   - Alpha Channel From.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'FADE'
 * @name  NodeTypes#Transparency
 * @property {double}  transparency=50   - Transparency.
 */


/**
 * Attributes present in the node of type: 'OGLBYPASS'
 * @name  NodeTypes#OpenGL-Bypass
 */


/**
 * Attributes present in the node of type: 'NOTE'
 * @name  NodeTypes#Note
 * @property {string}  text   - Text.
 */


/**
 * Attributes present in the node of type: 'OpenGLPreview'
 * @name  NodeTypes#RenderPreview
 * @property {generic_enum}  [refreshstrategy="Current Frame Only"]   - Render.
 * @property {generic_enum}  [scaling="Use Render Preview Setting"]   - Preview Resolution.
 * @property {generic_enum}  [renderstrategy="Use Previously Rendered"]   - Outdated Images Mode.
 * @property {push_button}  computeallimages   - Render Frames.
 */


/**
 * Attributes present in the node of type: 'TbdColorSelector'
 * @name  NodeTypes#Colour-Selector
 * @property {string}  selectedcolors   - Selected Colours.
 * @property {bool}  applytomatte=false   - Apply to Matte Ports on Input Effects.
 */


/**
 * Attributes present in the node of type: 'COLOR_OVERRIDE_TVG'
 * @name  NodeTypes#Colour-Override
 */


/**
 * Attributes present in the node of type: 'FLATTEN'
 * @name  NodeTypes#Flatten
 */


/**
 * Attributes present in the node of type: 'DISPLAY'
 * @name  NodeTypes#Display
 */


/**
 * Attributes present in the node of type: 'DynamicSpring'
 * @name  NodeTypes#Dynamic-Spring
 * @property {double}  active=100   - Active.
 * @property {bool}  matchexposures=false   - Match Animation on Active Attribute.
 * @property {double}  tensionx=7   - Tension X.
 * @property {double}  inertiax=80   - Inertia X.
 * @property {double}  tensiony=7   - Tension Y.
 * @property {double}  inertiay=80   - Inertia Y.
 * @property {double}  tensionz=7   - Tension Z.
 * @property {double}  inertiaz=80   - Inertia Z.
 * @property {double}  tensionscale=7   - Tension Scale.
 * @property {double}  inertiascale=80   - Inertia Scale.
 * @property {double}  tensionskew=7   - Tension Skew.
 * @property {double}  inertiaskew=80   - Inertia Skew.
 * @property {double}  tensionrotate=7   - Tension Rotate.
 * @property {double}  inertiarotate=80   - Inertia Rotate.
 * @property {double}  pignore=0   - Ignore Parents.
 * @property {string}  parentname   - Parent's Name.
 */


/**
 * Attributes present in the node of type: 'WRITE'
 * @name  NodeTypes#Write
 * @property {generic_enum}  [export_to_movie="Output Drawings"]   - Export to movie.
 * @property {string}  drawing_name=frames/final-   - Drawing name.
 * @property {string}  movie_path=frames/output   - Movie path.
 * @property {string}  movie_format=com.toonboom.quicktime.legacy   - Movie format setting.
 * @property {string}  movie_audio   - Movie audio settings.
 * @property {string}  movie_video   - Movie video settings.
 * @property {string}  movie_videoaudio   - Movie video and audio settings.
 * @property {int}  leading_zeros=3   - Leading zeros.
 * @property {int}  start=1   - Start.
 * @property {string}  drawing_type=TGA   - Drawing type.
 * @property {enable}  [enabling="Always Enabled"]   - Enabling.
 * @property {generic_enum}  [enabling.filter="Always Enabled"]   - Filter.
 * @property {string}  enabling.filter_name   - Filter name.
 * @property {int}  enabling.filter_res_x=720   - X resolution.
 * @property {int}  enabling.filter_res_y=540   - Y resolution.
 * @property {bool}  script_movie=false   - Script Movie.
 * @property {string}  [script_editor="// Following code will be called at the end of Write Node rendering
// operations to create a movie file from rendered images.

// ..."]   - Movie Generation Script.
 * @property {string}  color_space   - Colour Space.
 * @property {generic_enum}  [composite_partitioning="Off"]   - Composite Partitioning.
 * @property {double}  z_partition_range=1   - Z Partition Range.
 * @property {bool}  clean_up_partition_folders=true   - Clean up partition folders.
 */


/**
 * Attributes present in the node of type: 'MultiLayerWrite'
 * @name  NodeTypes#Multi-Layer-Write
 * @property {generic_enum}  [export_to_movie="Output Drawings"]   - Export to movie.
 * @property {string}  drawing_name=frames/final-   - Drawing name.
 * @property {string}  movie_path=frames/output   - Movie path.
 * @property {string}  movie_format=com.toonboom.quicktime.legacy   - Movie format setting.
 * @property {string}  movie_audio   - Movie audio settings.
 * @property {string}  movie_video   - Movie video settings.
 * @property {string}  movie_videoaudio   - Movie video and audio settings.
 * @property {int}  leading_zeros=3   - Leading zeros.
 * @property {int}  start=1   - Start.
 * @property {string}  drawing_type=PSD   - Drawing type.
 * @property {enable}  [enabling="Always Enabled"]   - Enabling.
 * @property {generic_enum}  [enabling.filter="Always Enabled"]   - Filter.
 * @property {string}  enabling.filter_name   - Filter name.
 * @property {int}  enabling.filter_res_x=720   - X resolution.
 * @property {int}  enabling.filter_res_y=540   - Y resolution.
 * @property {bool}  script_movie=false   - Script Movie.
 * @property {string}  [script_editor="// Following code will be called at the end of Write Node rendering
// operations to create a movie file from rendered images.

// ..."]   - Movie Generation Script.
 * @property {string}  color_space   - Colour Space.
 * @property {generic_enum}  [composite_partitioning="Off"]   - Composite Partitioning.
 * @property {double}  z_partition_range=1   - Z Partition Range.
 * @property {bool}  clean_up_partition_folders=true   - Clean up partition folders.
 * @property {string}  input_names   - Input Names.
 */


/**
 * Attributes present in the node of type: 'BLUR_DIRECTIONAL'
 * @name  NodeTypes#Blur-Directional
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {bool}  truck_factor=true   - Truck Factor.
 * @property {double}  fallof_rate=0   - Falloff Rate.
 * @property {double}  angle=0   - Angle.
 * @property {double}  radius=0   - Radius.
 * @property {generic_enum}  [direction_of_trail="Angle"]   - Direction of trail.
 * @property {bool}  ignore_alpha=false   - Ignore Alpha.
 * @property {bool}  extra_final_blur=true   - Extra Final Blur.
 */


/**
 * Attributes present in the node of type: 'TONE'
 * @name  NodeTypes#Tone
 * @property {bool}  truck_factor=true   - Truck Factor.
 * @property {generic_enum}  [blur_type="Radial"]   - Blur Type.
 * @property {double}  radius=2   - Radius.
 * @property {double}  directional_angle=0   - Directional Angle.
 * @property {double}  directional_falloff_rate=1   - Directional Falloff Rate.
 * @property {bool}  use_matte_color=false   - Use Matte Colour.
 * @property {bool}  invert_matte=false   - Invert Matte.
 * @property {color}  color=649c9c9c   - Color.
 * @property {int}  color.red=-100   - Red.
 * @property {int}  color.green=-100   - Green.
 * @property {int}  color.blue=-100   - Blue.
 * @property {int}  color.alpha=100   - Alpha.
 * @property {generic_enum}  [color.preferred_ui="Separate"]   - Preferred Editor.
 * @property {bool}  multiplicative=false   - Multiplicative.
 * @property {double}  colour_gain=1   - Intensity.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'GAUSSIANBLUR-PLUGIN'
 * @name  NodeTypes#Blur-Gaussian
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {bool}  truck_factor=true   - Truck Factor.
 * @property {bool}  bidirectional=true   - Bidirectional.
 * @property {generic_enum}  [precision="Medium 8"]   - Precision.
 * @property {bool}  repeat_edge_pixels=false   - Repeat Edge Pixels.
 * @property {bool}  directional=false   - Directional.
 * @property {double}  angle=0   - Angle.
 * @property {int}  iterations=1   - Number of Iterations.
 * @property {double}  blurriness=0   - Blurriness.
 * @property {double}  vertical=0   - Vertical Blurriness.
 * @property {double}  horizontal=0   - Horizontal Blurriness.
 */


/**
 * Attributes present in the node of type: 'HIGHLIGHT'
 * @name  NodeTypes#Highlight
 * @property {bool}  truck_factor=true   - Truck Factor.
 * @property {generic_enum}  [blur_type="Radial"]   - Blur Type.
 * @property {double}  radius=2   - Radius.
 * @property {double}  directional_angle=0   - Directional Angle.
 * @property {double}  directional_falloff_rate=1   - Directional Falloff Rate.
 * @property {bool}  use_matte_color=false   - Use Matte Colour.
 * @property {bool}  invert_matte=false   - Invert Matte.
 * @property {color}  color=64646464   - Color.
 * @property {int}  color.red=100   - Red.
 * @property {int}  color.green=100   - Green.
 * @property {int}  color.blue=100   - Blue.
 * @property {int}  color.alpha=100   - Alpha.
 * @property {generic_enum}  [color.preferred_ui="Separate"]   - Preferred Editor.
 * @property {bool}  multiplicative=false   - Multiplicative.
 * @property {double}  colour_gain=1   - Intensity.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'MATTE_BLUR'
 * @name  NodeTypes#Matte-Blur
 * @property {bool}  truck_factor=true   - Truck Factor.
 * @property {generic_enum}  [blur_type="Radial"]   - Blur Type.
 * @property {double}  radius=0   - Radius.
 * @property {double}  directional_angle=0   - Directional Angle.
 * @property {double}  directional_falloff_rate=1   - Directional Falloff Rate.
 * @property {bool}  use_matte_color=false   - Use Matte Colour.
 * @property {bool}  invert_matte=false   - Invert Matte.
 * @property {color}  color=ffffffff   - Color.
 * @property {int}  color.red=255   - Red.
 * @property {int}  color.green=255   - Green.
 * @property {int}  color.blue=255   - Blue.
 * @property {int}  color.alpha=255   - Alpha.
 * @property {generic_enum}  [color.preferred_ui="Separate"]   - Preferred Editor.
 * @property {bool}  multiplicative=false   - Multiplicative.
 * @property {double}  colour_gain=1   - Intensity.
 */


/**
 * Attributes present in the node of type: 'PEG'
 * @name  NodeTypes#Peg
 * @property {bool}  enable_3d=false   - Enable 3D.
 * @property {bool}  face_camera=false   - Face Camera.
 * @property {generic_enum}  [camera_alignment="None"]   - Camera Alignment.
 * @property {position_3d}  position   - Position.
 * @property {bool}  position.separate=On   - Separate.
 * @property {double}  position.x=0   - Pos x.
 * @property {double}  position.y=0   - Pos y.
 * @property {double}  position.z=0   - Pos z.
 * @property {path_3d}  position.3dpath   - Path.
 * @property {scale_3d}  scale   - Scale.
 * @property {bool}  scale.separate=On   - Separate.
 * @property {bool}  scale.in_fields=Off   - In fields.
 * @property {doublevb}  scale.xy=1   - Scale.
 * @property {doublevb}  scale.x=1   - Scale x.
 * @property {doublevb}  scale.y=1   - Scale y.
 * @property {doublevb}  scale.z=1   - Scale z.
 * @property {rotation_3d}  rotation   - Rotation.
 * @property {bool}  rotation.separate=Off   - Separate.
 * @property {doublevb}  rotation.anglex=0   - Angle_x.
 * @property {doublevb}  rotation.angley=0   - Angle_y.
 * @property {doublevb}  rotation.anglez=0   - Angle_z.
 * @property {quaternion_path}  rotation.quaternionpath   - Quaternion.
 * @property {alias}  angle=0   - Angle.
 * @property {double}  skew=0   - Skew.
 * @property {position_3d}  pivot   - Pivot.
 * @property {bool}  pivot.separate=On   - Separate.
 * @property {double}  pivot.x=0   - Pos x.
 * @property {double}  pivot.y=0   - Pos y.
 * @property {double}  pivot.z=0   - Pos z.
 * @property {position_3d}  spline_offset   - Spline Offset.
 * @property {bool}  spline_offset.separate=On   - Separate.
 * @property {double}  spline_offset.x=0   - Pos x.
 * @property {double}  spline_offset.y=0   - Pos y.
 * @property {double}  spline_offset.z=0   - Pos z.
 * @property {bool}  ignore_parent_peg_scaling=false   - Ignore Parent Scaling.
 * @property {bool}  disable_field_rendering=false   - Disable Field Rendering.
 * @property {int}  depth=0   - Depth.
 * @property {bool}  enable_min_max_angle=false   - Enable Min/Max Angle.
 * @property {double}  min_angle=-360   - Min Angle.
 * @property {double}  max_angle=360   - Max Angle.
 * @property {bool}  nail_for_children=false   - Nail for Children.
 * @property {bool}  ik_hold_orientation=false   - Hold Orientation in IK.
 * @property {bool}  ik_hold_x=false   - Hold X in IK.
 * @property {bool}  ik_hold_y=false   - Hold Y in IK.
 * @property {bool}  ik_excluded=false   - Is Excluded from IK.
 * @property {bool}  ik_can_rotate=true   - Can Rotate during IK.
 * @property {bool}  ik_can_translate_x=false   - Can Translate in X during IK.
 * @property {bool}  ik_can_translate_y=false   - Can Translate in Y during IK.
 * @property {double}  ik_bone_x=0.2000   - X Direction of Bone.
 * @property {double}  ik_bone_y=0   - Y Direction of Bone.
 * @property {double}  ik_stiffness=1   - Stiffness of Bone.
 * @property {bool}  group_at_network_building=false   - Group at Network Building.
 * @property {bool}  add_composite_to_group=true   - Add Composite to Group.
 */


/**
 * Attributes present in the node of type: 'GLOW'
 * @name  NodeTypes#Glow
 * @property {bool}  truck_factor=true   - Truck Factor.
 * @property {generic_enum}  [blur_type="Radial"]   - Blur Type.
 * @property {double}  radius=0   - Radius.
 * @property {double}  directional_angle=0   - Directional Angle.
 * @property {double}  directional_falloff_rate=1   - Directional Falloff Rate.
 * @property {bool}  use_matte_color=false   - Use Source Colour.
 * @property {bool}  invert_matte=false   - Invert Matte.
 * @property {color}  color=ff646464   - Color.
 * @property {int}  color.red=100   - Red.
 * @property {int}  color.green=100   - Green.
 * @property {int}  color.blue=100   - Blue.
 * @property {int}  color.alpha=255   - Alpha.
 * @property {generic_enum}  [color.preferred_ui="Separate"]   - Preferred Editor.
 * @property {bool}  multiplicative=false   - Multiplicative.
 * @property {double}  colour_gain=1   - Intensity.
 */


/**
 * Attributes present in the node of type: 'BLEND_MODE_MODULE'
 * @name  NodeTypes#Blending
 * @property {generic_enum}  [blend_mode="Normal"]   - Blend Mode.
 * @property {generic_enum}  [flash_blend_mode="Normal"]   - SWF Blend Mode.
 */


/**
 * Attributes present in the node of type: 'BLUR_RADIAL'
 * @name  NodeTypes#Blur
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {bool}  truck_factor=true   - Truck Factor.
 * @property {double}  radius=0   - Radius.
 * @property {generic_enum}  [quality="High"]   - Quality.
 */


/**
 * Attributes present in the node of type: 'ImageSwitch'
 * @name  NodeTypes#Image-Switch
 * @property {int}  port_index=0   - Port Index.
 */


/**
 * Attributes present in the node of type: 'ORTHOLOCK'
 * @name  NodeTypes#OrthoLock
 * @property {generic_enum}  [rotation_axis="X and Y Axes"]   - Rotation Axis.
 * @property {double}  max_angle=0   - Max Angle.
 */


/**
 * Attributes present in the node of type: 'CHROMA_KEYING'
 * @name  NodeTypes#Chroma-Keying
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {color}  color=ffffffff   - Color.
 * @property {int}  color.red=255   - Red.
 * @property {int}  color.green=255   - Green.
 * @property {int}  color.blue=255   - Blue.
 * @property {int}  color.alpha=255   - Alpha.
 * @property {generic_enum}  [color.preferred_ui="Separate"]   - Preferred Editor.
 * @property {double}  chroma_key_minimum=0   - Black Point.
 * @property {double}  chroma_key_maximum=255   - White Point.
 * @property {double}  chroma_key_filter_intensity=1   - Blur Passes.
 * @property {double}  chroma_key_sampling=2   - Adjacent Pixels per Pass.
 * @property {bool}  applyfinalthreshold=true   - Threshold Matte.
 * @property {double}  finalthreshold=10   - Threshold.
 * @property {bool}  cutimage=true   - Cut Colour.
 */


/**
 * Attributes present in the node of type: 'Quake'
 * @name  NodeTypes#Quake
 * @property {int}  hold=1   - Hold Time.
 * @property {bool}  interpolate=false   - Interpolate.
 * @property {double}  moveamplitude=1   - Move Amplitude.
 * @property {bool}  applyx=true   - Apply on X.
 * @property {bool}  applyy=true   - Apply on Y.
 * @property {bool}  applyz=true   - Apply on Z.
 * @property {double}  rotationamplitude=0   - Rotation Amplitude.
 * @property {int}  seed=0   - Random Seed.
 */


/**
 * Attributes present in the node of type: 'GRADIENT-PLUGIN'
 * @name  NodeTypes#Gradient
 * @property {int}  depth=0   - Depth.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {generic_enum}  [type="Linear"]   - Gradient Type.
 * @property {position_2d}  0   - Position 0.
 * @property {bool}  0.separate=On   - Separate.
 * @property {double}  0.x=0   - Pos x.
 * @property {double}  0.y=12   - Pos y.
 * @property {point_2d}  0.2dpoint   - Point.
 * @property {position_2d}  1   - Position 1.
 * @property {bool}  1.separate=On   - Separate.
 * @property {double}  1.x=0   - Pos x.
 * @property {double}  1.y=-12   - Pos y.
 * @property {point_2d}  1.2dpoint   - Point.
 * @property {color}  color0=ff000000   - Colour 0.
 * @property {int}  color0.red=0   - Red.
 * @property {int}  color0.green=0   - Green.
 * @property {int}  color0.blue=0   - Blue.
 * @property {int}  color0.alpha=255   - Alpha.
 * @property {generic_enum}  [color0.preferred_ui="Separate"]   - Preferred Editor.
 * @property {color}  color1=ffffffff   - Colour 1.
 * @property {int}  color1.red=255   - Red.
 * @property {int}  color1.green=255   - Green.
 * @property {int}  color1.blue=255   - Blue.
 * @property {int}  color1.alpha=255   - Alpha.
 * @property {generic_enum}  [color1.preferred_ui="Separate"]   - Preferred Editor.
 * @property {double}  offset_z=0   - Offset Z.
 */


/**
 * Attributes present in the node of type: 'BRIGHTNESS_CONTRAST'
 * @name  NodeTypes#BrightnessContrast
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {bool}  brightcontrast_legacy_brightness=false   - Legacy Brightness.
 * @property {double}  brightcontrast_brightness_adjustment=0   - Brightness.
 * @property {double}  brightcontrast_contrast_adjustment=0   - Contrast.
 * @property {bool}  brightcontrast_legacy_contrast=false   - Legacy Contrast.
 */


/**
 * Attributes present in the node of type: 'Switch'
 * @name  NodeTypes#Constraint-Switch
 * @property {double}  active=100   - ACTIVE.
 * @property {int}  gatenum=0   - TARGET GATE.
 * @property {position_2d}  uioffsetpos   - GUI OFFSET.
 * @property {bool}  uioffsetpos.separate=On   - Separate.
 * @property {double}  uioffsetpos.x=0   - Pos x.
 * @property {double}  uioffsetpos.y=0   - Pos y.
 * @property {double}  uiscale=1   - GUI SCALE.
 */


/**
 * Attributes present in the node of type: 'Grid'
 * @name  NodeTypes#Grid
 * @property {int}  size=12   - Size.
 * @property {double}  aspect=1.3333   - Aspect.
 * @property {bool}  showtext=true   - Display Text.
 * @property {color}  gridcolor=ff000000   - Color.
 * @property {int}  gridcolor.red=0   - Red.
 * @property {int}  gridcolor.green=0   - Green.
 * @property {int}  gridcolor.blue=0   - Blue.
 * @property {int}  gridcolor.alpha=255   - Alpha.
 * @property {generic_enum}  [gridcolor.preferred_ui="Separate"]   - Preferred Editor.
 * @property {color}  bgcolor=ffffffff   - Color.
 * @property {int}  bgcolor.red=255   - Red.
 * @property {int}  bgcolor.green=255   - Green.
 * @property {int}  bgcolor.blue=255   - Blue.
 * @property {int}  bgcolor.alpha=255   - Alpha.
 * @property {generic_enum}  [bgcolor.preferred_ui="Separate"]   - Preferred Editor.
 * @property {bool}  opaque=false   - Fill.
 * @property {bool}  fitvertical=true   - Fit Vertical.
 */


/**
 * Attributes present in the node of type: 'Turbulence'
 * @name  NodeTypes#Turbulence
 * @property {generic_enum}  [fractal_type="Fractional Brownian"]   - Fractal Type.
 * @property {generic_enum}  [noise_type="Perlin"]   - Noise Type.
 * @property {locked}  frequency   - Frequency.
 * @property {bool}  frequency.separate=Off   - Separate.
 * @property {doublevb}  frequency.xyfrequency=1   - Frequency xy.
 * @property {doublevb}  frequency.xfrequency=0   - Frequency x.
 * @property {doublevb}  frequency.yfrequency=0   - Frequency y.
 * @property {locked}  amount   - Amount.
 * @property {bool}  amount.separate=Off   - Separate.
 * @property {doublevb}  amount.xyamount=0   - Amount xy.
 * @property {doublevb}  amount.xamount=0   - Amount x.
 * @property {doublevb}  amount.yamount=0   - Amount y.
 * @property {locked}  offset   - Offset.
 * @property {bool}  offset.separate=Off   - Separate.
 * @property {doublevb}  offset.xyoffset=0   - Offset xy.
 * @property {doublevb}  offset.xoffset=0   - Offset x.
 * @property {doublevb}  offset.yoffset=0   - Offset y.
 * @property {locked}  seed   - Seed.
 * @property {bool}  seed.separate=On   - Separate.
 * @property {doublevb}  seed.xyseed=0   - Seed xy.
 * @property {doublevb}  seed.xseed=10   - Seed x.
 * @property {doublevb}  seed.yseed=0   - Seed y.
 * @property {double}  evolution=0   - Evolution.
 * @property {double}  evolution_frequency=0   - Evolution Frequency.
 * @property {double}  gain=0.6500   - Gain.
 * @property {double}  lacunarity=2   - Sub Scaling.
 * @property {double}  octaves=1   - Complexity.
 * @property {bool}  pinning=false   - Pinning.
 * @property {generic_enum}  [deformationquality="Medium"]   - Deformation Quality.
 */


/**
 * Attributes present in the node of type: 'PointConstraintMulti'
 * @name  NodeTypes#Multi-Points-Constraint
 * @property {double}  active=100   - Active.
 * @property {generic_enum}  [flattentype="Allow 3D Transform"]   - Flatten Type.
 * @property {bool}  convexhull=false   - Ignore Internal Points.
 * @property {bool}  allowpersp=false   - Allow Perspective Transform.
 */


/**
 * Attributes present in the node of type: 'VISIBILITY'
 * @name  NodeTypes#Visibility
 * @property {bool}  oglrender=true   - Display in OpenGL View.
 * @property {bool}  softrender=true   - Soft Render.
 */


/**
 * Attributes present in the node of type: 'REFRACT'
 * @name  NodeTypes#Refract
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {double}  intensity=10   - Intensity.
 * @property {double}  height=0   - Height.
 */


/**
 * Attributes present in the node of type: 'MULTIPORT_OUT'
 * @name  NodeTypes#Multi-Port-Out
 */


/**
 * Attributes present in the node of type: 'REMOVE_TRANSPARENCY'
 * @name  NodeTypes#Remove-Transparency
 * @property {double}  threshold=50   - Threshold.
 * @property {bool}  remove_color_transparency=true   - Remove Colour Transparency.
 * @property {bool}  remove_alpha_transparency=true   - Remove Alpha Transparency.
 */


/**
 * Attributes present in the node of type: 'Bloom'
 * @name  NodeTypes#Bloom
 * @property {double}  luminancethresholdthresh=75   - Threshold.
 * @property {bool}  luminancethresholdsoften=true   - Soften Colours.
 * @property {double}  luminancethresholdgamma=1.5000   - Gamma Correction.
 * @property {bool}  luminancethresholdgrey=false   - Output Greyscale Matte.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {bool}  truck_factor=true   - Truck Factor.
 * @property {double}  radius=4   - Radius.
 * @property {generic_enum}  [quality="High"]   - Quality.
 * @property {bool}  composite_src_image=true   - Composite with Source Image.
 * @property {generic_enum}  [blend_mode="Screen"]   - Blend Mode.
 */


/**
 * Attributes present in the node of type: 'MULTIPORT_IN'
 * @name  NodeTypes#Multi-Port-In
 */


/**
 * Attributes present in the node of type: 'MedianFilter'
 * @name  NodeTypes#Median
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {double}  radius=0   - Radius.
 * @property {int}  bitdepth=256   - Colour Depth.
 */


/**
 * Attributes present in the node of type: 'ToneShader'
 * @name  NodeTypes#Tone-Shader
 * @property {generic_enum}  [lighttype="Directional"]   - Light Type.
 * @property {double}  floodangle=90   - Cone Angle.
 * @property {double}  floodsharpness=0   - Diffusion.
 * @property {double}  floodradius=2000   - Falloff.
 * @property {double}  pointelevation=200   - Light Source Elevation.
 * @property {double}  anglethreshold=90   - Surface Reflectivity.
 * @property {generic_enum}  [shadetype="Smooth"]   - Shading Type.
 * @property {double}  bias=0.1000   - Bias.
 * @property {double}  exponent=2   - Abruptness.
 * @property {color}  lightcolor=ff646464   - Light Colour.
 * @property {int}  lightcolor.red=100   - Red.
 * @property {int}  lightcolor.green=100   - Green.
 * @property {int}  lightcolor.blue=100   - Blue.
 * @property {int}  lightcolor.alpha=255   - Alpha.
 * @property {generic_enum}  [lightcolor.preferred_ui="Separate"]   - Preferred Editor.
 * @property {bool}  flatten=true   - Flatten Fx.
 * @property {bool}  useimagecolor=false   - Use image Colour.
 * @property {double}  imagecolorweight=50   - Image Colour Intensity.
 * @property {bool}  adjustlevel=false   - Adjust Light Intensity.
 * @property {double}  adjustedlevel=75   - Intensity.
 * @property {double}  scale=1   - Multiplier.
 * @property {bool}  usesurface=false   - Use Surface Lighting.
 * @property {double}  speculartransparency=0   - Specular Transparency.
 * @property {double}  specularity=100   - Specular Strength.
 * @property {double}  distancefalloff=0   - Distance Falloff.
 */


/**
 * Attributes present in the node of type: 'DeformationCompositeModule'
 * @name  NodeTypes#Deformation-Composite
 * @property {bool}  outputmatrixonly=false   - Output Kinematic Only.
 * @property {bool}  outputselectedonly=false   - Output Selected Port Only.
 * @property {generic_enum}  [outputkinematicchainselector="Rightmost"]   - Output Kinematic Chain.
 * @property {int}  outputkinematicchain=1   - Output Kinematic Chain Selection.
 */


/**
 * Attributes present in the node of type: 'AnimatedMatteGenerator'
 * @name  NodeTypes#Animated-Matte-Generator
 * @property {double}  snapradius=15   - Drag-to-Snap Distance.
 * @property {bool}  snapoutlinesonly=false   - Snap to Outlines Only.
 * @property {generic_enum}  [outputtype="Feathered"]   - Type.
 * @property {double}  outputinterpolation=0   - Interpolation Factor.
 * @property {color}  insidecolor=ffffffff   - Inside Colour.
 * @property {int}  insidecolor.red=255   - Red.
 * @property {int}  insidecolor.green=255   - Green.
 * @property {int}  insidecolor.blue=255   - Blue.
 * @property {int}  insidecolor.alpha=255   - Alpha.
 * @property {generic_enum}  [insidecolor.preferred_ui="Separate"]   - Preferred Editor.
 * @property {color}  outsidecolor=ffffffff   - Outside Colour.
 * @property {int}  outsidecolor.red=255   - Red.
 * @property {int}  outsidecolor.green=255   - Green.
 * @property {int}  outsidecolor.blue=255   - Blue.
 * @property {int}  outsidecolor.alpha=255   - Alpha.
 * @property {generic_enum}  [outsidecolor.preferred_ui="Separate"]   - Preferred Editor.
 * @property {generic_enum}  [interpolationmode="Distance"]   - Interpolation Mode.
 * @property {generic_enum}  [colorinterpolation="Constant"]   - Colour Interpolation.
 * @property {generic_enum}  [alphamapping="Linear"]   - Alpha Mapping.
 * @property {int}  colorlutdomain=100   - Colour LUT Domain.
 * @property {int}  alphalutdomain=100   - Alpha LUT Domain.
 * @property {double}  colorgamma=1   - Colour Gamma.
 * @property {double}  alphagamma=1   - Alpha Gamma.
 * @property {double}  colorlut=0   - Colour LUT.
 * @property {double}  alphalut=0   - Alpha LUT.
 * @property {bool}  snapunderlay=false   - Underlay Art.
 * @property {bool}  snapcolor=true   - Colour Art.
 * @property {bool}  snapline=true   - Line Art.
 * @property {bool}  snapoverlay=false   - Overlay Art.
 * @property {bool}  usehints=true   - Enable Hints.
 * @property {double}  snapradiusdraghint=20   - Drag-to-Snap Distance.
 * @property {double}  snapradiusgeneratehint=95   - Generated Matte Snap Distance.
 * @property {double}  mindistancepregeneratehints=75   - Minimum Distance Between Generated Hints.
 * @property {bool}  snaphintunderlay=false   - Underlay Art.
 * @property {bool}  snaphintcolor=true   - Colour Art.
 * @property {bool}  snaphintline=false   - Line Art.
 * @property {bool}  snaphintoverlay=false   - Overlay Art.
 * @property {bool}  overlayisnote=true   - Use Overlay Layer as Note.
 * @property {string}  contourcentres   - Contour Centres.
 */


/**
 * Attributes present in the node of type: 'COLOR2BW'
 * @name  NodeTypes#Greyscale
 * @property {double}  percent=100   - Percent.
 * @property {bool}  matte_output=false   - Matte Output.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'CONTRAST'
 * @name  NodeTypes#Contrast
 * @property {double}  mid_point=0.5000   - Mid Point.
 * @property {double}  dark_pixel_adjustement=1   - Dark Pixel Adjustment.
 * @property {double}  bright_pixel_adjustement=1   - Bright Pixel Adjustment.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'COLOR_CURVES'
 * @name  NodeTypes#Colour-Curves
 * @property {color-correction-control-point-attribute}  control_point_red_0   - Control point.
 * @property {position_2d}  control_point_red_0.control   - Control Point.
 * @property {bool}  control_point_red_0.control.separate=Off   - Separate.
 * @property {double}  control_point_red_0.control.x=0   - Pos x.
 * @property {double}  control_point_red_0.control.y=0   - Pos y.
 * @property {point_2d}  control_point_red_0.control.2dpoint   - Point.
 * @property {position_2d}  control_point_red_0.left_handle   - Left Handle.
 * @property {bool}  control_point_red_0.left_handle.separate=Off   - Separate.
 * @property {double}  control_point_red_0.left_handle.x=-0.1000   - Pos x.
 * @property {double}  control_point_red_0.left_handle.y=-0.1000   - Pos y.
 * @property {point_2d}  control_point_red_0.left_handle.2dpoint   - Point.
 * @property {position_2d}  control_point_red_0.right_handle   - Right Handle.
 * @property {bool}  control_point_red_0.right_handle.separate=Off   - Separate.
 * @property {double}  control_point_red_0.right_handle.x=0.1000   - Pos x.
 * @property {double}  control_point_red_0.right_handle.y=0.1000   - Pos y.
 * @property {point_2d}  control_point_red_0.right_handle.2dpoint   - Point.
 * @property {color-correction-control-point-attribute}  control_point_red_1   - Control point.
 * @property {position_2d}  control_point_red_1.control   - Control Point.
 * @property {bool}  control_point_red_1.control.separate=Off   - Separate.
 * @property {double}  control_point_red_1.control.x=1   - Pos x.
 * @property {double}  control_point_red_1.control.y=1   - Pos y.
 * @property {point_2d}  control_point_red_1.control.2dpoint   - Point.
 * @property {position_2d}  control_point_red_1.left_handle   - Left Handle.
 * @property {bool}  control_point_red_1.left_handle.separate=Off   - Separate.
 * @property {double}  control_point_red_1.left_handle.x=-0.1000   - Pos x.
 * @property {double}  control_point_red_1.left_handle.y=-0.1000   - Pos y.
 * @property {point_2d}  control_point_red_1.left_handle.2dpoint   - Point.
 * @property {position_2d}  control_point_red_1.right_handle   - Right Handle.
 * @property {bool}  control_point_red_1.right_handle.separate=Off   - Separate.
 * @property {double}  control_point_red_1.right_handle.x=0.1000   - Pos x.
 * @property {double}  control_point_red_1.right_handle.y=0.1000   - Pos y.
 * @property {point_2d}  control_point_red_1.right_handle.2dpoint   - Point.
 * @property {color-correction-control-point-attribute}  control_point_green_0   - Control point.
 * @property {position_2d}  control_point_green_0.control   - Control Point.
 * @property {bool}  control_point_green_0.control.separate=Off   - Separate.
 * @property {double}  control_point_green_0.control.x=0   - Pos x.
 * @property {double}  control_point_green_0.control.y=0   - Pos y.
 * @property {point_2d}  control_point_green_0.control.2dpoint   - Point.
 * @property {position_2d}  control_point_green_0.left_handle   - Left Handle.
 * @property {bool}  control_point_green_0.left_handle.separate=Off   - Separate.
 * @property {double}  control_point_green_0.left_handle.x=-0.1000   - Pos x.
 * @property {double}  control_point_green_0.left_handle.y=-0.1000   - Pos y.
 * @property {point_2d}  control_point_green_0.left_handle.2dpoint   - Point.
 * @property {position_2d}  control_point_green_0.right_handle   - Right Handle.
 * @property {bool}  control_point_green_0.right_handle.separate=Off   - Separate.
 * @property {double}  control_point_green_0.right_handle.x=0.1000   - Pos x.
 * @property {double}  control_point_green_0.right_handle.y=0.1000   - Pos y.
 * @property {point_2d}  control_point_green_0.right_handle.2dpoint   - Point.
 * @property {color-correction-control-point-attribute}  control_point_green_1   - Control point.
 * @property {position_2d}  control_point_green_1.control   - Control Point.
 * @property {bool}  control_point_green_1.control.separate=Off   - Separate.
 * @property {double}  control_point_green_1.control.x=1   - Pos x.
 * @property {double}  control_point_green_1.control.y=1   - Pos y.
 * @property {point_2d}  control_point_green_1.control.2dpoint   - Point.
 * @property {position_2d}  control_point_green_1.left_handle   - Left Handle.
 * @property {bool}  control_point_green_1.left_handle.separate=Off   - Separate.
 * @property {double}  control_point_green_1.left_handle.x=-0.1000   - Pos x.
 * @property {double}  control_point_green_1.left_handle.y=-0.1000   - Pos y.
 * @property {point_2d}  control_point_green_1.left_handle.2dpoint   - Point.
 * @property {position_2d}  control_point_green_1.right_handle   - Right Handle.
 * @property {bool}  control_point_green_1.right_handle.separate=Off   - Separate.
 * @property {double}  control_point_green_1.right_handle.x=0.1000   - Pos x.
 * @property {double}  control_point_green_1.right_handle.y=0.1000   - Pos y.
 * @property {point_2d}  control_point_green_1.right_handle.2dpoint   - Point.
 * @property {color-correction-control-point-attribute}  control_point_blue_0   - Control point.
 * @property {position_2d}  control_point_blue_0.control   - Control Point.
 * @property {bool}  control_point_blue_0.control.separate=Off   - Separate.
 * @property {double}  control_point_blue_0.control.x=0   - Pos x.
 * @property {double}  control_point_blue_0.control.y=0   - Pos y.
 * @property {point_2d}  control_point_blue_0.control.2dpoint   - Point.
 * @property {position_2d}  control_point_blue_0.left_handle   - Left Handle.
 * @property {bool}  control_point_blue_0.left_handle.separate=Off   - Separate.
 * @property {double}  control_point_blue_0.left_handle.x=-0.1000   - Pos x.
 * @property {double}  control_point_blue_0.left_handle.y=-0.1000   - Pos y.
 * @property {point_2d}  control_point_blue_0.left_handle.2dpoint   - Point.
 * @property {position_2d}  control_point_blue_0.right_handle   - Right Handle.
 * @property {bool}  control_point_blue_0.right_handle.separate=Off   - Separate.
 * @property {double}  control_point_blue_0.right_handle.x=0.1000   - Pos x.
 * @property {double}  control_point_blue_0.right_handle.y=0.1000   - Pos y.
 * @property {point_2d}  control_point_blue_0.right_handle.2dpoint   - Point.
 * @property {color-correction-control-point-attribute}  control_point_blue_1   - Control point.
 * @property {position_2d}  control_point_blue_1.control   - Control Point.
 * @property {bool}  control_point_blue_1.control.separate=Off   - Separate.
 * @property {double}  control_point_blue_1.control.x=1   - Pos x.
 * @property {double}  control_point_blue_1.control.y=1   - Pos y.
 * @property {point_2d}  control_point_blue_1.control.2dpoint   - Point.
 * @property {position_2d}  control_point_blue_1.left_handle   - Left Handle.
 * @property {bool}  control_point_blue_1.left_handle.separate=Off   - Separate.
 * @property {double}  control_point_blue_1.left_handle.x=-0.1000   - Pos x.
 * @property {double}  control_point_blue_1.left_handle.y=-0.1000   - Pos y.
 * @property {point_2d}  control_point_blue_1.left_handle.2dpoint   - Point.
 * @property {position_2d}  control_point_blue_1.right_handle   - Right Handle.
 * @property {bool}  control_point_blue_1.right_handle.separate=Off   - Separate.
 * @property {double}  control_point_blue_1.right_handle.x=0.1000   - Pos x.
 * @property {double}  control_point_blue_1.right_handle.y=0.1000   - Pos y.
 * @property {point_2d}  control_point_blue_1.right_handle.2dpoint   - Point.
 * @property {color-correction-control-point-attribute}  control_point_rgb_0   - Control point.
 * @property {position_2d}  control_point_rgb_0.control   - Control Point.
 * @property {bool}  control_point_rgb_0.control.separate=Off   - Separate.
 * @property {double}  control_point_rgb_0.control.x=0   - Pos x.
 * @property {double}  control_point_rgb_0.control.y=0   - Pos y.
 * @property {point_2d}  control_point_rgb_0.control.2dpoint   - Point.
 * @property {position_2d}  control_point_rgb_0.left_handle   - Left Handle.
 * @property {bool}  control_point_rgb_0.left_handle.separate=Off   - Separate.
 * @property {double}  control_point_rgb_0.left_handle.x=-0.1000   - Pos x.
 * @property {double}  control_point_rgb_0.left_handle.y=-0.1000   - Pos y.
 * @property {point_2d}  control_point_rgb_0.left_handle.2dpoint   - Point.
 * @property {position_2d}  control_point_rgb_0.right_handle   - Right Handle.
 * @property {bool}  control_point_rgb_0.right_handle.separate=Off   - Separate.
 * @property {double}  control_point_rgb_0.right_handle.x=0.1000   - Pos x.
 * @property {double}  control_point_rgb_0.right_handle.y=0.1000   - Pos y.
 * @property {point_2d}  control_point_rgb_0.right_handle.2dpoint   - Point.
 * @property {color-correction-control-point-attribute}  control_point_rgb_1   - Control point.
 * @property {position_2d}  control_point_rgb_1.control   - Control Point.
 * @property {bool}  control_point_rgb_1.control.separate=Off   - Separate.
 * @property {double}  control_point_rgb_1.control.x=1   - Pos x.
 * @property {double}  control_point_rgb_1.control.y=1   - Pos y.
 * @property {point_2d}  control_point_rgb_1.control.2dpoint   - Point.
 * @property {position_2d}  control_point_rgb_1.left_handle   - Left Handle.
 * @property {bool}  control_point_rgb_1.left_handle.separate=Off   - Separate.
 * @property {double}  control_point_rgb_1.left_handle.x=-0.1000   - Pos x.
 * @property {double}  control_point_rgb_1.left_handle.y=-0.1000   - Pos y.
 * @property {point_2d}  control_point_rgb_1.left_handle.2dpoint   - Point.
 * @property {position_2d}  control_point_rgb_1.right_handle   - Right Handle.
 * @property {bool}  control_point_rgb_1.right_handle.separate=Off   - Separate.
 * @property {double}  control_point_rgb_1.right_handle.x=0.1000   - Pos x.
 * @property {double}  control_point_rgb_1.right_handle.y=0.1000   - Pos y.
 * @property {point_2d}  control_point_rgb_1.right_handle.2dpoint   - Point.
 * @property {color-correction-control-point-attribute}  control_point_alpha_0   - Control point.
 * @property {position_2d}  control_point_alpha_0.control   - Control Point.
 * @property {bool}  control_point_alpha_0.control.separate=Off   - Separate.
 * @property {double}  control_point_alpha_0.control.x=0   - Pos x.
 * @property {double}  control_point_alpha_0.control.y=0   - Pos y.
 * @property {point_2d}  control_point_alpha_0.control.2dpoint   - Point.
 * @property {position_2d}  control_point_alpha_0.left_handle   - Left Handle.
 * @property {bool}  control_point_alpha_0.left_handle.separate=Off   - Separate.
 * @property {double}  control_point_alpha_0.left_handle.x=-0.1000   - Pos x.
 * @property {double}  control_point_alpha_0.left_handle.y=-0.1000   - Pos y.
 * @property {point_2d}  control_point_alpha_0.left_handle.2dpoint   - Point.
 * @property {position_2d}  control_point_alpha_0.right_handle   - Right Handle.
 * @property {bool}  control_point_alpha_0.right_handle.separate=Off   - Separate.
 * @property {double}  control_point_alpha_0.right_handle.x=0.1000   - Pos x.
 * @property {double}  control_point_alpha_0.right_handle.y=0.1000   - Pos y.
 * @property {point_2d}  control_point_alpha_0.right_handle.2dpoint   - Point.
 * @property {color-correction-control-point-attribute}  control_point_alpha_1   - Control point.
 * @property {position_2d}  control_point_alpha_1.control   - Control Point.
 * @property {bool}  control_point_alpha_1.control.separate=Off   - Separate.
 * @property {double}  control_point_alpha_1.control.x=1   - Pos x.
 * @property {double}  control_point_alpha_1.control.y=1   - Pos y.
 * @property {point_2d}  control_point_alpha_1.control.2dpoint   - Point.
 * @property {position_2d}  control_point_alpha_1.left_handle   - Left Handle.
 * @property {bool}  control_point_alpha_1.left_handle.separate=Off   - Separate.
 * @property {double}  control_point_alpha_1.left_handle.x=-0.1000   - Pos x.
 * @property {double}  control_point_alpha_1.left_handle.y=-0.1000   - Pos y.
 * @property {point_2d}  control_point_alpha_1.left_handle.2dpoint   - Point.
 * @property {position_2d}  control_point_alpha_1.right_handle   - Right Handle.
 * @property {bool}  control_point_alpha_1.right_handle.separate=Off   - Separate.
 * @property {double}  control_point_alpha_1.right_handle.x=0.1000   - Pos x.
 * @property {double}  control_point_alpha_1.right_handle.y=0.1000   - Pos y.
 * @property {point_2d}  control_point_alpha_1.right_handle.2dpoint   - Point.
 */


/**
 * Attributes present in the node of type: 'HUE_SATURATION'
 * @name  NodeTypes#Hue-Saturation
 * @property {hue_range}  masterrangecolor   - Master.
 * @property {double}  masterrangecolor.hue_shift=0   - Hue.
 * @property {double}  masterrangecolor.saturation=0   - Saturation.
 * @property {double}  masterrangecolor.lightness=0   - Lightness.
 * @property {hue_range}  redrangecolor   - Reds.
 * @property {double}  redrangecolor.hue_shift=0   - Hue.
 * @property {double}  redrangecolor.saturation=0   - Saturation.
 * @property {double}  redrangecolor.lightness=0   - Lightness.
 * @property {double}  redrangecolor.low_range=345   - LowRange.
 * @property {double}  redrangecolor.high_range=15   - HighRange.
 * @property {double}  redrangecolor.low_falloff=30   - LowFalloff.
 * @property {double}  redrangecolor.high_falloff=30   - HighFalloff.
 * @property {hue_range}  greenrangecolor   - Greens.
 * @property {double}  greenrangecolor.hue_shift=0   - Hue.
 * @property {double}  greenrangecolor.saturation=0   - Saturation.
 * @property {double}  greenrangecolor.lightness=0   - Lightness.
 * @property {double}  greenrangecolor.low_range=105   - LowRange.
 * @property {double}  greenrangecolor.high_range=135   - HighRange.
 * @property {double}  greenrangecolor.low_falloff=30   - LowFalloff.
 * @property {double}  greenrangecolor.high_falloff=30   - HighFalloff.
 * @property {hue_range}  bluerangecolor   - Blues.
 * @property {double}  bluerangecolor.hue_shift=0   - Hue.
 * @property {double}  bluerangecolor.saturation=0   - Saturation.
 * @property {double}  bluerangecolor.lightness=0   - Lightness.
 * @property {double}  bluerangecolor.low_range=225   - LowRange.
 * @property {double}  bluerangecolor.high_range=255   - HighRange.
 * @property {double}  bluerangecolor.low_falloff=30   - LowFalloff.
 * @property {double}  bluerangecolor.high_falloff=30   - HighFalloff.
 * @property {hue_range}  cyanrangecolor   - Cyans.
 * @property {double}  cyanrangecolor.hue_shift=0   - Hue.
 * @property {double}  cyanrangecolor.saturation=0   - Saturation.
 * @property {double}  cyanrangecolor.lightness=0   - Lightness.
 * @property {double}  cyanrangecolor.low_range=165   - LowRange.
 * @property {double}  cyanrangecolor.high_range=195   - HighRange.
 * @property {double}  cyanrangecolor.low_falloff=30   - LowFalloff.
 * @property {double}  cyanrangecolor.high_falloff=30   - HighFalloff.
 * @property {hue_range}  magentarangecolor   - Magentas.
 * @property {double}  magentarangecolor.hue_shift=0   - Hue.
 * @property {double}  magentarangecolor.saturation=0   - Saturation.
 * @property {double}  magentarangecolor.lightness=0   - Lightness.
 * @property {double}  magentarangecolor.low_range=285   - LowRange.
 * @property {double}  magentarangecolor.high_range=315   - HighRange.
 * @property {double}  magentarangecolor.low_falloff=30   - LowFalloff.
 * @property {double}  magentarangecolor.high_falloff=30   - HighFalloff.
 * @property {hue_range}  yellowrangecolor   - Yellows.
 * @property {double}  yellowrangecolor.hue_shift=0   - Hue.
 * @property {double}  yellowrangecolor.saturation=0   - Saturation.
 * @property {double}  yellowrangecolor.lightness=0   - Lightness.
 * @property {double}  yellowrangecolor.low_range=45   - LowRange.
 * @property {double}  yellowrangecolor.high_range=75   - HighRange.
 * @property {double}  yellowrangecolor.low_falloff=30   - LowFalloff.
 * @property {double}  yellowrangecolor.high_falloff=30   - HighFalloff.
 * @property {bool}  colorizeenable=false   - Colorize.
 * @property {hsl}  colorizehsl   - Colorize HSL.
 * @property {double}  colorizehsl.hue=0   - Hue.
 * @property {double}  colorizehsl.saturation=25   - Saturation.
 * @property {double}  colorizehsl.lightness=0   - Lightness.
 * @property {push_button}  resetred   - Reset Range.
 * @property {push_button}  resetgreen   - Reset Range.
 * @property {push_button}  resetblue   - Reset Range.
 * @property {push_button}  resetcyan   - Reset Range.
 * @property {push_button}  resetmagenta   - Reset Range.
 * @property {push_button}  resetyellow   - Reset Range.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'NEGATE'
 * @name  NodeTypes#Negate
 * @property {bool}  color=true   - Negate Colour.
 * @property {bool}  color_alpha=false   - Negate Alpha.
 * @property {bool}  color_clamp_to_alpha=true   - Negate Colour Clamp to Alpha.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'TurbulentNoise'
 * @name  NodeTypes#TurbulentNoise
 * @property {int}  depth=0   - Depth.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {generic_enum}  [fractal_type="Fractional Brownian"]   - Fractal Type.
 * @property {generic_enum}  [noise_type="Perlin"]   - Noise Type.
 * @property {locked}  frequency   - Frequency.
 * @property {bool}  frequency.separate=Off   - Separate.
 * @property {doublevb}  frequency.xyfrequency=0   - Frequency xy.
 * @property {doublevb}  frequency.xfrequency=0   - Frequency x.
 * @property {doublevb}  frequency.yfrequency=0   - Frequency y.
 * @property {locked}  offset   - Offset.
 * @property {bool}  offset.separate=Off   - Separate.
 * @property {doublevb}  offset.xyoffset=0   - Offset xy.
 * @property {doublevb}  offset.xoffset=0   - Offset x.
 * @property {doublevb}  offset.yoffset=0   - Offset y.
 * @property {double}  evolution=0   - Evolution.
 * @property {double}  evolution_frequency=0   - Evolution Frequency.
 * @property {double}  gain=0.6500   - Gain.
 * @property {double}  lacunarity=2   - Sub Scaling.
 * @property {double}  octaves=1   - Complexity.
 */


/**
 * Attributes present in the node of type: 'BezierMesh'
 * @name  NodeTypes#Mesh-Warp
 * @property {array_position_2d}  mesh   - Mesh.
 * @property {int}  mesh.size=105   - Size.
 * @property {position_2d}  mesh.meshpoint0x0   - MeshPoint0x0.
 * @property {bool}  mesh.meshpoint0x0.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x0.x=-12   - Pos x.
 * @property {double}  mesh.meshpoint0x0.y=-12   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x0.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x1   - MeshPoint0x1.
 * @property {bool}  mesh.meshpoint0x1.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x1.x=-10   - Pos x.
 * @property {double}  mesh.meshpoint0x1.y=-12   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x1.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x2   - MeshPoint0x2.
 * @property {bool}  mesh.meshpoint0x2.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x2.x=-8   - Pos x.
 * @property {double}  mesh.meshpoint0x2.y=-12   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x2.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x3   - MeshPoint0x3.
 * @property {bool}  mesh.meshpoint0x3.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x3.x=-6   - Pos x.
 * @property {double}  mesh.meshpoint0x3.y=-12   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x3.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x4   - MeshPoint0x4.
 * @property {bool}  mesh.meshpoint0x4.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x4.x=-4   - Pos x.
 * @property {double}  mesh.meshpoint0x4.y=-12   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x4.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x5   - MeshPoint0x5.
 * @property {bool}  mesh.meshpoint0x5.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x5.x=-2   - Pos x.
 * @property {double}  mesh.meshpoint0x5.y=-12   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x5.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x6   - MeshPoint0x6.
 * @property {bool}  mesh.meshpoint0x6.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x6.x=0   - Pos x.
 * @property {double}  mesh.meshpoint0x6.y=-12   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x6.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x7   - MeshPoint0x7.
 * @property {bool}  mesh.meshpoint0x7.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x7.x=2   - Pos x.
 * @property {double}  mesh.meshpoint0x7.y=-12   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x7.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x8   - MeshPoint0x8.
 * @property {bool}  mesh.meshpoint0x8.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x8.x=4   - Pos x.
 * @property {double}  mesh.meshpoint0x8.y=-12   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x8.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x9   - MeshPoint0x9.
 * @property {bool}  mesh.meshpoint0x9.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x9.x=6   - Pos x.
 * @property {double}  mesh.meshpoint0x9.y=-12   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x9.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x10   - MeshPoint0x10.
 * @property {bool}  mesh.meshpoint0x10.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x10.x=8   - Pos x.
 * @property {double}  mesh.meshpoint0x10.y=-12   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x10.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x11   - MeshPoint0x11.
 * @property {bool}  mesh.meshpoint0x11.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x11.x=10   - Pos x.
 * @property {double}  mesh.meshpoint0x11.y=-12   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x11.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x12   - MeshPoint0x12.
 * @property {bool}  mesh.meshpoint0x12.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x12.x=12   - Pos x.
 * @property {double}  mesh.meshpoint0x12.y=-12   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x12.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x13   - MeshPoint0x13.
 * @property {bool}  mesh.meshpoint0x13.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x13.x=-12   - Pos x.
 * @property {double}  mesh.meshpoint0x13.y=-10   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x13.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x14   - MeshPoint0x14.
 * @property {bool}  mesh.meshpoint0x14.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x14.x=-6   - Pos x.
 * @property {double}  mesh.meshpoint0x14.y=-10   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x14.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x15   - MeshPoint0x15.
 * @property {bool}  mesh.meshpoint0x15.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x15.x=0   - Pos x.
 * @property {double}  mesh.meshpoint0x15.y=-10   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x15.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x16   - MeshPoint0x16.
 * @property {bool}  mesh.meshpoint0x16.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x16.x=6   - Pos x.
 * @property {double}  mesh.meshpoint0x16.y=-10   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x16.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x17   - MeshPoint0x17.
 * @property {bool}  mesh.meshpoint0x17.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x17.x=12   - Pos x.
 * @property {double}  mesh.meshpoint0x17.y=-10   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x17.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x18   - MeshPoint0x18.
 * @property {bool}  mesh.meshpoint0x18.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x18.x=-12   - Pos x.
 * @property {double}  mesh.meshpoint0x18.y=-8   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x18.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x19   - MeshPoint0x19.
 * @property {bool}  mesh.meshpoint0x19.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x19.x=-6   - Pos x.
 * @property {double}  mesh.meshpoint0x19.y=-8   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x19.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x20   - MeshPoint0x20.
 * @property {bool}  mesh.meshpoint0x20.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x20.x=0   - Pos x.
 * @property {double}  mesh.meshpoint0x20.y=-8   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x20.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x21   - MeshPoint0x21.
 * @property {bool}  mesh.meshpoint0x21.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x21.x=6   - Pos x.
 * @property {double}  mesh.meshpoint0x21.y=-8   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x21.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x22   - MeshPoint0x22.
 * @property {bool}  mesh.meshpoint0x22.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x22.x=12   - Pos x.
 * @property {double}  mesh.meshpoint0x22.y=-8   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x22.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x23   - MeshPoint0x23.
 * @property {bool}  mesh.meshpoint0x23.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x23.x=-12   - Pos x.
 * @property {double}  mesh.meshpoint0x23.y=-6   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x23.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x24   - MeshPoint0x24.
 * @property {bool}  mesh.meshpoint0x24.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x24.x=-10   - Pos x.
 * @property {double}  mesh.meshpoint0x24.y=-6   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x24.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x25   - MeshPoint0x25.
 * @property {bool}  mesh.meshpoint0x25.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x25.x=-8   - Pos x.
 * @property {double}  mesh.meshpoint0x25.y=-6   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x25.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x26   - MeshPoint0x26.
 * @property {bool}  mesh.meshpoint0x26.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x26.x=-6   - Pos x.
 * @property {double}  mesh.meshpoint0x26.y=-6   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x26.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x27   - MeshPoint0x27.
 * @property {bool}  mesh.meshpoint0x27.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x27.x=-4   - Pos x.
 * @property {double}  mesh.meshpoint0x27.y=-6   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x27.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x28   - MeshPoint0x28.
 * @property {bool}  mesh.meshpoint0x28.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x28.x=-2   - Pos x.
 * @property {double}  mesh.meshpoint0x28.y=-6   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x28.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x29   - MeshPoint0x29.
 * @property {bool}  mesh.meshpoint0x29.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x29.x=0   - Pos x.
 * @property {double}  mesh.meshpoint0x29.y=-6   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x29.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint0x30   - MeshPoint0x30.
 * @property {bool}  mesh.meshpoint0x30.separate=On   - Separate.
 * @property {double}  mesh.meshpoint0x30.x=2   - Pos x.
 * @property {double}  mesh.meshpoint0x30.y=-6   - Pos y.
 * @property {point_2d}  mesh.meshpoint0x30.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint1x0   - MeshPoint1x0.
 * @property {bool}  mesh.meshpoint1x0.separate=On   - Separate.
 * @property {double}  mesh.meshpoint1x0.x=4   - Pos x.
 * @property {double}  mesh.meshpoint1x0.y=-6   - Pos y.
 * @property {point_2d}  mesh.meshpoint1x0.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint1x1   - MeshPoint1x1.
 * @property {bool}  mesh.meshpoint1x1.separate=On   - Separate.
 * @property {double}  mesh.meshpoint1x1.x=6   - Pos x.
 * @property {double}  mesh.meshpoint1x1.y=-6   - Pos y.
 * @property {point_2d}  mesh.meshpoint1x1.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint1x2   - MeshPoint1x2.
 * @property {bool}  mesh.meshpoint1x2.separate=On   - Separate.
 * @property {double}  mesh.meshpoint1x2.x=8   - Pos x.
 * @property {double}  mesh.meshpoint1x2.y=-6   - Pos y.
 * @property {point_2d}  mesh.meshpoint1x2.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint1x3   - MeshPoint1x3.
 * @property {bool}  mesh.meshpoint1x3.separate=On   - Separate.
 * @property {double}  mesh.meshpoint1x3.x=10   - Pos x.
 * @property {double}  mesh.meshpoint1x3.y=-6   - Pos y.
 * @property {point_2d}  mesh.meshpoint1x3.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint1x4   - MeshPoint1x4.
 * @property {bool}  mesh.meshpoint1x4.separate=On   - Separate.
 * @property {double}  mesh.meshpoint1x4.x=12   - Pos x.
 * @property {double}  mesh.meshpoint1x4.y=-6   - Pos y.
 * @property {point_2d}  mesh.meshpoint1x4.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint1x5   - MeshPoint1x5.
 * @property {bool}  mesh.meshpoint1x5.separate=On   - Separate.
 * @property {double}  mesh.meshpoint1x5.x=-12   - Pos x.
 * @property {double}  mesh.meshpoint1x5.y=-4   - Pos y.
 * @property {point_2d}  mesh.meshpoint1x5.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint1x6   - MeshPoint1x6.
 * @property {bool}  mesh.meshpoint1x6.separate=On   - Separate.
 * @property {double}  mesh.meshpoint1x6.x=-6   - Pos x.
 * @property {double}  mesh.meshpoint1x6.y=-4   - Pos y.
 * @property {point_2d}  mesh.meshpoint1x6.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint1x7   - MeshPoint1x7.
 * @property {bool}  mesh.meshpoint1x7.separate=On   - Separate.
 * @property {double}  mesh.meshpoint1x7.x=0   - Pos x.
 * @property {double}  mesh.meshpoint1x7.y=-4   - Pos y.
 * @property {point_2d}  mesh.meshpoint1x7.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint1x8   - MeshPoint1x8.
 * @property {bool}  mesh.meshpoint1x8.separate=On   - Separate.
 * @property {double}  mesh.meshpoint1x8.x=6   - Pos x.
 * @property {double}  mesh.meshpoint1x8.y=-4   - Pos y.
 * @property {point_2d}  mesh.meshpoint1x8.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint1x9   - MeshPoint1x9.
 * @property {bool}  mesh.meshpoint1x9.separate=On   - Separate.
 * @property {double}  mesh.meshpoint1x9.x=12   - Pos x.
 * @property {double}  mesh.meshpoint1x9.y=-4   - Pos y.
 * @property {point_2d}  mesh.meshpoint1x9.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint1x10   - MeshPoint1x10.
 * @property {bool}  mesh.meshpoint1x10.separate=On   - Separate.
 * @property {double}  mesh.meshpoint1x10.x=-12   - Pos x.
 * @property {double}  mesh.meshpoint1x10.y=-2   - Pos y.
 * @property {point_2d}  mesh.meshpoint1x10.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint2x0   - MeshPoint2x0.
 * @property {bool}  mesh.meshpoint2x0.separate=On   - Separate.
 * @property {double}  mesh.meshpoint2x0.x=-6   - Pos x.
 * @property {double}  mesh.meshpoint2x0.y=-2   - Pos y.
 * @property {point_2d}  mesh.meshpoint2x0.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint2x1   - MeshPoint2x1.
 * @property {bool}  mesh.meshpoint2x1.separate=On   - Separate.
 * @property {double}  mesh.meshpoint2x1.x=0   - Pos x.
 * @property {double}  mesh.meshpoint2x1.y=-2   - Pos y.
 * @property {point_2d}  mesh.meshpoint2x1.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint2x2   - MeshPoint2x2.
 * @property {bool}  mesh.meshpoint2x2.separate=On   - Separate.
 * @property {double}  mesh.meshpoint2x2.x=6   - Pos x.
 * @property {double}  mesh.meshpoint2x2.y=-2   - Pos y.
 * @property {point_2d}  mesh.meshpoint2x2.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint2x3   - MeshPoint2x3.
 * @property {bool}  mesh.meshpoint2x3.separate=On   - Separate.
 * @property {double}  mesh.meshpoint2x3.x=12   - Pos x.
 * @property {double}  mesh.meshpoint2x3.y=-2   - Pos y.
 * @property {point_2d}  mesh.meshpoint2x3.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint2x4   - MeshPoint2x4.
 * @property {bool}  mesh.meshpoint2x4.separate=On   - Separate.
 * @property {double}  mesh.meshpoint2x4.x=-12   - Pos x.
 * @property {double}  mesh.meshpoint2x4.y=0   - Pos y.
 * @property {point_2d}  mesh.meshpoint2x4.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint2x5   - MeshPoint2x5.
 * @property {bool}  mesh.meshpoint2x5.separate=On   - Separate.
 * @property {double}  mesh.meshpoint2x5.x=-10   - Pos x.
 * @property {double}  mesh.meshpoint2x5.y=0   - Pos y.
 * @property {point_2d}  mesh.meshpoint2x5.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint2x6   - MeshPoint2x6.
 * @property {bool}  mesh.meshpoint2x6.separate=On   - Separate.
 * @property {double}  mesh.meshpoint2x6.x=-8   - Pos x.
 * @property {double}  mesh.meshpoint2x6.y=0   - Pos y.
 * @property {point_2d}  mesh.meshpoint2x6.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint2x7   - MeshPoint2x7.
 * @property {bool}  mesh.meshpoint2x7.separate=On   - Separate.
 * @property {double}  mesh.meshpoint2x7.x=-6   - Pos x.
 * @property {double}  mesh.meshpoint2x7.y=0   - Pos y.
 * @property {point_2d}  mesh.meshpoint2x7.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint2x8   - MeshPoint2x8.
 * @property {bool}  mesh.meshpoint2x8.separate=On   - Separate.
 * @property {double}  mesh.meshpoint2x8.x=-4   - Pos x.
 * @property {double}  mesh.meshpoint2x8.y=0   - Pos y.
 * @property {point_2d}  mesh.meshpoint2x8.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint2x9   - MeshPoint2x9.
 * @property {bool}  mesh.meshpoint2x9.separate=On   - Separate.
 * @property {double}  mesh.meshpoint2x9.x=-2   - Pos x.
 * @property {double}  mesh.meshpoint2x9.y=0   - Pos y.
 * @property {point_2d}  mesh.meshpoint2x9.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint2x10   - MeshPoint2x10.
 * @property {bool}  mesh.meshpoint2x10.separate=On   - Separate.
 * @property {double}  mesh.meshpoint2x10.x=0   - Pos x.
 * @property {double}  mesh.meshpoint2x10.y=0   - Pos y.
 * @property {point_2d}  mesh.meshpoint2x10.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x0   - MeshPoint3x0.
 * @property {bool}  mesh.meshpoint3x0.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x0.x=2   - Pos x.
 * @property {double}  mesh.meshpoint3x0.y=0   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x0.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x1   - MeshPoint3x1.
 * @property {bool}  mesh.meshpoint3x1.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x1.x=4   - Pos x.
 * @property {double}  mesh.meshpoint3x1.y=0   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x1.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x2   - MeshPoint3x2.
 * @property {bool}  mesh.meshpoint3x2.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x2.x=6   - Pos x.
 * @property {double}  mesh.meshpoint3x2.y=0   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x2.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x3   - MeshPoint3x3.
 * @property {bool}  mesh.meshpoint3x3.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x3.x=8   - Pos x.
 * @property {double}  mesh.meshpoint3x3.y=0   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x3.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x4   - MeshPoint3x4.
 * @property {bool}  mesh.meshpoint3x4.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x4.x=10   - Pos x.
 * @property {double}  mesh.meshpoint3x4.y=0   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x4.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x5   - MeshPoint3x5.
 * @property {bool}  mesh.meshpoint3x5.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x5.x=12   - Pos x.
 * @property {double}  mesh.meshpoint3x5.y=0   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x5.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x6   - MeshPoint3x6.
 * @property {bool}  mesh.meshpoint3x6.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x6.x=-12   - Pos x.
 * @property {double}  mesh.meshpoint3x6.y=2   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x6.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x7   - MeshPoint3x7.
 * @property {bool}  mesh.meshpoint3x7.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x7.x=-6   - Pos x.
 * @property {double}  mesh.meshpoint3x7.y=2   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x7.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x8   - MeshPoint3x8.
 * @property {bool}  mesh.meshpoint3x8.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x8.x=0   - Pos x.
 * @property {double}  mesh.meshpoint3x8.y=2   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x8.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x9   - MeshPoint3x9.
 * @property {bool}  mesh.meshpoint3x9.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x9.x=6   - Pos x.
 * @property {double}  mesh.meshpoint3x9.y=2   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x9.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x10   - MeshPoint3x10.
 * @property {bool}  mesh.meshpoint3x10.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x10.x=12   - Pos x.
 * @property {double}  mesh.meshpoint3x10.y=2   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x10.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x11   - MeshPoint3x11.
 * @property {bool}  mesh.meshpoint3x11.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x11.x=-12   - Pos x.
 * @property {double}  mesh.meshpoint3x11.y=4   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x11.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x12   - MeshPoint3x12.
 * @property {bool}  mesh.meshpoint3x12.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x12.x=-6   - Pos x.
 * @property {double}  mesh.meshpoint3x12.y=4   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x12.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x13   - MeshPoint3x13.
 * @property {bool}  mesh.meshpoint3x13.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x13.x=0   - Pos x.
 * @property {double}  mesh.meshpoint3x13.y=4   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x13.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x14   - MeshPoint3x14.
 * @property {bool}  mesh.meshpoint3x14.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x14.x=6   - Pos x.
 * @property {double}  mesh.meshpoint3x14.y=4   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x14.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x15   - MeshPoint3x15.
 * @property {bool}  mesh.meshpoint3x15.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x15.x=12   - Pos x.
 * @property {double}  mesh.meshpoint3x15.y=4   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x15.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x16   - MeshPoint3x16.
 * @property {bool}  mesh.meshpoint3x16.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x16.x=-12   - Pos x.
 * @property {double}  mesh.meshpoint3x16.y=6   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x16.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x17   - MeshPoint3x17.
 * @property {bool}  mesh.meshpoint3x17.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x17.x=-10   - Pos x.
 * @property {double}  mesh.meshpoint3x17.y=6   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x17.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x18   - MeshPoint3x18.
 * @property {bool}  mesh.meshpoint3x18.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x18.x=-8   - Pos x.
 * @property {double}  mesh.meshpoint3x18.y=6   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x18.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x19   - MeshPoint3x19.
 * @property {bool}  mesh.meshpoint3x19.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x19.x=-6   - Pos x.
 * @property {double}  mesh.meshpoint3x19.y=6   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x19.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x20   - MeshPoint3x20.
 * @property {bool}  mesh.meshpoint3x20.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x20.x=-4   - Pos x.
 * @property {double}  mesh.meshpoint3x20.y=6   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x20.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x21   - MeshPoint3x21.
 * @property {bool}  mesh.meshpoint3x21.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x21.x=-2   - Pos x.
 * @property {double}  mesh.meshpoint3x21.y=6   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x21.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x22   - MeshPoint3x22.
 * @property {bool}  mesh.meshpoint3x22.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x22.x=0   - Pos x.
 * @property {double}  mesh.meshpoint3x22.y=6   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x22.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x23   - MeshPoint3x23.
 * @property {bool}  mesh.meshpoint3x23.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x23.x=2   - Pos x.
 * @property {double}  mesh.meshpoint3x23.y=6   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x23.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x24   - MeshPoint3x24.
 * @property {bool}  mesh.meshpoint3x24.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x24.x=4   - Pos x.
 * @property {double}  mesh.meshpoint3x24.y=6   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x24.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x25   - MeshPoint3x25.
 * @property {bool}  mesh.meshpoint3x25.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x25.x=6   - Pos x.
 * @property {double}  mesh.meshpoint3x25.y=6   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x25.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x26   - MeshPoint3x26.
 * @property {bool}  mesh.meshpoint3x26.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x26.x=8   - Pos x.
 * @property {double}  mesh.meshpoint3x26.y=6   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x26.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x27   - MeshPoint3x27.
 * @property {bool}  mesh.meshpoint3x27.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x27.x=10   - Pos x.
 * @property {double}  mesh.meshpoint3x27.y=6   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x27.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x28   - MeshPoint3x28.
 * @property {bool}  mesh.meshpoint3x28.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x28.x=12   - Pos x.
 * @property {double}  mesh.meshpoint3x28.y=6   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x28.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x29   - MeshPoint3x29.
 * @property {bool}  mesh.meshpoint3x29.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x29.x=-12   - Pos x.
 * @property {double}  mesh.meshpoint3x29.y=8   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x29.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint3x30   - MeshPoint3x30.
 * @property {bool}  mesh.meshpoint3x30.separate=On   - Separate.
 * @property {double}  mesh.meshpoint3x30.x=-6   - Pos x.
 * @property {double}  mesh.meshpoint3x30.y=8   - Pos y.
 * @property {point_2d}  mesh.meshpoint3x30.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint4x0   - MeshPoint4x0.
 * @property {bool}  mesh.meshpoint4x0.separate=On   - Separate.
 * @property {double}  mesh.meshpoint4x0.x=0   - Pos x.
 * @property {double}  mesh.meshpoint4x0.y=8   - Pos y.
 * @property {point_2d}  mesh.meshpoint4x0.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint4x1   - MeshPoint4x1.
 * @property {bool}  mesh.meshpoint4x1.separate=On   - Separate.
 * @property {double}  mesh.meshpoint4x1.x=6   - Pos x.
 * @property {double}  mesh.meshpoint4x1.y=8   - Pos y.
 * @property {point_2d}  mesh.meshpoint4x1.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint4x2   - MeshPoint4x2.
 * @property {bool}  mesh.meshpoint4x2.separate=On   - Separate.
 * @property {double}  mesh.meshpoint4x2.x=12   - Pos x.
 * @property {double}  mesh.meshpoint4x2.y=8   - Pos y.
 * @property {point_2d}  mesh.meshpoint4x2.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint4x3   - MeshPoint4x3.
 * @property {bool}  mesh.meshpoint4x3.separate=On   - Separate.
 * @property {double}  mesh.meshpoint4x3.x=-12   - Pos x.
 * @property {double}  mesh.meshpoint4x3.y=10   - Pos y.
 * @property {point_2d}  mesh.meshpoint4x3.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint4x4   - MeshPoint4x4.
 * @property {bool}  mesh.meshpoint4x4.separate=On   - Separate.
 * @property {double}  mesh.meshpoint4x4.x=-6   - Pos x.
 * @property {double}  mesh.meshpoint4x4.y=10   - Pos y.
 * @property {point_2d}  mesh.meshpoint4x4.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint4x5   - MeshPoint4x5.
 * @property {bool}  mesh.meshpoint4x5.separate=On   - Separate.
 * @property {double}  mesh.meshpoint4x5.x=0   - Pos x.
 * @property {double}  mesh.meshpoint4x5.y=10   - Pos y.
 * @property {point_2d}  mesh.meshpoint4x5.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint4x6   - MeshPoint4x6.
 * @property {bool}  mesh.meshpoint4x6.separate=On   - Separate.
 * @property {double}  mesh.meshpoint4x6.x=6   - Pos x.
 * @property {double}  mesh.meshpoint4x6.y=10   - Pos y.
 * @property {point_2d}  mesh.meshpoint4x6.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint4x7   - MeshPoint4x7.
 * @property {bool}  mesh.meshpoint4x7.separate=On   - Separate.
 * @property {double}  mesh.meshpoint4x7.x=12   - Pos x.
 * @property {double}  mesh.meshpoint4x7.y=10   - Pos y.
 * @property {point_2d}  mesh.meshpoint4x7.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint4x8   - MeshPoint4x8.
 * @property {bool}  mesh.meshpoint4x8.separate=On   - Separate.
 * @property {double}  mesh.meshpoint4x8.x=-12   - Pos x.
 * @property {double}  mesh.meshpoint4x8.y=12   - Pos y.
 * @property {point_2d}  mesh.meshpoint4x8.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint4x9   - MeshPoint4x9.
 * @property {bool}  mesh.meshpoint4x9.separate=On   - Separate.
 * @property {double}  mesh.meshpoint4x9.x=-10   - Pos x.
 * @property {double}  mesh.meshpoint4x9.y=12   - Pos y.
 * @property {point_2d}  mesh.meshpoint4x9.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint4x10   - MeshPoint4x10.
 * @property {bool}  mesh.meshpoint4x10.separate=On   - Separate.
 * @property {double}  mesh.meshpoint4x10.x=-8   - Pos x.
 * @property {double}  mesh.meshpoint4x10.y=12   - Pos y.
 * @property {point_2d}  mesh.meshpoint4x10.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint5x0   - MeshPoint5x0.
 * @property {bool}  mesh.meshpoint5x0.separate=On   - Separate.
 * @property {double}  mesh.meshpoint5x0.x=-6   - Pos x.
 * @property {double}  mesh.meshpoint5x0.y=12   - Pos y.
 * @property {point_2d}  mesh.meshpoint5x0.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint5x1   - MeshPoint5x1.
 * @property {bool}  mesh.meshpoint5x1.separate=On   - Separate.
 * @property {double}  mesh.meshpoint5x1.x=-4   - Pos x.
 * @property {double}  mesh.meshpoint5x1.y=12   - Pos y.
 * @property {point_2d}  mesh.meshpoint5x1.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint5x2   - MeshPoint5x2.
 * @property {bool}  mesh.meshpoint5x2.separate=On   - Separate.
 * @property {double}  mesh.meshpoint5x2.x=-2   - Pos x.
 * @property {double}  mesh.meshpoint5x2.y=12   - Pos y.
 * @property {point_2d}  mesh.meshpoint5x2.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint5x3   - MeshPoint5x3.
 * @property {bool}  mesh.meshpoint5x3.separate=On   - Separate.
 * @property {double}  mesh.meshpoint5x3.x=0   - Pos x.
 * @property {double}  mesh.meshpoint5x3.y=12   - Pos y.
 * @property {point_2d}  mesh.meshpoint5x3.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint5x4   - MeshPoint5x4.
 * @property {bool}  mesh.meshpoint5x4.separate=On   - Separate.
 * @property {double}  mesh.meshpoint5x4.x=2   - Pos x.
 * @property {double}  mesh.meshpoint5x4.y=12   - Pos y.
 * @property {point_2d}  mesh.meshpoint5x4.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint5x5   - MeshPoint5x5.
 * @property {bool}  mesh.meshpoint5x5.separate=On   - Separate.
 * @property {double}  mesh.meshpoint5x5.x=4   - Pos x.
 * @property {double}  mesh.meshpoint5x5.y=12   - Pos y.
 * @property {point_2d}  mesh.meshpoint5x5.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint5x6   - MeshPoint5x6.
 * @property {bool}  mesh.meshpoint5x6.separate=On   - Separate.
 * @property {double}  mesh.meshpoint5x6.x=6   - Pos x.
 * @property {double}  mesh.meshpoint5x6.y=12   - Pos y.
 * @property {point_2d}  mesh.meshpoint5x6.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint5x7   - MeshPoint5x7.
 * @property {bool}  mesh.meshpoint5x7.separate=On   - Separate.
 * @property {double}  mesh.meshpoint5x7.x=8   - Pos x.
 * @property {double}  mesh.meshpoint5x7.y=12   - Pos y.
 * @property {point_2d}  mesh.meshpoint5x7.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint5x8   - MeshPoint5x8.
 * @property {bool}  mesh.meshpoint5x8.separate=On   - Separate.
 * @property {double}  mesh.meshpoint5x8.x=10   - Pos x.
 * @property {double}  mesh.meshpoint5x8.y=12   - Pos y.
 * @property {point_2d}  mesh.meshpoint5x8.2dpoint   - Point.
 * @property {position_2d}  mesh.meshpoint5x9   - MeshPoint5x9.
 * @property {bool}  mesh.meshpoint5x9.separate=On   - Separate.
 * @property {double}  mesh.meshpoint5x9.x=12   - Pos x.
 * @property {double}  mesh.meshpoint5x9.y=12   - Pos y.
 * @property {point_2d}  mesh.meshpoint5x9.2dpoint   - Point.
 * @property {int}  mesh.rows=4   - Rows.
 * @property {int}  mesh.columns=4   - Columns.
 * @property {position_2d}  origin   - Origin.
 * @property {bool}  origin.separate=On   - Separate.
 * @property {double}  origin.x=0   - Pos x.
 * @property {double}  origin.y=0   - Pos y.
 * @property {point_2d}  origin.2dpoint   - Point.
 * @property {double}  width=12   - Width.
 * @property {double}  height=12   - Height.
 * @property {generic_enum}  [deformationquality="Very High"]   - Deformation Quality.
 */


/**
 * Attributes present in the node of type: 'EXTERNAL'
 * @name  NodeTypes#External
 * @property {string}  program_name   - External Program.
 * @property {string}  program_input   - Program First Input File ($IN1).
 * @property {string}  program_input2   - Program Second Input File ($IN2).
 * @property {string}  program_output   - Program Output File ($OUT).
 * @property {string}  extension=TGA   - Extension ($EXT).
 * @property {double}  program_num_param=0   - Numerical Parameter 1 ($NUM).
 * @property {bool}  program_uniqueid=true   - Generate Unique FileNames.
 * @property {double}  program_num_param_2=0   - Numerical Parameter 2 ($NUM2).
 * @property {double}  program_num_param_3=0   - Numerical Parameter 3 ($NUM3).
 * @property {double}  program_num_param_4=0   - Numerical Parameter 4 ($NUM4).
 * @property {double}  program_num_param_5=0   - Numerical Parameter 5 ($NUM5).
 */


/**
 * Attributes present in the node of type: 'PointConstraint2'
 * @name  NodeTypes#Two-Points-Constraint
 * @property {double}  active=100   - Active.
 * @property {double}  volumemod=75   - Volume Modifier.
 * @property {double}  volumemax=200   - Volume Max.
 * @property {double}  volumemin=25   - Volume Min.
 * @property {double}  stretchmax=0   - Distance Max.
 * @property {double}  stretchmin=0   - Distance Min.
 * @property {double}  skewcontrol=0   - Skew Modifier.
 * @property {double}  smooth=0   - Smoothing.
 * @property {double}  balance=0   - Point Balance.
 * @property {generic_enum}  [flattentype="Allow 3D Transform"]   - Flatten Type.
 * @property {generic_enum}  [transformtype="Translate"]   - Transform Type.
 * @property {generic_enum}  [primaryport="Right"]   - Primary Port.
 */


/**
 * Attributes present in the node of type: 'COLOR_SCALE'
 * @name  NodeTypes#Colour-Scale
 * @property {double}  red=1   - Red.
 * @property {double}  green=1   - Green.
 * @property {double}  blue=1   - Blue.
 * @property {double}  alpha=1   - Alpha.
 * @property {double}  hue=1   - Hue.
 * @property {double}  hue_offset=0   - Hue Offset.
 * @property {double}  saturation=1   - Saturation.
 * @property {double}  value=1   - Value.
 * @property {bool}  clampneg=false   - Clamp Negative.
 * @property {bool}  pre_multiplied_alpha=false   - Pre-multiplied Alpha.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'LightPosition'
 * @name  NodeTypes#Light-Position
 * @property {position_3d}  position0   - Position.
 * @property {bool}  position0.separate=On   - Separate.
 * @property {double}  position0.x=0   - Pos x.
 * @property {double}  position0.y=0   - Pos y.
 * @property {double}  position0.z=0   - Pos z.
 * @property {path_3d}  position0.3dpath   - Path.
 * @property {position_3d}  position1   - Look at.
 * @property {bool}  position1.separate=On   - Separate.
 * @property {double}  position1.x=1   - Pos x.
 * @property {double}  position1.y=0   - Pos y.
 * @property {double}  position1.z=0   - Pos z.
 * @property {path_3d}  position1.3dpath   - Path.
 */


/**
 * Attributes present in the node of type: 'SurfaceNormal'
 * @name  NodeTypes#Surface-Normal
 * @property {generic_enum}  [normalquality="Low"]   - Surface Normal Quality.
 */


/**
 * Attributes present in the node of type: 'FilterBanding'
 * @name  NodeTypes#Colour-Banding
 * @property {double}  threshold1=20   - Threshold 1.
 * @property {color}  colour1=ffffffff   - Colour 1.
 * @property {int}  colour1.red=255   - Red.
 * @property {int}  colour1.green=255   - Green.
 * @property {int}  colour1.blue=255   - Blue.
 * @property {int}  colour1.alpha=255   - Alpha.
 * @property {generic_enum}  [colour1.preferred_ui="Separate"]   - Preferred Editor.
 * @property {double}  blur1=0   - Blur 1.
 * @property {double}  threshold2=40   - Threshold 2.
 * @property {color}  colour2=ffffffff   - Colour 2.
 * @property {int}  colour2.red=255   - Red.
 * @property {int}  colour2.green=255   - Green.
 * @property {int}  colour2.blue=255   - Blue.
 * @property {int}  colour2.alpha=255   - Alpha.
 * @property {generic_enum}  [colour2.preferred_ui="Separate"]   - Preferred Editor.
 * @property {double}  blur2=0   - Blur 2.
 * @property {double}  threshold3=20   - Threshold 3.
 * @property {color}  colour3=ffffffff   - Colour 3.
 * @property {int}  colour3.red=255   - Red.
 * @property {int}  colour3.green=255   - Green.
 * @property {int}  colour3.blue=255   - Blue.
 * @property {int}  colour3.alpha=255   - Alpha.
 * @property {generic_enum}  [colour3.preferred_ui="Separate"]   - Preferred Editor.
 * @property {double}  blur3=0   - Blur 3.
 * @property {double}  threshold4=20   - Threshold 4.
 * @property {color}  colour4=ffffffff   - Colour 4.
 * @property {int}  colour4.red=255   - Red.
 * @property {int}  colour4.green=255   - Green.
 * @property {int}  colour4.blue=255   - Blue.
 * @property {int}  colour4.alpha=255   - Alpha.
 * @property {generic_enum}  [colour4.preferred_ui="Separate"]   - Preferred Editor.
 * @property {double}  blur4=0   - Blur 4.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'MATTE_RESIZE'
 * @name  NodeTypes#Matte-Resize
 * @property {double}  radius=0   - Radius.
 */


/**
 * Attributes present in the node of type: 'IncreaseOpacity'
 * @name  NodeTypes#Increase-Opacity
 * @property {double}  factor=1.8000   - Factor.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'FLICKER_BLUR'
 * @name  NodeTypes#Anti-Flicker
 * @property {double}  radius=0   - Radius.
 */


/**
 * Attributes present in the node of type: 'ObjectDefinition'
 * @name  NodeTypes#Volume-Object
 * @property {int}  objectid=1   - ID.
 * @property {bool}  cutvolumecues=false   - Cut Volume Cues with Geometry.
 * @property {bool}  usegeometry=true   - Use Drawing to Create Volume.
 * @property {double}  geometryintensity=50   - Elevation Baseline.
 * @property {double}  elevationmin=0   - Elevation Min.
 * @property {double}  elevationmax=1   - Elevation Max.
 * @property {double}  smoothness=1   - Elevation Smoothness.
 * @property {bool}  invertmask=false   - Invert Height Matte.
 */


/**
 * Attributes present in the node of type: 'LuminanceThreshold'
 * @name  NodeTypes#Luminance-Threshold
 * @property {double}  luminancethresholdthresh=75   - Threshold.
 * @property {bool}  luminancethresholdsoften=true   - Soften Colours.
 * @property {double}  luminancethresholdgamma=1.5000   - Gamma Correction.
 * @property {bool}  luminancethresholdgrey=false   - Output Greyscale Matte.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'PIXELATE'
 * @name  NodeTypes#Pixelate
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 * @property {double}  factor=0.0125   - Factor.
 */


/**
 * Attributes present in the node of type: 'LightShader'
 * @name  NodeTypes#Light-Shader
 * @property {generic_enum}  [lighttype="Directional"]   - Light Type.
 * @property {double}  floodangle=90   - Cone Angle.
 * @property {double}  floodsharpness=0   - Diffusion.
 * @property {double}  floodradius=2000   - Falloff.
 * @property {double}  pointelevation=200   - Light Source Elevation.
 * @property {double}  anglethreshold=90   - Surface Reflectivity.
 * @property {generic_enum}  [shadetype="Smooth"]   - Shading Type.
 * @property {double}  bias=0.1000   - Bias.
 * @property {double}  exponent=2   - Abruptness.
 * @property {color}  lightcolor=ffc8c8c8   - Light Colour.
 * @property {int}  lightcolor.red=200   - Red.
 * @property {int}  lightcolor.green=200   - Green.
 * @property {int}  lightcolor.blue=200   - Blue.
 * @property {int}  lightcolor.alpha=255   - Alpha.
 * @property {generic_enum}  [lightcolor.preferred_ui="Separate"]   - Preferred Editor.
 * @property {bool}  flatten=true   - Flatten Fx.
 * @property {bool}  useimagecolor=false   - Use image Colour.
 * @property {double}  imagecolorweight=50   - Image Colour Intensity.
 * @property {bool}  adjustlevel=false   - Adjust Light Intensity.
 * @property {double}  adjustedlevel=75   - Intensity.
 * @property {double}  scale=1   - Multiplier.
 * @property {bool}  usesurface=false   - Use Surface Lighting.
 * @property {double}  speculartransparency=100   - Specular Transparency.
 * @property {double}  specularity=100   - Specular Strength.
 * @property {double}  distancefalloff=0   - Distance Falloff.
 */


/**
 * Attributes present in the node of type: 'DeformationRootModule'
 * @name  NodeTypes#Deformation-Root
 * @property {generic_enum}  [deformationquality="Very High"]   - Quality.
 */


/**
 * Attributes present in the node of type: 'DeformationSwitchModule'
 * @name  NodeTypes#Deformation-Switch
 * @property {generic_enum}  [vectorquality="Very High"]   - Vector Quality.
 * @property {double}  fadeexponent=3   - Influence Fade Exponent.
 * @property {bool}  fadeinside=false   - Fade Inside Zones.
 * @property {int}  enabledeformation=1   - Enable Deformation.
 * @property {int}  chainselectionreference=1   - Kinematic Chain Selection Reference.
 */


/**
 * Attributes present in the node of type: 'AutoMuscleModule'
 * @name  NodeTypes#Auto-Muscle
 * @property {bool}  enableleft=true   - Muscle Left.
 * @property {double}  leftstart=-3   - Left Start.
 * @property {double}  leftspan=1   - Left Span.
 * @property {double}  leftamplitude=0.2500   - Left Amplitude.
 * @property {bool}  enableright=true   - Muscle Right.
 * @property {bool}  symmetric=false   - Same as Left.
 * @property {double}  rightstart=-3   - Right Start.
 * @property {double}  rightspan=1   - Right Span.
 * @property {double}  rightamplitude=0.2500   - Right Amplitude.
 */


/**
 * Attributes present in the node of type: 'AutoFoldModule'
 * @name  NodeTypes#Deformation-AutoFold
 * @property {int}  enable=1   - Enable AutoFold.
 * @property {double}  length=12   - Length.
 */


/**
 * Attributes present in the node of type: 'DeformationScaleModule'
 * @name  NodeTypes#Deformation-Scale
 * @property {bool}  enableleft=true   - Scale Left.
 * @property {double}  leftfadein=0   - Left Fade In.
 * @property {double}  leftfadeout=0   - Left Fade Out.
 * @property {double}  leftstart=0   - Left Start.
 * @property {double}  leftspan=1   - Left Span.
 * @property {double}  leftscale0=1   - Left Start Scale.
 * @property {double}  leftscale1=1   - Left End Scale.
 * @property {double}  lefthandleposition0=25   - Left Start Handle Position.
 * @property {double}  lefthandleposition1=25   - Left End Handle Position.
 * @property {double}  lefthandlescale0=1   - Left Start Handle Scale.
 * @property {double}  lefthandlescale1=1   - Left End Handle Scale.
 * @property {bool}  enableright=true   - Scale Right.
 * @property {bool}  symmetric=false   - Same as Left.
 * @property {double}  rightfadein=0   - Right Fade In.
 * @property {double}  rightfadeout=0   - Right Fade Out.
 * @property {double}  rightstart=0   - Right Start.
 * @property {double}  rightspan=1   - Right Span.
 * @property {double}  rightscale0=1   - Right Start Scale.
 * @property {double}  rightscale1=1   - Right End Scale.
 * @property {double}  righthandleposition0=25   - Right Start Handle Position.
 * @property {double}  righthandleposition1=25   - Right End Handle Position.
 * @property {double}  righthandlescale0=1   - Right Start Handle Scale.
 * @property {double}  righthandlescale1=1   - Right End Handle Scale.
 */


/**
 * Attributes present in the node of type: 'DeformationWaveModule'
 * @name  NodeTypes#Deformation-Wave
 * @property {bool}  enableleft=true   - Wave Left.
 * @property {double}  leftstart=0   - Left Start.
 * @property {double}  leftspan=10   - Left Span.
 * @property {double}  leftoffsett=0   - Left Offset Deformer.
 * @property {double}  leftamplitude=1   - Left Amplitude.
 * @property {double}  leftoffset=1   - Left Offset Scaling.
 * @property {double}  leftperiod=1   - Left Period.
 * @property {bool}  enableright=true   - Wave Right.
 * @property {bool}  symmetric=false   - Same as Left.
 * @property {double}  rightstart=0   - Right Start.
 * @property {double}  rightspan=10   - Right Span.
 * @property {double}  rightoffsett=0   - Right Offset Deformer.
 * @property {double}  rightamplitude=1   - Right Amplitude.
 * @property {double}  rightoffset=1   - Right Offset Scaling.
 * @property {double}  rightperiod=1   - Right Period.
 */


/**
 * Attributes present in the node of type: 'FoldModule'
 * @name  NodeTypes#Deformation-Fold
 * @property {int}  enable=1   - Enable Fold.
 * @property {double}  t=1   - Where.
 * @property {double}  tbefore=1   - Span Before.
 * @property {double}  tafter=1   - Span After.
 * @property {double}  angle=0   - Orientation.
 * @property {double}  length=12   - Length.
 */


/**
 * Attributes present in the node of type: 'DeformationUniformScaleModule'
 * @name  NodeTypes#Deformation-Uniform-Scale
 * @property {double}  scale=1   - Scale.
 */


/**
 * Attributes present in the node of type: 'DEPTHBLUR'
 * @name  NodeTypes#Z-Buffer-Smoothing
 * @property {double}  histogram_range=80   - Histogram Range.
 * @property {int}  kernel_size=5   - Kernel Size.
 */


/**
 * Attributes present in the node of type: 'ParticleExplosion'
 * @name  NodeTypes#Explosion
 * @property {int}  trigger=1   - Trigger.
 * @property {double}  explosionx=0   - X.
 * @property {double}  explosiony=0   - Y.
 * @property {double}  explosionz=0   - Z.
 * @property {double}  explosionradius=3   - Radius.
 * @property {double}  explosionsigma=1   - Sigma.
 * @property {double}  explosionmagnitude=5   - Magnitude.
 * @property {double}  explosionepsilon=0.0010   - Epsilon.
 */


/**
 * Attributes present in the node of type: 'ParticleImageEmitter'
 * @name  NodeTypes#Image-Fracture
 * @property {int}  trigger=0   - Trigger.
 * @property {double}  ageatbirth=0   - Age at Birth.
 * @property {double}  ageatbirthstd=0   - Age at Birth Standard Deviation.
 * @property {double}  mass=1   - Particles Mass.
 * @property {generic_enum}  [typechoosingstrategy="Sequentially Assign Type Number"]   - Type Generation Strategy.
 * @property {int}  particletype0=1   - Particle Type 0.
 * @property {int}  particletype1=1   - Particle Type 1.
 * @property {double}  particlesize=1   - Size over Age.
 * @property {bool}  overridevelocity=false   - Align Initial Velocity.
 * @property {generic_enum}  [blend_mode="Normal"]   - Blend Mode.
 * @property {double}  blendintensity=100   - Blend Intensity.
 * @property {generic_enum}  [colouringstrategy="Use Drawing Colour"]   - Colouring Strategy.
 * @property {color}  particlecolour=ffffffff   - Colour.
 * @property {int}  particlecolour.red=255   - Red.
 * @property {int}  particlecolour.green=255   - Green.
 * @property {int}  particlecolour.blue=255   - Blue.
 * @property {int}  particlecolour.alpha=255   - Alpha.
 * @property {generic_enum}  [particlecolour.preferred_ui="Separate"]   - Preferred Editor.
 * @property {bool}  alignwithdirection=true   - Align with Direction.
 * @property {bool}  userotation=false   - Use Rotation of Particle.
 * @property {bool}  directionalscale=false   - Directional Scale.
 * @property {double}  directionalscalefactor=1   - Directional Scale Exponent Factor.
 * @property {bool}  keepvolume=true   - Keep Volume.
 * @property {generic_enum}  [blur="No Blur"]   - Blur.
 * @property {double}  blurintensity=1   - Blur Intensity.
 * @property {double}  blurfallof=0.5000   - Falloff Rate.
 * @property {bool}  flipwithdirectionx=false   - Flip X Axis to Match Direction.
 * @property {bool}  flipwithdirectiony=false   - Flip Y Axis to Match Direction.
 * @property {generic_enum}  [alignwithdirectionaxis="Positive X"]   - Axis to Align.
 */


/**
 * Attributes present in the node of type: 'ParticleBounce'
 * @name  NodeTypes#Bounce
 * @property {int}  trigger=1   - Trigger.
 * @property {double}  friction=0.5000   - Friction.
 * @property {double}  resilience=0.5000   - Resilience.
 * @property {double}  cutoff=0.5000   - Cutoff Speed.
 */


/**
 * Attributes present in the node of type: 'ParticleMove'
 * @name  NodeTypes#Move-Particles
 * @property {int}  trigger=1   - Trigger.
 * @property {bool}  moveage=false   - Age Particles.
 * @property {bool}  moveposition=true   - Move Position.
 * @property {bool}  moveangle=true   - Move Angle.
 * @property {bool}  followeachother=false   - Make Particles Follow each Other.
 * @property {double}  followintensity=1   - Follow Intensity.
 */


/**
 * Attributes present in the node of type: 'ParticleKill'
 * @name  NodeTypes#Kill
 * @property {int}  trigger=1   - Trigger.
 * @property {bool}  handlenaturaldeth=true   - Use Maximum Lifespan.
 * @property {bool}  killyounger=false   - Kill Younger.
 * @property {int}  killyoungerthan=-1   - Kill Younger than.
 * @property {bool}  killolder=true   - Kill Older.
 * @property {int}  killolderthan=100   - Kill Older than.
 */


/**
 * Attributes present in the node of type: 'ParticleOrbit'
 * @name  NodeTypes#Orbit
 * @property {int}  trigger=1   - Trigger.
 * @property {generic_enum}  [strategy="Around Point"]   - Orbit Type.
 * @property {double}  magnitude=1   - Magnitude.
 * @property {double}  v0x=0   - Point X.
 * @property {double}  v0y=0   - Point Y.
 * @property {double}  v0z=0   - Point Z.
 * @property {double}  v1x=0   - Direction X.
 * @property {double}  v1y=0   - Direction Y.
 * @property {double}  v1z=1   - Direction Z.
 */


/**
 * Attributes present in the node of type: 'ParticleGravity'
 * @name  NodeTypes#Gravity
 * @property {int}  trigger=1   - Trigger.
 * @property {bool}  applygravity=true   - Apply Gravity.
 * @property {double}  directionx=0   - X Direction.
 * @property {double}  directiony=-1   - Y Direction.
 * @property {double}  directionz=0   - Z Direction.
 * @property {bool}  relativegravity=false   - Apply Gravity between Particles (Relative Gravity).
 * @property {double}  relativemagnitude=1   - Relative Gravity Magnitude.
 * @property {double}  relativegravityepsilon=0.0010   - Relative Gravity Epsilon.
 * @property {double}  relativegravitymaxradius=2   - Relative Gravity Maximum Distance.
 */


/**
 * Attributes present in the node of type: 'Particle3dRegion'
 * @name  NodeTypes#3D-Region
 * @property {generic_enum}  [shapetype="Sphere"]   - Type.
 * @property {double}  sizex=6   - Width.
 * @property {double}  sizey=6   - Height.
 * @property {double}  sizez=6   - Depth.
 * @property {double}  outerradius=6   - Max.
 * @property {double}  innerradius=0   - Min.
 */


/**
 * Attributes present in the node of type: 'ParticleSink'
 * @name  NodeTypes#Sink
 * @property {int}  trigger=1   - Trigger.
 * @property {bool}  ifinside=false   - Invert.
 */


/**
 * Attributes present in the node of type: 'ParticleRandom'
 * @name  NodeTypes#Random-Parameter
 * @property {int}  trigger=1   - Trigger.
 * @property {generic_enum}  [parametertorandomize="Speed"]   - Parameter.
 */


/**
 * Attributes present in the node of type: 'ParticleVortex'
 * @name  NodeTypes#Vortex
 * @property {int}  trigger=1   - Trigger.
 * @property {double}  vortexx=0   - X Direction.
 * @property {double}  vortexy=12   - Y Direction.
 * @property {double}  vortexz=0   - Z Direction.
 * @property {double}  vortexradius=4   - Radius.
 * @property {double}  vortexexponent=1   - Exponent (1=cone).
 * @property {double}  vortexupspeed=0.0050   - Up Acceleration.
 * @property {double}  vortexinspeed=0.0050   - In Acceleration.
 * @property {double}  vortexaroundspeed=0.0050   - Around Acceleration.
 */


/**
 * Attributes present in the node of type: 'ParticleWindFriction'
 * @name  NodeTypes#Wind-Friction
 * @property {int}  trigger=1   - Trigger.
 * @property {double}  windfrictionx=0   - Friction/Wind X.
 * @property {double}  windfrictiony=0   - Friction/Wind Y.
 * @property {double}  windfrictionz=0   - Friction/Wind Z.
 * @property {double}  windfrictionminspeed=0   - Min Speed.
 * @property {double}  windfrictionmaxspeed=10   - Max Speed.
 */


/**
 * Attributes present in the node of type: 'ParticleRotationVelocity'
 * @name  NodeTypes#Rotation-Velocity
 * @property {int}  trigger=1   - Trigger.
 * @property {double}  w0=0   - Minimum.
 * @property {double}  w1=5   - Maximum.
 * @property {generic_enum}  [axisstrategy="Constant Axis"]   - Axis Type.
 * @property {double}  v0x=0   - Axis0 X.
 * @property {double}  v0y=0   - Axis0 Y.
 * @property {double}  v0z=1   - Axis0 Z.
 * @property {double}  v1x=0   - Axis1 X.
 * @property {double}  v1y=1   - Axis1 Y.
 * @property {double}  v1z=0   - Axis1 Z.
 */


/**
 * Attributes present in the node of type: 'ParticleRepulse'
 * @name  NodeTypes#Repulse
 * @property {int}  trigger=1   - Trigger.
 * @property {double}  magnitude=1   - Magnitude.
 * @property {double}  lookahead=1   - Look Ahead.
 * @property {double}  epsilon=0.0010   - Epsilon.
 */


/**
 * Attributes present in the node of type: 'ParticleJavascript'
 * @name  NodeTypes#Scripted-Action[Beta]
 * @property {int}  trigger=1   - Trigger.
 * @property {file_editor}  particle_action_script   - .
 * @property {file_library}  files   - .
 */


/**
 * Attributes present in the node of type: 'ParticleVelocity'
 * @name  NodeTypes#Velocity
 * @property {int}  trigger=1   - Trigger.
 * @property {generic_enum}  [velocitytype="Constant Speed"]   - Velocity Type.
 * @property {double}  v0x=1   - X.
 * @property {double}  v0y=0   - Y.
 * @property {double}  v0z=0   - Z.
 * @property {double}  minspeed=0.5000   - Minimum.
 * @property {double}  maxspeed=0.5000   - Maximum.
 * @property {double}  theta0=0   - Minimum Angle (degrees).
 * @property {double}  theta1=30   - Maximum Angle (degrees).
 * @property {bool}  bilateral=false   - Bilateral.
 */


/**
 * Attributes present in the node of type: 'ParticleSize'
 * @name  NodeTypes#Size
 * @property {int}  trigger=1   - Trigger.
 * @property {generic_enum}  [sizestrategy="Constant Size"]   - Size Type.
 * @property {double}  particlesize=1   - Size.
 */


/**
 * Attributes present in the node of type: 'ParticlePlanarRegion'
 * @name  NodeTypes#Planar-Region
 * @property {generic_enum}  [shapetype="Rectangle"]   - Shape Type.
 * @property {double}  sizex=12   - Width.
 * @property {double}  sizey=12   - Height.
 * @property {double}  x1=0   - X.
 * @property {double}  y1=0   - Y.
 * @property {double}  x2=0   - X.
 * @property {double}  y2=0   - Y.
 * @property {double}  x3=1   - X.
 * @property {double}  y3=1   - Y.
 * @property {double}  minradius=0   - Minimum.
 * @property {double}  maxradius=6   - Maximum.
 * @property {bool}  mirrornegativeframes=false   - Mirror Negative Frames.
 */


/**
 * Attributes present in the node of type: 'ParticleBkerComposite'
 * @name  NodeTypes#Baker-Composite
 */


/**
 * Attributes present in the node of type: 'ParticleSprite'
 * @name  NodeTypes#Sprite-Emitter
 * @property {int}  trigger=1   - Trigger.
 * @property {double}  ageatbirth=0   - Age at Birth.
 * @property {double}  ageatbirthstd=0   - Age at Birth Standard Deviation.
 * @property {double}  mass=1   - Particles Mass.
 * @property {generic_enum}  [typechoosingstrategy="Sequentially Assign Type Number"]   - Type Generation Strategy.
 * @property {int}  particletype0=1   - Particle Type 0.
 * @property {int}  particletype1=1   - Particle Type 1.
 * @property {double}  particlesize=1   - Size over Age.
 * @property {bool}  overridevelocity=false   - Align Initial Velocity.
 * @property {generic_enum}  [blend_mode="Normal"]   - Blend Mode.
 * @property {double}  blendintensity=100   - Blend Intensity.
 * @property {generic_enum}  [colouringstrategy="Use Drawing Colour"]   - Colouring Strategy.
 * @property {color}  particlecolour=ffffffff   - Colour.
 * @property {int}  particlecolour.red=255   - Red.
 * @property {int}  particlecolour.green=255   - Green.
 * @property {int}  particlecolour.blue=255   - Blue.
 * @property {int}  particlecolour.alpha=255   - Alpha.
 * @property {generic_enum}  [particlecolour.preferred_ui="Separate"]   - Preferred Editor.
 * @property {bool}  alignwithdirection=true   - Align with Direction.
 * @property {bool}  userotation=false   - Use Rotation of Particle.
 * @property {bool}  directionalscale=false   - Directional Scale.
 * @property {double}  directionalscalefactor=1   - Directional Scale Exponent Factor.
 * @property {bool}  keepvolume=true   - Keep Volume.
 * @property {generic_enum}  [blur="No Blur"]   - Blur.
 * @property {double}  blurintensity=1   - Blur Intensity.
 * @property {double}  blurfallof=0.5000   - Falloff Rate.
 * @property {bool}  flipwithdirectionx=false   - Flip X Axis to Match Direction.
 * @property {bool}  flipwithdirectiony=false   - Flip Y Axis to Match Direction.
 * @property {generic_enum}  [alignwithdirectionaxis="Positive X"]   - Axis to Align.
 * @property {generic_enum}  [renderingstrategy="Use Particle Type"]   - Rendering Strategy.
 * @property {generic_enum}  [cycletype="No Cycle"]   - Cycling.
 * @property {int}  cyclesize=5   - Number of Drawings in Cycle.
 * @property {int}  numberofparticles=100   - Number of Particles.
 * @property {double}  probabilityofgeneratingparticles=100   - Probability of Generating Any Particles.
 * @property {int}  indexselector=0   - Selector.
 * @property {double}  multisize=1   - Region Size for Baked Particle Input.
 * @property {bool}  copyvelocity=false   - Copy Particle Velocity for Baked Particle Input.
 * @property {double}  mininitialangle=0   - Minimum Initial Rotation.
 * @property {double}  maxinitialangle=0   - Maximum Initial Rotation.
 * @property {bool}  copyage=false   - Add Particle Age for Baked Particle Input.
 * @property {bool}  applyprobabilityforeachparticle=true   - Apply Probability for Each Particle.
 * @property {double}  sourcetimespan=0   - Source Sampling Duration.
 * @property {double}  sourcesamplesperframe=16   - Source Samples per Frame.
 * @property {int}  seed=0   - Streak Seed.
 * @property {double}  streaksize=0   - Streak Size.
 * @property {double}  sourcetimeoffset=0   - Source Sampling Time Offset.
 * @property {bool}  setmaxlifespan=false   - Set Maximum Lifespan.
 * @property {double}  maxlifespan=30   - Maximum Lifespan.
 * @property {double}  maxlifespansigma=0   - Maximum Lifespan Sigma.
 */


/**
 * Attributes present in the node of type: 'ParticleRegionComposite'
 * @name  NodeTypes#Particle-Region-Composite
 */


/**
 * Attributes present in the node of type: 'ParticleSystemComposite'
 * @name  NodeTypes#Particle-System-Composite
 */


/**
 * Attributes present in the node of type: 'LensFlare'
 * @name  NodeTypes#LensFlare
 * @property {generic_enum}  [blend_mode="Normal"]   - Blend Mode.
 * @property {generic_enum}  [flash_blend_mode="Normal"]   - SWF Blend Mode.
 * @property {bool}  usergba=false   - Blend Mode: Normal/Screen.
 * @property {bool}  brightenable=true   - On/Off.
 * @property {double}  brightness=100   - Intensity.
 * @property {color}  brightcolor=ffffffff   - Color.
 * @property {int}  brightcolor.red=255   - Red.
 * @property {int}  brightcolor.green=255   - Green.
 * @property {int}  brightcolor.blue=255   - Blue.
 * @property {int}  brightcolor.alpha=255   - Alpha.
 * @property {generic_enum}  [brightcolor.preferred_ui="Separate"]   - Preferred Editor.
 * @property {double}  positionx=6   - PositionX.
 * @property {double}  positiony=6   - PositionY.
 * @property {double}  positionz=0   - PositionZ.
 * @property {generic_enum}  [flareconfig="Type 1"]   - Flare Type.
 * @property {bool}  enable1=true   - Enable/Disable.
 * @property {double}  size1=0.7500   - Size.
 * @property {double}  position1=0   - Position.
 * @property {int}  drawing1=1   - Drawing.
 * @property {double}  blur1=0   - Blur Intensity.
 * @property {bool}  enable2=true   - Enable/Disable.
 * @property {double}  size2=0.8000   - Size.
 * @property {double}  position2=2   - Position.
 * @property {int}  drawing2=2   - Drawing.
 * @property {double}  blur2=0   - Blur Intensity.
 * @property {bool}  enable3=true   - Enable/Disable.
 * @property {double}  size3=1.2000   - Size.
 * @property {double}  position3=-0.2000   - Position.
 * @property {int}  drawing3=3   - Drawing.
 * @property {double}  blur3=0   - Blur Intensity.
 * @property {bool}  enable4=true   - Enable/Disable.
 * @property {double}  size4=0.6500   - Size.
 * @property {double}  position4=0.7500   - Position.
 * @property {int}  drawing4=4   - Drawing.
 * @property {double}  blur4=0   - Blur Intensity.
 * @property {bool}  enable5=true   - Enable/Disable.
 * @property {double}  size5=1   - Size.
 * @property {double}  position5=2   - Position.
 * @property {int}  drawing5=5   - Drawing.
 * @property {double}  blur5=0   - Blur Intensity.
 * @property {bool}  enable6=true   - Enable/Disable.
 * @property {double}  size6=1   - Size.
 * @property {double}  position6=0   - Position.
 * @property {int}  drawing6=6   - Drawing.
 * @property {double}  blur6=0   - Blur Intensity.
 * @property {bool}  enable7=true   - Enable/Disable.
 * @property {double}  size7=0.8000   - Size.
 * @property {double}  position7=2   - Position.
 * @property {int}  drawing7=7   - Drawing.
 * @property {double}  blur7=0   - Blur Intensity.
 * @property {bool}  enable8=true   - Enable/Disable.
 * @property {double}  size8=0.5500   - Size.
 * @property {double}  position8=-0.3000   - Position.
 * @property {int}  drawing8=8   - Drawing.
 * @property {double}  blur8=0   - Blur Intensity.
 * @property {bool}  enable9=true   - Enable/Disable.
 * @property {double}  size9=0.6500   - Size.
 * @property {double}  position9=1.2500   - Position.
 * @property {int}  drawing9=9   - Drawing.
 * @property {double}  blur9=0   - Blur Intensity.
 * @property {bool}  enable10=true   - Enable/Disable.
 * @property {double}  size10=0.5500   - Size.
 * @property {double}  position10=2.3000   - Position.
 * @property {int}  drawing10=10   - Drawing.
 * @property {double}  blur10=0   - Blur Intensity.
 */


/**
 * Attributes present in the node of type: 'CROP'
 * @name  NodeTypes#Crop
 * @property {int}  res_x=1920   - X Resolution.
 * @property {int}  res_y=1080   - Y Resolution.
 * @property {double}  offset_x=0   - X Offset.
 * @property {double}  offset_y=0   - Y Offset.
 * @property {bool}  draw_frame=false   - Draw Frame.
 * @property {color}  frame_color=ffffffff   - Frame Color.
 * @property {int}  frame_color.red=255   - Red.
 * @property {int}  frame_color.green=255   - Green.
 * @property {int}  frame_color.blue=255   - Blue.
 * @property {int}  frame_color.alpha=255   - Alpha.
 * @property {generic_enum}  [frame_color.preferred_ui="Separate"]   - Preferred Editor.
 * @property {enable}  [enabling="Always Enabled"]   - Enabling.
 * @property {generic_enum}  [enabling.filter="Always Enabled"]   - Filter.
 * @property {string}  enabling.filter_name   - Filter name.
 * @property {int}  enabling.filter_res_x=720   - X resolution.
 * @property {int}  enabling.filter_res_y=540   - Y resolution.
 */


/**
 * Attributes present in the node of type: 'GLUE'
 * @name  NodeTypes#Glue
 * @property {bool}  invert_matte_port=true   - Invert Matte.
 * @property {double}  bias=0.5000   - Bias.
 * @property {double}  tension=1   - Tension.
 * @property {generic_enum}  [type="Curve"]   - Type.
 * @property {bool}  use_z=true   - Use Z for Composition Order.
 * @property {bool}  a_over_b=true   - A Over B.
 * @property {bool}  spread_a=false   - Spread A.
 */


/**
 * Attributes present in the node of type: 'DeformTransformOut'
 * @name  NodeTypes#Point-Kinematic-Output
 * @property {generic_enum}  [sample="One-Point Sampling"]   - Sampling Type.
 * @property {position_2d}  pivot1   - Main Position Tracker.
 * @property {bool}  pivot1.separate=Off   - Separate.
 * @property {double}  pivot1.x=0   - Pos x.
 * @property {double}  pivot1.y=0   - Pos y.
 * @property {point_2d}  pivot1.2dpoint   - Point.
 * @property {position_2d}  pivot2   - Tracker 2.
 * @property {bool}  pivot2.separate=Off   - Separate.
 * @property {double}  pivot2.x=1   - Pos x.
 * @property {double}  pivot2.y=0   - Pos y.
 * @property {point_2d}  pivot2.2dpoint   - Point.
 * @property {position_2d}  pivot3   - Tracker 3.
 * @property {bool}  pivot3.separate=Off   - Separate.
 * @property {double}  pivot3.x=0   - Pos x.
 * @property {double}  pivot3.y=1   - Pos y.
 * @property {point_2d}  pivot3.2dpoint   - Point.
 * @property {double}  volume=1   - Volume Modifier.
 */


/**
 * Attributes present in the node of type: 'AmbientOcclusion'
 * @name  NodeTypes#Ambient-Occlusion
 * @property {double}  darkness=200   - Darkness.
 * @property {double}  zrange=1   - Shadow Max Depth Range.
 * @property {double}  bias=0   - Shadow Bias.
 * @property {double}  exponent=1   - Abruptness.
 * @property {double}  gamma=2   - Shadow Gamma.
 * @property {double}  blur=10   - Affected Range.
 * @property {double}  postblur=0   - Post-Blur.
 * @property {double}  postblurthreshold=0.1000   - Post-Blur Depth Threshold.
 * @property {bool}  useimagecolor=false   - Use Image Colour.
 * @property {color}  color=ff000000   - Light Colour.
 * @property {int}  color.red=0   - Red.
 * @property {int}  color.green=0   - Green.
 * @property {int}  color.blue=0   - Blue.
 * @property {int}  color.alpha=255   - Alpha.
 * @property {generic_enum}  [color.preferred_ui="Separate"]   - Preferred Editor.
 * @property {double}  imagecolorweight=50   - Image Colour Intensity.
 * @property {bool}  invert_matte_port=false   - Invert Matte.
 */


/**
 * Attributes present in the node of type: 'SHADOW'
 * @name  NodeTypes#Shadow
 * @property {bool}  truck_factor=true   - Truck Factor.
 * @property {generic_enum}  [blur_type="Radial"]   - Blur Type.
 * @property {double}  radius=2   - Radius.
 * @property {double}  directional_angle=0   - Directional Angle.
 * @property {double}  directional_falloff_rate=1   - Directional Falloff Rate.
 * @property {bool}  use_matte_color=false   - Use Source Colour.
 * @property {bool}  invert_matte=false   - Invert Matte.
 * @property {color}  color=649c9c9c   - Color.
 * @property {int}  color.red=-100   - Red.
 * @property {int}  color.green=-100   - Green.
 * @property {int}  color.blue=-100   - Blue.
 * @property {int}  color.alpha=100   - Alpha.
 * @property {generic_enum}  [color.preferred_ui="Separate"]   - Preferred Editor.
 * @property {bool}  multiplicative=false   - Multiplicative.
 * @property {double}  colour_gain=1   - Intensity.
 */
