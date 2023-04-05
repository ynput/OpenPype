// Copyright 2023, Ayon, All rights reserved.
#include "Commandlets/Implementations/AyonGenerateProjectCommandlet.h"

#include "GameProjectUtils.h"
#include "AyonConstants.h"
#include "Commandlets/AyonActionResult.h"
#include "ProjectDescriptor.h"

int32 UAyonGenerateProjectCommandlet::Main(const FString& CommandLineParams)
{
	//Parses command line parameters & creates structure FProjectInformation
	const FAyonGenerateProjectParams ParsedParams = FAyonGenerateProjectParams(CommandLineParams);
	ProjectInformation = ParsedParams.GenerateUEProjectInformation();

	//Creates .uproject & other UE files
	EVALUATE_Ayon_ACTION_RESULT(TryCreateProject());

	//Loads created .uproject
	EVALUATE_Ayon_ACTION_RESULT(TryLoadProjectDescriptor());

	//Adds needed plugin to .uproject
	AttachPluginsToProjectDescriptor();

	//Saves .uproject
	EVALUATE_Ayon_ACTION_RESULT(TrySave());

	//When we are here, there should not be problems in generating Unreal Project for Ayon
	return 0;
}


FAyonGenerateProjectParams::FAyonGenerateProjectParams(): FAyonGenerateProjectParams("")
{
}

FAyonGenerateProjectParams::FAyonGenerateProjectParams(const FString& CommandLineParams): CommandLineParams(
	CommandLineParams)
{
	UCommandlet::ParseCommandLine(*CommandLineParams, Tokens, Switches);
}

FProjectInformation FAyonGenerateProjectParams::GenerateUEProjectInformation() const
{
	FProjectInformation ProjectInformation = FProjectInformation();
	ProjectInformation.ProjectFilename = GetProjectFileName();

	ProjectInformation.bShouldGenerateCode = IsSwitchPresent("GenerateCode");

	return ProjectInformation;
}

FString FAyonGenerateProjectParams::TryGetToken(const int32 Index) const
{
	return Tokens.IsValidIndex(Index) ? Tokens[Index] : "";
}

FString FAyonGenerateProjectParams::GetProjectFileName() const
{
	return TryGetToken(0);
}

bool FAyonGenerateProjectParams::IsSwitchPresent(const FString& Switch) const
{
	return INDEX_NONE != Switches.IndexOfByPredicate([&Switch](const FString& Item) -> bool
		{
			return Item.Equals(Switch);
		}
	);
}


UAyonGenerateProjectCommandlet::UAyonGenerateProjectCommandlet()
{
	LogToConsole = true;
}

FAyon_ActionResult UAyonGenerateProjectCommandlet::TryCreateProject() const
{
	FText FailReason;
	FText FailLog;
	TArray<FString> OutCreatedFiles;

	if (!GameProjectUtils::CreateProject(ProjectInformation, FailReason, FailLog, &OutCreatedFiles))
		return FAyon_ActionResult(EAyon_ActionResult::ProjectNotCreated, FailReason);
	return FAyon_ActionResult();
}

FAyon_ActionResult UAyonGenerateProjectCommandlet::TryLoadProjectDescriptor()
{
	FText FailReason;
	const bool bLoaded = ProjectDescriptor.Load(ProjectInformation.ProjectFilename, FailReason);

	return FAyon_ActionResult(bLoaded ? EAyon_ActionResult::Ok : EAyon_ActionResult::ProjectNotLoaded, FailReason);
}

void UAyonGenerateProjectCommandlet::AttachPluginsToProjectDescriptor()
{
	FPluginReferenceDescriptor AyonPluginDescriptor;
	AyonPluginDescriptor.bEnabled = true;
	AyonPluginDescriptor.Name = AyonConstants::Ayon_PluginName;
	ProjectDescriptor.Plugins.Add(AyonPluginDescriptor);

	FPluginReferenceDescriptor PythonPluginDescriptor;
	PythonPluginDescriptor.bEnabled = true;
	PythonPluginDescriptor.Name = AyonConstants::PythonScript_PluginName;
	ProjectDescriptor.Plugins.Add(PythonPluginDescriptor);

	FPluginReferenceDescriptor SequencerScriptingPluginDescriptor;
	SequencerScriptingPluginDescriptor.bEnabled = true;
	SequencerScriptingPluginDescriptor.Name = AyonConstants::SequencerScripting_PluginName;
	ProjectDescriptor.Plugins.Add(SequencerScriptingPluginDescriptor);

	FPluginReferenceDescriptor MovieRenderPipelinePluginDescriptor;
	MovieRenderPipelinePluginDescriptor.bEnabled = true;
	MovieRenderPipelinePluginDescriptor.Name = AyonConstants::MovieRenderPipeline_PluginName;
	ProjectDescriptor.Plugins.Add(MovieRenderPipelinePluginDescriptor);

	FPluginReferenceDescriptor EditorScriptingPluginDescriptor;
	EditorScriptingPluginDescriptor.bEnabled = true;
	EditorScriptingPluginDescriptor.Name = AyonConstants::EditorScriptingUtils_PluginName;
	ProjectDescriptor.Plugins.Add(EditorScriptingPluginDescriptor);
}

FAyon_ActionResult UAyonGenerateProjectCommandlet::TrySave()
{
	FText FailReason;
	const bool bSaved = ProjectDescriptor.Save(ProjectInformation.ProjectFilename, FailReason);

	return FAyon_ActionResult(bSaved ? EAyon_ActionResult::Ok : EAyon_ActionResult::ProjectNotSaved, FailReason);
}

FAyonGenerateProjectParams UAyonGenerateProjectCommandlet::ParseParameters(const FString& Params) const
{
	FAyonGenerateProjectParams ParamsResult;

	TArray<FString> Tokens, Switches;
	ParseCommandLine(*Params, Tokens, Switches);

	return ParamsResult;
}
