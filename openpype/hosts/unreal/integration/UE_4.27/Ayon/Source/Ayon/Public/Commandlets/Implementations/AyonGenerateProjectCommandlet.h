// Copyright 2023, Ayon, All rights reserved.
#pragma once

#include "GameProjectUtils.h"
#include "Commandlets/AyonActionResult.h"
#include "ProjectDescriptor.h"
#include "Commandlets/Commandlet.h"
#include "AyonGenerateProjectCommandlet.generated.h"

struct FProjectDescriptor;
struct FProjectInformation;

/**
* @brief Structure which parses command line parameters and generates FProjectInformation
*/
USTRUCT()
struct FAyonGenerateProjectParams
{
	GENERATED_BODY()

private:
	FString CommandLineParams;
	TArray<FString> Tokens;
	TArray<FString> Switches;

public:
	FAyonGenerateProjectParams();
	FAyonGenerateProjectParams(const FString& CommandLineParams);

	FProjectInformation GenerateUEProjectInformation() const;

private:
	FString TryGetToken(const int32 Index) const;
	FString GetProjectFileName() const;

	bool IsSwitchPresent(const FString& Switch) const;
};
 
UCLASS()
class AYON_API UAyonGenerateProjectCommandlet : public UCommandlet
{
	GENERATED_BODY()

private:
	FProjectInformation ProjectInformation;
	FProjectDescriptor ProjectDescriptor;

public:
	UAyonGenerateProjectCommandlet();
	
	virtual int32 Main(const FString& CommandLineParams) override;

private:
	FAyonGenerateProjectParams ParseParameters(const FString& Params) const;
	FAyon_ActionResult TryCreateProject() const;
	FAyon_ActionResult TryLoadProjectDescriptor();
	void AttachPluginsToProjectDescriptor();
	FAyon_ActionResult TrySave();
};

