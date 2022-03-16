# Harmony Integration

## Setup

The easiest way to setup for using Toon Boom Harmony is to use the built-in launch:

```
python -c "import openpype.hosts.harmony.api as harmony;harmony.launch("path/to/harmony/executable")"
```

Communication with Harmony happens with a server/client relationship where the server is in the Python process and the client is in the Harmony process. Messages between Python and Harmony are required to be dictionaries, which are serialized to strings:
```
+------------+
|            |
|   Python   |
|   Process  |
|            |
| +--------+ |
| |        | |
| |  Main  | |
| | Thread | |
| |        | |
| +----^---+ |
|     ||     |
|     ||     |
| +---v----+ |     +---------+
| |        | |     |         |
| | Server +-------> Harmony |
| | Thread <-------+ Process |
| |        | |     |         |
| +--------+ |     +---------+
+------------+
```

Server/client now uses stricter protocol to handle communication. This is necessary because of precise control over data passed between server/client. Each message is prepended with 6 bytes:
```
| A | H | 0x00 | 0x00 | 0x00 | 0x00 | ...

```
First two bytes are *magic* bytes stands for **A**valon **H**armony. Next four bytes hold length of the message `...` encoded as 32bit unsigned integer. This way we know how many bytes to read from the socket and if we need more or we need to parse multiple messages.


## Usage

The integration creates an `Openpype` menu entry where all related tools are located.

**NOTE: Menu creation can be temperamental. The best way is to launch Harmony and do nothing else until Harmony is fully launched.**

### Work files

Because Harmony projects are directories, this integration uses `.zip` as work file extension. Internally the project directories are stored under `[User]/.avalon/harmony`. Whenever the user saves the `.xstage` file, the integration zips up the project directory and moves it to the Avalon project path. Zipping and moving happens in the background.

### Show Workfiles on launch

You can show the Workfiles app when Harmony launches by setting environment variable `AVALON_HARMONY_WORKFILES_ON_LAUNCH=1`.

## Developing

### Low level messaging
To send from Python to Harmony you can use the exposed method:
```python
import openpype.hosts.harmony.api as harmony
from uuid import uuid4


func = """function %s_hello(person)
{
  return ("Hello " + person + "!");
}
%s_hello
""" % (uuid4(), uuid4())
print(harmony.send({"function": func, "args": ["Python"]})["result"])
```
**NOTE:** Its important to declare the function at the end of the function string. You can have multiple functions within your function string, but the function declared at the end is what gets executed.

To send a function with multiple arguments its best to declare the arguments within the function:
```python
import openpype.hosts.harmony.api as harmony
from uuid import uuid4

signature = str(uuid4()).replace("-", "_")
func = """function %s_hello(args)
{
  var greeting = args[0];
  var person = args[1];
  return (greeting + " " + person + "!");
}
%s_hello
""" % (signature, signature)
print(harmony.send({"function": func, "args": ["Hello", "Python"]})["result"])
```

### Caution

