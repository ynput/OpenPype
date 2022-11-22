#pragma once
#include "Engine.h"
#include "OpenPypePythonBridge.generated.h"

UCLASS(Blueprintable)
class UOpenPypePythonBridge : public UObject
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category = Python)
		static UOpenPypePythonBridge* Get();

	UFUNCTION(BlueprintImplementableEvent, Category = Python)
		void RunInPython_Popup() const;

	UFUNCTION(BlueprintImplementableEvent, Category = Python)
		void RunInPython_Dialog() const;

};
