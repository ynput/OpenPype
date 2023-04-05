// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Factories/Factory.h"
#include "AyonAssetContainerFactory.generated.h"

UCLASS()
class AYON_API UAyonAssetContainerFactory : public UFactory
{
	GENERATED_BODY()

public:
	UAyonAssetContainerFactory(const FObjectInitializer& ObjectInitializer);
	virtual UObject* FactoryCreateNew(UClass* Class, UObject* InParent, FName Name, EObjectFlags Flags, UObject* Context, FFeedbackContext* Warn) override;
	virtual bool ShouldShowInNewMenu() const override;
};
