// Copyright 2023, Ayon, All rights reserved.

#include "Commandlets/OPActionResult.h"
#include "Logging/OP_Log.h"

EOP_ActionResult::Type& FOP_ActionResult::GetStatus()
{
	return Status;
}

FText& FOP_ActionResult::GetReason()
{
	return Reason;
}

FOP_ActionResult::FOP_ActionResult():Status(EOP_ActionResult::Type::Ok)
{
	
}

FOP_ActionResult::FOP_ActionResult(const EOP_ActionResult::Type& InEnum):Status(InEnum)
{
	TryLog();
}

FOP_ActionResult::FOP_ActionResult(const EOP_ActionResult::Type& InEnum, const FText& InReason):Status(InEnum), Reason(InReason)
{
	TryLog();
};

bool FOP_ActionResult::IsProblem() const
{
	return Status != EOP_ActionResult::Ok;
}

void FOP_ActionResult::TryLog() const
{
	if(IsProblem())		
		UE_LOG(LogCommandletOPGenerateProject, Error, TEXT("%s"), *Reason.ToString());		
}
