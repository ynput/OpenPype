# OpenHarmony - The Toonboom Harmony Open Source DOM Library

## Why did we make this library ?

Ever tried to make a simple script for toonboom Harmony, then got stumped by the numerous amount of steps required to execute the simplest action? Or bored of coding the same helper routines again and again for every studio you work for?

Toonboom Harmony is a very powerful software, with hundreds of functions and tools, and it unlocks a great amount of possibilities for animation studios around the globe. And... being the produce of the hard work of a small team forced to prioritise, it can also be a bit rustic at times!

We are users at heart, animators and riggers, who just want to interact with the software as simply as possible. Simplicity is at the heart of the design of openHarmony. But we also are developpers, and we made the library for people like us who can't resist tweaking the software and bend it in all possible ways, and are looking for powerful functions to help them do it.

This library's aim is to create a more direct way to interact with Toonboom through scripts, by providing a more intuitive way to access its elements, and help with the cumbersome and repetitive tasks as well as help unlock untapped potential in its many available systems. So we can go from having to do things like this:

```javascript
  // adding a Drawing to the scene with the official API
  var myNodeName = "Drawing";
  var myColumnName = myNodeName;
  var myNode = node.add("Top", myNodeName, "READ",0,0,0);
  var myColumn = column.add(myColumnName, "DRAWING", "BOTTOM");
  var myElement = element.add (myNodeName, "COLOR", 12, "SCAN", "TVG");
  column.setElementIdOfDrawing(myColumnName, myElement);
  node.linkAttr (myNode, "DRAWING.ELEMENT", myColumnName);
  drawing.create (myElement, "1", false, false);
  column.setEntry (myColumnName, 0, 1, "1");
```

to simply writing :

```javascript
  // with openHarmony
  var myNode = $.scene.root.addDrawingNode("Drawing");
  myNode.element.addDrawing(1);
```

Less time spent coding, more time spent having ideas!

-----
## Do I need any knowledge of toonboom scripting to use openHarmony?

OpenHarmony aims to be self contained and to reimplement all the basic functions of the Harmony API. So, while it might help to have prior experience to understand what goes on under the hood, knowledge of the official API is not required.

However, should you reach the limits of what openHarmony can offer at this time, you can always access the official API at any moment. Maybe you can submit a request and the missing parts will be added eventually, or you can even delve into the code and add the necessary functions yourself if you feel like it!

You can access a list of all the functions, how to use them, as well as examples, from the online documentation:

