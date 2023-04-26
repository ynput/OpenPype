// Copyright 2023, Ayon, All rights reserved.
#pragma once
#include "AyonPythonBridge.generated.h"

UCLASS(Blueprintable)
class UAyonPythonBridge : public UObject
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category = Python)
		static UAyonPythonBridge* Get();

	UFUNCTION(BlueprintImplementableEvent, Category = Python)
		void RunInPython_Popup() const;

	UFUNCTION(BlueprintImplementableEvent, Category = Python)
		void RunInPython_Dialog() const;

};
