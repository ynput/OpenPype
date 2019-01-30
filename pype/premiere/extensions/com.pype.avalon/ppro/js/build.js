var app = angular.module("Plugin", ["ui-rangeSlider", "ui.bootstrap"]);
app.run(["$rootScope", "MainHelper", function($rootScope, MainHelper) {
    MainHelper.init(BM_VIDEO, 15)
}]), app.controller("ModalIntroController", function($scope, $uibModal, CreateOnFileSystemService, DestinationsService) {
    $scope.items = [], $scope.obj = {
        state: 1
    }, $scope.$root.$on("intro requested", function(event) {
        console.log("ModalIntroController event handler"), $scope.open("sm")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_INTRO_HTML,
            backdrop: "static",
            controller: ModalIntroInstanceCtrl,
            windowClass: "modal-intro"
        }).result.then(function() {
            console.log("ModalIntroController OK"), CreateOnFileSystemService.createDestinationBaseFolder(), DestinationsService.saveItem()
        }, function() {
            console.log("ModalIntroController CANCELED")
        })
    }
});

var ModalIntroInstanceCtrl = function($scope, $uibModalInstance, BrowseDestinationService, AppModel) {
    $scope.obj = {
        state: 1,
        title: "",
        message: "",
        labelLeft: [!1, "PREVIOUS"],
        labelCenter: [!1, ""],
        labelRight: [!0, "NEXT"],
        stateImage: [!0, ""],
        selectedFolder: AppModel.currentBaseFolder
    }, $scope.onChange = function() {
        switch (1 < $scope.obj.state && ($scope.obj.stateImage = [!0, STATE_IMG + $scope.obj.state + ".png"]), $scope.obj.state) {
            case 1:
                $scope.obj.stateName = "", $scope.obj.stateImage = [!1, ""], $scope.obj.labelLeft = [!1, "PREVIOUS"], $scope.obj.title = "Welcome!", $scope.obj.message = "Thanks for downloading the Pond5 Adobe Add-On.<BR>Click through this short tutorial to learn some of the basics.";
                break;
            case 2:
                $scope.obj.labelLeft = [!0, "PREVIOUS"], $scope.obj.stateName = "search", $scope.obj.title = "", $scope.obj.message = "Start by searching our massive library of royalty-free video clips<BR>and easily add them to your working projects.";
                break;
            case 3:
                $scope.obj.stateName = "filters", $scope.obj.labelLeft = [!0, "PREVIOUS"], $scope.obj.message = "Use the toolbar on the left to filter your search results,<BR>view your previews, and update your directory folder.";
                break;
            case 4:
                $scope.obj.stateName = "collections", $scope.obj.message = "View and create new collections below.<BR>We've even added 50 free clips to get you started!";
                break;
            case 5:
                $scope.obj.stateName = "login", $scope.obj.labelCenter = [!1, "SELECT"], $scope.obj.labelRight = [!0, "NEXT"], $scope.obj.message = "Log in to your Pond5 account here for easy checkout<BR>once you've found the perfect clips for your project.";
                break;
            case 6:
                $scope.obj.stateName = "", $scope.obj.labelLeft = [!0, "PREVIOUS"], $scope.obj.labelCenter = [!0, "SELECT"], $scope.obj.labelRight = [!0, "FINISH"], $scope.obj.message = "Select your destination folder to get started. Pond5 media will be saved in this folder.", 0 < AppModel.currentBaseFolder.length && ($scope.obj.message = "Select your destination folder to get started.<BR>The default folder is " + AppModel.currentBaseFolder)
        }
    }, $scope.buttonLeftClicked = function() {
        $scope.obj.state--, $scope.onChange(), getStateObject($scope.obj.stateName)
    }, $scope.buttonCenterClicked = function() {
        $scope.obj.selectedFolder = BrowseDestinationService.browse(), $scope.obj.message = "Your current destination folder is:<BR>" + $scope.obj.selectedFolder
    }, $scope.buttonRightClicked = function() {
        console.log("ModalIntroController buttonRightClicked"), $scope.obj.state < 6 ? ($scope.obj.state++, $scope.onChange(), getStateObject($scope.obj.stateName)) : (console.log("ModalIntroController buttonRightClicked", $scope.obj.selectedFolder), BrowseDestinationService.save($scope.obj.selectedFolder), $uibModalInstance.close())
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }, getStateObject = function(stateName) {
        console.log("modalIntroController look for: ", stateName), INTRO_DATA.forEach(function(entry) {
            var obj = {};
            entry.stateName === stateName ? (console.log("modalIntroController found stateName: ", entry), obj.stateName = entry.stateName, obj.arrowClass = entry.arrowClass, obj.posX = entry.posX, obj.posY = entry.posY, console.log("modalIntroController found obj: ", obj)) : (obj.stateName = stateName, obj.arrowClass = ""), $scope.$root.$emit("intro asset requested", obj)
        })
    }, $scope.onChange()
};
PLUGIN_VERSION = "", HOST_NAME = "PPRO", THIRD_PARTY = "", MEDIA_TYPES = ["Footage", "Music", "SFX"], BUTTON_REPLACE_LABEL = "REPLACE WITH HI-RES CLIPS", BUTTON_REPLACE_TOOLTIP = "Replace lo-res with paid items", MODAL_REPLACE_HEADER = "Replace With Hi-Res Clips", MODAL_REPLACE_CONTENT = "The selected items below will be replaced by full resolution versions after you complete checkout. Items already in your account history will also be downloaded.", MODAL_REPLACE_RES_TITLE = "RESOLUTION", MODAL_INTRO_SEARCH = "Start by searching our massive library of royalty-free video clips<BR>and easily add them to your working projects.", MODAL_INTRO_COLLECTIONS = "View and create new collections below.<BR>We've even added 50 free clips to get you started!", MODAL_INTRO_LOGIN = "Log in to your Pond5 account here for easy checkout<BR>once you've found the perfect clips for your project.", INTRO_DATA = [{
    state: 7,
    stateName: "downloads",
    arrowClass: ".intro-asset-arrow-left",
    posY: ["top", "96px"],
    posX: ["left", "60px"]
}, {
    state: 3,
    stateName: "filters",
    arrowClass: ".intro-asset-arrow-left",
    posY: ["top", "60px"],
    posX: ["left", "55px"]
}, {
    state: 9,
    stateName: "destination",
    arrowClass: ".intro-asset-arrow-left",
    posY: ["bottom", "55px"],
    posX: ["left", "60px"]
}, {
    state: 4,
    stateName: "collections",
    arrowClass: ".intro-asset-arrow-down",
    posY: ["bottom", "140px"],
    posX: ["left", "260px"]
}, {
    state: 2,
    stateName: "search",
    arrowClass: ".intro-asset-arrow-up",
    posY: ["top", "60px"],
    posX: ["left", "165px"]
}, {
    state: 5,
    stateName: "login",
    arrowClass: ".intro-asset-arrow-up",
    posY: ["top", "60px"],
    posX: ["right", "75px"]
}], app.service("ReplaceService", ["$rootScope", "ReplaceModel", "Service", "ReplaceServiceShared", function($rootScope, ReplaceModel, Service, ReplaceServiceShared) {
    var call = {
        onClipFSCollected: function() {
            call.getSequences()
        },
        getSequences: function() {
            csInterface.evalScript("getSequences()", function(result) {
                var sequences = JSON.parse(result).sequences;
                console.log("\nReplaceService sequences NEW", sequences.length, sequences), ReplaceModel.setSequences(sequences)
            })
        },
        getMedia: function() {
            var obj = ReplaceModel.sequences;
            csInterface.evalScript("getSequenceItems(" + JSON.stringify(obj) + ")", function(result) {
                var clipsInSequences = JSON.parse(result).data;
                ReplaceModel.clipsInSequences = clipsInSequences, console.log("\nReplaceService clipsInSequences", ReplaceModel.clipsInSequences), csInterface.evalScript("getProjectItems()", function(result) {
                    call.getMissingItemIDs()
                })
            })
        },
        getClipsInSelectedSequences: function() {
            for (var clipsInSequences = ReplaceModel.clipsInSequences, clipsInSelectedSequences = [], s = 0; s < ReplaceModel.sequences.length; s++)
                for (var j = 0; j < clipsInSequences.length; j++)
                    if (ReplaceModel.sequences[s].sequenceID === clipsInSequences[j].sequenceID && ReplaceModel.sequences[s].checked)
                        for (var k = 0; k < clipsInSequences[j].clipNames.length; k++) clipsInSelectedSequences.push(clipsInSequences[j].clipNames[k]);
            return clipsInSelectedSequences
        },
        getMissingItemIDs: function() {
            var clipsInSelectedSequences = call.getClipsInSelectedSequences();
            clipsInSelectedSequences = ReplaceServiceShared.removeDuplicates(clipsInSelectedSequences), console.log("\nReplaceService clipsInSelectedSequences after removing duplicates: ", clipsInSelectedSequences);
            var previewNamesonFS = ReplaceServiceShared.getPreviewsOnFSNames();
            clipsInSelectedSequences = ReplaceServiceShared.filterNonP5Clips(clipsInSelectedSequences, previewNamesonFS), console.log("\nReplaceService after filterNonP5Clips", clipsInSelectedSequences);
            var previewIDs = ReplaceServiceShared.getPreviewsIDs(clipsInSelectedSequences);
            console.log("\nReplaceService previewIDs: " + previewIDs), ReplaceServiceShared.setReplaceProp(previewIDs), console.log("\nReplaceService after set replace: " + ReplaceModel.hiresOnFS);
            var hiresIDs = ReplaceServiceShared.getHiresIDsonFS();
            console.log("\nReplaceService hiresIDs: " + hiresIDs);
            var missingItemIDs = _(previewIDs).difference(hiresIDs),
                missingIDsToString = missingItemIDs.join(",");
            0 < missingItemIDs.length ? Service.getMissingItems(missingIDsToString) : 0 < hiresIDs.length ? call.onPurchasedAndDownloaded() : 0 === clipsInSelectedSequences.length && (ReplaceModel.setState(DEFAULT), $rootScope.$emit("modal simple requested", ["", "There are are currently no Pond5 previews in the sequence(s) you've selected."]))
        },
        onPurchasedAndDownloaded: function() {
            var hasReplaceCandidates = !1;
            if (ReplaceModel.hiresOnFS.forEach(function(entry) {
                    entry.replace && (hasReplaceCandidates = !0)
                }), !hasReplaceCandidates) return $rootScope.$emit("modal simple requested", ["", "Replacing previews by hi-res clips has been canceled"]), void ReplaceModel.setState(DEFAULT);
            var obj = {
                hiresOnFS: ReplaceModel.hiresOnFS
            };
            csInterface.evalScript("replaceClips(" + JSON.stringify(obj) + ")", function(result) {
                $rootScope.$emit("modal simple requested", ["", "Your previews have been successfully replaced by your purchased clips. Right-click the clips and choose Scale to Frame Size to scale them correctly."]), ReplaceModel.setState(DEFAULT)
            })
        }
    };
    return call
}]), app.controller("ModalAddDestinationController", function($scope, $uibModal, UserModel, AppModel, CreateOnFileSystemService, DestinationsService) {
    $scope.obj = {}, $scope.$root.$on("modal add destination requested", function() {
        console.log("ModalAddDestinationController event handler", UserModel.getFirstTimeUser()), $scope.obj.title = "Add a destination folder", $scope.obj.content = "Please select a new folder to store your previews and purchased items.", $scope.obj.okButtonLabel = "APPLY", $scope.obj.selectedFolderPrefix = "Current folder: ", $scope.obj.selectedFolder = AppModel.currentBaseFolder, $scope.open("lg")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_ADD_DESTINATION_HTML,
            controller: ModalAddDestinatonInstanceCtrl,
            size: size,
            resolve: {
                obj: function() {
                    return $scope.obj
                }
            }
        }).result.then(function() {
            console.log("ModalAddDestinationController OK", AppModel.currentBaseFolder), $scope.onClicked()
        }, function() {
            console.log("ModalAddDestinationController CANCEL", AppModel.currentBaseFolder), $scope.onClicked()
        })
    }, $scope.onClicked = function() {
        console.log("ModalAddDestinationController onClicked"), UserModel.getFirstTimeUser() && $scope.$root.$emit("modal freebies"), CreateOnFileSystemService.createDestinationBaseFolder(), DestinationsService.saveItem()
    }
});
var ModalAddDestinatonInstanceCtrl = function($scope, $uibModalInstance, obj, BrowseDestinationService) {
    $scope.obj = {}, $scope.obj.showTitle = obj.showTitle, $scope.obj.title = obj.title, $scope.obj.content = obj.content, $scope.obj.selectedFolder = obj.selectedFolder, $scope.obj.selectedFolderPrefix = obj.selectedFolderPrefix, $scope.obj.okButtonLabel = obj.okButtonLabel, $scope.browse = function() {
        console.log("ModalAddDestinatonInstanceCtrl browse"), $scope.obj.selectedFolder = BrowseDestinationService.browse()
    }, $scope.ok = function() {
        BrowseDestinationService.save($scope.obj.selectedFolder), $uibModalInstance.close()
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("ModalSelectSequencesController", function($scope, $uibModal, ReplaceModel, ReplaceService) {
    $scope.items = [], $scope.$root.$on("modal select sequences", function(event, data) {
        $scope.items = data, $scope.open("lg")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_SELECT_SEQUENCES_HTML,
            controller: ModalSelectSequencesInstanceCtrl,
            size: size,
            resolve: {
                items: function() {
                    return $scope.items
                }
            }
        }).result.then(function() {
            console.log("ModalSelectSequencesController OK: ", $scope.items);
            for (var i = 0; i < $scope.items.length; i++) $scope.items[i].selected && (ReplaceModel.sequences[i].checked = !0);
            ReplaceService.getMedia()
        }, function() {
            ReplaceModel.setState(DEFAULT)
        })
    }
});
var ModalSelectSequencesInstanceCtrl = function($scope, $uibModalInstance, items) {
    $scope.items = items, $scope.obj = {
        showWarning: !1
    }, $scope.ok = function() {
        for (var checked = !1, i = 0; i < $scope.items.length; i++) $scope.items[i].selected && (checked = !0);
        checked ? $uibModalInstance.close() : $scope.obj.showWarning = !0
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.factory("MainHelper", ["$rootScope", "AppModel", "StartUpService", "SearchModel", function($rootScope, AppModel, StartUpService, SearchModel) {
    var result = {
        init: function(mediaType, sumOfBitmasks) {
            csInterface = new CSInterface, csInterface.addEventListener("LogEvent", function(evt) {
                console.log("JSX : " + evt.data)
            });
            var rootFolderPath = csInterface.getSystemPath(SystemPath.EXTENSION);
            AppModel.rootFolderPath = rootFolderPath, fs = require("fs"), os = require("os"), path = require("path"), url = require("url"), https = require("https"), xml2js = require(rootFolderPath + "/node_modules/xml2js/lib/xml2js.js"), walk = require(rootFolderPath + "/node_modules/walk/lib/walk.js"), junk = require(rootFolderPath + "/node_modules/junk/index.js"), rimraf = require(rootFolderPath + "/node_modules/rimraf/rimraf.js"), opn = require(rootFolderPath + "/node_modules/opn/index.js"), DecompressZip = require(rootFolderPath + "/node_modules/decompress-zip/lib/decompress-zip.js"), $("#logo").click(function() {
                location.reload()
            }), result.readManifestXML(), SearchModel.sumOfBitmasks = sumOfBitmasks, $rootScope.$emit("media filter change", mediaType), setTimeout(function() {
                AppModel.setEnv()
            }, 2e3)
        },
        readManifestXML: function() {
            var file = AppModel.rootFolderPath + "/CSXS/manifest.xml";
            fs.readFile(file, "utf8", function(err, data) {
                if (err) throw err;
                result.parseXML(data)
            })
        },
        parseXML: function(xml) {
            var parser = new xml2js.Parser;
            parser.addListener("end", function(res) {
                PLUGIN_VERSION = res.ExtensionManifest.$.ExtensionBundleVersion, console.log("mainHelper parsed manifest xml, version:", PLUGIN_VERSION), result.loadJSX()
            }), parser.parseString(xml)
        },
        loadJSX: function(fileName) {
            var jsxPath = AppModel.rootFolderPath + "./js/vendor/json2.js";
            console.log("mainHelper loadJSX:", jsxPath), csInterface.evalScript('$.evalFile("' + jsxPath + '")', function(result) {})
        }
    };
    return result
}]), app.service("BrowseDestinationService", ["AppModel", function(AppModel) {
    this.browse = function() {
        var result = window.cep.fs.showOpenDialog(!1, !0, "Select a folder for your previews and hi-res downloads.", ""),
            selectedFolder = AppModel.currentBaseFolder;
        return console.log("BrowseDestinationService folder chosen, result.err: ", result.err), 0 == result.err ? (console.log("BrowseDestinationService folder chosen: ", result.data[0]), result.data[0] && (selectedFolder = result.data[0])) : selectedFolder = "This folder cannot be selected. Please choose another folder.", console.log("BrowseDestinationService return folder: ", selectedFolder), selectedFolder
    }, this.save = function(selectedFolder) {
        console.log("BrowseDestinationService save", AppModel.getOS(), "win" === AppModel.getOS()), "win" === AppModel.getOS() ? AppModel.currentBaseFolder = selectedFolder.replace(/\//g, "\\") : AppModel.currentBaseFolder = selectedFolder
    }
}]), app.service("CreateFileCompleteService", ["ImportedPreviewsService", "DestinationsService", "UserService", function(ImportedPreviewsService, DestinationsService, UserService) {
    return {
        onFileReady: function(file) {
            -1 != file.indexOf("imported_previews.xml") && ImportedPreviewsService.readXML(), -1 != file.indexOf("destinations.xml") && DestinationsService.readXML(), -1 != file.indexOf("user.xml") && UserService.readXML()
        }
    }
}]), app.factory("DestinationsService", ["$rootScope", "AppModel", "UserModel", function($rootScope, AppModel, UserModel) {
    var result = {
        xmlVersion: "",
        readXML: function() {
            result.file = AppModel.getDestinationsXML(), console.log("DestinationsService file: ", result.file), fs.readFile(result.file, "utf8", function(err, data) {
                if (err) throw err;
                result.xml = data, console.log("DestinationsService, xml:", result.xml), result.parseXML()
            })
        },
        saveItem: function() {
            var node = '<destination destination="' + AppModel.currentBaseFolder + '" />';
            result.xml = result.xml.insert(result.xml.indexOf("destinations") + 13, node), result.writeToDisk()
        },
        deleteItem: function() {},
        parseXML: function() {
            var parser = new xml2js.Parser;
            parser.addListener("end", function(res) {
                var i;
                result.parsedXML = res, AppModel.baseFolders = [], UserModel.setFirstTimeUser(!1), res.root.$[HOST_NAME] ? result.xmlVersion = res.root.$[HOST_NAME] : res.root.$.version ? result.xmlVersion = res.root.$.version : res.root.$.PPRO && (result.xmlVersion = res.root.$.PPRO), UserModel.setUID(res.root.$.id), PLUGIN_VERSION != result.xmlVersion && (console.log("DestinationsService other or no version number in xml, first time user: ", result.xmlVersion), UserModel.setFirstTimeUser(!0));
                var destinations = res.root.destinations[0].destination;
                if (console.log("DestinationsService destinations: ", destinations), destinations) {
                    for (i = 0; i < destinations.length; i++) - 1 == AppModel.baseFolders.indexOf(destinations[i].$.destination) && fs.existsSync(destinations[i].$.destination + path.sep + "pond5") && AppModel.baseFolders.push(destinations[i].$.destination);
                    fs.stat(AppModel.baseFolders[0] + path.sep + "pond5", function(err, stats) {
                        err ? setTimeout(function() {
                            $rootScope.$emit("modal add destination requested")
                        }, 3e3) : AppModel.currentBaseFolder = AppModel.baseFolders[0]
                    }), console.log("DestinationsService AppModel.baseFolders : ", AppModel.baseFolders), console.log("DestinationsService currentBaseFolder : ", AppModel.currentBaseFolder)
                }
                if (UserModel.getFirstTimeUser()) {
                    var newVersion = HOST_NAME + '="' + PLUGIN_VERSION + '"';
                    result.parsedXML.root.$[HOST_NAME] ? result.xml = result.xml.replace(HOST_NAME + '="' + result.xmlVersion + '"', newVersion) : result.parsedXML.root.$.version && "PPRO" === HOST_NAME ? result.xml = result.xml.replace('version="' + result.xmlVersion + '"', newVersion) : result.parsedXML.root.$.version && "PPRO" != HOST_NAME ? result.xml = result.xml.replace('version="' + result.xmlVersion + '"', 'version="' + result.xmlVersion + '" ' + newVersion) : result.parsedXML.root.$.PPRO && !result.parsedXML.root.$[HOST_NAME] && (result.xml = result.xml.replace('PPRO="' + result.xmlVersion + '"', 'PPRO="' + result.xmlVersion + '" ' + newVersion)), console.log("DestinationsService result.xml replaced: ", result.xml), console.log("DestinationsService getFirstTimeUser is true, show intro"), setTimeout(function() {
                        $rootScope.$emit("intro requested")
                    }, 3e3)
                }
            }), parser.parseString(result.xml)
        },
        writeToDisk: function() {
            fs.writeFile(result.file, result.xml, function(err) {
                if (err) throw err;
                result.readXML()
            })
        }
    };
    return result
}]), app.service("ImportService", ["$rootScope", function($rootScope) {
    this.importClips = function(items) {
        var i, importPaths = [];
        for (i = 0; i < items.length; i++) console.log("ImportService item.canceled:", items[i].canceled), items[i].canceled || items[i].imported || (items[i].imported = !0, importPaths.push(items[i].downloadDestination + items[i].fileName));
        console.log("ImportService importPath:", importPaths);
        var obj = {
            paths: importPaths
        };
        csInterface.evalScript("importClips(" + JSON.stringify(obj) + ")", function(result) {
            console.log("ImportService result: ", result), $rootScope.$emit("on importing bin complete")
        })
    }
}]), app.service("OpenURLService", [function() {
    this.openURL = function(url) {
        csInterface.openURLInDefaultBrowser(url)
    }
}]), app.controller("AdvancedSearchController", function($scope, ViewStateModel, SearchModel, ViewStateService) {
    $scope.obj = {
        show: !1,
        fpsItems: [{
            fps: "23.98"
        }, {
            fps: "24"
        }, {
            fps: "25"
        }, {
            fps: "29.97"
        }, {
            fps: "30"
        }, {
            fps: "60"
        }, {
            fps: "60+"
        }],
        resItems: [{
            res: "4K+",
            param: "8K"
        }, {
            res: "4K",
            param: "4K"
        }, {
            res: "2K",
            param: "2K"
        }, {
            res: "HD (1080)",
            param: "HD1080"
        }, {
            res: "HD (720)",
            param: "HD720"
        }, {
            res: "SD",
            param: "SD"
        }, {
            res: "Web",
            param: "WEB"
        }],
        showCbFilters: !0,
        _minPrice: 0,
        _maxPrice: 500,
        minPrice: function(newValue) {
            return arguments.length ? $scope.obj._minPrice = newValue : $scope.obj._minPrice
        },
        maxPrice: function(newValue) {
            return 500 == $scope.obj._maxPrice ? $scope.obj.maxPriceValue = "$500+" : $scope.obj.maxPriceValue = "$" + $scope.obj._maxPrice, arguments.length ? $scope.obj._maxPrice = newValue : $scope.obj._maxPrice
        },
        _minTime: 0,
        _maxTime: 120,
        minTime: function(newValue) {
            return arguments.length ? $scope.obj._minTime = newValue : $scope.obj._minTime
        },
        maxTime: function(newValue) {
            return 120 == $scope.obj._maxTime ? $scope.obj.showTimePlusSign = !0 : $scope.obj.showTimePlusSign = !1, arguments.length ? $scope.obj._maxTime = newValue : $scope.obj._maxTime
        }
    }, $scope.oneAtATime = !0, $scope.reset = function() {
        for ($scope.obj._minPrice = 0, $scope.obj._maxPrice = 500, $scope.obj._minTime = 0, $scope.obj._maxTime = 120, SearchModel.fps = "", SearchModel.fpsgt = "", SearchModel.res = "", SearchModel.pricegt = "", SearchModel.pricelt = "", SearchModel.durationgt = "", SearchModel.durationlt = "", i = 0; i < $scope.obj.fpsItems.length; i++) $scope.obj.fpsItems[i].checked = !1;
        for (i = 0; i < $scope.obj.resItems.length; i++) $scope.obj.resItems[i].checked = !1
    }, $scope.reset(), $scope.$root.$on("filters button clicked", function(event, state) {
        $scope.obj.show = state
    }), $scope.$root.$on("media filter change", function(event, data) {
        data == BM_VIDEO || data == BM_PUBLIC_DOMAIN ? $scope.obj.showCbFilters = !0 : ($scope.obj.showCbFilters = !1, $scope.reset()), data == BM_AFTER_EFFECTS ? $scope.obj.showDuration = !1 : $scope.obj.showDuration = !0
    }), $scope.change = function() {
        var fpsgt, fps = " fps",
            res = " resolutions";
        for (i = 0; i < $scope.obj.fpsItems.length - 1; i++) $scope.obj.fpsItems[i].checked && (fps += ":" + $scope.obj.fpsItems[i].fps);
        for (fpsgt = $scope.obj.fpsItems[6].checked ? " fpsgt:60" : "", i = 0; i < $scope.obj.resItems.length; i++) $scope.obj.resItems[i].checked && (res += ":" + $scope.obj.resItems[i].param);
        fps.length <= 5 ? fps = "" : fpsgt = "", res.length <= 13 && (res = ""), SearchModel.fps = fps, SearchModel.fpsgt = fpsgt, SearchModel.res = res, SearchModel.resultType = "replace", SearchModel.page = 0, ViewStateService.viewRequested("search")
    }, $scope.onHideFiltersClicked = function() {
        $scope.obj.show = !1, $scope.$root.$emit("filters button clicked", !1)
    }, $scope.onResetFiltersClicked = function() {
        $scope.reset(), $scope.change()
    }, $scope.viewState = function() {
        return ViewStateModel.getState()
    }, $scope.$watch($scope.viewState, function() {
        "cart" !== ViewStateModel.getState() && "downloads" !== ViewStateModel.getState() || ($scope.obj.show = !1)
    }, !0), window.addEventListener("rangeSliderOff", function(e) {
        "" == $scope.obj._minPrice ? SearchModel.pricegt = "" : SearchModel.pricegt = " pricegt:" + $scope.obj._minPrice, "500" == $scope.obj._maxPrice ? SearchModel.pricelt = "" : SearchModel.pricelt = " pricelt:" + $scope.obj._maxPrice, "" == $scope.obj._minTime ? SearchModel.durationgt = "" : SearchModel.durationgt = " durationgt:" + $scope.obj._minTime, "120" == $scope.obj._maxTime ? SearchModel.durationlt = "" : SearchModel.durationlt = " durationlt:" + $scope.obj._maxTime, $scope.change()
    }, !1)
}), app.controller("AlertController", function($scope) {
    $scope.alerts = [], $scope.addAlert = function() {
        console.log("AlertController add"), $scope.alerts.push({
            msg: "Another alert!"
        })
    }, $scope.closeAlert = function(index) {
        $scope.alerts.splice(index, 1)
    }
}), app.controller("BinsController", function($scope, BinsModel, Service, LoginModel, ViewStateModel, ViewStateService) {
    $scope.obj = {}, $scope.obj.showImportAll = !1, $scope.obj.showSelect = !1, $scope.obj.direction = "dropup", $scope.loginModel = function() {
        return LoginModel.loggedIn
    }, $scope.viewStateModel = function() {
        return ViewStateModel.getState()
    }, $scope.$watch($scope.loginModel, function() {
        LoginModel.loggedIn ? $scope.obj.showSelect = !0 : $scope.obj.showSelect = !1
    }), $scope.$watch($scope.viewStateModel, function() {
        "bins" != ViewStateModel.getState() && ($scope.obj.selectedNameFormatted = "Collection")
    }), $scope.$root.$on("onBins", function(event) {
        $scope.bins = BinsModel.bins
    }), $scope.onClick = function() {
        console.log("BinsController onClick"), $scope.$root.$emit("select clicked")
    }, $scope.onChange = function(bin) {
        console.log("onChange, bin: ", bin), 14 < bin.name.length ? $scope.obj.selectedNameFormatted = bin.name.substr(0, 14) + "..." : $scope.obj.selectedNameFormatted = bin.name, $scope.obj.open = !1, $scope.selected = bin, $scope.selected && (BinsModel.selectedBin = bin, $scope.$root.$emit("bin selected", bin.name), ViewStateService.viewRequested("bins"))
    }, $scope.onDelete = function(bin) {
        console.log("onDelete, bin: ", bin)
    }, $scope.toggled = function(open) {
        $scope.obj.direction = open ? "down" : "dropup"
    }, $scope.onAddClicked = function() {
        console.log("onAddClicked"), $scope.$root.$emit("modal add collection requested")
    }, $scope.onRemoveClicked = function() {
        console.log("onRemoveClicked"), $scope.$root.$emit("modal remove collection requested")
    }
}), app.controller("CartController", function($scope, Service, ViewStateService, CartModel, LoginModel, AnalyticsService) {
    $scope.obj = {
        numberOfItem: 0,
        clearCartIcon: CLEAR_CART_TRASH_IMG,
        imageUrl: CART_BUTTON_IMG,
        cartButtonStyle: "button-cart-logged-out"
    }, $scope.cartModel = function() {
        return CartModel.cartVO
    }, $scope.$watch($scope.cartModel, function() {
        CartModel.cartVO.items && ($scope.obj.numberOfItems = CartModel.cartVO.items.length)
    }), $scope.loginModel = function() {
        return LoginModel
    }, $scope.$watch($scope.loginModel, function() {
        LoginModel.getLoggedIn() ? $scope.obj.cartButtonStyle = "button-cart-logged-in" : ($scope.obj.cartButtonStyle = "button-cart-logged-out", $scope.obj.numberOfItems = "")
    }, !0), $scope.onCartButtonClicked = function() {
        ViewStateService.viewRequested("cart");
        var ga = {
            ec: "cart"
        };
        AnalyticsService.sendData(ga)
    }
}), app.controller("CheckOutController", function($scope, Service, ViewStateModel, CheckOutService, CartModel) {
    $scope.obj = {
        show: !1,
        disabled: !0,
        info: "",
        showInfo: !1,
        subTotalText: "",
        showVAT: !1,
        lineStyle: "",
        totalStyle: "",
        remainingStyle: "",
        cartInfoStyle: ""
    }, $scope.CartModel = function() {
        return CartModel.cartVO
    }, $scope.$watch($scope.CartModel, function() {
        CartModel.cartVO.items && 0 < CartModel.cartVO.items.length ? $scope.obj.disabled = !1 : $scope.obj.disabled = !0
    }, !0), $scope.$root.$on("checkout complete", function() {
        $scope.obj.disabled = !1
    }), $scope.$root.$on("billing info canceled", function() {
        $scope.obj.disabled = !1
    }), $scope.viewState = function() {
        return ViewStateModel.getState()
    }, $scope.$watch($scope.viewState, function() {
        "cart" === ViewStateModel.getState() ? $scope.obj.show = !0 : $scope.obj.show = !1
    }, !0), $scope.onClick = function() {
        $scope.obj.disabled = !0, $scope.$root.$emit("on modal choose billing info requested"), $scope.onOut()
    }, $scope.onOver = function() {
        $scope.obj.showInfo = !0, $scope.showData()
    }, $scope.onOut = function() {
        $scope.obj.showInfo = !1
    }, $scope.showData = function() {
        var data = CartModel.getCartTotal();
        data && ($scope.obj.subTotalText = data.subtotals.beforeDiscounts, data.vatData.display ? $scope.obj.showVAT = !0 : $scope.obj.showVAT = !1, $scope.obj.showVAT ? ($scope.obj.cartInfoStyle = "cart-info-vat", $scope.obj.lineStyle = "cart-info-line-vat", $scope.obj.totalStyle = "cart-info-total-vat", $scope.obj.remainingStyle = "cart-info-remaining-vat", $scope.obj.vatPerc = data.vatData.percentage, $scope.obj.vat = data.vatData.amount) : ($scope.obj.cartInfoStyle = "cart-info-no-vat", $scope.obj.lineStyle = "cart-info-line-no-vat", $scope.obj.totalStyle = "cart-info-total-no-vat", $scope.obj.remainingStyle = "cart-info-remaining-no-vat"), $scope.obj.credits = data.creditsData.usedSum, $scope.obj.total = data.subtotals.final, $scope.obj.remaining = data.creditsData.remainingSum)
    }, $scope.$root.$on("alreadyBought", function(event, data) {
        CheckOutService.onCheckOutRequested(data)
    }), $scope.$root.$on("ownClips", function(event, data) {
        CheckOutService.onCheckOutRequested(data)
    })
}), app.controller("CollectionsController", function($scope, BinsModel, Service, LoginModel, ViewStateService) {
    $scope.obj = {}, $scope.obj.showImportAll = !1, $scope.obj.showFooter = !1, $scope.obj.showList = !1, $scope.obj.showBin, $scope.obj.addToBin, $scope.obj.addToBinName = "Collections", $scope.obj.collectionsList = COLLECTIONS_LIST_HTML, $scope.loginModel = function() {
        return LoginModel.loggedIn
    }, $scope.$watch($scope.loginModel, function() {
        LoginModel.loggedIn ? $scope.obj.showFooter = !0 : $scope.obj.showFooter = !1
    }), $scope.$root.$on("onBins", function(event) {
        $scope.bins = BinsModel.bins, 0 == BinsModel.bins.length && ($scope.obj.addToBinName = "Collections")
    }), $scope.$root.$on("active bin changed", function(event) {
        $scope.obj.addToBin = BinsModel.addToBin, BinsModel.addToBin && ($scope.obj.addToBinName = getAbbrName(BinsModel.addToBin.name, 10))
    }), $scope.toggleList = function() {
        $scope.obj.showList = !$scope.obj.showList
    }, $scope.openList = function() {
        $scope.obj.showList = !0
    }, $scope.closeList = function() {
        $scope.obj.showList = !1
    }, $scope.deleteIconClicked = function(bin) {
        $scope.$root.$emit("collection delete requested", [bin])
    }, $scope.showCollectionIconClicked = function(bin) {
        BinsModel.showBin = bin, $scope.$root.$emit("bin selected", bin.name), ViewStateService.viewRequested("bins"), $scope.closeList()
    }, $scope.collectionNameClicked = function(bin) {
        BinsModel.addToBin = bin, $scope.obj.addToBinName = getAbbrName(bin.name, 10), $scope.closeList(), Service.setActiveBin(BinsModel.addToBin.id)
    }, $scope.freeItemsClicked = function() {
        ViewStateService.viewRequested("freebies"), $scope.closeList()
    }, $scope.onClick = function() {
        $scope.$root.$emit("select clicked")
    }, $scope.onAddClicked = function() {
        $scope.$root.$emit("modal add collection requested")
    }
}), app.controller("DownloadAllController", function($scope, ViewStateModel, DownloadBatchService, PurchasesModel, AnalyticsService) {
    function onStateChange() {
        "downloads" === ViewStateModel.getState() && PurchasesModel.purchasesVO && PurchasesModel.purchasesVO.items ? $scope.obj.show = !0 : $scope.obj.show = !1
    }
    $scope.obj = {
        show: !1,
        isDownloading: !1
    }, $scope.$root.$on("on downloading all purchases complete", function(event) {
        $scope.$apply(function() {
            $scope.obj.isDownloading = !1
        })
    }), $scope.$root.$on("cancel all requested", function(event) {
        console.log("DownloadAllController cancel all requested"), $scope.obj.isDownloading = !1
    }), $scope.$root.$on("on purchases vo", function() {
        onStateChange()
    }), $scope.viewState = function() {
        return ViewStateModel.getState()
    }, $scope.$watch($scope.viewState, onStateChange, !0), $scope.onDownloadAllClicked = function() {
        console.log("DownloadAllController onDownloadAllClicked"), $scope.obj.isDownloading = !0, DownloadBatchService.onBatchRequested();
        var ga = {
            ec: "download%20all"
        };
        console.log("DownloadAllController ga", ga), AnalyticsService.sendData(ga)
    }
}), app.controller("DownloadProgressController", function($scope, $timeout, ProgressService, DownloadRequestService, DownloadCancelService, ViewStateModel, DownloadModel) {
    $scope.obj = {
        items: [],
        isOpen: !1,
        progressCloseIcon: PROGRESS_CLOSE_IMG
    }, $scope.viewStateModel = function() {
        return ViewStateModel.getState()
    }, $scope.$watch($scope.viewStateModel, function() {
        $scope.obj.view = ViewStateModel.getState()
    }), $scope.$root.$on("select clicked", function(event) {
        $scope.obj.isOpen = !1
    }), $scope.$root.$on("import all clicked", function(event) {
        $scope.obj.isOpen = !0
    }), $scope.$root.$on("open progress", function(event) {
        $scope.obj.isOpen || ($scope.obj.isOpen = !0)
    }), $scope.$root.$on("clear progress", function(event) {
        $scope.obj.items = DownloadModel.itemsDownloadList
    }), $scope.$root.$on("added to progress", function(event, data) {
        $scope.obj.items = DownloadModel.itemsDownloadList
    }), $scope.onProgressIconClicked = function() {
        $scope.$root.$emit("progress button clicked")
    }, $scope.$root.$on("progress button clicked", function(event) {
        $scope.obj.isOpen = !$scope.obj.isOpen
    }), $scope.clearListClicked = function() {
        $scope.$root.$emit("progress button clicked"), ProgressService.clearCompleteItems(), 0 < $scope.obj.items.length ? $scope.obj.isOpen = !0 : $scope.obj.isOpen = !1
    }, $scope.showClear = function() {
        var show = !1;
        return $scope.obj.items.forEach(function(item) {
            item.completed && (show = !0)
        }), !ProgressService.getDownloadingStatus() && 0 < DownloadModel.itemsDownloadList.length && (show = !0), show
    }, $scope.isDownloading = function() {
        var isDownloading = !1;
        return $scope.obj.items.forEach(function(item) {
            item.downloading && (isDownloading = !0)
        }), ProgressService.getDownloadingStatus() && (show = !0), isDownloading
    }, $scope.showMenu = function() {
        return 0 < $scope.obj.items.length
    }, $scope.cancelAllClicked = function() {
        DownloadCancelService.onCancelAll(), $scope.$root.$emit("cancel all requested")
    }, $scope.closeClicked = function() {
        $scope.$root.$emit("progress button clicked"), console.log("DownloadProgressController closeClicked", $scope.obj.isOpen), $scope.obj.isOpen = !1, console.log("DownloadProgressController closeClicked", $scope.obj.isOpen)
    }, $scope.cancelSingleClicked = function(item) {
        DownloadCancelService.onCancelSingle(item)
    }, $scope.hideTooltip = function() {
        $timeout(function() {
            $("#clearListButton").trigger("hide")
        }, 0)
    }
}), app.controller("FilterController", function($scope, Service, SearchModel, ViewStateModel, AnalyticsService) {
    $scope.obj = {
        filters: ["Best Match", "Popular", "Newest", "Price", "Duration"]
    }, $scope.caret = {
        direction: "down"
    }, $scope.obj.selected = $scope.obj.filters[0], $scope.onChange = function(val) {
        var sortID;
        switch (console.log("FilterController changed: ", $scope.obj.selected), $scope.obj.selected = val || $scope.obj.selected, $scope.obj.open = !1, $scope.obj.selected) {
            case "Best Match":
                sortID = 1;
                break;
            case "ARTIST":
                sortID = 2;
                break;
            case "Newest":
                sortID = 6;
                break;
            case "Duration":
                sortID = 5;
                break;
            case "Popular":
                sortID = 8;
                break;
            case "PAGE VIEWS":
                sortID = 10;
                break;
            case "Price":
                sortID = 4
        }
        console.log("FilterController  sortID: ", sortID), SearchModel.filter = sortID, SearchModel.resultType = "replace", SearchModel.page = "0", Service.search(), window.scrollTo(0, 0);
        var ga = {};
        ga.ec = "search%20filter%20" + $scope.obj.selected.replace(/ /g, "%20"), ga.label = SearchModel.query, AnalyticsService.sendData(ga)
    }, $scope.setCurrent = function(val) {
        $scope.obj.selected = val
    }, $scope.toggled = function(open) {
        $scope.obj.direction = open ? "dropup" : "down"
    }
}), app.controller("FooterLinksController", function($scope, ViewStateModel, CartModel) {
    $scope.obj = {
        show: !1
    }, $scope.viewState = function() {
        return ViewStateModel.getState()
    }, $scope.$watch($scope.viewState, function() {
        "cart" === ViewStateModel.getState() ? $scope.obj.show = !0 : $scope.obj.show = !1
    }, !0), $scope.onPromoCodeClicked = function() {
        $scope.$root.$emit("modal promo requested")
    }
});
var FreebiesController = function($scope, ViewStateService, FreebiesModel, ViewStateModel, LoginModel, AnalyticsService) {
    function onViewStateChange() {
        console.log("FreebiesController onViewStateChange:", ViewStateModel.getState()), "freebies" === ViewStateModel.getState() && LoginModel.getLoggedIn() ? $scope.obj.show = !0 : $scope.obj.show = !1
    }
    $scope.obj = {
        show: !1
    }, $scope.viewState = function() {
        return ViewStateModel.getState()
    }, $scope.loggedIn = function() {
        return LoginModel.getLoggedIn()
    }, $scope.$watch($scope.viewState, onViewStateChange, !0), $scope.$watch($scope.loggedIn, onViewStateChange), $scope.onFreebiesButtonClicked = function() {
        ViewStateService.viewRequested("freebies"), console.log("FreebiesController onFreebiesButtonClicked");
        var ga = {
            ec: "freebies"
        };
        console.log("FreebiesController ga", ga), AnalyticsService.sendData(ga)
    }, $scope.onAddAllFreebiesToCartClicked = function() {
        var ids = [];
        FreebiesModel.freebiesVO.items.forEach(function(item) {
            ids.push(item.id)
        });
        var apiObj = {
            fn: "modifyCart",
            args: [convertArrayToCommaSeperatedString(ids), ""]
        };
        $scope.$root.$emit("api call", apiObj), $scope.$root.$emit("modal add to cart")
    }
};
FreebiesController.$inject = ["$scope", "ViewStateService", "FreebiesModel", "ViewStateModel", "LoginModel", "AnalyticsService"], app.controller("ImportCollectionsController", function($scope, DownloadModel, ViewStateModel, BinsModel) {
    $scope.obj = {
        show: !1,
        isImporting: !1
    }, $scope.$root.$on("on importing bin complete", function(event) {
        console.log("ImportCollectionsController on importing bin complete"), $scope.$apply(function() {
            $scope.obj.isImporting = !1
        })
    }), $scope.viewState = function() {
        return ViewStateModel.getState()
    }, $scope.binsModel = function() {
        return BinsModel.binVO
    }, $scope.$watch($scope.viewState, function() {
        "bins" === ViewStateModel.getState() ? $scope.obj.show = !0 : $scope.obj.show = !1
    }, !0), $scope.$watch($scope.binsModel, function() {
        "bins" === ViewStateModel.getState() && ($scope.obj.show = !0, 0 < BinsModel.binVO.items.length ? $scope.obj.isImporting = !1 : $scope.obj.isImporting = !0)
    }, !0), $scope.onImportAllClicked = function() {
        $scope.obj.isImporting = !0, $scope.$root.$emit("download requested", BinsModel.binVO.items), $scope.$root.$emit("import all clicked")
    }
}), app.controller("IntroAssetsController", function($scope) {
    $scope.obj = {
        state: 0,
        stateName: ""
    }, $scope.$root.$on("intro asset requested", function(event, stateObj) {
        $scope.obj.stateName = stateObj.stateName, console.log("IntroAssetsController stateName", $scope.obj.stateName);
        var fromX, toX, fromY, toY, currArrow = stateObj.arrowClass;
        switch (currArrow) {
            case ".intro-asset-arrow-up":
                fromY = 20, toY = 0;
                break;
            case ".intro-asset-arrow-left":
                fromX = 20, toX = 0;
                break;
            case ".intro-asset-arrow-down":
                fromY = 0, toY = 20
        }
        "" != currArrow && ($(currArrow).css("top", "").css("left", "").css("bottom", ""), $(currArrow).css(stateObj.posX[0], stateObj.posX[1]), $(currArrow).css(stateObj.posY[0], stateObj.posY[1]), $(".intro-asset-arrow").velocity("stop"), $scope.loop(currArrow, fromX, toX, fromY, toY))
    }), $scope.loop = function(target, fromX, toX, fromY, toY) {
        $(target).velocity({
            translateX: [fromX, toX],
            translateY: [fromY, toY]
        }, {
            duration: 1e3,
            loop: !0
        })
    }
}), app.controller("ListItemController", function($scope, VersionsModel, ViewStateModel) {
    $scope.obj = {}, $scope.deleteIconClicked = function() {
        var apiObj = {
            fn: "modifyCart",
            args: ["", $scope.item.id]
        };
        $scope.$root.$emit("api call", apiObj)
    }, $scope.versionButtonClicked = function() {
        VersionsModel.setVersions($scope.item.versions)
    }, $scope.imageHovered = function(e) {
        var item;
        "cart" == ViewStateModel.getState() ? item = $scope.item : "downloads" == ViewStateModel.getState() && (item = $scope.item.versions[0]), $scope.$root.$emit("start preview", item)
    }, $scope.imageLeft = function(item) {
        $scope.$root.$emit("stop preview", item)
    }
}), app.controller("ListCartController", function($scope, CartModel) {
    $scope.obj = {}, $scope.cartItems = function() {
        return CartModel
    }, $scope.$watchCollection($scope.cartItems, function() {
        CartModel.cartVO && ($scope.obj.items = CartModel.cartVO.items)
    })
}), app.controller("ListDownloadsController", function($scope, PurchasesModel) {
    $scope.obj = {}, $scope.purchasedItems = function() {
        return PurchasesModel
    }, $scope.$watchCollection($scope.purchasedItems, function() {
        PurchasesModel.purchasesVO && (console.log("ListController onPurchasesModelChange: ", PurchasesModel.purchasesVO.items), $scope.obj.items = PurchasesModel.purchasesVO.items)
    })
}), app.controller("LoginController", function($scope, LoginModel, UserModel) {
    $scope.obj = {
        loggedIn: !1,
        logo: LOGO_IMG,
        logoStyle: "logo-reg"
    }, $scope.loginModel = function() {
        return LoginModel
    }, $scope.userModel = function() {
        return UserModel
    }, $scope.$watch($scope.loginModel, function() {
        void 0 === LoginModel.getLoggedIn() ? $scope.obj.loggedIn = $scope.obj.loggedIn : $scope.obj.loggedIn = LoginModel.getLoggedIn();
        $scope.obj.loggedIn && ($scope.obj.avatarURL = UserModel.getAvatarURL());
        !1 === LoginModel.getLoggedIn() || void 0 === LoginModel.getLoggedIn() ? $scope.obj.row_top_style = "row-top-loggedout" : $scope.obj.row_top_style = "row-top-loggedin"
    }, !0), $scope.$watch($scope.userModel, function() {
        $scope.obj.avatarURL = UserModel.getAvatarURL(), 0 < THIRD_PARTY.length && ($scope.obj.logo = BASE_URL + "pond5_shared/images/" + THIRD_PARTY + ".png", $scope.obj.logoStyle = "logo-tp")
    }, !0), $scope.loginRequested = function() {
        $scope.$root.$emit("modal login requested")
    }, $scope.logoutClicked = function() {
        $scope.$root.$emit("modal logout requested")
    }
}), app.controller("MainViewController", function($scope, ViewStateModel, SearchModel) {
    $scope.obj = {
        tilesClass: "main-content"
    }, $scope.$root.$on("filters button clicked", function(event, state) {
        $scope.obj.tilesClass = state ? (ViewStateModel.setState("search"), "main-content-advanced-search") : "main-content"
    }), $scope.$root.$on("advanced search close requested", function(event) {
        $scope.obj.tilesClass = "main-content"
    }), $scope.viewState = function() {
        return ViewStateModel.getState()
    }, $scope.$watch($scope.viewState, function() {
        "search" === ViewStateModel.getState() && "add" === SearchModel.resultType ? console.log("MainViewController, do not scroll to top") : window.scrollTo(0, 0);
        "cart" !== ViewStateModel.getState() && "downloads" !== ViewStateModel.getState() || ($scope.obj.tilesClass = "main-content");
        $scope.obj.state = ViewStateModel.getState()
    }, !0)
});
var MenuController = function($scope, ViewStateService, AnalyticsService) {
    $scope.states = ["default", "hover", "selected"], $scope.btn0 = {
        state: $scope.states[2],
        selected: !0
    }, $scope.btn1 = {
        state: $scope.states[0],
        selected: !1
    }, $scope.btn2 = {
        state: $scope.states[0],
        selected: !1
    }, $scope.btn3 = {
        state: $scope.states[0],
        selected: !1
    }, $scope.buttons = [$scope.btn0, $scope.btn1, $scope.btn2, $scope.btn3], $scope.click = function(button) {
        console.log("MenuController clicked ", button), $scope.selected = button;
        for (var i = 0; i < $scope.buttons.length - 1; i++) button === $scope.buttons[i] ? ($scope.buttons[i].selected = !0, $scope.buttons[i].state = $scope.states[2]) : button != $scope.buttons[3] && ($scope.buttons[i].selected = !1, $scope.buttons[i].state = $scope.states[0]);
        var view;
        switch (button) {
            case $scope.buttons[0]:
                view = "search";
                break;
            case $scope.buttons[1]:
                view = "downloads";
                break;
            case $scope.buttons[2]:
                view = "previews";
                break;
            case $scope.buttons[3]:
                view = "settings"
        }
        console.log("MenuController clicked view ", view), $scope.requestView(view)
    }, $scope.requestView = function(view) {
        "settings" === view ? $scope.$root.$emit("modal add destination requested") : ViewStateService.viewRequested(view);
        var ga = {};
        ga.ec = view, console.log("MenuController ga", ga), AnalyticsService.sendData(ga)
    }, $scope.over = function(button) {
        console.log("MenuController over ", button), button.selected || (button.state = $scope.states[1])
    }, $scope.out = function(button) {
        console.log("MenuController over ", button), button.selected || (button.state = $scope.states[0])
    }
};
MenuController.$inject = ["$scope", "ViewStateService", "AnalyticsService"], app.controller("MessageController", function($scope, ViewStateModel) {
    $scope.obj = {
        show: !1
    }, $scope.$root.$on("message view requested", function(event, show, data, list, imgUrl) {
        $scope.obj.title = null, $scope.obj.messageList = null, $scope.obj.message = null, $scope.obj.imgUrl = null, $scope.obj.showImg = !1, ($scope.obj.show = show) && ($scope.obj.title = data[0], list ? $scope.obj.messageList = data[1] : $scope.obj.message = data[1], 2 === data.length ? $scope.obj.label = "OK" : $scope.obj.label = data[2], imgUrl && ($scope.obj.imgUrl = imgUrl, $scope.obj.showImg = !0))
    }), $scope.viewStateModel = function() {
        return ViewStateModel.getState()
    }, $scope.$watch($scope.viewStateModel, function() {
        "search" !== ViewStateModel.getState() && ($scope.obj.show = !1)
    })
}), app.controller("ModalAddCollectionConfirmationController", function($scope, $uibModal, BinsModel) {
    $scope.items = [], $scope.$root.$on("collection created", function(event, data) {
        console.log("ModalAddCollectionConfirmationController event handler", data), $scope.open("sm")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_ADD_COLLECTION_CONFIRMATION_HTML,
            controller: ModalAddCollectionConfirmationInstanceCtrl,
            size: size,
            resolve: {
                items: function() {
                    return $scope
                }
            }
        }).result.then(function() {
            console.log("ModalAddCollectionConfirmationController OK")
        }, function() {
            console.log("ModalAddCollectionConfirmationController CANCELED")
        })
    }
});
var ModalAddCollectionConfirmationInstanceCtrl = function($scope, $uibModalInstance, items, BinsModel) {
    $scope.obj = {
        title: "Complete!",
        messagePre: "Your collection '",
        messagePost: "' was succesfully created",
        newBinName: BinsModel.newBinName
    }, $scope.ok = function() {
        $uibModalInstance.dismiss("cancel")
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("ModalAddCollectionController", function($scope, $uibModal, Service, UserModel, BinsModel) {
    $scope.items = [], $scope.$root.$on("modal add collection requested", function(event) {
        console.log("ModalAddCollectionController event handler"), $scope.open("sm")
    }), $scope.open = function(size) {
        var modalInstance = $uibModal.open({
            templateUrl: MODAL_ADD_COLLECTION_HTML,
            controller: ModalAddCollectionInstanceCtrl,
            size: size,
            windowClass: "modal-small",
            resolve: {
                items: function() {
                    return $scope
                }
            }
        });
        modalInstance.result.then(function() {
            console.log("ModalAddCollectionController OK")
        }, function() {
            console.log("ModalAddCollectionController CANCELED")
        }), modalInstance.result.then(function(result) {}, function(result) {})
    }
});
var ModalAddCollectionInstanceCtrl = function($scope, $uibModalInstance, items, Service, BinsModel) {
    $scope.obj = {
        showMessage: !1
    }, $scope.create = function() {
        console.log("ModalAddCollectionInstanceCtrl bin name: ", document.getElementById("addCollectionInput").value);
        var binName = document.getElementById("addCollectionInput").value;
        1 < binName.length && ($uibModalInstance.close(), BinsModel.newBinName = binName, Service.createBin(binName))
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("ModalAddToCartController", function($scope, $uibModal, Service, ViewStateService) {
    $scope.$root.$on("modal add to cart", function(event) {
        console.log("ModalAddToCartController event handler"), $scope.open("sm")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_ADD_TO_CART_HTML,
            controller: ModalAddToCartInstanceCtrl,
            size: size
        }).result.then(function() {
            console.log("ModalAddToCartController proceed"), ViewStateService.viewRequested("cart")
        }, function() {
            console.log("ModalAddToCartController later")
        })
    }
});
var ModalAddToCartInstanceCtrl = function($scope, $uibModalInstance) {
    $scope.onProceed = function() {
        console.log("ModalAddToCartInstanceCtrl onProceed"), $uibModalInstance.close()
    }, $scope.onCancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("ModalBillingAddressController", function($scope, $uibModal) {
    $scope.obj = {}, $scope.$root.$on("modal billing address requested", function(event) {
        console.log("ModalBillingAddressController event handler"), $scope.open("lg")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_BILLING_ADDRESS_HTML,
            controller: ModalBillingAddressInstanceCtrl,
            size: size,
            windowClass: "modal-billing-address",
            resolve: {
                obj: function() {
                    return $scope.obj
                }
            }
        }).result.then(function() {
            console.log("ModalBillingAddressController OK")
        }, function() {
            console.log("ModalBillingAddressController CANCELED"), $scope.$root.$emit("billing info canceled")
        })
    }
});
var ModalBillingAddressInstanceCtrl = function($scope, $uibModalInstance, obj, Service) {
    $scope.firstName = "", $scope.lastName = "", $scope.street1 = "", $scope.street2 = "", $scope.province = "", $scope.zipCode = "", $scope.city = "", $scope.state = "", $scope.country = "", $scope.error = !1, $scope.countries = COUNTRIES, $scope.states = STATES, $scope.submit = function(myForm) {
        if (console.log("ModalBillingAddressInstanceCtrl ok: ", myForm.firstName.$modelValue, myForm.lastName.$modelValue), console.log("ModalBillingAddressInstanceCtrl form valid: ", myForm.$valid), myForm.$valid) {
            var stateCode;
            stateCode = "" == myForm.state.$modelValue ? "" : myForm.state.$modelValue.code;
            var data = {
                country: myForm.country.$modelValue.code,
                firstName: myForm.firstName.$modelValue,
                lastName: myForm.lastName.$modelValue,
                organization: myForm.organization.$modelValue,
                department: myForm.department.$modelValue,
                companyID: myForm.companyID.$modelValue,
                vatID: myForm.vatID.$modelValue,
                street1: myForm.street1.$modelValue,
                street2: myForm.street2.$modelValue,
                province: myForm.province.$modelValue,
                zipCode: myForm.zipCode.$modelValue,
                city: myForm.city.$modelValue,
                state: stateCode
            };
            console.log("ModalBillingAddressInstanceCtrl DATA", data);
            var apiObj = {
                fn: "setBillingAddress",
                args: [data]
            };
            $scope.$root.$emit("api call", apiObj), $uibModalInstance.dismiss()
        } else console.log("ModalBillingAddressInstanceCtrl form is not valid"), $scope.error = !0
    }, $scope.close = function() {
        $uibModalInstance.dismiss()
    }, $scope.back = function() {
        $uibModalInstance.dismiss(), $scope.$root.$emit("on modal choose billing info requested")
    }
};
app.controller("ModalBuyCreditsController", function($scope, $uibModal, ViewStateModel) {
    $scope.obj = {}, $scope.$root.$on("modal buy credits requested", function() {
        console.log("ModalBuyCreditsController event handler"), $scope.obj.title = "", $scope.obj.message = "As a reminder, only credits purchased in $USD can be used in this Add-on.";
        $scope.open("sm")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_BUY_CREDITS_HTML,
            controller: ModalBuyCreditsInstanceCtrl,
            size: size,
            resolve: {
                obj: function() {
                    return $scope.obj
                }
            },
            windowClass: "modal-small"
        }).result.then(function() {
            console.log("ModalBuyCreditsController OK"), ViewStateModel.allowPreviews = !0, opn("https://www.pond5.com/credit-packages")
        }, function() {
            console.log("ModalBuyCreditsController CANCELED")
        })
    }
});
var ModalBuyCreditsInstanceCtrl = function($scope, $uibModalInstance, obj) {
    $scope.obj = {}, $scope.obj.message = obj.message, $scope.obj.title = obj.title, $scope.ok = function() {
        console.log("ModalBuyCreditsInstanceCtrl OK"), $uibModalInstance.close()
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel"), console.log("ModalBuyCreditsInstanceCtrl cancel")
    }
};
app.controller("ModalChooseBillingInfoController", function($scope, $uibModal, BillingInfoModel, CheckOutService, Service) {
    $scope.items = [], $scope.obj = {}, $scope.$root.$on("on modal choose billing info requested", function(event) {
        console.log("ModalChooseBillingInfoController event handler: ", BillingInfoModel.getBillingInfo()), $scope.items = BillingInfoModel.getBillingInfo(), $scope.open("lg")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_CHOOSE_BILLING_INFO_HTML,
            controller: ModalChooseBillingInfoInstanceCtrl,
            windowClass: "modal-choose-billing",
            size: size,
            resolve: {
                items: function() {
                    return $scope.items
                }
            }
        }).result.then(function(item) {
            console.log("ModalChooseBillingInfoController ok, selected: ", item.addressid), CheckOutService.onCheckOutRequested()
        }, function() {
            console.log("ModalChooseBillingInfoController dismissed"), $scope.$root.$emit("billing info canceled")
        })
    }
});
var ModalChooseBillingInfoInstanceCtrl = function($scope, $uibModalInstance, items, BillingInfoModel, Service) {
    console.log("ModalChooseBillingInfoInstanceCtrl items", items), console.log("ModalChooseBillingInfoInstanceCtrl default", BillingInfoModel.getDefaultInfo()), $scope.items = items, $scope.selected = BillingInfoModel.getDefaultInfo(), $scope.adyenEncryption = "https://plugin.pond5.com/pond5_shared/images/adyen-encryption.png", $scope.onRbClicked = function(item) {
        $scope.selected = item, console.log("ModalChooseBillingInfoInstanceCtrl rb > default", item), BillingInfoModel.setDefaultInfo(item), Service.getCartTotal()
    }, $scope.onOKClicked = function() {
        $uibModalInstance.close($scope.selected)
    }, $scope.close = function() {
        $uibModalInstance.dismiss()
    }, $scope.addNewClicked = function() {
        $uibModalInstance.dismiss(), $scope.$root.$emit("modal billing address requested")
    }, $scope.readAgreement = function() {
        console.log("ModalChooseBillingInfoInstanceCtrl readAgreement"), opn("https://www.pond5.com/legal/license")
    }, $scope.helpCenter = function() {
        opn("https://help.pond5.com/hc/en-us/")
    }, $scope.callUs = function() {
        opn("https://help.pond5.com/hc/en-us/requests/new")
    }
};
app.controller("ModalChooseFormatController", function($scope, $uibModal) {
    $scope.items = [], $scope.$root.$on("on add to cart clicked", function(event, formats) {
        console.log("ModalChooseFormatController handler, formats: ", formats), $scope.items = [], $scope.items = formats, $scope.open("sm")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_CHOOSE_FORMAT_HTML,
            controller: ModalChooseFormatInstanceCtrl,
            size: size,
            windowClass: "modal-small",
            resolve: {
                items: function() {
                    return $scope.items
                }
            }
        }).result.then(function() {}, function() {
            console.log("ModalChooseFormatController dismissed")
        })
    }
});
var ModalChooseFormatInstanceCtrl = function($scope, $uibModalInstance, items, Service) {
    $scope.items = items, $scope.items[0].selected = !0, $scope.onRbClicked = function(item, index) {
        console.log("ModalChooseFormatInstanceCtrl onRbClicked: " + item + "-" + index);
        for (var i = 0; i < $scope.items.length; i++) $scope.items[i].selected = index === i
    }, $scope.onAddToCartClicked = function() {
        for (var i = 0; i < $scope.items.length; i++)
            if ($scope.items[i].selected) {
                var item = $scope.items[i],
                    apiObj = {
                        fn: "modifyCart",
                        args: [item.id + ":" + item.offset]
                    };
                $scope.$root.$emit("api call", apiObj)
            } $uibModalInstance.dismiss()
    }
};
app.controller("ModalChooseVersionController", function($scope, $uibModal, Service, DownloadModel) {
    $scope.items = [], $scope.$root.$on("on versions selected", function(event, versions) {
        console.log("ModalChooseVersionController event handler: ", $scope.items, versions), $scope.items = [], $scope.items = versions, $scope.open("sm")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_CHOOSE_VERSION_HTML,
            controller: ModalChooseVersionInstanceCtrl,
            size: size,
            resolve: {
                items: function() {
                    return $scope.items
                }
            },
            windowClass: "modal-small"
        }).result.then(function(selectedIndex) {
            var selectedItem = $scope.items[selectedIndex];
            DownloadModel.selectedVersion = selectedIndex, Service.getPurchaseURL(selectedItem.id, selectedItem.transactionID, selectedItem.versionID, selectedItem.version)
        }, function() {
            console.log("ModalChooseVersionController dismissed")
        })
    }
});
var ModalChooseVersionInstanceCtrl = function($scope, $uibModalInstance, items) {
    $scope.items = items, $scope.selected = $scope.items[0], $scope.selectedIndex = 0, $scope.onRbClicked = function(index) {
        $scope.selected = $scope.items[index], $scope.selectedIndex = index
    }, $scope.ok = function() {
        $uibModalInstance.close($scope.selectedIndex)
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("ModalClearCartConfirmationController", function($scope, $uibModal) {
    $scope.obj = [], $scope.$root.$on("clear cart requested", function(event, data, size) {
        console.log("ModalClearCartConfirmationController event handler", data), $scope.obj.title = "Clear My Cart", $scope.obj.message = "Are you sure you want to clear your cart?", $scope.obj.itemsToDelete = data[0], $scope.obj.label = "CLEAR", $scope.obj.showButtonLeft = !0, $scope.obj.labelLeft = "CANCEL", size = size || "sm", $scope.open(size)
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_SIMPLE_HTML,
            controller: ModalClearCartConfirmationInstanceCtrl,
            size: size,
            windowClass: "modal-small",
            resolve: {
                obj: function() {
                    return $scope.obj
                }
            }
        }).result.then(function() {
            console.log("ModalClearCartConfirmationController OK");
            var apiObj = {
                fn: "modifyCart",
                args: ["", $scope.obj.itemsToDelete]
            };
            $scope.$root.$emit("api call", apiObj)
        }, function() {
            console.log("ModalClearCartConfirmationController CANCELED")
        })
    }
});
var ModalClearCartConfirmationInstanceCtrl = function($scope, $uibModalInstance, obj) {
    $scope.obj = {}, $scope.obj.message = obj.message, $scope.obj.title = obj.title, $scope.obj.label = obj.label, $scope.obj.showButtonLeft = !0, $scope.obj.labelLeft = "CANCEL", $scope.ok = function() {
        $uibModalInstance.close()
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("ModalDeleteCollectionConfirmationController", function($scope, $uibModal, Service, ViewStateModel, BinsModel, ViewStateService) {
    $scope.obj = {}, $scope.$root.$on("collection delete requested", function(event, data, size) {
        console.log("ModalDeleteCollectionConfirmationController event handler", data, data.length, size), $scope.obj.title = "Delete Collection", $scope.obj.message = "Are you sure you want to delete the collection <strong>" + data[0].name + "</strong>?", $scope.obj.bin = data[0], $scope.obj.label = "DELETE", $scope.obj.showButtonLeft = !0, $scope.obj.labelLeft = "CANCEL", size = size || "sm", $scope.open(size)
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_SIMPLE_HTML,
            controller: ModalDeleteCollectionConfirmationInstanceCtrl,
            size: size,
            windowClass: "modal-small",
            resolve: {
                obj: function() {
                    return $scope.obj
                }
            }
        }).result.then(function() {
            BinsModel.selectedBin == $scope.obj.bin && ViewStateService.viewRequested("search"), Service.removeBin($scope.obj.bin.id), ViewStateModel.allowPreviews = !0
        }, function() {})
    }
});
var ModalDeleteCollectionConfirmationInstanceCtrl = function($scope, $uibModalInstance, obj) {
    $scope.obj = {}, $scope.obj.message = obj.message, $scope.obj.title = obj.title, $scope.obj.label = obj.label, $scope.obj.showButtonLeft = !0, $scope.obj.labelLeft = "CANCEL", $scope.ok = function() {
        $uibModalInstance.close()
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("ModalFreebiesController", function($scope, $uibModal, ViewStateService) {
    $scope.$root.$on("modal freebies", function(event) {
        console.log("ModalFreebiesController event handler"), $scope.open("lg")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_FREEBIES_HTML,
            controller: ModalFreebiesInstanceCtrl,
            size: size
        }).result.then(function() {
            console.log("ModalFreebiesController OK"), ViewStateService.viewRequested("freebies")
        }, function() {
            console.log("ModalFreebiesController dismissed")
        })
    }
});
var ModalFreebiesInstanceCtrl = function($scope, $uibModalInstance) {
    $scope.ok = function() {
        $uibModalInstance.close()
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("ModalLoginController", function($scope, $uibModal) {
    $scope.obj = {}, $scope.$root.$on("modal login requested", function(event) {
        console.log("ModalLoginController event handler"), $scope.open("lg")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_LOGIN_HTML,
            controller: ModalLoginInstanceCtrl,
            size: size,
            windowClass: "modal-small",
            resolve: {
                obj: function() {
                    return $scope.obj
                }
            }
        }).result.then(function() {
            console.log("ModalLoginController OK")
        }, function() {
            console.log("ModalLoginController CANCELED")
        })
    }
});
var ModalLoginInstanceCtrl = function($scope, $uibModalInstance, obj) {
    $scope.obj = {}, $scope.obj.userName = obj.userName, $scope.obj.password = obj.password, $scope.obj.showTitle = !0, $scope.obj.showClose = !0, $scope.loginRequested = function() {
        $uibModalInstance.close();
        var apiObj = {
            fn: "login",
            args: [$scope.obj.userName, $scope.obj.password]
        };
        $scope.$root.$emit("api call", apiObj)
    }, $scope.close = function() {
        $uibModalInstance.dismiss("cancel")
    }, $scope.signUp = function() {
        opn("https://www.pond5.com/login")
    }
};
app.controller("ModalLogoutConfirmationController", function($scope, $uibModal, Service, ViewStateModel) {
    $scope.obj = {}, $scope.$root.$on("modal logout requested", function(event, data, size) {
        console.log("ModalLogoutConfirmationController event handler"), $scope.obj.title = "Log out", $scope.obj.message = "Are you sure you want to log out?", $scope.obj.label = "YES", $scope.obj.showButtonLeft = !0, $scope.obj.labelLeft = "CANCEL", size = size || "sm", $scope.open(size)
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_SIMPLE_HTML,
            controller: ModalLogoutConfirmationInstanceCtrl,
            size: size,
            windowClass: "modal-small",
            resolve: {
                obj: function() {
                    return $scope.obj
                }
            }
        }).result.then(function() {
            Service.logout(), ViewStateModel.allowPreviews = !0
        }, function() {})
    }
});
var ModalLogoutConfirmationInstanceCtrl = function($scope, $uibModalInstance, obj) {
    $scope.obj = {}, $scope.obj.message = obj.message, $scope.obj.title = obj.title, $scope.obj.label = obj.label, $scope.obj.showButtonLeft = !0, $scope.obj.labelLeft = "CANCEL", $scope.ok = function() {
        $uibModalInstance.close()
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("ModalNotLoggedInController", function($scope, $uibModal) {
    $scope.obj = {}, $scope.$root.$on("modal not logged in", function(event, data) {
        $scope.obj.title = data[0], $scope.obj.message = "You're not logged in", $scope.open("lg")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_NOT_LOGGED_IN_HTML,
            controller: ModalNotLoggedInInstanceCtrl,
            size: size,
            windowClass: "modal-small",
            resolve: {
                obj: function() {
                    return $scope.obj
                }
            }
        }).result.then(function() {
            console.log("ModalNotLoggedInController OK")
        }, function() {
            console.log("ModalNotLoggedInController CANCELED")
        })
    }
});
var ModalNotLoggedInInstanceCtrl = function($scope, $uibModalInstance, obj) {
    $scope.obj = {}, $scope.obj.message = obj.message, $scope.obj.title = obj.title, $scope.loginRequested = function() {
        $uibModalInstance.dismiss("cancel"), $scope.$root.$emit("modal login requested")
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }, $scope.signUp = function() {
        opn("https://www.pond5.com/login")
    }
};
app.controller("ModalPromoCodeController", function($scope, $uibModal, Service, UserModel) {
    $scope.items = [], $scope.obj = {
        label: "APPLY",
        onlyNumbers: /^\d+$/
    }, $scope.$root.$on("modal promo requested", function(event) {
        console.log("ModalPromoCodeController event handler"), $scope.open("sm")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_PROMO_CODE_HTML,
            controller: ModalPromoCodeInstanceCtrl,
            size: size,
            windowClass: "modal-small",
            resolve: {
                items: function() {
                    return $scope
                }
            }
        }).result.then(function() {
            console.log("ModalPromoCodeController OK")
        }, function() {
            console.log("ModalPromoCodeController CANCELED")
        })
    }
});
var ModalPromoCodeInstanceCtrl = function($scope, $uibModalInstance, items, Service, $filter) {
    $scope.obj = {
        showMessage: !1,
        label: "APPLY",
        onlyNumbers: /^\d+$/
    }, $scope.$root.$on("promo code added", function(event, data) {
        var message;
        console.log("ModalPromoCodeController event handler", data), message = data.commands[0].sum ? $filter("currency")(data.commands[0].sum) + " were succesfully added to your account!" : "Invalid code. Please try again or contact Pond5.", $scope.obj.credits = data, $scope.obj.showMessage = !0, $scope.obj.message = message, $scope.obj.label = "OK"
    }), $scope.codeApplied = function() {
        if (console.log("ModalPromoCodeInstanceCtrl codeApplied: ", document.getElementById("promoInput").value), "OK" == $scope.obj.label) $uibModalInstance.close();
        else {
            var code = document.getElementById("promoInput").value;
            1 < code.length && Service.promoRedeem(code)
        }
    }, $scope.ok = function() {
        console.log("ModalPromoCodeInstanceCtrl OK"), $uibModalInstance.close()
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("ModalRemoveCollectionController", function($scope, $uibModal, Service, BinsModel, ViewStateModel) {
    $scope.items = [], $scope.showModal = function() {
        return BinsModel.showModal
    }, $scope.$root.$on("modal remove collection requested", function(event) {
        console.log("ModalRemoveCollectionController remove collection requested event handler", BinsModel.showModal, BinsModel.clipClicked), $scope.items = BinsModel.bins, 0 < $scope.items.length && $scope.open()
    }), $scope.$root.$on("collection removed", function(event) {
        console.log("ModalAddCollectionController collection removed event handler")
    }), $scope.open = function(size) {
        var modalInstance = $uibModal.open({
            templateUrl: MODAL_REMOVE_COLLECTION_HTML,
            controller: ModalRemoveCollectionInstanceCtrl,
            windowClass: "modal-fit",
            resolve: {
                items: function() {
                    return $scope.items
                }
            }
        });
        $scope.resetBins = function() {
            BinsModel.showModal = !1;
            for (var i = 0; i < $scope.items.length; i++) $scope.items[i].selected = !1
        }, modalInstance.result.then(function() {
            console.log("OK: ", BinsModel.clipClicked, $scope.items);
            for (var i = 0; i < $scope.items.length; i++) $scope.items[i].selected && (console.log("ModalRemoveCollectionController selected bin:", $scope.items[i].id), Service.removeBin($scope.items[i].id));
            $scope.resetBins(), ViewStateModel.allowPreviews = !0
        }, function() {
            $scope.resetBins()
        })
    }
});
var ModalRemoveCollectionInstanceCtrl = function($scope, $uibModalInstance, items) {
    $scope.items = items, $scope.ok = function() {
        $uibModalInstance.close()
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("ModalReplaceController", function($scope, $uibModal, ReplaceModel, ReplaceServiceShared) {
    $scope.items = [], $scope.$root.$on("modal replace", function(event, items) {
        console.log("ModalReplaceController event handler: ", items), $scope.items = items, $scope.open("lg")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_REPLACE_HTML,
            controller: ModalReplaceInstanceCtrl,
            size: size,
            resolve: {
                items: function() {
                    return $scope.items
                }
            },
            windowClass: "modal-replace"
        }).result.then(function() {
            ReplaceServiceShared.onModalReplaceOK()
        }, function() {
            ReplaceModel.setState(DEFAULT)
        })
    }
});
var ModalReplaceInstanceCtrl = function($scope, $uibModalInstance, items) {
    $scope.obj = {
        checkIcon: "https://plugin.pond5.com/pond5_shared/images/check-icon.png",
        modalHeader: MODAL_REPLACE_HEADER,
        modalContent: MODAL_REPLACE_CONTENT,
        resTitle: MODAL_REPLACE_RES_TITLE
    }, $scope.items = items;
    for (var i = 0; i < $scope.items.length; i++) {
        $scope.items[i].selected = !0;
        for (var j = 0; j < $scope.items[i].formats.length; j++) console.log("ModalReplaceInstanceCtrl incart: ", $scope.items[i].formats[j].inDownloads), $scope.items[i].formats[j].inDownloads && ($scope.items[i].formats.length = 0), 0 < $scope.items[i].formats.length && $scope.items[i].formats[j].inCart && ($scope.items[i].formats[j].selected = !0, $scope.items[i].oneFormatInCart = !0);
        !$scope.items[i].oneFormatInCart && 0 < $scope.items[i].formats.length && ($scope.items[i].formats[0].selected = !0)
    }
    $scope.selectAllClicked = function() {
        var item;
        console.log("ModalReplaceInstanceCtrl selectAllClicked: ", $scope.obj.selectAll);
        for (var i = 0; i < $scope.items.length; i++) item = $scope.items[i], !$scope.obj.selectAll || item.inCart || item.inDownloads ? item.selected = !0 : item.selected = !1
    }, $scope.onRbClicked = function(item, index) {
        console.log("ModalReplaceInstanceCtrl onRbClicked: " + item.name + "-" + item.selected);
        for (var i = 0; i < item.formats.length; i++) item.formats[i].selected = index === i
    }, $scope.onCbClicked = function(item, index) {
        console.log("ModalReplaceInstanceCtrl onCbClicked: " + item.name + "-" + item.selected), item.selected = !item.selected;
        for (var i = 0; i < item.formats.length; i++) item.formats[i].selected = index === i;
        console.log("ModalReplaceInstanceCtrl onCbClicked after toggle: " + item.name + "-" + item.selected)
    }, $scope.ok = function() {
        $uibModalInstance.close()
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("ModalReplaceWarningController", function($scope, $uibModal, Service, DownloadModel, ViewStateService, ReplaceModel) {
    $scope.obj = {}, $scope.obj.requestedState = "", $scope.$root.$on("modal replace warning", function(event, viewState) {
        console.log("ModalReplaceWarningController event handler, event: ", event), console.log("ModalReplaceWarningController event handler, viewState: ", viewState), $scope.obj.requestedState = viewState, $scope.obj.message = "Visiting the " + viewState + " view will cancel the process of replacing your lo-res previews with hi-res clips. Are you sure you want to visit the " + viewState + " view?", $scope.open("sm")
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_REPLACE_WARNING_HTML,
            controller: ModalReplaceWarningInstanceCtrl,
            size: size,
            resolve: {
                obj: function() {
                    return $scope.obj
                }
            },
            windowClass: "modal-small"
        }).result.then(function() {
            ViewStateService.onViewApproved(!0)
        }, function() {
            console.log("ModalReplaceWarningController CANCELED"), ViewStateService.onViewApproved(!1)
        })
    }
});
var ModalReplaceWarningInstanceCtrl = function($scope, $uibModalInstance, obj) {
    $scope.obj = {}, $scope.obj.message = obj.message, $scope.ok = function() {
        $uibModalInstance.close()
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("ModalSimpleController", function($scope, $uibModal, Service, DownloadModel, ViewStateModel) {
    $scope.obj = {
        imgUrl: "",
        showImg: !1
    }, $scope.$root.$on("modal simple requested", function(event, data, size, list, imgUrl) {
        var windowClass;
        $scope.obj.title = null, $scope.obj.messageList = null, $scope.obj.message = null, $scope.obj.imgUrl = null, $scope.obj.showImg = !1, list ? $scope.obj.messageList = data[1] : $scope.obj.message = data[1], 2 === data.length ? $scope.obj.label = "OK" : $scope.obj.label = data[2], imgUrl && ($scope.obj.imgUrl = imgUrl, $scope.obj.showImg = !0), "sm" === size ? windowClass = "modal-small" : "lg" === size && (windowClass = "modal-large"), $scope.open(windowClass)
    }), $scope.open = function(size) {
        $uibModal.open({
            templateUrl: MODAL_SIMPLE_HTML,
            controller: ModalSimpleInstanceCtrl,
            windowClass: size,
            resolve: {
                obj: function() {
                    return $scope.obj
                }
            }
        }).result.then(function() {
            ViewStateModel.allowPreviews = !0
        }, function() {})
    }
});
var ModalSimpleInstanceCtrl = function($scope, $uibModalInstance, obj) {
    $scope.obj = {}, $scope.obj.message = obj.message, $scope.obj.messageList = obj.messageList, $scope.obj.title = obj.title, $scope.obj.label = obj.label, $scope.obj.imgUrl = obj.imgUrl, $scope.ok = function() {
        $uibModalInstance.close()
    }, $scope.cancel = function() {
        $uibModalInstance.dismiss("cancel")
    }
};
app.controller("PreviewAudioController", function($scope, ViewStateModel) {
    $scope.obj = {
        show: !1
    }, $scope.$root.$on("start preview", function(event, item, xpos) {
        if (("Music" == item.type || "Sound effect" == item.type) && ViewStateModel.allowPreviews) {
            var num = Number(item.dur),
                seconds = Math.floor(num / 1e3),
                minutes = Math.floor(seconds / 60);
            1 === (seconds = seconds - 60 * minutes).toString().length && (seconds = "0" + seconds);
            var format = minutes + ":" + seconds;
            $scope.obj.dur = format, item.dur || ($scope.obj.dur = ""), $scope.obj.timer = setTimeout(function() {
                document.getElementById("tracktime").style.left = "0px", $scope.playAudio(item.m4aURL, xpos), $scope.obj.name = item.abbrName, item.artistName ? $scope.obj.artist = "BY " + item.artistName.toUpperCase() : "n/a" === item.fps ? $scope.obj.artist = "" : $scope.obj.artist = item.fps, $scope.obj.iconLargeURL = item.iconLargeURL, item.priceRange && item.priceRange[0] != item.priceRange[1] ? ($scope.obj.price = "$" + item.priceRange[0] + "-$" + item.priceRange[1], $scope.obj.priceStyle = "preview-price-double") : ($scope.obj.price = "$" + item.price, $scope.obj.priceStyle = "preview-price-single"), $scope.$apply(function() {
                    $scope.obj.show = !0
                })
            }, 400)
        }
    }), $scope.$root.$on("stop preview", function(event, data) {
        data && (clearTimeout($scope.obj.timer), setTimeout(function() {
            $scope.playAudio("")
        }, 200), $scope.obj.name = "", $scope.obj.price = "", $scope.obj.type = "", $scope.obj.dur = "", $scope.obj.show = !1)
    }), $scope.playAudio = function(url, xpos) {
        var audio = document.getElementById("audio");
        document.getElementById("source-audio").setAttribute("src", url), audio.load()
    }
}), app.controller("PreviewPhotoController", function($scope, ViewStateModel) {
    $scope.obj = {
        show: !1,
        showInfo: !0
    }, $scope.$root.$on("start preview", function(event, item, xpos) {
        "Photo" != item.type && "Illustration" != item.type || ViewStateModel.allowPreviews && ($scope.obj.timer = setTimeout(function() {
            $scope.obj.name = item.abbrName, item.artistName ? $scope.obj.artist = "BY " + item.artistName.toUpperCase() : "n/a" === item.fps ? $scope.obj.artist = "" : $scope.obj.artist = item.fps, $scope.obj.vs = item.vs, $scope.obj.ar = item.ar, $scope.obj.audioCodec = item.audioCodec, $scope.obj.videoCodec = item.videoCodec, item.priceRange && item.priceRange[0] != item.priceRange[1] ? ($scope.obj.price = "$" + item.priceRange[0] + "-$" + item.priceRange[1], $scope.obj.priceStyle = "preview-price-double") : ($scope.obj.price = "$" + item.price, $scope.obj.priceStyle = "preview-price-single"), item.ox ? $scope.obj.res = item.ox + " x " + item.oy : $scope.obj.res = "", $scope.obj.type = item.type, $scope.obj.iconLargeURL = item.iconLargeURL;
            var size = convertAspectRatio(370, 208, item.aq);
            actualRatio = item.aq, targetRatio = size.x / size.y, adjustmentRatio = targetRatio / actualRatio;
            var photo = document.getElementById("photo");
            photo.width = size.x, photo.height = size.y, document.getElementById("preview-loading").style.visibility = "hidden", photo.style.position = "absolute";
            var x_pos = 185 - photo.width / 2;
            photo.style.left = x_pos + "px", $scope.obj.name = item.abbrName, item.artistName ? $scope.obj.artist = "BY " + item.artistName.toUpperCase() : "n/a" === item.fps ? $scope.obj.artist = "" : $scope.obj.artist = item.fps, $scope.obj.fps = item.fps, $scope.obj.vs = item.vs, $scope.obj.ar = item.ar, $scope.obj.audioCodec = item.audioCodec, $scope.obj.videoCodec = item.videoCodec, item.videoCodec && -1 != item.videoCodec.indexOf("Apple ProRes") && ($scope.obj.videoCodec = "Apple ProRes"), item.priceRange && item.priceRange[0] != item.priceRange[1] ? ($scope.obj.price = "$" + item.priceRange[0] + "-$" + item.priceRange[1], $scope.obj.priceStyle = "preview-price-double") : ($scope.obj.price = "$" + item.price, $scope.obj.priceStyle = "preview-price-single"), item.ox ? $scope.obj.res = item.ox + " x " + item.oy : $scope.obj.res = "", $scope.$apply(function() {
                $scope.obj.show = !0
            })
        }, 400))
    }), $scope.$root.$on("stop preview", function(event, item) {
        item && (clearTimeout($scope.obj.timer), $scope.obj.name = "", $scope.obj.price = "", $scope.obj.type = "", $scope.obj.show = !1)
    })
}), app.controller("PreviewVideoController", function($scope, ViewStateModel) {
    $scope.obj = {
        show: !1,
        timer: null,
        item: null,
        showInfo: !0
    }, $scope.$root.$on("start preview", function(event, item) {
        "Video" != item.type && "AE" != item.type || ViewStateModel.allowPreviews && ($scope.obj.timer = setTimeout(function() {
            $scope.obj.name = item.abbrName, item.artistName ? $scope.obj.artist = "BY " + item.artistName.toUpperCase() : "n/a" === item.fps && ($scope.obj.artist = ""), $scope.obj.fps = item.fps, $scope.obj.vs = item.vs, $scope.obj.ar = item.ar, $scope.obj.audioCodec = item.audioCodec, $scope.obj.videoCodec = item.videoCodec, item.videoCodec && -1 != item.videoCodec.indexOf("Apple ProRes") && ($scope.obj.videoCodec = "Apple ProRes"), item.priceRange && item.priceRange[0] != item.priceRange[1] ? ($scope.obj.price = "$" + item.priceRange[0] + "-$" + item.priceRange[1], $scope.obj.priceStyle = "preview-price-double") : ($scope.obj.price = "$" + item.price, $scope.obj.priceStyle = "preview-price-single"), item.ox ? $scope.obj.res = item.ox + " x " + item.oy : $scope.obj.res = "", $scope.$apply(function() {
                $scope.obj.show = !0
            }), $scope.playVideo(item)
        }, 400))
    }), $scope.$root.$on("stop preview", function(event, data) {
        clearTimeout($scope.obj.timer), $("#video-frame").children().filter("video").each(function() {
            this.pause(), $(this).remove()
        }), $("#video-frame").empty(), $scope.obj.name = "", $scope.obj.price = "", $scope.obj.fps = "", $scope.obj.vs = "", $scope.obj.show = !1, document.getElementById("preview-loading").style.visibility = "visible"
    }), $scope.playVideo = function(item) {
        $("#video-frame").append($("<video id='video' autoplay loop><source id='source-video' src='' type='video/mp4'></source><source id='source-video' src='' type='video/ogg'></source></video>"));
        var video = document.getElementsByTagName("video")[0],
            source = document.getElementById("source-video");
        video.style.visibility = "hidden";
        var size = convertAspectRatio(370, 208, item.aq);
        video.addEventListener("loadedmetadata", function(event) {
            video.width = size.x, video.height = size.y, document.getElementById("preview-loading").style.visibility = "hidden", video.style.visibility = "visible"
        }), item.h264URL ? (video.pause(), source.setAttribute("src", ""), source.setAttribute("src", item.h264URL), video.load()) : (source.setAttribute("src", ""), video.pause())
    }, $scope.$root.$on("preview info icon over", function() {
        $scope.obj.showInfo = !0
    }), $scope.$root.$on("preview info icon out", function() {
        $scope.obj.showInfo = !1
    })
}), app.controller("ReplaceController", function($scope, $timeout, ViewStateModel, ReplaceService, LoginModel, AnalyticsService, ReadClipsOnFSService) {
    $scope.obj = {
        show: !1,
        disabled: !1,
        buttonLabel: BUTTON_REPLACE_LABEL,
        buttonTooltip: BUTTON_REPLACE_TOOLTIP
    }, $scope.$root.$on("replacing complete", function() {
        $scope.obj.disabled = !1
    }), $scope.viewState = function() {
        return ViewStateModel.getState()
    }, $scope.$watch($scope.viewState, function() {
        "cart" != ViewStateModel.getState() ? $scope.obj.show = !0 : $scope.obj.show = !1
    }, !0), $scope.onReplaceButtonClicked = function() {
        if (LoginModel.getLoggedIn()) {
            $scope.hideTooltip(), $scope.obj.disabled = !0, ReadClipsOnFSService.listPurchasesOnFS(function() {
                console.log("DragAndDropController fs items listed, call onClipsFSCollected"), ReplaceService.onClipFSCollected()
            });
            var ga = {
                ec: "replace%20with%20hires"
            };
            AnalyticsService.sendData(ga)
        } else $scope.$root.$emit("modal not logged in", [ERROR])
    }, $scope.onReplaceButtonOver = function() {
        $timeout(function() {
            $("#replaceButton").trigger("show")
        }, 0)
    }, $scope.onReplaceButtonOut = function() {
        $scope.hideTooltip()
    }, $scope.hideTooltip = function() {
        $timeout(function() {
            $("#replaceButton").trigger("hide")
        }, 0)
    }
}), app.controller("SearchController", function($scope, ViewStateService, SearchModel, ViewStateModel, AnalyticsService) {
    $scope.obj = {
        filters: MEDIA_TYPES,
        direction: "down",
        showFilters: !1,
        view: "search",
        styleInput: "search-input-reg"
    }, $scope.viewStateModel = function() {
        return ViewStateModel.getState()
    }, $scope.$watch($scope.viewStateModel, function() {
        $scope.obj.view = ViewStateModel.getState(), 0 < THIRD_PARTY.length && ($scope.obj.styleInput = "search-input-tp")
    }, !0), resizePanel = function() {
        var numOfTotalResults = SearchModel.searchResultItems.length,
            numOfResults = SearchModel.numOfResults,
            rect = window.innerWidth * window.innerHeight;
        0 < numOfResults && numOfResults != numOfTotalResults && numOfTotalResults < rect / 25e3 && "search" == ViewStateModel.getState() && (SearchModel.isSearching || (console.log("SearchController resize, new search"), SearchModel.isSearching = !0, SearchModel.resultType = "add", SearchModel.page = SearchModel.page + 1, ViewStateService.viewRequested("search")))
    }, $scope.obj.selected = $scope.obj.filters[0], $scope.$root.$on("filters button clicked", function(event, state) {
        $scope.obj.showFilters = state
    }), $scope.filtersRequested = function() {
        $scope.obj.showFilters = !$scope.obj.showFilters, $scope.$root.$emit("filters button clicked", $scope.obj.showFilters)
    }, $scope.onChange = function(val) {
        var sortID;
        switch (console.log("SearchController onChange: ", val), $scope.obj.selected = val, $scope.obj.open = !1, $scope.obj.selected) {
            case "Footage":
                sortID = BM_VIDEO;
                break;
            case "After Effects":
                sortID = BM_AFTER_EFFECTS;
                break;
            case "Music":
                sortID = BM_MUSIC;
                break;
            case "SFX":
                sortID = BM_SFX;
                break;
            case "Public Domain":
                sortID = BM_PUBLIC_DOMAIN;
                break;
            case "Photos":
                sortID = BM_PHOTO;
                break;
            case "Illustrations":
                sortID = BM_ILLUSTRATIONS
        }
        SearchModel.sumOfBitmasks = sortID, console.log("SearchController changed, selected, bm: ", SearchModel.sumOfBitmasks), $scope.$root.$emit("media filter change", sortID), $scope.search()
    }, $scope.setCurrent = function(val) {
        $scope.obj.selected = val
    }, $scope.toggled = function(open) {
        $scope.obj.direction = open ? "dropup" : "down"
    }, $scope.search = function() {
        var query = document.getElementById("search").value;
        "Search Pond5..." === query && (query = "");
        var ga = {
            ec: "search"
        };
        ga.ea = $scope.obj.selected.replace(/ /g, "%20"), ga.el = query.replace(/ /g, "%20"), AnalyticsService.sendData(ga), SearchModel.query = query, SearchModel.resultType = "replace", SearchModel.page = 0, SearchModel.sumOfBitmasks === BM_PUBLIC_DOMAIN && (SearchModel.query = SearchModel.query + " editorial:1"), console.log("SearchController search: ", query, SearchModel.sumOfBitmasks, SearchModel.resultType, SearchModel.page), ViewStateService.viewRequested("search")
    }, $scope.searchButtonClicked = function() {
        $scope.search()
    }, $scope.enterThis = function() {
        13 === event.keyCode && $scope.search()
    }, $scope.onSearchIconClicked = function() {
        ViewStateService.viewRequested("search")
    }
});
var SellController = function($scope, AnalyticsService) {
    $scope.sellClicked = function() {
        var ga = {
            ec: "sell%20media"
        };
        console.log("SellController ga", ga), AnalyticsService.sendData(ga), opn("https://www.pond5.com/index.php?page=my_uploads")
    }
};
SellController.$inject = ["$scope", "AnalyticsService"], app.controller("SidebarController", function($scope, ViewStateModel, ViewStateService, AnalyticsService) {
    $scope.obj = {
        view: "search"
    }, $scope.viewStateModel = function() {
        return ViewStateModel.getState()
    }, $scope.$watch($scope.viewStateModel, function() {
        $scope.obj.view = ViewStateModel.getState()
    }), $scope.onDownloadsIconClicked = function() {
        $scope.$root.$emit("views requested", "downloads"), ViewStateService.viewRequested("downloads");
        var ga = {
            ec: "downloads"
        };
        AnalyticsService.sendData(ga)
    }, $scope.onPreviewsIconClicked = function() {
        ViewStateService.viewRequested("previews");
        var ga = {
            ec: "imported%20previews"
        };
        AnalyticsService.sendData(ga)
    }, $scope.onDestinationIconClicked = function() {
        $scope.$root.$emit("modal add destination requested");
        var ga = {
            ec: "add%20destination"
        };
        AnalyticsService.sendData(ga)
    }
}), app.controller("SubTopRowController", function($scope, ViewStateModel, BinsModel, SearchModel, CartModel, PurchasesModel, UserModel, AnalyticsService) {
    function onViewStateChange() {
        var title;
        switch (ViewStateModel.getState()) {
            case "downloads":
                title = "MY DOWNLOADS";
                break;
            case "previews":
                title = "MY IMPORTED PREVIEWS";
                break;
            case "cart":
                title = "MY CART";
                break;
            case "freebies":
                title = "50 FREE MEDIA CLIPS";
                break;
            case "bins":
                console.log("SubTopRowController selected bin name:", BinsModel.showBin.name), title = "COLLECTION: " + BinsModel.showBin.name;
                break;
            case "search":
                title = 0 < SearchModel.query.length ? SearchModel.query.toUpperCase() : "";
                break;
            default:
                title = ""
        }
        $scope.obj.title = title, "search" == ViewStateModel.getState() ? $scope.obj.showDropdown = !0 : $scope.obj.showDropdown = !1, "cart" == ViewStateModel.getState() ? $scope.obj.showCreditsWrapper = !0 : $scope.obj.showCreditsWrapper = !1, $scope.showClearAll()
    }
    $scope.obj = {
        showFilters: !1,
        titleClass: "sub-top-row-title-no-filters",
        showClearAll: !1,
        showDropdown: !0,
        showCreditsWrapper: !1,
        credits: 0
    }, $scope.$root.$on("on cart total", function(event) {
        $scope.obj.credits = CartModel.getCartTotal().creditsData.availableSum
    }), $scope.cartModel = function() {
        return CartModel.cartVO
    }, $scope.$watch($scope.cartModel, function() {
        $scope.showClearAll()
    }), $scope.$root.$on("bin selected", function(event) {
        onViewStateChange()
    }), $scope.viewStateModelQuery = function() {
        return SearchModel.query
    }, $scope.$watch($scope.viewStateModelQuery, onViewStateChange), $scope.viewStateModel = function() {
        return ViewStateModel.getState()
    }, $scope.$watch($scope.viewStateModel, onViewStateChange), $scope.showClearAll = function() {
        "cart" == ViewStateModel.getState() && 0 < CartModel.cartVO.items.length ? $scope.obj.showClearAll = !0 : $scope.obj.showClearAll = !1
    }, $scope.$root.$on("filters button clicked", function(event, state) {
        $scope.obj.titleClass = state ? "sub-top-row-title-filters" : "sub-top-row-title-no-filters"
    }), $scope.onClearCartClicked = function() {
        if (0 != CartModel.cartVO.items.length) {
            for (var ids = "", i = 0; i < CartModel.cartVO.items.length; i++) i < CartModel.cartVO.items.length ? ids += CartModel.cartVO.items[i].id + "," : ids += CartModel.cartVO.items[i].id;
            $scope.$root.$emit("clear cart requested", [ids])
        }
    }, $scope.buyCreditsClicked = function() {
        var ga = {
            ec: "buy%20credits"
        };
        console.log("CreditsController ga", ga), AnalyticsService.sendData(ga), $scope.$root.$emit("modal buy credits requested"), console.log("SubTopRowController button clicked")
    }
}), app.controller("TileListItemController", function($scope, Service, BinsModel, ImportedPreviewsService, ViewStateModel, LoginModel, ReplaceModel, DownloadModel) {
    $scope.childObj = {}, $scope.childObj.addedToCart = !1, $scope.childObj.addedToBin = !1, $scope.allowDownload = !0, $scope.childObj.cartClicked = !1, $scope.childObj.binClicked = !1, $scope.childObj.showEditorial = !0, $scope.childObj.viewState = "search", $scope.childObj.notification = "", "FCPX" === HOST_NAME ? $scope.childObj.importTooltip = "CLICK TO DOWNLOAD" : $scope.childObj.importTooltip = "CLICK TO IMPORT", $scope.viewState = function() {
        return ViewStateModel.getState()
    }, $scope.$watch($scope.viewState, function() {
        $scope.childObj.viewState = ViewStateModel.getState()
    }, !0), $scope.$root.$on("added to cart", function(event) {
        $scope.childObj.cartClicked && ($scope.childObj.addedToCart = !0), setTimeout(function() {
            $scope.childObj.cartClicked = !1, $scope.childObj.addedToCart = !1
        }, 1e3)
    }), $scope.$root.$on("added to bin", function(event) {
        $scope.childObj.binClicked && ($scope.childObj.addedToBin = !0), setTimeout(function() {
            $scope.childObj.binClicked = !1, $scope.childObj.addedToBin = !1
        }, 1e3)
    }), $scope.itemHovered = function(e) {
        $scope.childObj.showMenu = !0, $scope.$root.$emit("start preview", $scope.item, e.clientX)
    }, $scope.itemLeft = function() {
        $scope.childObj.showMenu = !1, $scope.$root.$emit("stop preview", $scope.item)
    }, $scope.opaqueClicked = function() {
        console.log("TileListItemController opaqueClicked", $scope.allowDownload), $scope.allowDownload && ($scope.allowDownload = !1, $scope.$root.$emit("download requested", [$scope.item]), ImportedPreviewsService.saveItem($scope.item.id), $scope.$root.$emit("stop preview", $scope.item)), setTimeout(function() {
            $scope.allowDownload = !0
        }, 2e3)
    }, $scope.overInfoIcon = function() {
        $scope.$root.$emit("preview info icon over")
    }, $scope.outInfoIcon = function() {
        $scope.$root.$emit("preview info icon out")
    }, $scope.binIconClicked = function() {
        console.log("TileListItemController binIconClicked"), LoginModel.loggedIn ? 0 < BinsModel.bins.length ? (console.log("TileListItemController binIconClicked show notification"), Service.modifyBin(BinsModel.addToBin.id, $scope.item.id), $scope.childObj.notification = "Added to the collection!", $scope.childObj.binClicked = !0, setTimeout(function() {
            $scope.childObj.binClicked = !1, $scope.childObj.addedToBin = !1
        }, 4e3), $scope.childObj.binClicked = !0) : $scope.$root.$emit("modal simple requested", ["You don't have Collections", "In order to add clips to a Collection you first need to create a Collection"]) : $scope.$root.$emit("modal not logged in", [ERROR])
    }, $scope.cartIconClicked = function() {
        $scope.childObj.notification = "Added to the cart successfully!", $scope.childObj.cartClicked = !0, setTimeout(function() {
            $scope.childObj.cartClicked = !1, $scope.childObj.addedToCart = !1
        }, 4e3), Service.getFormats($scope.item)
    }, $scope.trashIconClicked = function() {
        $scope.$root.$emit("stop preview", $scope.item), "bins" === ViewStateModel.getState() ? Service.modifyBin(BinsModel.binVO.id, "", $scope.item.id) : "previews" === ViewStateModel.getState() && ImportedPreviewsService.deleteItem($scope.item.id)
    }, $scope.linkClicked = function() {
        opn("https://www.pond5.com/item/" + $scope.item.id)
    }
}), app.controller("TileListSearchController", function($scope, SearchModel, Service) {
    $scope.obj = {
        showDeleteIcon: !1
    }, $scope.searchItems = function() {
        if (SearchModel.searchResultVO) return SearchModel.searchResultVO.items
    }, $scope.$watch($scope.searchItems, function() {
        SearchModel.searchResultVO && ($scope.obj.items = SearchModel.searchResultItems)
    })
}), app.controller("TileListPreviewsController", function($scope, PreviewsModel) {
    $scope.obj = {
        showDeleteIcon: !0
    }, $scope.previewItems = function() {
        if (PreviewsModel.previewsVO) return PreviewsModel.previewsVO.items
    }, $scope.$watch($scope.previewItems, function() {
        if (PreviewsModel.previewsVO) {
            console.log("TileListPreviewsController: ", PreviewsModel.previewsVO), PreviewsModel.previewsVO.items.reverse();
            for (var previews = PreviewsModel.previewsVO.items, nonAEpreviews = [], i = 0; i < previews.length; i++) "AE" != previews[i].type && nonAEpreviews.push(previews[i]);
            $scope.obj.items = nonAEpreviews
        }
    })
}), app.controller("TileListBinsController", function($scope, BinsModel) {
    $scope.obj = {
        showDeleteIcon: !0
    }, $scope.binItems = function() {
        if (BinsModel.binVO) return BinsModel.getBinVO()
    }, $scope.$watch($scope.binItems, function() {
        BinsModel.binVO && ($scope.obj.items = BinsModel.binVO.items)
    }, !0)
}), app.controller("TileListFreebiesController", function($scope, FreebiesModel) {
    $scope.obj = {
        showDeleteIcon: !1
    }, $scope.freeItems = function() {
        if (FreebiesModel.freebiesVO) return FreebiesModel.freebiesVO.items
    }, $scope.$watch($scope.freeItems, function() {
        FreebiesModel.freebiesVO && ($scope.obj.items = FreebiesModel.freebiesVO.items)
    })
}), app.controller("TransactionController", function($scope, ViewStateModel, ViewStateService, Service, AnalyticsService, CheckOutModel, ReplaceModel) {
    $scope.obj = {
        url: "",
        show: !1
    }, $scope.CheckOutModel = function() {
        return CheckOutModel
    }, $scope.$watch($scope.CheckOutModel, function() {
        if (CheckOutModel.checkOutURL) {
            (new Date).getTime();
            $scope.obj.url = CheckOutModel.checkOutURL, $scope.obj.show = !0, CheckOutModel.checkOutURL = "", $("body,html").css("overflow", "hidden")
        }
    }, !0), window.parent.addEventListener("message", function() {
        switch (ViewStateModel.allowPreviews = !0, console.log("TransactionController postMessage: ", event.data), event.data) {
            case "PAID":
                ReplaceModel.getState() === NOT_PURCHASED ? Service.getPurchases() : ($scope.$root.$emit("modal simple requested", PURCHASE_SUCCESSFULL), ViewStateService.viewRequested("downloads")), $scope.$root.$emit("purchase complete"), Service.getUserInfo(), console.log("TransactionController CC payment success");
                break;
            case "CANCELED":
                $scope.$root.$emit("modal simple requested", PURCHASE_CANCELED);
                break;
            default:
                $scope.$root.$emit("modal simple requested", [ERROR, "UNKNOWN"])
        }
        $scope.obj.show = !1, console.log("TransactionController onDone, show:", $scope.obj.show), $scope.$root.$emit("checkout complete"), $("body,html").css("overflow", "visible")
    }, !1)
}), app.directive("enter", function() {
    return function(scope, element, attrs) {
        element.bind("keydown", function() {
            13 === event.which && scope.$apply(attrs.enter)
        })
    }
}), app.directive("enterFooter", function() {
    return function(scope, element, attrs) {
        element.bind("mouseenter", function() {
            element.children()[0].style.color = "#ccc"
        })
    }
}), app.directive("leaveFooter", function() {
    return function(scope, element, attrs) {
        element.bind("mouseleave", function() {
            element.children()[0].style.color = "#969493"
        })
    }
}), app.directive("repositionImage", function() {
    return {
        restrict: "A",
        link: function(scope, elem, attrs) {
            elem.on("load", function() {
                108 < $(this).height() && elem.addClass("high")
            })
        }
    }
}), app.directive("rotate", function() {
    return {
        restrict: "A",
        link: function(scope, element, attrs) {
            scope.$watch(attrs.rotate, function(dir) {
                var r = "rotate(" + ("up" === dir ? 180 : 0) + "deg)";
                element.css({
                    "-webkit-transform": r
                })
            })
        }
    }
}), app.directive("whenScrolled", ["$window", "ScrollService", function($window, ScrollService) {
    return function(scope, elm, attr) {
        elm[0];
        angular.element($window).bind("scroll", function() {
            ScrollService.onScroll()
        })
    }
}]), app.directive("scrollTop", [function() {
    return {
        restrict: "A",
        link: function(scope, $elm, attr) {
            scope.$root.$on("scroll progress to top", function() {
                $elm.animate({
                    scrollTop: 0
                }, "slow")
            })
        }
    }
}]), app.directive("dragMe", function() {
    return {
        restrict: "A",
        link: function(scope, elem, attr, ctrl) {
            elem.draggable()
        }
    }
}), app.directive("onHoverInfoCart", function() {
    return {
        link: function(scope, element, attrs) {
            element.bind("mouseenter", function($event) {
                initialMouseX = $event.clientX, initialMouseY = $event.clientY, scope.$root.$emit("cart icon over", initialMouseX, initialMouseY)
            }), element.bind("mouseleave", function() {
                scope.$root.$emit("cart icon out")
            })
        }
    }
}), app.directive("onHoverPreview", function() {
    return {
        link: function(scope, element, attrs) {
            element.bind("mouseenter", function($event) {
                var previewX, previewY, tileX = element[0].getBoundingClientRect().left;
                previewX = tileX < 310 ? tileX + 220 : tileX - 400, (previewY = element[0].getBoundingClientRect().top - 200) < 20 && (previewY = 20), 340 < previewY && (previewY = 340);
                var cols = document.getElementsByClassName("preview");
                for (i = 0; i < cols.length; i++) cols[i].style.left = previewX.toString() + "px", cols[i].style.top = previewY.toString() + "px"
            })
        }
    }
}), app.filter("to_trusted", ["$sce", function($sce) {
    return function(text) {
        return $sce.trustAsHtml(text)
    }
}]), app.filter("trusted", ["$sce", function($sce) {
    return function(url) {
        return $sce.trustAsResourceUrl(url)
    }
}]), app.filter("secondsToDateTime", [function() {
    return function(seconds) {
        return new Date(1970, 0, 1).setSeconds(seconds)
    }
}]), app.directive("closeCollectionsList", function($document) {
    return {
        restrict: "A",
        link: function(scope, elem, attr, ctrl) {
            elem.bind("click", function(e) {
                e.stopPropagation()
            }), $document.bind("click", function() {
                scope.$apply(attr.closeCollectionsList)
            })
        }
    }
}), app.directive("fieldValidation", function() {
    return {
        require: "ngModel",
        link: function(scope, element, attr, mCtrl) {
            mCtrl.$parsers.push(function(value) {
                return /^\w+$/.test(value) && 1 < value.toString().length || 0 == value.toString().length ? (mCtrl.$setValidity("charE", !0), console.log("directive valid true")) : (mCtrl.$setValidity("charE", !1), console.log("directive valid false")), value
            })
        }
    }
}), app.directive("vatValidation", function() {
    return {
        require: "ngModel",
        link: function(scope, element, attr, mCtrl) {
            mCtrl.$parsers.push(function(value) {
                return /^\w+$/.test(value) && 2 < value.toString().length || 0 == value.toString().length ? (mCtrl.$setValidity("charE", !0), console.log("directive valid true")) : (mCtrl.$setValidity("charE", !1), console.log("directive valid false")), value
            })
        }
    }
}), app.directive("restrictInput", [function() {
    return {
        restrict: "A",
        link: function(scope, element, attrs) {
            var ele = element[0],
                regex = RegExp(attrs.restrictInput),
                value = ele.value;
            ele.addEventListener("keyup", function(e) {
                regex.test(ele.value) ? value = ele.value : ele.value = value
            })
        }
    }
}]), app.filter("searchFilter", function() {
    return function(input, param1) {
        if (console.log("------------------------------------------------- begin dump of custom parameters"), console.log("searchFilter input: ", input), input && input.length) {
            console.log("searchFilter param1: ", param1);
            var filteredItems = [];
            for (i = 0; i < input.length; i++) input[i].fps == param1 && filteredItems.push(input[i]);
            return filteredItems
        }
    }
}), PURCHASE_SUCCESSFULL = ["Your purchase has been successfull!", "Your items are now ready to download."], PURCHASE_CANCELED = ["Canceled.", "Purchase was canceled."], ERROR = "Oops, something went wrong...", NO_RESULTS = ["Your search returned no results", "<ul><li>Try adjusting your filters</li><li>Check your search term for misspelling or try a few synonyms</li></ul>"], BM_VIDEO = 15, BM_MUSIC = 16, BM_SFX = 32, BM_PHOTO = 128, BM_ILLUSTRATIONS = 1024, BM_AFTER_EFFECTS = 64, BM_PUBLIC_DOMAIN = 16384, MODE = "live", THIRD_PARTY = "", TARGET_APP = "", GA_TRACKING_CODE = "UA-60083218-9", DEFAULT = "not replacing", MISSING_ITEMS = "missing items", NOT_PURCHASED = "not purchased", NOT_DOWNLOADED = "not downloaded", PURCHASED_AND_DOWNLOADED = "purchased and downloaded";
var BASE_URL = "https://plugin.pond5.com/",
    NO_RESULTS_ICON = BASE_URL + "pond5_shared/images/no_results_icon.png",
    DRAGNDROP_IMG = BASE_URL + "pond5_shared/images/intro-icons/dragndrop.png",
    STATE_IMG = BASE_URL + "pond5_shared/images/intro-states/step",
    STATE_FCP_IMG = BASE_URL + "pond5_shared/images/intro-states-fcp/step",
    DOWNLOAD_IMG = BASE_URL + "pond5_shared/images/intro-icons/download.png",
    CART_IMG = BASE_URL + "pond5_shared/images/intro-icons/cart.png",
    PREVIEWS_IMG = BASE_URL + "pond5_shared/images/intro-icons/previews.png",
    DUMMY_IMG = BASE_URL + "pond5_shared/images/intro-icons/dummy.png",
    CLEAR_CART_TRASH_IMG = BASE_URL + "pond5_shared/images/clear-cart-trash-icon.png",
    CART_BUTTON_IMG = BASE_URL + "pond5_shared/images/cartButtonIcon.png",
    PROGRESS_CLOSE_IMG = BASE_URL + "pond5_shared/images/progress-close-icon.png",
    LOGO_IMG = BASE_URL + "pond5_shared/images/logo-white.png",
    MODAL_SIMPLE_HTML = BASE_URL + "pond5_shared/views/modals/modalSimple.html",
    MODAL_ADD_DESTINATION_HTML = BASE_URL + "pond5_shared/views/modals/modalAddDestination.html",
    MODAL_ADD_COLLECTION_HTML = BASE_URL + "pond5_shared/views/modals/modalAddCollection.html",
    MODAL_ADD_COLLECTION_CONFIRMATION_HTML = BASE_URL + "pond5_shared/views/modals/modalAddCollectionConfirmation.html",
    MODAL_SELECT_SEQUENCES_HTML = BASE_URL + "pond5_shared/views/modals/modalSelectSequences.html",
    MODAL_INTRO_HTML = BASE_URL + "pond5_shared/views/modals/modalIntro.html",
    MODAL_ADD_TO_CART_HTML = BASE_URL + "pond5_shared/views/modals/modalAddToCart.html",
    MODAL_BILLING_ADDRESS_HTML = BASE_URL + "pond5_shared/views/modals/modalBillingAddress.html",
    MODAL_CHOOSE_BILLING_INFO_HTML = BASE_URL + "pond5_shared/views/modals/modalChooseBillingInfo.html",
    MODAL_CHOOSE_FORMAT_HTML = BASE_URL + "pond5_shared/views/modals/modalChooseFormat.html",
    MODAL_CHOOSE_VERSION_HTML = BASE_URL + "pond5_shared/views/modals/modalChooseVersion.html",
    MODAL_FREEBIES_HTML = BASE_URL + "pond5_shared/views/modals/modalFreebies.html",
    MODAL_LOGIN_HTML = BASE_URL + "pond5_shared/views/modals/modalLogin.html",
    MODAL_NOT_LOGGED_IN_HTML = BASE_URL + "pond5_shared/views/modals/modalNotLoggedIn.html",
    MODAL_PROMO_CODE_HTML = BASE_URL + "pond5_shared/views/modals/modalPromoCode.html",
    MODAL_REMOVE_COLLECTION_HTML = BASE_URL + "pond5_shared/views/modals/modalRemoveCollection.html",
    MODAL_REPLACE_HTML = BASE_URL + "pond5_shared/views/modals/modalReplace.html",
    MODAL_REPLACE_WARNING_HTML = BASE_URL + "pond5_shared/views/modals/modalReplaceWarning.html",
    MODAL_BUY_CREDITS_HTML = BASE_URL + "pond5_shared/views/modals/modalBuyCredits.html",
    COLLECTIONS_LIST_HTML = BASE_URL + "pond5_shared/views/collectionsList.html";
$(function() {
    Offline.options = {
        checkOnLoad: !0,
        checks: {
            image: {
                url: function() {
                    return "https://plugin.pond5.com/pond5_shared/images/logo-white.png?_=" + Math.floor(1e9 * Math.random())
                }
            },
            active: "image"
        }
    }
}), app.service("AppModel", ["$rootScope", function($rootScope) {
    var path = require("path"),
        dirHomePond5 = getUserHome() + path.sep + "pond5",
        dirImports = dirHomePond5 + path.sep + "imports",
        dirPrefs = dirHomePond5 + path.sep + "prefs",
        dirDestinations = dirHomePond5 + path.sep + "destinations",
        dirDefaultLib = path.sep,
        dirUser = dirHomePond5 + path.sep + "user",
        result = (dirDefaultLib = dirHomePond5 + path.sep + "defaultLib", {
            OS: "",
            baseFolders: [],
            currentBaseFolder: "",
            previewsDir: "",
            purchasedDir: "",
            defaultLib: "",
            defaultLibName: "",
            defaultLibPath: "",
            targetApp: "",
            setEnv: function() {
                result.setOS(os.platform()), $rootScope.$emit("environment set")
            },
            getOS: function() {
                return result.OS
            },
            setOS: function(s) {
                result.OS = s
            },
            getDocumentsPath: function() {
                return os.homedir() + path.sep + "Documents"
            },
            getDirHomePond5: function() {
                return dirHomePond5
            },
            getDirImports: function() {
                return dirImports
            },
            getDirDestinations: function() {
                return dirDestinations
            },
            getDirPrefs: function() {
                return dirPrefs
            },
            getDirUser: function() {
                return dirUser
            },
            getDestinationsXML: function() {
                return result.getDirDestinations() + path.sep + "destinations.xml"
            },
            getUserXML: function() {
                return result.getDirUser() + path.sep + "user.xml"
            },
            getPreferencesXML: function() {
                return result.getDirPrefs() + path.sep + "preferences.xml"
            },
            getDirDefaultLib: function() {
                return dirDefaultLib
            },
            getDefaultLib: function() {
                return result.defaultLib
            },
            setDefaultLib: function(path) {
                "/" == path.substr(path.length - 1) && (path = path.slice(0, -1)), result.setDefaultLibName(path), result.setDefaultLibPath(path), result.defaultLib = path
            },
            getDefaultLibName: function() {
                return result.defaultLibName
            },
            setDefaultLibName: function(path) {
                var n = path.lastIndexOf("/");
                result.defaultLibName = path.substring(n + 1).replace(".fcpbundle", "")
            },
            getDefaultLibPath: function() {
                return result.defaultLibPath
            },
            setDefaultLibPath: function(path) {
                result.defaultLibPath = path.substring(0, path.lastIndexOf("/"))
            },
            getDefaultLibXML: function() {
                return result.getDirDefaultLib() + path.sep + "defaultLib.xml"
            },
            getTargetApp: function() {
                return result.targetApp
            },
            setTargetApp: function(app) {
                result.targetApp = app
            }
        });
    return result
}]), app.factory("BillingInfoModel", ["$rootScope", function($rootScope) {
    var info = {
        onBillingInfo: function(data) {
            info.setBillingInfo(data.commands[0]), info.getBillingInfo().forEach(function(item) {
                item.isdefault && info.setDefaultInfo(item)
            })
        },
        setBillingInfo: function(data) {
            info.billingInfo = data
        },
        getBillingInfo: function() {
            return info.billingInfo
        },
        setDefaultInfo: function(data) {
            info.defaultInfo = data
        },
        getDefaultInfo: function() {
            return info.defaultInfo
        }
    };
    return info
}]), app.service("BinsModel", ["$rootScope", function($rootScope) {
    var result = {
        binsVO: null,
        bins: [],
        binVO: null,
        showBin: null,
        addToBin: null,
        onBins: function(data) {
            result.binsVO = new BinsVO(data.commands[0]), result.bins = result.binsVO.bins, $rootScope.$emit("onBins")
        },
        onBin: function(data) {
            result.setBinVO(new BinVO(data.commands[0]))
        },
        onActiveBin: function(data) {
            result.bins.forEach(function(bin) {
                bin.id == data.commands[0].binid && (result.addToBin = bin)
            }), $rootScope.$emit("active bin changed", result.addToBin)
        },
        setBinVO: function(data) {
            result.binVO = data
        },
        getBinVO: function() {
            return result.binVO
        }
    };
    return result
}]);
var BinsVO = function BinsVO(data) {
        var i;
        for (this.bins = [], i = 0; i < data.bins.length; i += 1) {
            var bin = {};
            bin.name = data.bins[i].name, bin.abbrBinName = getAbbrName(bin.name, 17), bin.id = data.bins[i].id, bin.total = data.bins[i].tot, bin.selected = !1, this.bins[i] = bin
        }
        this.bins.sort(compare), BinsVO.prototype = {
            toString: function() {
                console.log("bins: " + this.bins)
            }
        }
    },
    BinVO = function BinVO(data) {
        var itemVO, i;
        this.items = [], this.id = data.binid, this.name = data.name, this.jpegBase = "http://ec.pond5.com/s3/", console.log("BinVO id: ", data.binid, data.name);
        var filterVS = 0;
        for (filterVS = "AEFT" == HOST_NAME ? 200 : 102, i = 0; i < data.items.length; i += 1) parseInt(data.items[i].vs) <= filterVS && (itemVO = new ItemVO(data.items[i], data.icon_base, data.flv_base, "", this.jpegBase), this.items.push(itemVO));
        BinVO.prototype = {
            toString: function() {
                console.log("name & id: ", this.id, this.name)
            }
        }
    };
app.factory("CartModel", ["$rootScope", "ReplaceModel", function($rootScope, ReplaceModel) {
    $rootScope.$on("on cart", function(event, data) {
        result.onCart(data)
    }), $rootScope.$on("on cart total", function(event, data) {
        result.onCartTotal(data)
    }), $rootScope.$on("formats complete", function(event, item, formats) {
        console.log("CartModel onCart ReplaceModel.getState(): ", ReplaceModel.getState()), result.onFormats(item, formats)
    });
    var result = {
        cartVO: [],
        cartTotal: null,
        onCart: function(data) {
            result.cartVO = new ItemsVO(data.commands[0])
        },
        onCartTotal: function(data) {
            result.setCartTotal(data.commands[0])
        },
        onFormats: function(item, formats) {
            if (console.log("CartModel onFormats, num of formats for id: ", item, formats.length), 1 < formats.length) {
                var uniqueResFormats = _.uniq(formats, function(p) {
                    return p.ti
                });
                $rootScope.$emit("on add to cart clicked", uniqueResFormats)
            } else {
                var apiObj = {
                    fn: "modifyCart",
                    args: [item.id, ""]
                };
                $rootScope.$emit("api call", apiObj)
            }
        },
        setCartTotal: function(data) {
            result.cartTotal = data
        },
        getCartTotal: function() {
            return result.cartTotal
        }
    };
    return result
}]), app.factory("CheckOutModel", ["$sce", function($sce) {
    var result = {
        onPurchase: function(data) {
            console.log("CheckOutModel onPurchase, url: ", data.commands[0].url);
            (new Date).getTime();
            result.checkOutURL = $sce.trustAsResourceUrl(data.commands[0].url), console.log("CheckOutModel onPurchase, url: ", result.checkOutURL)
        }
    };
    return result
}]), app.factory("DownloadModel", ["$rootScope", "PurchasesModel", "ReplaceModel", function($rootScope, PurchasesModel, ReplaceModel) {
    var result = {
        binBatch: null,
        itemsDownloadList: [],
        selectedVersion: 0,
        downloadingBatchURLs: !1,
        urlCounter: 0,
        downloadCounter: -1,
        stayAwake: !1,
        onGetPurchaseURL: function(data) {
            var item = result.getVersionByID(data.commands[0].bid);
            item && (item.hiresURL = data.commands[0].url, item.downloadType = "purchase", "AE" == item.vs && (item.type = item.vs), $rootScope.$emit("download requested", [item]))
        },
        onGetAllPurchaseURLs: function(data) {
            var i, purchase, purchases = [];
            for (ReplaceModel.getState() === DEFAULT ? purchases = PurchasesModel.purchasesVO.items : ReplaceModel.getState() === NOT_DOWNLOADED && (purchases = ReplaceModel.missingDownloads), result.urlCounter++, i = 0; i < purchases.length; i += 1) {
                purchase = purchases[i];
                var dataItem = data.commands[0];
                for (k = 0; k < purchase.formats.length; k += 1) purchase.formats[k].id == dataItem.bid && (purchase.hiresURL = dataItem.url, purchase.downloadType = "purchase");
                purchase.id == dataItem.bid && (purchase.hiresURL = dataItem.url, purchase.downloadType = "purchase", purchase.versions && 0 < purchase.versions.length && (purchase.vs = purchase.versions[0].vs))
            }
            purchases = purchases.filter(function(v, i, a) {
                return a.indexOf(v) == i
            }), result.urlCounter === purchases.length && ($rootScope.$emit("download requested", purchases), result.urlCounter = 0, result.downloadingBatchURLs = !1)
        },
        getVersionByID: function(id) {
            var foundItem;
            if (PurchasesModel.purchasesVO.items.forEach(function(item) {
                    item.id === id && (item.parentFormatID && (item.versions[result.selectedVersion].parentFormatID = item.parentFormatID), foundItem = item.versions[result.selectedVersion])
                }), foundItem) return foundItem
        }
    };
    return result
}]), app.factory("FreebiesModel", [function() {
    var result = {
        onFreebies: function(data) {
            result.freebiesVO = new ItemsVO(data.commands[0])
        }
    };
    return result
}]);
var HiresVO = function HiresVO(dest, name) {
        this.dest = dest, this.name = name, this.path = dest + name, this.id = name.split(" ")[1], this.replace = !1, this.type = "", this.nameFCP = this.name.replaceAll(" ", "%20"), this.nameFCP = this.nameFCP.replaceAll("-", "%2D"), this.nameFCP = this.nameFCP.replaceAll("&", "and"), this.pathFCP = "file://" + this.path.replaceAll(" ", "%20"), this.pathFCP = this.pathFCP.replaceAll("-", "%2D"), this.pathFCP = this.pathFCP.replaceAll("&", "and"), HiresVO.prototype = {
            toString: function() {
                return "\nHiresVO path: " + this.path + "\nname: " + this.name + "\nid: " + this.id + "\nreplace: " + this.replace
            }
        }
    },
    ItemsVO = function ItemsVO(data) {
        var itemVO, i;
        for (this.tot_nbr_rows = data.tot_nbr_rows, this.max_per_page = data.max_per_page, this.nbr_footage = data.nbr_footage, this.nbr_music = data.nbr_music, this.nbr_sfx = data.nbr_sfx, this.nbr_total = data.nbr_total, this.items = [], i = 0; i < data.items.length; i += 1) itemVO = new ItemVO(data.items[i], data.icon_base, data.flv_base, ""), this.items[i] = itemVO;
        ItemsVO.prototype = {
            toString: function() {
                console.log("vs: " + this.vs)
            }
        }
    },
    ItemVO = function ItemVO(data, iconBase, flvBase, parentID) {
        var getURL;
        this.selectedVersion = 0, this.name = data.n, this.abbrName = getAbbrName(this.name, 25), this.abbrTileName = getAbbrName(this.name, 22), this.abbrListName = getAbbrName(this.name, 40), this.artistName = getAbbrName(data.artistname, 40), this.id = data.id, this.title = data.ti, this.vr360 = data.vr360, data.pr < .001 ? this.price = "0" : this.price = data.pr, this.priceRange = data.pricerange, this.vs = getConvertedVideoStandard(data.vs), this.downloadType = "preview", this.downloadURL, this.downloadDestination = "", this.downloading = !1, this.progressPerc = "", this.progressMB = "", this.progressName = "", this.parentFormatID = "", this.canceled = !1, this.completed = !1, this.imported = !1, this.inCart = !1, this.inDownloads = !1, this.selected = !1, this.formats = [], this.versions = [], this.ox = data.ox, this.oy = data.oy, this.ar = getAspectRatio(data.ar), this.ar || (this.ar = "n/a"), this.aq = data.aq, this.dur = data.dur, data.fps ? this.fps = data.fps : this.fps = "n/a", data.ti && (this.title = data.ti), data.tb && (this.subTitle = data.tb), data.i && (this.additionalInfo = data.i), data.id ? this.id = data.id : this.id = parentID, 0 === this.id.length && (this.id = parentID), this.offset = data.so, this.transactionID = data.tr, this.expirationDate = data.exp, this.versionID = data.v, this.videoCodec = data.codg, this.audioCodec = data.coda, this.extension = data.ext, this.version = data.bitoffset, this.type = getMediaType(this.vs), this.baseURL = flvBase || "https://api-cdn.pond5.com/", getURL = function(id, type, baseURL) {
            var url;
            switch (type) {
                case "icon":
                    url = iconBase + ExtendedID.extend(id) + "_iconv.jpeg";
                    break;
                case "H264":
                    url = baseURL + ExtendedID.extend(id) + "_main_xl.mp4";
                    break;
                case "vr360":
                    url = baseURL + ExtendedID.extend(id) + "_main360.mp4";
                    break;
                case "mov":
                    url = baseURL + ExtendedID.extend(id) + "_prev_264.mov";
                    break;
                case "flv":
                    url = baseURL + ExtendedID.extend(id) + "_prev_xl.flv";
                    break;
                case "mp3":
                    url = baseURL + ExtendedID.extend(id) + "_prev.mp3";
                    break;
                case "m4a":
                    url = baseURL + ExtendedID.extend(id) + "_prev.m4a";
                    break;
                case "icon large":
                    url = iconBase + ExtendedID.extend(id) + "_iconl.jpeg"
            }
            return url
        }, this.iconURL = getURL(this.id, "icon", this.baseURL), this.iconLargeURL = getURL(this.id, "icon large", this.baseURL), this.vr360 ? this.h264URL = getURL(this.id, "vr360", this.baseURL) : this.h264URL = getURL(this.id, "H264", this.baseURL), this.mp3URL = getURL(this.id, "mp3", this.baseURL), this.m4aURL = getURL(this.id, "m4a", this.baseURL), ItemVO.prototype = {}
    };
app.factory("LoginModel", [function() {
    var data = {
        getLoggedIn: function() {
            return data.loggedIn
        },
        setLoggedIn: function(state) {
            data.loggedIn = state
        },
        getCX: function() {
            return data.cx
        },
        setCX: function(cx) {
            data.cx = cx
        },
        getCM: function() {
            return data.cm
        },
        setCM: function(cm) {
            data.cm = cm
        }
    };
    return data
}]), app.service("MissingItemsModel", [function() {
    return {
        missingItemsVO: null
    }
}]);
var MissingItemsVO = function MissingItemsVO(data) {
    var i;
    for (this.items = [], i = 0; i < data.items.length; i += 1) this.itemVO = new ItemVO(data.items[i], data.icon_base, data.flv_base), this.items[i] = this.itemVO;
    MissingItemsVO.prototype = {}
};
app.factory("PreviewsModel", [function() {
    var result = {
        onPreviews: function(data) {
            console.log("PreviewsModel onPreviews: ", data), result.previewsVO = new ItemsVO(data.commands[0])
        }
    };
    return result
}]);
var PreviewVO = function PreviewVO(dest, path) {
    var parts = (this.path = path).split("/");
    this.name = parts[parts.length - 1], this.id = this.name.split(" ")[0], PreviewVO.prototype = {
        toString: function() {
            return "\nPreviewVO path: " + this.path + "\nname: " + this.name + "\nid: " + this.id
        }
    }
};
app.service("PurchasesModel", ["$rootScope", "AnalyticsService", function($rootScope, AnalyticsService) {
    $rootScope.$on("on purchases", function(event, data) {
        result.onGetPurchases(data)
    }), $rootScope.$on("purchase complete", function(event) {
        console.log("PurchasesModel purchase complete handler"), result.sendGA = !0
    });
    var result = {
        purchasesVO: [],
        sendGA: !1,
        onGetPurchases: function(data) {
            result.purchasesVO = new PurchaseVO(data.commands[0]), $rootScope.$emit("on purchases vo", result.purchasesVO), console.log("PurchasesModel onGetPurchases result.purchasesVO: ", result.purchasesVO), result.sendGA && (AnalyticsService.sendData(result.purchasesVO, "transaction"), result.sendGA = !1)
        }
    };
    return result
}]);
var PurchaseVO = function PurchaseVO(data) {
    var i;
    this.items = [];
    for ("AEFT" == HOST_NAME ? 200 : 102, i = 0; i < data.items.length; i += 1) {
        var j;
        for (this.itemVO = new ItemVO(data.items[i], data.icon_base, data.flv_base, data.items[i].bid), this.itemVO.transactionID = data.items[i].versions[0].tr, this.itemVO.name = data.items[i].versions[0].n, this.itemVO.abbrName = getAbbrName(this.itemVO.name, 30), this.itemVO.expirationDate = data.items[i].versions[0].exp, this.itemVO.parentFormatID = data.items[i].versions[0].vm, this.itemVO.type = getMediaType(getConvertedVideoStandard(data.items[i].versions[0].vs)), this.itemVO.aq = data.items[i].versions[0].aq, this.itemVO.versionID = data.items[i].versions[0].v, this.itemVO.version = data.items[i].versions[0].bitoffset, j = 0; j < data.items[i].versions.length; j += 1) this.itemVO.versions[j] = new ItemVO(data.items[i].versions[j], data.icon_base, data.flv_base, data.items[i].bid);
        this.items.push(this.itemVO)
    }
    PurchaseVO.prototype = {
        toString: function() {
            console.log("name & id: ", this.items)
        }
    }
};

function checkNested(obj) {
    for (var args = Array.prototype.slice.call(arguments), i = (obj = args.shift(), 0); i < args.length; i++) {
        if (!obj.hasOwnProperty(args[i])) return !1;
        obj = obj[args[i]]
    }
    return !0
}

function compare(a, b) {
    return a.name < b.name ? -1 : a.name > b.name ? 1 : 0
}

function sortArgs() {
    return Array.prototype.slice.call(arguments, 0).sort()[0]
}

function getAspectRatio(as) {
    var standard;
    switch (as) {
        case 1:
            standard = "4:3";
            break;
        case 2:
            standard = "16:9 anamorphic";
            break;
        case 3:
            standard = "16:9 letterboxed";
            break;
        case 4:
            standard = "n/a";
            break;
        case 5:
            standard = "Other";
            break;
        case 6:
            standard = "16:9 native"
    }
    return standard
}

function convertAspectRatio($max_x, $max_y, $aspect_quotient) {
    var $out_x, $out_y;
    return $aspect_quotient ? ($out_y = $max_y, $max_x < ($out_x = Math.round($max_y * parseFloat($aspect_quotient))) && ($out_x = $max_x, $out_y = Math.round($max_x / parseFloat($aspect_quotient))), new Point($out_x, $out_y)) : ($out_x = $max_x, $out_y = $max_y, new Point(370, 208))
}
app.factory("ReplaceModel", ["$rootScope", function($rootScope) {
    var result = {
        clipsInSequences: [],
        aeItemsinProjectView: [],
        state: DEFAULT,
        missingDownloads: [],
        hiresOnFS: [],
        previewsOnFS: [],
        sequences: [],
        setState: function(newState) {
            result.state = newState, console.log("ReplaceModel STATE:", result.state), result.state === DEFAULT && $rootScope.$root.$emit("replacing complete")
        },
        getState: function() {
            return result.state
        },
        getAEItems: function() {
            return result.aeItemsinProjectView
        },
        setAEItems: function(items) {
            result.aeItemsinProjectView = items
        },
        setSequenceNames: function(seqNames) {
            result.sequences = [];
            for (var i = 0; i < seqNames.length; i++) {
                var obj = {
                    name: seqNames[i],
                    checked: !1
                };
                result.sequences[i] = obj
            }
            0 < seqNames.length ? $rootScope.$root.$emit("modal select sequences", result.sequences) : ($rootScope.$root.$emit("modal simple requested", ["Replace With Hi-Res Clips - Warning", "The 'Replace With Hi-Res clips' button replaces lo-res previews with hi-res clips that you have purchased and downloaded.<BR><BR>There are currently no sequences in your project."]), result.setState(DEFAULT))
        },
        setSequences: function(sequences) {
            result.sequences = [];
            for (var i = 0; i < sequences.length; i++) sequences[i].checked = !1;
            var newArray = [];
            newArray.push(sequences[0]);
            for (i = 1; i < sequences.length; i++) {
                for (var j = 0; j < newArray.length; j++) newArray[j].name === sequences[i].name && (console.log("already exists ", i, j, sequences[i].name), 0, sequences[i].name = sequences[i].name + "  (id: " + sequences[i].id + ")");
                newArray.push(sequences[i])
            }
            result.sequences = newArray, console.log("ReplaceModel, sequences:", result.sequences), 0 < sequences.length ? $rootScope.$root.$emit("modal select sequences", result.sequences) : ($rootScope.$root.$emit("modal simple requested", ["Replace With Hi-Res Clips - Warning", "The 'Replace With Hi-Res clips' button replaces lo-res previews with hi-res clips that you have purchased and downloaded.<BR><BR>There are currently no sequences in your project."]), result.setState(DEFAULT))
        },
        setComps: function(comps) {
            result.sequences = comps, $rootScope.$root.$emit("modal select comps", result.sequences)
        },
        addHires: function(dest, files) {
            for (var hiresVO, i = 0; i < files.length; i += 1)(hiresVO = new HiresVO(dest, files[i].fileName)).type = files[i].vs, hiresVO.replace = !0, result.hiresOnFS.push(hiresVO)
        }
    };
    return result
}]), app.service("SearchModel", ["$rootScope", function($rootScope) {
    var result = {
        allowInfiniteScroll: !1,
        searchResultItems: [],
        numOfResults: 0,
        onSearch: function(data) {
            result.searchResultVO = new ItemsVO(data.commands[0]), result.numOfResults = data.commands[0].nbr_footage + data.commands[0].nbr_music + data.commands[0].nbr_sfx + data.commands[0].nbr_ae, console.log("SearchModel onSearch num of results: ", result.numOfResults), "replace" === result.resultType && (result.searchResultItems = [], window.scrollTo(0, 0), 0 === result.numOfResults ? $rootScope.$emit("message view requested", !0, NO_RESULTS, !0, NO_RESULTS_ICON) : $rootScope.$emit("message view requested", !1));
            for (var i = 0; i < result.searchResultVO.items.length; i++) result.searchResultItems.push(result.searchResultVO.items[i]);
            result.isSearching = !1, resizePanel()
        },
        sumOfBitmasks: "",
        query: "",
        filter: "1",
        resultType: "replace",
        page: 0,
        isSearching: !1,
        filteredItems: [],
        fps: "",
        fpsgt: "",
        res: "",
        pricegt: "",
        pricelt: "",
        durationgt: "",
        durationlt: ""
    };
    return result
}]), app.factory("UserModel", [function() {
    var firstTimeUser = !0,
        user = {
            onUserInfo: function(data) {
                user.setCredits(data.credit), user.setUserName(data.un), user.setFirstName(data.fn), user.setLastName(data.ln), user.setAvatarURL(data.icon_base, data.av)
            },
            setCredits: function(num) {
                user.credits = num
            },
            getCredits: function() {
                return user.credits
            },
            setUID: function(uid) {
                user.uid = uid
            },
            getUID: function() {
                return user.uid
            },
            setCM: function(cm) {
                user.cm = cm
            },
            getCM: function() {
                return user.cm
            },
            setCX: function(cx) {
                user.cx = cx
            },
            getCX: function() {
                return user.cx
            },
            setUserName: function(name) {
                user.userName = name
            },
            getUserName: function() {
                return user.userName
            },
            setFirstName: function(name) {
                user.firstName = name
            },
            getFirstName: function() {
                return user.firstName
            },
            setLastName: function(name) {
                user.lastName = name
            },
            getLastName: function() {
                return user.lastName
            },
            setAvatarURL: function(base, url) {
                user.avatarURL = base + url
            },
            getAvatarURL: function() {
                return user.avatarURL
            },
            setFirstTimeUser: function(state) {
                firstTimeUser = state
            },
            getFirstTimeUser: function() {
                return firstTimeUser
            }
        };
    return user
}]), app.factory("VersionsModel", ["$rootScope", function($rootScope) {
    var result = {
        versions: [],
        setVersions: function(v) {
            result.versions = [];
            for (var i = 0; i < v.length; i++) result.versions[i] = v[i];
            $rootScope.$emit("on versions selected", result.versions)
        },
        getVersions: function() {
            return result.versions
        }
    };
    return result
}]), app.factory("ViewStateModel", ["$rootScope", "SearchModel", function($rootScope, SearchModel) {
    var state;
    return {
        allowPreviews: !1,
        setState: function(s) {
            state = s, SearchModel.allowInfiniteScroll = "search" === state || ($rootScope.$emit("filters button clicked", !1), !1)
        },
        getState: function() {
            return state
        }
    }
}]), app.service("AnalyticsService", ["$http", "$rootScope", "UserModel", "CartModel", function($http, $rootScope, UserModel, CartModel) {
    var result = {
        sendData: function(data, type) {
            GA_TRACKING_CODE,
            UserModel.getUID(),
            UserModel.getUID(),
            HOST_NAME,
            PLUGIN_VERSION
        },
        send: function(payload) {
            $http({
                method: "POST",
                url: payload
            }).then(function(response) {
                console.log("AnalyticsService then: ", response)
            }, function(response) {
                console.log("AnalyticsService error: ", response)
            })
        }
    };
    return result
}]), app.service("Service", ["$rootScope", "APIService", "LoginModel", "UserModel", "SearchModel", "FreebiesModel", "BinsModel", "ViewStateModel", "DownloadModel", "CheckOutModel", "PreviewsModel", "ReplaceModel", "ViewStateService", "ImportedPreviewsService", "AnalyticsService", "UserService", "BillingInfoModel", function($rootScope, APIService, LoginModel, UserModel, SearchModel, FreebiesModel, BinsModel, ViewStateModel, DownloadModel, CheckOutModel, PreviewsModel, ReplaceModel, ViewStateService, ImportedPreviewsService, AnalyticsService, UserService, BillingInfoModel) {
    $rootScope.$on("api call", function(event, apiObj) {
        call[apiObj.fn](sortArgs(apiObj.args))
    });
    var call = {
        login: function() {
            var obj = [{
                command: "login",
                username: arguments[0][0],
                password: arguments[0][1]
            }];
            APIService.call(obj).then(function(data) {
                LoginModel.setLoggedIn(!0), LoginModel.setCX(data.commands[0].cx), LoginModel.setCM(data.commands[0].cm), UserService.saveData(data.commands[0].cx, data.commands[0].cm), call.getUserInfo()
            }).catch(function(err) {})
        },
        logout: function() {
            console.log("Service logout");
            APIService.call([{
                command: "logout"
            }]).then(function(data) {
                LoginModel.setLoggedIn(!1)
            }).catch(function(err) {})
        },
        getUserInfo: function() {
            APIService.call([{
                command: "userinfo"
            }]).then(function(data) {
                "" != data.commands[0].uid && (UserModel.onUserInfo(data.commands[0]), call.getBins(), setTimeout(function() {
                    call.getCart()
                }, 1e3), call.getActiveBin(), call.getBillingAddresses(), LoginModel.getLoggedIn() || LoginModel.setLoggedIn(!0))
            }).catch(function(err) {})
        },
        search: function() {
            var obj = [{
                command: "search",
                query: SearchModel.query + SearchModel.res + SearchModel.fps + SearchModel.fpsgt + SearchModel.pricegt + SearchModel.pricelt + SearchModel.durationgt + SearchModel.durationlt,
                sb: SearchModel.filter,
                bm: SearchModel.sumOfBitmasks,
                no: "25",
                p: SearchModel.page,
                col: "1523"
            }];
            APIService.call(obj).then(function(data) {
                SearchModel.onSearch(data), ViewStateModel.allowPreviews = !0
            }).catch(function(err) {})
        },
        getFreeClips: function() {
            APIService.call([{
                command: "get_free_clips"
            }]).then(function(data) {
                FreebiesModel.onFreebies(data)
            }).catch(function(err) {})
        },
        getCart: function() {
            APIService.call([{
                command: "get_cart_formatted",
                artistinfo: "1"
            }]).then(function(data) {
                console.log("Service getCart data", data), $rootScope.$emit("on cart", data)
            }).catch(function(err) {})
        },
        getCartTotal: function() {
            var obj = [{
                command: "get_cart_total",
                addressid: BillingInfoModel.getDefaultInfo() ? BillingInfoModel.getDefaultInfo().addressid : "",
                use_credits: "1"
            }];
            APIService.call(obj).then(function(data) {
                $rootScope.$emit("on cart total", data)
            }).catch(function(err) {})
        },
        getBillingAddresses: function(setState) {
            APIService.call([{
                command: "get_billing_addresses"
            }]).then(function(data) {
                BillingInfoModel.onBillingInfo(data), setState && $rootScope.$emit("on modal choose billing info requested"), call.getCartTotal()
            }).catch(function(err) {})
        },
        setBillingAddress: function(info) {
            console.log("Service setBillingAddresses obj:", info);
            var data = info[0];
            data.addressID || (data.addressID = "");
            var obj = [{
                command: "set_billing_address",
                country: data.country,
                addressid: data.addressID,
                first_name: data.firstName,
                last_name: data.lastName,
                company_name: data.organization,
                company_department: data.department,
                company_id: data.companyID,
                vat_id: data.vatID,
                street1: data.street1,
                street2: data.street2,
                city: data.city,
                state: data.state,
                province: data.province,
                postal_code: data.zipCode
            }];
            APIService.call(obj).then(function(data) {
                call.getBillingAddresses(!0)
            }).catch(function(err) {})
        },
        getBins: function() {
            APIService.call([{
                command: "get_bins"
            }]).then(function(data) {
                BinsModel.onBins(data)
            }).catch(function(err) {})
        },
        getActiveBin: function() {
            APIService.call([{
                command: "get_active_bin"
            }]).then(function(data) {
                BinsModel.onActiveBin(data)
            }).catch(function(err) {})
        },
        setActiveBin: function(id) {
            var obj = [{
                command: "set_active_bin",
                binid: id
            }];
            APIService.call(obj).then(function(data) {
                setTimeout(function() {
                    call.getActiveBin()
                }, 1e3)
            }).catch(function(err) {})
        },
        getBin: function() {
            var obj = [{
                command: "get_bin_formatted",
                binid: BinsModel.showBin.id
            }];
            APIService.call(obj).then(function(data) {
                BinsModel.onBin(data)
            }).catch(function(err) {})
        },
        modifyBin: function(binID, addID, rmID) {
            var obj = [{
                command: "modify_active_bin",
                binid: binID,
                addid: addID,
                rmid: rmID
            }];
            APIService.call(obj).then(function(data) {
                "1" == data.commands[0].nbr_removed ? call.getBin(BinsModel.binVO.id) : $rootScope.$emit("added to bin")
            }).catch(function(err) {})
        },
        createBin: function(binName) {
            var obj = [{
                command: "create_bin",
                name: binName
            }];
            APIService.call(obj).then(function(data) {
                BinsModel.newBinName;
                call.setActiveBin(data.commands[0].binid), call.getBins()
            }).catch(function(err) {})
        },
        removeBin: function(id) {
            var obj = [{
                command: "delete_bin",
                binid: id
            }];
            APIService.call(obj).then(function(data) {
                call.getBins(), $rootScope.$emit("collection removed", data)
            }).catch(function(err) {})
        },
        getPurchases: function() {
            APIService.call([{
                command: "get_downloads_formatted"
            }]).then(function(data) {
                console.log("Service getPurchases data", data), $rootScope.$emit("on purchases", data)
            }).catch(function(err) {})
        },
        getPurchaseURL: function(itemID, transactionID, versionID, version) {
            console.log("Service getPurchaseURL", itemID, transactionID, versionID, version);
            var obj = [{
                command: "download",
                bid: itemID,
                tr: transactionID,
                v: versionID,
                bitoffset: version
            }];
            APIService.call(obj).then(function(data) {
                console.log("Service getPurchaseURL data", data), DownloadModel.downloadingBatchURLs ? DownloadModel.onGetAllPurchaseURLs(data) : DownloadModel.onGetPurchaseURL(data)
            }).catch(function(err) {})
        },
        modifyCart: function() {
            var obj = [{
                command: "modify_active_cart",
                addid: arguments[0][0],
                rmid: arguments[0][1]
            }];
            APIService.call(obj).then(function(data) {
                1 === data.commands[0].nbr_added && $rootScope.$emit("added to cart"), call.getCart(), call.getCartTotal()
            }).catch(function(err) {})
        },
        purchaseWithCredits: function(buyAnyway, userData) {
            var obj = [{
                command: "purchase_using_credits",
                override: buyAnyway,
                userdata: userData,
                addressid: BillingInfoModel.getDefaultInfo().addressid
            }];
            APIService.call(obj).then(function(data) {
                console.log("purchaseWithCredits data", data), ReplaceModel.getState() === DEFAULT && $rootScope.$emit("modal simple requested", ["Your purchase has been successful!", "Your items are now ready to download."]), $rootScope.$emit("purchase complete"), ReplaceModel.getState() === NOT_PURCHASED ? call.getPurchases() : ViewStateService.viewRequested("downloads"), call.getUserInfo()
            }).catch(function(err) {})
        },
        purchaseWithCash: function(buyAnyway, userData) {
            var obj = [{
                command: "purchase_using_cash",
                AdobePremierePlugin: "html",
                override: buyAnyway,
                userdata: userData,
                addressid: BillingInfoModel.getDefaultInfo().addressid,
                use_credits: "1"
            }];
            APIService.call(obj).then(function(data) {
                console.log("Service purchaseWithCash data", data), CheckOutModel.onPurchase(data)
            }).catch(function(err) {})
        },
        promoRedeem: function(code) {
            var obj = [{
                command: "promo_redeem",
                promocode: code
            }];
            APIService.call(obj).then(function(data) {
                call.getUserInfo(), $rootScope.$emit("promo code added", data)
            }).catch(function(err) {})
        },
        getImportedPreviews: function() {
            console.log("Service getImportedPreviews", ImportedPreviewsService.idsString);
            var obj = [{
                command: "get_clip_data_array",
                itemids: ImportedPreviewsService.idsString,
                col: "1523",
                verboselvl: "100"
            }];
            APIService.call(obj).then(function(data) {
                PreviewsModel.onPreviews(data)
            }).catch(function(err) {})
        },
        getFormats: function(item) {
            console.log("Service getFormats", item.id);
            var obj = [{
                command: "get_versions_formatted",
                vm: item.id
            }];
            APIService.call(obj).then(function(data) {
                console.log("Service getFormats data", data);
                var formats = data.commands[0].items;
                $rootScope.$emit("formats complete", item, formats)
            }).catch(function(err) {})
        },
        getFormatsReplacing: function(item) {
            console.log("Service getFormatsReplacing", item.id);
            var obj = [{
                command: "get_versions_formatted",
                vm: item.id
            }];
            APIService.call(obj).then(function(data) {
                console.log("Service getFormatsReplacing data", data);
                var formats = data.commands[0].items;
                $rootScope.$emit("formats replacing complete", item, formats)
            }).catch(function(err) {})
        },
        getMissingItems: function(itemIDsString) {
            console.log("Service getMissingItems itemIDsString", itemIDsString);
            var obj = [{
                command: "get_clip_data_array",
                itemids: itemIDsString,
                col: "1523",
                verboselvl: "100"
            }];
            APIService.call(obj).then(function(data) {
                ReplaceModel.setState(MISSING_ITEMS), console.log("Service getMissingItems data", data), $rootScope.$emit("missing items complete", data)
            }).catch(function(err) {})
        }
    };
    return call
}]), app.factory("APIService", ["$http", "ViewStateModel", "LoginModel", function($http, ViewStateModel, LoginModel) {
    return {
        call: function(data) {
            ViewStateModel.allowPreviews = !1;
            var url, secret, apiKey, _0xf310 = ["test", "https://test.pond5.com/?page=api", "live", "https://www.pond5.com/?page=api", "oi23Jan3Inwh2io", "220655_769351580"];
            MODE === _0xf310[0] ? API_URL = _0xf310[1] : MODE === _0xf310[2] && (API_URL = _0xf310[3]), API_SECRET = _0xf310[4], API_KEY = _0xf310[5], url = API_URL, secret = API_SECRET, apiKey = API_KEY;
            var stringified = JSON.stringify(data),
                md5target = stringified + secret + "dragspel",
                md5tostring = CryptoJS.MD5(md5target).toString(),
                cx = LoginModel.getCX(),
                cm = LoginModel.getCM(),
                dataObj = {
                    api_key: apiKey,
                    commands_json: stringified,
                    commands_hash: md5tostring,
                    ver: 1,
                    https: 1
                },
                jsnstr = JSON.stringify(dataObj);
            return $http({
                url: url,
                method: "POST",
                data: "api=" + jsnstr + "&apicx=" + cx + "&apicm=" + cm,
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            }).then(function(result) {
                return ViewStateModel.allowPreviews = !0, result.data
            })
        }
    }
}]), app.factory("myHttpInterceptor", ["$q", "$rootScope", "ViewStateModel", function($q, $rootScope, ViewStateModel) {
    return {
        response: function(response) {
            var errorFree = !0;
            return "POST" === response.config.method && (response.data.e ? (console.log("Apiservice myHttpInterceptor error >>>", response.data), errorFree = !1) : response.data.commands && response.data.commands.forEach(function(entry) {
                if (entry && entry.hasOwnProperty("e")) {
                    if (response.config.data && -1 != response.config.data.indexOf("userinfo")) console.log("myHttpInterceptor user info, do not show alert ", response);
                    else if (103 === response.data.commands[0].c) response.data.commands[0].a && (console.log("APIService myHttpInterceptor alreadyBought or onwClips", response.data.commands[0].a), 0 < response.data.commands[0].a.bought_before.length && ($rootScope.$emit("alreadyBought", response.data.commands[0].a.bought_before), console.log("APIService myHttpInterceptor alreadyBought", response.data.commands[0].a.bought_before)), 0 < response.data.commands[0].a.ownClips.length && ($rootScope.$emit("ownClips", response.data.commands[0].a.ownClips), console.log("APIService myHttpInterceptor ownClips", response.data.commands[0].a.ownClips)));
                    else {
                        console.log("myHttpInterceptor modal simple requested :", entry), "You are not logged in" == entry.s.split(": ")[1] ? $rootScope.$emit("modal not logged in", [ERROR]) : $rootScope.$emit("modal simple requested", [ERROR, entry.s.split(": ")[1]])
                    }
                    errorFree = !1
                }
            })), errorFree ? response : $q.reject(response)
        },
        responseError: function(response) {
            return response.config.url == MODAL_INTRO_HTML || response.config.url == MODAL_CHOOSE_BILLING_INFO_HTML ? console.log("apiService don't show error modal for ", response.config.url) : ($rootScope.$emit("modal simple requested", [ERROR, response.headers().status]), console.log("apiService don't show error modal but response ", response)), $q.reject(response)
        }
    }
}]), app.config(function($httpProvider) {
    $httpProvider.interceptors.push("myHttpInterceptor")
}), app.service("CheckOutService", ["CartModel", "UserModel", "Service", function(CartModel, UserModel, Service) {
    this.onCheckOutRequested = function(buyAnyway) {
        console.log("CheckOutService total before VAT: ", CartModel.cartTotal.subtotals.afterVat), console.log("CheckOutService credits: ", CartModel.cartTotal.creditsData.availableSum), console.log("CheckOutService buyAnyway: ", buyAnyway), CartModel.cartTotal.creditsData.availableSum < CartModel.cartTotal.subtotals.afterVat ? Service.purchaseWithCash(buyAnyway) : Service.purchaseWithCredits(buyAnyway)
    }
}]), app.service("CreateOnFileSystemService", ["AppModel", "CreateFileCompleteService", function(AppModel, CreateFileCompleteService) {
    var call = {
        createUserHomeFolder: function() {
            call.createDir(AppModel.getDirHomePond5())
        },
        createUserSubFolders: function() {
            console.log("CreateOnFileSystemService createUserSubFolders", AppModel.getDirDefaultLib());
            for (var dirs = [AppModel.getDirImports(), AppModel.getDirPrefs(), AppModel.getDirDefaultLib(), AppModel.getDirDestinations(), AppModel.getDirUser()], i = 0; i < dirs.length; i++) {
                var dir = dirs[i];
                call.createDir(dir)
            }
        },
        createDestinationBaseFolder: function() {
            call.createDir(AppModel.currentBaseFolder + path.sep + "pond5", !0)
        },
        createDestinationFolders: function() {
            AppModel.previewsDir = AppModel.currentBaseFolder + path.sep + "pond5" + path.sep + "previews", AppModel.purchasedDir = AppModel.currentBaseFolder + path.sep + "pond5" + path.sep + "purchased", call.createDir(AppModel.previewsDir), call.createDir(AppModel.purchasedDir)
        },
        createDir: function(dir, isDestination) {
            fs.exists(dir, function(exists) {
                exists ? call.onDirReady(dir, isDestination) : fs.mkdir(dir, 511, function(err) {
                    if (err) throw err;
                    call.onDirReady(dir, isDestination)
                })
            })
        },
        onDirReady: function(dir, isDestination) {
            if (isDestination = isDestination || !1) this.createDestinationFolders();
            else {
                var filePath, xml;
                switch (dir) {
                    case AppModel.getDirHomePond5():
                        call.createUserSubFolders();
                        break;
                    case AppModel.getDirImports():
                        filePath = "imported_previews.xml", xml = '<root><previews ids=""/></root>';
                        break;
                    case AppModel.getDirPrefs():
                        filePath = "preferences.xml", xml = '<root><prefs target="none"/></root>';
                        break;
                    case AppModel.getDirUser():
                        filePath = "user.xml", xml = '<root><user cm="" cx="" /></root>';
                        break;
                    case AppModel.getDirDestinations():
                        filePath = "destinations.xml", xml = '<root PPRO="init" AEFT="init" FCPX="init" AUDT="init" id="' + getUID() + '"><destinations></destinations></root>';
                        break;
                    case AppModel.getDirDefaultLib():
                        filePath = "defaultLib.xml", xml = '<root><defaultLib path=""/></root>';
                        break;
                    case AppModel.currentBaseFolder:
                        this.createDestinationFolders();
                        break;
                    default:
                        return
                }
                filePath && call.createFile(dir + path.sep + filePath, '<?xml version="1.0" encoding="UTF-8"?>' + xml)
            }
        },
        createFile: function(file, content) {
            fs.exists(file, function(exists) {
                exists ? CreateFileCompleteService.onFileReady(file) : fs.writeFile(file, content, function(err) {
                    if (err) throw err;
                    console.log("CreateOnFileSystemService, created file: ", file), CreateFileCompleteService.onFileReady(file)
                })
            })
        }
    };
    return call
}]), app.service("DeleteOnFileSystemService", [function() {
    return {
        deleteFiles: function(items) {
            items.forEach(function(item) {
                var file = item.downloadDestination + item.fileName;
                fs.exists(file, function(exists) {
                    exists && fs.unlink(file, function(err) {
                        if (err) throw err
                    })
                })
            })
        },
        deleteFolder: function(folders, cb) {
            console.log("DeleteOnFileSystemService deleteFolder, folders, length:", folders.length), folders.forEach(function(folder) {
                console.log("DeleteOnFileSystemService deleteFolder, folder:", folder), fs.exists(folder, function(exists) {
                    exists ? rimraf(folder, function(err) {
                        if (err) throw err;
                        console.log("DeleteOnFileSystemService deleteFolder deleted: ", folder), cb()
                    }) : (console.log("DeleteOnFileSystemService deleteFile folder does not exist:", folder), cb())
                })
            })
        }
    }
}]), app.factory("DownloadBatchService", ["Service", "PurchasesModel", "DownloadModel", function(Service, PurchasesModel, DownloadModel) {
    return {
        onBatchRequested: function(purchases) {
            var j, i;
            for (purchases = purchases || PurchasesModel.purchasesVO.items, i = 0; i < purchases.length; i += 1)
                for (j = 0; j < PurchasesModel.purchasesVO.items.length; j += 1) purchases[i].id == PurchasesModel.purchasesVO.items[j].id && (purchases[i] = PurchasesModel.purchasesVO.items[j]);
            for (DownloadModel.downloadingBatchURLs = !0, purchases = purchases.filter(function(v, i, a) {
                    return a.indexOf(v) == i
                }), i = 0; i < purchases.length; i += 1) Service.getPurchaseURL(purchases[i].id, purchases[i].transactionID, purchases[i].versionID, purchases[i].version)
        }
    }
}]), app.service("DownloadCancelService", ["$rootScope", "DeleteOnFileSystemService", "ProgressService", "DownloadModel", function($rootScope, DeleteOnFileSystemService, ProgressService, DownloadModel) {
    return {
        onCancelSingle: function(item) {
            console.log("DownloadCancelService onCancelSingle: ", item, item.downloadType), item.canceled = !0, $rootScope.$emit("cancel download", item), ProgressService.clearItem(item), DeleteOnFileSystemService.deleteFiles([item]), item.downloading && (item.downloading = !1, DownloadModel.downloadCounter--);
            for (var len = DownloadModel.itemsDownloadList.length; len--;)
                if (DownloadModel.itemsDownloadList[len].fileName === item.fileName) {
                    var removal = DownloadModel.itemsDownloadList[len];
                    DownloadModel.itemsDownloadList = DownloadModel.itemsDownloadList.filter(function(itm) {
                        return itm !== removal
                    })
                } console.log("DownloadCancelService onCancelSingle num of items: ", DownloadModel.itemsDownloadList.length), $rootScope.$emit("modal simple requested", ["", "Download of " + item.fileName + " has been canceled."], "sm")
        },
        onCancelAll: function() {
            console.log("DownloadCancelService cancel all downloads", DownloadModel.itemsDownloadList);
            for (var len = DownloadModel.itemsDownloadList.length; len--;) {
                var item = DownloadModel.itemsDownloadList[len];
                100 !== item.progressPerc && (item.canceled = !0, $rootScope.$emit("cancel download", item), ProgressService.clearItem(item), DeleteOnFileSystemService.deleteFiles([item]))
            }
            $rootScope.$emit("modal simple requested", ["", "All incomplete downloads have been canceled and deleted."], "sm"), DownloadModel.downloadCounter = -1, DownloadModel.itemsDownloadList = []
        }
    }
}]), app.service("DownloadCompleteService", ["$rootScope", "UnzipService", function($rootScope, UnzipService) {
    return {
        onComplete: function(items) {
            UnzipService.unzipItems(items)
        }
    }
}]), app.service("DownloadRequestService", ["$rootScope", "DownloadService", "ProgressService", "DownloadModel", "ReplaceModel", "AppModel", "ImportService", "ReplaceService", "StayAwakeService", "UnzipService", function($rootScope, DownloadService, ProgressService, DownloadModel, ReplaceModel, AppModel, ImportService, ReplaceService, StayAwakeService, UnzipService) {
    $rootScope.$on("download requested", function(event, items) {
        var downloadFolderName;
        console.log("DownloadRequestService DownloadModel.itemsDownloadList: ", DownloadModel.itemsDownloadList), "preview" === items[0].downloadType ? downloadFolderName = "previews" : "purchase" === items[0].downloadType && (downloadFolderName = "purchased");
        var item, dest = AppModel.currentBaseFolder + path.sep + "pond5" + path.sep + downloadFolderName + path.sep;
        console.log("DownloadRequestService downloadRequested items:", items), $rootScope.$emit("scroll progress to top");
        for (var i = 0; i < items.length; i++) {
            var codec;
            (item = items[i]).downloadDestination = dest, "preview" === item.downloadType ? "Video" == item.type || "AE" == item.type ? item.downloadURL = item.h264URL : "Sound effect" == item.type || "Music" == item.type ? item.downloadURL = item.m4aURL : "Photo" != item.type && "Illustration" != item.type || (item.downloadURL = item.iconLargeURL) : "purchase" === item.downloadType && (item.downloadURL = item.hiresURL), "Photo" == item.type ? item.ext = "jpg" : item.ext = item.downloadURL.substr(item.downloadURL.lastIndexOf(".") + 1).split("?")[0], item.videoCodec && (codec = item.videoCodec), "preview" !== item.downloadType && "unknown" !== codec && void 0 !== codec || (codec = ""), item.fileName = getFormattedName(item.id + " " + codec + " " + item.name + "." + item.ext), item.progressName = getAbbrName(item.fileName, 20), "preview" === item.downloadType && "AE" === item.vs && (item.fileName = "AE " + item.fileName), "purchase" === item.downloadType && ("AE" === item.vs ? item.fileName = "AE " + item.fileName : item.fileName = "hires " + item.fileName), $rootScope.$emit("open progress", !1), item.progressPerc = "", item.progressMB = "", ProgressService.addItem(item)
        }
        $rootScope.$$listenerCount["on item downloaded"] || $rootScope.$on("on item downloaded", function(event) {
            DownloadModel.downloadCounter++, console.log("DownloadRequestService on item downloaded DownloadModel.downloadCounter: ", DownloadModel.downloadCounter), console.log("DownloadRequestService on item downloaded DownloadModel.itemsDownloadList: ", DownloadModel.itemsDownloadList);
            var item = DownloadModel.itemsDownloadList[DownloadModel.downloadCounter];
            if (item) {
                StayAwakeService.updateState(!0);
                new DownloadService.download(item)
            } else if (StayAwakeService.updateState(!1), DownloadModel.downloadCounter--, console.log("DownloadRequestService download complete, check if something needs to be done, complete previews", ProgressService.getCompletedPreviews()), ProgressService.getCompletedPreviewsStatus() && ImportService.importClips(ProgressService.getCompletedPreviews()), ProgressService.getCompletedPurchasesStatus()) {
                console.log("DownloadRequestService purchases completed: ", ProgressService.getCompletedPurchases()), console.log("DownloadRequestService purchases completed ReplaceModel.getState(): ", ReplaceModel.getState());
                var AEItems = [];
                if (ProgressService.getCompletedPurchases().forEach(function(item) {
                        "AE" == item.type && AEItems.push(item)
                    }), "1.0.8" != PLUGIN_VERSION && UnzipService.unzipItems(AEItems), ReplaceModel.getState() === NOT_DOWNLOADED) {
                    var dest = AppModel.currentBaseFolder + path.sep + "pond5" + path.sep + "purchased" + path.sep;
                    ProgressService.getCompletedPurchases().forEach(function(entry) {
                        ReplaceModel.addHires(dest, [entry])
                    }), ReplaceService.onPurchasedAndDownloaded(AEItems.length)
                }
            }
        }), console.log("DownloadRequestService new request, ProgressService.getIncompleteItems ", ProgressService.getIncompleteItems()), 0 < ProgressService.getIncompleteItems().length && !ProgressService.getDownloadingStatus() && $rootScope.$emit("on item downloaded")
    })
}]), app.service("DownloadService", ["$rootScope", "ProgressService", function($rootScope, ProgressService) {
    function download(item) {
        console.log("DownloadService download item: ", item);
        var allowWriting = !0;
        $rootScope.$on("cancel download", function(event, itm) {
            itm.fileName === item.fileName && (itm.canceled = !0, item.canceled = !0, allowWriting = !1)
        }), item.downloading = !0;
        var file, sizeOnFS, writeOptions, path = item.downloadDestination + item.fileName;
        writeOptions = fs.existsSync(path) ? (sizeOnFS = fs.statSync(path).size, console.log("DownloadService sizeOnFS: ", sizeOnFS), {
            flags: "r+"
        }) : (console.log("DownloadService file does not exist yet, create stream"), {
            flags: "w"
        }), file = fs.createWriteStream(path, writeOptions), https.get(item.downloadURL, function(res) {
            var len;
            res.headers["content-length"] ? (len = parseInt(res.headers["content-length"], 10), console.log("DownloadService res has content-length: ", res)) : console.log("DownloadService content-length unknown", res);
            var progressPerc, cur = 0,
                total = len / 1048576;

            function setToComplete() {
                item.canceled || (item.progressPerc = 100, item.progressMB = total.toFixed(2) + "/" + total.toFixed(2) + "MB", item.completed = !0), item.canceled = !1, item.downloading = !1, $rootScope.$emit("on item downloaded"), $rootScope.$digest()
            }
            res.pipe(file), len <= sizeOnFS && (file.end(), setToComplete()), res.on("data", function(chunk) {
                allowWriting ? (cur += chunk.length, progressPerc = (100 * cur / len).toFixed(2), $rootScope.$apply(function() {
                    item.progressPerc = progressPerc.split(".")[0], item.progressMB = (cur / 1048576).toFixed(2) + "/" + total.toFixed(2) + "MB"
                })) : res.destroy()
            }).on("error", function(e) {
                console.log("DownloadService error: " + e.message)
            }).on("end", function() {
                file.end(), setToComplete()
            })
        }).on("error", function(err) {
            console.error("Download Error code and filename:", err.code, item.fileName), console.error("Download err:", err), item.progressPerc = 0, item.progressMB = "", setTimeout(function() {
                download(item, options)
            }, 1e3)
        })
    }
    return {
        download: function(item, options) {
            return new download(item, options)
        }
    }
}]), app.service("ImportAEService", ["$rootScope", "ReplaceModel", function($rootScope, ReplaceModel) {
    var call = {
        showingModal: !1,
        import: function(sourceDir) {
            var walk = function(dir, done) {
                var files = [];
                fs.readdir(dir, function(err, list) {
                    if (err) return done(err);
                    var i = 0;
                    ! function next() {
                        var file = list[i++];
                        if (!file) return done(null, files);
                        file = dir + "/" + file, fs.stat(file, function(err, stat) {
                            stat && stat.isDirectory() ? walk(file, function(err, res) {
                                files = files.concat(res), next()
                            }) : (files.push(file), next())
                        })
                    }()
                })
            };
            walk(sourceDir, function(err, files) {
                if (err) throw err;
                for (var i = 0; i < files.length; i += 1) console.log("ImportService file", files[i]), -1 != files[i].indexOf(".aep") && csInterface.evalScript("importAETemplate(" + JSON.stringify(files[i]) + ")", function(result) {
                    call.showingModal || ($rootScope.$emit("modal simple requested", ["", "Your project has been updated."]), call.showingModal = !0), console.log("ImportAEService import showingModal", call.showingModal)
                })
            })
        }
    };
    return call
}]), app.factory("ImportedPreviewsService", ["$rootScope", function($rootScope) {
    var result = {
        readXML: function() {
            var dest = path.sep + "pond5" + path.sep + "imports" + path.sep + "imported_previews.xml";
            result.file = getUserHome() + dest, fs.readFile(result.file, "utf8", function(err, data) {
                if (err) throw err;
                result.xml = data, result.parseXML()
            })
        },
        saveItem: function(id) {
            var idsString = result.idsString.toString(); - 1 == idsString.indexOf(id.toString()) && (0 < idsString.length ? result.idsString += "," + id : result.idsString = id, result.writeToDisk())
        },
        deleteItem: function(id) {
            -1 != result.idsString.indexOf(id) && (result.idsString = result.idsString.replace(id, "")), "," == result.idsString.substr(0, 1) && (result.idsString = result.idsString.substr(1)), "," == result.idsString.substr(result.idsString.length - 1, result.idsString.length) && (result.idsString = result.idsString.slice(0, -1)), result.writeToDisk(), $rootScope.$emit("api call", {
                fn: "getImportedPreviews"
            })
        },
        parseXML: function() {
            var parser = new xml2js.Parser;
            parser.addListener("end", function(res) {
                (result.parsedXML = res) && (result.idsString = res.root.previews[0].$.ids)
            }), parser.parseString(result.xml)
        },
        writeToDisk: function() {
            result.parsedXML.root.previews[0].$.ids = result.idsString;
            var xml = (new xml2js.Builder).buildObject(result.parsedXML);
            fs.writeFile(result.file, xml, function(err) {
                if (err) throw err
            })
        }
    };
    return result
}]), app.service("MissingItemsService", ["$rootScope", "MissingItemsModel", "ReplaceModel", "Service", "CartModel", "ReplaceServiceShared", function($rootScope, MissingItemsModel, ReplaceModel, Service, CartModel, ReplaceServiceShared) {
    $rootScope.$on("missing items complete", function(event, items) {
        console.log("MissingItemsService on missing items: ", items), ReplaceModel.getState() === MISSING_ITEMS && result.onMissingItems(items)
    }), $rootScope.$on("formats replacing complete", function(event, item, formats) {
        ReplaceModel.getState() === MISSING_ITEMS && result.onMissingItemsFormats(item, formats)
    }), $rootScope.$on("on purchases vo", function(event, vo) {
        console.log("MissingItemsService on purchases vo, state: ", ReplaceModel.getState()), ReplaceModel.getState() != DEFAULT && result.onPurchasesVO(vo)
    });
    var result = {
        missingItemsCounter: 0,
        onMissingItems: function(data) {
            var missingItemsVO = new MissingItemsVO(data.commands[0]);
            (MissingItemsModel.missingItemsVO = missingItemsVO).items.forEach(function(entry) {
                Service.getFormatsReplacing(entry)
            })
        },
        onMissingItemsFormats: function(item, formats) {
            if (result.missingItemsCounter++, 1 < (formats = _.uniq(formats, function(p) {
                    return p.ti
                })).length)
                for (i = 0; i < formats.length; i++) item.formats[i] = new ItemVO(formats[i]), item.parentFormatID = item.id, item.formats[i].offset = formats[i].offset;
            result.missingItemsCounter === MissingItemsModel.missingItemsVO.items.length && (result.missingItemsCounter = 0, Service.getPurchases())
        },
        onPurchasesVO: function(purchasesVO) {
            for (var item, missingItems = MissingItemsModel.missingItemsVO.items, cartItems = CartModel.cartVO.items, purchasedItems = purchasesVO.items, i = 0; i < missingItems.length; i++) {
                var cartItem, purchase;
                item = missingItems[i];
                for (var j = 0; j < cartItems.length; j++) {
                    cartItem = cartItems[j], item.id == cartItem.id && (item.inCart = !0);
                    for (var formats = item.formats, k = 0; k < formats.length; k++) formats[k].id == cartItem.id && formats[k].offset == cartItem.offset && (formats[k].inCart = !0, item.inCart = !0)
                }
                for (j = 0; j < purchasedItems.length; j++) {
                    purchase = purchasedItems[j], item.id == purchase.id && (item.inDownloads = !0, item.transactionID = purchase.transactionID);
                    for (formats = item.formats, k = 0; k < formats.length; k++) formats[k].id == purchase.id && (formats[k].inDownloads = !0, formats[k].transactionID = purchase.transactionID, purchasedItems[j].parentFormatID && (formats[k].parentFormatID = purchase.parentFormatID))
                }
            }
            ReplaceModel.getState() === MISSING_ITEMS ? $rootScope.$emit("modal replace", missingItems) : ReplaceModel.getState() === NOT_PURCHASED && ReplaceServiceShared.onPurchased(missingItems)
        }
    };
    return result
}]), app.service("ProgressService", ["$rootScope", "DownloadModel", function($rootScope, DownloadModel) {
    var result = {
        alreadyHasItem: function(item) {
            var itemsContainItem = !1;
            return DownloadModel.itemsDownloadList.forEach(function(entry) {
                entry.fileName === item.fileName && (itemsContainItem = !0)
            }), itemsContainItem
        },
        addItem: function(item) {
            DownloadModel.itemsDownloadList.forEach(function(entry) {
                entry.fileName === item.fileName && (console.log("ProgressService already in list: ", item.fileName), item.completed = !1, item.imported = !1, item.canceled = !1, item.progressPerc = 0, item.progressMB = "", DownloadModel.downloadCounter--, result.clearItem(item), console.log("ProgressService already in list, cleared: ", DownloadModel.itemsDownloadList))
            }), DownloadModel.itemsDownloadList.push(item), console.log("ProgressService addItem, list: ", DownloadModel.itemsDownloadList), $rootScope.$emit("added to progress")
        },
        clearCompleteItems: function() {
            console.log("ProgressService clearCompleteItems ");
            for (var len = DownloadModel.itemsDownloadList.length, oldLen = len; len--;) {
                var item = DownloadModel.itemsDownloadList[len];
                if (100 === item.progressPerc) {
                    item.completed = !1, item.imported = !1, item.canceled = !1, item.progressPerc = 0;
                    var removal = DownloadModel.itemsDownloadList[len];
                    DownloadModel.itemsDownloadList = DownloadModel.itemsDownloadList.filter(function(itm) {
                        return itm !== removal
                    })
                }
            }
            var diff = oldLen - DownloadModel.itemsDownloadList.length;
            DownloadModel.downloadCounter = DownloadModel.downloadCounter - diff, console.log("ProgressService clearCompleteItems DownloadModel.itemsDownloadList: ", DownloadModel.itemsDownloadList), console.log("ProgressService clearCompleteItems new downloadCounter: ", DownloadModel.downloadCounter), $rootScope.$emit("clear progress")
        },
        clearIncompleteItems: function() {
            console.log("ProgressService clearIncompleteItems ");
            for (var len = DownloadModel.itemsDownloadList.length; len--;)
                if (100 !== DownloadModel.itemsDownloadList[len].progressPerc) {
                    var removal = DownloadModel.itemsDownloadList[len];
                    DownloadModel.itemsDownloadList = DownloadModel.itemsDownloadList.filter(function(itm) {
                        return itm !== removal
                    })
                } $rootScope.$emit("on clear", DownloadModel.itemsDownloadList)
        },
        clearAllItems: function() {
            console.log("ProgressService clearAllItems "), DownloadModel.itemsDownloadList = [], $rootScope.$emit("clear progress"), DownloadModel.downloadCounter = 0
        },
        clearItem: function(item) {
            console.log("ProgressService clearItem ");
            for (var len = DownloadModel.itemsDownloadList.length; len--;)
                if (DownloadModel.itemsDownloadList[len].fileName === item.fileName) {
                    var removal = DownloadModel.itemsDownloadList[len];
                    DownloadModel.itemsDownloadList = DownloadModel.itemsDownloadList.filter(function(itm) {
                        return itm !== removal
                    })
                } $rootScope.$emit("clear progress")
        },
        getIncompleteItems: function() {
            var incompletes = [];
            return DownloadModel.itemsDownloadList.forEach(function(entry) {
                entry.completed || (console.log("ProgressService not completed: ", entry.fileName), incompletes.push(entry))
            }), incompletes
        },
        getCompletedPreviewsStatus: function() {
            var allCompleted = !0;
            return DownloadModel.itemsDownloadList.forEach(function(entry) {
                entry.completed || "preview" !== entry.downloadType || (allCompleted = !1)
            }), 0 === DownloadModel.itemsDownloadList.length && (allCompleted = !1), console.log("ProgressService getCompletedPreviewsStatus allCompleted", allCompleted), allCompleted
        },
        getCompletedPreviews: function() {
            var completes = [];
            return DownloadModel.itemsDownloadList.forEach(function(entry) {
                entry.completed && "preview" == entry.downloadType && completes.push(entry)
            }), completes
        },
        getCompletedPurchasesStatus: function() {
            var allCompleted = !0;
            return DownloadModel.itemsDownloadList.forEach(function(entry) {
                entry.completed || "purchase" !== entry.downloadType || (allCompleted = !1)
            }), 0 === DownloadModel.itemsDownloadList.length && (allCompleted = !1), console.log("ProgressService getCompletedPurchasesStatus allCompleted", allCompleted), allCompleted
        },
        getCompletedPurchases: function() {
            var completes = [];
            return DownloadModel.itemsDownloadList.forEach(function(entry) {
                entry.completed && "purchase" == entry.downloadType && completes.push(entry)
            }), completes
        },
        getDownloadingStatus: function() {
            var downloading = !1;
            return DownloadModel.itemsDownloadList.forEach(function(entry) {
                entry.downloading && (downloading = !0)
            }), downloading
        }
    };
    return result
}]), app.service("ReadClipsOnFSService", ["$rootScope", "ReplaceModel", "MissingItemsModel", "ViewStateService", "DownloadBatchService", "AppModel", function($rootScope, ReplaceModel, MissingItemsModel, ViewStateService, DownloadBatchService, AppModel) {
    var call = {
        listPurchasesOnFS: function(cb) {
            ReplaceModel.hiresOnFS = [];
            for (var cbCounter = 0, i = 0; i < AppModel.baseFolders.length; i++) call.readPurchasesFolders(AppModel.baseFolders[i] + path.sep + "pond5" + path.sep + "purchased" + path.sep, function() {
                ++cbCounter === AppModel.baseFolders.length && (console.log("\nReadClipsOnFSService ReplaceModel.hiresOnFS done: ", cbCounter, ReplaceModel.hiresOnFS), call.listPreviewsOnFS(function() {
                    cb()
                }))
            })
        },
        readPurchasesFolders: function(dest, cb) {
            fs.readdir(dest, function(err, files) {
                if (err) throw new Error("ReadClipsOnFSService: " + dest + " does not exist.");
                var hiresVO;
                files = files.filter(junk.not);
                for (var i = 0; i < files.length; i += 1) hiresVO = new HiresVO(dest, files[i]), ReplaceModel.hiresOnFS.push(hiresVO), 0 === path.extname(files[i]).length ? hiresVO.type = "AE folder" : ".zip" === path.extname(files[i]) ? hiresVO.type = "AE zip" : ".mov" === path.extname(files[i]) ? hiresVO.type = "video" : ".wav" === path.extname(files[i]) && (hiresVO.type = "audio");
                cb()
            })
        },
        listPreviewsOnFS: function(cb) {
            ReplaceModel.previewsOnFS = [];
            for (var i = 0; i < AppModel.baseFolders.length; i++) {
                var walk = function(dir, done) {
                        var files = [];
                        fs.readdir(dir, function(err, list) {
                            if (err) return done(err);
                            var i = 0;
                            ! function next() {
                                var file = list[i++];
                                if (!file) return done(null, files);
                                file = dir + "/" + file, fs.stat(file, function(err, stat) {
                                    stat && stat.isDirectory() ? walk(file, function(err, res) {
                                        files = files.concat(res), next()
                                    }) : (files.push(file), next())
                                })
                            }()
                        })
                    },
                    dest = AppModel.baseFolders[i] + path.sep + "pond5" + path.sep + "previews",
                    counter = 0;
                walk(dest, function(err, files) {
                    if (err) throw err;
                    for (var previewVO, i = 0; i < files.length; i += 1) previewVO = new PreviewVO(dest, files[i]), ReplaceModel.previewsOnFS.push(previewVO);
                    ++counter === AppModel.baseFolders.length && cb()
                })
            }
        }
    };
    return call
}]), app.service("ReplaceServiceShared", ["$rootScope", "ReplaceModel", "Service", "MissingItemsModel", "ViewStateService", "DownloadBatchService", "ImportAEService", "DeleteOnFileSystemService", function($rootScope, ReplaceModel, Service, MissingItemsModel, ViewStateService, DownloadBatchService, ImportAEService, DeleteOnFileSystemService) {
    var call = {
        removeDuplicates: function(clips) {
            return clips = clips.filter(function(v, i, a) {
                return a.indexOf(v) === i
            })
        },
        getPreviewsOnFSNames: function() {
            var previewNamesonFS = [];
            return ReplaceModel.previewsOnFS.forEach(function(entry) {
                previewNamesonFS.push(entry.name)
            }), previewNamesonFS
        },
        filterNonP5Clips: function(clips, previewNamesOnFS) {
            return clips = clips.filter(function(n) {
                return -1 != previewNamesOnFS.indexOf(n)
            })
        },
        getPreviewsIDs: function(clips) {
            var previewIDs = [];
            return clips.forEach(function(entry) {
                var substr = entry.split(" ");
                "AE" === substr[0] ? previewIDs.push(substr[1]) : previewIDs.push(substr[0])
            }), console.log("\nReplaceServiceShared previewIDs: " + previewIDs), previewIDs
        },
        setReplaceProp: function(ids) {
            for (var i = 0; i < ids.length; i++)
                for (var j = 0; j < ReplaceModel.hiresOnFS.length; j++) ids[i] === ReplaceModel.hiresOnFS[j].id && (ReplaceModel.hiresOnFS[j].replace = !0)
        },
        getMissingItemIDs: function(clipsInSeqs) {
            var clipsInSelectedSequences = clipsInSeqs;
            console.log("ReplaceService ReplaceModel.aeItemsinProjectView: ", ReplaceModel.getAEItems()), 0 < ReplaceModel.getAEItems().length && (clipsInSelectedSequences = clipsInSelectedSequences.concat(ReplaceModel.getAEItems())), console.log("ReplaceService clips after concat layer items and AE items: ", clipsInSelectedSequences), clipsInSelectedSequences = call.removeDuplicates(clipsInSelectedSequences), console.log("\nReplaceServiceShared clipsInSelectedSequences after removing duplicates: ", clipsInSelectedSequences);
            var previewNamesonFS = call.getPreviewsOnFSNames();
            console.log("\nReplaceServiceShared  previewNamesonFS: ", previewNamesonFS), clipsInSelectedSequences = call.filterNonP5Clips(clipsInSelectedSequences, previewNamesonFS), console.log("\nReplaceServiceShared after filterNonP5Clips", clipsInSelectedSequences);
            var previewIDs = call.getPreviewsIDs(clipsInSelectedSequences);
            console.log("\nReplaceServiceShared previewIDs: " + previewIDs), call.setReplaceProp(previewIDs), console.log("\nReplaceServiceShared after set replace: " + ReplaceModel.hiresOnFS);
            var hiresIDs = call.getHiresIDsonFS();
            console.log("\nReplaceServiceShared hiresIDs: " + hiresIDs);
            var missingItemIDs = _(previewIDs).difference(hiresIDs),
                missingIDsToString = missingItemIDs.join(",");
            if (console.log("nReplaceServiceShared  missingIDsToString: " + missingIDsToString), 0 < missingItemIDs.length) Service.getMissingItems(missingIDsToString);
            else {
                if (0 < hiresIDs.length) return hiresIDs.length;
                0 === clipsInSelectedSequences.length && (ReplaceModel.setState(DEFAULT), $rootScope.$emit("modal simple requested", ["", "There are no Pond5 previews in your current project."]))
            }
        },
        getHiresIDsonFS: function() {
            var hiresIDs = [];
            return ReplaceModel.hiresOnFS.forEach(function(entry) {
                (entry.replace || entry.importAE) && hiresIDs.push(entry.id)
            }), hiresIDs
        },
        onModalReplaceOK: function() {
            for (var item, missingItems = MissingItemsModel.missingItemsVO.items, itemsNotPurchased = [], itemsNotDownloaded = [], i = 0; i < missingItems.length; i++)(item = missingItems[i]).selected && !item.inDownloads && itemsNotPurchased.push(item), item.selected && item.inDownloads && itemsNotDownloaded.push(item);
            0 < itemsNotPurchased.length ? call.onNotPurchased(itemsNotPurchased) : 0 < itemsNotDownloaded.length ? (console.log("ReplaceServiceShared onModalReplaceOK, download items: ", itemsNotDownloaded), ReplaceModel.missingDownloads = itemsNotDownloaded, call.onNotDownloaded(itemsNotDownloaded)) : (ReplaceModel.setState(PURCHASED_AND_DOWNLOADED), console.log("ReplaceServiceShared onModalReplaceOK, replace"), call.onPurchasedAndDownloaded())
        },
        onNotPurchased: function(itemsNotPurchased) {
            for (var addToCartItems = [], i = 0; i < itemsNotPurchased.length; i++)
                if (item = itemsNotPurchased[i], 0 < itemsNotPurchased[i].formats.length)
                    for (var j = 0; j < itemsNotPurchased[i].formats.length; j++) format = itemsNotPurchased[i].formats[j], format.selected && (console.log("ReplaceServiceShared onNotPurchased add this format to cart: ", format), addToCartItems.push(format.id));
                else console.log("ReplaceServiceShared onNotPurchased add this item to cart: ", item), addToCartItems.push(item.id);
            $rootScope.$emit("modal simple requested", ["", "Please review your Cart. Press the 'Checkout' button to proceed with replacing your previews."]);
            var apiObj = {
                fn: "modifyCart",
                args: [addToCartItems.join(","), ""]
            };
            $rootScope.$emit("api call", apiObj), ViewStateService.viewRequested("cart"), ReplaceModel.setState(NOT_PURCHASED)
        },
        onPurchased: function(downloadItems) {
            console.log("ReplaceServiceShared onPurchased: ", downloadItems);
            for (var item, missingItems = MissingItemsModel.missingItemsVO.items, itemsNotDownloaded = [], i = 0; i < missingItems.length; i++)(item = missingItems[i]).inDownloads && itemsNotDownloaded.push(item);
            0 < itemsNotDownloaded.length && (console.log("ReplaceServiceShared onPurchased, download items: ", itemsNotDownloaded), ReplaceModel.missingDownloads = itemsNotDownloaded, $rootScope.$emit("modal simple requested", ["Your purchase has been successful.", "Your purchased clips will begin downloading now. Once the downloads are completed, your lo-res previews will be replaced with your high-res clips."]), call.onNotDownloaded(itemsNotDownloaded, !0))
        },
        onNotDownloaded: function(itemsNotDownloaded, afterPurchase) {
            afterPurchase = afterPurchase || !1, console.log("ReplaceServiceShared onNotDownloaded missing items:", itemsNotDownloaded);
            for (var downloadItems = [], i = 0; i < itemsNotDownloaded.length; i++)
                if (item = itemsNotDownloaded[i], 0 < itemsNotDownloaded[i].formats.length)
                    for (var j = 0; j < itemsNotDownloaded[i].formats.length; j++) format = itemsNotDownloaded[i].formats[j], format.selected && (console.log("ReplaceServiceShared onNotDownloaded download this format: ", format), downloadItems.push(format));
                else console.log("ReplaceServiceShared onNotDownloaded download item: ", item), downloadItems.push(item);
            afterPurchase || $rootScope.$emit("modal simple requested", ["You have purchases that are missing in your project. ", "They will be downloaded. Once the downloads are completed, your lo-res previews will be replaced with your high-res clips."]), DownloadBatchService.onBatchRequested(downloadItems), ReplaceModel.setState(NOT_DOWNLOADED)
        }
    };
    return call
}]), app.service("ScrollService", ["SearchModel", "Service", function(SearchModel, Service) {
    this.onScroll = function() {
        if (SearchModel.allowInfiniteScroll) {
            var m = document.getElementById("main-holder");
            1 === (getScroll()[1] - 72) / (m.scrollHeight - window.innerHeight) && (console.log("ScrollService show more: " + SearchModel.isSearching), SearchModel.isSearching || (SearchModel.isSearching = !0, SearchModel.resultType = "add", SearchModel.page = SearchModel.page + 1, Service.search()))
        }
    }
}]), app.factory("StartUpService", ["$rootScope", "CreateOnFileSystemService", "MissingItemsService", "ViewStateService", "AppModel", function($rootScope, CreateOnFileSystemService, MissingItemsService, ViewStateService, AppModel) {
    return $("#logo").click(function() {
        location.reload()
    }), $rootScope.$on("environment set", function() {
        console.log("StartUpService, 26/10 pointing at ", window.location.href), gup("tp", window.location.href) && (THIRD_PARTY = gup("tp", window.location.href)), -1 < window.location.href.indexOf("test") ? MODE = "test" : MODE = "live", console.log("StartUpService MODE:", MODE), console.log("StartUpService OS:", os.platform()), console.log("StartUpService, app version: ", PLUGIN_VERSION), AppModel.currentBaseFolder = AppModel.getDocumentsPath(), console.log("StartUpService currentBaseFolder: ", AppModel.currentBaseFolder + "\n\n"), CreateOnFileSystemService.createUserHomeFolder(), MissingItemsService.missingItemsCounter = 0, ViewStateService.viewRequested("search")
    }), {
        init: function() {
            setTimeout(function() {
                AppModel.setEnv()
            }, 2e3)
        }
    }
}]), app.factory("StayAwakeService", ["$rootScope", "DownloadModel", function($rootScope, DownloadModel) {
    return {
        updateState: function(state) {
            console.log("StayAwakeService state: ", state), state && !DownloadModel.stayAwake ? (sleep.prevent(), DownloadModel.stayAwake = !0) : !state && DownloadModel.stayAwake && (sleep.allow(), DownloadModel.stayAwake = !1)
        }
    }
}]), app.service("TransactionService", ["$q", "ViewStateService", "Service", "ReplaceModel", "AnalyticsService", "CartModel", function($q, ViewStateService, Service, ReplaceModel, AnalyticsService, CartModel) {
    this.onMessageReceivedFromAdyen = function(event) {
        console.log("event.source: ", event.source), console.log("event origin: ", event.origin), console.log("event data: ", event.data);
        var deferred = $q.defer();
        switch (event.data) {
            case "PAID":
                console.log("TransactionService PAID"), deferred.resolve("PAID"), ReplaceModel.getState() === NOT_PURCHASED ? Service.getPurchases() : ViewStateService.viewRequested("downloads"), AnalyticsService.sendData(null, "transaction"), Service.getUserInfo();
                break;
            case "CANCELED":
                deferred.reject("CANCELED"), console.log("TransactionService CANCELED");
                break;
            case "PENDING":
                console.log("TransactionService PENDING"), deferred.reject("PENDING");
                break;
            default:
                deferred.reject("UNKNOWN")
        }
        return deferred.promise
    }
}]), app.service("UnzipService", ["$rootScope", "DeleteOnFileSystemService", "ReplaceModel", "ImportAEService", function($rootScope, DeleteOnFileSystemService, ReplaceModel, ImportAEService) {
    var call = {
        unzippedCounter: 0,
        deletedCounter: 0,
        numOfItems: 0,
        items: [],
        deleteObjects: [],
        itemObjects: [],
        unzipItems: function(items) {
            call.unzippedCounter = 0, call.deletedCounter = 0, call.numOfItems = items.length, call.items = items, call.deleteObjects = [], call.itemObjects = [], call.items.forEach(function(item) {
                var itemObj = {
                    dest: item.downloadDestination + "AE " + item.id,
                    source: item.downloadDestination + item.fileName
                };
                call.itemObjects.push(itemObj), call.deleteObjects.push(itemObj.source, itemObj.dest + path.sep + "__MACOSX"), call.unzip(itemObj)
            }), console.log("UnzipService unzipItems numOfItems:", call.numOfItems), console.log("UnzipService unzipItems call.deleteObjects:", call.deleteObjects), console.log("UnzipService unzipItems call.deleteObjects.length:", call.deleteObjects.length)
        },
        unzip: function(itemObj) {
            var unzipper = new DecompressZip(itemObj.source);
            unzipper.on("error", function(err) {
                console.log("UnzipService Caught an error: ", err)
            }), unzipper.on("extract", function(log) {
                console.log("UnzipService Finished extracting"), call.unzippedCounter++, call.unzippedCounter === call.numOfItems && (console.log("UnzipService Finished extracting all items, unzippedCounter", call.unzippedCounter), DeleteOnFileSystemService.deleteFolder(call.deleteObjects, function() {
                    console.log("UnzipService zip or mac os folder deleted"), call.deletedCounter++, console.log("UnzipService call.deletedCounter: ", call.deletedCounter), console.log("UnzipService call.deleteObjects.length: ", call.deleteObjects.length), call.deletedCounter === call.deleteObjects.length && (console.log("UnzipService ALL zip or mac os folders deleted", ReplaceModel.getState()), call.itemObjects.forEach(function(item) {
                        ReplaceModel.getState() === NOT_DOWNLOADED && "AEFT" == HOST_NAME && ImportAEService.import(item.dest)
                    }), ReplaceModel.getState() === DEFAULT && 1 < call.numOfItems ? opn(call.items[0].downloadDestination) : ReplaceModel.getState() === DEFAULT && 1 === call.numOfItems && (console.log("UnzipService opn finder"), opn(itemObj.dest)), ReplaceModel.setState(DEFAULT))
                }))
            }), unzipper.on("progress", function(fileIndex, fileCount) {
                console.log("UnzipService Extracted file " + (fileIndex + 1) + " of " + fileCount)
            }), unzipper.extract({
                path: itemObj.dest
            })
        }
    };
    return call
}]), app.factory("UserService", ["$rootScope", "AppModel", "LoginModel", function($rootScope, AppModel, LoginModel) {
    var file, parsedLocalXML, cm, cx, result = {
        readXML: function() {
            file = AppModel.getUserXML(), fs.readFile(file, "utf8", function(err, data) {
                if (err) throw err;
                result.parseLocalXML(data)
            })
        },
        saveData: function(cx, cm) {
            parsedLocalXML.root.user[0].$.cm = cm, parsedLocalXML.root.user[0].$.cx = cx, result.writeToDisk()
        },
        parseLocalXML: function(xml) {
            var parser = new xml2js.Parser;
            parser.addListener("end", function(res) {
                if (cm = (parsedLocalXML = res).root.user[0].$.cm, cx = res.root.user[0].$.cx, 0 < cm.length && 0 < cx.length) {
                    LoginModel.setCX(cx), LoginModel.setCM(cm);
                    $rootScope.$emit("api call", {
                        fn: "getUserInfo"
                    })
                }
            }), parser.parseString(xml)
        },
        writeToDisk: function() {
            var xml = (new xml2js.Builder).buildObject(parsedLocalXML);
            fs.writeFile(file, xml, function(err) {
                if (err) throw err
            })
        }
    };
    return result
}]), app.factory("ViewStateService", ["$rootScope", "ViewStateModel", "ReplaceModel", "LoginModel", function($rootScope, ViewStateModel, ReplaceModel, LoginModel) {
    var requestedState, result = {
        viewRequested: function(state) {
            console.log("ViewStateService viewRequested: ", state), "downloads" !== (requestedState = state) && "previews" !== requestedState && "cart" !== requestedState || LoginModel.getLoggedIn() ? (ViewStateModel.setState(state), result.onViewApproved(!0)) : $rootScope.$emit("modal not logged in", [ERROR])
        },
        onViewApproved: function(result) {
            if (console.log("ViewStateService onViewApproved ", result, requestedState), result) {
                var fName;
                switch (ViewStateModel.setState(requestedState), requestedState) {
                    case "downloads":
                        fName = "getPurchases";
                        break;
                    case "previews":
                        fName = "getImportedPreviews";
                        break;
                    case "cart":
                        fName = "getCart";
                        break;
                    case "freebies":
                        fName = "getFreeClips";
                        break;
                    case "bins":
                        fName = "getBin";
                        break;
                    case "search":
                    default:
                        fName = "search"
                }
                $rootScope.$emit("api call", {
                    fn: fName
                })
            } else console.log("ViewStateService onViewApproved cancel clicked in modal, stay in current view")
        }
    };
    return result
}]);
var imgHeight, imgWidth, COUNTRIES = [{
        name: "United States",
        code: "US"
    }, {
        name: "Afghanistan",
        code: "AF"
    }, {
        name: "Aland Islands",
        code: "AX"
    }, {
        name: "Albania",
        code: "AL"
    }, {
        name: "Algeria",
        code: "DZ"
    }, {
        name: "American Samoa",
        code: "AS"
    }, {
        name: "Andorra",
        code: "AD"
    }, {
        name: "Angola",
        code: "AO"
    }, {
        name: "Anguilla",
        code: "AI"
    }, {
        name: "Antarctica",
        code: "AQ"
    }, {
        name: "Antigua and Barbuda",
        code: "AG"
    }, {
        name: "Argentina",
        code: "AR"
    }, {
        name: "Armenia",
        code: "AM"
    }, {
        name: "Aruba",
        code: "AW"
    }, {
        name: "Australia",
        code: "AU"
    }, {
        name: "Austria",
        code: "AT"
    }, {
        name: "Azerbaijan",
        code: "AZ"
    }, {
        name: "Bahamas",
        code: "BS"
    }, {
        name: "Bahrain",
        code: "BH"
    }, {
        name: "Bangladesh",
        code: "BD"
    }, {
        name: "Barbados",
        code: "BB"
    }, {
        name: "Belarus",
        code: "BY"
    }, {
        name: "Belgium",
        code: "BE"
    }, {
        name: "Belize",
        code: "BZ"
    }, {
        name: "Benin",
        code: "BJ"
    }, {
        name: "Bermuda",
        code: "BM"
    }, {
        name: "Bhutan",
        code: "BT"
    }, {
        name: "Bolivia",
        code: "BO"
    }, {
        name: "Bosnia and Herzegovina",
        code: "BA"
    }, {
        name: "Botswana",
        code: "BW"
    }, {
        name: "Bouvet Island",
        code: "BV"
    }, {
        name: "Brazil",
        code: "BR"
    }, {
        name: "British Indian Ocean Territory",
        code: "IO"
    }, {
        name: "Brunei Darussalam",
        code: "BN"
    }, {
        name: "Bulgaria",
        code: "BG"
    }, {
        name: "Burkina Faso",
        code: "BF"
    }, {
        name: "Burundi",
        code: "BI"
    }, {
        name: "Cambodia",
        code: "KH"
    }, {
        name: "Cameroon",
        code: "CM"
    }, {
        name: "Canada",
        code: "CA"
    }, {
        name: "Cape Verde",
        code: "CV"
    }, {
        name: "Cayman Islands",
        code: "KY"
    }, {
        name: "Central African Republic",
        code: "CF"
    }, {
        name: "Chad",
        code: "TD"
    }, {
        name: "Chile",
        code: "CL"
    }, {
        name: "China",
        code: "CN"
    }, {
        name: "Christmas Island",
        code: "CX"
    }, {
        name: "Cocos (Keeling) Islands",
        code: "CC"
    }, {
        name: "Colombia",
        code: "CO"
    }, {
        name: "Comoros",
        code: "KM"
    }, {
        name: "Congo",
        code: "CG"
    }, {
        name: "Congo, The Democratic Republic of the",
        code: "CD"
    }, {
        name: "Cook Islands",
        code: "CK"
    }, {
        name: "Costa Rica",
        code: "CR"
    }, {
        name: "Cote D'Ivoire",
        code: "CI"
    }, {
        name: "Croatia",
        code: "HR"
    }, {
        name: "Cuba",
        code: "CU"
    }, {
        name: "Cyprus",
        code: "CY"
    }, {
        name: "Czech Republic",
        code: "CZ"
    }, {
        name: "Denmark",
        code: "DK"
    }, {
        name: "Djibouti",
        code: "DJ"
    }, {
        name: "Dominica",
        code: "DM"
    }, {
        name: "Dominican Republic",
        code: "DO"
    }, {
        name: "Ecuador",
        code: "EC"
    }, {
        name: "Egypt",
        code: "EG"
    }, {
        name: "El Salvador",
        code: "SV"
    }, {
        name: "Equatorial Guinea",
        code: "GQ"
    }, {
        name: "Eritrea",
        code: "ER"
    }, {
        name: "Estonia",
        code: "EE"
    }, {
        name: "Ethiopia",
        code: "ET"
    }, {
        name: "Falkland Islands (Malvinas)",
        code: "FK"
    }, {
        name: "Faroe Islands",
        code: "FO"
    }, {
        name: "Fiji",
        code: "FJ"
    }, {
        name: "Finland",
        code: "FI"
    }, {
        name: "France",
        code: "FR"
    }, {
        name: "French Guiana",
        code: "GF"
    }, {
        name: "French Polynesia",
        code: "PF"
    }, {
        name: "French Southern Territories",
        code: "TF"
    }, {
        name: "Gabon",
        code: "GA"
    }, {
        name: "Gambia",
        code: "GM"
    }, {
        name: "Georgia",
        code: "GE"
    }, {
        name: "Germany",
        code: "DE"
    }, {
        name: "Ghana",
        code: "GH"
    }, {
        name: "Gibraltar",
        code: "GI"
    }, {
        name: "Greece",
        code: "GR"
    }, {
        name: "Greenland",
        code: "GL"
    }, {
        name: "Grenada",
        code: "GD"
    }, {
        name: "Guadeloupe",
        code: "GP"
    }, {
        name: "Guam",
        code: "GU"
    }, {
        name: "Guatemala",
        code: "GT"
    }, {
        name: "Guernsey",
        code: "GG"
    }, {
        name: "Guinea",
        code: "GN"
    }, {
        name: "Guinea-Bissau",
        code: "GW"
    }, {
        name: "Guyana",
        code: "GY"
    }, {
        name: "Haiti",
        code: "HT"
    }, {
        name: "Heard Island and Mcdonald Islands",
        code: "HM"
    }, {
        name: "Holy See (Vatican City State)",
        code: "VA"
    }, {
        name: "Honduras",
        code: "HN"
    }, {
        name: "Hong Kong",
        code: "HK"
    }, {
        name: "Hungary",
        code: "HU"
    }, {
        name: "Iceland",
        code: "IS"
    }, {
        name: "India",
        code: "IN"
    }, {
        name: "Indonesia",
        code: "ID"
    }, {
        name: "Iran, Islamic Republic Of",
        code: "IR"
    }, {
        name: "Iraq",
        code: "IQ"
    }, {
        name: "Ireland",
        code: "IE"
    }, {
        name: "Isle of Man",
        code: "IM"
    }, {
        name: "Israel",
        code: "IL"
    }, {
        name: "Italy",
        code: "IT"
    }, {
        name: "Jamaica",
        code: "JM"
    }, {
        name: "Japan",
        code: "JP"
    }, {
        name: "Jersey",
        code: "JE"
    }, {
        name: "Jordan",
        code: "JO"
    }, {
        name: "Kazakhstan",
        code: "KZ"
    }, {
        name: "Kenya",
        code: "KE"
    }, {
        name: "Kiribati",
        code: "KI"
    }, {
        name: "Korea, Democratic People's Republic of",
        code: "KP"
    }, {
        name: "Korea, Republic of",
        code: "KR"
    }, {
        name: "Kuwait",
        code: "KW"
    }, {
        name: "Kyrgyzstan",
        code: "KG"
    }, {
        name: "Lao People's Democratic Republic",
        code: "LA"
    }, {
        name: "Latvia",
        code: "LV"
    }, {
        name: "Lebanon",
        code: "LB"
    }, {
        name: "Lesotho",
        code: "LS"
    }, {
        name: "Liberia",
        code: "LR"
    }, {
        name: "Libyan Arab Jamahiriya",
        code: "LY"
    }, {
        name: "Liechtenstein",
        code: "LI"
    }, {
        name: "Lithuania",
        code: "LT"
    }, {
        name: "Luxembourg",
        code: "LU"
    }, {
        name: "Macao",
        code: "MO"
    }, {
        name: "Macedonia, The Former Yugoslav Republic of",
        code: "MK"
    }, {
        name: "Madagascar",
        code: "MG"
    }, {
        name: "Malawi",
        code: "MW"
    }, {
        name: "Malaysia",
        code: "MY"
    }, {
        name: "Maldives",
        code: "MV"
    }, {
        name: "Mali",
        code: "ML"
    }, {
        name: "Malta",
        code: "MT"
    }, {
        name: "Marshall Islands",
        code: "MH"
    }, {
        name: "Martinique",
        code: "MQ"
    }, {
        name: "Mauritania",
        code: "MR"
    }, {
        name: "Mauritius",
        code: "MU"
    }, {
        name: "Mayotte",
        code: "YT"
    }, {
        name: "Mexico",
        code: "MX"
    }, {
        name: "Micronesia, Federated States of",
        code: "FM"
    }, {
        name: "Moldova, Republic of",
        code: "MD"
    }, {
        name: "Monaco",
        code: "MC"
    }, {
        name: "Mongolia",
        code: "MN"
    }, {
        name: "Montserrat",
        code: "MS"
    }, {
        name: "Morocco",
        code: "MA"
    }, {
        name: "Mozambique",
        code: "MZ"
    }, {
        name: "Myanmar",
        code: "MM"
    }, {
        name: "Namibia",
        code: "NA"
    }, {
        name: "Nauru",
        code: "NR"
    }, {
        name: "Nepal",
        code: "NP"
    }, {
        name: "Netherlands",
        code: "NL"
    }, {
        name: "Netherlands Antilles",
        code: "AN"
    }, {
        name: "New Caledonia",
        code: "NC"
    }, {
        name: "New Zealand",
        code: "NZ"
    }, {
        name: "Nicaragua",
        code: "NI"
    }, {
        name: "Niger",
        code: "NE"
    }, {
        name: "Nigeria",
        code: "NG"
    }, {
        name: "Niue",
        code: "NU"
    }, {
        name: "Norfolk Island",
        code: "NF"
    }, {
        name: "Northern Mariana Islands",
        code: "MP"
    }, {
        name: "Norway",
        code: "NO"
    }, {
        name: "Oman",
        code: "OM"
    }, {
        name: "Pakistan",
        code: "PK"
    }, {
        name: "Palau",
        code: "PW"
    }, {
        name: "Palestinian Territory, Occupied",
        code: "PS"
    }, {
        name: "Panama",
        code: "PA"
    }, {
        name: "Papua New Guinea",
        code: "PG"
    }, {
        name: "Paraguay",
        code: "PY"
    }, {
        name: "Peru",
        code: "PE"
    }, {
        name: "Philippines",
        code: "PH"
    }, {
        name: "Pitcairn",
        code: "PN"
    }, {
        name: "Poland",
        code: "PL"
    }, {
        name: "Portugal",
        code: "PT"
    }, {
        name: "Puerto Rico",
        code: "PR"
    }, {
        name: "Qatar",
        code: "QA"
    }, {
        name: "Reunion",
        code: "RE"
    }, {
        name: "Romania",
        code: "RO"
    }, {
        name: "Russian Federation",
        code: "RU"
    }, {
        name: "Rwanda",
        code: "RW"
    }, {
        name: "Saint Helena",
        code: "SH"
    }, {
        name: "Saint Kitts and Nevis",
        code: "KN"
    }, {
        name: "Saint Lucia",
        code: "LC"
    }, {
        name: "Saint Pierre and Miquelon",
        code: "PM"
    }, {
        name: "Saint Vincent and the Grenadines",
        code: "VC"
    }, {
        name: "Samoa",
        code: "WS"
    }, {
        name: "San Marino",
        code: "SM"
    }, {
        name: "Sao Tome and Principe",
        code: "ST"
    }, {
        name: "Saudi Arabia",
        code: "SA"
    }, {
        name: "Senegal",
        code: "SN"
    }, {
        name: "Serbia and Montenegro",
        code: "CS"
    }, {
        name: "Seychelles",
        code: "SC"
    }, {
        name: "Sierra Leone",
        code: "SL"
    }, {
        name: "Singapore",
        code: "SG"
    }, {
        name: "Slovakia",
        code: "SK"
    }, {
        name: "Slovenia",
        code: "SI"
    }, {
        name: "Solomon Islands",
        code: "SB"
    }, {
        name: "Somalia",
        code: "SO"
    }, {
        name: "South Africa",
        code: "ZA"
    }, {
        name: "South Georgia and the South Sandwich Islands",
        code: "GS"
    }, {
        name: "Spain",
        code: "ES"
    }, {
        name: "Sri Lanka",
        code: "LK"
    }, {
        name: "Sudan",
        code: "SD"
    }, {
        name: "Suriname",
        code: "SR"
    }, {
        name: "Svalbard and Jan Mayen",
        code: "SJ"
    }, {
        name: "Swaziland",
        code: "SZ"
    }, {
        name: "Sweden",
        code: "SE"
    }, {
        name: "Switzerland",
        code: "CH"
    }, {
        name: "Syrian Arab Republic",
        code: "SY"
    }, {
        name: "Taiwan, Province of China",
        code: "TW"
    }, {
        name: "Tajikistan",
        code: "TJ"
    }, {
        name: "Tanzania, United Republic of",
        code: "TZ"
    }, {
        name: "Thailand",
        code: "TH"
    }, {
        name: "Timor-Leste",
        code: "TL"
    }, {
        name: "Togo",
        code: "TG"
    }, {
        name: "Tokelau",
        code: "TK"
    }, {
        name: "Tonga",
        code: "TO"
    }, {
        name: "Trinidad and Tobago",
        code: "TT"
    }, {
        name: "Tunisia",
        code: "TN"
    }, {
        name: "Turkey",
        code: "TR"
    }, {
        name: "Turkmenistan",
        code: "TM"
    }, {
        name: "Turks and Caicos Islands",
        code: "TC"
    }, {
        name: "Tuvalu",
        code: "TV"
    }, {
        name: "Uganda",
        code: "UG"
    }, {
        name: "Ukraine",
        code: "UA"
    }, {
        name: "United Arab Emirates",
        code: "AE"
    }, {
        name: "United Kingdom",
        code: "GB"
    }, {
        name: "United States",
        code: "US"
    }, {
        name: "United States Minor Outlying Islands",
        code: "UM"
    }, {
        name: "Uruguay",
        code: "UY"
    }, {
        name: "Uzbekistan",
        code: "UZ"
    }, {
        name: "Vanuatu",
        code: "VU"
    }, {
        name: "Venezuela",
        code: "VE"
    }, {
        name: "Vietnam",
        code: "VN"
    }, {
        name: "Virgin Islands, British",
        code: "VG"
    }, {
        name: "Virgin Islands, U.S.",
        code: "VI"
    }, {
        name: "Wallis and Futuna",
        code: "WF"
    }, {
        name: "Western Sahara",
        code: "EH"
    }, {
        name: "Yemen",
        code: "YE"
    }, {
        name: "Zambia",
        code: "ZM"
    }, {
        name: "Zimbabwe",
        code: "ZW"
    }],
    STATES = [{
        name: "Alabama",
        label: "Alabama",
        code: "AL"
    }, {
        name: "Alaska",
        label: "Alaska",
        code: "AK"
    }, {
        name: "American Samoa",
        label: "American Samoa",
        code: "AS"
    }, {
        name: "Arizona",
        label: "Arizona",
        code: "AZ"
    }, {
        name: "Arkansas",
        label: "Arkansas",
        code: "AR"
    }, {
        name: "Armed Forces Europe",
        label: "Armed Forces Europe",
        code: "AE"
    }, {
        name: "Armed Forces Pacific",
        label: "Armed Forces Pacific",
        code: "AP"
    }, {
        name: "Armed Forces the Americas",
        label: "Armed Forces the Americas",
        code: "AA"
    }, {
        name: "California",
        label: "California",
        code: "CA"
    }, {
        name: "Colorado",
        label: "Colorado",
        code: "CO"
    }, {
        name: "Connecticut",
        label: "Connecticut",
        code: "CT"
    }, {
        name: "Delaware",
        label: "Delaware",
        code: "DE"
    }, {
        name: "District of Columbia",
        label: "District of Columbia",
        code: "DC"
    }, {
        name: "Federated States of Micronesia",
        label: "Federated States of Micronesia",
        code: "FM"
    }, {
        name: "Florida",
        label: "Florida",
        code: "FL"
    }, {
        name: "Georgia",
        label: "Georgia",
        code: "GA"
    }, {
        name: "Guam",
        label: "Guam",
        code: "GU"
    }, {
        name: "Hawaii",
        label: "Hawaii",
        code: "HI"
    }, {
        name: "Idaho",
        label: "Idaho",
        code: "ID"
    }, {
        name: "Illinois",
        label: "Illinois",
        code: "IL"
    }, {
        name: "Indiana",
        label: "Indiana",
        code: "IN"
    }, {
        name: "Iowa",
        label: "Iowa",
        code: "IA"
    }, {
        name: "Kansas",
        label: "Kansas",
        code: "KS"
    }, {
        name: "Kentucky",
        label: "Kentucky",
        code: "KY"
    }, {
        name: "Louisiana",
        label: "Louisiana",
        code: "LA"
    }, {
        name: "Maine",
        label: "Maine",
        code: "ME"
    }, {
        name: "Marshall Islands",
        label: "Marshall Islands",
        code: "MH"
    }, {
        name: "Maryland",
        label: "Maryland",
        code: "MD"
    }, {
        name: "Massachusetts",
        label: "Massachusetts",
        code: "MA"
    }, {
        name: "Michigan",
        label: "Michigan",
        code: "MI"
    }, {
        name: "Minnesota",
        label: "Minnesota",
        code: "MN"
    }, {
        name: "Mississippi",
        label: "Mississippi",
        code: "MS"
    }, {
        name: "Missouri",
        label: "Missouri",
        code: "MO"
    }, {
        name: "Montana",
        label: "Montana",
        code: "MT"
    }, {
        name: "Nebraska",
        label: "Nebraska",
        code: "NE"
    }, {
        name: "Nevada",
        label: "Nevada",
        code: "NV"
    }, {
        name: "New Hampshire",
        label: "New Hampshire",
        code: "NH"
    }, {
        name: "New Jersey",
        label: "New Jersey",
        code: "NJ"
    }, {
        name: "New Mexico",
        label: "New Mexico",
        code: "NM"
    }, {
        name: "New York",
        label: "New York",
        code: "NY"
    }, {
        name: "North Carolina",
        label: "North Carolina",
        code: "NC"
    }, {
        name: "North Dakota",
        label: "North Dakota",
        code: "ND"
    }, {
        name: "Northern Mariana Islands",
        label: "Northern Mariana Islands",
        code: "MP"
    }, {
        name: "Ohio",
        label: "Ohio",
        code: "OH"
    }, {
        name: "Oklahoma",
        label: "Oklahoma",
        code: "OK"
    }, {
        name: "Oregon",
        label: "Oregon",
        code: "OR"
    }, {
        name: "Pennsylvania",
        label: "Pennsylvania",
        code: "PA"
    }, {
        name: "Puerto Rico",
        label: "Puerto Rico",
        code: "PR"
    }, {
        name: "Rhode Island",
        label: "Rhode Island",
        code: "RI"
    }, {
        name: "South Carolina",
        label: "South Carolina",
        code: "SC"
    }, {
        name: "South Dakota",
        label: "South Dakota",
        code: "SD"
    }, {
        name: "Tennessee",
        label: "Tennessee",
        code: "TN"
    }, {
        name: "Texas",
        label: "Texas",
        code: "TX"
    }, {
        name: "Utah",
        label: "Utah",
        code: "UT"
    }, {
        name: "Vermont",
        label: "Vermont",
        code: "VT"
    }, {
        name: "Virgin Islands, U.S.",
        label: "Virgin Islands, U.S.",
        code: "VI"
    }, {
        name: "Virginia",
        label: "Virginia",
        code: "VA"
    }, {
        name: "Washington",
        label: "Washington",
        code: "WA"
    }, {
        name: "West Virginia",
        label: "West Virginia",
        code: "WV"
    }, {
        name: "Wisconsin",
        label: "Wisconsin",
        code: "WI"
    }, {
        name: "Wyoming",
        label: "Wyoming",
        code: "WY"
    }];

function get_browser() {
    var tem, ua = navigator.userAgent,
        M = ua.match(/(opera|chrome|safari|firefox|msie|trident(?=\/))\/?\s*(\d+)/i) || [];
    return /trident/i.test(M[1]) ? "IE " + ((tem = /\brv[ :]+(\d+)/g.exec(ua) || [])[1] || "") : "Chrome" === M[1] && null != (tem = ua.match(/\bOPR\/(\d+)/)) ? "Opera " + tem[1] : (M = M[2] ? [M[1], M[2]] : [navigator.appName, navigator.appVersion, "-?"], null != (tem = ua.match(/version\/(\d+)/i)) && M.splice(1, 1, tem[1]), M[0])
}

function get_browser_version() {
    var tem, ua = navigator.userAgent,
        M = ua.match(/(opera|chrome|safari|firefox|msie|trident(?=\/))\/?\s*(\d+)/i) || [];
    return /trident/i.test(M[1]) ? "IE " + ((tem = /\brv[ :]+(\d+)/g.exec(ua) || [])[1] || "") : "Chrome" === M[1] && null != (tem = ua.match(/\bOPR\/(\d+)/)) ? "Opera " + tem[1] : (M = M[2] ? [M[1], M[2]] : [navigator.appName, navigator.appVersion, "-?"], null != (tem = ua.match(/version\/(\d+)/i)) && M.splice(1, 1, tem[1]), M[1])
}

function findHHandWW() {
    return imgHeight = this.height, imgWidth = this.width, !0
}

function showImage(imgPath) {
    var myImage = new Image;
    myImage.name = imgPath, myImage.onload = findHHandWW, myImage.src = imgPath
}

function log(className, prefix, obj) {
    if (prefix = "    " + prefix + ": ", obj instanceof Array) obj.forEach(function(entry) {
        log(className, "item", entry)
    });
    else
        for (key in console.log(className + ":"), obj) console.log(prefix + key + ": " + obj[key]), "formats" === key && obj[key].forEach(function(entry) {
            log(className, "    format", entry)
        }), "versions" === key && obj[key].forEach(function(entry) {
            log(className, "    versions", entry)
        })
}

function ExtendedID() {}

function getAbbrName(name, len) {
    return name && name.length > len ? name.slice(0, len) + "..." : name
}

function convertArrayToCommaSeperatedString(ids) {
    var idsToString = "";
    return ids.forEach(function(id) {
        idsToString += id + ","
    }), idsToString = idsToString.slice(0, -1)
}

function getFormattedName(input) {
    for (; - 1 != input.indexOf(",");) input = input.replace(",", " ");
    for (; - 1 != input.indexOf("&");) input = input.replace("&", "and");
    for (; - 1 != input.indexOf("/");) input = input.replace("/", " ");
    for (; - 1 != input.indexOf("'");) input = input.replace("'", " ");
    for (; - 1 != input.indexOf("(");) input = input.replace("(", " ");
    for (; - 1 != input.indexOf(")");) input = input.replace(")", " ");
    for (; - 1 != input.indexOf(":");) input = input.replace(":", " ");
    for (; - 1 != input.indexOf("  ");) input = input.replace("  ", " ");
    return input
}

function getUID() {
    var d = (new Date).getTime();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function(c) {
        var r = (d + 16 * Math.random()) % 16 | 0;
        return d = Math.floor(d / 16), ("x" == c ? r : 3 & r | 8).toString(16)
    })
}

function getStringPosition(string, subString, index) {
    return string.split(subString, index).join(subString).length
}

function gup(name, url) {
    url || (url = location.href), name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var results = new RegExp("[\\?&]" + name + "=([^&#]*)").exec(url);
    return null == results ? null : results[1]
}

function checkVersion(tv, uv) {
    var updaterVersion = uv;
    if (tv === updaterVersion) return !1;
    var splitThis = tv.split("."),
        splitThisInt = [];
    splitThis.forEach(function(string) {
        splitThisInt.push(parseInt(string))
    });
    var splitUpdater = updaterVersion.split("."),
        splitUpdaterInt = [];
    return splitUpdater.forEach(function(string) {
        splitUpdaterInt.push(parseInt(string))
    }), splitUpdaterInt[0] > splitThisInt[0] || (splitUpdaterInt[0] >= splitThisInt[0] && splitUpdaterInt[1] > splitThisInt[1] || splitUpdaterInt[0] >= splitThisInt[0] && splitUpdaterInt[1] >= splitThisInt[1] && splitUpdaterInt[2] > splitThisInt[2])
}

function getConvertedVideoStandard(vs) {
    var standard;
    switch (parseInt(vs)) {
        case 0:
            standard = "Multimedia / Unknown";
            break;
        case 1:
            standard = "NTSC D1";
            break;
        case 2:
            standard = "NTSC DV";
            break;
        case 3:
            standard = "PAL / PAL DV";
            break;
        case 4:
            standard = "HD 1080";
            break;
        case 5:
            standard = "HDV 720p";
            break;
        case 6:
            standard = "Other Hi-Def";
            break;
        case 7:
            standard = "Multimedia";
            break;
        case 8:
            standard = "HDV 1080i";
            break;
        case 9:
            standard = "HD 720";
            break;
        case 10:
            standard = "4k+";
            break;
        case 100:
            standard = "Music";
            break;
        case 101:
            standard = "Sound effect";
            break;
        case 200:
            standard = "AE";
            break;
        case 300:
            standard = "Photo";
            break;
        case 301:
            standard = "Illustration";
            break;
        case 400:
            standard = "3D"
    }
    return standard
}

function getMediaType(vs) {
    var type;
    switch (vs) {
        case "Music":
        case "Sound effect":
        case "Photo":
        case "Illustration":
        case "AE":
            type = vs;
            break;
        default:
            type = "Video"
    }
    return type
}
Number.prototype.formatMoney = function(decPlaces, thouSeparator, decSeparator, currencySymbol) {
        decPlaces = isNaN(decPlaces = Math.abs(decPlaces)) ? 2 : decPlaces, decSeparator = null == decSeparator ? "." : decSeparator, thouSeparator = null == thouSeparator ? "," : thouSeparator, currencySymbol = null == currencySymbol ? "$" : currencySymbol;
        var n = this,
            sign = n < 0 ? "-" : "",
            i = parseInt(n = Math.abs(+n || 0).toFixed(decPlaces)) + "",
            j = 3 < (j = i.length) ? j % 3 : 0;
        return sign + currencySymbol + (j ? i.substr(0, j) + thouSeparator : "") + i.substr(j).replace(/(\d{3})(?=\d)/g, "$1" + thouSeparator) + (decPlaces ? decSeparator + Math.abs(n - i).toFixed(decPlaces).slice(2) : "")
    },
    function() {
        function Point(x, y) {
            this.x = x || 0, this.y = y || 0
        }
        Point.prototype.x = null, Point.prototype.y = null, Point.prototype.add = function(v) {
            return new Point(this.x + v.x, this.y + v.y)
        }, Point.prototype.clone = function() {
            return new Point(this.x, this.y)
        }, Point.prototype.degreesTo = function(v) {
            var dx = this.x - v.x,
                dy = this.y - v.y;
            return Math.atan2(dy, dx) * (180 / Math.PI)
        }, Point.prototype.distance = function(v) {
            var x = this.x - v.x,
                y = this.y - v.y;
            return Math.sqrt(x * x + y * y)
        }, Point.prototype.equals = function(toCompare) {
            return this.x == toCompare.x && this.y == toCompare.y
        }, Point.prototype.interpolate = function(v, f) {
            return new Point((this.x + v.x) * f, (this.y + v.y) * f)
        }, Point.prototype.length = function() {
            return Math.sqrt(this.x * this.x + this.y * this.y)
        }, Point.prototype.normalize = function(thickness) {
            var l = this.length();
            this.x = this.x / l * thickness, this.y = this.y / l * thickness
        }, Point.prototype.orbit = function(origin, arcWidth, arcHeight, degrees) {
            var radians = degrees * (Math.PI / 180);
            this.x = origin.x + arcWidth * Math.cos(radians), this.y = origin.y + arcHeight * Math.sin(radians)
        }, Point.prototype.offset = function(dx, dy) {
            this.x += dx, this.y += dy
        }, Point.prototype.subtract = function(v) {
            return new Point(this.x - v.x, this.y - v.y)
        }, Point.prototype.toString = function() {
            return "(x=" + this.x + ", y=" + this.y + ")"
        }, Point.interpolate = function(pt1, pt2, f) {
            return new Point((pt1.x + pt2.x) * f, (pt1.y + pt2.y) * f)
        }, Point.polar = function(len, angle) {
            return new Point(len * Math.sin(angle), len * Math.cos(angle))
        }, Point.distance = function(pt1, pt2) {
            var x = pt1.x - pt2.x,
                y = pt1.y - pt2.y;
            return Math.sqrt(x * x + y * y)
        }, this.Point = window.Point = Point
    }(), ExtendedID.extend = function(id) {
        if (id) {
            for (var extendedID = id.toString(); extendedID.length < 9;) extendedID = "0" + extendedID;
            return extendedID
        }
    }, String.prototype.insert = function(index, string) {
        return 0 < index ? this.substring(0, index) + string + this.substring(index, this.length) : string + this
    }, String.prototype.replaceAll = function(search, replacement) {
        return this.replace(new RegExp(search, "g"), replacement)
    }, getMousePosition = function(element) {
        for (var xPosition = 0, yPosition = 0; element;) xPosition += element.offsetLeft - element.scrollLeft + element.clientLeft, yPosition += element.offsetTop - element.scrollTop + element.clientTop, element = element.offsetParent;
        return {
            x: xPosition,
            y: yPosition
        }
    }, getScroll = function() {
        if (null != window.pageYOffset) return [pageXOffset, pageYOffset];
        var d = document,
            r = d.documentElement,
            b = d.body;
        return [r.scrollLeft || b.scrollLeft || 0, r.scrollTop || b.scrollTop || 0]
    }, getUserHome = function() {
        return require("os").homedir()
    }, getName = function(input) {
        for (; - 1 != input.indexOf(",");) input = input.replace(",", " ");
        for (; - 1 != input.indexOf("&");) input = input.replace("&", "and");
        for (; - 1 != input.indexOf("/");) input = input.replace("/", " ");
        for (; - 1 != input.indexOf("'");) input = input.replace("'", " ");
        for (; - 1 != input.indexOf("(");) input = input.replace("(", " ");
        for (; - 1 != input.indexOf(")");) input = input.replace(")", " ");
        for (; - 1 != input.indexOf(":");) input = input.replace(":", " ");
        return input
    }, getPosition = function(element) {
        for (var xPosition = 0, yPosition = 0; element;) xPosition += element.offsetLeft - element.scrollLeft + element.clientLeft, yPosition += element.offsetTop - element.scrollTop + element.clientTop, element = element.offsetParent;
        return {
            x: xPosition,
            y: yPosition
        }
    }, getChromeVersion = function() {
        var raw = navigator.userAgent.match(/Chrom(e|ium)\/([0-9]+)\./);
        return !!raw && parseInt(raw[2], 10)
    };
