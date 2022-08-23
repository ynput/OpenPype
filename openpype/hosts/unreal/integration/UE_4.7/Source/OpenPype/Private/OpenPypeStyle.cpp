#include "OpenPypeStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "Styling/SlateStyle.h"
#include "Styling/SlateStyleRegistry.h"


TUniquePtr< FSlateStyleSet > FOpenPypeStyle::OpenPypeStyleInstance = nullptr;

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
	if (OpenPypeStyleInstance.IsValid())
	{
		FSlateStyleRegistry::UnRegisterSlateStyle(*OpenPypeStyleInstance);
		OpenPypeStyleInstance.Reset();
	}
}

FName FOpenPypeStyle::GetStyleSetName()
{
	static FName StyleSetName(TEXT("OpenPypeStyle"));
	return StyleSetName;
}

FName FOpenPypeStyle::GetContextName()
{
	static FName ContextName(TEXT("OpenPype"));
	return ContextName;
}

#define IMAGE_BRUSH(RelativePath, ...) FSlateImageBrush( Style->RootToContentDir( RelativePath, TEXT(".png") ), __VA_ARGS__ )

const FVector2D Icon40x40(40.0f, 40.0f);

TUniquePtr< FSlateStyleSet > FOpenPypeStyle::Create()
{
	TUniquePtr< FSlateStyleSet > Style = MakeUnique<FSlateStyleSet>(GetStyleSetName());
	Style->SetContentRoot(FPaths::ProjectPluginsDir() / TEXT("OpenPype/Resources"));

	return Style;
}

void FOpenPypeStyle::SetIcon(const FString& StyleName, const FString& ResourcePath)
{
	FSlateStyleSet* Style = OpenPypeStyleInstance.Get();

	FString Name(GetContextName().ToString());
	Name = Name + "." + StyleName;
	Style->Set(*Name, new FSlateImageBrush(Style->RootToContentDir(ResourcePath, TEXT(".png")), Icon40x40));


	FSlateApplication::Get().GetRenderer()->ReloadTextureResources();
}

#undef IMAGE_BRUSH

const ISlateStyle& FOpenPypeStyle::Get()
{
	check(OpenPypeStyleInstance);
	return *OpenPypeStyleInstance;
	return *OpenPypeStyleInstance;
}
