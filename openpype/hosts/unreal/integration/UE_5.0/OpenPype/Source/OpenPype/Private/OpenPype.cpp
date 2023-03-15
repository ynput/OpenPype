// Copyright 2023, Ayon, All rights reserved.
#include "OpenPype.h"

#include "ISettingsContainer.h"
#include "ISettingsModule.h"
#include "ISettingsSection.h"
#include "OpenPypeStyle.h"
#include "OpenPypeCommands.h"
#include "OpenPypeCommunication.h"
#include "OpenPypePythonBridge.h"
#include "OpenPypeSettings.h"
#include "LevelEditor.h"
#include "Misc/MessageDialog.h"
#include "ToolMenus.h"


static const FName OpenPypeTabName("OpenPype");

#define LOCTEXT_NAMESPACE "FOpenPypeModule"

// This function is triggered when the plugin is staring up
void FOpenPypeModule::StartupModule()
{
	if(!FModuleManager::Get().IsModuleLoaded("WebSockets"))
	{
		FModuleManager::Get().LoadModule("WebSockets");
	}

	FOpenPypeStyle::Initialize();
	FOpenPypeStyle::ReloadTextures();
	FOpenPypeCommands::Register();

	FOpenPypeCommunication::CreateSocket();
	FOpenPypeCommunication::ConnectToSocket();

	MapCommands();

	UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FOpenPypeModule::RegisterMenus));

	RegisterSettings();
}

void FOpenPypeModule::ShutdownModule()
{
	FOpenPypeCommunication::CloseConnection();

	UToolMenus::UnRegisterStartupCallback(this);

	UToolMenus::UnregisterOwner(this);

	FOpenPypeStyle::Shutdown();

	FOpenPypeCommands::Unregister();
}

TSharedRef<SWidget> FOpenPypeModule::GenerateOpenPypeMenuContent(TSharedRef<FUICommandList> InCommandList)
{
	FToolMenuContext MenuContext(InCommandList);

	return UToolMenus::Get()->GenerateWidget("LevelEditor.LevelEditorToolBar.OpenPype", MenuContext);
}

void FOpenPypeModule::RegisterSettings()
{
	ISettingsModule& SettingsModule = FModuleManager::LoadModuleChecked<ISettingsModule>("Settings");

	// Create the new category
	// TODO: After the movement of the plugin from the game to editor, it might be necessary to move this!
	ISettingsContainerPtr SettingsContainer = SettingsModule.GetContainer("Project");

	UOpenPypeSettings* Settings = GetMutableDefault<UOpenPypeSettings>();

	// Register the settings
	ISettingsSectionPtr SettingsSection = SettingsModule.RegisterSettings("Project", "OpenPype", "General",
	                                                                      LOCTEXT("RuntimeGeneralSettingsName",
		                                                                      "General"),
	                                                                      LOCTEXT("RuntimeGeneralSettingsDescription",
		                                                                      "Base configuration for Open Pype Module"),
	                                                                      Settings
	);

	// Register the save handler to your settings, you might want to use it to
	// validate those or just act to settings changes.
	if (SettingsSection.IsValid())
	{
		SettingsSection->OnModified().BindRaw(this, &FOpenPypeModule::HandleSettingsSaved);
	}
}

bool FOpenPypeModule::HandleSettingsSaved()
{
	UOpenPypeSettings* Settings = GetMutableDefault<UOpenPypeSettings>();
	bool ResaveSettings = false;

	// You can put any validation code in here and resave the settings in case an invalid
	// value has been entered

	if (ResaveSettings)
	{
		Settings->SaveConfig();
	}

	return true;
}

void FOpenPypeModule::CallMethod(const FString MethodName, const TArray<FString> Args)
{
	FOpenPypeCommunication::CallMethod(MethodName, Args);
}

void FOpenPypeModule::RegisterMenus()
{
	// Owner will be used for cleanup in call to UToolMenus::UnregisterOwner
	FToolMenuOwnerScoped OwnerScoped(this);

	RegisterOpenPypeMenu();

	UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar.User");

	FToolMenuSection& Section = ToolbarMenu->AddSection("OpenPype");

	FToolMenuEntry OpenPypeEntry = FToolMenuEntry::InitComboButton(
		"OpenPype Menu",
		FUIAction(),
		FOnGetContent::CreateStatic(&FOpenPypeModule::GenerateOpenPypeMenuContent, OpenPypeCommands.ToSharedRef()),
		LOCTEXT("OpenPypeMenu_Label", "OpenPype"),
		LOCTEXT("OpenPypeMenu_Tooltip", "Open OpenPype Menu"),
		FSlateIcon(FOpenPypeStyle::GetStyleSetName(), "OpenPype.OpenPypeMenu")
	);
	Section.AddEntry(OpenPypeEntry);
}

void FOpenPypeModule::RegisterOpenPypeMenu()
{
	UToolMenu* OpenPypeMenu = UToolMenus::Get()->RegisterMenu("LevelEditor.LevelEditorToolBar.OpenPype");
	{
		FToolMenuSection& Section = OpenPypeMenu->AddSection("OpenPype");

		Section.InitSection("OpenPype", LOCTEXT("OpenPype_Label", "OpenPype"), FToolMenuInsert(NAME_None, EToolMenuInsertType::First));

		Section.AddMenuEntry(FOpenPypeCommands::Get().OpenPypeLoaderTool);
		Section.AddMenuEntry(FOpenPypeCommands::Get().OpenPypeCreatorTool);
		Section.AddMenuEntry(FOpenPypeCommands::Get().OpenPypeSceneInventoryTool);
		Section.AddMenuEntry(FOpenPypeCommands::Get().OpenPypePublishTool);
	}
}

void FOpenPypeModule::MapCommands()
{
	OpenPypeCommands = MakeShareable(new FUICommandList);

	OpenPypeCommands->MapAction(
		FOpenPypeCommands::Get().OpenPypeLoaderTool,
		FExecuteAction::CreateStatic(&FOpenPypeModule::CallMethod, FString("loader_tool"), TArray<FString>()),
		FCanExecuteAction());
	OpenPypeCommands->MapAction(
		FOpenPypeCommands::Get().OpenPypeCreatorTool,
		FExecuteAction::CreateStatic(&FOpenPypeModule::CallMethod, FString("creator_tool"), TArray<FString>()),
		FCanExecuteAction());
	OpenPypeCommands->MapAction(
		FOpenPypeCommands::Get().OpenPypeSceneInventoryTool,
		FExecuteAction::CreateStatic(&FOpenPypeModule::CallMethod, FString("scene_inventory_tool"), TArray<FString>()),
		FCanExecuteAction());
	OpenPypeCommands->MapAction(
		FOpenPypeCommands::Get().OpenPypePublishTool,
		FExecuteAction::CreateStatic(&FOpenPypeModule::CallMethod, FString("publish_tool"), TArray<FString>()),
		FCanExecuteAction());
}

IMPLEMENT_MODULE(FOpenPypeModule, OpenPype)
