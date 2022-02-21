#include "AvalonStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "Styling/SlateStyle.h"
#include "Styling/SlateStyleRegistry.h"


TUniquePtr< FSlateStyleSet > FAvalonStyle::AvalonStyleInstance = nullptr;

void FAvalonStyle::Initialize()
{
	if (!AvalonStyleInstance.IsValid())
	{
		AvalonStyleInstance = Create();
		FSlateStyleRegistry::RegisterSlateStyle(*AvalonStyleInstance);
	}
}

void FAvalonStyle::Shutdown()
{
	if (AvalonStyleInstance.IsValid())
	{
		FSlateStyleRegistry::UnRegisterSlateStyle(*AvalonStyleInstance);
		AvalonStyleInstance.Reset();
	}
}

FName FAvalonStyle::GetStyleSetName()
{
	static FName StyleSetName(TEXT("AvalonStyle"));
	return StyleSetName;
}

FName FAvalonStyle::GetContextName()
{
	static FName ContextName(TEXT("OpenPype"));
	return ContextName;
}

#define IMAGE_BRUSH(RelativePath, ...) FSlateImageBrush( Style->RootToContentDir( RelativePath, TEXT(".png") ), __VA_ARGS__ )

const FVector2D Icon40x40(40.0f, 40.0f);

TUniquePtr< FSlateStyleSet > FAvalonStyle::Create()
{
	TUniquePtr< FSlateStyleSet > Style = MakeUnique<FSlateStyleSet>(GetStyleSetName());
	Style->SetContentRoot(FPaths::ProjectPluginsDir() / TEXT("Avalon/Resources"));

	return Style;
}

void FAvalonStyle::SetIcon(const FString& StyleName, const FString& ResourcePath)
{
	FSlateStyleSet* Style = AvalonStyleInstance.Get();

	FString Name(GetContextName().ToString());
	Name = Name + "." + StyleName;
	Style->Set(*Name, new FSlateImageBrush(Style->RootToContentDir(ResourcePath, TEXT(".png")), Icon40x40));


	FSlateApplication::Get().GetRenderer()->ReloadTextureResources();
}

#undef IMAGE_BRUSH

const ISlateStyle& FAvalonStyle::Get()
{
	check(AvalonStyleInstance);
	return *AvalonStyleInstance;
}
