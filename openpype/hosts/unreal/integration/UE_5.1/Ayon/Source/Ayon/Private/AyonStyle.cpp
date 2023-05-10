// Copyright 2023, Ayon, All rights reserved.

#include "AyonStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "Styling/SlateStyleRegistry.h"
#include "Slate/SlateGameResources.h"
#include "Interfaces/IPluginManager.h"
#include "Styling/SlateStyleMacros.h"

#define RootToContentDir Style->RootToContentDir

TSharedPtr<FSlateStyleSet> FAyonStyle::AyonStyleInstance = nullptr;

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
	FSlateStyleRegistry::UnRegisterSlateStyle(*AyonStyleInstance);
	ensure(AyonStyleInstance.IsUnique());
	AyonStyleInstance.Reset();
}

FName FAyonStyle::GetStyleSetName()
{
	static FName StyleSetName(TEXT("AyonStyle"));
	return StyleSetName;
}

const FVector2D Icon16x16(16.0f, 16.0f);
const FVector2D Icon20x20(20.0f, 20.0f);
const FVector2D Icon40x40(40.0f, 40.0f);

TSharedRef< FSlateStyleSet > FAyonStyle::Create()
{
	TSharedRef< FSlateStyleSet > Style = MakeShareable(new FSlateStyleSet("AyonStyle"));
	Style->SetContentRoot(IPluginManager::Get().FindPlugin("Ayon")->GetBaseDir() / TEXT("Resources"));

	Style->Set("Ayon.AyonTools", new IMAGE_BRUSH(TEXT("ayon40"), Icon40x40));
	Style->Set("Ayon.AyonToolsDialog", new IMAGE_BRUSH(TEXT("ayon40"), Icon40x40));

	return Style;
}

void FAyonStyle::ReloadTextures()
{
	if (FSlateApplication::IsInitialized())
	{
		FSlateApplication::Get().GetRenderer()->ReloadTextureResources();
	}
}

const ISlateStyle& FAyonStyle::Get()
{
	return *AyonStyleInstance;
}
