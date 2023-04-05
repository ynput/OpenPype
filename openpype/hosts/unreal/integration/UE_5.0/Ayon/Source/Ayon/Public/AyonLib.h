// Copyright 2023, Ayon, All rights reserved.
#pragma once

#include "AyonLib.generated.h"


UCLASS(Blueprintable)
class AYON_API UAyonLib : public UBlueprintFunctionLibrary
{

	GENERATED_BODY()

public: 
	UFUNCTION(BlueprintCallable, Category = Python)
		static bool SetFolderColor(const FString& FolderPath, const FLinearColor& FolderColor,const bool& bForceAdd);

	UFUNCTION(BlueprintCallable, Category = Python)
		static TArray<FString> GetAllProperties(UClass* cls);
};