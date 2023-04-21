// Copyright 2023, Ayon, All rights reserved.
#include "Ayon.h"

#include "ISettingsContainer.h"
#include "ISettingsModule.h"
#include "ISettingsSection.h"
#include "AyonStyle.h"
#include "AyonCommands.h"
#include "AyonPythonBridge.h"
#include "AyonSettings.h"
#include "ToolMenus.h"


static const FName AyonTabName("Ayon");

#define LOCTEXT_NAMESPACE "FAyonModule"

// This function is triggered when the plugin is staring up
void FAyonModule::StartupModule()
{
	FAyonStyle::Initialize();
	FAyonStyle::ReloadTextures();
	FAyonCommands::Register();

	PluginCommands = MakeShareable(new FUICommandList);

	PluginCommands->MapAction(
		FAyonCommands::Get().AyonTools,
		FExecuteAction::CreateRaw(this, &FAyonModule::MenuPopup),
		FCanExecuteAction());
	PluginCommands->MapAction(
		FAyonCommands::Get().AyonToolsDialog,
		FExecuteAction::CreateRaw(this, &FAyonModule::MenuDialog),
		FCanExecuteAction());

	UToolMenus::RegisterStartupCallback(
		FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FAyonModule::RegisterMenus));

	RegisterSettings();
}

void FAyonModule::ShutdownModule()
{
	UToolMenus::UnRegisterStartupCallback(this);

	UToolMenus::UnregisterOwner(this);

	FAyonStyle::Shutdown();

	FAyonCommands::Unregister();
}


void FAyonModule::RegisterSettings()
{
	ISettingsModule& SettingsModule = FModuleManager::LoadModuleChecked<ISettingsModule>("Settings");

	// Create the new category
	// TODO: After the movement of the plugin from the game to editor, it might be necessary to move this!
	ISettingsContainerPtr SettingsContainer = SettingsModule.GetContainer("Project");

	UAyonSettings* Settings = GetMutableDefault<UAyonSettings>();

	// Register the settings
	ISettingsSectionPtr SettingsSection = SettingsModule.RegisterSettings("Project", "Ayon", "General",
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
		SettingsSection->OnModified().BindRaw(this, &FAyonModule::HandleSettingsSaved);
	}
}

bool FAyonModule::HandleSettingsSaved()
{
	UAyonSettings* Settings = GetMutableDefault<UAyonSettings>();
	bool ResaveSettings = false;

	// You can put any validation code in here and resave the settings in case an invalid
	// value has been entered

	if (ResaveSettings)
	{
		Settings->SaveConfig();
	}

	return true;
}

void FAyonModule::RegisterMenus()
{
	// Owner will be used for cleanup in call to UToolMenus::UnregisterOwner
	FToolMenuOwnerScoped OwnerScoped(this);

	{
		UToolMenu* Menu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Tools");
		{
			// FToolMenuSection& Section = Menu->FindOrAddSection("Ayon");
			FToolMenuSection& Section = Menu->AddSection(
				"Ayon",
				TAttribute<FText>(FText::FromString("Ayon")),
				FToolMenuInsert("Programming", EToolMenuInsertType::Before)
			);
			Section.AddMenuEntryWithCommandList(FAyonCommands::Get().AyonTools, PluginCommands);
			Section.AddMenuEntryWithCommandList(FAyonCommands::Get().AyonToolsDialog, PluginCommands);
		}
		UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar.PlayToolBar");
		{
			FToolMenuSection& Section = ToolbarMenu->FindOrAddSection("PluginTools");
			{
				FToolMenuEntry& Entry = Section.AddEntry(
					FToolMenuEntry::InitToolBarButton(FAyonCommands::Get().AyonTools));
				Entry.SetCommandList(PluginCommands);
			}
		}
	}
}


void FAyonModule::MenuPopup()
{
	UAyonPythonBridge* bridge = UAyonPythonBridge::Get();
	bridge->RunInPython_Popup();
}

void FAyonModule::MenuDialog()
{
	UAyonPythonBridge* bridge = UAyonPythonBridge::Get();
	bridge->RunInPython_Dialog();
}

IMPLEMENT_MODULE(FAyonModule, Ayon)
