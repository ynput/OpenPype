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
	FString ls() const;

	UFUNCTION(BlueprintImplementableEvent, Category = Python)
	FString containerise(const FString & name, const FString & namespc, const FString & str_nodes, const FString & str_context, const FString & loader, const FString & suffix) const;

	UFUNCTION(BlueprintImplementableEvent, Category = Python)
	FString instantiate(const FString & root, const FString & name, const FString & str_data, const FString & str_assets, const FString & suffix) const;
};
