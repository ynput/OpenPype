#include "OpenPype.h"
#include "OpenPypeStyle.h"
#include "OpenPypeCommands.h"
#include "OpenPypeCommunication.h"
#include "OpenPypePythonBridge.h"
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

	UE_LOG(LogTemp, Warning, TEXT("OpenPype Plugin Started"));

	FOpenPypeCommunication::CreateSocket();
	FOpenPypeCommunication::ConnectToSocket();

	MapCommands();

	UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FOpenPypeModule::RegisterMenus));
}

void FOpenPypeModule::ShutdownModule()
{
	FOpenPypeCommunication::CloseConnection();

	UToolMenus::UnRegisterStartupCallback(this);

	UToolMenus::UnregisterOwner(this);

	FOpenPypeStyle::Shutdown();

	FOpenPypeCommands::Unregister();
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
			Section.AddMenuEntryWithCommandList(FOpenPypeCommands::Get().OpenPypeTestMethod, PluginCommands);
		}
		UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar.PlayToolBar");
		{
			FToolMenuSection& Section = ToolbarMenu->FindOrAddSection("PluginTools");
			{
				FToolMenuEntry& Entry = Section.AddEntry(FToolMenuEntry::InitToolBarButton(FOpenPypeCommands::Get().OpenPypeTestMethod));
				Entry.SetCommandList(PluginCommands);
			}
		}
	}
}

void FOpenPypeModule::MapCommands()
{
	PluginCommands = MakeShareable(new FUICommandList);

	PluginCommands->MapAction(
		FOpenPypeCommands::Get().OpenPypeTools,
		FExecuteAction::CreateRaw(this, &FOpenPypeModule::MenuPopup),
		FCanExecuteAction());
	PluginCommands->MapAction(
		FOpenPypeCommands::Get().OpenPypeToolsDialog,
		FExecuteAction::CreateRaw(this, &FOpenPypeModule::MenuDialog),
		FCanExecuteAction());
	PluginCommands->MapAction(
		FOpenPypeCommands::Get().OpenPypeTestMethod,
		FExecuteAction::CreateRaw(this, &FOpenPypeModule::TestMethod),
		FCanExecuteAction());
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

void FOpenPypeModule::TestMethod()
{
	FOpenPypeCommunication::CallMethod("loader_tool", TArray<FString>());
}

IMPLEMENT_MODULE(FOpenPypeModule, OpenPype)
