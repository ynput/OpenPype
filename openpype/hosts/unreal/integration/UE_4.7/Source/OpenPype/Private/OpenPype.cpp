#include "OpenPype.h"
#include "LevelEditor.h"
#include "OpenPypePythonBridge.h"
#include "OpenPypeStyle.h"
#include "GenericPlatform/GenericPlatformMisc.h"
#include "WebSocketsModule.h" // Module definition


static const FName OpenPypeTabName("OpenPype");

#define LOCTEXT_NAMESPACE "FOpenPypeModule"

// This function is triggered when the plugin is staring up
void FOpenPypeModule::StartupModule()
{

	FOpenPypeStyle::Initialize();
	FOpenPypeStyle::SetIcon("Logo", "openpype40");

	CreateSocket();
	ConnectToSocket();

	// Create the Extender that will add content to the menu
	FLevelEditorModule& LevelEditorModule = FModuleManager::LoadModuleChecked<FLevelEditorModule>("LevelEditor");

	TSharedPtr<FExtender> MenuExtender = MakeShareable(new FExtender());
	TSharedPtr<FExtender> ToolbarExtender = MakeShareable(new FExtender());

	MenuExtender->AddMenuExtension(
		"LevelEditor",
		EExtensionHook::After,
		NULL,
		FMenuExtensionDelegate::CreateRaw(this, &FOpenPypeModule::AddMenuEntry)
	);
	ToolbarExtender->AddToolBarExtension(
		"Settings",
		EExtensionHook::After,
		NULL,
		FToolBarExtensionDelegate::CreateRaw(this, &FOpenPypeModule::AddToobarEntry));


	LevelEditorModule.GetMenuExtensibilityManager()->AddExtender(MenuExtender);
	LevelEditorModule.GetToolBarExtensibilityManager()->AddExtender(ToolbarExtender);

}

void FOpenPypeModule::ShutdownModule()
{
	FOpenPypeStyle::Shutdown();
}


void FOpenPypeModule::AddMenuEntry(FMenuBuilder& MenuBuilder)
{
	// Create Section
	MenuBuilder.BeginSection("OpenPype", TAttribute<FText>(FText::FromString("OpenPype")));
	{
		// Create a Submenu inside of the Section
		MenuBuilder.AddMenuEntry(
			FText::FromString("Tools..."),
			FText::FromString("Pipeline tools"),
			FSlateIcon(FOpenPypeStyle::GetStyleSetName(), "OpenPype.Logo"),
			FUIAction(FExecuteAction::CreateRaw(this, &FOpenPypeModule::MenuPopup))
		);

		MenuBuilder.AddMenuEntry(
			FText::FromString("Tools dialog..."),
			FText::FromString("Pipeline tools dialog"),
			FSlateIcon(FOpenPypeStyle::GetStyleSetName(), "OpenPype.Logo"),
			FUIAction(FExecuteAction::CreateRaw(this, &FOpenPypeModule::MenuDialog))
		);

	}
	MenuBuilder.EndSection();
}

void FOpenPypeModule::AddToobarEntry(FToolBarBuilder& ToolbarBuilder)
{
	ToolbarBuilder.BeginSection(TEXT("OpenPype"));
	{
		ToolbarBuilder.AddToolBarButton(
			FUIAction(
				FExecuteAction::CreateRaw(this, &FOpenPypeModule::MenuPopup),
				NULL,
				FIsActionChecked()

			),
			NAME_None,
			LOCTEXT("OpenPype_label", "OpenPype"),
			LOCTEXT("OpenPype_tooltip", "OpenPype Tools"),
			FSlateIcon(FOpenPypeStyle::GetStyleSetName(), "OpenPype.Logo")
		);
	}
	ToolbarBuilder.EndSection();
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
