#include "OpenPype.h"

#include "ISettingsContainer.h"
#include "ISettingsModule.h"
#include "ISettingsSection.h"
#include "OpenPypeStyle.h"
#include "OpenPypeCommands.h"
#include "OpenPypePythonBridge.h"
#include "OpenPypeSettings.h"
#include "Misc/MessageDialog.h"
#include "ToolMenus.h"


static const FName OpenPypeTabName("OpenPype");

#define LOCTEXT_NAMESPACE "FOpenPypeModule"

// This function is triggered when the plugin is staring up
void FOpenPypeModule::StartupModule()
{
	FOpenPypeStyle::Initialize();
	FOpenPypeStyle::ReloadTextures();
	FOpenPypeCommands::Register();

	PluginCommands = MakeShareable(new FUICommandList);

	PluginCommands->MapAction(
		FOpenPypeCommands::Get().OpenPypeTools,
		FExecuteAction::CreateRaw(this, &FOpenPypeModule::MenuPopup),
		FCanExecuteAction());
	PluginCommands->MapAction(
		FOpenPypeCommands::Get().OpenPypeToolsDialog,
		FExecuteAction::CreateRaw(this, &FOpenPypeModule::MenuDialog),
		FCanExecuteAction());

	UToolMenus::RegisterStartupCallback(
		FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FOpenPypeModule::RegisterMenus));

	RegisterSettings();
}

void FOpenPypeModule::ShutdownModule()
{
	UToolMenus::UnRegisterStartupCallback(this);

	UToolMenus::UnregisterOwner(this);

	FOpenPypeStyle::Shutdown();

	FOpenPypeCommands::Unregister();
}


void FOpenPypeModule::RegisterSettings()
{
	ISettingsModule& SettingsModule = FModuleManager::LoadModuleChecked<ISettingsModule>("Settings");

	// Create the new category
	// TODO: After the movement of the plugin from the game to editor, it might be necessary to move this!
	ISettingsContainerPtr SettingsContainer = SettingsModule.GetContainer("Project");

	SettingsContainer->DescribeCategory("OpenPypeSettings",
	                                    LOCTEXT("RuntimeWDCategoryName", "OpenPypeSettings"),
	                                    LOCTEXT("RuntimeWDCategoryDescription",
	                                            "Configuration for the Open pype module"));

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

void FOpenPypeModule::RegisterMenus()
{
	// Owner will be used for cleanup in call to UToolMenus::UnregisterOwner
	FToolMenuOwnerScoped OwnerScoped(this);

	{
		UToolMenu* Menu = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu.Tools");
		{
			// FToolMenuSection& Section = Menu->FindOrAddSection("OpenPype");
			FToolMenuSection& Section = Menu->AddSection(
				"OpenPype",
				TAttribute<FText>(FText::FromString("OpenPype")),
				FToolMenuInsert("Programming", EToolMenuInsertType::Before)
			);
			Section.AddMenuEntryWithCommandList(FOpenPypeCommands::Get().OpenPypeTools, PluginCommands);
			Section.AddMenuEntryWithCommandList(FOpenPypeCommands::Get().OpenPypeToolsDialog, PluginCommands);
		}
		UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar.PlayToolBar");
		{
			FToolMenuSection& Section = ToolbarMenu->FindOrAddSection("PluginTools");
			{
				FToolMenuEntry& Entry = Section.AddEntry(
					FToolMenuEntry::InitToolBarButton(FOpenPypeCommands::Get().OpenPypeTools));
				Entry.SetCommandList(PluginCommands);
			}
		}
	}
}


void FOpenPypeModule::MenuPopup()
{
	UOpenPypePythonBridge* bridge = UOpenPypePythonBridge::Get();
	bridge->RunInPython_Popup();
}

void FOpenPypeModule::MenuDialog()
{
	UOpenPypePythonBridge* bridge = UOpenPypePythonBridge::Get();
	bridge->RunInPython_Dialog();
}

IMPLEMENT_MODULE(FOpenPypeModule, OpenPype)
