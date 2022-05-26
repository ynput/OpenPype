#include "OpenPype.h"
#include "OpenPypeStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "Styling/SlateStyleRegistry.h"
#include "Slate/SlateGameResources.h"
#include "Interfaces/IPluginManager.h"
#include "Styling/SlateStyleMacros.h"

#define RootToContentDir Style->RootToContentDir

TSharedPtr<FSlateStyleSet> FOpenPypeStyle::OpenPypeStyleInstance = nullptr;

void FOpenPypeStyle::Initialize()
{
	if (!OpenPypeStyleInstance.IsValid())
	{
		OpenPypeStyleInstance = Create();
		FSlateStyleRegistry::RegisterSlateStyle(*OpenPypeStyleInstance);
	}
}

void FOpenPypeStyle::Shutdown()
{
	FSlateStyleRegistry::UnRegisterSlateStyle(*OpenPypeStyleInstance);
	ensure(OpenPypeStyleInstance.IsUnique());
	OpenPypeStyleInstance.Reset();
}

FName FOpenPypeStyle::GetStyleSetName()
{
	static FName StyleSetName(TEXT("OpenPypeStyle"));
	return StyleSetName;
}

const FVector2D Icon16x16(16.0f, 16.0f);
const FVector2D Icon20x20(20.0f, 20.0f);
const FVector2D Icon40x40(40.0f, 40.0f);

TSharedRef< FSlateStyleSet > FOpenPypeStyle::Create()
{
	TSharedRef< FSlateStyleSet > Style = MakeShareable(new FSlateStyleSet("OpenPypeStyle"));
	Style->SetContentRoot(IPluginManager::Get().FindPlugin("OpenPype")->GetBaseDir() / TEXT("Resources"));

	Style->Set("OpenPype.OpenPypeTools", new IMAGE_BRUSH(TEXT("openpype40"), Icon40x40));
	Style->Set("OpenPype.OpenPypeToolsDialog", new IMAGE_BRUSH(TEXT("openpype40"), Icon40x40));

	return Style;
}

void FOpenPypeStyle::ReloadTextures()
{
	if (FSlateApplication::IsInitialized())
	{
		FSlateApplication::Get().GetRenderer()->ReloadTextureResources();
	}
}

const ISlateStyle& FOpenPypeStyle::Get()
{
	return *OpenPypeStyleInstance;
}
