// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Factories/Factory.h"
#include "AssetContainerFactory.generated.h"

/**
 * 
 */
UCLASS()
class OPENPYPE_API UAssetContainerFactory : public UFactory
{
	GENERATED_BODY()

public:
	UAssetContainerFactory(const FObjectInitializer& ObjectInitializer);
	virtual UObject* FactoryCreateNew(UClass* Class, UObject* InParent, FName Name, EObjectFlags Flags, UObject* Context, FFeedbackContext* Warn) override;
	virtual bool ShouldShowInNewMenu() const override;
};