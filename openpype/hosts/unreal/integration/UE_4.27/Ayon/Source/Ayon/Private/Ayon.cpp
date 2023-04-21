// Copyright 2023, Ayon, All rights reserved.
#include "Ayon.h"

#include "ISettingsContainer.h"
#include "ISettingsModule.h"
#include "ISettingsSection.h"
#include "LevelEditor.h"
#include "AyonPythonBridge.h"
#include "AyonSettings.h"
#include "AyonStyle.h"
#include "Modules/ModuleManager.h"


static const FName AyonTabName("Ayon");

#define LOCTEXT_NAMESPACE "FAyonModule"

// This function is triggered when the plugin is staring up
void FAyonModule::StartupModule()
{
	if (!IsRunningCommandlet()) {
		FAyonStyle::Initialize();
		FAyonStyle::SetIcon("Logo", "ayon40");

		// Create the Extender that will add content to the menu
		FLevelEditorModule& LevelEditorModule = FModuleManager::LoadModuleChecked<FLevelEditorModule>("LevelEditor");

		TSharedPtr<FExtender> MenuExtender = MakeShareable(new FExtender());
		TSharedPtr<FExtender> ToolbarExtender = MakeShareable(new FExtender());

		MenuExtender->AddMenuExtension(
			"LevelEditor",
			EExtensionHook::After,
			NULL,
			FMenuExtensionDelegate::CreateRaw(this, &FAyonModule::AddMenuEntry)
		);
		ToolbarExtender->AddToolBarExtension(
			"Settings",
			EExtensionHook::After,
			NULL,
			FToolBarExtensionDelegate::CreateRaw(this, &FAyonModule::AddToobarEntry));


		LevelEditorModule.GetMenuExtensibilityManager()->AddExtender(MenuExtender);
		LevelEditorModule.GetToolBarExtensibilityManager()->AddExtender(ToolbarExtender);

		RegisterSettings();
	}
}

void FAyonModule::ShutdownModule()
{
	FAyonStyle::Shutdown();
}


void FAyonModule::AddMenuEntry(FMenuBuilder& MenuBuilder)
{
	// Create Section
	MenuBuilder.BeginSection("Ayon", TAttribute<FText>(FText::FromString("Ayon")));
	{
		// Create a Submenu inside of the Section
		MenuBuilder.AddMenuEntry(
			FText::FromString("Tools..."),
			FText::FromString("Pipeline tools"),
			FSlateIcon(FAyonStyle::GetStyleSetName(), "Ayon.Logo"),
			FUIAction(FExecuteAction::CreateRaw(this, &FAyonModule::MenuPopup))
		);

		MenuBuilder.AddMenuEntry(
			FText::FromString("Tools dialog..."),
			FText::FromString("Pipeline tools dialog"),
			FSlateIcon(FAyonStyle::GetStyleSetName(), "Ayon.Logo"),
			FUIAction(FExecuteAction::CreateRaw(this, &FAyonModule::MenuDialog))
		);
	}
	MenuBuilder.EndSection();
}

void FAyonModule::AddToobarEntry(FToolBarBuilder& ToolbarBuilder)
{
	ToolbarBuilder.BeginSection(TEXT("Ayon"));
	{
		ToolbarBuilder.AddToolBarButton(
			FUIAction(
				FExecuteAction::CreateRaw(this, &FAyonModule::MenuPopup),
				NULL,
				FIsActionChecked()

			),
			NAME_None,
			LOCTEXT("Ayon_label", "Ayon"),
			LOCTEXT("Ayon_tooltip", "Ayon Tools"),
			FSlateIcon(FAyonStyle::GetStyleSetName(), "Ayon.Logo")
		);
	}
	ToolbarBuilder.EndSection();
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
