// Copyright 2023, Ayon, All rights reserved.
// Deprecation warning: this is left here just for backwards compatibility
// and will be removed in next versions of Ayon.
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
