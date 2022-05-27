#include "OpenPype.h"
#include "LevelEditor.h"
#include "OpenPypePythonBridge.h"
#include "OpenPypeStyle.h"


static const FName OpenPypeTabName("OpenPype");

#define LOCTEXT_NAMESPACE "FOpenPypeModule"

// This function is triggered when the plugin is staring up
void FOpenPypeModule::StartupModule()
{

	FOpenPypeStyle::Initialize();
	FOpenPypeStyle::SetIcon("Logo", "openpype40");

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

IMPLEMENT_MODULE(FOpenPypeModule, OpenPype)
