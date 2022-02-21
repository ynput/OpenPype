#pragma once

#include "CoreMinimal.h"
#include "Factories/Factory.h"
#include "AvalonPublishInstanceFactory.generated.h"

/**
 *
 */
UCLASS()
class AVALON_API UAvalonPublishInstanceFactory : public UFactory
{
	GENERATED_BODY()

public:
	UAvalonPublishInstanceFactory(const FObjectInitializer& ObjectInitializer);
	virtual UObject* FactoryCreateNew(UClass* Class, UObject* InParent, FName Name, EObjectFlags Flags, UObject* Context, FFeedbackContext* Warn) override;
	virtual bool ShouldShowInNewMenu() const override;
};