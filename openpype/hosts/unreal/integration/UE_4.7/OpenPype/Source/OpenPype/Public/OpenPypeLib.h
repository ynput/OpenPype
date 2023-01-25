#pragma once

#include "Engine.h"
#include "OpenPypeLib.generated.h"


UCLASS(Blueprintable)
class OPENPYPE_API UOpenPypeLib : public UBlueprintFunctionLibrary
{

	GENERATED_BODY()

public: 
	UFUNCTION(BlueprintCallable, Category = Python)
		static bool SetFolderColor(const FString& FolderPath, const FLinearColor& FolderColor,const bool& bForceAdd);

	UFUNCTION(BlueprintCallable, Category = Python)
		static TArray<FString> GetAllProperties(UClass* cls);
};