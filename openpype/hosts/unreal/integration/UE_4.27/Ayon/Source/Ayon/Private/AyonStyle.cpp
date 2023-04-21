// Copyright 2023, Ayon, All rights reserved.
#include "AyonStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "Styling/SlateStyle.h"
#include "Styling/SlateStyleRegistry.h"


TUniquePtr< FSlateStyleSet > FAyonStyle::AyonStyleInstance = nullptr;

void FAyonStyle::Initialize()
{
	if (!AyonStyleInstance.IsValid())
	{
		AyonStyleInstance = Create();
		FSlateStyleRegistry::RegisterSlateStyle(*AyonStyleInstance);
	}
}

void FAyonStyle::Shutdown()
{
	if (AyonStyleInstance.IsValid())
	{
		FSlateStyleRegistry::UnRegisterSlateStyle(*AyonStyleInstance);
		AyonStyleInstance.Reset();
	}
}

FName FAyonStyle::GetStyleSetName()
{
	static FName StyleSetName(TEXT("AyonStyle"));
	return StyleSetName;
}

FName FAyonStyle::GetContextName()
{
	static FName ContextName(TEXT("Ayon"));
	return ContextName;
}

#define IMAGE_BRUSH(RelativePath, ...) FSlateImageBrush( Style->RootToContentDir( RelativePath, TEXT(".png") ), __VA_ARGS__ )

const FVector2D Icon40x40(40.0f, 40.0f);

TUniquePtr< FSlateStyleSet > FAyonStyle::Create()
{
	TUniquePtr< FSlateStyleSet > Style = MakeUnique<FSlateStyleSet>(GetStyleSetName());
	Style->SetContentRoot(FPaths::EnginePluginsDir() / TEXT("Marketplace/Ayon/Resources"));

	return Style;
}

void FAyonStyle::SetIcon(const FString& StyleName, const FString& ResourcePath)
{
	FSlateStyleSet* Style = AyonStyleInstance.Get();

	FString Name(GetContextName().ToString());
	Name = Name + "." + StyleName;
	Style->Set(*Name, new FSlateImageBrush(Style->RootToContentDir(ResourcePath, TEXT(".png")), Icon40x40));


	FSlateApplication::Get().GetRenderer()->ReloadTextureResources();
}

#undef IMAGE_BRUSH

const ISlateStyle& FAyonStyle::Get()
{
	check(AyonStyleInstance);
	return *AyonStyleInstance;
}
