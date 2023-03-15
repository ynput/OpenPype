#include "OpenPype.h"
#include "OpenPypeStyle.h"
#include "OpenPypeCommands.h"
#include "OpenPypeCommunication.h"
#include "LevelEditor.h"
#include "Misc/MessageDialog.h"
#include "LevelEditorMenuContext.h"
#include "ToolMenus.h"


static const FName OpenPypeTabName("OpenPype");

#define LOCTEXT_NAMESPACE "OpenPypeModule"

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

TSharedRef<SWidget> FOpenPypeModule::GenerateOpenPypeMenuContent(TSharedRef<FUICommandList> InCommandList)
{
	FToolMenuContext MenuContext(InCommandList);

	return UToolMenus::Get()->GenerateWidget("LevelEditor.LevelEditorToolBar.OpenPype", MenuContext);
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
