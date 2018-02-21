------------------------------------------------------------
-- Change various options in Loadertools, Revision: 2.1
--
--
-- place in Fusion:\Scripts\Comp 
--
-- written by Isaac Guenard (izyk@eyeonline.com) / Sean Konrad
-- created : January 24rd, 2005
-- modified by Eric Westphal (Eric@SirEdric.de), February 2007
------------------------------------------------------------


MissingFramesOpt = {"Do Not Change", "Fail", "Hold Previous", "Output Black", "Wait"}
DepthOpt={"Do Not Change", "Format", "Default", "int8", "int16", "float16", "float32"}
GeneralOpt={"Do Not Change", "Off", "On"}
HoldOpt={"Do Not Change", "Set to..."}
PixelOpt={"Do Not Change", "From File", "Default", "Custom (set below)"}

ret = comp.AskUser("SirEdric's Tweak-All-Loaders", {	
	{"AlphaSolid",  "Dropdown", Options = GeneralOpt},
	{"PostMultiply",  "Dropdown", Options = GeneralOpt},
	{"InvertAlpha",  "Dropdown", Options = GeneralOpt},
	{"MissingFrames",  "Dropdown", Options = MissingFramesOpt},
	{"Depth",  "Dropdown", Options = DepthOpt},
	{"PixelAspect",  "Dropdown", Options = PixelOpt},
	{"CustomPixelAspect",  "Position", Default={1,1} },
	{"HoldFirstOpt",  Name="Hold First Frame", "Dropdown", Options = HoldOpt},
	{"HoldFirst",  Name = "Hold first Frame for", "Screw", Default = 0, Min = 0, Max=500, Integer = true},
	{"HoldLastOpt",  Name="Hold Last Frame",  "Dropdown", Options = HoldOpt},
	{"HoldLast",  Name = "Hold first Frame for", "Screw", Default = 0, Min = 0, Max=500, Integer = true},
	{"Selected", Name = "Affect Selected Tools Only", "Checkbox", Default = 0}
	})

if ret then
	composition:StartUndo("SE_LoaderTweaker")
	MyPixX=ret.CustomPixelAspect[1]
	MyPixY=ret.CustomPixelAspect[2]
	print(MyPixX.."bb".. MyPixY)
	print()
	print("SE_LoaderTweaker is about to change...")
	print("...AlphaSolid to ["..GeneralOpt[ret.AlphaSolid+1].."]")
	print("...PostMultiply to ["..GeneralOpt[ret.PostMultiply+1].."]")
	print("...InvertAlpha to ["..GeneralOpt[ret.InvertAlpha+1].."]")
	print("...Missing Frames to [".. MissingFramesOpt[ret.MissingFrames + 1].."]")
	print("...Depth to ["..DepthOpt[ret.Depth+1].."]")
	print("...PixelAspect to ["..PixelOpt[ret.PixelAspect+1].."]")
	print("...CustomPixelAspect(if selected): X="..MyPixX.." Y="..MyPixY)
	print("...Hold First Frame to ["..HoldOpt[ret.HoldFirstOpt+1]..": " .. ret.HoldFirst.."]")
	print("...Hold Last Frame to ["..HoldOpt[ret.HoldLastOpt+1]..": " .. ret.HoldLast.."]")
	if ret.Selected then
		print("...... *** on selected tools only! ***")
	end
	print("---------------------------------------------------")
	print()

	-- ((ret.Selected ==1)) will return true if the 
	-- selected checkbox is enabled.....
	
	for i, v in composition:GetToolList((ret.Selected == 1)) do
		id = v:GetAttrs().TOOLS_RegID
		MyName = v:GetAttrs().TOOLS_Name
		if id == "Loader" then
			print("Changing "..MyName.." Options:")
			if ret.AlphaSolid > 0 then -- check for 'DoNothing'
				print("MakeAlphaSolid set to: "..(ret.AlphaSolid-1))
				v.MakeAlphaSolid = (ret.AlphaSolid-1)
			end
			if ret.PostMultiply > 0 then -- check for 'DoNothing'
				print("PostMultiplyByAlpha set to: "..(ret.PostMultiply-1))
				v.PostMultiplyByAlpha = (ret.PostMultiply-1)
			end
			if ret.InvertAlpha > 0 then -- check for 'DoNothing'
				print("InvertAlpha set to: "..(ret.InvertAlpha-1))
				v.InvertAlpha = (ret.InvertAlpha-1)
			end
			if ret.MissingFrames >0 then -- check for 'DoNothing'
				print("MissingFrames set to: "..(ret.MissingFrames-1))
				v.MissingFrames = (ret.MissingFrames-1)
			end
			if ret.Depth >0 then -- check for 'DoNothing'
				print("Depth set to: "..(ret.Depth-1))
				v.Depth = (ret.Depth-1)
			end
			if ret.PixelAspect >0 then -- check for 'DoNothing'
				print("PixelAspect set to: "..(ret.PixelAspect-1))
				v.PixelAspect = (ret.PixelAspect-1)
				if ret.PixelAspect == 3 then
					v.CustomPixelAspect={MyPixX, MyPixY}
				end
			end
			if ret.HoldFirstOpt >0 then -- check for 'DoNothing'
				print("HoldFirstFrame set to: "..(ret.HoldFirst))
				v.HoldFirstFrame = (ret.HoldFirst)
			end

			if ret.HoldLastOpt >0 then -- check for 'DoNothing'
				print("HoldLastFrame set to: "..(ret.HoldLast))
				v.HoldLastFrame = (ret.HoldLast)
			end

			print(v:GetAttrs().TOOLS_Name)
		end
	end
composition:EndUndo(true)	
end

print()
