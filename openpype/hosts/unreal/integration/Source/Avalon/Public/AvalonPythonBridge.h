#pragma once
#include "Engine.h"
#include "AvalonPythonBridge.generated.h"

UCLASS(Blueprintable)
class UAvalonPythonBridge : public UObject
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category = Python)
		static UAvalonPythonBridge* Get();

	UFUNCTION(BlueprintImplementableEvent, Category = Python)
		void RunInPython_Popup() const;

	UFUNCTION(BlueprintImplementableEvent, Category = Python)
		void RunInPython_Dialog() const;

};
