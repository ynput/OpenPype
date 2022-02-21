#pragma once
#include "CoreMinimal.h"

class FSlateStyleSet;
class ISlateStyle;


class FAvalonStyle
{
public:
	static void Initialize();
	static void Shutdown();
	static const ISlateStyle& Get();
	static FName GetStyleSetName();
	static FName GetContextName();

	static void SetIcon(const FString& StyleName, const FString& ResourcePath);

private:
	static TUniquePtr< FSlateStyleSet > Create();
	static TUniquePtr< FSlateStyleSet > AvalonStyleInstance;
};