// Copyright 2023, Ayon, All rights reserved.
#pragma once


#include "GameProjectUtils.h"
#include "Commandlets/OPActionResult.h"
#include "ProjectDescriptor.h"
#include "Commandlets/Commandlet.h"
#include "OPGenerateProjectCommandlet.generated.h"

struct FProjectDescriptor;
struct FProjectInformation;

/**
* @brief Structure which parses command line parameters and generates FProjectInformation
*/
USTRUCT()
struct FOPGenerateProjectParams
{
	GENERATED_BODY()

private:
	FString CommandLineParams;
	TArray<FString> Tokens;
	TArray<FString> Switches;

public:
	FOPGenerateProjectParams();
	FOPGenerateProjectParams(const FString& CommandLineParams);

	FProjectInformation GenerateUEProjectInformation() const;

private:
	FString TryGetToken(const int32 Index) const;
	FString GetProjectFileName() const;

	bool IsSwitchPresent(const FString& Switch) const;
};
 
UCLASS()
class OPENPYPE_API UOPGenerateProjectCommandlet : public UCommandlet
{
	GENERATED_BODY()

private:
	FProjectInformation ProjectInformation;
	FProjectDescriptor ProjectDescriptor;

public:
	UOPGenerateProjectCommandlet();
	
	virtual int32 Main(const FString& CommandLineParams) override;

private:
	FOPGenerateProjectParams ParseParameters(const FString& Params) const;
	FOP_ActionResult TryCreateProject() const;
	FOP_ActionResult TryLoadProjectDescriptor();
	void AttachPluginsToProjectDescriptor();
	FOP_ActionResult TrySave();
};

