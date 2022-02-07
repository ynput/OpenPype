/*
         _ ______  __   _
        | / ___\ \/ /  (_)___
     _  | \___ \\  /   | / __|
    | |_| |___) /  \ _ | \__ \
     \___/|____/_/\_(_)/ |___/
                     |__/
                        _               ____
    /\   /\___ _ __ ___(_) ___  _ __   |___ \
    \ \ / / _ \ '__/ __| |/ _ \| '_ \    __) |
     \ V /  __/ |  \__ \ | (_) | | | |  / __/
      \_/ \___|_|  |___/_|\___/|_| |_| |_____|
*/


//////////////////////////////////////////////////////////////////////////////////
// JSX.js © and writtent by Trevor https://creative-scripts.com/jsx-js           //
// If you turn over is less the $50,000,000 then you don't have to pay anything //
// License MIT, don't complain, don't sue NO MATTER WHAT                        //
// If you turn over is more the $50,000,000 then you DO have to pay             //
// Contact me https://creative-scripts.com/contact for pricing and licensing     //
// Don't remove these commented lines                                           //
// For simple and effective calling of jsx from the js engine                   //
// Version 2 last modified April 18 2018                                        //
//////////////////////////////////////////////////////////////////////////////////

///////////////////////////////////////////////////////////////////////////////////////////////////////////
// Change log:                                                                                           //
// JSX.js V2 is now independent of NodeJS and CSInterface.js <span class="wp-font-emots-emo-happy"></span>                                         //
// forceEval is now by default true                                                                      //
// It wraps the scripts in a try catch and an eval providing useful error handling                       //
// One can set in the jsx engine $.includeStack = true to return the call stack in the event of an error //
///////////////////////////////////////////////////////////////////////////////////////////////////////////

///////////////////////////////////////////////////////////////////////////////////////////////////////////
// JSX.js for calling jsx code from the js engine                                                        //
// 2 methods included                                                                                    //
// 1) jsx.evalScript AKA jsx.eval                                                                        //
// 2) jsx.evalFile AKA jsx.file                                                                          //
// Special features                                                                                      //
// 1) Allows all changes in your jsx code to be reloaded into your extension at the click of a button    //
// 2) Can enable the $.fileName property to work and provides a $.__fileName() method as an alternative  //
// 3) Can force a callBack result from InDesign                                                          //
// 4) No more csInterface.evalScript('alert("hello "' + title + " " + name + '");')                      //
//    use jsx.evalScript('alert("hello __title__ __name__");', {title: title, name: name});              //
// 5) execute jsx files from your jsx folder like this jsx.evalFile('myFabJsxScript.jsx');               //
//    or from a relative path jsx.evalFile('../myFabScripts/myFabJsxScript.jsx');                        //
//    or from an absolute url jsx.evalFile('/Path/to/my/FabJsxScript.jsx'); (mac)                        //
//    or from an absolute url jsx.evalFile('C:Path/to/my/FabJsxScript.jsx'); (windows)                   //
// 6) Parameter can be entered in the from of a parameter list which can be in any order or as an object //
// 7) Not camelCase sensitive (very useful for the illiterate)                                           //
// <span class="wp-font-emots-emo-sunglasses"></span> Dead easy to use BUT SPEND THE 3 TO 5 MINUTES IT SHOULD TAKE TO READ THE INSTRUCTIONS              //
///////////////////////////////////////////////////////////////////////////////////////////////////////////

/* jshint undef:true, unused:true, esversion:6 */

//////////////////////////////////////
// jsx is the interface for the API //
//////////////////////////////////////

var jsx;