When naming your functions be aware that they are executed in global scope. They can potentially clash with Harmony own function and object names.
For example `func` is already existing Harmony object. When you call your function `func` it will overwrite in global scope the one from Harmony, causing
erratic behavior of Harmony. Openpype is prefixing those function names with [UUID4](https://docs.python.org/3/library/uuid.html) making chance of such clash minimal.
See above examples how that works. This will result in function named `38dfcef0_a6d7_4064_8069_51fe99ab276e_hello()`.
You can find list of Harmony object and function in Harmony documentation.

### Higher level (recommended)

Instead of sending functions directly to Harmony, it is more efficient and safe to just add your code to `js/PypeHarmony.js` or utilize `{"script": "..."}` method.

#### Extending PypeHarmony.js

Add your function to `PypeHarmony.js`. For example:

```javascript
PypeHarmony.myAwesomeFunction = function() {
  someCoolStuff();
};
```
Then you can call that javascript code from your Python like:

```Python
import openpype.hosts.harmony.api as harmony

harmony.send({"function": "PypeHarmony.myAwesomeFunction"});

```

#### Using Script method

You can also pass whole scripts into harmony and call their functions later as needed.

For example, you have bunch of javascript files:

```javascript
/* Master.js */

var Master = {
  Foo = {};
  Boo = {};
};

/* FileA.js */
var Foo = function() {};

Foo.prototype.A = function() {
  someAStuff();
}

// This will construct object Foo and add it to Master namespace.
Master.Foo = new Foo();

/* FileB.js */
var Boo = function() {};

Boo.prototype.B = function() {
  someBStuff();
}

// This will construct object Boo and add it to Master namespace.
Master.Boo = new Boo();
```

Now in python, just read all those files and send them to Harmony.

```python
from pathlib import Path
import openpype.hosts.harmony.api as harmony

path_to_js = Path('/path/to/my/js')
script_to_send = ""

for file in path_to_js.iterdir():
  if file.suffix == ".js":
    script_to_send += file.read_text()

harmony.send({"script": script_to_send})

# and use your code in Harmony
harmony.send({"function": "Master.Boo.B"})

```

### Scene Save
Instead of sending a request to Harmony with `scene.saveAll` please use:
```python
import openpype.hosts.harmony.api as harmony
harmony.save_scene()
```

<details>
  <summary>Click to expand for details on scene save.</summary>

  Because Openpype tools does not deal well with folders for a single entity like a Harmony scene, this integration has implemented to use zip files to encapsulate the Harmony scene folders. Saving scene in Harmony via menu or CTRL+S will not result in producing zip file, only saving it from Workfiles will. This is because
  zipping process can take some time in which we cannot block user from saving again. If xstage file is changed during zipping process it will produce corrupted zip
  archive.
</details>

### Plugin Examples
These plugins were made with the [polly config](https://github.com/mindbender-studio/config).

#### Creator Plugin
```python
import openpype.hosts.harmony.api as harmony
from uuid import uuid4


class CreateComposite(harmony.Creator):
    """Composite node for publish."""

    name = "compositeDefault"
    label = "Composite"
    family = "mindbender.template"

    def __init__(self, *args, **kwargs):
        super(CreateComposite, self).__init__(*args, **kwargs)
```

The creator plugin can be configured to use other node types. For example here is a write node creator:
```python
import openpype.hosts.harmony.api as harmony


class CreateRender(harmony.Creator):
    """Composite node for publishing renders."""

    name = "writeDefault"
    label = "Write"
    family = "mindbender.imagesequence"
    node_type = "WRITE"

    def __init__(self, *args, **kwargs):
        super(CreateRender, self).__init__(*args, **kwargs)

    def setup_node(self, node):
        signature = str(uuid4()).replace("-", "_")
        func = """function %s_func(args)
        {
            node.setTextAttr(args[0], "DRAWING_TYPE", 1, "PNG4");
        }
        %s_func
        """ % (signature, signature)
        harmony.send(
            {"function": func, "args": [node]}
        )
```

#### Collector Plugin
```python
import pyblish.api
import openpype.hosts.harmony.api as harmony


class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances by nodes metadata.

    This collector takes into account assets that are associated with
    a composite node and marked with a unique identifier;

    Identifier:
        id (str): "pyblish.avalon.instance"
    """

    label = "Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["harmony"]

    def process(self, context):
        nodes = harmony.send(
            {"function": "node.getNodes", "args": [["COMPOSITE"]]}
        )["result"]

        for node in nodes:
            data = harmony.read(node)

            # Skip non-tagged nodes.
            if not data:
                continue

            # Skip containers.
            if "container" in data["id"]:
                continue

            instance = context.create_instance(node.split("/")[-1])
            instance.append(node)
            instance.data.update(data)

            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.data["name"])
```

#### Extractor Plugin
```python
import os

import pyblish.api
import openpype.hosts.harmony.api as harmony

import clique


class ExtractImage(pyblish.api.InstancePlugin):
    """Produce a flattened image file from instance.
    This plug-in only takes into account the nodes connected to the composite.
    """
    label = "Extract Image Sequence"
    order = pyblish.api.ExtractorOrder
    hosts = ["harmony"]
    families = ["mindbender.imagesequence"]

    def process(self, instance):
        project_path = harmony.send(
            {"function": "scene.currentProjectPath"}
        )["result"]

        # Store reference for integration
        if "files" not in instance.data:
            instance.data["files"] = list()

        # Store display source node for later.
        display_node = "Top/Display"
        signature = str(uuid4()).replace("-", "_")
        func = """function %s_func(display_node)
        {
            var source_node = null;
            if (node.isLinked(display_node, 0))
            {
                source_node = node.srcNode(display_node, 0);
                node.unlink(display_node, 0);
            }
            return source_node
        }
        %s_func
        """ % (signature, signature)
        display_source_node = harmony.send(
            {"function": func, "args": [display_node]}
        )["result"]

        # Perform extraction
        path = os.path.join(
            os.path.normpath(
                project_path
            ).replace("\\", "/"),
            instance.data["name"]
        )
        if not os.path.exists(path):
            os.makedirs(path)

        render_func = """function frameReady(frame, celImage)
        {{
          var path = "{path}/{filename}" + frame + ".png";
          celImage.imageFileAs(path, "", "PNG4");
        }}
        function %s_func(composite_node)
        {{
            node.link(composite_node, 0, "{display_node}", 0);
            render.frameReady.connect(frameReady);
            render.setRenderDisplay("{display_node}");
            render.renderSceneAll();
            render.frameReady.disconnect(frameReady);
        }}
        %s_func
        """ % (signature, signature)
        restore_func = """function %s_func(args)
        {
            var display_node = args[0];
            var display_source_node = args[1];
            if (node.isLinked(display_node, 0))
            {
                node.unlink(display_node, 0);
            }
            node.link(display_source_node, 0, display_node, 0);
        }
        %s_func
        """ % (signature, signature)

        with harmony.maintained_selection():
            self.log.info("Extracting %s" % str(list(instance)))

            harmony.send(
                {
                    "function": render_func.format(
                        path=path.replace("\\", "/"),
                        filename=os.path.basename(path),
                        display_node=display_node
                    ),
                    "args": [instance[0]]
                }
            )

            # Restore display.
            if display_source_node:
                harmony.send(
                    {
                        "function": restore_func,
                        "args": [display_node, display_source_node]
                    }
                )

        files = os.listdir(path)
        collections, remainder = clique.assemble(files, minimum_items=1)
        assert not remainder, (
            "There shouldn't have been a remainder for '%s': "
            "%s" % (instance[0], remainder)
        )
        assert len(collections) == 1, (
            "There should only be one image sequence in {}. Found: {}".format(
                path, len(collections)
            )
        )

        data = {
            "subset": collections[0].head,
            "isSeries": True,
            "stagingDir": path,
            "files": list(collections[0]),
        }
        instance.data.update(data)

        self.log.info("Extracted {instance} to {path}".format(**locals()))
```

#### Loader Plugin
```python
import os

from avalon import api, io
import openpype.hosts.harmony.api as harmony

signature = str(uuid4()).replace("-", "_")
copy_files = """function copyFile(srcFilename, dstFilename)
{
    var srcFile = new PermanentFile(srcFilename);
    var dstFile = new PermanentFile(dstFilename);
    srcFile.copy(dstFile);
}
"""

import_files = """function %s_import_files()
{
  var PNGTransparencyMode = 0;  // Premultiplied wih Black
  var TGATransparencyMode = 0;  // Premultiplied wih Black
  var SGITransparencyMode = 0;  // Premultiplied wih Black
  var LayeredPSDTransparencyMode = 1;  // Straight
  var FlatPSDTransparencyMode = 2;  // Premultiplied wih White

  function getUniqueColumnName( column_prefix )
  {
      var suffix = 0;
      // finds if unique name for a column
      var column_name = column_prefix;
      while(suffix < 2000)
      {
          if(!column.type(column_name))
          break;

          suffix = suffix + 1;
          column_name = column_prefix + "_" + suffix;
      }
      return column_name;
  }

  function import_files(args)
  {
      var root = args[0];
      var files = args[1];
      var name = args[2];
      var start_frame = args[3];

      var vectorFormat = null;
      var extension = null;
      var filename = files[0];

      var pos = filename.lastIndexOf(".");
      if( pos < 0 )
          return null;

      extension = filename.substr(pos+1).toLowerCase();

      if(extension == "jpeg")
          extension = "jpg";
      if(extension == "tvg")
      {
          vectorFormat = "TVG"
          extension ="SCAN"; // element.add() will use this.
      }

      var elemId = element.add(
          name,
          "BW",
          scene.numberOfUnitsZ(),
          extension.toUpperCase(),
          vectorFormat
      );
      if (elemId == -1)
      {
          // hum, unknown file type most likely -- let's skip it.
          return null; // no read to add.
      }

      var uniqueColumnName = getUniqueColumnName(name);
      column.add(uniqueColumnName , "DRAWING");
      column.setElementIdOfDrawing(uniqueColumnName, elemId);

      var read = node.add(root, name, "READ", 0, 0, 0);
      var transparencyAttr = node.getAttr(
          read, frame.current(), "READ_TRANSPARENCY"
      );
      var opacityAttr = node.getAttr(read, frame.current(), "OPACITY");
      transparencyAttr.setValue(true);
      opacityAttr.setValue(true);

      var alignmentAttr = node.getAttr(read, frame.current(), "ALIGNMENT_RULE");
      alignmentAttr.setValue("ASIS");

      var transparencyModeAttr = node.getAttr(
          read, frame.current(), "applyMatteToColor"
      );
      if (extension == "png")
          transparencyModeAttr.setValue(PNGTransparencyMode);
      if (extension == "tga")
          transparencyModeAttr.setValue(TGATransparencyMode);
      if (extension == "sgi")
          transparencyModeAttr.setValue(SGITransparencyMode);
      if (extension == "psd")
          transparencyModeAttr.setValue(FlatPSDTransparencyMode);

      node.linkAttr(read, "DRAWING.ELEMENT", uniqueColumnName);

      // Create a drawing for each file.
      for( var i =0; i <= files.length - 1; ++i)
      {
          timing = start_frame + i
          // Create a drawing drawing, 'true' indicate that the file exists.
          Drawing.create(elemId, timing, true);
          // Get the actual path, in tmp folder.
          var drawingFilePath = Drawing.filename(elemId, timing.toString());
          copyFile( files[i], drawingFilePath );

          column.setEntry(uniqueColumnName, 1, timing, timing.toString());
      }
      return read;
  }
  import_files();
}
%s_import_files
""" % (signature, signature)

replace_files = """function %s_replace_files(args)
{
    var files = args[0];
    var _node = args[1];
    var start_frame = args[2];

    var _column = node.linkedColumn(_node, "DRAWING.ELEMENT");

    // Delete existing drawings.
    var timings = column.getDrawingTimings(_column);
    for( var i =0; i <= timings.length - 1; ++i)
    {
        column.deleteDrawingAt(_column, parseInt(timings[i]));
    }

    // Create new drawings.
    for( var i =0; i <= files.length - 1; ++i)
    {
        timing = start_frame + i
        // Create a drawing drawing, 'true' indicate that the file exists.
        Drawing.create(node.getElementId(_node), timing, true);
        // Get the actual path, in tmp folder.
        var drawingFilePath = Drawing.filename(
            node.getElementId(_node), timing.toString()
        );
        copyFile( files[i], drawingFilePath );

        column.setEntry(_column, 1, timing, timing.toString());
    }
}
%s_replace_files
""" % (signature, signature)


class ImageSequenceLoader(load.LoaderPlugin):
    """Load images
    Stores the imported asset in a container named after the asset.
    """
    families = ["mindbender.imagesequence"]
    representations = ["*"]

    def load(self, context, name=None, namespace=None, data=None):
        files = []
        for f in context["version"]["data"]["files"]:
            files.append(
                os.path.join(
                    context["version"]["data"]["stagingDir"], f
                ).replace("\\", "/")
            )

        read_node = harmony.send(
            {
                "function": copy_files + import_files,
                "args": ["Top", files, context["version"]["data"]["subset"], 1]
            }
        )["result"]

        self[:] = [read_node]

        return harmony.containerise(
            name,
            namespace,
            read_node,
            context,
            self.__class__.__name__
        )

    def update(self, container, representation):
        node = container.pop("node")

        version = io.find_one({"_id": representation["parent"]})
        files = []
        for f in version["data"]["files"]:
            files.append(
                os.path.join(
                    version["data"]["stagingDir"], f
                ).replace("\\", "/")
            )

        harmony.send(
            {
                "function": copy_files + replace_files,
                "args": [files, node, 1]
            }
        )

        harmony.imprint(
            node, {"representation": str(representation["_id"])}
        )

    def remove(self, container):
        node = container.pop("node")
        signature = str(uuid4()).replace("-", "_")
        func = """function %s_deleteNode(_node)
        {
            node.deleteNode(_node, true, true);
        }
        %_deleteNode
        """ % (signature, signature)
        harmony.send(
            {"function": func, "args": [node]}
        )

    def switch(self, container, representation):
        self.update(container, representation)
```

## Resources
- https://github.com/diegogarciahuerta/tk-harmony
- https://github.com/cfourney/OpenHarmony
- [Toon Boom Discord](https://discord.gg/syAjy4H)
- [Toon Boom TD](https://discord.gg/yAjyQtZ)
