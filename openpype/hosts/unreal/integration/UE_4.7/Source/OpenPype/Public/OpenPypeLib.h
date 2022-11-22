#pragma once

#include "Engine.h"
#include "OpenPypeLib.generated.h"


UCLASS(Blueprintable)
class OPENPYPE_API UOpenPypeLib : public UObject
{

	GENERATED_BODY()

public: 
	UFUNCTION(BlueprintCallable, Category = Python)
		static void CSetFolderColor(FString FolderPath, FLinearColor FolderColor, bool bForceAdd);

	UFUNCTION(BlueprintCallable, Category = Python)
		static TArray<FString> GetAllProperties(UClass* cls);
};