[https://cfourney.github.io/OpenHarmony/$.html](https://cfourney.github.io/OpenHarmony/$.html)

To help you get started, here is a full example using the library to make and animate a small car, covering most of the basic features.

[https://github.com/cfourney/OpenHarmony/blob/master/examples/openHarmonyExample.js](https://github.com/cfourney/OpenHarmony/blob/master/examples/openHarmonyExample.js)

-----
## The OpenHarmony Document Object Model or DOM

OpenHarmony is based around the four principles of Object Oriented Programming: *Abstraction*, *Encapsulation*, *Inheritance*, *Polymorphism*.

This means every element of the Harmony scene has a corresponding abstraction existing in the code as a class. We have oNode, oScene, oColumn, etc. Unlike in the official API, each class is designed to create objects that are instances of these classes and encapsulate them and all their actions. It means no more storing the path of nodes, column abstract names and element ids to interact with them; if you can create or call it, you can access all of its functionalities. Nodes are declined as DrawingNodes and PegNodes, which inherint from the Node Class, and so on.

The openHarmony library doesn't merely provide *access* to the elements of a Toonboom Harmony file, it *models* them and their relationship to each others.

<img src="https://raw.githubusercontent.com/cfourney/OpenHarmony/master/oH_DOM.jpg" alt="The Document ObjectModel" width="1600">

The *Document Object Model* is a way to organise the elements of the Toonboom scene by highlighting the way they interact with each other. The Scene object has a root group, which contains Nodes, which have Attributes which can be linked to Columns which contain Frames, etc. This way it's always easy to find and access the content you are looking for. The attribute system has also been streamlined and you can now set values of node properties with a simple attribution synthax.

We implemented a global access to all elements and functions through the standard **dot notation** for the hierarchy, for ease of use, and clarity of code.

Functions and methods also make extensive use of **optional parameters** so no more need to fill in all arguments when calling functions when the default behavior is all that's needed.

On the other hand, the "o" naming scheme allows us to retain full access to the official API at all times. This means you can use it only when it really makes your life better.

-----
## Adopting openHarmony for your project

This library is made available under the [Mozilla Public license 2.0](https://www.mozilla.org/en-US/MPL/2.0/).

OpenHarmony can be downloaded from [this repository](https://github.com/cfourney/OpenHarmony/releases/) directly. In order to make use of its functions, it needs to be unzipped next to the scripts you will be writing.

All you have to do is call :
```javascript
include("openHarmony.js");
```
at the beggining of your script.

You can ask your users to download their copy of the library and store it alongside, or bundle it as you wish as long as you include the license file provided on this repository.

The entire library is documented at the address :

https://cfourney.github.io/OpenHarmony/$.html

This include a list of all the available functions as well as examples and references (such as the list of all available node attributes).

As time goes by, more functions will be added and the documentation will also get richer as more examples get created.

-----
## Installation

#### simple install:
- download the zip from [the releases page](https://github.com/cfourney/OpenHarmony/releases/),
- unzip the contents to [your scripts folder](https://docs.toonboom.com/help/harmony-17/advanced/scripting/import-script.html).

#### advanced install (for developers):
- clone the repository to the location of your choice

 -- or --

- download the zip from [the releases page](https://github.com/cfourney/OpenHarmony/releases/)
- unzip the contents where you want to store the library,

 -- then --

- run `install.bat`.

This last step will tell Harmony where to look to load the library, by setting the environment variable `LIB_OPENHARMONY_PATH` to the current folder.

It will then create a `openHarmony.js` file into the user scripts folder which calls the files from the folder from the `LIB_OPENHARMONY_PATH` variable, so that scripts can make direct use of it without having to worry about where openHarmony is stored.

##### Troubleshooting:
- to test if the library is correctly installed, open the `Script Editor` window and type:
```javascript
include ("openHarmony.js");
$.alert("hello world");
```
Run the script, and if there is an error (for ex `MAX_REENTRENCY `), check that the file `openHarmony.js` exists in the script folder, and contains only the line:
```javascript
include(System.getenv('LIB_OPENHARMONY_PATH')+'openHarmony.js');
```
Check that the environment variable `LIB_OPENHARMONY_PATH` is set correctly to the remote folder.

-----
## How to add openHarmony to vscode intellisense for autocompletion

Although not fully supported, you can get most of the autocompletion features to work by adding the following lines to a `jsconfig.json` file placed at the root of your working folder.
The paths need to be relative which means the openHarmony source code must be placed directly in your developping environnement.

For example, if your working folder contains the openHarmony source in a folder called `OpenHarmony` and your working scripts in a folder called `myScripts`, place the `jsconfig.json` file at the root of the folder and add these lines to the file:

```javascript
{
  include : [
    "OpenHarmony/*",
    "OpenHarmony/openHarmony/*",
    "myScripts/*",
    "*"
  ]
}
```

[More information on vs code and jsconfig.json.](https://code.visualstudio.com/docs/nodejs/working-with-javascript)

-----
## Let's get technical. I can code, and want to contribute, where do I start?

Reading and understanding the existing code, or at least the structure of the lib, is a great start, but not a requirement. You can simply start adding your classes to the $ object that is the root of the harmony lib, and start implementing. However, try to follow these guidelines as they are the underlying principles that make the library consistent:

  * There is a $ global object, which contains all the class declarations, and can be passed from one context to another to access the functions.

  * Each class is an abstract representation of a core concept of Harmony, so naming and consistency (within the lib) is essential. But we are not bound by the structure or naming of Harmony if we find a better way, for example to make nomenclatures more consistent between the scripting interface and the UI.

  * Each class defines a bunch of class properties with getter/setters for the values that are directly related to an entity of the scene. If you're thinking of making a getter function that doesn't require arguments, use a getter setter instead!

  * Each class also defines methods which can be called on the class instances to affect its contents, or its children's contents. For example, you'd go to the scene class to add the things that live in the scene, such as elements, columns and palettes. You wouldn't go to the column class or palette class to add one, because then what are you adding it *to*?

  * We use encapsulation over having to pass a function arguments every time we can. Instead of adding a node to the scene, and having to pass a group as argument, adding a node is done directly by calling a method of the parent group. This way the parent/child relationship is always clear and the arguments list kept to a minimum.

  * The goal is to make the most useful set of functions we can. Instead of making a large function that does a lot, consider extracting the small useful subroutines you need in your function into the existing classes directly.

  * Each method argument besides the core one (for example, for adding nodes, we have to specify the type of the new node we create) must have a default fallback to make the argument optional.

  * Don't use globals ever, but maybe use a class property if you need an enum for example.

  * Don't use the official API namespace, any function that exists in the official API must remain accessible otherwise things will break. Prefix your class names with "o" to avoid this and to signify this function is part of openHarmony.

  * We use the official API as little as we can in the code, so that if the implementation changes, we can easily fix it in a minimal amount of places. Wrap it, then use the wrapper. (ex: oScene.name)

  * Users of the lib should almost never have to use "new" to create instances of their classes. Create accessors/factories that will do that for them. For example, $.scn creates and return a oScene instance, and $.scn.nodes returns new oNodes instances, but users don't have to create them themselves, so it's like they were always there, contained within. It also lets you create different subclasses for one factory. For example, $.scn.$node("Top/myNode") will either return a oNode, oDrawingNode, oPegNode or oGroupNode object depending on the node type of the node represented by the object.
  Exceptions are small useful value containing objects that don't belong to the Harmony hierarchy like oPoint, oBox, oColorValue, etc.

  * It's a JS Library, so use camelCase naming and try to follow the google style guide for JS :
  https://google.github.io/styleguide/jsguide.html

  * Document your new functions using the JSDocs synthax : https://devdocs.io/jsdoc/howto-es2015-classes

  * Make a branch, create a merge request when you're done, and we'll add the new stuff you added to the lib :)


-----
## Credits

This library was created by Mathieu Chaptel and Chris Fourney.

If you're using openHarmony, and are noticing things that you would like to see in the library, please feel free to contribute to the code directly, or send us feedback through Github. This project will only be as good as people working together can make it, and we need every piece of code and feedback we can get, and would love to hear from you!

-----
## Community

Join the discord community for help with the library and to contribute:
https://discord.gg/kgT38MG

-----
## Acknowledgements
  * [Yu Ueda](https://github.com/yueda1984) for his help to understand Harmony coordinate systems
  * [Dash](https://github.com/35743) for his help to debug, test and develop the Pie Menus widgets
  * [All the contributors](https://github.com/cfourney/OpenHarmony/graphs/contributors) for their precious help.