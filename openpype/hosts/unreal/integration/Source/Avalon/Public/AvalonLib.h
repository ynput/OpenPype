#pragma once

#include "Engine.h"
#include "AvalonLib.generated.h"


UCLASS(Blueprintable)
class AVALON_API UAvalonLib : public UObject 
{

	GENERATED_BODY()

public: 
	UFUNCTION(BlueprintCallable, Category = Python)
		static void CSetFolderColor(FString FolderPath, FLinearColor FolderColor, bool bForceAdd);

	UFUNCTION(BlueprintCallable, Category = Python)
		static TArray<FString> GetAllProperties(UClass* cls);
};