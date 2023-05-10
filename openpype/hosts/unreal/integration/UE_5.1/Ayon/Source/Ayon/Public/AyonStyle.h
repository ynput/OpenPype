// Copyright 2023, Ayon, All rights reserved.
#pragma once
#include "CoreMinimal.h"
#include "Styling/SlateStyle.h"

class FAyonStyle
{
public:
	static void Initialize();
	static void Shutdown();
	static void ReloadTextures();
	static const ISlateStyle& Get();
	static FName GetStyleSetName();


private:
	static TSharedRef< class FSlateStyleSet > Create();
	static TSharedPtr< class FSlateStyleSet > AyonStyleInstance;
};