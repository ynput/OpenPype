// Copyright 2023, Ayon, All rights reserved.
#pragma once

#include "CoreMinimal.h"
#include "Factories/Factory.h"
#include "AyonPublishInstanceFactory.generated.h"

/**
 *
 */
UCLASS()
class AYON_API UAyonPublishInstanceFactory : public UFactory
{
	GENERATED_BODY()

public:
	UAyonPublishInstanceFactory(const FObjectInitializer& ObjectInitializer);
	virtual UObject* FactoryCreateNew(UClass* InClass, UObject* InParent, FName InName, EObjectFlags Flags, UObject* Context, FFeedbackContext* Warn) override;
	virtual bool ShouldShowInNewMenu() const override;
};