// Wrap everything in an anonymous function to prevent leeks
(function() {
    /////////////////////////////////////////////////////////////////////
    // Substitute some CSInterface functions to avoid dependency on it //
    /////////////////////////////////////////////////////////////////////

    var __dirname = (function() {
        var path, isMac;
        path = decodeURI(window.__adobe_cep__.getSystemPath('extension'));
        isMac = navigator.platform[0] === 'M'; // [M]ac
        path = path.replace('file://' + (isMac ? '' : '/'), '');
        return path;
    })();

    var evalScript = function(script, callback) {
        callback = callback || function() {};
        window.__adobe_cep__.evalScript(script, callback);
    };


    ////////////////////////////////////////////
    // In place of using the node path module //
    ////////////////////////////////////////////

    // jshint undef: true, unused: true

    // A very minified version of the NodeJs Path module!!
    // For use outside of NodeJs
    // Majorly nicked by Trevor from Joyent
    var path = (function() {

        var isString = function(arg) {
            return typeof arg === 'string';
        };

        // var isObject = function(arg) {
        //     return typeof arg === 'object' && arg !== null;
        // };

        var basename = function(path) {
            if (!isString(path)) {
                throw new TypeError('Argument to path.basename must be a string');
            }
            var bits = path.split(/[\/\\]/g);
            return bits[bits.length - 1];
        };

        // jshint undef: true
        // Regex to split a windows path into three parts: [*, device, slash,
        // tail] windows-only
        var splitDeviceRe =
            /^([a-zA-Z]:|[\\\/]{2}[^\\\/]+[\\\/]+[^\\\/]+)?([\\\/])?([\s\S]*?)$/;

        // Regex to split the tail part of the above into [*, dir, basename, ext]
        // var splitTailRe =
        //     /^([\s\S]*?)((?:\.{1,2}|[^\\\/]+?|)(\.[^.\/\\]*|))(?:[\\\/]*)$/;

        var win32 = {};
        // Function to split a filename into [root, dir, basename, ext]
        // var win32SplitPath = function(filename) {
        //     // Separate device+slash from tail
        //     var result = splitDeviceRe.exec(filename),
        //         device = (result[1] || '') + (result[2] || ''),
        //         tail = result[3] || '';
        //     // Split the tail into dir, basename and extension
        //     var result2 = splitTailRe.exec(tail),
        //         dir = result2[1],
        //         basename = result2[2],
        //         ext = result2[3];
        //     return [device, dir, basename, ext];
        // };

        var win32StatPath = function(path) {
            var result = splitDeviceRe.exec(path),
                device = result[1] || '',
                isUnc = !!device && device[1] !== ':';
            return {
                device: device,
                isUnc: isUnc,
                isAbsolute: isUnc || !!result[2], // UNC paths are always absolute
                tail: result[3]
            };
        };

        var normalizeUNCRoot = function(device) {
            return '\\\\' + device.replace(/^[\\\/]+/, '').replace(/[\\\/]+/g, '\\');
        };

        var normalizeArray = function(parts, allowAboveRoot) {
            var res = [];
            for (var i = 0; i < parts.length; i++) {
                var p = parts[i];

                // ignore empty parts
                if (!p || p === '.')
                    continue;

                if (p === '..') {
                    if (res.length && res[res.length - 1] !== '..') {
                        res.pop();
                    } else if (allowAboveRoot) {
                        res.push('..');
                    }
                } else {
                    res.push(p);
                }
            }

            return res;
        };

        win32.normalize = function(path) {
            var result = win32StatPath(path),
                device = result.device,
                isUnc = result.isUnc,
                isAbsolute = result.isAbsolute,
                tail = result.tail,
                trailingSlash = /[\\\/]$/.test(tail);

            // Normalize the tail path
            tail = normalizeArray(tail.split(/[\\\/]+/), !isAbsolute).join('\\');

            if (!tail && !isAbsolute) {
                tail = '.';
            }
            if (tail && trailingSlash) {
                tail += '\\';
            }

            // Convert slashes to backslashes when `device` points to an UNC root.
            // Also squash multiple slashes into a single one where appropriate.
            if (isUnc) {
                device = normalizeUNCRoot(device);
            }

            return device + (isAbsolute ? '\\' : '') + tail;
        };
        win32.join = function() {
            var paths = [];
            for (var i = 0; i < arguments.length; i++) {
                var arg = arguments[i];
                if (!isString(arg)) {
                    throw new TypeError('Arguments to path.join must be strings');
                }
                if (arg) {
                    paths.push(arg);
                }
            }

            var joined = paths.join('\\');

            // Make sure that the joined path doesn't start with two slashes, because
            // normalize() will mistake it for an UNC path then.
            //
            // This step is skipped when it is very clear that the user actually
            // intended to point at an UNC path. This is assumed when the first
            // non-empty string arguments starts with exactly two slashes followed by
            // at least one more non-slash character.
            //
            // Note that for normalize() to treat a path as an UNC path it needs to
            // have at least 2 components, so we don't filter for that here.
            // This means that the user can use join to construct UNC paths from
            // a server name and a share name; for example:
            //   path.join('//server', 'share') -> '\\\\server\\share\')
            if (!/^[\\\/]{2}[^\\\/]/.test(paths[0])) {
                joined = joined.replace(/^[\\\/]{2,}/, '\\');
            }
            return win32.normalize(joined);
        };

        var posix = {};

        // posix version
        posix.join = function() {
            var path = '';
            for (var i = 0; i < arguments.length; i++) {
                var segment = arguments[i];
                if (!isString(segment)) {
                    throw new TypeError('Arguments to path.join must be strings');
                }
                if (segment) {
                    if (!path) {
                        path += segment;
                    } else {
                        path += '/' + segment;
                    }
                }
            }
            return posix.normalize(path);
        };

        // path.normalize(path)
        // posix version
        posix.normalize = function(path) {
            var isAbsolute = path.charAt(0) === '/',
                trailingSlash = path && path[path.length - 1] === '/';

            // Normalize the path
            path = normalizeArray(path.split('/'), !isAbsolute).join('/');

            if (!path && !isAbsolute) {
                path = '.';
            }
            if (path && trailingSlash) {
                path += '/';
            }

            return (isAbsolute ? '/' : '') + path;
        };

        win32.basename = posix.basename = basename;

        this.win32 = win32;
        this.posix = posix;
        return (navigator.platform[0] === 'M') ? posix : win32;
    })();

    ////////////////////////////////////////////////////////////////////////////////////////////////////////
    // The is the  "main" function which is to be prototyped                                              //
    // It run a small snippet in the jsx engine that                                                      //
    // 1) Assigns $.__dirname with the value of the extensions __dirname base path                        //
    // 2) Sets up a method $.__fileName() for retrieving from within the jsx script it's $.fileName value //
    //    more on that method later                                                                       //
    // At the end of the script the global declaration jsx = new Jsx(); has been made.                    //
    // If you like you can remove that and include in your relevant functions                             //
    // var jsx = new Jsx(); You would never call the Jsx function without the "new" declaration           //
    ////////////////////////////////////////////////////////////////////////////////////////////////////////
    var Jsx = function() {
        var jsxScript;
        // Setup jsx function to enable the jsx scripts to easily retrieve their file location
        jsxScript = [
            '$.level = 0;',
            'if(!$.__fileNames){',
            '    $.__fileNames = {};',
            '    $.__dirname = "__dirname__";'.replace('__dirname__', __dirname),
            '    $.__fileName = function(name){',
            '        name = name || $.fileName;',
            '        return ($.__fileNames && $.__fileNames[name]) || $.fileName;',
            '    };',
            '}'
        ].join('');
        evalScript(jsxScript);
        return this;
    };

    /**
     * [evalScript] For calling jsx scripts from the js engine
     *
     *         The jsx.evalScript method is used for calling jsx scripts directly from the js engine
     *         Allows for easy replacement i.e. variable insertions and for forcing eval.
     *         For convenience jsx.eval or jsx.script or jsx.evalscript can be used instead of calling jsx.evalScript
     *
     * @param  {String} jsxScript
     *                            The string that makes up the jsx script
     *                            it can contain a simple template like syntax for replacements
     *                            'alert("__foo__");'
     *                            the __foo__ will be replaced as per the replacements parameter
     *
     * @param  {Function} callback
     *                            The callback function you want the jsx script to trigger on completion
     *                            The result of the jsx script is passed as the argument to that function
     *                            The function can exist in some other file.
     *                            Note that InDesign does not automatically pass the callBack as a string.
     *                            Either write your InDesign in a way that it returns a sting the form of
     *                            return 'this is my result surrounded by quotes'
     *                            or use the force eval option
     *                            [Optional DEFAULT no callBack]
     *
     * @param  {Object} replacements
     *                            The replacements to make on the jsx script
     *                            given the following script (template)
     *                            'alert("__message__: " + __val__);'
     *                            and we want to change the script to
     *                            'alert("I was born in the year: " + 1234);'
     *                            we would pass the following object
     *                            {"message": 'I was born in the year', "val": 1234}
     *                            or if not using reserved words like do we can leave out the key quotes
     *                            {message: 'I was born in the year', val: 1234}
     *                            [Optional DEFAULT no replacements]
     *
     * @param  {Bolean} forceEval
     *                             If the script should be wrapped in an eval and try catch
     *                             This will 1) provide useful error feedback if heaven forbid it is needed
     *                             2) The result will be a string which is required for callback results in InDesign
     *                             [Optional DEFAULT true]
     *
     * Note 1) The order of the parameters is irrelevant
     * Note 2) One can pass the arguments as an object if desired
     *         jsx.evalScript(myCallBackFunction, 'alert("__myMessage__");', true);
     *         is the same as
     *         jsx.evalScript({
     *             script: 'alert("__myMessage__");',
     *             replacements: {myMessage: 'Hi there'},
     *             callBack: myCallBackFunction,
     *             eval: true
     *         });
     *         note that either lower or camelCase key names are valid
     *         i.e. both callback or callBack will work
     *
     *      The following keys are the same jsx || script || jsxScript || jsxscript || file
     *      The following keys are the same callBack || callback
     *      The following keys are the same replacements || replace
     *      The following keys are the same eval || forceEval || forceeval
     *      The following keys are the same forceEvalScript || forceevalscript || evalScript || evalscript;
     *
     * @return {Boolean} if the jsxScript was executed or not
     */

    Jsx.prototype.evalScript = function() {
        var arg, i, key, replaceThis, withThis, args, callback, forceEval, replacements, jsxScript, isBin;

        //////////////////////////////////////////////////////////////////////////////////////
        // sort out order which arguments into jsxScript, callback, replacements, forceEval //
        //////////////////////////////////////////////////////////////////////////////////////

        args = arguments;

        // Detect if the parameters were passed as an object and if so allow for various keys
        if (args.length === 1 && (arg = args[0]) instanceof Object) {
            jsxScript = arg.jsxScript || arg.jsx || arg.script || arg.file || arg.jsxscript;
            callback = arg.callBack || arg.callback;
            replacements = arg.replacements || arg.replace;
            forceEval = arg.eval || arg.forceEval || arg.forceeval;
        } else {
            for (i = 0; i < 4; i++) {
                arg = args[i];
                if (arg === undefined) {
                    continue;
                }
                if (arg.constructor === String) {
                    jsxScript = arg;
                    continue;
                }
                if (arg.constructor === Object) {
                    replacements = arg;
                    continue;
                }
                if (arg.constructor === Function) {
                    callback = arg;
                    continue;
                }
                if (arg === false) {
                    forceEval = false;
                }
            }
        }

        // If no script provide then not too much to do!
        if (!jsxScript) {
            return false;
        }

        // Have changed the forceEval default to be true as I prefer the error handling
        if (forceEval !== false) {
            forceEval = true;
        }

        //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
        // On Illustrator and other apps the result of the jsx script is automatically passed as a string                                       //
        // if you have a "script" containing the single number 1 and nothing else then the callBack will register as "1"                        //
        // On InDesign that same script will provide a blank callBack                                                                           //
        // Let's say we have a callBack function var callBack = function(result){alert(result);}                                                //
        // On Ai your see the 1 in the alert                                                                                                    //
        // On ID your just see a blank alert                                                                                                    //
        // To see the 1 in the alert you need to convert the result to a string and then it will show                                           //
        // So if we rewrite out 1 byte script to '1' i.e. surround the 1 in quotes then the call back alert will show 1                         //
        // If the scripts planed one can make sure that the results always passed as a string (including errors)                                //
        // otherwise one can wrap the script in an eval and then have the result passed as a string                                             //
        // I have not gone through all the apps but can say                                                                                     //
        // for Ai you never need to set the forceEval to true                                                                                   //
        // for ID you if you have not coded your script appropriately and your want to send a result to the callBack then set forceEval to true //
        // I changed this that even on Illustrator it applies the try catch, Note the try catch will fail if $.level is set to 1                //
        //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

        if (forceEval) {

            isBin = (jsxScript.substring(0, 10) === '@JSXBIN@ES') ? '' : '\n';
            jsxScript = (
                // "\n''') + '';} catch(e){(function(e){var n, a=[]; for (n in e){a.push(n + ': ' + e[n])}; return a.join('\n')})(e)}");
                // "\n''') + '';} catch(e){e + (e.line ? ('\\nLine ' + (+e.line - 1)) : '')}");
                [
                    "$.level = 0;",
                    "try{eval('''" + isBin, // need to add an extra line otherwise #targetengine doesn't work ;-]
                    jsxScript.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"') + "\n''') + '';",
                    "} catch (e) {",
                    "    (function(e) {",
                    "        var line, sourceLine, name, description, ErrorMessage, fileName, start, end, bug;",
                    "        line = +e.line" + (isBin === '' ? ';' : ' - 1;'), // To take into account the extra line added
                    "        fileName = File(e.fileName).fsName;",
                    "        sourceLine = line && e.source.split(/[\\r\\n]/)[line];",
                    "        name = e.name;",
                    "        description = e.description;",
                    "        ErrorMessage = name + ' ' + e.number + ': ' + description;",
                    "        if (fileName.length && !(/[\\/\\\\]\\d+$/.test(fileName))) {",
                    "           ErrorMessage += '\\nFile: ' + fileName;",
                    "           line++;",
                    "        }",
                    "        if (line){",
                    "           ErrorMessage += '\\nLine: ' + line +",
                    "               '-> ' + ((sourceLine.length < 300) ? sourceLine : sourceLine.substring(0,300) + '...');",
                    "        }",
                    "        if (e.start) {ErrorMessage += '\\nBug: ' + e.source.substring(e.start - 1, e.end)}",
                    "        if ($.includeStack) {ErrorMessage += '\\nStack:' + $.stack;}",
                    "        return ErrorMessage;",
                    "    })(e);",
                    "}"
                ].join('')
            );

        }

        /////////////////////////////////////////////////////////////
        // deal with the replacements                              //
        // Note it's probably better to use ${template} `literals` //
        /////////////////////////////////////////////////////////////

        if (replacements) {
            for (key in replacements) {
                if (replacements.hasOwnProperty(key)) {
                    replaceThis = new RegExp('__' + key + '__', 'g');
                    withThis = replacements[key];
                    jsxScript = jsxScript.replace(replaceThis, withThis + '');
                }
            }
        }


        try {
            evalScript(jsxScript, callback);
            return true;
        } catch (err) {
            ////////////////////////////////////////////////
            // Do whatever error handling you want here ! //
            ////////////////////////////////////////////////
            var newErr;
            newErr = new Error(err);
            alert('Error Eek: ' + newErr.stack);
            return false;
        }

    };


    /**
     * [evalFile] For calling jsx scripts from the js engine
     *
     *         The jsx.evalFiles method is used for executing saved jsx scripts
     *         where the jsxScript parameter is a string of the jsx scripts file location.
     *         For convenience jsx.file or jsx.evalfile can be used instead of jsx.evalFile
     *
     * @param  {String} file
     *                            The path to jsx script
     *                            If only the base name is provided then the path will be presumed to be the
     *                            To execute files stored in the jsx folder located in the __dirname folder use
     *                            jsx.evalFile('myFabJsxScript.jsx');
     *                            To execute files stored in the a folder myFabScripts located in the __dirname folder use
     *                            jsx.evalFile('./myFabScripts/myFabJsxScript.jsx');
     *                            To execute files stored in the a folder myFabScripts located at an absolute url use
     *                            jsx.evalFile('/Path/to/my/FabJsxScript.jsx'); (mac)
     *                            or jsx.evalFile('C:Path/to/my/FabJsxScript.jsx'); (windows)
     *
     * @param  {Function} callback
     *                            The callback function you want the jsx script to trigger on completion
     *                            The result of the jsx script is passed as the argument to that function
     *                            The function can exist in some other file.
     *                            Note that InDesign does not automatically pass the callBack as a string.
     *                            Either write your InDesign in a way that it returns a sting the form of
     *                            return 'this is my result surrounded by quotes'
     *                            or use the force eval option
     *                            [Optional DEFAULT no callBack]
     *
     * @param  {Object} replacements
     *                            The replacements to make on the jsx script
     *                            give the following script (template)
     *                            'alert("__message__: " + __val__);'
     *                            and we want to change the script to
     *                            'alert("I was born in the year: " + 1234);'
     *                            we would pass the following object
     *                            {"message": 'I was born in the year', "val": 1234}
     *                            or if not using reserved words like do we can leave out the key quotes
     *                            {message: 'I was born in the year', val: 1234}
     *                            By default when possible the forceEvalScript will be set to true
     *                            The forceEvalScript option cannot be true when there are replacements
     *                            To force the forceEvalScript to be false you can send a blank set of replacements
     *                            jsx.evalFile('myFabScript.jsx', {}); Will NOT be executed using the $.evalScript method
     *                            jsx.evalFile('myFabScript.jsx'); Will YES be executed using the $.evalScript method
     *                            see the forceEvalScript parameter for details on this
     *                            [Optional DEFAULT no replacements]
     *
     * @param  {Bolean} forceEval
     *                             If the script should be wrapped in an eval and try catch
     *                             This will 1) provide useful error feedback if heaven forbid it is needed
     *                             2) The result will be a string which is required for callback results in InDesign
     *                             [Optional DEFAULT true]
     *
     *                             If no replacements are needed then the jsx script is be executed by using the $.evalFile method
     *                             This exposes the true value of the $.fileName property <span class="wp-font-emots-emo-sunglasses"></span>
     *                             In such a case it's best to avoid using the $.__fileName() with no base name as it won't work
     *                             BUT one can still use the $.__fileName('baseName') method which is more accurate than the standard $.fileName property <span class="wp-font-emots-emo-happy"></span>
     *                             Let's say you have a Drive called "Graphics" AND YOU HAVE a root folder on your "main" drive called "Graphics"
     *                             You call a script jsx.evalFile('/Volumes/Graphics/myFabScript.jsx');
     *                             $.fileName will give you '/Graphics/myFabScript.jsx' which is wrong
     *                             $.__fileName('myFabScript.jsx') will give you '/Volumes/Graphics/myFabScript.jsx' which is correct
     *                             $.__fileName() will not give you a reliable result
     *                             Note that if your calling multiple versions of myFabScript.jsx stored in multiple folders then you can get stuffed!
     *                             i.e. if the fileName is important to you then don't do that.
     *                             It also will force the result of the jsx file as a string which is particularly useful for InDesign callBacks
     *
     * Note 1) The order of the parameters is irrelevant
     * Note 2) One can pass the arguments as an object if desired
     *         jsx.evalScript(myCallBackFunction, 'alert("__myMessage__");', true);
     *         is the same as
     *         jsx.evalScript({
     *             script: 'alert("__myMessage__");',
     *             replacements: {myMessage: 'Hi there'},
     *             callBack: myCallBackFunction,
     *             eval: false,
     *         });
     *         note that either lower or camelCase key names or valid
     *         i.e. both callback or callBack will work
     *
     *      The following keys are the same file || jsx || script || jsxScript || jsxscript
     *      The following keys are the same callBack || callback
     *      The following keys are the same replacements || replace
     *      The following keys are the same eval || forceEval || forceeval
     *
     * @return {Boolean} if the jsxScript was executed or not
     */

    Jsx.prototype.evalFile = function() {
        var arg, args, callback, fileName, fileNameScript, forceEval, forceEvalScript,
            i, jsxFolder, jsxScript, newLine, replacements, success;

        success = true; // optimistic <span class="wp-font-emots-emo-happy"></span>
        args = arguments;

        jsxFolder = path.join(__dirname, 'jsx');
        //////////////////////////////////////////////////////////////////////////////////////////////////////////
        // $.fileName does not return it's correct path in the jsx engine for files called from the js engine   //
        // In Illustrator it returns an integer in InDesign it returns an empty string                          //
        // This script injection allows for the script to know it's path by calling                             //
        // $.__fileName();                                                                                      //
        // on Illustrator this works pretty well                                                                //
        // on InDesign it's best to use with a bit of care                                                      //
        // If the a second script has been called the InDesing will "forget" the path to the first script       //
        // 2 work-arounds for this                                                                              //
        // 1) at the beginning of your script add var thePathToMeIs = $.fileName();                             //
        //    thePathToMeIs will not be forgotten after running the second script                               //
        // 2) $.__fileName('myBaseName.jsx');                                                                   //
        //    for example you have file with the following path                                                 //
        //    /path/to/me.jsx                                                                                   //
        //    Call $.__fileName('me.jsx') and you will get /path/to/me.jsx even after executing a second script //
        // Note When the forceEvalScript option is used then you just use the regular $.fileName property       //
        //////////////////////////////////////////////////////////////////////////////////////////////////////////
        fileNameScript = [
            // The if statement should not normally be executed
            'if(!$.__fileNames){',
            '    $.__fileNames = {};',
            '    $.__dirname = "__dirname__";'.replace('__dirname__', __dirname),
            '    $.__fileName = function(name){',
            '        name = name || $.fileName;',
            '        return ($.__fileNames && $.__fileNames[name]) || $.fileName;',
            '    };',
            '}',
            '$.__fileNames["__basename__"] = $.__fileNames["" + $.fileName] = "__fileName__";'
        ].join('');

        //////////////////////////////////////////////////////////////////////////////////////
        // sort out order which arguments into jsxScript, callback, replacements, forceEval //
        //////////////////////////////////////////////////////////////////////////////////////


        // Detect if the parameters were passed as an object and if so allow for various keys
        if (args.length === 1 && (arg = args[0]) instanceof Object) {
            jsxScript = arg.jsxScript || arg.jsx || arg.script || arg.file || arg.jsxscript;
            callback = arg.callBack || arg.callback;
            replacements = arg.replacements || arg.replace;
            forceEval = arg.eval || arg.forceEval || arg.forceeval;
        } else {
            for (i = 0; i < 5; i++) {
                arg = args[i];
                if (arg === undefined) {
                    continue;
                }
                if (arg.constructor.name === 'String') {
                    jsxScript = arg;
                    continue;
                }
                if (arg.constructor.name === 'Object') {
                    //////////////////////////////////////////////////////////////////////////////////////////////////////////////
                    // If no replacements are provided then the $.evalScript method will be used                                //
                    // This will allow directly for the $.fileName property to be used                                          //
                    // If one does not want the $.evalScript method to be used then                                             //
                    // either send a blank object as the replacements {}                                                        //
                    // or explicitly set the forceEvalScript option to false                                                    //
                    // This can only be done if the parameters are passed as an object                                          //
                    // i.e. jsx.evalFile({file:'myFabScript.jsx', forceEvalScript: false});                                     //
                    // if the file was called using                                                                             //
                    // i.e. jsx.evalFile('myFabScript.jsx');                                                                    //
                    // then the following jsx code is called $.evalFile(new File('Path/to/myFabScript.jsx', 10000000000)) + ''; //
                    // forceEval is never needed if the forceEvalScript is triggered                                            //
                    //////////////////////////////////////////////////////////////////////////////////////////////////////////////
                    replacements = arg;
                    continue;
                }
                if (arg.constructor === Function) {
                    callback = arg;
                    continue;
                }
                if (arg === false) {
                    forceEval = false;
                }
            }
        }

        // If no script provide then not too much to do!
        if (!jsxScript) {
            return false;
        }

        forceEvalScript = !replacements;


        //////////////////////////////////////////////////////
        // Get path of script                               //
        // Check if it's literal, relative or in jsx folder //
        //////////////////////////////////////////////////////

        if (/^\/|[a-zA-Z]+:/.test(jsxScript)) { // absolute path Mac  | Windows
            jsxScript = path.normalize(jsxScript);
        } else if (/^\.+\//.test(jsxScript)) {
            jsxScript = path.join(__dirname, jsxScript); // relative path
        } else {
            jsxScript = path.join(jsxFolder, jsxScript); // files in the jsxFolder
        }

        if (forceEvalScript) {
            jsxScript = jsxScript.replace(/"/g, '\\"');
            // Check that the path exist, should change this to asynchronous at some point
            if (!window.cep.fs.stat(jsxScript).err) {
                jsxScript = fileNameScript.replace(/__fileName__/, jsxScript).replace(/__basename__/, path.basename(jsxScript)) +
                    '$.evalFile(new File("' + jsxScript.replace(/\\/g, '\\\\') + '")) + "";';
                return this.evalScript(jsxScript, callback, forceEval);
            } else {
            throw new Error(`The file: {jsxScript} could not be found / read`);
            }
        }

        ////////////////////////////////////////////////////////////////////////////////////////////////
        // Replacements made so we can't use $.evalFile and need to read the jsx script for ourselves //
        ////////////////////////////////////////////////////////////////////////////////////////////////

        fileName = jsxScript.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
        try {
            jsxScript = window.cep.fs.readFile(jsxScript).data;
        } catch (er) {
            throw new Error(`The file: ${fileName} could not be read`);
        }
        // It is desirable that the injected fileNameScript is on the same line as the 1st line of the script
        // This is so that the $.line or error.line returns the same value as the actual file
        // However if the 1st line contains a # directive then we need to insert a new line and stuff the above problem
        // When possible i.e.  when there's no replacements then $.evalFile will be used and then the whole issue is avoided
        newLine = /^\s*#/.test(jsxScript) ? '\n' : '';
        jsxScript = fileNameScript.replace(/__fileName__/, fileName).replace(/__basename__/, path.basename(fileName)) + newLine + jsxScript;

        try {
            // evalScript(jsxScript, callback);
            return this.evalScript(jsxScript, callback, replacements, forceEval);
        } catch (err) {
            ////////////////////////////////////////////////
            // Do whatever error handling you want here ! //
            ////////////////////////////////////////////////
            var newErr;
            newErr = new Error(err);
            alert('Error Eek: ' + newErr.stack);
            return false;
        }

        return success; // success should be an array but for now it's a Boolean
    };


    ////////////////////////////////////
    // Setup alternative method names //
    ////////////////////////////////////
    Jsx.prototype.eval = Jsx.prototype.script = Jsx.prototype.evalscript = Jsx.prototype.evalScript;
    Jsx.prototype.file = Jsx.prototype.evalfile = Jsx.prototype.evalFile;

    ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    // Examples                                                                                                                      //
    // jsx.evalScript('alert("foo");');                                                                                              //
    // jsx.evalFile('foo.jsx'); // where foo.jsx is stored in the jsx folder at the base of the extensions directory                 //
    // jsx.evalFile('../myFolder/foo.jsx'); // where a relative or absolute file path is given                                       //
    //                                                                                                                               //
    // using conventional methods one would use in the case were the values to swap were supplied by variables                       //
    // csInterface.evalScript('var q = "' + name + '"; alert("' + myString + '" ' + myOp + ' q);q;', callback);                      //
    // Using all the '' + foo + '' is very error prone                                                                               //
    // jsx.evalScript('var q = "__name__"; alert(__string__ __opp__ q);q;',{'name':'Fred', 'string':'Hello ', 'opp':'+'}, callBack); //
    // is much simpler and less error prone                                                                                          //
    //                                                                                                                               //
    // more readable to use object                                                                                                   //
    // jsx.evalFile({                                                                                                                //
    //      file: 'yetAnotherFabScript.jsx',                                                                                         //
    //      replacements: {"this": foo, That: bar, and: "&&", the: foo2, other: bar2},                                               //
    //      eval: true                                                                                                               //
    // })                                                                                                                            //
    // Enjoy <span class="wp-font-emots-emo-happy"></span>                                                                                                                     //
    ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


    jsx = new Jsx();
})();
