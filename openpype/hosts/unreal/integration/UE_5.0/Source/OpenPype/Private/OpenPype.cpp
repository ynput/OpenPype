#include "OpenPype.h"
#include "OpenPypeStyle.h"
#include "OpenPypeCommands.h"
#include "OpenPypePythonBridge.h"
#include "LevelEditor.h"
#include "Misc/MessageDialog.h"
#include "ToolMenus.h"
#include "GenericPlatform/GenericPlatformMisc.h"
#include "WebSocketsModule.h" // Module definition


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

	CreateSocket();
	ConnectToSocket();

	PluginCommands = MakeShareable(new FUICommandList);

	PluginCommands->MapAction(
		FOpenPypeCommands::Get().OpenPypeTools,
		FExecuteAction::CreateRaw(this, &FOpenPypeModule::MenuPopup),
		FCanExecuteAction());
	PluginCommands->MapAction(
		FOpenPypeCommands::Get().OpenPypeToolsDialog,
		FExecuteAction::CreateRaw(this, &FOpenPypeModule::MenuDialog),
		FCanExecuteAction());

	UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FOpenPypeModule::RegisterMenus));
}

void FOpenPypeModule::ShutdownModule()
{
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
		}
		UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar.PlayToolBar");
		{
			FToolMenuSection& Section = ToolbarMenu->FindOrAddSection("PluginTools");
			{
				FToolMenuEntry& Entry = Section.AddEntry(FToolMenuEntry::InitToolBarButton(FOpenPypeCommands::Get().OpenPypeTools));
				Entry.SetCommandList(PluginCommands);
			}
		}
	}
}


void FOpenPypeModule::MenuPopup() {
	UOpenPypePythonBridge* bridge = UOpenPypePythonBridge::Get();
	bridge->RunInPython_Popup();
}

void FOpenPypeModule::MenuDialog() {
	UOpenPypePythonBridge* bridge = UOpenPypePythonBridge::Get();
	bridge->RunInPython_Dialog();
}

void FOpenPypeModule::CreateSocket() {
	UE_LOG(LogTemp, Warning, TEXT("Starting web socket..."));

	FString url = FWindowsPlatformMisc::GetEnvironmentVariable(*FString("WEBSOCKET_URL"));

	UE_LOG(LogTemp, Warning, TEXT("Websocket URL: %s"), *url);

	const FString ServerURL = url; // Your server URL. You can use ws, wss or wss+insecure.
	const FString ServerProtocol = TEXT("ws");  // The WebServer protocol you want to use.

	TMap<FString, FString> UpgradeHeaders;
	UpgradeHeaders.Add(TEXT("upgrade"), TEXT("websocket"));

	Socket = FWebSocketsModule::Get().CreateWebSocket(ServerURL, ServerProtocol, UpgradeHeaders);
}

void FOpenPypeModule::ConnectToSocket() {
	// We bind all available events
	Socket->OnConnected().AddLambda([]() -> void {
		// This code will run once connected.
		UE_LOG(LogTemp, Warning, TEXT("Connected"));
	});

	Socket->OnConnectionError().AddLambda([](const FString & Error) -> void {
		// This code will run if the connection failed. Check Error to see what happened.
		UE_LOG(LogTemp, Warning, TEXT("Error during connection"));
		UE_LOG(LogTemp, Warning, TEXT("%s"), *Error);
	});

	Socket->OnClosed().AddLambda([](int32 StatusCode, const FString& Reason, bool bWasClean) -> void {
		// This code will run when the connection to the server has been terminated.
		// Because of an error or a call to Socket->Close().
	});

	Socket->OnMessage().AddLambda([](const FString & Message) -> void {
		// This code will run when we receive a string message from the server.
	});

	Socket->OnRawMessage().AddLambda([](const void* Data, SIZE_T Size, SIZE_T BytesRemaining) -> void {
		// This code will run when we receive a raw (binary) message from the server.
	});

	Socket->OnMessageSent().AddLambda([](const FString& MessageString) -> void {
		// This code is called after we sent a message to the server.
	});

	UE_LOG(LogTemp, Warning, TEXT("Connecting web socket to server..."));

	// And we finally connect to the server.
	Socket->Connect();
}

IMPLEMENT_MODULE(FOpenPypeModule, OpenPype)
