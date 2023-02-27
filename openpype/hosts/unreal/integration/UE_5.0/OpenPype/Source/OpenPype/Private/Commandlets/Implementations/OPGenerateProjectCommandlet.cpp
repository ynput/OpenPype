// Copyright 2023, Ayon, All rights reserved.
#include "Commandlets/Implementations/OPGenerateProjectCommandlet.h"

#include "Editor.h"
#include "GameProjectUtils.h"
#include "OPConstants.h"
#include "Commandlets/OPActionResult.h"
#include "ProjectDescriptor.h"

int32 UOPGenerateProjectCommandlet::Main(const FString& CommandLineParams)
{
	//Parses command line parameters & creates structure FProjectInformation
	const FOPGenerateProjectParams ParsedParams = FOPGenerateProjectParams(CommandLineParams);
	ProjectInformation = ParsedParams.GenerateUEProjectInformation();

	//Creates .uproject & other UE files
	EVALUATE_OP_ACTION_RESULT(TryCreateProject());

	//Loads created .uproject
	EVALUATE_OP_ACTION_RESULT(TryLoadProjectDescriptor());

	//Adds needed plugin to .uproject
	AttachPluginsToProjectDescriptor();

	//Saves .uproject
	EVALUATE_OP_ACTION_RESULT(TrySave());

	//When we are here, there should not be problems in generating Unreal Project for OpenPype
	return 0;
}


FOPGenerateProjectParams::FOPGenerateProjectParams(): FOPGenerateProjectParams("")
{
}

FOPGenerateProjectParams::FOPGenerateProjectParams(const FString& CommandLineParams): CommandLineParams(
	CommandLineParams)
{
	UCommandlet::ParseCommandLine(*CommandLineParams, Tokens, Switches);
}

FProjectInformation FOPGenerateProjectParams::GenerateUEProjectInformation() const
{
	FProjectInformation ProjectInformation = FProjectInformation();
	ProjectInformation.ProjectFilename = GetProjectFileName();

	ProjectInformation.bShouldGenerateCode = IsSwitchPresent("GenerateCode");

	return ProjectInformation;
}

FString FOPGenerateProjectParams::TryGetToken(const int32 Index) const
{
	return Tokens.IsValidIndex(Index) ? Tokens[Index] : "";
}

FString FOPGenerateProjectParams::GetProjectFileName() const
{
	return TryGetToken(0);
}

bool FOPGenerateProjectParams::IsSwitchPresent(const FString& Switch) const
{
	return INDEX_NONE != Switches.IndexOfByPredicate([&Switch](const FString& Item) -> bool
		{
			return Item.Equals(Switch);
		}
	);
}


UOPGenerateProjectCommandlet::UOPGenerateProjectCommandlet()
{
	LogToConsole = true;
}

FOP_ActionResult UOPGenerateProjectCommandlet::TryCreateProject() const
{
	FText FailReason;
	FText FailLog;
	TArray<FString> OutCreatedFiles;

	if (!GameProjectUtils::CreateProject(ProjectInformation, FailReason, FailLog, &OutCreatedFiles))
		return FOP_ActionResult(EOP_ActionResult::ProjectNotCreated, FailReason);
	return FOP_ActionResult();
}

FOP_ActionResult UOPGenerateProjectCommandlet::TryLoadProjectDescriptor()
{
	FText FailReason;
	const bool bLoaded = ProjectDescriptor.Load(ProjectInformation.ProjectFilename, FailReason);

	return FOP_ActionResult(bLoaded ? EOP_ActionResult::Ok : EOP_ActionResult::ProjectNotLoaded, FailReason);
}

void UOPGenerateProjectCommandlet::AttachPluginsToProjectDescriptor()
{
	FPluginReferenceDescriptor OPPluginDescriptor;
	OPPluginDescriptor.bEnabled = true;
	OPPluginDescriptor.Name = OPConstants::OP_PluginName;
	ProjectDescriptor.Plugins.Add(OPPluginDescriptor);

	FPluginReferenceDescriptor PythonPluginDescriptor;
	PythonPluginDescriptor.bEnabled = true;
	PythonPluginDescriptor.Name = OPConstants::PythonScript_PluginName;
	ProjectDescriptor.Plugins.Add(PythonPluginDescriptor);

	FPluginReferenceDescriptor SequencerScriptingPluginDescriptor;
	SequencerScriptingPluginDescriptor.bEnabled = true;
	SequencerScriptingPluginDescriptor.Name = OPConstants::SequencerScripting_PluginName;
	ProjectDescriptor.Plugins.Add(SequencerScriptingPluginDescriptor);

	FPluginReferenceDescriptor MovieRenderPipelinePluginDescriptor;
	MovieRenderPipelinePluginDescriptor.bEnabled = true;
	MovieRenderPipelinePluginDescriptor.Name = OPConstants::MovieRenderPipeline_PluginName;
	ProjectDescriptor.Plugins.Add(MovieRenderPipelinePluginDescriptor);

	FPluginReferenceDescriptor EditorScriptingPluginDescriptor;
	EditorScriptingPluginDescriptor.bEnabled = true;
	EditorScriptingPluginDescriptor.Name = OPConstants::EditorScriptingUtils_PluginName;
	ProjectDescriptor.Plugins.Add(EditorScriptingPluginDescriptor);
}

FOP_ActionResult UOPGenerateProjectCommandlet::TrySave()
{
	FText FailReason;
	const bool bSaved = ProjectDescriptor.Save(ProjectInformation.ProjectFilename, FailReason);

	return FOP_ActionResult(bSaved ? EOP_ActionResult::Ok : EOP_ActionResult::ProjectNotSaved, FailReason);
}

FOPGenerateProjectParams UOPGenerateProjectCommandlet::ParseParameters(const FString& Params) const
{
	FOPGenerateProjectParams ParamsResult;

	TArray<FString> Tokens, Switches;
	ParseCommandLine(*Params, Tokens, Switches);

	return ParamsResult;
}
