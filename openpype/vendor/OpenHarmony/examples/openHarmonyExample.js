// add this line at the top of your scripts to load the library before the execution.
include("openHarmony.js")


/**
 * Example function to showcase the functionalities of openHarmony.
 * This function creates a small rig of a car, animates it and exports it as a tpl.
 */
function makeCar(){
  // we group the functions in an undo group to undo it all at once.
  $.beginUndo("makeCar");

  var scene = $.scn;

  // get the main composite by getting all composites in the scene and keeping the first one.
  // a list of node types that exist in harmony is available here:
  // https://cfourney.github.io/OpenHarmony/NodeTypes.html
  var sceneComposite = scene.getNodesByType("COMPOSITE")[0];

  // --- creating the car's body ---

  // create a drawing node in the scene, with a single drawing spanning the scene
  // scene.root is the root group of the scene (or "Top"), and is considered to be a oGroupNode.
  // each node will be added directly into it.
  var carBodyNode = scene.root.addDrawingNode("car_body");

  // set some basic attributes on the drawing node. List of attributes available here:
  // https://cfourney.github.io/OpenHarmony/NodeTypes.html#Drawing
  carBodyNode.use_drawing_pivot = "Apply Embeded Pivot On Parent Peg";
  carBodyNode.can_animate = false; // disable "Animate using Animation Tools"

  // link the node to the scene composite, and place it above in the node view.
  carBodyNode.linkOutNode(sceneComposite);
  carBodyNode.centerAbove(sceneComposite);

  // we add a drawing to our drawing node and display it until the end of the timeline.
  var bodyDrawing = carBodyNode.element.addDrawing(1, "CAR_1");
  carBodyNode.timingColumn.extendExposures();

  // add a palette in the scene for our car.
  var carPalette = scene.addPalette("car");
  carPalette.colors[0].remove(); // we remove the "Default" color created with the palette.
  var carColor = carPalette.addColor("Body", new $.oColorValue("ffff00"));
  var carFill = new $.oFillStyle(carColor.id);

  // draw a car body onto the drawing:
  //
  //        ---------
  //       /  top    \
  //   +-------------------+
  //   |      body         |
  //   +-------------------+
  //

  // first we need to make sure the drawing we want to draw on is active
  scene.activeDrawing = bodyDrawing;

  // note: Harmony coordinates system is not like most computer graphics, with y values starting at the top and going down.
  // positive y values go up, and the center of the coordinates is the middle of the drawing.
  // When placing a rectangle, the "anchor" will be the bottom left corner and not the top left one.
  bodyDrawing.colorArt.drawRectangle(-400, -150, 800, 200, null, carFill);

  // we make a bit more complex shape for the top part, by specifying exactly the points we want.
  // a point with "onCurve" set to false will be a bezier handle an not a point on the outline.
  var topPath = [
    {x:200,y:-150,onCurve:true},
    {x:135,y:100,onCurve:false},
    {x:-250,y:100,onCurve:false},
    {x:-300,y:-150,onCurve:true},
    {x:200,y:-150,onCurve:true}, // we repeat the first point to close the shape.
  ];

  bodyDrawing.colorArt.drawShape(topPath, null, carFill);

  // set the pivot at the center of the contents of the drawing
  bodyDrawing.pivot = bodyDrawing.boundingBox.center;

  // --- creating a wheel on a separate drawing node ---

  // first add the new colors
  var wheelColor = carPalette.addColor("Wheel", new $.oColorValue("555555"));
  var wheelLineColor = carPalette.addColor("Wheel_line", new $.oColorValue("222222"));
  var wheelFill = new $.oFillStyle(wheelColor.id);

  // we create a line style to draw the outline and some details
  var wheelStencil = new $.oStencil("line", "pencil", {minThickness: 5, maxThickness: 5})
  var wheelLine = new $.oLineStyle(wheelLineColor.id, wheelStencil);

  // create the node, link it and create a drawing spanning the entire scene
  var wheelNode = scene.root.addDrawingNode("car_wheel");
  wheelNode.use_drawing_pivot = "Apply Embeded Pivot On Parent Peg";
  wheelNode.can_animate = false;
  wheelNode.linkOutNode(sceneComposite);

  var wheelDrawing = wheelNode.element.addDrawing(1, "WHE_1");
  wheelNode.timingColumn.extendExposures();

  // draw a wheel onto the drawing, with the line on line art and color on color art
  scene.activeDrawing = wheelDrawing;
  wheelDrawing.lineArt.drawCircle(new $.oPoint(0,0), 80, wheelLine);
  var innerCircle = wheelDrawing.lineArt.drawCircle(new $.oPoint(0,0), 45, wheelLine, null);
  var fullCircle = wheelDrawing.colorArt.drawCircle(new $.oPoint(0,0), 80, null, wheelFill);

  // add a graphical detail onto the wheel so we can see the rotation.
  // We'll base it on existing points on the drawing.
  var wheelDetailPath = [];
  var wheelCenter = fullCircle.bounds.center;

  // we get the points from the stroke of the circle.
  // This only includes points that are on the curve, and excludes bezier handles.
  var points = innerCircle.strokes[0].points;

  for (var i in points){
    var point = points[i];
    wheelDetailPath.push({x:point.x, y:point.y, onCurve:true});
    // we add a bezier handle at the center after each point except the last one (which is a repeat of the first)
    if (i != points.length) {
      wheelDetailPath.push({x:wheelCenter.x, y:wheelCenter.y, onCurve:false});
    }
  }

  wheelDrawing.lineArt.drawStroke(wheelDetailPath, wheelLine);

  // create a peg to move the wheel at the back of the car
  var wheelPeg = scene.root.addNode("PEG", "car_wheel-P");
  wheelPeg.linkOutNode(wheelNode);
  wheelPeg.centerAbove(wheelNode);

  wheelPeg.position.x = -1.2;
  wheelPeg.position.y = -2;
  wheelPeg.attributes.rotation.anglez.addColumn();

  // clone the back wheel and pegs, rename and link them
  var frontWheelNode = wheelNode.clone();
  var frontWheelPeg = wheelPeg.clone();
  frontWheelNode.name = "car_wheel2";
  frontWheelPeg.name = "car_wheel2-P";
  frontWheelNode.linkInNode(frontWheelPeg);
  frontWheelPeg.position.x = 1.2;

  // start rigging the car, by adding a master peg and linking the various elements:
  var masterPeg = scene.root.addNode("PEG", "car-MASTER-P");
  masterPeg.linkOutNode(frontWheelPeg);
  masterPeg.linkOutNode(wheelPeg);
  masterPeg.linkOutNode(carBodyNode);

  // make a group with all our nodes, with a composite inside
  var carRigNodes = [masterPeg, carBodyNode, frontWheelPeg, frontWheelNode, wheelPeg, wheelNode];
  var carGroup = scene.root.addGroup("car-MASTER", true, false, carRigNodes);
  carGroup.linkOutNode(sceneComposite);

  // we order the nodes inside the group to increase visibility
  carGroup.orderNodeView();

  // add the composite from the group to the list of nodes
  carRigNodes.push(carGroup.multiportOut.linkedInNodes[0]);

  // we'll also create a backdrop around all the nodes inside
  carGroup.addBackdropToNodes(carRigNodes, "CAR", "", "005500");

  // we link the car palette as element palette to all our read nodes
  carNodes = carGroup.getNodesByType("READ");
  for (var i in carNodes){
    carNodes[i].linkPalette(carPalette);
  }

  // we create a little animation on the master peg, with rotation of the wheels
  var posxColumn = masterPeg.attributes.position.x.addColumn() // adding a column to the attribute allows to create keys when setting values;
  masterPeg.attributes.position.x.setValue(-10, 1);
  masterPeg.attributes.position.x.setValue(10, scene.length);

  posxColumn.keyframes[0].tween = true; // activate interpolation between the keys

  // animate the wheels turning. Since the wheels are cloned, their share the animation.
  // This time we'll set the values another way that is also supported:
  wheelPeg.rotation.anglez = {frameNumber:1, value:0};
  wheelPeg.rotation.anglez = {frameNumber:scene.length, value:50000};
  wheelPeg.attributes.rotation.anglez.column.keyframes[0].tween = true;

  // now we have a rig that we like, we'll export it as a tpl.
  // first we ask the user where to save it, starting the dialog on the user Desktop
  var exportLocation = $.browseForFolder("Select tpl save location.", System.getenv("userprofile")+"/Destkop/")
  if (!exportLocation) return; // if the user cancelled the dialog, we don't export.

  exportLocation += "/" + carGroup.name + ".tpl"
  scene.exportTemplate([carGroup], exportLocation, "usedOnly") // "usedOnly" tells the export we only want the palettes used by the template to be included."

  $.alert("Export finished!")

  $.endUndo();
}