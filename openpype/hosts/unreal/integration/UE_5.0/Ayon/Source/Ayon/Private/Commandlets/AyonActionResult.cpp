// Copyright 2023, Ayon, All rights reserved.

#include "Commandlets/AyonActionResult.h"
#include "Logging/Ayon_Log.h"

EAyon_ActionResult::Type& FAyon_ActionResult::GetStatus()
{
	return Status;
}

FText& FAyon_ActionResult::GetReason()
{
	return Reason;
}

FAyon_ActionResult::FAyon_ActionResult():Status(EAyon_ActionResult::Type::Ok)
{
	
}

FAyon_ActionResult::FAyon_ActionResult(const EAyon_ActionResult::Type& InEnum):Status(InEnum)
{
	TryLog();
}

FAyon_ActionResult::FAyon_ActionResult(const EAyon_ActionResult::Type& InEnum, const FText& InReason):Status(InEnum), Reason(InReason)
{
	TryLog();
};

bool FAyon_ActionResult::IsProblem() const
{
	return Status != EAyon_ActionResult::Ok;
}

void FAyon_ActionResult::TryLog() const
{
	if(IsProblem())		
		UE_LOG(LogCommandletAyonGenerateProject, Error, TEXT("%s"), *Reason.ToString());		
}
